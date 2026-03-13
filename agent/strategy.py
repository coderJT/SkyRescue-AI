"""Local tactical logic for the orchestrator."""

import math
import random
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

    # Get sectors already claimed by other drones
    claimed = {
        d.get("target_sector")
        for did, d in drones.items()
        if did != drone_id and isinstance(d, dict) and d.get("target_sector")
    }
    
    # EARLY GAME: Add virtual claims to prevent initial clustering
    # During first 30 seconds, virtually claim sectors near other idle drones
    # to encourage spatial distribution
    if elapsed_seconds < 30:
        for other_did, other_d in drones.items():
            if other_did == drone_id or not isinstance(other_d, dict):
                continue
            other_status = other_d.get("status", "").lower()
            other_target = other_d.get("target_sector")
            # If other drone is idle and has no target, consider its position
            if other_status in ["idle", "waiting_orders"] and not other_target:
                other_pos = other_d.get("coordinates", [0, 0, 0])
                other_cx, other_cz = other_pos[0], other_pos[2]
                # Virtually claim the sector closest to this other drone
                closest_sector = None
                closest_dist = float('inf')
                for sid, sector in sectors.items():
                    if not isinstance(sector, dict):
                        continue
                    if sector.get("scanned") or sector.get("hazard") == "no_fly":
                        continue
                    center = sector.get("center", [0, 0])
                    dist = math.hypot(center[0] - other_cx, center[1] - other_cz)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_sector = sid
                if closest_sector and closest_sector not in claimed:
                    # Only virtually claim if this other drone is closer to that sector
                    my_dist = math.hypot(
                        sectors[closest_sector]["center"][0] - cx,
                        sectors[closest_sector]["center"][1] - cz
                    ) if closest_sector in sectors else float('inf')
                    if closest_dist < my_dist:
                        claimed.add(closest_sector)

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
        # Don't restrict to only fire sectors when fire is discovered
        # Instead, we'll adjust penalties to balance fire response and exploration
        # Keep smoke logic - if smoke but no fire, prioritize fire/smoke sectors
        if not has_fire and has_smoke and hazard not in ("fire", "smoke"):
            continue

        if hazard == "fire":
            # Check how many drones are already targeting or near this fire sector
            drones_targeting_this_fire = 0
            for other_did, other_d in drones.items():
                if other_did == drone_id or not isinstance(other_d, dict):
                    continue
                other_target = other_d.get("target_sector")
                if other_target == sid:
                    drones_targeting_this_fire += 1
                else:
                    # Check if drone is already at or near this sector
                    other_pos = other_d.get("coordinates", [0, 0, 0])
                    other_dist_to_fire = math.hypot(center[0] - other_pos[0], center[1] - other_pos[2])
                    if other_dist_to_fire < 50:  # Within 50 units
                        drones_targeting_this_fire += 0.5  # Partial credit for nearby drones
            
            # Adjust penalty based on existing drone coverage
            # Base penalty for fire (still attractive but not overwhelmingly so)
            base_fire_penalty = -30
            
            # Reduce attractiveness of distant fires - drones far from fire should consider local exploration
            distance_factor = 1.0
            if dist > 200:  # Fire is more than 200 units away
                # Reduce attractiveness for distant fires
                distance_factor = 0.5
            elif dist > 400:  # Fire is very far
                distance_factor = 0.2
            
            # Add penalty for each drone already targeting this fire (reduces attractiveness)
            coverage_penalty = drones_targeting_this_fire * 15 * distance_factor
            penalty += (base_fire_penalty * distance_factor) + coverage_penalty
            
        elif hazard == "smoke":
            penalty += 10

        fleet_eta = min(get_eta(d, center) for d in drones.values() if isinstance(d, dict))
        my_eta = get_eta(drone, center)
        fleet_comparison_string = "fastest_to_reach" if my_eta <= fleet_eta else "fallback"

        # Add exploration bonus for sectors far from known fires
        exploration_bonus = 0
        min_fire_distance = float('inf')
        if has_fire and hazard != "fire":
            # This is a non-fire sector, give bonus based on distance from nearest fire
            for fire_sid, fire_sector in discovered_fire.items():
                fire_center = fire_sector.get("center", [0, 0])
                fire_dist = math.hypot(center[0] - fire_center[0], center[1] - fire_center[1])
                min_fire_distance = min(min_fire_distance, fire_dist)
            
            # Give exploration bonus for sectors far from fires
            # Bonus increases with distance from nearest fire
            if min_fire_distance > 100:  # More than 100 units from nearest fire
                exploration_bonus = -min_fire_distance * 0.2  # Negative bonus (better score)
        
        total_cost = rt_distance * DRAIN_PER_UNIT + SCAN_COST
        battery_after_return = battery - total_cost - SAFETY_MARGIN
        if battery_after_return < 0:
            continue
        
        # Apply exploration bonus to penalty
        penalty += exploration_bonus
        
        # EARLY GAME: Add directional preference to spread drones
        # Assign each drone a preferred quadrant based on their index
        if elapsed_seconds < 60:
            # Extract drone index from drone_id (e.g., "drone_3" -> 3)
            drone_idx = 0
            try:
                drone_idx = int(drone_id.split('_')[-1]) if '_' in drone_id else 0
            except (ValueError, IndexError):
                drone_idx = 0
            
            # Calculate angle from base to sector
            dx = center[0] - BASE_X
            dz = center[1] - BASE_Z
            sector_angle = math.atan2(dz, dx)  # -pi to pi
            
            # Assign preferred angle based on drone index
            # Drone 1: 0°, Drone 2: 90°, Drone 3: 180°, Drone 4: 270°, etc.
            preferred_angle = (drone_idx - 1) * (math.pi / 2) % (2 * math.pi)
            if preferred_angle > math.pi:
                preferred_angle -= 2 * math.pi
            
            # Calculate angular difference
            angle_diff = abs(sector_angle - preferred_angle)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            
            # Add penalty for sectors not in preferred direction (0 to pi penalty)
            # This is a soft preference - drones can still go elsewhere if needed
            directional_penalty = (angle_diff / math.pi) * 50  # Max 50 point penalty
            penalty += directional_penalty

        if hazard == "fire":
            score = dist + penalty
            # Update reason to include drone coverage info
            drones_on_fire = sum(1 for other_did, other_d in drones.items() 
                               if other_did != drone_id and isinstance(other_d, dict) 
                               and other_d.get("target_sector") == sid)
            reason = f"fire (coverage: {drones_on_fire} drones), {fleet_comparison_string}"
        elif hazard == "smoke":
            score = dist + 60 + penalty
            reason = f"smoke (secondary), {fleet_comparison_string}"
        else:
            # Reduced frontier penalty to encourage exploration when fires are covered
            # Base frontier penalty is now dynamic based on fire coverage
            frontier_base_penalty = 100  # Reduced from 220
            
            # Reduce further if we have good fire coverage
            total_fire_drones = 0
            for other_did, other_d in drones.items():
                if other_did == drone_id or not isinstance(other_d, dict):
                    continue
                other_target = other_d.get("target_sector")
                if other_target and other_target in discovered_fire:
                    total_fire_drones += 1
            
            # If we have enough drones on fires, encourage more exploration
            if total_fire_drones >= 2:  # At least 2 drones on fires
                frontier_base_penalty = 50  # Even more encouragement to explore
            
            score = dist + frontier_base_penalty + penalty
            # Include exploration info in reason
            fire_dist_str = f"{round(min_fire_distance, 1)}u" if has_fire and min_fire_distance < float('inf') else "N/A"
            reason = f"frontier exploration (fire_dist: {fire_dist_str}), {fleet_comparison_string}"

        # Add small random factor to break ties and prevent packing
        import random
        random_factor = random.uniform(-0.1, 0.1) * dist  # Small random factor based on distance
        
        candidates.append(
            {
                "id": sid,
                "score": score + random_factor,
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
        self.pending = {did: ts for did, ts in self.pending.items() if now - ts < 1}
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
        # More responsive: invoke LLM if there are new idle drones (even just 1)
        # or if it's been more than 2 seconds (instead of 10)
        if new_idle and (len(current_idle) >= 1 or now - self.last_idle_time > 2):
            return True
        if current_idle and now - self.last_idle_time > 2:
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
