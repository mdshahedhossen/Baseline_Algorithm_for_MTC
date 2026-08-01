import random
import math
import time
import copy
from graph import (
    NUM_NODES,
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

# ==========================================================
# ACO PARAMETERS
# ==========================================================
NUM_ANTS = 50
MAX_ITERATIONS = 60
ALPHA = 1.0
BETA = 2.0
RHO = 0.2
Q = 100

OBJECTIVE_ALPHA = 0.5    # weight for travel time

# PHEROMONE INITIALIZATION
pheromone = {}
for edge in edges:
    pheromone[edge] = 1.0
# ==========================================================
# ANT
# ==========================================================

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
# ANT CLASS
# ==========================================================

class Ant:

    def __init__(self):

        self.current = SOURCE

        self.path = [SOURCE]

        self.visited = set()

        self.visited.add(SOURCE)

        self.finished = False

        self.total_cost = float("inf")

        self.result = None
# ==========================================================
# HEURISTIC
# ==========================================================

def heuristic(current, neighbor):

    edge = (current, neighbor)

    distance = edges[edge]["distance"]

    degree = len(adjacency[neighbor])

    eta = (

        (1/(distance+1))

        *

        (degree+1)

    )

    return eta
# ==========================================================
# TRANSITION PROBABILITY
# ==========================================================

def transition_probability(ant):

    current = ant.current

    probabilities = []

    total = 0

    for neighbor in adjacency[current]:

        if neighbor in ant.visited:

            continue

        edge = (current, neighbor)

        tau = pheromone[edge]

        eta = heuristic(current, neighbor)

        value = (

            tau ** ALPHA

        ) * (

            eta ** BETA

        )

        probabilities.append(

            (neighbor, value)

        )

        total += value

    if total == 0:

        return None

    normalized = []

    for node, value in probabilities:

        normalized.append(

            (

                node,

                value / total

            )

        )

    return normalized
# ==========================================================
# ROULETTE WHEEL
# ==========================================================

def roulette(probabilities):

    r = random.random()

    cumulative = 0

    for node, prob in probabilities:

        cumulative += prob

        if cumulative >= r:

            return node

    return probabilities[-1][0]
# ==========================================================
# CONSTRUCT ANT PATH (Improved)
# ==========================================================

def construct_ant_path(ant):

    MAX_STEPS = NUM_NODES

    steps = 0

    while (
        ant.current != DESTINATION
        and
        steps < MAX_STEPS
    ):

        probabilities = transition_probability(ant)

        # Dead end
        if probabilities is None:

            ant.finished = False

            return

        # 90% exploration
        if random.random() < 0.90:

            next_node = roulette(probabilities)

        # 10% greedy
        else:

            next_node = max(

                probabilities,

                key=lambda x:x[1]

            )[0]

        ant.path.append(next_node)

        ant.visited.add(next_node)

        ant.current = next_node

        steps += 1

    if ant.current == DESTINATION:

        ant.finished = True

    else:

        ant.finished = False

# ==========================================================
# INITIALIZE COLONY
# ==========================================================

def initialize_colony():

    colony = []

    for _ in range(NUM_ANTS):

        colony.append(

            Ant()

        )

    return colony
# ==========================================================
# EVALUATE COLONY
# ==========================================================

def evaluate_colony(colony):

    for ant in colony:

        if not ant.finished:
            ant.total_cost = float("inf")
            ant.result = None
            continue

        fitness, result = evaluate(ant.path)

        ant.total_cost = fitness

        ant.result = result
# ==========================================================
# BEST ANT
# ==========================================================

def get_best_ant(colony):

    best_ant = None

    best_cost = float("inf")

    for ant in colony:

        if not ant.finished:

            continue

        if ant.result is None:

            continue

        if ant.total_cost < best_cost:

            best_cost = ant.total_cost

            best_ant = ant

    return best_ant
# ==========================================================
# EVAPORATE PHEROMONE
# ==========================================================

def evaporate_pheromone():

    for edge in pheromone:

        pheromone[edge] *= (1 - RHO)

        if pheromone[edge] < 0.0001:

            pheromone[edge] = 0.0001
# ==========================================================
# UPDATE PHEROMONE
# ==========================================================

def update_pheromone(best_ant):

    if best_ant is None:

        return

    evaporate_pheromone()

    # deposit = Q / best_ant.total_cost
    deposit = Q / (best_ant.total_cost + 1)

    path = best_ant.path

    for i in range(len(path)-1):

        edge = (

            path[i],

            path[i+1]

        )

        if edge in pheromone:

            pheromone[edge] += deposit
# ==========================================================
# MAIN ACO
# ==========================================================

def ACO():

    start = time.time()

    global_best = None

    global_cost = float("inf")

    for iteration in range(MAX_ITERATIONS):

        colony = initialize_colony()

        # Build path
        for ant in colony:

            construct_ant_path(ant)

        # Evaluate using your GA function
        evaluate_colony(colony)

        best_ant = get_best_ant(colony)

        if best_ant is not None:

            if best_ant.total_cost < global_cost:

                global_cost = best_ant.total_cost

                global_best = copy.deepcopy(best_ant)

        update_pheromone(best_ant)

        print(

            f"Iteration {iteration+1} "

            f"Best Cost = {global_cost:.2f}"

        )

    execution_time = time.time() - start

    return global_best, execution_time




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
        energy = calculate_energy(
            distance,
            angle,
            speed
        )

        # -----------------------------------
        # Travel cost
        # -----------------------------------
        travel_cost = (
            energy *
            current_energy_rate
        )

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
        OBJECTIVE_ALPHA * normalized_time +
        (1 - OBJECTIVE_ALPHA) * normalized_cost
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
# ---------------------------Updated part end--------------

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
# RUN ACO
# ==========================================================

best_ant, execution_time = ACO()

if best_ant is None:

    print("No feasible solution found.")

    exit()

result = best_ant.result

write_output_to_file(
    result,
    execution_time
)


# # ==========================================================
# # BEST RESULT
# # ==========================================================
# best = min(
#     population,
#     key=lambda x: evaluate(x)[0]
# )

# fitness,result = evaluate(best)

# execution_time = time.time()-start


# ==========================================================
# OUTPUT
# ==========================================================
print("-----------------------------------------------------")
print(f"Optimal Path: {result['path']}")
print(f"Total Cost: ${result['total_cost']:.2f}")
print(f"Total Distance: {result['distance']:.2f} km")
print(f"Total Travel Time: {result['time']:.2f} min")
print(f"Energy Consumed: {result['energy_consumed']:.2f} kWh")
print(f"Energy Charged: {result['energy_charged']:.2f} kWh")
print(f"Charging Cost: ${result['charging_cost']:.2f}")
print(f"Final Battery: {result['final_battery']:.2f}%")
print(f"Current Energy Rate: ${result['current_energy_rate']:.2f}")
print(f"Charging Plan: {result['charging_plan']}")
print(f"Execution Time: {execution_time:.4f} sec")
print("-----------------------------------------------------")