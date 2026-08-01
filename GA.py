import random
import math
import time
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

POP_SIZE = 50
GENERATIONS = 60
MUTATION_RATE = 0.2

#alpha value:
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
# RANDOM PATH GENERATION
# ==========================================================
def generate_path():

    path = [SOURCE]
    current = SOURCE

    while current != DESTINATION:

        neighbors = [
            j for (i,j) in edges
            if i == current
        ]

        if not neighbors:
            break

        nxt = random.choice(neighbors)

        if nxt in path:
            break

        path.append(nxt)
        current = nxt

    if path[-1] != DESTINATION:
        path.append(DESTINATION)

    return path


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

                charging_plan.append(

                    f"{charge_type} at node {current_node}"

                )
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
# SELECTION
# ==========================================================
def selection(population):

    return sorted(
        population,
        key=lambda x: evaluate(x)[0]
    )[:10]


# ==========================================================
# CROSSOVER
# ==========================================================
def crossover(p1,p2):

    cut = random.randint(
        1,
        min(len(p1),len(p2))-2
    )

    child = p1[:cut]

    for node in p2:
        if node not in child:
            child.append(node)

    if child[-1] != DESTINATION:
        child.append(DESTINATION)

    return child


# ==========================================================
# MUTATION
# ==========================================================
def mutate(path):

    if random.random() < MUTATION_RATE:
        return generate_path()

    return path


# ==========================================================
# MAIN GA
# ==========================================================
start = time.time()

population = [
    generate_path()
    for _ in range(POP_SIZE)
]

for generation in range(GENERATIONS):

    parents = selection(population)

    new_population = parents[:5]

    while len(new_population) < POP_SIZE:

        p1,p2 = random.sample(
            parents,
            2
        )

        child = crossover(p1,p2)
        child = mutate(child)

        new_population.append(child)

    population = new_population


# ==========================================================
# BEST RESULT
# ==========================================================
best = min(
    population,
    key=lambda x: evaluate(x)[0]
)

fitness,result = evaluate(best)

execution_time = time.time()-start

write_output_to_file(
    result,
    execution_time
)

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