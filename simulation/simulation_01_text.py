from drone.Drone import Drone

class DroneSystemSimulation01Text:

    def __init__(self):

        # Initialize 5 drones with full battery capacity (100), and starts at (0, 0, 0)
        self.drones = {
            "drone_1": Drone("drone_1", 100, "active", (0, 0, 0)),
            "drone_2": Drone("drone_2", 100, "active", (0, 0, 0)),
            "drone_3": Drone("drone_3", 100, "active", (0, 0, 0)),
            "drone_4": Drone("drone_4", 100, "active", (0, 0, 0)),
            "drone_5": Drone("drone_5", 100, "active", (0, 0, 0)),
        }

        # Initialize 3 survivors at (5, 5, 3), (6, 6, 3), (7, 7, 3)
        self.survivors = [(50, 50, 3), (60, 60, 3), (70, 70, 3)]

    def move_to(self, drone_id, x, y, z):
        """
        Move the drone to the specified coordinates.
        """
        return self.drones[drone_id].move_to(x, y, z)

    def get_battery_status(self, drone_id):
        """
        Get remaining battery status.
        """
        return self.drones[drone_id].get_battery_status()

    def get_status(self, drone_id):
        """
        Get current status of the drone.
        """
        return self.drones[drone_id].get_status()

    def thermal_scan(self, drone_id):
        """
        Use thermal scanner to detect heat signatures.
        """
        return self.drones[drone_id].thermal_scan(self.survivors)

    def run_simulation(self, steps=10):
        """
        Run the simulation for a number of steps.
        """
        print(f"Starting simulation with {len(self.drones)} drones and {len(self.survivors)} survivors.")
        
        for step in range(1, steps + 1):
            print(f"\n--- Step {step} ---")
            for drone_id, drone in self.drones.items():
                
                # Simple logic to find the first survivor for now
                target = self.survivors[0]
                curr_x, curr_y, curr_z = drone.coordinates
                
                new_x = curr_x + (1 if target[0] > curr_x else -1 if target[0] < curr_x else 0)
                new_y = curr_y + (1 if target[1] > curr_y else -1 if target[1] < curr_y else 0)
                new_z = curr_z 
                
                self.move_to(drone_id, new_x, new_y, new_z)
                print(f"{drone_id} moved to {drone.coordinates}")
                
                detected = self.thermal_scan(drone_id)
                if detected:
                    print(f"  [ALERT] {drone_id} detected heat signatures at: {detected}")
                else:
                    print(f"  {drone_id}: No heat signatures detected.")

if __name__ == "__main__":
    simulation = DroneSystemSimulation01Text()
    simulation.run_simulation(steps=10)
