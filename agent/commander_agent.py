import asyncio
import os
import json
import sys
from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage

# Initialize LLM
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    print("❌ ERROR: MISTRAL_API_KEY environment variable not set.")
    sys.exit(1)

llm = ChatMistralAI(model="mistral-small-latest", mistral_api_key=MISTRAL_API_KEY)

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

async def run_commander(session):
    print("\n" + "="*50)
    print("🚀 COMMANDER AGENT: Autonomous Swarm Brain Active")
    print("Connecting via SSE to Shared Mission State...")
    print("="*50 + "\n")
    
    consecutive_idle = 0
    
    while True:
        try:
            # 1. Get current world state from MCP Server (Source of Truth)
            world = await call_tool(session, "get_world_state")
            if not world:
                print("⚠️ Waiting for simulation data...")
                await asyncio.sleep(2)
                continue
                
            if world.get("mission_complete"):
                print("✅ MISSION SUCCESS: All sectors cleared. Commander standing down.")
                break

            # 2. Triage Drones
            drones = world["drones"]
            # Filter for drones that are available for tasking
            idle_drone_ids = []
            
            # --- DEBUG: Dump all drone states ---
            print("\n--- 🔍 SWARM TELEMETRY DUMP ---")
            for did, d in drones.items():
                status = d.get("status", "").lower()
                target = d.get("target_sector")
                is_idle = status in ["active", "idle", "waiting_orders"]
                has_no_target = not target or target in ["None", None]
                will_be_idle = is_idle and has_no_target
                print(f"{did} | Status: {status:15} | Target: {str(target):10} | IsIdle: {will_be_idle}")
                
                if will_be_idle:
                    idle_drone_ids.append(did)
            print("-------------------------------\n")
            
            if not idle_drone_ids:
                consecutive_idle += 1
                if consecutive_idle % 5 == 0:
                    print(f"Mission Status: {len(drones)} drones monitored, checking for reassignments...")
                await asyncio.sleep(2)
                continue
            
            consecutive_idle = 0
            print(f"🧠 Reasoning: Found {len(idle_drone_ids)} idle drones waiting for tasking.")

            # 3. Analyze Environment
            sectors = world["sectors"]
            # Find prioritize candidates
            unscanned = {sid: s for sid, s in sectors.items() if not s["scanned"] and s["hazard"] != "no_fly" and not s.get("assigned_to")}
            
            # 4. Strategic Planning with LLM
            # Sort unscanned sectors by priority (Fire > Smoke > Clear)
            priority_map = {"fire": 0, "smoke": 1, "clear": 2}
            sorted_candidates = sorted(
                unscanned.items(), 
                key=lambda x: (priority_map.get(x[1]["hazard"], 3), x[0])
            )
            
            # Formulate detailed candidate list for LLM context
            candidate_details = {}
            idle_drone_telemetry = {}

            try:
                for did in idle_drone_ids:
                    d = drones[did]
                    # Get drone pos from tuple (x, y, z) -> we want (x, z)
                    d_pos = (d['coordinates'][0], d['coordinates'][2])
                    idle_drone_telemetry[did] = {"pos": (round(d_pos[0], 1), round(d_pos[1], 1))}

                    # Find top 5 closest scannable sectors for THIS drone
                    d_candidates = []
                    for sid, s in unscanned.items():
                        s_pos = s['center']
                        dist = get_dist(d_pos, s_pos)
                        d_candidates.append((sid, s, dist))
                    
                    # Sort candidates by (hazard_priority, distance)
                    d_candidates.sort(key=lambda x: (priority_map.get(x[1]["hazard"], 3), x[2]))
                    
                    # Add top 5 for this drone to the global candidate set
                    for sid, s, dist in d_candidates[:5]:
                        if sid not in candidate_details:
                            candidate_details[sid] = {
                                "hazard": s['hazard'].upper(),
                                "discovered": s.get("discovered", False),
                                "center": (round(s['center'][0], 1), round(s['center'][1], 1)),
                                "approx_dist": round(dist, 1)
                            }
            except Exception as e:
                print(f"❌ Error extracting telemetry/candidates: {e}")
                raise e # re-raise to catch in outer loop
            
            if not candidate_details:
                print("Mission Logic: No scannable targets remain. Recalling idle fleet.")
                for did in idle_drone_ids:
                    await call_tool(session, "update_drone_assignment", {"drone_id": did, "sector_id": "__RECALL__"})
                await asyncio.sleep(5)
                continue

            # Build a compact prompt for the LLM brain
            prompt = f"""
MISSION: Enhanced Search & Rescue (Fog of War Active)
Drones have a 3-tile observation radius. Hazards (Fire/Smoke) are HIDDEN until a drone flies nearby.

STATE:
- Idle Drones (Current [X,Z]): {idle_drone_telemetry}
- Candidates (Hazard/Discovered/[X,Z]): {candidate_details}

OBJECTIVE:
Assign exactly one unique sector to EACH idle drone.

STRATEGY: 
1. SCOUTING: If few/no FIRE sectors are discovered, prioritize scanning 'discovered': False sectors to find the fire.
2. TRIAGE: If FIRE is discovered, prioritize those sectors IMMEDIATELY (survivors die in 60s).
3. EFFICIENCY: Assign drones to the CLOSEST candidates to save battery.
4. COORDINATION: Use the X,Z coordinates to ensure drones don't cross paths unnecessarily.

STRICT JSON FORMAT:
{{"assignments": {{"drone_1": "S2_3", "drone_2": "S4_5"}} , "reasoning": "Dispatching drone_1 to scout new area, drone_2 to handle local fire."}}
"""
            
            response = await llm.ainvoke([
                SystemMessage(content="You are the Autonomous SAR Commander. Output ONLY valid JSON."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content.strip()
            # Clean markdown if present
            if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content: content = content.split("```")[1].split("```")[0].strip()
            
            try:
                data = json.loads(content)
                assignments = data.get("assignments", {})
                reasoning = data.get("reasoning", "Coordinated dispatch.")
                
                # with open("/tmp/commander_debug.log", "a") as f:
                #     f.write(f"[{len(idle_drone_ids)} IDLE] {idle_drone_ids} -> Assigns: {assignments}\n")
                
                print(f"📝 Plan: {reasoning}")
                
                # 5. Dispatch commands back to MCP Server
                for did, sid in assignments.items():
                    if did in idle_drone_ids:
                        # Check if sector exists or is recall
                        target = sid if (sid in sectors or sid == "__RECALL__") else "__RECALL__"
                        await call_tool(session, "update_drone_assignment", {"drone_id": did, "sector_id": target})
                        print(f"📡 DISPATCH: {did} -> {target}")
                        
            except Exception as e:
                with open("/tmp/commander_debug.log", "a") as f:
                    f.write(f"❌ JSON ERROR: {e} | Raw: {content}\n")
                print(f"❌ Failed to coordinate: {e} | Raw: {content}")

        except Exception as e:
            if "429" in str(e):
                print("⚠️ Rate limit exceeded. Backing off for 10 seconds...")
                await asyncio.sleep(10)
            else:
                print(f"❌ Critical Agent Error: {e}")
            
        await asyncio.sleep(5)  # Cooldown between strategic cycles

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
