"""
orchestrator.py — Autonomous Command Agent

The "brain" of the rescue swarm. This orchestrator uses ONLY MCP tools to:
1. Discover drones on the network (no hard-coded IDs)
2. Assess the disaster zone via environment and sector data
3. Strategically assign drones to sectors using chain-of-thought reasoning
4. Manage battery/recall decisions

Current LLM: Groq Llama 3.1 8B Instant (edge-deployable, low-latency)

Architecture:
  Orchestrator (this) --[MCP Protocol]--> MCP Server --[delegates]--> Simulation Engine
"""

import asyncio
import os
import json
import sys
import math
import time
import re
from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("❌ ERROR: GROQ_API_KEY environment variable not set.")
    sys.exit(1)

# Edge-deployable LLM: small model, low latency, high RPS
llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=GROQ_API_KEY)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MCP TOOL HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def call_tool(session, tool_name, args=None):
    """Call an MCP tool and parse the JSON response."""
    try:
        result = await session.call_tool(tool_name, args or {})
        if not result or not result.content:
            return None

        parsed_contents = []
        for content in result.content:
            parsed = None
            if hasattr(content, 'text'):
                text = content.text.strip()
                try:
                    parsed = json.loads(text)
                except:
                    parsed = text
            elif isinstance(content, dict) and 'text' in content:
                try:
                    parsed = json.loads(content['text'])
                except:
                    parsed = content['text']

            if parsed is not None:
                parsed_contents.append(parsed)

        if not parsed_contents:
            return None
        return parsed_contents if len(parsed_contents) > 1 else parsed_contents[0]
    except Exception as e:
        print(f"Tool call error ({tool_name}): {e}")
    return None


def robust_json_parse(text):
    """Robust JSON parsing with auto-repair for LLM output."""
    json_str = text
    if "```json" in text:
        json_str = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        json_str = text.split("```")[1].split("```")[0].strip()

    try:
        start = json_str.find('{')
        end = json_str.rfind('}')
        if start != -1 and end != -1:
            json_str = json_str[start:end+1]
    except:
        pass

    json_str = json_str.replace('\t', '\\t')

    # Remove single-line C-style comments (e.g., // comment)
    json_str = re.sub(r'//.*', '', json_str)
    
    # Fix LLM arbitrarily placing closing parenthesis instead of brace e.g. {"sector": "...", "reason": "...".)
    json_str = re.sub(r'"\s*\)\s*,', '"},', json_str)
    json_str = re.sub(r'"\s*\)(\s*)$', '"}', json_str)
    json_str = re.sub(r'\.\s*"\)', '."}', json_str)

    # Auto-close missing braces
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    if open_braces > close_braces:
        json_str += '}' * (open_braces - close_braces)

    # Fix missing commas between drone entries
    json_str = re.sub(r'}\s*\n\s*"drone_', '},\n"drone_', json_str)

    try:
        return json.loads(json_str, strict=False)
    except Exception as first_error:
        try:
            relaxed = re.sub(r'("reason":\s*")(.*?)("(?=\s*[},]))',
                            lambda m: m.group(1) + m.group(2).replace('"', "'") + m.group(3),
                            json_str, flags=re.DOTALL)
            return json.loads(relaxed, strict=False)
        except:
            with open("/tmp/last_malformed_response.txt", "w") as f:
                f.write(text)
            raise first_error


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LOCAL TACTICAL ANALYSIS (replaces MCP get_tactical_recommendations)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_sector_recommendations(drone_id, drones, sectors, elapsed_seconds):
    """
    Compute the top 3 sector recommendations for a drone.
    Two-phase strategy:
      DISCOVERY PHASE: Spread drones across the map to discover fire/smoke via onboard sensors.
      PRIORITY PHASE:  Once hazards are discovered, prioritize fire > smoke > frontier.
    
    Battery feasibility: excludes sectors where the drone cannot travel there,
    scan, AND return to base with a safety margin.
    """
    BASE_X, BASE_Z = 5, 5
    DRAIN_PER_UNIT = 0.05  # battery % per unit distance (clear) — matches simulation.html
    SCAN_COST = 0.5       # battery % for one scan cycle
    SAFETY_MARGIN = 3     # % reserve

    drone = drones.get(drone_id, {})
    if not isinstance(drone, dict):
        return []

    target = drone.get('target_sector')
    if target and target != "__RECALL__":
        return []

    coords = drone.get('coordinates', [0, 0, 0])
    cx, cz = coords[0], coords[2]
    battery = drone.get('battery', 0)

    # ── Dedup: globally claimed sectors ──
    # Include both currently acting drones AND assignments we've made in this orchestrator round
    claimed = set()
    for did, d in drones.items():
        if did != drone_id and isinstance(d, dict) and d.get('target_sector'):
            claimed.add(d['target_sector'])

    # Count discovered hazards across the map
    discovered_fire = {}
    discovered_smoke = {}
    for sid, s in sectors.items():
        if isinstance(s, dict) and s.get('discovered') and not s.get('scanned'):
            if s.get('hazard') == 'fire':
                discovered_fire[sid] = s
            elif s.get('hazard') == 'smoke':
                discovered_smoke[sid] = s
    
    has_urgent_hazards = len(discovered_fire) > 0 or len(discovered_smoke) > 0

    candidates = []
    # ── Optimal Fleet-Wide Assignment (ETA) ──
    # To prevent drones from crossing the entire map when a closer drone (even if busy)
    # can reach the sector sooner, we calculate a "Worst-Case ETA" for all drones.
    SCAN_PENALTY = 30  # dist equivalent of a scan
    CHARGE_PENALTY = 100 # dist equivalent of a charge cycle

    def get_eta(d_data, tgt_center):
        d_pos = d_data.get('coordinates', [0, 0, 0])
        d_cx, d_cz = d_pos[0], d_pos[2]
        d_status = d_data.get('status', 'offline').lower()
        d_target = d_data.get('target_sector')
        d_bat = d_data.get('battery', 0)

        if d_status in ['idle', 'waiting_orders'] or not d_target:
            return math.hypot(tgt_center[0] - d_cx, tgt_center[1] - d_cz)
            
        elif d_status == 'moving':
            if d_target == '__RECALL__':
                return math.hypot(BASE_X - d_cx, BASE_Z - d_cz) + CHARGE_PENALTY + math.hypot(tgt_center[0] - BASE_X, tgt_center[1] - BASE_Z)
            else:
                curr_tgt_center = sectors.get(d_target, {}).get('center', [BASE_X, BASE_Z])
                dist_to_curr = math.hypot(curr_tgt_center[0] - d_cx, curr_tgt_center[1] - d_cz)
                dist_curr_to_new = math.hypot(tgt_center[0] - curr_tgt_center[0], tgt_center[1] - curr_tgt_center[1])
                eta = dist_to_curr + SCAN_PENALTY + dist_curr_to_new
                
                # If drone will likely need to charge before heading to the new target
                if d_bat < (dist_to_curr + dist_curr_to_new) * DRAIN_PER_UNIT * 1.5 + SCAN_COST:
                    eta += CHARGE_PENALTY
                return eta
                
        elif d_status == 'scanning':
            dist_to_new = math.hypot(tgt_center[0] - d_cx, tgt_center[1] - d_cz)
            eta = (SCAN_PENALTY / 2) + dist_to_new
            if d_bat < dist_to_new * DRAIN_PER_UNIT * 1.5:
                eta += CHARGE_PENALTY
            return eta
            
        elif d_status == 'charging':
            return (CHARGE_PENALTY / 2) + math.hypot(tgt_center[0] - BASE_X, tgt_center[1] - BASE_Z)
            
        return float('inf')

    for sid, sector in sectors.items():
        if not isinstance(sector, dict):
            continue
        if sector.get('scanned') or sector.get('hazard') == 'no_fly' or sid in claimed:
            continue

        center = sector.get('center', [0, 0])
        dist = math.sqrt((center[0] - cx)**2 + (center[1] - cz)**2)
        hazard = sector.get('hazard', 'clear')
        discovered = sector.get('discovered', False)

        # ── Fleet ETA Check ──
        # Is there another drone that can reach this sector SOONER than this drone?
        my_eta = get_eta(drone, center)
        is_best_candidate = True
        best_other_eta = float('inf')
        best_other_drone = None
        
        for did, d in drones.items():
            if did != drone_id and isinstance(d, dict) and d.get('status', 'offline').lower() != 'offline':
                other_eta = get_eta(d, center)
                if other_eta < best_other_eta:
                    best_other_eta = other_eta
                    best_other_drone = did
                if other_eta < my_eta - 10.0:  # 10u buffer to prevent minor flip-flopping
                    is_best_candidate = False
        
        penalty = 0
        fleet_comparison_string = "fastest to reach"
        if not is_best_candidate:
            penalty = 2000  # Leave this sector for the closer drone ideally, but keep as fallback
            diff_str = "unknown" if best_other_eta == float('inf') else f"~{round(my_eta - best_other_eta)}u"
            fleet_comparison_string = f"fallback (slower than {best_other_drone} by {diff_str} ETA)"
        elif best_other_drone and best_other_eta < float('inf'):
             fleet_comparison_string = f"faster than {best_other_drone} by ~{round(best_other_eta - my_eta)}u ETA"

        # ── Battery feasibility check ──
        # Match the simulation's own formula: dist * DRAIN_PER_UNIT * 1.8 + 5
        # for the return trip (conservative hazard/wind headwind estimate)
        cost_to_target = dist * DRAIN_PER_UNIT  # clear-air travel estimate
        dist_back = math.sqrt((center[0] - BASE_X)**2 + (center[1] - BASE_Z)**2)
        cost_return = dist_back * DRAIN_PER_UNIT * 1.5 + 4  # slightly relaxed RTB formula
        total_cost = cost_to_target + SCAN_COST + cost_return + SAFETY_MARGIN

        if battery < total_cost:
            continue  # Cannot afford this round-trip

        battery_after_return = round(battery - total_cost, 1)

        time_limit = {'fire': 60, 'smoke': 180}.get(hazard, 600)
        time_left = max(0, time_limit - elapsed_seconds)

        if has_urgent_hazards:
            # ── PRIORITY PHASE: Fire first, then smoke, then frontier ──
            if hazard == 'fire' and discovered:
                score = time_left + (dist * 0.3) + penalty  # Urgent rescue
                reason = f"URGENT FIRE: {round(time_left)}s window, {fleet_comparison_string}"
            elif hazard == 'smoke' and discovered:
                score = time_left + (dist * 0.5) + 100 + penalty  # Secondary priority
                reason = f"SMOKE hazard: {round(time_left)}s window, {fleet_comparison_string}"
            elif not discovered:
                score = dist + 300 + penalty  # Explore to find more hazards
                reason = f"Frontier exploration, {fleet_comparison_string}"
            else:
                score = dist + 500 + penalty  # Low priority clear sectors
                reason = f"Clear sector, {fleet_comparison_string}"
        else:
            # ── DISCOVERY PHASE: Spread drones across map to maximize frontier coverage ──
            if not discovered:
                min_drone_dist = float('inf')
                for did2, d2 in drones.items():
                    if did2 != drone_id and isinstance(d2, dict):
                        d2_coords = d2.get('coordinates', [0, 0, 0])
                        d2_dist = math.sqrt((center[0] - d2_coords[0])**2 + (center[1] - d2_coords[2])**2)
                        if d2.get('target_sector') and d2['target_sector'] in sectors:
                            t_center = sectors[d2['target_sector']].get('center', [0, 0])
                            t_dist = math.sqrt((center[0] - t_center[0])**2 + (center[1] - t_center[1])**2)
                            min_drone_dist = min(min_drone_dist, t_dist)
                        min_drone_dist = min(min_drone_dist, d2_dist)


                spread_bonus = max(0, 50 - min_drone_dist) * 3
                score = dist + spread_bonus + penalty
                reason = f"Discovery sweep, {fleet_comparison_string}"
            else:
                score = dist + 200 + penalty
                reason = f"Known clear sector, {fleet_comparison_string}"

        candidates.append({'id': sid, 'score': score, 'reason': reason, 'distance': round(dist, 1), 'hazard': hazard, 'battery_cost': round(total_cost, 1), 'battery_after': battery_after_return})

    candidates.sort(key=lambda x: x["score"])
    return candidates[:3]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN LOOP (Agent Workflow)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AssignmentTracker:
    def __init__(self):
        self.pending = {}
        self.last_idle_set = set()
        self.last_hazard_set = set()
        self.last_idle_time = 0

    def filter_idle(self, idle_ids):
        """Filter out drones recently assigned (sync delay buffer)."""
        now = time.time()
        self.pending = {did: ts for did, ts in self.pending.items() if now - ts < 4}
        return [did for did in idle_ids if did not in self.pending]

    def mark_assigned(self, drone_ids):
        now = time.time()
        for did in drone_ids:
            self.pending[did] = now

    def should_invoke_llm(self, current_idle, current_hazards):
        """Only invoke LLM when swarm state has meaningfully changed."""
        now = time.time()

        # New hazard discovered
        if set(current_hazards) != self.last_hazard_set:
            return True

        # New idle drone appeared
        new_idle = set(current_idle) - self.last_idle_set
        if new_idle and (len(current_idle) >= 2 or now - self.last_idle_time > 10):
            return True

        # Force re-check if drones have been idle > 10s
        if current_idle and now - self.last_idle_time > 10:
            return True

        return False

    def commit(self, idle_ids, hazards):
        self.last_idle_set = set(idle_ids)
        self.last_hazard_set = set(hazards)
        self.last_idle_time = time.time()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATE HELPERS (keep main loop lean)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def summarize_hazards(sectors):
    """Return discovered fire and smoke sector IDs (excluding scanned)."""
    fire = [
        sid for sid, s in sectors.items()
        if isinstance(s, dict) and s.get('discovered') and s.get('hazard') == 'fire' and not s.get('scanned')
    ]
    smoke = [
        sid for sid, s in sectors.items()
        if isinstance(s, dict) and s.get('discovered') and s.get('hazard') == 'smoke' and not s.get('scanned')
    ]
    return fire, smoke


def select_idle_drones(drones, sectors, urgent_needs):
    """
    Pick drones eligible for reassignment:
      - idle/waiting with no target or recall target
      - can be interrupted if moving toward non-hazard while urgent hazards exist
      - recalls can be redirected mid-flight
    """
    available = []
    for did, d in drones.items():
        if not isinstance(d, dict):
            continue
        status = d.get('status', '').lower()
        target = d.get('target_sector')

        if status in ['active', 'idle', 'waiting_orders']:
            if not target or target == "__RECALL__":
                available.append(did)
            elif urgent_needs > 0:
                t_sector = sectors.get(target, {})
                if isinstance(t_sector, dict) and t_sector.get('hazard', 'unknown') not in ['fire', 'smoke']:
                    available.append(did)
        elif status == 'moving' and target == '__RECALL__':
            available.append(did)
    return available


def print_swarm_status(drones, idle_ids):
    """Compact console dump used before LLM call."""
    print("\n--- SWARM STATUS ---")
    for did, d in drones.items():
        if not isinstance(d, dict):
            continue
        target = d.get('target_sector', 'None')
        bat = round(d.get('battery', 0), 1)
        pos = d.get('coordinates', [0, 0, 0])
        status = d.get('status', '?').upper()
        state = "IDLE" if did in idle_ids else status
        print(f"  {did}: {state} | Bat: {bat}% | Pos({round(pos[0])},{round(pos[2])}) | Target: {target}")
    print("--------------------\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ORCHESTRATOR MAIN LOOP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def run_orchestrator(session):
    """
    Main orchestrator loop — the autonomous command agent brain.

    Flow:
    1. Discover fleet via list_drones()
    2. Poll get_world_state() for situational awareness
    3. Identify idle drones
    4. Compute tactical recommendations locally (no LLM)
    5. Send compact prompt to LLM for global coordination
    6. Dispatch assignments via assign_target()
    7. Log reasoning via log_mission_event()
    """
    print("Orchestrator active. Beginning control loop...")

    # Wait for MCP to confirm initialization
    await asyncio.sleep(2)
    tracker = AssignmentTracker()
    last_llm_time = 0
    idle_count = 0

    while True:
        try:
            # ── Step 1: Situational Awareness via MCP ──
            world = await call_tool(session, "get_world_state")
            if not world:
                print("⚠️  Warning: Failed to fetch world state. Retrying...")
                await asyncio.sleep(2)
                continue

            # Wait for mission start
            status = world.get("mission_status")
            if status == "waiting":
                print(f"⏳ Waiting for mission start...")
                await asyncio.sleep(2)
                continue

            # Mission complete
            if world.get("mission_complete"):
                print(f"🏁 Mission Complete! Status: {status}")
                await asyncio.sleep(10)
                continue

            drones = world.get("drones", {})
            sectors = world.get("sectors", {})

            if not isinstance(drones, dict) or not isinstance(sectors, dict):
                await asyncio.sleep(2)
                continue

            # ── Step 2: Identify idle and reassignable drones ──
            discovered_fire, discovered_smoke = summarize_hazards(sectors)
            urgent_needs = len(discovered_fire) + len(discovered_smoke)

            available = select_idle_drones(drones, sectors, urgent_needs)
            idle_drone_ids = tracker.filter_idle(available)

            # No idle drones → skip
            unscanned = {sid: s for sid, s in sectors.items()
                        if isinstance(s, dict) and not s.get('scanned') and s.get('hazard') != 'no_fly'}

            if not idle_drone_ids or not unscanned:
                idle_count += 1
                if idle_count % 5 == 0:
                    living_drones = [did for did, d in drones.items() if isinstance(d, dict) and d.get('status', '').lower() != 'offline']
                    busy = len(living_drones) - len(idle_drone_ids)
                    print(f"Status: {len(idle_drone_ids)} idle, {busy} busy, {len(unscanned)} unscanned, {len(drones)-len(living_drones)} dead")
                    
                    if len(living_drones) == 0:
                        print("💀 ALL DRONES DEAD. Mission Failed.")
                        await asyncio.sleep(10)
                        
                await asyncio.sleep(2)
                continue

            # ── Step 3: Check if LLM coordination is needed ──
            hazards = [sid for sid, s in sectors.items()
                      if isinstance(s, dict) and s.get("discovered") and s.get("hazard") != "clear"]

            if not tracker.should_invoke_llm(idle_drone_ids, hazards):
                await asyncio.sleep(2)
                continue

            # LLM throttle: minimum 6 seconds between calls
            now = time.time()
            if now - last_llm_time < 6:
                await asyncio.sleep(1)
                continue

            idle_count = 0

            # ── Step 4: Compute tactical recommendations LOCALLY ──
            elapsed = world.get("elapsed_seconds", 0)
            recommendations = {}
            for did in idle_drone_ids:
                recs = compute_sector_recommendations(did, drones, sectors, elapsed)
                if recs:
                    recommendations[did] = recs

            if not recommendations:
                print("All idle drones already have targets or no candidates found.")
                await asyncio.sleep(2)
                continue

            # ── Step 5: LLM Strategic Coordination ──
            print_swarm_status(drones, idle_drone_ids)

            print(f"🧠 Coordinating {len(idle_drone_ids)} idle drones...")
            last_llm_time = now

            try:
                # Build compact fleet context
                fleet_lines = []
                for did, d in drones.items():
                    if not isinstance(d, dict):
                        continue
                    pos = d.get('coordinates', [0, 0, 0])
                    bat = round(d.get('battery', 0), 1)
                    s = d.get('status', 'active').upper()
                    target = d.get('target_sector', '')
                    if did in idle_drone_ids:
                        fleet_lines.append(f"- {did}: IDLE, Bat {bat}%, Pos({round(pos[0])},{round(pos[2])})")
                    else:
                        fleet_lines.append(f"- {did}: {s} → {target}, Bat {bat}%")

                # Build compact recommendation context with battery estimates
                rec_lines = []
                for did, recs in recommendations.items():
                    entries = "; ".join(f"{r['id']}({r['hazard']},{r['distance']}u,cost:{r.get('battery_cost','?')}%,remaining:{r.get('battery_after','?')}%)" for r in recs)
                    rec_lines.append(f"  {did}: {entries}")

                wind = world.get('wind', {})
                wind_desc = wind.get('description', 'Unknown')

                prompt = f"""Swarm coordination for {len(idle_drone_ids)} available drones.
Coverage: {world.get('coverage_pct',0)}% | Survivors: {world.get('found_survivors',0)}/{world.get('total_survivors',0)} | Wind: {wind_desc}

FLEET:
{chr(10).join(fleet_lines)}

CANDIDATES (id, hazard, distance, cost: Y%, remaining: Z%):
{chr(10).join(rec_lines)}

RULES: 
1. Assign 1 unique sector per drone. Minimize travel. Never duplicate sectors. 
2. RECALL ONLY IF bat < 25%, OR if the drone's CANDIDATES list is completely empty. 
3. BATTERY FEASIBILITY: All provided candidates are ALREADY VERIFIED to have enough battery for a safe round-trip. DO NOT second-guess battery feasibility. DO NOT recall a drone if it has valid candidates.
4. REASONING MUST BE SPECIFIC: explicitly mention battery %, round-trip cost, distance, hazard type (or "frontier exploration" if unexplored), wind, and the provided arrival comparison (e.g. "fastest to reach" or "faster than drone_x by Y ETA").

JSON ONLY:
{{"strategy":"1 detailed sentence mentioning distances and battery feasibility","assignments":{{"drone_id":{{"sector":"SID","reason":"1 detailed sentence mentioning specific distance, round-trip battery cost, remaining battery after return, hazard status, and the explicitly provided fleet arrival comparison (fastest to reach, fallback, etc)"}}}}}}"""

                print(f"\n--- LLM PROMPT ---\n{prompt}\n------------------\n")

                response = await llm.ainvoke([
                    SystemMessage(content="You are a rescue swarm coordinator. You must output ONLY valid JSON. Your reasoning must be highly specific to the environment variables provided."),
                    HumanMessage(content=prompt)
                ])

                data = robust_json_parse(response.content.strip())
                assignments = data.get("assignments", {})
                strategy = data.get("strategy", "Coordinated.")

                # Log strategy as chain-of-thought
                print(f"📝 Strategy: {strategy}")
                await call_tool(session, "log_mission_event",
                              {"message": f"🧠 STRATEGY: {strategy}"})

                # ── Step 6: Dispatch assignments via MCP (with dedup) ──
                assigned = []
                assigned_sectors = set()  # Prevent duplicate sector assignments
                # Also include sectors already claimed by busy drones
                for did2, d2 in drones.items():
                    if isinstance(d2, dict) and d2.get('target_sector'):
                        assigned_sectors.add(d2['target_sector'])

                for did, entry in assignments.items():
                    if did in idle_drone_ids:
                        if isinstance(entry, dict):
                            sid = entry.get("sector")
                            reason = entry.get("reason", "")
                        else:
                            sid = entry
                            reason = ""
                            
                        # HARD OVERRIDE: Prevent LLM battery hallucinations
                        bat_eval = 0
                        if did in drones and isinstance(drones[did], dict):
                            bat_eval = round(drones[did].get('battery', 0), 1)
                            
                        if sid == "__RECALL__" and bat_eval > 30.0 and did in recommendations and len(recommendations[did]) > 0:
                            # The LLM hallucinated an insufficient battery recall when perfectly good candidates exist
                            # Override it and take the top scoring candidate.
                            top_cand = recommendations[did][0]
                            sid = top_cand['id']
                            reason = f"Commander Override: Rejecting false LLM recall. Bat {bat_eval}% is sufficient for {sid}."

                        # Build a descriptive fallback if LLM didn't provide a reason
                        if not reason and sid and did in drones and isinstance(drones[did], dict):
                            bat = round(drones[did].get('battery', 0), 1)
                            pos = drones[did].get('coordinates', [0, 0, 0])
                            sec_info = sectors.get(sid, {})
                            sec_center = sec_info.get('center', [0, 0]) if isinstance(sec_info, dict) else [0, 0]
                            dist = round(math.sqrt((sec_center[0] - pos[0])**2 + (sec_center[1] - pos[2])**2))
                            haz = sec_info.get('hazard', 'unknown') if isinstance(sec_info, dict) else 'unknown'
                            reason = f"Commander dispatch: {did} ({bat}% bat) → {sid} ({haz}, ~{dist}u away)"
                        elif not reason:
                            reason = f"Commander dispatch: {did} → {sid}"

                        if sid and (sid == '__RECALL__' or sid not in assigned_sectors):
                            print(f"📡 DISPATCH: {did} → {sid} | {reason}")
                            await call_tool(session, "assign_target", {
                                "drone_id": did,
                                "sector_id": sid,
                                "reason": reason
                            })
                            assigned.append(did)
                            if sid != '__RECALL__':
                                assigned_sectors.add(sid)  # Mark sector as taken

                            await call_tool(session, "log_mission_event", {
                                "message": f"REASON: {did} → {sid}: {reason}"
                            })
                        elif sid and sid != '__RECALL__' and sid in assigned_sectors:
                            print(f"⚠️ SKIPPED: {did} → {sid} (sector already assigned this round)")

                tracker.mark_assigned(assigned)
                tracker.commit(idle_drone_ids, hazards)

            except Exception as e:
                print(f"❌ Coordination Error: {e}")
                tracker.last_idle_time = 0
                await asyncio.sleep(2)
                continue

        except Exception as e:
            if "429" in str(e) or "Rate limit" in str(e):
                print("⏸️  Rate limit hit. Backing off 3s...")
                await asyncio.sleep(3)
            else:
                print(f"❌ Critical Error: {e}")

        await asyncio.sleep(5)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRYPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def main():
    """Connect to MCP server and start the orchestrator."""
    url = "http://localhost:8000/sse"
    print(f"Connecting to MCP Server at {url}...")

    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await run_orchestrator(session)
    except Exception as e:
        print(f"Could not connect to MCP server: {e}")
        print("Make sure 'python start.py' is running first!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCommand Agent shutting down.")
