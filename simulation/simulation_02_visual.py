import turtle
import time
from simulation.simulation_01_text import DroneSystemSimulation01Text

class DroneSystemSimulation02Visual(DroneSystemSimulation01Text):
    def __init__(self, padding=20):
        super().__init__()
        self.padding = padding
        self.screen = turtle.Screen()
        self.screen.title("Drone Search and Rescue Simulation")
        self.screen.setup(width=800, height=800)
        self.screen.tracer(0) 

        # Dynamically calculate the world coordinates based on survivor positions
        all_x = [s[0] for s in self.survivors] + [0]
        all_y = [s[1] for s in self.survivors] + [0]
        min_x, max_x = min(all_x) - padding, max(all_x) + padding
        min_y, max_y = min(all_y) - padding, max(all_y) + padding
        
        # Ensure a square-ish aspect ratio or at least enough space
        range_x = max_x - min_x
        range_y = max_y - min_y
        max_range = max(range_x, range_y)
        
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2
        
        self.screen.setworldcoordinates(
            mid_x - max_range/2, 
            mid_y - max_range/2, 
            mid_x + max_range/2, 
            mid_y + max_range/2
        )
        
        # Create turtles for drones
        self.drone_turtles = {}
        self.radius_turtles = {}
        for drone_id in self.drones:
            t = turtle.Turtle()
            t.shape("triangle")
            t.color("blue")
            t.penup()
            self.drone_turtles[drone_id] = t
            
            rt = turtle.Turtle()
            rt.hideturtle()
            rt.penup()
            rt.color("lightblue")
            self.radius_turtles[drone_id] = rt
            
        # Create turtles for survivors
        self.survivor_turtles = []
        for sur in self.survivors:
            st = turtle.Turtle()
            st.shape("circle")
            st.color("red")
            st.penup()
            st.goto(sur[0], sur[1])
            self.survivor_turtles.append(st)

    def draw_radius(self, drone_id, pos, is_detecting, pulse_radius=None):
        rt = self.radius_turtles[drone_id]
        rt.clear()
        
        # Standard detection radius (the scan area)
        if is_detecting:
            rt.color("lime")
        else:
            rt.color("lightblue")
        
        # Radius is 3 units in world coordinates
        radius = 5
        rt.goto(pos[0], pos[1] - radius)
        rt.pendown()
        rt.circle(radius)
        rt.penup()

        # If we are pulsing (animation), draw the extra expanding circle
        if pulse_radius is not None:
            rt.color("chartreuse")
            rt.goto(pos[0], pos[1] - pulse_radius)
            rt.pendown()
            rt.circle(pulse_radius)
            rt.penup()

    def run_visual_simulation(self, steps=100):
        print(f"Starting visual simulation with {len(self.drones)} drones.")
        
        try:
            for step in range(1, steps + 1):
                for drone_id, drone in self.drones.items():
                    target = self.survivors[0]
                    curr_x, curr_y, curr_z = drone.coordinates
                    
                    new_x = curr_x + (1 if target[0] > curr_x else -1 if target[0] < curr_x else 0)
                    new_y = curr_y + (1 if target[1] > curr_y else -1 if target[1] < curr_y else 0)
                    new_z = curr_z
                    
                    self.move_to(drone_id, new_x, new_y, new_z)
                    
                    # Visual update
                    pos = (new_x, new_y)
                    self.drone_turtles[drone_id].goto(pos)
                    
                    detected = self.thermal_scan(drone_id)
                    is_det = len(detected) > 0
                    self.draw_radius(drone_id, pos, is_det)
                    
                    # Detection animation: Pulse if detected
                    if is_det:
                        for p_radius in range(4, 8, 1): # pulse from radius 4 to 8
                            self.draw_radius(drone_id, pos, is_det, pulse_radius=p_radius)
                            self.screen.update()
                            time.sleep(0.02)
                        # Clear pulse after finishing
                        self.draw_radius(drone_id, pos, is_det)
                    
                self.screen.update()
                time.sleep(0.05) # Slightly faster to accommodate animation
                
                # Stop if all drones reached target
                if all(drone.coordinates[:2] == target[:2] for drone in self.drones.values()):
                    print("All drones reached target area.")
                    break
        except turtle.Terminator:
            print("Simulation window closed.")
            return
        except Exception as e:
            if "invalid command name" in str(e):
                print("Simulation window closed.")
                return
            raise e
        
        print("Simulation complete. Click window to exit.")
        try:
            self.screen.exitonclick()
        except:
            pass

if __name__ == "__main__":
    vis_sim = DroneSystemSimulation02Visual()
    vis_sim.run_visual_simulation(steps=100)
