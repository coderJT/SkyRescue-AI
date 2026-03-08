import os
from mcp.server.fastmcp import FastMCP
from simulation.simulation_engine import SimulationEngine
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage

mcp = FastMCP("Rescue Drone Server")

# Shared simulation state (singleton)
engine = SimulationEngine()

# Initialize LLM only if API key is present
api_key = os.environ.get("MISTRAL_API_KEY")
llm = None
if api_key:
    llm = ChatMistralAI(model="mistral-large-latest", mistral_api_key=api_key)


@mcp.tool()
def get_high_level_decision(drone_id: str, battery: float, current_pos: list[float], other_drones: list[dict]) -> dict:
    """
    Use the high-level Mistral LLM brain to decide the next move for a drone.
    This tool combines tactical recommendations with strategic swarm coordination.
    """
    if not llm:
        return {"error": "MISTRAL_API_KEY not set on MCP server. LLM Brain unavailable."}

    # Fetch top tactical candidates from the SAME engine instance
    recommendations = engine.get_tactical_recommendations(drone_id, battery, current_pos, other_drones)

    if not recommendations:
        return {"decision": "__RECALL__", "reasoning": "No scannable sectors available within safe reach."}

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
COMMANDERS GOAL:
1. Review the recommendations. 
2. Choose the BEST sector from the list.
3. DEADLINE PRIORITY: Prioritize sectors with the LOWEST 'Time Remaining' (Fire: 60s, Smoke: 180s).
4. STRATEGIC SEPARATION: Do NOT pick a sector if another drone is already targeting it.

REQUIRED JSON FORMAT:
{
    "decision": "SectorID",
    "reasoning": "Explain your choice (e.g., 'Choosing S3_2: critical fire area with only 15s remaining')."
}
"""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a high-level rescue commander AI. You output ONLY valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        import json
        content = response.content.strip()
        if content.startswith("```json"): content = content[7:-3]
        elif content.startswith("```"): content = content[3:-3]
            
        result = json.loads(content)
        # Final validation against scannable list
        if result.get("decision") not in [r["id"] for r in recommendations] and result.get("decision") != "__RECALL__":
             result["decision"] = recommendations[0]["id"]
             result["reasoning"] = "(Tactical Override) " + result.get("reasoning", "")
             
        return result
    except Exception as e:
        return {"decision": recommendations[0]["id"], "reasoning": f"Tactical fallback: {str(e)}"}


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
