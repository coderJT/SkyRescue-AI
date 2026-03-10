import os
import sys

# Ensure project root is in PYTHONPATH for cloud deployment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.cors import CORSMiddleware
from simulation.simulation_engine import SimulationEngine

mcp = FastMCP("Rescue Drone Server", transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))

# Shared simulation state (singleton)
engine = SimulationEngine()



@mcp.tool()
def log_mission_event(message: str) -> dict:
    """
    Log a custom mission event (e.g., agent reasoning) to the central mission log.
    Use this for transparency of the logic flow.
    """
    engine.log(message)
    return {"status": "success"}


@mcp.tool()
def get_world_state() -> dict:
    """
    Get the complete current state of the world: drones, sectors, survivors, and time.
    Use this for high-frequency polling to keep the simulation and agent in sync.
    """
    try:
        return engine.get_world_state()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@mcp.tool()
def update_drone_assignment(drone_id: str, sector_id: str, reason: str = None) -> dict:
    """
    Command a drone to target a specific sector.
    'reason' provides the LLM's strategic context for this assignment.
    """
    try:
        print(f"🤖 COMMAND RECEIVED: {drone_id} -> {sector_id} ({reason})")
        return engine.set_drone_target(drone_id, sector_id, reason)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@mcp.tool()
def update_drone_state(drone_id: str, battery: float, x: float, y: float, z: float, status: str) -> dict:
    """
    Update a drone's telemetry. The simulation should call this to sync the 
    physical movement occurring in the 3D renderer back to the server.
    """
    try:
        if drone_id not in engine.drones:
            return {"error": f"Drone {drone_id} not found"}
        drone = engine.drones[drone_id]
        drone.battery_remaining = battery
        drone.coordinates = (x, y, z)
        drone.status = status
        
        # Trigger dynamic discovery as the drone moves
        engine._update_discovery(x, z)
        
        return {"status": "success"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@mcp.tool()
def update_environment(fire_sectors: list = None, smoke_sectors: list = None, scanned_sectors: list = None) -> dict:
    """
    Sync the environment state from the simulation.
    Useful if the simulation generates dynamic hazards or scan results.
    """
    try:
        if fire_sectors is not None:
            engine.fire_sector_ids = set(fire_sectors)
        if smoke_sectors is not None:
            engine.smoke_sector_ids = set(smoke_sectors)
        if scanned_sectors is not None:
            for sid in scanned_sectors:
                if sid in engine.sectors:
                    if not engine.sectors[sid].get("scanned", False):
                        print(f"🔥 update_environment MARKING AS SCANNED: {sid}")
                    engine.sectors[sid]["scanned"] = True
                    engine.sectors[sid]["status"] = "scanned"
                    engine.sectors[sid]["assigned_to"] = None
        return {"status": "success"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}




@mcp.tool()
def reset_mission() -> dict:
    """
    Reset the mission clock and survival timers. 
    Call this when starting a new simulation run.
    """
    return engine.reset_mission()


@mcp.tool()
def start_mission() -> dict:
    """
    Transition the mission from 'waiting' to 'active'.
    Call this when the user clicks the start button in the UI.
    """
    return engine.start_mission()


@mcp.tool()
def list_drones() -> list:
    """
    Discover all drones currently on the network.
    Returns a list of drone IDs available for tasking.
    """
    return engine.list_drones()



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
    Detection radius is 14.5 units (covers a 20x20 sector).
    Costs extra battery in fire zones.
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
