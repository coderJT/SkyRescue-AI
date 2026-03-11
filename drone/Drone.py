"""
drone.py

Basic implementation of a Drone object, with basic attributes with observability methods to simulate a real-world drone
with detection capabilities.
"""

import uuid
import math

class Drone:

    def __init__(self, name, battery_remaining, status, coordinates):
        """
        Initialize the drone with basic attributes.
        """
        self.id = uuid.uuid4().hex
        self.name = name
        self.battery_remaining = battery_remaining
        self.status = status  # active, returning, charging, offline
        self.coordinates = coordinates
        self.base_coordinates = coordinates 
        self.target_sector = None
        self.current_reason = None

    def get_battery_status(self):
        """
        Get remaining battery status.
        """
        return self.battery_remaining

    def get_status(self):
        """
        Get current status of the drone.
        """
        return self.status

    def set_status(self, status):
        """
        Set the drone status: active, returning, charging, offline.
        """
        self.status = status

    def thermal_scan(self, survivors, radius=18.0):
        """
        Use thermal scanner to detect heat signatures within a radius (default 18.0).
        Costs 1.0% battery per scan.
        TODO: Here, we will implement a binary classification machine learning model to simulate a drone performing thermal scanning.
        """
        self.drain_battery(1.0)
        detected_survivors = []
        x1, _, z1 = self.coordinates
        
        for survivor in survivors:
            x2, _, z2 = survivor
            distance = ((x2 - x1)**2 + (z2 - z1)**2)**0.5
            if distance <= radius:
                detected_survivors.append(survivor)
        return detected_survivors

    def scan_surrounding(self, all_sectors, radius=40):
        """
        Scans the immediate vicinity to discover hazards.
        This represents the drone's onboard sensors revealing the "true_hazard" of nearby sectors.
        Updates the shared simulation engine sectors directly.
        """
        discovered = {}
        x1, _, z1 = self.coordinates
        
        for sid, sector in all_sectors.items():
            scx, scz = sector["center"]
            distance = ((scx - x1)**2 + (scz - z1)**2)**0.5
            if distance <= radius:
                # Mutate the source of truth
                sector["discovered"] = True
                sector["hazard"] = sector["true_hazard"]
                discovered[sid] = sector
                
        return discovered

    def move_to(self, x, y, z):
        """
        Move the drone to the specified coordinates.
        Battery drains proportional to distance traveled by 0.50% per unit distance.
        """
        old_x, old_y, old_z = self.coordinates
        distance = math.sqrt((x - old_x)**2 + (y - old_y)**2 + (z - old_z)**2)
        self.drain_battery(distance * 0.50)
        self.coordinates = (x, y, z)

    def drain_battery(self, amount):
        """
        Drain battery by the given amount. Clamp to 0.
        """
        self.battery_remaining = max(0, self.battery_remaining - amount)
        if self.battery_remaining == 0:
            self.status = "offline"

    def charge(self):
        """
        Simulate charging. Resets battery to 100 and sets status to active.
        """
        self.battery_remaining = 100
        self.status = "active"

    def to_dict(self):
        """
        Serialize drone state for MCP responses.
        """
        return {
            "name": self.name,
            "battery": round(self.battery_remaining, 1),
            "status": self.status,
            "coordinates": list(self.coordinates),
            "target_sector": getattr(self, 'target_sector', None),
            "reason": getattr(self, 'current_reason', None),
        }