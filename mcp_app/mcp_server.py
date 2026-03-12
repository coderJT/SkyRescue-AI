"""
mcp_server.py — Drone Control API

MCP Server that exposes drone functions as standardized tools for the Command Agent.
This server acts as a radio interface between the command center and the drone fleet,
delegating all physical operations to the Simulation Engine (source of truth).

Tools exposed:
  - Fleet Discovery: list_drones()
  - Drone Queries:   get_drone_status(), get_battery_status()
  - Drone Commands:  move_to(), assign_target(), scan_sector(), thermal_scan(), recall_for_charging()
  - Environment:     get_environment(), get_sectors(), get_unscanned_sectors(), get_hazard_map()
  - Mission:         get_world_state(), start_mission(), reset_mission(), get_mission_summary()
  - Logging:         log_mission_event()
"""

import os
import sys
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from simulation.service import SimulationService
from config import settings as cfg

mcp = FastMCP("Rescue Drone Server", transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))

# The MCP server is a thin adapter; all domain logic lives in the simulation service.
service = SimulationService()


def _world_with_truth():
    """Attach visualization-only ground truth to the world snapshot."""
    world = service.get_world_state()
    world["ground_truth_hazards"] = service.ground_truth_hazards()
    world["settings"] = cfg.to_dict()
    return world


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MISSION LIFECYCLE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def start_mission(survivor_count: int = None, active_drones: int = None) -> dict:
    """
    Initialize and start a search-and-rescue mission.
    Generates hazards (fire, smoke) and places survivors in the disaster zone.
    Call this once when the simulation begins.
    """
    return service.start_mission(survivor_count=survivor_count, active_drones=active_drones)


@mcp.tool()
def reset_mission() -> dict:
    """
    Reset the mission state for a fresh run.
    Clears all timers, survivors, and sector states.
    """
    return service.reset_mission()


@mcp.tool()
def log_mission_event(message: str) -> dict:
    """
    Log a mission event (e.g., agent reasoning, strategy decisions) to the central mission log.
    These logs are displayed in the simulation UI for transparency.
    """
    return service.log_event(message)


@mcp.tool()
def toggle_pause(paused: bool = None) -> dict:
    """
    Toggle or set the pause state of the simulation.
    When paused, the mission clock, battery drain, and survivor deadlines are frozen.
    """
    return service.toggle_pause(paused=paused)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FLEET DISCOVERY & DRONE QUERIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def list_drones() -> list:
    """
    Discover all drones currently active on the network.
    The agent must NOT hard-code drone IDs — use this tool to discover the fleet dynamically.
    Returns a list of drone IDs available for tasking.
    """
    return service.list_drones()


@mcp.tool()
def get_drone_status(drone_id: str) -> dict:
    """
    Get the full status of a specific drone: position, battery, status, current target.
    """
    return service.get_drone_status(drone_id)


@mcp.tool()
def get_battery_status(drone_id: str) -> dict:
    """
    Get the battery level of a specific drone.
    Returns battery percentage and estimated remaining flight time.
    """
    return service.get_battery_status(drone_id)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DRONE COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def move_to(drone_id: str, x: float, y: float, z: float) -> dict:
    """
    Command a drone to fly to the specified (x, y, z) coordinates.
    Battery drains proportionally to distance traveled.
    Fire and smoke zones cause increased battery drain.
    Movement into designated no-fly zones will be REJECTED.
    """
    return service.move_to(drone_id, x, y, z)


@mcp.tool()
def assign_target(drone_id: str, sector_id: str, reason: str = None) -> dict:
    """
    Assign a drone to navigate to and scan a specific sector.
    The 'reason' field provides the agent's strategic reasoning for this assignment
    (chain-of-thought transparency).
    Use sector_id='__RECALL__' to recall a drone to base.
    """
    try:
        print(f"🤖 COMMAND: {drone_id} → {sector_id} | Reason: {reason}")
        return service.assign_target(drone_id, sector_id, reason)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def scan_sector(drone_id: str, sector_id: str) -> dict:
    """
    Command a drone to move to a sector's center and perform a full thermal scan.
    Detects survivors and reveals the sector's true hazard status.
    Updates the sector as 'scanned' in the world state.
    """
    try:
        return service.scan_sector(drone_id, sector_id)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def thermal_scan(drone_id: str, sector: str = None) -> dict:
    """
    Perform a thermal scan at the drone's current position (or a specified sector).
    Detects heat signatures (survivors) within the scan radius.
    Pass 'sector' (e.g. 'S5_3') to scan a specific sector directly — used for
    fly-over scans where the backend position may not yet reflect the drone's
    real-world location.
    Returns list of detected survivor positions.
    """
    try:
        result = engine.thermal_scan(drone_id, sector_id=sector)
        return result
        return service.thermal_scan(drone_id)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def recall_for_charging(drone_id: str) -> dict:
    """
    Recall a drone to base for emergency recharging.
    Battery will be restored to 100% upon arrival.
    Use this when battery drops below safe levels.
    """
    return service.recall_for_charging(drone_id)


@mcp.tool()
def report_telemetry(drone_id: str, battery: float, x: float, y: float, z: float, status: str, clear_target: bool = False) -> dict:
    """
    Called by the drone/frontend to report its current telemetry to the engine.
    This triggers the drone's sensors to discover new hazards in its vicinity.
    If clear_target is true, it indicates the drone has reached base and finished its mission.
    """
    try:
        return service.report_telemetry(drone_id, battery, x, y, z, status, clear_target)
    except Exception as e:
        return {"error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENVIRONMENT & SITUATIONAL AWARENESS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def get_world_state() -> dict:
    """
    Get the complete current state of the mission.
    Includes: mission status, drone fleet, sector grid, discovered survivors,
    wind conditions, and ground-truth hazard map for visualization.
    This is the primary tool for situational awareness.
    """
    try:
        return _world_with_truth()
    except Exception as e:
        print(f"get_world_state error: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_environment() -> dict:
    """
    Get environmental hazard data for the disaster zone.
    Returns: identified fire zones, smoke sectors, no-fly zones, wind conditions.
    Essential for mission planning — call this FIRST before planning routes.
    """
    return service.get_environment()


@mcp.tool()
def get_sectors() -> dict:
    """
    Get the full sector grid with hazard type and scan status for each sector.
    Hazard types: clear, fire, smoke, no_fly.
    """
    return service.get_sectors()


@mcp.tool()
def get_unscanned_sectors() -> dict:
    """
    Get only sectors that have NOT been scanned yet (excludes no-fly zones).
    Use this to identify remaining search areas.
    """
    return service.get_unscanned_sectors()


@mcp.tool()
def get_hazard_map() -> dict:
    """
    Get a per-sector hazard map with hazard type, center coordinates, and scan status.
    Useful for visualizing the disaster zone and planning safe routes.
    """
    return service.get_hazard_map()


@mcp.tool()
def get_mission_summary() -> dict:
    """
    Get a full mission summary: coverage percentage, survivors found, fleet status, mission logs.
    No-fly zones are excluded from coverage calculations.
    """
    return service.get_mission_summary()


@mcp.tool()
def get_settings() -> dict:
    """Return current simulation/orchestrator tunable settings."""
    return cfg.to_dict()


@mcp.tool()
def update_settings(changes: dict) -> dict:
    """
    Update simulation/orchestrator constants (e.g., drain_per_unit, scan_cost, fire_multiplier).
    A mission reset is recommended after structural changes.
    """
    new_cfg = service.update_settings(changes)
    return {"status": "updated", "settings": new_cfg}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HTTP SETTINGS ENDPOINTS (for UI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def http_get_settings(request):
    return JSONResponse(cfg.to_dict())


async def http_update_settings(request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    new_cfg = service.update_settings(payload if isinstance(payload, dict) else {})
    return JSONResponse({"status": "updated", "settings": new_cfg})


def create_app():
    app = mcp.sse_app()
    app.add_route("/settings", http_get_settings, methods=["GET"])
    app.add_route("/settings", http_update_settings, methods=["POST"])
    return app
