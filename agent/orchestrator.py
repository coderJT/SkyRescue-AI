"""
orchestrator.py — Autonomous Command Agent

Roles:
- Orchestrator (this file): edge LLM brain that only speaks MCP.
- MCP Server: exposes drone + world tools.
- Simulation Engine: source-of-truth state and physics.
- Drone code: vehicle dynamics & onboard sensing.
"""

import asyncio
import os
import sys
import time
from typing import Dict, List

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from mcp import ClientSession
from mcp.client.sse import sse_client

from mcp_helper import call_tool, robust_json_parse
from strategy import (
    AssignmentTracker,
    compute_sector_recommendations,
    print_swarm_status,
    select_idle_drones,
    summarize_hazards,
)


GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("❌ ERROR: GROQ_API_KEY environment variable not set.")
    sys.exit(1)

# Edge-deployable LLM: small model, low latency
llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=GROQ_API_KEY)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PROMPT BUILDING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_prompt(
    drones: Dict,
    sectors: Dict,
    idle_ids: List[str],
    recommendations: Dict,
    elapsed_seconds: float,
) -> str:
    fleet_lines = []
    for did, d in drones.items():
        if not isinstance(d, dict):
            continue
        pos = d.get("coordinates", [0, 0, 0])
        bat = round(d.get("battery", 0), 1)
        status = d.get("status", "active").upper()
        target = d.get("target_sector", "")
        if did in idle_ids:
            fleet_lines.append(f"- {did}: IDLE, Bat {bat}%, Pos({round(pos[0])},{round(pos[2])})")
        else:
            fleet_lines.append(f"- {did}: {status} → {target}, Bat {bat}%")

    rec_lines = []
    for did, recs in recommendations.items():
        entries = "; ".join(
            f"{r['id']}({r['hazard']},{r['distance']}u,cost:{r.get('battery_cost','?')}%,remaining:{r.get('battery_after','?')}%)"
            for r in recs
        )
        rec_lines.append(f"  {did}: {entries}")

    prompt = f"""
    
    
Swarm coordination for {len(idle_ids)} available drones.
Coverage: {sectors.get('coverage_pct',0)}% | Survivors: {sectors.get('found_survivors',0)}/{sectors.get('total_survivors',0)} | Wind: {sectors.get('wind','')}
Elapsed seconds: {elapsed_seconds}

FLEET:
{os.linesep.join(fleet_lines)}

CANDIDATES (id, hazard, distance, cost: Y%, remaining: Z%):
{os.linesep.join(rec_lines)}

RULES: 
1. Assign 1 unique sector per drone. Minimize travel. Never duplicate sectors. 
2. RECALL ONLY IF bat < 25%, OR if the drone's CANDIDATES list is completely empty. 
3. BATTERY FEASIBILITY: All provided candidates are ALREADY VERIFIED to have enough battery for a safe round-trip. DO NOT second-guess battery feasibility. DO NOT recall a drone if it has valid candidates.
4. REASONING MUST BE SPECIFIC: explicitly mention battery %, round-trip cost, distance, hazard type (or "frontier exploration" if unexplored), wind, and the provided arrival comparison (e.g. "fastest to reach" or "faster than drone_x by Y ETA").

JSON ONLY:
{{"strategy":"1 detailed sentence mentioning distances and battery feasibility","assignments":{{"drone_id":{{"sector":"SID","reason":"1 detailed sentence mentioning specific distance, round-trip battery cost, remaining battery after return, hazard status, and the explicitly provided fleet arrival comparison (fastest to reach, fallback, etc)"}}}}}}
"""
    return prompt.strip()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ORCHESTRATOR MAIN LOOP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def run_orchestrator(session):
    """Main orchestrator loop — the autonomous command agent brain."""
    print("Orchestrator active. Beginning control loop...")
    await asyncio.sleep(2)  # give MCP time to init

    tracker = AssignmentTracker()
    last_llm_time = 0
    idle_count = 0

    while True:
        try:
            world = await call_tool(session, "get_world_state")
            if not world:
                print("⚠️  Warning: Failed to fetch world state. Retrying...")
                await asyncio.sleep(2)
                continue

            status = world.get("mission_status")
            if status == "waiting":
                print("⏳ Waiting for mission start...")
                await asyncio.sleep(2)
                continue

            if world.get("mission_complete"):
                print(f"🏁 Mission Complete! Status: {status}")
                await asyncio.sleep(10)
                continue

            drones = world.get("drones", {})
            sectors = world.get("sectors", {})
            if not isinstance(drones, dict) or not isinstance(sectors, dict):
                await asyncio.sleep(2)
                continue

            discovered_fire, discovered_smoke = summarize_hazards(sectors)
            urgent_needs = len(discovered_fire) + len(discovered_smoke)

            available = select_idle_drones(drones, sectors, urgent_needs)
            idle_drone_ids = tracker.filter_idle(available)

            unscanned = {
                sid: s
                for sid, s in sectors.items()
                if isinstance(s, dict) and not s.get("scanned") and s.get("hazard") != "no_fly"
            }
            if not idle_drone_ids or not unscanned:
                idle_count += 1
                if idle_count % 5 == 0:
                    living = [did for did, d in drones.items() if isinstance(d, dict) and d.get("status", "").lower() != "offline"]
                    busy = len(living) - len(idle_drone_ids)
                    print(f"Status: {len(idle_drone_ids)} idle, {busy} busy, {len(unscanned)} unscanned, {len(drones)-len(living)} dead")
                    if len(living) == 0:
                        print("💀 ALL DRONES DEAD. Mission Failed.")
                        await asyncio.sleep(10)
                await asyncio.sleep(2)
                continue

            hazards = [sid for sid, s in sectors.items() if isinstance(s, dict) and s.get("discovered") and s.get("hazard") != "clear"]
            
            # Calculate recommendations for all idle drones immediately
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

            # ALWAYS try fast-path first for immediate assignment
            # Get currently assigned sectors
            currently_assigned_sectors = {
                d.get("target_sector")
                for did, d in drones.items()
                if isinstance(d, dict) and d.get("target_sector")
            }
            
            # Track which drones were assigned via fast path
            fast_path_assigned = []
            
            # Process drones in a coordinated way even in fast path to avoid duplicates
            # Sort by recommendation score to prioritize drones with better options
            drone_rec_pairs = []
            for did in idle_drone_ids:
                if did in recommendations and recommendations[did]:
                    top_rec = recommendations[did][0]
                    drone_rec_pairs.append((did, top_rec))
            
            # Sort by recommendation score (lower is better)
            drone_rec_pairs.sort(key=lambda x: x[1].get("score", 9999))
            
            fast_path_assigned_sectors = set(currently_assigned_sectors)
            
            for did, top_rec in drone_rec_pairs:
                sid = top_rec["id"]
                
                # Check if sector is already assigned (by other drones in this fast-path batch)
                if sid in fast_path_assigned_sectors:
                    # Try to find an alternative from this drone's recommendations
                    alt_rec = None
                    for rec in recommendations[did]:
                        if rec["id"] not in fast_path_assigned_sectors:
                            alt_rec = rec
                            break
                    
                    if alt_rec:
                        sid = alt_rec["id"]
                        reason = alt_rec.get("reason", f"Fast-path alternate to {sid} (original {top_rec['id']} taken)")
                    else:
                        # No alternative available, skip this drone for now
                        continue
                else:
                    reason = top_rec.get("reason", f"Fast-path assignment to {sid}")
                
                print(f"⚡ FAST-PATH: {did} → {sid} | {reason}")
                resp = await call_tool(session, "assign_target", {"drone_id": did, "sector_id": sid, "reason": reason})
                if resp and isinstance(resp, dict) and resp.get("error"):
                    print(f"⚠️ FAST-PATH ERROR for {did}: {resp['error']}")
                else:
                    fast_path_assigned.append(did)
                    fast_path_assigned_sectors.add(sid)
                    await call_tool(session, "log_mission_event", {"message": f"FAST-PATH: {did} → {sid}: {reason}"})
                    # Small delay between assignments to prevent congestion
                    await asyncio.sleep(0.05)
            
            # Update idle drone list to exclude those assigned via fast path
            idle_drone_ids = [did for did in idle_drone_ids if did not in fast_path_assigned]
            
            if fast_path_assigned:
                tracker.mark_assigned(fast_path_assigned)
                # Don't commit yet - we'll commit after LLM processing or if no LLM needed
            
            # If no drones left after fast-path, continue to next iteration
            if not idle_drone_ids:
                tracker.commit([], hazards)  # No idle drones left
                await asyncio.sleep(0.1)
                continue
            
            # Only use LLM if we have multiple drones left AND tracker says to invoke LLM
            # OR if we have hazards that need coordination
            if len(idle_drone_ids) > 1 and tracker.should_invoke_llm(idle_drone_ids, hazards):
                # Continue to LLM path below
                pass
            else:
                # Try to assign remaining drones with fast-path logic (non-LLM)
                # This handles cases like 1 drone remaining or when LLM isn't needed
                remaining_drone_rec_pairs = []
                for did in idle_drone_ids:
                    if did in recommendations and recommendations[did]:
                        # Filter recommendations to only unassigned sectors
                        available_recs = [r for r in recommendations[did] if r["id"] not in fast_path_assigned_sectors]
                        if available_recs:
                            remaining_drone_rec_pairs.append((did, available_recs[0]))
                
                # Sort by recommendation score
                remaining_drone_rec_pairs.sort(key=lambda x: x[1].get("score", 9999))
                
                for did, rec in remaining_drone_rec_pairs:
                    sid = rec["id"]
                    reason = rec.get("reason", f"Non-LLM assignment to {sid}")
                    
                    print(f"⚡ NON-LLM: {did} → {sid} | {reason}")
                    resp = await call_tool(session, "assign_target", {"drone_id": did, "sector_id": sid, "reason": reason})
                    if resp and isinstance(resp, dict) and resp.get("error"):
                        print(f"⚠️ NON-LLM ERROR for {did}: {resp['error']}")
                    else:
                        fast_path_assigned.append(did)
                        fast_path_assigned_sectors.add(sid)
                        await call_tool(session, "log_mission_event", {"message": f"NON-LLM: {did} → {sid}: {reason}"})
                        await asyncio.sleep(0.05)
                
                if fast_path_assigned:
                    tracker.mark_assigned(fast_path_assigned)
                    tracker.commit(idle_drone_ids, hazards)  # idle_drone_ids is updated to exclude assigned drones
                    await asyncio.sleep(0.1)
                    continue
                else:
                    # No assignments made, continue to LLM
                    pass
            
            # LLM PATH: Use LLM for complex coordination (multiple drones, hazards, etc.)
            now = time.time()
            if now - last_llm_time < 2:
                await asyncio.sleep(0.5)
                continue
            last_llm_time = now
            idle_count = 0

            print_swarm_status(drones, idle_drone_ids)
            print(f"🧠 Coordinating {len(idle_drone_ids)} idle drones with LLM...")

            prompt = build_prompt(drones, sectors, idle_drone_ids, recommendations, elapsed)
            try:
                response = await llm.ainvoke(
                    [
                        SystemMessage(content="You are a rescue swarm coordinator. You must output ONLY valid JSON. Your reasoning must be highly specific to the environment variables provided."),
                        HumanMessage(content=prompt),
                    ]
                )
                data = robust_json_parse(response.content.strip())
                assignments = data.get("assignments", {})
                strategy = data.get("strategy", "Coordinated.")
            except Exception as e:
                print(f"❌ LLM/parse error: {e}")
                await asyncio.sleep(3)
                continue

            print(f"📝 Strategy: {strategy}")
            await call_tool(session, "log_mission_event", {"message": f"🧠 STRATEGY: {strategy}"})

            assigned = []
            assigned_sectors = {
                d.get("target_sector")
            for did, d in drones.items()
            if isinstance(d, dict) and d.get("target_sector")
        }

            def nearest_unassigned(did):
                pos = drones.get(did, {}).get("coordinates", [0, 0, 0])
                best = None
                for sid, s in sectors.items():
                    if not isinstance(s, dict):
                        continue
                    if s.get("scanned") or s.get("hazard") == "no_fly" or sid in assigned_sectors:
                        continue
                    cx, cz = s.get("center", [0, 0])
                    dist = ((cx - pos[0]) ** 2 + (cz - pos[2]) ** 2) ** 0.5
                    if best is None or dist < best[1]:
                        best = (sid, dist, s.get("hazard", "clear"))
                return best

            for did, entry in assignments.items():
                if did not in idle_drone_ids:
                    continue
                sid = entry.get("sector") if isinstance(entry, dict) else entry
                reason = entry.get("reason", "") if isinstance(entry, dict) else ""

                bat_eval = round(drones.get(did, {}).get("battery", 0), 1) if did in drones else 0
                if sid == "__RECALL__" and bat_eval > 30 and recommendations.get(did):
                    top_cand = recommendations[did][0]
                    sid = top_cand["id"]
                    reason = f"Commander override: recall unnecessary; dispatch to {sid}."

                # If LLM proposed a duplicate, pick the next best candidate immediately.
                if sid and sid != "__RECALL__" and sid in assigned_sectors and recommendations.get(did):
                    alt = next((r for r in recommendations[did] if r["id"] not in assigned_sectors), None)
                    if alt:
                        sid = alt["id"]
                        reason = alt.get("reason", f"Alternate sector to avoid duplicate for {did}")
                # If still duplicate or no sid, fall back to nearest unassigned frontier
                if (not sid or (sid != "__RECALL__" and sid in assigned_sectors)):
                    alt = nearest_unassigned(did)
                    if alt:
                        sid = alt[0]
                        reason = reason or f"Fallback frontier ({alt[2]}) for {did}, ~{round(alt[1],1)}u"

                if not reason:
                    sec_info = sectors.get(sid, {})
                    sec_center = sec_info.get("center", [0, 0]) if isinstance(sec_info, dict) else [0, 0]
                    pos = drones.get(did, {}).get("coordinates", [0, 0, 0])
                    dist = round(((sec_center[0] - pos[0]) ** 2 + (sec_center[1] - pos[2]) ** 2) ** 0.5)
                    haz = sec_info.get("hazard", "unknown") if isinstance(sec_info, dict) else "unknown"
                    reason = f"{did} ({bat_eval}% bat) → {sid} ({haz}, ~{dist}u away)"

                if sid and (sid == "__RECALL__" or sid not in assigned_sectors):
                    print(f"📡 DISPATCH: {did} → {sid} | {reason}")
                    resp = await call_tool(session, "assign_target", {"drone_id": did, "sector_id": sid, "reason": reason})
                    if resp and isinstance(resp, dict) and resp.get("error"):
                        print(f"⚠️ ASSIGN ERROR for {did}: {resp['error']}")
                        continue
                    assigned.append(did)
                    if sid != "__RECALL__":
                        assigned_sectors.add(sid)
                    await call_tool(session, "log_mission_event", {"message": f"REASON: {did} → {sid}: {reason}"})
                elif sid and sid != "__RECALL__" and sid in assigned_sectors:
                    print(f"⚠️ SKIPPED: {did} → {sid} (sector already assigned this round)")

            # Auto-fill any still-idle drones with next-best unassigned candidates
            still_idle = [did for did in idle_drone_ids if did not in assigned]
            for did in still_idle:
                alt = None
                if recommendations.get(did):
                    alt = next((r for r in recommendations[did] if r["id"] not in assigned_sectors), None)
                if not alt:
                    best = nearest_unassigned(did)
                    if not best:
                        continue
                    sid, dist, haz = best
                    reason = f"Auto frontier for {did} ({haz}, ~{round(dist,1)}u)"
                else:
                    sid = alt["id"]
                    reason = alt.get("reason", f"Alternate for {did} to avoid idling")
                print(f"📡 DISPATCH (fallback): {did} → {sid} | {reason}")
                await call_tool(session, "assign_target", {"drone_id": did, "sector_id": sid, "reason": reason})
                assigned.append(did)
                assigned_sectors.add(sid)
                await call_tool(session, "log_mission_event", {"message": f"REASON: {did} → {sid}: {reason}"})
                # Small delay to prevent simultaneous assignments
                await asyncio.sleep(0.1)

            tracker.mark_assigned(assigned)
            tracker.commit(idle_drone_ids, hazards)

        except Exception as e:
            if "429" in str(e) or "Rate limit" in str(e):
                print("⏸️  Rate limit hit. Backing off 3s...")
                await asyncio.sleep(3)
            else:
                print(f"❌ Critical Error: {e}")
            await asyncio.sleep(2)


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
