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
import math
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from simulation.simulation_engine import SimulationEngine

mcp = FastMCP("Rescue Drone Server", transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))

# The simulation engine is the single source of truth for all world state.
# The MCP server is a thin passthrough that wraps engine methods as MCP tools.
engine = SimulationEngine()


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
    return engine.start_mission(survivor_count=survivor_count, active_drones=active_drones)


@mcp.tool()
def reset_mission() -> dict:
    """
    Reset the mission state for a fresh run.
    Clears all timers, survivors, and sector states.
    """
    return engine.reset_mission()


@mcp.tool()
def log_mission_event(message: str) -> dict:
    """
    Log a mission event (e.g., agent reasoning, strategy decisions) to the central mission log.
    These logs are displayed in the simulation UI for transparency.
    """
    engine.log(message)
    return {"status": "logged"}


@mcp.tool()
def toggle_pause(paused: bool = None) -> dict:
    """
    Toggle or set the pause state of the simulation.
    When paused, the mission clock, battery drain, and survivor deadlines are frozen.
    """
    return engine.toggle_pause(paused=paused)


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
    return engine.list_drones()


@mcp.tool()
def get_drone_status(drone_id: str) -> dict:
    """
    Get the full status of a specific drone: position, battery, status, current target.
    """
    return engine.get_drone_status(drone_id)


@mcp.tool()
def get_battery_status(drone_id: str) -> dict:
    """
    Get the battery level of a specific drone.
    Returns battery percentage and estimated remaining flight time.
    """
    return engine.get_battery_status(drone_id)


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
    return engine.move_to(drone_id, x, y, z)


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
        result = engine.set_drone_target(drone_id, sector_id, reason)
        return result
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
        result = engine.scan_sector(drone_id, sector_id)
        return result
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def thermal_scan(drone_id: str) -> dict:
    """
    Perform a thermal scan at the drone's current position.
    Detects heat signatures (survivors) within the scan radius.
    Returns list of detected survivor positions.
    """
    try:
        result = engine.thermal_scan(drone_id)
        return result
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def recall_for_charging(drone_id: str) -> dict:
    """
    Recall a drone to base for emergency recharging.
    Battery will be restored to 100% upon arrival.
    Use this when battery drops below safe levels.
    """
    return engine.recall_for_charging(drone_id)


@mcp.tool()
def report_telemetry(drone_id: str, battery: float, x: float, y: float, z: float, status: str, clear_target: bool = False) -> dict:
    """
    Called by the drone/frontend to report its current telemetry to the engine.
    This triggers the drone's sensors to discover new hazards in its vicinity.
    If clear_target is true, it indicates the drone has reached base and finished its mission.
    """
    try:
        # Sync physical state into the engine
        # Also triggers the drone's onboard sensors to discover nearby hazards (decentralized sensing).
        # If clear_target is true, it indicates the drone has reached base and finished its mission.
        engine.update_drone_telemetry(drone_id, battery, x, y, z, status, clear_target)

        old_discovered_fires = {sid for sid, s in engine.sectors.items() if s["discovered"] and s["hazard"] == "fire"}
        
        # Decentralized Discovery: drone's onboard sensors scan the area
        drone_obj = engine.drones.get(drone_id)
        if hasattr(drone_obj, 'scan_surrounding'):
            discovered = drone_obj.scan_surrounding(engine.sectors)
            
            # Log immediate discoveries
            new_discovered_fires = {sid for sid, s in engine.sectors.items() if s["discovered"] and s["hazard"] == "fire"}
            just_discovered = new_discovered_fires - old_discovered_fires
            if just_discovered:
                for sid in just_discovered:
                    engine.log(f"🚨 ALERT! {drone_id} discovered a NEW FIRE at {sid}!")

        return {"status": "ok"}
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
        world = engine.get_world_state()

        # Add ground-truth hazard map for frontend fire/smoke visualization
        # (Fire is visible to everyone — this is visual-only, not used for AI decisions)
        ground_truth_hazards = {}
        for sid, sdata in engine.sectors.items():
            th = sdata.get("true_hazard", "clear")
            if th != "clear":
                ground_truth_hazards[sid] = th
        world["ground_truth_hazards"] = ground_truth_hazards

        return world
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@mcp.tool()
def get_environment() -> dict:
    """
    Get environmental hazard data for the disaster zone.
    Returns: identified fire zones, smoke sectors, no-fly zones, wind conditions.
    Essential for mission planning — call this FIRST before planning routes.
    """
    return engine.get_environment()


@mcp.tool()
def get_sectors() -> dict:
    """
    Get the full sector grid with hazard type and scan status for each sector.
    Hazard types: clear, fire, smoke, no_fly.
    """
    return engine.get_sectors()


@mcp.tool()
def get_unscanned_sectors() -> dict:
    """
    Get only sectors that have NOT been scanned yet (excludes no-fly zones).
    Use this to identify remaining search areas.
    """
    return engine.get_unscanned_sectors()


@mcp.tool()
def get_hazard_map() -> dict:
    """
    Get a per-sector hazard map with hazard type, center coordinates, and scan status.
    Useful for visualizing the disaster zone and planning safe routes.
    """
    return engine.get_hazard_map()


@mcp.tool()
def get_mission_summary() -> dict:
    """
    Get a full mission summary: coverage percentage, survivors found, fleet status, mission logs.
    No-fly zones are excluded from coverage calculations.
    """
    return engine.get_mission_summary()
