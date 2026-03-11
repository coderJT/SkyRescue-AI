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
    """
    drone = drones.get(drone_id, {})
    if not isinstance(drone, dict):
        return []

    target = drone.get('target_sector')
    if target and target != "__RECALL__":
        return []

    coords = drone.get('coordinates', [0, 0, 0])
    cx, cz = coords[0], coords[2]

    # Sectors claimed by other drones
    claimed = set()
    for did, d in drones.items():
        if did != drone_id and isinstance(d, dict) and d.get('target_sector'):
            claimed.add(d['target_sector'])

    # Count discovered hazards across the map
    discovered_fire = [sid for sid, s in sectors.items()
                       if isinstance(s, dict) and s.get('discovered') and s.get('hazard') == 'fire' and not s.get('scanned')]
    discovered_smoke = [sid for sid, s in sectors.items()
                        if isinstance(s, dict) and s.get('discovered') and s.get('hazard') == 'smoke' and not s.get('scanned')]
    has_urgent_hazards = len(discovered_fire) > 0 or len(discovered_smoke) > 0

    candidates = []
    for sid, sector in sectors.items():
        if not isinstance(sector, dict):
            continue
        if sector.get('scanned') or sector.get('hazard') == 'no_fly' or sid in claimed:
            continue

        center = sector.get('center', [0, 0])
        dist = math.sqrt((center[0] - cx)**2 + (center[1] - cz)**2)
        hazard = sector.get('hazard', 'clear')
        discovered = sector.get('discovered', False)

        time_limit = {'fire': 60, 'smoke': 180}.get(hazard, 600)
        time_left = max(0, time_limit - elapsed_seconds)

        if has_urgent_hazards:
            # ── PRIORITY PHASE: Fire first, then smoke, then frontier ──
            if hazard == 'fire' and discovered:
                score = time_left + (dist * 0.3)  # Urgent rescue
                reason = f"URGENT FIRE: {round(time_left)}s window, {round(dist)}u"
            elif hazard == 'smoke' and discovered:
                score = time_left + (dist * 0.5) + 100  # Secondary priority
                reason = f"SMOKE hazard: {round(time_left)}s window, {round(dist)}u"
            elif not discovered:
                score = dist + 300  # Explore to find more hazards
                reason = f"Frontier exploration, {round(dist)}u"
            else:
                score = dist + 500  # Low priority clear sectors
                reason = f"Clear sector, {round(dist)}u"
        else:
            # ── DISCOVERY PHASE: Spread drones across map to maximize frontier coverage ──
            # Prefer DISTANT undiscovered sectors to cover more ground with onboard sensors
            if not discovered:
                # Spread factor: prefer sectors far from other drones to maximize coverage
                min_drone_dist = float('inf')
                for did2, d2 in drones.items():
                    if did2 != drone_id and isinstance(d2, dict):
                        d2_coords = d2.get('coordinates', [0, 0, 0])
                        d2_dist = math.sqrt((center[0] - d2_coords[0])**2 + (center[1] - d2_coords[2])**2)
                        # Also check claimed targets' destinations
                        if d2.get('target_sector') and d2['target_sector'] in sectors:
                            t_center = sectors[d2['target_sector']].get('center', [0, 0])
                            t_dist = math.sqrt((center[0] - t_center[0])**2 + (center[1] - t_center[1])**2)
                            min_drone_dist = min(min_drone_dist, t_dist)
                        min_drone_dist = min(min_drone_dist, d2_dist)

                # Score: prefer sectors that are reachable but spread from other drones
                spread_bonus = max(0, 50 - min_drone_dist) * 3  # Penalty for being near other drones
                score = dist + spread_bonus
                reason = f"Discovery sweep, {round(dist)}u (spread: {round(min_drone_dist)}u from fleet)"
            else:
                score = dist + 200
                reason = f"Known clear sector, {round(dist)}u"

        candidates.append({
            "id": sid,
            "hazard": hazard if discovered else "unexplored",
            "distance": round(dist, 1),
            "reason": reason,
            "score": score
        })

    candidates.sort(key=lambda x: x["score"])
    return candidates[:3]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ASSIGNMENT TRACKER (prevents duplicate dispatches)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DroneAssignmentTracker:
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
    print("\n" + "="*50)
    print("🚀 COMMAND AGENT: Autonomous Swarm Brain Active")
    print("   Connected via MCP Protocol to Drone Fleet")
    print("="*50 + "\n")

    tracker = DroneAssignmentTracker()
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
            # Check for urgent hazards that might warrant interrupting low-priority missions
            discovered_fire = [sid for sid, s in sectors.items()
                               if isinstance(s, dict) and s.get('discovered') and s.get('hazard') == 'fire' and not s.get('scanned')]
            discovered_smoke = [sid for sid, s in sectors.items()
                                if isinstance(s, dict) and s.get('discovered') and s.get('hazard') == 'smoke' and not s.get('scanned')]
            urgent_needs = len(discovered_fire) + len(discovered_smoke)

            available = []
            for did, d in drones.items():
                if not isinstance(d, dict):
                    continue
                s = d.get('status', '').lower()
                target = d.get('target_sector')
                if s in ['active', 'idle', 'waiting_orders']:
                    if not target:
                        available.append(did)  # Truly idle
                    elif urgent_needs > 0 and target != "__RECALL__":
                        # Allow interruption: if drone is heading to clear/unknown, it can be reassigned to fire
                        t_sector = sectors.get(target, {})
                        if isinstance(t_sector, dict):
                            t_haz = t_sector.get('hazard', 'unknown')
                            if t_haz not in ['fire', 'smoke']:
                                available.append(did)

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
            print("\n--- SWARM STATUS ---")
            for did, d in drones.items():
                if not isinstance(d, dict):
                    continue
                target = d.get('target_sector', 'None')
                bat = round(d.get('battery', 0), 1)
                print(f"  {did}: {d.get('status','?').upper()} | Bat: {bat}% | Target: {target}")
            print("--------------------\n")

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

                # Build compact recommendation context
                rec_lines = []
                for did, recs in recommendations.items():
                    entries = "; ".join(f"{r['id']}({r['hazard']},{r['distance']}u)" for r in recs)
                    rec_lines.append(f"  {did}: {entries}")

                wind = world.get('wind', {})
                wind_desc = wind.get('description', 'Unknown')

                prompt = f"""Swarm coordination for {len(idle_drone_ids)} available drones.
Coverage: {world.get('coverage_pct',0)}% | Survivors: {world.get('found_survivors',0)}/{world.get('total_survivors',0)} | Wind: {wind_desc}

FLEET:
{chr(10).join(fleet_lines)}

CANDIDATES (id, hazard, distance):
{chr(10).join(rec_lines)}

RULES: 
1. Assign 1 unique sector per drone. Minimize travel. Never duplicate sectors. 
2. Recall if bat<25%. 
3. REASONING MUST BE SPECIFIC: explicitly mention battery %, distance, hazard type (or "frontier exploration" if unexplored), and wind.

JSON ONLY:
{{"strategy":"1 detailed sentence mentioning distances and battery","assignments":{{"drone_id":{{"sector":"SID","reason":"1 detailed sentence mentioning specific distance to target, hazard/exploration status, and current battery %"}}}}}}"""

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
                            reason = entry.get("reason", "Assigned by Commander.")
                        else:
                            sid = entry
                            reason = "Assigned by Commander."

                        if sid and sid not in assigned_sectors:
                            print(f"📡 DISPATCH: {did} → {sid} | {reason}")
                            await call_tool(session, "assign_target", {
                                "drone_id": did,
                                "sector_id": sid,
                                "reason": reason
                            })
                            assigned.append(did)
                            assigned_sectors.add(sid)  # Mark sector as taken

                            await call_tool(session, "log_mission_event", {
                                "message": f"REASON: {did} → {sid}: {reason}"
                            })
                        elif sid and sid in assigned_sectors:
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
