"""
MCP Server - Rescue Drone Server (Forest Wildfire Environment)
Exposes drone operations and environmental tools as standardized MCP tools.
Uses a singleton SimulationEngine for persistent state across tool calls.
"""
from mcp.server.fastmcp import FastMCP
from simulation.simulation_engine import SimulationEngine

mcp = FastMCP("Rescue Drone Server")

# Shared simulation state (singleton)
engine = SimulationEngine()


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
def get_mission_summary() -> dict:
    """
    Get a full mission summary: coverage, survivors found, fleet status, logs.
    No-fly zones are excluded from coverage calculations.
    """
    return engine.get_mission_summary()
