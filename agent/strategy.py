"""Local tactical logic for the orchestrator."""

import math
import time
from typing import Dict, List, Tuple


def compute_sector_recommendations(drone_id, drones, sectors, elapsed_seconds):
    """
    Compute the top 3 sector recommendations for a drone.
    Two-phase strategy:
      DISCOVERY PHASE: Spread drones across the map to discover fire/smoke via onboard sensors.
      PRIORITY PHASE:  Once hazards are discovered, prioritize fire > smoke > frontier.
    Battery feasibility: excludes sectors where the drone cannot travel there,
    scan, AND return to base with a safety margin.
    """
    from config.settings import settings

    BASE_X, BASE_Z = settings.base_x, settings.base_z
    DRAIN_PER_UNIT = settings.drain_per_unit
    SCAN_COST = settings.scan_cost
    SAFETY_MARGIN = settings.safety_margin

    drone = drones.get(drone_id, {})
    if not isinstance(drone, dict):
        return []

    target = drone.get("target_sector")
    if target and target != "__RECALL__":
        return []

    coords = drone.get("coordinates", [0, 0, 0])
    cx, cz = coords[0], coords[2]
    battery = drone.get("battery", 0)

    claimed = {
        d.get("target_sector")
        for did, d in drones.items()
        if did != drone_id and isinstance(d, dict) and d.get("target_sector")
    }

    discovered_fire = {
        sid: s
        for sid, s in sectors.items()
        if isinstance(s, dict) and s.get("discovered") and not s.get("scanned") and s.get("hazard") == "fire"
    }
    discovered_smoke = {
        sid: s
        for sid, s in sectors.items()
        if isinstance(s, dict) and s.get("discovered") and not s.get("scanned") and s.get("hazard") == "smoke"
    }
    has_fire = bool(discovered_fire)
    has_smoke = bool(discovered_smoke)
    candidates = []
    SCAN_PENALTY = 30  # dist equivalent of a scan
    CHARGE_PENALTY = 100  # dist equivalent of a charge cycle

    def get_eta(d_data, tgt_center):
        d_pos = d_data.get("coordinates", [0, 0, 0])
        d_cx, d_cz = d_pos[0], d_pos[2]
        d_status = d_data.get("status", "offline").lower()
        d_target = d_data.get("target_sector")
        d_bat = d_data.get("battery", 0)

        if d_status in ["idle", "waiting_orders"] or not d_target:
            return math.hypot(tgt_center[0] - d_cx, tgt_center[1] - d_cz)

        if d_status == "moving":
            if d_target == "__RECALL__":
                return (
                    math.hypot(BASE_X - d_cx, BASE_Z - d_cz)
                    + CHARGE_PENALTY
                    + math.hypot(tgt_center[0] - BASE_X, tgt_center[1] - BASE_Z)
                )

            curr_tgt_center = sectors.get(d_target, {}).get("center", [BASE_X, BASE_Z])
            dist_to_curr = math.hypot(curr_tgt_center[0] - d_cx, curr_tgt_center[1] - d_cz)
            dist_curr_to_new = math.hypot(tgt_center[0] - curr_tgt_center[0], tgt_center[1] - curr_tgt_center[1])
            eta = dist_to_curr + SCAN_PENALTY + dist_curr_to_new

            if d_bat < (dist_to_curr + dist_curr_to_new) * DRAIN_PER_UNIT * 1.5 + SCAN_COST:
                eta += CHARGE_PENALTY
            return eta

        if d_status == "scanning":
            dist_to_new = math.hypot(tgt_center[0] - d_cx, tgt_center[1] - d_cz)
            eta = (SCAN_PENALTY / 2) + dist_to_new
            if d_bat < dist_to_new * DRAIN_PER_UNIT * 1.5:
                eta += CHARGE_PENALTY
            return eta

        if d_status == "charging":
            return (CHARGE_PENALTY / 2) + math.hypot(tgt_center[0] - BASE_X, tgt_center[1] - BASE_Z)

        return float("inf")

    for sid, sector in sectors.items():
        if not isinstance(sector, dict):
            continue
        if sector.get("scanned") or sector.get("hazard") == "no_fly" or sid in claimed:
            continue

        center = sector.get("center", [0, 0])
        dist = math.hypot(center[0] - cx, center[1] - cz)
        rt_distance = dist * 2
        penalty = 0
        hazard = sector.get("hazard", "clear")
        if has_fire and hazard != "fire":
            continue
        if not has_fire and has_smoke and hazard not in ("fire", "smoke"):
            continue

        if hazard == "fire":
            penalty -= 50  # strong pull to fire
        elif hazard == "smoke":
            penalty += 10

        fleet_eta = min(get_eta(d, center) for d in drones.values() if isinstance(d, dict))
        my_eta = get_eta(drone, center)
        fleet_comparison_string = "fastest_to_reach" if my_eta <= fleet_eta else "fallback"

        total_cost = rt_distance * DRAIN_PER_UNIT + SCAN_COST
        battery_after_return = battery - total_cost - SAFETY_MARGIN
        if battery_after_return < 0:
            continue

        if hazard == "fire":
            score = dist + penalty
            reason = f"fire priority, {fleet_comparison_string}"
        elif hazard == "smoke":
            score = dist + 60 + penalty
            reason = f"smoke (secondary), {fleet_comparison_string}"
        else:
            score = dist + 220 + penalty
            reason = f"frontier exploration, {fleet_comparison_string}"

        candidates.append(
            {
                "id": sid,
                "score": score,
                "reason": reason,
                "distance": round(dist, 1),
                "hazard": hazard,
                "battery_cost": round(total_cost, 1),
                "battery_after": battery_after_return,
            }
        )

    candidates.sort(key=lambda x: x["score"])
    return candidates[:3]


class AssignmentTracker:
    """Debounce assignments so the orchestrator doesn't double-dispatch."""

    def __init__(self):
        self.pending = {}
        self.last_idle_set = set()
        self.last_hazard_set = set()
        self.last_idle_time = 0

    def filter_idle(self, idle_ids):
        now = time.time()
        self.pending = {did: ts for did, ts in self.pending.items() if now - ts < 4}
        return [did for did in idle_ids if did not in self.pending]

    def mark_assigned(self, drone_ids):
        now = time.time()
        for did in drone_ids:
            self.pending[did] = now

    def should_invoke_llm(self, current_idle, current_hazards):
        now = time.time()
        if set(current_hazards) != self.last_hazard_set:
            return True
        new_idle = set(current_idle) - self.last_idle_set
        if new_idle and (len(current_idle) >= 2 or now - self.last_idle_time > 10):
            return True
        if current_idle and now - self.last_idle_time > 10:
            return True
        return False

    def commit(self, idle_ids, hazards):
        self.last_idle_set = set(idle_ids)
        self.last_hazard_set = set(hazards)
        self.last_idle_time = time.time()


def summarize_hazards(sectors):
    """Return discovered fire and smoke sector IDs (excluding scanned)."""
    fire = [
        sid
        for sid, s in sectors.items()
        if isinstance(s, dict) and s.get("discovered") and s.get("hazard") == "fire" and not s.get("scanned")
    ]
    smoke = [
        sid
        for sid, s in sectors.items()
        if isinstance(s, dict) and s.get("discovered") and s.get("hazard") == "smoke" and not s.get("scanned")
    ]
    return fire, smoke


def select_idle_drones(drones, sectors, urgent_needs):
    """Pick drones eligible for reassignment."""
    available = []
    for did, d in drones.items():
        if not isinstance(d, dict):
            continue
        status = d.get("status", "").lower()
        target = d.get("target_sector")

        if status in ["active", "idle", "waiting_orders"]:
            if not target or target == "__RECALL__":
                available.append(did)
            elif urgent_needs > 0:
                t_sector = sectors.get(target, {})
                if isinstance(t_sector, dict) and t_sector.get("hazard", "unknown") not in ["fire", "smoke"]:
                    available.append(did)
        elif status == "moving" and target == "__RECALL__":
            available.append(did)
    return available


def print_swarm_status(drones, idle_ids):
    """Compact console dump used before LLM call."""
    print("\n--- SWARM STATUS ---")
    for did, d in drones.items():
        if not isinstance(d, dict):
            continue
        target = d.get("target_sector", "None")
        bat = round(d.get("battery", 0), 1)
        pos = d.get("coordinates", [0, 0, 0])
        status = d.get("status", "?").upper()
        state = "IDLE" if did in idle_ids else status
        print(f"  {did}: {state} | Bat: {bat}% | Pos({round(pos[0])},{round(pos[2])}) | Target: {target}")
    print("--------------------\n")
