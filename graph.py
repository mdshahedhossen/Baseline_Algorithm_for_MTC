import random
import math
from collections import deque
import numpy as np
SEED=42
np.random.seed(SEED)
print("Random Seed :", SEED)

# ==========================================================
# PARAMETERS
# ==========================================================

NUM_NODES = 1600
MAP_WIDTH = 700      # km
MAP_HEIGHT = 900     # km
MIN_DISTANCE = 10    # km
MAX_DISTANCE = 45    # km

FIXED_ANGLE = 0.86

NUM_CHARGING_STATIONS = 20



# ==========================================================
# NODE GENERATION
# ==========================================================

nodes = {}

for i in range(NUM_NODES):

    nodes[i] = {
        "x": random.uniform(0, MAP_WIDTH),
        "y": random.uniform(0, MAP_HEIGHT)
    }

# ==========================================================
# DISTANCE FUNCTION
# ==========================================================

def euclidean(n1, n2):

    return math.sqrt(

        (nodes[n1]["x"] - nodes[n2]["x"])**2 +

        (nodes[n1]["y"] - nodes[n2]["y"])**2
    )


# ==========================================================
# EDGE GENERATION
# ==========================================================

edges = {}
adjacency = {}

for i in range(NUM_NODES):

    adjacency[i] = []


# ----------------------------------------------------------
# Backbone Connection
# ----------------------------------------------------------

for i in range(NUM_NODES - 1):

    distance = round(

        random.uniform(
            MIN_DISTANCE,
            MAX_DISTANCE
        ),

        2
    )

    edges[(i, i + 1)] = {

        "distance": distance,
        "angle": FIXED_ANGLE
    }

    edges[(i + 1, i)] = {

        "distance": distance,
        "angle": FIXED_ANGLE
    }


# ----------------------------------------------------------
# 3 Nearest Neighbor Connections
# ----------------------------------------------------------

for i in range(NUM_NODES):

    candidates = []

    for j in range(NUM_NODES):

        if i == j:
            continue

        candidates.append(

            (euclidean(i, j), j)
        )

    candidates.sort()

    nearest = candidates[:3]

    for _, j in nearest:

        if (i, j) not in edges:

            distance = round(

                random.uniform(
                    MIN_DISTANCE,
                    MAX_DISTANCE
                ),

                2
            )

            edges[(i, j)] = {

                "distance": distance,
                "angle": FIXED_ANGLE
            }

            edges[(j, i)] = {

                "distance": distance,
                "angle": FIXED_ANGLE
            }


# ==========================================================
# BUILD ADJACENCY
# ==========================================================

for u, v in edges:

    adjacency[u].append(v)


# ==========================================================
# PURE PYTHON K-MEANS
# ==========================================================

points = []

for node_id in nodes:

    points.append(

        (
            node_id,
            nodes[node_id]["x"],
            nodes[node_id]["y"]
        )
    )


centroids = random.sample(

    [(x, y) for _, x, y in points],

    NUM_CHARGING_STATIONS
)

MAX_ITER = 50

for _ in range(MAX_ITER):

    clusters = [

        []
        for _ in range(NUM_CHARGING_STATIONS)
    ]

    # Assign nodes to nearest centroid
    for node_id, x, y in points:

        best_cluster = 0
        best_distance = float("inf")

        for idx, (cx, cy) in enumerate(centroids):

            d = math.sqrt(

                (x - cx)**2 +

                (y - cy)**2
            )

            if d < best_distance:

                best_distance = d
                best_cluster = idx

        clusters[best_cluster].append(

            (node_id, x, y)
        )

    # Update centroids
    new_centroids = []

    for cluster in clusters:

        if len(cluster) == 0:

            new_centroids.append(

                random.choice(
                    [(x, y) for _, x, y in points]
                )
            )

            continue

        avg_x = sum(
            p[1] for p in cluster
        ) / len(cluster)

        avg_y = sum(
            p[2] for p in cluster
        ) / len(cluster)

        new_centroids.append(

            (avg_x, avg_y)
        )

    centroids = new_centroids


# ==========================================================
# CHARGING STATIONS
# ==========================================================

charging_stations = []

for cx, cy in centroids:

    best_node = None
    best_distance = float("inf")

    for node_id in nodes:

        d = math.sqrt(

            (nodes[node_id]["x"] - cx)**2 +

            (nodes[node_id]["y"] - cy)**2
        )

        if d < best_distance:

            best_distance = d
            best_node = node_id

    charging_stations.append(best_node)

charging_stations = list(
    set(charging_stations)
)

# ==========================================================
# CHARGING STATION PRICE
# ==========================================================

charging_station_data = {}

for station in charging_stations:

    charging_station_data[station] = {

        "price": round(random.uniform(0.20, 0.60), 2)

    }
# Print all charging station prices
print("\n========== Charging Station Prices ==========")

for station in charging_stations:

    print(
        f"Station {station}: "
        f"${charging_station_data[station]['price']:.2f}/kWh"
    )

print("=============================================\n")
# ==========================================================
# BFS
# ==========================================================

def bfs(start):

    visited = set([start])

    queue = deque([start])

    while queue:

        current = queue.popleft()

        for neighbor in adjacency[current]:

            if neighbor not in visited:

                visited.add(neighbor)

                queue.append(neighbor)

    return visited


# ==========================================================
# SOURCE
# Upper Left Corner
# ==========================================================

SOURCE = min(

    nodes,

    key=lambda n:

    nodes[n]["x"]**2 +

    nodes[n]["y"]**2
)


# ==========================================================
# DESTINATION
# Lower Right Corner
# ==========================================================

reachable = bfs(SOURCE)

DESTINATION = min(

    reachable,

    key=lambda n:

    (MAP_WIDTH - nodes[n]["x"])**2 +

    (MAP_HEIGHT - nodes[n]["y"])**2
)


# ==========================================================
# INFORMATION
# ==========================================================

print("\n===================================")
print("EV GRAPH GENERATED")
print("===================================")

print("Nodes:", len(nodes))
print("Edges:", len(edges))

print("\nCharging Stations:",
      len(charging_stations))

print(charging_stations)

print("\nSource:", SOURCE)
print("Coordinates:",
      nodes[SOURCE])

print("\nDestination:",
      DESTINATION)

print("Coordinates:",
      nodes[DESTINATION])

print("\nReachable Nodes:",
      len(reachable))

print("===================================\n")
from datetime import datetime

# ==========================================================
# WRITE OUTPUT TO FILE
# ==========================================================

def write_output_to_file(result,
                         execution_time,
                         filename="ACO_Results.txt"):

    with open(filename, "a") as file:
        timestamp = datetime.now().strftime("%Y-%m-%d  %I:%M:%S %p")
        file.write(f"Timestamp: {timestamp}\n")
        file.write(f"Source: {SOURCE}, Destination: {DESTINATION}")
        if result["path"]:
            file.write(f"Optimal Path: {result['path']}\n")
        else:
            file.write("No path found.\n")
        file.write(f"Total Nodes: {len(result['path'])}\n")
        file.write(f"Total Distance: {result['distance']:.2f} km\n")
        file.write(f"Total Travel Time: {result['time']:.2f} Minutes\n")
        file.write(f"Energy Consumed: {result['energy_consumed']:.2f} kWh\n")
        file.write(f"Energy Charged: {result['energy_charged']:.2f} kWh\n")
        file.write(f"Charging Cost: ${result['charging_cost']:.2f}\n")
        file.write(f"Total Cost: ${result['total_cost']:.2f}\n")
        file.write(f"Final Battery: {result['final_battery']:.2f}%\n")
        file.write(f"Current Energy Rate: ${result['current_energy_rate']:.2f}/kWh\n")
        if len(result["charging_plan"]) == 0:
            file.write("Charging Plan: No Charging\n")
        else:
            file.write("Charging Plan:\n")
            for plan in result["charging_plan"]:
                file.write(f"{plan}\n")
        file.write(f"Execution Time: {execution_time:.4f} seconds\n")

        file.write("------------------------------------------------\n")