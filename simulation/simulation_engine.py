"""
Simulation Engine - Forest Wildfire Search & Rescue
Implements a singleton pattern so all MCP tool calls share the same state.
Manages a sector grid, no-fly zones, fire zones, smoke, and wind.
"""
import math
from drone.Drone import Drone


class SimulationEngine:
    """
    Singleton simulation engine that manages drones, survivors, sectors,
    and environmental hazards (no-fly zones, fire, smoke, wind).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        self._initialized = True
        import time
        self.start_time = time.time()

        # --- Drones (start at base camp in bottom-left) ---
        self.drones = {
            "drone_1": Drone("drone_1", 100, "active", (5, 5, 5)),
            "drone_2": Drone("drone_2", 100, "active", (5, 5, 5)),
            "drone_3": Drone("drone_3", 100, "active", (5, 5, 5)),
            "drone_4": Drone("drone_4", 100, "active", (5, 5, 5)),
            "drone_5": Drone("drone_5", 100, "active", (5, 5, 5)),
        }

        # Survivors: (x, y, z, survival_limit_seconds)
        self.survivors = []
        raw_survivors = [
            (25, 35, 0), (50, 50, 0), (65, 55, 0), 
            (15, 75, 0), (80, 65, 0), (35, 85, 0), (72, 12, 0)
        ]
        for x, y, z in raw_survivors:
            sid = self._get_sector_at(x, y)
            limit = 600 # default 10 mins
            if sid in self.fire_sector_ids: limit = 60
            elif sid in self.smoke_sector_ids: limit = 180
            self.survivors.append({"pos": (x, y, z), "limit": limit, "expired": False})

        # --- Discovered survivors (found during scans) ---
        self.discovered_survivors = []

        # --- Environment: No-Fly Zones (impassable obstacles) ---
        # Each zone: {"name", "sectors": [list of sector IDs], "reason"}
        self.no_fly_zones = [
            {
                "name": "Rocky Cliffs",
                "sectors": ["S1_1", "S2_1"],
                "reason": "Steep cliff face with unpredictable updrafts — too dangerous for drones",
            },
            {
                "name": "Dense Forest Canopy",
                "sectors": ["S0_4", "S1_4"],
                "reason": "Thick tree canopy blocks GPS and thermal sensors",
            },
        ]
        self.no_fly_sector_ids = set()
        for zone in self.no_fly_zones:
            self.no_fly_sector_ids.update(zone["sectors"])

        # --- Environment: Fire Zones (hazardous, high battery drain) ---
        self.fire_zones = [
            {
                "name": "Northern Fire Front",
                "sectors": ["S3_2", "S4_2"],
                "intensity": "high",
                "battery_multiplier": 3.0,
            },
            {
                "name": "Eastern Blaze",
                "sectors": ["S2_3", "S3_3"],
                "intensity": "medium",
                "battery_multiplier": 2.5,
            },
        ]
        self.fire_sector_ids = set()
        self.fire_multipliers = {}
        for zone in self.fire_zones:
            for sid in zone["sectors"]:
                self.fire_sector_ids.add(sid)
                self.fire_multipliers[sid] = zone["battery_multiplier"]

        # --- Environment: Smoke Zones (adjacent to fire, moderate penalty) ---
        self.smoke_sector_ids = set()
        self.smoke_multiplier = 1.5
        # Auto-calculate smoke zones: any sector adjacent to a fire sector
        for sid in list(self.fire_sector_ids):
            row, col = int(sid[1]), int(sid[3])
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < 5 and 0 <= nc < 5:
                    adj_id = f"S{nr}_{nc}"
                    if adj_id not in self.fire_sector_ids and adj_id not in self.no_fly_sector_ids:
                        self.smoke_sector_ids.add(adj_id)

        # --- Environment: Wind ---
        self.wind = {
            "direction": "NE",  # Wind blowing north-east
            "speed_kmh": 35,
            "effect": "Drones flying against the wind (SW direction) use 1.3× battery",
            "battery_multiplier_against": 1.3,
        }

        # --- Sector Grid ---
        self.grid_size = 100
        self.sector_cols = 5
        self.sector_rows = 5
        self.sector_width = self.grid_size / self.sector_cols
        self.sector_height = self.grid_size / self.sector_rows
        self.sectors = {}
        for row in range(self.sector_rows):
            for col in range(self.sector_cols):
                sector_id = f"S{row}_{col}"
                cx = col * self.sector_width + self.sector_width / 2
                cy = row * self.sector_height + self.sector_height / 2

                # Determine hazard type
                if sector_id in self.no_fly_sector_ids:
                    hazard = "no_fly"
                elif sector_id in self.fire_sector_ids:
                    hazard = "fire"
                elif sector_id in self.smoke_sector_ids:
                    hazard = "smoke"
                else:
                    hazard = "clear"

                self.sectors[sector_id] = {
                    "id": sector_id,
                    "row": row,
                    "col": col,
                    "center": (cx, cy),
                    "hazard": hazard,
                    "scanned": False,
                    "assigned_to": None,
                    "survivors_found": [],
                }

        # Mark no-fly zones as "scanned" (they can never be scanned)
        for sid in self.no_fly_sector_ids:
            self.sectors[sid]["scanned"] = True

        # --- Mission Log ---
        self.mission_log = []

    def log(self, message):
        self.mission_log.append(message)

    def reset_mission(self):
        """Reset mission timer, survivors, and sector states for a new run."""
        import time
        self.start_time = time.time()
        self.discovered_survivors = []
        self.mission_log = []
        
        # Reset survivors
        for s in self.survivors:
            s["expired"] = False
            
        # Reset sectors (except no-fly zones)
        for sid, sector in self.sectors.items():
            if sector["hazard"] != "no_fly":
                sector["scanned"] = False
            sector["assigned_to"] = None
            sector["survivors_found"] = []
                
        self.log("Mission Reset: Grid cleared and timers restarted.")
        return {"status": "success", "message": "Mission state fully reset."}

    def _get_sector_at(self, x, y):
        """Return the sector ID for a given coordinate."""
        col = min(int(x / self.sector_width), self.sector_cols - 1)
        row = min(int(y / self.sector_height), self.sector_rows - 1)
        return f"S{row}_{col}"

    def _battery_multiplier_at(self, x, y):
        """Return the battery drain multiplier at a given position."""
        sid = self._get_sector_at(x, y)
        if sid in self.fire_multipliers:
            return self.fire_multipliers[sid]
        if sid in self.smoke_sector_ids:
            return self.smoke_multiplier
        return 1.0

    # ─── Drone Operations ───

    def list_drones(self):
        return list(self.drones.keys())

    def get_fleet_status(self):
        return {did: d.to_dict() for did, d in self.drones.items()}

    def get_drone_status(self, drone_id):
        if drone_id not in self.drones:
            return {"error": f"Drone {drone_id} not found"}
        return self.drones[drone_id].to_dict()

    def move_to(self, drone_id, x, y, z):
        if drone_id not in self.drones:
            return {"error": f"Drone {drone_id} not found"}
        drone = self.drones[drone_id]
        if drone.status != "active":
            return {"error": f"Drone {drone_id} is {drone.status}, cannot move"}

        # Check if destination is in a no-fly zone
        dest_sector = self._get_sector_at(x, y)
        if dest_sector in self.no_fly_sector_ids:
            self.log(f"BLOCKED: {drone_id} cannot enter no-fly zone {dest_sector} at ({x},{y})")
            return {"error": f"Cannot fly to ({x},{y}) — sector {dest_sector} is a no-fly zone"}

        # Calculate environmental drain multiplier at destination
        multiplier = self._battery_multiplier_at(x, y)

        # Apply extra drain for hazardous zones
        old_coords = drone.coordinates
        drone.move_to(x, y, z)

        if multiplier > 1.0:
            # Extra drain on top of movement drain already applied
            old_x, old_y, old_z = old_coords
            distance = math.sqrt((x - old_x)**2 + (y - old_y)**2 + (z - old_z)**2)
            extra_drain = distance * 0.3 * (multiplier - 1)
            drone.drain_battery(extra_drain)

        hazard_label = ""
        if dest_sector in self.fire_sector_ids:
            hazard_label = " [🔥 FIRE ZONE]"
        elif dest_sector in self.smoke_sector_ids:
            hazard_label = " [💨 SMOKE]"

        self.log(f"{drone_id} moved to ({x}, {y}, {z}){hazard_label}, battery: {drone.battery_remaining:.1f}%")
        return drone.to_dict()

    def thermal_scan(self, drone_id):
        if drone_id not in self.drones:
            return {"error": f"Drone {drone_id} not found"}
        drone = self.drones[drone_id]
        if drone.status != "active":
            return {"error": f"Drone {drone_id} is {drone.status}, cannot scan"}

        # Extra scan cost in fire zones
        multiplier = self._battery_multiplier_at(drone.coordinates[0], drone.coordinates[1])
        
        # Check survival limits
        import time
        elapsed = time.time() - self.start_time
        active_survivors = [s["pos"] for s in self.survivors if not s["expired"] and elapsed < s["limit"]]
        
        detected = drone.thermal_scan(active_survivors)
        if multiplier > 1.0:
            drone.drain_battery(0.5 * (multiplier - 1))  # extra scan drain

        for s in detected:
            if s not in self.discovered_survivors:
                self.discovered_survivors.append(s)
                self.log(f"🔥 NEW SURVIVOR FOUND by {drone_id} at {s}!")
        return {
            "drone": drone_id,
            "position": list(drone.coordinates),
            "detected_count": len(detected),
            "detected": [list(s) for s in detected],
            "battery_after": round(drone.battery_remaining, 1),
        }

    def get_battery_status(self, drone_id):
        if drone_id not in self.drones:
            return {"error": f"Drone {drone_id} not found"}
        return {
            "drone": drone_id,
            "battery": round(self.drones[drone_id].battery_remaining, 1),
            "status": self.drones[drone_id].status,
        }

    def recall_for_charging(self, drone_id):
        if drone_id not in self.drones:
            return {"error": f"Drone {drone_id} not found"}
        drone = self.drones[drone_id]
        for s in self.sectors.values():
            if s["assigned_to"] == drone_id:
                s["assigned_to"] = None
        drone.move_to(*drone.base_coordinates)
        drone.set_status("charging")
        drone.charge()
        self.log(f"{drone_id} recalled for charging. Battery restored to 100%.")
        return drone.to_dict()

    # ─── Environment ───

    def get_environment(self):
        """Return full environmental hazard data."""
        return {
            "no_fly_zones": self.no_fly_zones,
            "fire_zones": self.fire_zones,
            "smoke_sectors": sorted(list(self.smoke_sector_ids)),
            "wind": self.wind,
            "grid_size": self.grid_size,
            "sector_layout": "5x5 grid, 20x20 units each",
        }

    def get_hazard_map(self):
        """Return a per-sector hazard map."""
        hazard_map = {}
        for sid, sector in self.sectors.items():
            hazard_map[sid] = {
                "center": list(sector["center"]),
                "hazard": sector["hazard"],
                "scanned": sector["scanned"],
            }
        return hazard_map

    # ─── Sector Operations ───

    def get_sectors(self):
        return self.sectors

    def get_unscanned_sectors(self):
        return {sid: s for sid, s in self.sectors.items() if not s["scanned"]}

    def get_scannable_sectors(self):
        """Sectors that are unscanned AND not no-fly zones."""
        return {
            sid: s for sid, s in self.sectors.items()
            if not s["scanned"] and sid not in self.no_fly_sector_ids
        }

    def scan_sector(self, drone_id, sector_id):
        if drone_id not in self.drones:
            return {"error": f"Drone {drone_id} not found"}
        if sector_id not in self.sectors:
            return {"error": f"Sector {sector_id} not found"}
        if sector_id in self.no_fly_sector_ids:
            return {"error": f"Sector {sector_id} is a NO-FLY ZONE — cannot scan"}

        drone = self.drones[drone_id]
        sector = self.sectors[sector_id]

        if drone.status != "active":
            return {"error": f"Drone {drone_id} is {drone.status}, cannot scan sector"}

        cx, cy = sector["center"]
        move_result = self.move_to(drone_id, cx, cy, 5)
        if "error" in move_result:
            return move_result

        scan_result = self.thermal_scan(drone_id)
        if "error" in scan_result:
            return scan_result

        sector["scanned"] = True
        sector["assigned_to"] = drone_id
        sector["survivors_found"] = scan_result["detected"]

        hazard = sector["hazard"]
        hazard_label = f" [{hazard.upper()}]" if hazard != "clear" else ""
        self.log(f"{drone_id} scanned sector {sector_id}{hazard_label} at ({cx},{cy}). Found {scan_result['detected_count']} survivors.")

        return {
            "drone": drone_id,
            "sector": sector_id,
            "sector_center": [cx, cy],
            "hazard": hazard,
            "survivors_found": scan_result["detected"],
            "battery_after": scan_result["battery_after"],
        }

    def get_tactical_recommendations(self, drone_id, battery, current_pos, other_drones):
        """
        Calculate the top 5 tactical candidates based on:
        1. Priority (Fire > Smoke > Clear)
        2. Proximity (Distance to drone)
        3. Swarm Coordination (Avoid sectors already targeted by teammates)
        """
        cx, cy, cz = current_pos
        candidates = []
        
        # Identify sectors already claimed by teammates
        claimed_sectors = {d.get('target_sector') for d in other_drones if d.get('target_sector')}
        
        import time
        elapsed = time.time() - self.start_time

        for sid, sector in self.sectors.items():
            if sector["scanned"] or sector["hazard"] == "no_fly" or sid in claimed_sectors:
                continue
                
            scx, scy = sector["center"]
            dist = math.sqrt((scx - cx)**2 + (scy - cy)**2)
            
            # Priority weights (Survival Timers: Fire=60s, Smoke=180s, Clear=600s)
            limit = 600
            if sector["hazard"] == "fire": limit = 60
            elif sector["hazard"] == "smoke": limit = 180
            
            time_left = max(0, limit - elapsed)
            
            # Urgent if time_left is low
            candidates.append({
                "id": sid,
                "center": list(sector["center"]),
                "distance": round(dist, 1),
                "hazard": sector["hazard"],
                "time_left_seconds": round(time_left, 1),
                "priority_weight": time_left # Lower time left = higher priority
            })
            
        # Sort: Primary by Time Left (Urgency), Secondary by Distance
        candidates.sort(key=lambda x: (x["priority_weight"], x["distance"]))
        
        return candidates[:5]

    # ─── Summary ───

    def get_mission_summary(self):
        total_scannable = len(self.sectors) - len(self.no_fly_sector_ids)
        scanned = sum(1 for s in self.sectors.values() if s["scanned"] and s["id"] not in self.no_fly_sector_ids)
        return {
            "sectors_scanned": scanned,
            "sectors_total": total_scannable,
            "sectors_no_fly": len(self.no_fly_sector_ids),
            "coverage_pct": round(scanned / total_scannable * 100, 1) if total_scannable > 0 else 0,
            "survivors_found": len(self.discovered_survivors),
            "survivor_locations": [list(s) for s in self.discovered_survivors],
            "fleet_status": self.get_fleet_status(),
            "log": self.mission_log[-20:],
        }
