import random
import math
import time
import copy
import heapq
from graph import (
    NUM_NODES,
    nodes,
    edges,
    adjacency,
    charging_stations,
    charging_station_data,
    SOURCE,
    DESTINATION,
    write_output_to_file
)
# ==========================================================
# SYSTEM PARAMETERS
# ==========================================================
BATTERY_CAPACITY = 100              # kWh
INITIAL_BATTERY = 80               # %
BATTERY_THRESHOLD = 5            # %

INITIAL_ENERGY_RATE = 0.50         # $/kWh
BASE_SPEED = 50                    # km/h
ALPHA = 0.5      # Weight for travel time

# Vehicle parameters
M = 1800
m = 1.1
f = 0.01
c = 0.6
A = 3.5
dv_dt = 0.3
g = 9.8 

# ==========================================================
# DYNAMIC TRAFFIC
# ==========================================================
def get_dynamic_traffic():

    traffic = random.choice([
        "low",
        "medium",
        "high"
    ])

    # if traffic == "low":
    #     factor = random.uniform(1.0,1.2)

    # elif traffic == "medium":
    #     factor = random.uniform(0.7,1.0)

    # else:
    #     factor = random.uniform(0.4,0.7)

    if traffic == "low":
        factor = random.uniform(0.90, 1.00)
    elif traffic == "medium":
        factor = random.uniform(0.70, 0.90)
    else:  # High traffic
        factor = random.uniform(0.40, 0.70)
    return traffic, factor

# ==========================================================
# UPDATE CURRENT ENERGY RATE
# ==========================================================
def update_current_energy_rate(
        old_battery,
        old_rate,
        new_charge,
        station_rate):

    total_energy = old_battery + new_charge

    if total_energy == 0:
        return station_rate

    current_rate = (
        (old_battery * old_rate)
        + (new_charge * station_rate)
    ) / total_energy
    # print("current_rate",current_rate)

    return round(current_rate,2)


# ==========================================================
# ENERGY MODEL
# ==========================================================
def calculate_energy(distance, angle, speed):

    air_density = 1.225

    cos_alpha = math.cos(
        math.radians(angle)
    )

    sin_alpha = math.sin(
        math.radians(angle)
    )

    energy = (1/3600) * (
        M*g*(f*cos_alpha + sin_alpha)
        + 0.0386*(air_density*c*A*speed**2)
        + (M+m)*dv_dt
    ) * distance

    return energy

# ==========================================================
# FUTURE CHARGING STATIONS
# ==========================================================
def get_future_stations(path, current_index):

    future = []

    for i in range(
        current_index+1,
        len(path)
    ):
        node = path[i]

        if node in charging_stations:
            future.append(node)

    return future


# ==========================================================
# FITNESS FUNCTION
# ==========================================================
def evaluate(path):

    battery = INITIAL_BATTERY
    current_energy_rate = INITIAL_ENERGY_RATE

    total_cost = 0
    total_distance = 0
    total_time = 0

    energy_consumed = 0
    energy_charged = 0
    charging_cost = 0

    charging_plan = []

    for i in range(len(path)-1):

        edge = (path[i], path[i+1])

        if edge not in edges:
            return float("inf"), None

        edge_data = edges[edge]

        distance = edge_data["distance"]
        angle = edge_data["angle"]

        # -----------------------------------
        # Dynamic traffic
        # -----------------------------------
        traffic, factor = get_dynamic_traffic()
        speed = BASE_SPEED * factor

        # -----------------------------------
        # Travel time
        # -----------------------------------
        travel_time = (
            distance/speed
        ) * 60

        # -----------------------------------
        # Energy consumption
        # -----------------------------------
        energy = calculate_energy(distance,angle,speed)
        # -----------------------------------
        # Travel cost
        # -----------------------------------
        travel_cost = (energy * current_energy_rate)
        # -----------------------------------
        # Battery update
        # -----------------------------------
        battery_drop = (
            energy/BATTERY_CAPACITY
        ) * 100

        battery -= battery_drop

        total_distance += distance
        total_time += travel_time
        total_cost += travel_cost
        energy_consumed += energy

        if battery < BATTERY_THRESHOLD:
            return float("inf"), None

        current_node = path[i+1]

        # -----------------------------------
        # Charging Decision
        # -----------------------------------
        if current_node in charging_stations:

            station_rate = charging_station_data[current_node]["price"]

            # Current battery energy (kWh)
            available_energy = (
                battery / 100
            ) * BATTERY_CAPACITY

            # Safety energy
            safe_energy = (
                BATTERY_THRESHOLD / 100
            ) * BATTERY_CAPACITY
            # -----------------------------------
            # Calculate remaining energy
            # -----------------------------------
            remaining_energy = 0

            for j in range(i + 1, len(path) - 1):

                future_edge = (
                    path[j],
                    path[j + 1]
                )

                if future_edge in edges:

                    future_data = edges[future_edge]

                    future_traffic, future_factor = get_dynamic_traffic()

                    future_speed = (
                        BASE_SPEED *
                        future_factor
                    )

                    remaining_energy += calculate_energy(

                        future_data["distance"],

                        future_data["angle"],

                        future_speed

                    )
            # -----------------------------------
            # Future charging stations
            # -----------------------------------
            future_stations = get_future_stations(
                path,
                i + 1
            )

            future_prices = [

                charging_station_data[s]["price"]

                for s in future_stations

            ]
            should_charge = False
            charge_type = ""
            # ==================================================
            # CASE 1
            # Battery cannot safely reach destination
            # ==================================================
            if available_energy < (remaining_energy +safe_energy):
                should_charge = True
                # Cheapest station
                if (not future_prices or station_rate <= min(future_prices)):
                    required_energy = (BATTERY_CAPACITY - available_energy)
                    charge_type = "Full Charge"
                else:
                    required_energy = (remaining_energy+safe_energy-available_energy)
                    charge_type = "Partial Charge"
             # ==================================================
            # CASE 2
            # Battery is enough,
            # but charging reduces average energy rate
            # ==================================================
            elif station_rate < current_energy_rate:

                should_charge = True

                # Small amount only to reduce
                # the average energy rate
                required_energy = min(

                    BATTERY_CAPACITY * 0.20,

                    BATTERY_CAPACITY -

                    available_energy

                )

                charge_type = "Cost Optimization"
            # ==================================================
            # Perform Charging
            # ==================================================
            if should_charge and required_energy > 0:

                required_energy = min(required_energy,BATTERY_CAPACITY-available_energy)

                charge_percent = (required_energy/BATTERY_CAPACITY)*100
                charge_cost = (required_energy*station_rate)

                charging_power = 50      # kW
                charging_time = (required_energy/charging_power)*60
                old_energy = available_energy

                battery = min(100,battery+charge_percent)
                energy_charged += required_energy
                charging_cost += charge_cost
                total_cost += charge_cost
                total_time += charging_time
                current_energy_rate = update_current_energy_rate(old_energy,current_energy_rate,required_energy,station_rate)

                charging_plan.append(f"{charge_type} at node {current_node}")
    # ---------------------------Updated part Start------------------
    # note:
    # These are example normalization values.
    # Replace them with appropriate values from your experiments.
    MAX_TIME = 300.0
    MAX_COST = 100.0

    normalized_time = total_time / MAX_TIME
    normalized_cost = total_cost / MAX_COST

    objective = (
        ALPHA * normalized_time +
        (1 - ALPHA) * normalized_cost
    )
    return objective, {
        "path": path,
        "objective": objective,
        "total_cost": total_cost,
        "distance": total_distance,
        "time": total_time,
        "energy_consumed": energy_consumed,
        "energy_charged": energy_charged,
        "charging_cost": charging_cost,
        "final_battery": battery,
        "current_energy_rate": current_energy_rate,
        "charging_plan": charging_plan
    }
# ---------------------------Updated part end------------------
    # return total_cost,{
    #     "path": path,
    #     "total_cost": total_cost,
    #     "distance": total_distance,
    #     "time": total_time,
    #     "energy_consumed": energy_consumed,
    #     "energy_charged": energy_charged,
    #     "charging_cost": charging_cost,
    #     "final_battery": battery,
    #     "current_energy_rate": current_energy_rate,
    #     "charging_plan": charging_plan
    # }
    
# ==========================================================
# NODE
# ==========================================================

class Node:

    def __init__(self, node):

        self.node = node

        self.g = float("inf")

        self.h = 0

        self.f = float("inf")

        self.parent = None

    def __lt__(self, other):

        return self.f < other.f
    
# ==========================================================
# HEURISTIC
# ==========================================================

def heuristic(node):
    dx = nodes[node]["x"] - nodes[DESTINATION]["x"]
    dy = nodes[node]["y"] - nodes[DESTINATION]["y"]
    return math.sqrt(dx**2 + dy**2)

# ==========================================================
# RECONSTRUCT PATH
# ==========================================================
def reconstruct_path(goal):
    path = []
    current = goal
    while current is not None:
        path.append(current.node)
        current = current.parent
    path.reverse()
    return path
# ==========================================================
# INITIALIZE ASTAR
# ==========================================================

def initialize_astar():
    open_list = []
    closed_set = set()
    all_nodes = {}
    for node in nodes:
        all_nodes[node] = Node(node)
    start = all_nodes[SOURCE]
    start.g = 0
    start.h = heuristic(SOURCE)
    start.f = start.g + start.h
    heapq.heappush(
        open_list,
        start
    )

    return open_list, closed_set, all_nodes
# ==========================================================
# ASTAR SEARCH
# ==========================================================
def astar():
    # Initialize
    open_list, closed_set, all_nodes = initialize_astar()
    # Continue until no node remains
    while open_list:
        # Get node having smallest f value
        current = heapq.heappop(open_list)
        # Destination found
        if current.node == DESTINATION:
            return reconstruct_path(current)
        # Mark current node as visited
        closed_set.add(current.node)
        # Explore every neighbor
        for neighbor in adjacency[current.node]:
            # Skip visited node
            if neighbor in closed_set:
                continue
            # -----------------------------
            # Edge Information
            # -----------------------------
            edge = (current.node,neighbor)
            edge_data = edges[edge]
            distance = edge_data["distance"]
            angle = edge_data["angle"]
            # -----------------------------
            # Dynamic Traffic
            # -----------------------------
            traffic, factor = get_dynamic_traffic()
            speed = BASE_SPEED * factor
            # -----------------------------
            # Energy Consumption
            # -----------------------------
            energy = calculate_energy(distance,angle,speed)
            # -----------------------------
            # Travel Cost
            # -----------------------------

            travel_cost = (

                energy *

                INITIAL_ENERGY_RATE

            )

            # -----------------------------
            # New Cost
            # -----------------------------

            tentative_g = (

                current.g +

                travel_cost

            )

            # Get neighbor object
            neighbor_node = all_nodes[neighbor]

            # Better path?
            if tentative_g < neighbor_node.g:

                neighbor_node.parent = current

                neighbor_node.g = tentative_g

                neighbor_node.h = heuristic(neighbor)

                neighbor_node.f = (

                    neighbor_node.g +

                    neighbor_node.h

                )

                heapq.heappush(

                    open_list,

                    neighbor_node

                )

    return None

# ==========================================================
# RUN ASTAR
# ==========================================================

def run_astar():
    start_time = time.time()
    path = astar()
    execution_time = time.time() - start_time
    if path is None:
        print("No feasible path found.")
        return None
    # Evaluate path using the same function as GA
    fitness, result = evaluate(path)
    return fitness, result, execution_time

# ==========================================================
# PRINT RESULT
# ==========================================================

def print_result(result, execution_time):

    print("\n")
    print("=" * 60)
    print("               COST-AWARE ASTAR RESULT")
    print("=" * 60)

    print("\nOptimal Path:")
    print(result["path"])

    print("\nTotal Nodes:")
    print(len(result["path"]))

    print("\nTotal Distance (km):")
    print(round(result["distance"],2))

    print("\nTotal Travel Time (min):")
    print(round(result["time"],2))

    print("\nEnergy Consumed (kWh):")
    print(round(result["energy_consumed"],2))

    print("\nEnergy Charged (kWh):")
    print(round(result["energy_charged"],2))

    print("\nCharging Cost ($):")
    print(round(result["charging_cost"],2))

    print("\nTotal Cost ($):")
    print(round(result["total_cost"],2))

    print("\nRemaining Battery (%):")
    print(round(result["final_battery"],2))

    print("\nCurrent Energy Rate ($/kWh):")
    print(round(result["current_energy_rate"],2))

    print("\nCharging Plan:")

    if len(result["charging_plan"]) == 0:
        print("No Charging")
    else:
        for plan in result["charging_plan"]:
            print(plan)
    print("\nExecution Time (second):")
    print(round(execution_time,4))
    print("=" * 60)
# ==========================================================
# MAIN
# ==========================================================

def main():
    output = run_astar()
    if output is None:
        return
    fitness, result, execution_time = output
    print_result(result,execution_time)
     # Save into text file
    write_output_to_file(
        result,
        execution_time
    )


if __name__ == "__main__":

    main()