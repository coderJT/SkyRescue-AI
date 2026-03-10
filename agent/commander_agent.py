import asyncio
import os
import json
import sys
from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

# Initialize LLM
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("❌ ERROR: GROQ_API_KEY environment variable not set.")
    sys.exit(1)

llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=GROQ_API_KEY)

def get_dist(p1, p2):
    """Euclidean distance for (x, z) coordinates."""
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5

async def call_tool(session, tool_name, args=None):
    """Helper to call MCP tools and parse the JSON string response."""
    try:
        result = await session.call_tool(tool_name, args or {})
        if not result or not result.content:
            return None
            
        for content in result.content:
            if hasattr(content, 'text'):
                text = content.text.strip()
                try:
                    return json.loads(text)
                except:
                    return text
            elif isinstance(content, dict) and 'text' in content:
                # Some implementations might return dicts
                try:
                    return json.loads(content['text'])
                except:
                    return content['text']
    except Exception as e:
        print(f"Tool call error ({tool_name}): {e}")
    return None

class AssignmentTracker:
    def __init__(self):
        self.pending = {} # drone_id -> timestamp
        self.last_idle_set = set()
        self.last_hazard_set = set()

    def filter_idle(self, idle_ids):
        import time
        now = time.time()
        # Clean up old pending assignments (give drones 4s to react - covers SSE latency)
        self.pending = {did: ts for did, ts in self.pending.items() if now - ts < 4}
        return [did for did in idle_ids if did not in self.pending]

    def mark_assigned(self, drone_ids):
        import time
        now = time.time()
        for did in drone_ids:
            self.pending[did] = now

    def has_significant_change(self, current_idle, current_hazards):
        # Change if new drones became idle OR new hazards discovered
        if set(current_idle) != self.last_idle_set:
            self.last_idle_set = set(current_idle)
            return True
        if set(current_hazards) != self.last_hazard_set:
            self.last_hazard_set = set(current_hazards)
            return True
        return False

async def run_commander(session):
    print("\n" + "="*50)
    print("🚀 COMMANDER AGENT: Autonomous Swarm Brain Active")
    print("Connecting via SSE to Shared Mission State...")
    print("="*50 + "\n")
    
    tracker = AssignmentTracker()
    consecutive_idle = 0
    
    last_llm_time = 0
    while True:
        try:
            # 1. Get current world state from MCP Server (Source of Truth)
            world = await call_tool(session, "get_world_state")
            if not world:
                print("⚠️  Warning: Failed to fetch world state. Retrying...")
                await asyncio.sleep(2)
                continue

            # Check if simulation is waiting for the user to click START
            status = world.get("mission_status")
            if status == "waiting":
                print(f"⏳ Status: {status} (Waiting for UI 'START SIMULATION'...)")
                await asyncio.sleep(2)
                continue

            if world.get("mission_complete"):
                print(f"🏁 Mission Complete! Status: {status}")
                await asyncio.sleep(10)
                continue

            drones = world.get("drones", {})
            sectors = world.get("sectors", {})
            
            # 2. Identify Idle Drones & Priority Sectors
            raw_active = [did for did, d in drones.items() if d['status'].lower() in ['active', 'idle', 'waiting_orders']]
            available = [did for did in raw_active if not drones[did].get('target_sector')]
            idle_drone_ids = tracker.filter_idle(available)
            
            unscanned = {sid: s for sid, s in sectors.items() if not s['scanned'] and s['hazard'] != 'no_fly'}
            
            if not idle_drone_ids or not unscanned:
                consecutive_idle += 1
                if consecutive_idle % 5 == 0:
                     print(f"Status Tracking: {len(idle_drone_ids)} drones truly idle. {len(drones)-len(idle_drone_ids)} busy or syncing...")
                     if idle_drone_ids:
                         print(f"DEBUG: Tracing Idle: {idle_drone_ids}")
                await asyncio.sleep(2)
                continue
            hazards = [sid for sid, s in sectors.items() if s["discovered"] and s["hazard"] != "clear"]
            
            # If no hazards discovered yet, and we are just scouting, we can be more efficient
            # But we still use the LLM if the set of idle drones changed.
            if not tracker.has_significant_change(idle_drone_ids, hazards):
                await asyncio.sleep(2)
                continue

            # --- [HARDENING] 3s LLM THROTTLE ---
            import time
            now = time.time()
            time_since_last = now - last_llm_time
            if time_since_last < 3:
                # Still sleep a bit to avoid CPU spike, but don't print logic unless it's a long wait
                await asyncio.sleep(1)
                continue

            consecutive_idle = 0
            
            # --- [DIAGNOSTIC] Drone Status Summary ---
            print("\n--- SWARM STATUS CHECK ---")
            for did, d in drones.items():
                target = d.get('target_sector', 'None')
                pending = " [PENDING]" if did in tracker.pending else ""
                print(f"  {did}: {d['status'].upper()} | Target: {target}{pending}")
            print("---------------------------\n")

            print(f"🧠 Reasoning: Coordinating {len(idle_drone_ids)} idle drones...")
            last_llm_time = now

            # 3. Analyze Environment (Tactical Fog-of-War)
            # ONLY provide discovered sectors as tactical candidates
            unscanned = {sid: s for sid, s in sectors.items() if not s["scanned"] and s["discovered"] and s["hazard"] != "no_fly" and not s.get("assigned_to")}
            
            is_exploring = False
            if not unscanned:
                # No hazards discovered! Fallback to EXPLORATION FRONTIER
                # Find undiscovered scannable sectors closest to the base or average drone position
                is_exploring = True
                undiscovered = {sid: s for sid, s in sectors.items() if not s["scanned"] and not s["discovered"] and s["hazard"] != "no_fly"}
                
                if undiscovered:
                    # Pick 10 closest undiscovered sectors to current swarm centroid
                    swarm_x = sum([d['pos'][0] for d in idle_drone_telemetry.values()]) / len(idle_drone_telemetry)
                    swarm_z = sum([d['pos'][1] for d in idle_drone_telemetry.values()]) / len(idle_drone_telemetry)
                    
                    sorted_frontier = sorted(undiscovered.items(), key=lambda x: get_dist((swarm_x, swarm_z), x[1]['center']))
                    unscanned = dict(sorted_frontier[:12]) # Provide a small buffer of frontier targets
            
            # 4. Strategic Planning with LLM
            # Gather all necessary context for the global swarm commander
            mission_stats = {
                "coverage_pct": world.get("coverage_pct", 0),
                "found_survivors": world.get("found_survivors", 0),
                "total_survivors": world.get("total_survivors", 0),
                "elapsed_time": world.get("elapsed_seconds", 0)
            }
            wind = world.get("wind", {})
            
            idle_drone_telemetry = {}
            for did in idle_drone_ids:
                d = drones[did]
                d_pos = (d['coordinates'][0], d['coordinates'][2])
                idle_drone_telemetry[did] = {
                    "pos": (round(d_pos[0], 1), round(d_pos[1], 1)),
                    "battery": round(d['battery'], 1)
                }

            active_drones_context = []
            for did, d in drones.items():
                if d['status'].lower() in ['active', 'tasked'] and did not in idle_drone_ids:
                    active_drones_context.append({
                        "id": did,
                        "target_sector": d.get("target_sector", "None"),
                        "pos": (round(d['coordinates'][0], 1), round(d['coordinates'][2], 1))
                    })

            # Build tactical candidates list for the prompt
            unscanned_context = {}
            for sid, s in unscanned.items():
                # Find closest distance from any idle drone for context
                min_dist = min([get_dist(idle_drone_telemetry[did]["pos"], s['center']) for did in idle_drone_ids]) if idle_drone_ids else 999
                unscanned_context[sid] = {
                    "hazard": s['hazard'],
                    "time_left": s.get("time_left", 600), 
                    "distance": round(min_dist, 1)
                }

            if not unscanned_context:
                print("Mission Logic: No scannable targets remain. Recalling.")
                for did in idle_drone_ids:
                    await call_tool(session, "update_drone_assignment", {"drone_id": did, "sector_id": "__RECALL__"})
                tracker.mark_assigned(idle_drone_ids)
                await asyncio.sleep(5)
                continue

            # Compressed Fleet Context
            fleet_ctx = "FLEET STATUS:\n"
            for did, d in idle_drone_telemetry.items():
                fleet_ctx += f"- {did}:Bat{d['battery']}%,Pos{d['pos']}\n"
            for d in active_drones_context:
                fleet_ctx += f"- {d['id']}:BUSY(Target:{d['target_sector']}),Pos{d['pos']}\n"

            # Compressed Tactical Candidates
            candidates_ctx = f"TACTICAL CANDIDATES ({'EXPLORATION' if is_exploring else 'SCAN'} MODE):\n"
            for sid, s in unscanned_context.items():
                h = s['hazard'].upper() if not is_exploring else "UNKN"
                candidates_ctx += f"- {sid}:{h},{s['distance']}u,{s['time_left']}s\n"

            prompt = f"""
Coordination for {len(idle_drone_ids)} IDLE drones.
Stats: Time {mission_stats['elapsed_time']}s | Coverage {mission_stats['coverage_pct']}% | Surv {mission_stats['found_survivors']}/{mission_stats['total_survivors']}
Wind: {wind.get('description')}

DRAIN: Base 0.05%/u | FIRE 3x (60s life) | SMOKE 1.5x (180s life) | Wind up to 1.3x.

{fleet_ctx}
{candidates_ctx}

RULES:
1. Assign 1 unique sector from CANDIDATES to each IDLE drone.
2. Prioritize FIRE near drones. Check battery.
3. CONFLICT AVOIDANCE: No duplicate targets.
4. RECALL: Bat < 25% or no targets.

OUTPUT JSON:
{{
  "global_strategy": "2-3 sentences max on swarm logic and wind.",
  "assignments": {{
    "drone_id": {{ "sector": "SID", "reason": "2 concise sentences max: [OBS]... [RISK/DECISION]..." }}
  }}
}}
"""

            print(f"\n--- [AGENT] ENHANCED LLM COORDINATION PROMPT ---\n{prompt}\n-----------------------------------------------\n")

            response = await llm.ainvoke([
                SystemMessage(content="You are a swarm coordination AI. You output ONLY valid JSON."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content.strip()
            def robust_json_parse(text):
                """Attempts to extract and parse JSON even if surrounded by text or malformed."""
                import re
                import json
                
                # 1. Try standard extraction from code blocks
                json_str = text
                if "```json" in text:
                    json_str = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    json_str = text.split("```")[1].split("```")[0].strip()
                
                # 2. Try to find the first '{' and last '}'
                try:
                    start = json_str.find('{')
                    end = json_str.rfind('}')
                    if start != -1 and end != -1:
                        json_str = json_str[start:end+1]
                except:
                    pass

                # 3. Clean up common LLM issues (trailing commas, unescaped quotes in reasoning)
                # Note: We do NOT replace newlines with spaces here, as JSON allows newlines in keys/values
                # if they are properly escaped, or between structural elements.
                
                # ESCAPE LITERAL TABS (illegal in JSON strings)
                json_str = json_str.replace('\t', '\\t')
                
                try:
                    # strict=False allows literal newlines in strings
                    return json.loads(json_str, strict=False)
                except Exception as first_error:
                    # 4. Emergency Backup: Try to fix common "unescaped quote" in reasoning
                    # Look for things like "[OBSERVATION]: ... " ... " [RISK ASSESSMENT]"
                    try:
                        # This is a very targeted fix for the reasoning field
                        relaxed = re.sub(r'(?<=: ")(.*?)(?=",)', lambda m: m.group(1).replace('"', "'"), json_str, flags=re.DOTALL)
                        return json.loads(relaxed, strict=False)
                    except:
                        # Log the failure for debugging
                        with open("/tmp/last_malformed_response.txt", "w") as f:
                            f.write(text)
                        raise first_error

            # Robust parsing
            try:
                data = robust_json_parse(content)
                assignments_data = data.get("assignments", {})
                global_strategy = data.get("global_strategy", "Coordinated.")
                
                print(f"📝 {global_strategy}")
                await call_tool(session, "log_mission_event", {"message": f"🧠 STRATEGY: {global_strategy}"})

                assigned_this_round = []
                for did, entry in assignments_data.items():
                    if did in idle_drone_ids:
                        if isinstance(entry, dict):
                            sid = entry.get("sector")
                            reason = entry.get("reason", "Assigned by Commander.")
                        else:
                            sid = entry
                            reason = "Assigned by Commander."

                        # Safety check: sector exists or is RECALL
                        target = sid if (sid in sectors or sid == "__RECALL__") else "__RECALL__"
                        
                        print(f"📡 DISPATCH: {did} -> {target} | Reason: {reason}")
                        await call_tool(session, "update_drone_assignment", {
                            "drone_id": did, 
                            "sector_id": target,
                            "reason": reason
                        })
                        assigned_this_round.append(did)
                
                tracker.mark_assigned(assigned_this_round)

            except Exception as e:
                print(f"❌ Coordination Error: {e}")

        except Exception as e:
            if "429" in str(e) or "Rate limit" in str(e):
                print("⚠️ Rate limit exceeded. Backing off for 15 seconds...")
                await asyncio.sleep(15)
            else:
                print(f"❌ Critical Agent Error: {e}")
            
        await asyncio.sleep(5) 

async def main():
    # Connect to the ALREADY RUNNING SSE server from start.py
    url = "http://localhost:8000/sse"
    print(f"Connecting to MCP Central Server at {url}...")
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await run_commander(session)
    except Exception as e:
        print(f"❌ Could not connect to MCP server: {e}")
        print("Make sure 'python start.py' is running first!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCommander Agent shutting down.")
