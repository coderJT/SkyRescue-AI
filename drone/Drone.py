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
        self.base_coordinates = coordinates  # remember home base for recall

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

    def thermal_scan(self, survivors):
        """
        Use thermal scanner to detect heat signatures within a radius of 5.
        Costs 0.2% battery per scan.
        """
        self.drain_battery(0.2)
        detected_survivors = []
        x1, y1, _ = self.coordinates
        
        for survivor in survivors:
            x2, y2, _ = survivor
            distance = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
            if distance <= 5:
                detected_survivors.append(survivor)
        
        return detected_survivors

    def move_to(self, x, y, z):
        """
        Move the drone to the specified coordinates.
        Battery drains proportional to distance traveled.
        """
        old_x, old_y, old_z = self.coordinates
        distance = math.sqrt((x - old_x)**2 + (y - old_y)**2 + (z - old_z)**2)
        self.drain_battery(distance * 0.02)  # 0.02% per unit distance
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
        }