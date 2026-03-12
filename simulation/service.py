"""Thin service layer that keeps the simulation engine behind a single boundary.

The MCP server imports only this file so the simulator stays decoupled from
transport concerns, while the orchestrator continues to talk solely to MCP.
"""

from typing import Dict, Any, Optional

from simulation.simulation_engine import SimulationEngine


class SimulationService:
    """Facade over the simulation engine to enforce separation of concerns."""

    def __init__(self, engine: Optional[SimulationEngine] = None):
        self.engine = engine or SimulationEngine()

    # ── Mission lifecycle ──────────────────────────────────────────────────
    def start_mission(self, survivor_count: int = None, active_drones: int = None) -> dict:
        return self.engine.start_mission(survivor_count=survivor_count, active_drones=active_drones)

    def reset_mission(self) -> dict:
        return self.engine.reset_mission()

    def toggle_pause(self, paused: bool = None) -> dict:
        return self.engine.toggle_pause(paused=paused)

    def log_event(self, message: str) -> dict:
        self.engine.log(message)
        return {"status": "logged"}

    # ── Discovery & telemetry ──────────────────────────────────────────────
    def list_drones(self):
        return self.engine.list_drones()

    def get_drone_status(self, drone_id: str) -> dict:
        return self.engine.get_drone_status(drone_id)

    def get_battery_status(self, drone_id: str) -> dict:
        return self.engine.get_battery_status(drone_id)

    def report_telemetry(
        self,
        drone_id: str,
        battery: float,
        x: float,
        y: float,
        z: float,
        status: str,
        clear_target: bool = False,
    ) -> dict:
        """Ingest telemetry and let the drone's onboard sensors reveal hazards."""
        self.engine.update_drone_telemetry(drone_id, battery, x, y, z, status, clear_target)

        # Decentralized discovery: use the drone's local sensors to reveal hazards nearby.
        old_discovered_fires = {sid for sid, s in self.engine.sectors.items() if s["discovered"] and s["hazard"] == "fire"}

        drone_obj = self.engine.drones.get(drone_id)
        if hasattr(drone_obj, "scan_surrounding"):
            drone_obj.scan_surrounding(self.engine.sectors)
            new_discovered_fires = {sid for sid, s in self.engine.sectors.items() if s["discovered"] and s["hazard"] == "fire"}
            just_discovered = new_discovered_fires - old_discovered_fires
            for sid in just_discovered:
                self.engine.log(f"🚨 ALERT! {drone_id} discovered a NEW FIRE at {sid}!")

        return {"status": "ok"}

    # ── Commands ───────────────────────────────────────────────────────────
    def assign_target(self, drone_id: str, sector_id: str, reason: str = None) -> dict:
        return self.engine.set_drone_target(drone_id, sector_id, reason)

    def move_to(self, drone_id: str, x: float, y: float, z: float) -> dict:
        return self.engine.move_to(drone_id, x, y, z)

    def scan_sector(self, drone_id: str, sector_id: str) -> dict:
        return self.engine.scan_sector(drone_id, sector_id)

    def thermal_scan(self, drone_id: str) -> dict:
        return self.engine.thermal_scan(drone_id)

    def recall_for_charging(self, drone_id: str) -> dict:
        return self.engine.recall_for_charging(drone_id)

    # ── Situational awareness ──────────────────────────────────────────────
    def get_world_state(self) -> dict:
        return self.engine.get_world_state()

    def get_environment(self) -> dict:
        return self.engine.get_environment()

    def get_sectors(self) -> dict:
        return self.engine.get_sectors()

    def get_unscanned_sectors(self) -> dict:
        return self.engine.get_unscanned_sectors()

    def get_hazard_map(self) -> dict:
        return self.engine.get_hazard_map()

    def get_mission_summary(self) -> dict:
        return self.engine.get_mission_summary()

    def ground_truth_hazards(self) -> Dict[str, Any]:
        """Expose only the visualization-friendly ground-truth hazards."""
        return {
            sid: sdata["true_hazard"]
            for sid, sdata in self.engine.sectors.items()
            if sdata.get("true_hazard") and sdata.get("true_hazard") != "clear"
        }
