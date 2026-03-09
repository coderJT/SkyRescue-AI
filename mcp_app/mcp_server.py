import os
import sys

# Ensure project root is in PYTHONPATH for cloud deployment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.cors import CORSMiddleware
from simulation.simulation_engine import SimulationEngine
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage

mcp = FastMCP("Rescue Drone Server", transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))

# Shared simulation state (singleton)
engine = SimulationEngine()

# Initialize LLM only if API key is present
api_key = os.environ.get("MISTRAL_API_KEY")
llm = None
if api_key:
    llm = ChatMistralAI(model="mistral-small-latest", mistral_api_key=api_key)


@mcp.tool()
async def get_high_level_decision(drone_id: str, battery: float, current_pos: list[float], other_drones: list[dict]) -> str:
    """
    Use the high-level Mistral LLM brain to decide the next move for a drone.
    This tool combines tactical recommendations with strategic swarm coordination.
    """
    import json
    if not llm:
        return json.dumps({"error": "MISTRAL_API_KEY not set on MCP server. LLM Brain unavailable."})

    # Fetch top tactical candidates from the SAME engine instance
    recommendations = engine.get_tactical_recommendations(drone_id, battery, current_pos, other_drones)

    if not recommendations:
        return json.dumps({"decision": "__RECALL__", "reasoning": "No scannable sectors available within safe reach."})

    # Build prompt context
    prompt = f"""
You are the high-level swarm commander for {drone_id} in a critical SAR mission.
Current Battery: {battery:.1f}%
Current Position [x, y, z]: {current_pos}
Base Station: [5, 0, 5]

SWARM CONTEXT (Teammates):
"""
    for d in other_drones:
        ts = d.get('target_sector') or 'None'
        prompt += f"- {d['id']}: Position {d['pos']} | State: {d['state']} | Target: {ts}\n"

    prompt += """
TACTICAL RECOMMENDATIONS (Sorted by Urgency & Proximity):
Your tactical specialist (the simulation engine) has curated these candidates:
"""
    for r in recommendations:
        prompt += f"- {r['id']}: {r['hazard'].upper()} | Time Remaining: {r['time_left_seconds']}s | Distance: {r['distance']} units\n"

    prompt += """
COMMANDERS GOAL AND STRICT RULES:
1. Review the recommendations provided above. 
2. Choose the BEST sector from the EXACT list of Candidate IDs provided. DO NOT invent sectors.
3. DEADLINE PRIORITY: Prioritize sectors with the LOWEST 'Time Remaining' (Fire: 60s, Smoke: 180s).
4. STRATEGIC SEPARATION: Do NOT pick a sector if another drone is already targeting it.
5. BATTERY AWARENESS: Drones drain battery by distance. Fire zones cost 3x battery per unit, smoke costs 1.5x. If a priority sector is too far for the current battery safely, pick a closer safe sector.

REQUIRED JSON FORMAT:
{
    "decision": "SectorID",
    "reasoning": "Explain your choice concisely regarding time limits, teammates, and battery."
}
"""

    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a brilliant SAR commander. You output valid JSON with no conversational text."),
            HumanMessage(content=prompt)
        ])
        
        content = response.content.strip()
        if content.startswith("```json"): content = content[7:-3]
        elif content.startswith("```"): content = content[3:-3]
            
        result = json.loads(content)
        # Final validation against scannable list
        if result.get("decision") not in [r["id"] for r in recommendations] and result.get("decision") != "__RECALL__":
             result["decision"] = recommendations[0]["id"]
             result["reasoning"] = "(Tactical Override: Invalid Sector) " + result.get("reasoning", "")
             
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"decision": recommendations[0]["id"], "reasoning": f"Tactical fallback: {str(e)}"})

@mcp.tool()
async def get_batch_decision(idle_drones: list[dict], active_drones: list[dict], unscanned_sectors: dict, hazard_map: dict) -> str:
    """
    Use the high-level Mistral LLM brain to coordinate batch assignments for multiple idle drones.
    """
    import json
    if not llm:
        return json.dumps({"error": "MISTRAL_API_KEY not set on server"})

    if not unscanned_sectors:
        return json.dumps({"assignments": {d["id"]: "__RECALL__" for d in idle_drones}, "reasoning": "No scannable sectors remain."})

    # Build multi-drone coordination prompt
    prompt = f"""
You are the GLOBAL SWARM COMMANDER for a critical SAR mission.
You must assign targets to {len(idle_drones)} IDLE drones simultaneously.

IDLE DRONES (Waiting for Orders):
"""
    for d in idle_drones:
        prompt += f"- {d['id']}: Battery {d['battery']:.1f}% | Position {d['pos']}\n"

    prompt += "\nACTIVE TEAMMATES (Already busy):\n"
    for d in active_drones:
        ts = d.get('target_sector') or 'None'
        prompt += f"- {d['id']}: Target: {ts}\n"

    prompt += """
TACTICAL CANDIDATES:
DANGER: Survivors in FIRE die in 60s, SMOKE in 180s, others in 600s.
"""
    for sid, s in unscanned_sectors.items():
        prompt += f"- {sid}: {s['hazard']} | Time Remaining: {s['time_left']}s | Distance (from closest drone): {s['distance']} units\n"

    prompt += """
COMMANDERS COORDINATION GOAL AND STRICT RULES:
1. Assign EXACTLY ONE unique sector to EACH IDLE drone.
2. USE ONLY the sector IDs provided in the TACTICAL CANDIDATES list. DO NOT hallucinate sectors.
3. GLOBAL OPTIMIZATION: Ensure the CLOSEST drone is assigned to the most critical (low time) fire areas.
4. CONFLICT AVOIDANCE: Do NOT assign a sector that is already being targeted by an ACTIVE teammate.
5. BATTERY AWARENESS: Estimate if a drone has enough battery. Fire zones use 3x battery per unit distance.
6. RECALL: If a drone has low battery (<25%) or no good targets remain, assign "__RECALL__".

REQUIRED JSON FORMAT:
{
    "assignments": {
        "drone_1": "S2_3",
        "drone_3": "__RECALL__"
    },
    "reasoning": "Drone_1 sent to critical fire front S2_3; drone_3 recalled due to 20% battery."
}
"""

    try:
        print(f"--- BATCH PROMPT for {len(idle_drones)} drones ---\n{prompt[:200]}...")
        response = await llm.ainvoke([
            SystemMessage(content="You are a swarm coordination AI. You output ONLY valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        import json
        content = response.content.strip()
        print(f"--- LLM RAW RESPONSE ---\n{content}")
        if content.startswith("```json"): content = content[7:-3]
        elif content.startswith("```"): content = content[3:-3]
        
        result = json.loads(content)
        # Final safety check: ensure every idle drone has an entry
        for d in idle_drones:
            if d['id'] not in result.get("assignments", {}):
                result.setdefault("assignments", {})[d['id']] = "__RECALL__"
                
        return json.dumps(result)
    except Exception as e:
        print(f"Error calling LLM for batch: {e}")
        # Emergency fallback: Assign first available sector to first drone, others recall
        fallback = {"assignments": {}, "reasoning": f"Emergency batch fallback: {str(e)}"}
        sids = list(unscanned_sectors.keys())
        for i, d in enumerate(idle_drones):
            fallback["assignments"][d['id']] = sids[i] if i < len(sids) else "__RECALL__"
        return json.dumps(fallback)


@mcp.tool()
def reset_mission() -> dict:
    """
    Reset the mission clock and survival timers. 
    Call this when starting a new simulation run.
    """
    return engine.reset_mission()


@mcp.tool()
def list_drones() -> list:
    """
    Discover all drones currently on the network.
    Returns a list of drone IDs available for tasking.
    """
    return engine.list_drones()


@mcp.tool()
def get_fleet_status() -> dict:
    """
    Get the full status of all drones in the fleet.
    Returns each drone's name, battery level, status, and coordinates.
    """
    return engine.get_fleet_status()


@mcp.tool()
def get_battery_status(drone_id: str) -> dict:
    """
    Get the battery status of a specific drone.
    """
    return engine.get_battery_status(drone_id)


@mcp.tool()
def get_status(drone_id: str) -> dict:
    """
    Get the current status of a specific drone.
    """
    return engine.get_drone_status(drone_id)


@mcp.tool()
def move_to(drone_id: str, x: float, y: float, z: float) -> dict:
    """
    Move a drone to the specified (x, y, z) coordinates.
    Battery drains proportional to distance. Fire/smoke zones cause extra drain.
    Movement into no-fly zones will be REJECTED.
    """
    return engine.move_to(drone_id, x, y, z)


@mcp.tool()
def thermal_scan(drone_id: str) -> dict:
    """
    Perform a thermal scan at the drone's current position.
    Detection radius is 5 units. Costs extra battery in fire zones.
    """
    return engine.thermal_scan(drone_id)


@mcp.tool()
def scan_sector(drone_id: str, sector_id: str) -> dict:
    """
    Move a drone to a sector's center and perform a thermal scan.
    Will be REJECTED if the sector is a no-fly zone.
    Fire/smoke sectors incur extra battery drain.
    Returns scan results, hazard type, and remaining battery.
    """
    return engine.scan_sector(drone_id, sector_id)


@mcp.tool()
def recall_for_charging(drone_id: str) -> dict:
    """
    Recall a drone to base for charging. Battery restored to 100%.
    """
    return engine.recall_for_charging(drone_id)


@mcp.tool()
def get_sectors() -> dict:
    """
    Get the full sector grid with hazard type and scan status.
    Hazard types: clear, fire, smoke, no_fly.
    """
    return engine.get_sectors()


@mcp.tool()
def get_unscanned_sectors() -> dict:
    """
    Get only sectors that have NOT been scanned (includes no-fly zones).
    """
    return engine.get_unscanned_sectors()


@mcp.tool()
def get_environment() -> dict:
    """
    Get the full environmental hazard data for the disaster zone.
    Returns: no-fly zones, fire zones, smoke sectors, wind conditions.
    Essential for mission planning — call this FIRST before planning routes.
    """
    return engine.get_environment()


@mcp.tool()
def get_hazard_map() -> dict:
    """
    Get a per-sector hazard map showing hazard type, center, and scan status.
    Useful for visualizing the disaster zone and planning safe routes.
    """
    return engine.get_hazard_map()


@mcp.tool()
def get_tactical_recommendations(drone_id: str, battery: float, current_pos: list[float], other_drones: list[dict]) -> list:
    """
    Get the top 5 tactical candidates for a drone based on hierarchical priority and proximity.
    'other_drones' should be a list of {id, pos, state, target_sector} to avoid duplicate targeting.
    """
    return engine.get_tactical_recommendations(drone_id, battery, current_pos, other_drones)


@mcp.tool()
def get_mission_summary() -> dict:
    """
    Get a full mission summary: coverage, survivors found, fleet status, logs.
    No-fly zones are excluded from coverage calculations.
    """
    return engine.get_mission_summary()
