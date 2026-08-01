import random
import math

# ==========================================================
# USER INPUT
# ==========================================================

NUM_NODES = int(input("Enter number of nodes: "))

MIN_DISTANCE = float(
    input("Minimum road distance (km): ")
)

MAX_DISTANCE = float(
    input("Maximum road distance (km): ")
)

NUM_CHARGING_STATIONS = int(
    input("Number of charging stations: ")
)

SOURCE = int(
    input("Enter source node: ")
)

DESTINATION = int(
    input("Enter destination node: ")
)

# ==========================================================
# NODES
# ==========================================================

nodes = list(
    range(NUM_NODES)
)

# ==========================================================
# EDGES
# ==========================================================

edges = {}

for i in range(NUM_NODES):

    # connect each node to 2–3 future nodes
    num_connections = random.randint(2, 3)

    possible = list(
        range(i + 1, NUM_NODES)
    )

    random.shuffle(possible)

    neighbors = possible[
        :num_connections
    ]

    for j in neighbors:

        distance = round(
            random.uniform(
                MIN_DISTANCE,
                MAX_DISTANCE
            ),
            2
        )

        angle = 0.86

        edges[(i, j)] = {
            "distance": distance,
            "angle": angle
        }

# ==========================================================
# CHARGING STATIONS
# ==========================================================

available_nodes = [

    n for n in nodes

    if n not in (
        SOURCE,
        DESTINATION
    )
]

charging_stations = random.sample(
    available_nodes,
    min(
        NUM_CHARGING_STATIONS,
        len(available_nodes)
    )
)

# ==========================================================
# OUTPUT
# ==========================================================

print("\nNodes:")

print(nodes)

print("\nEdges:")

for edge, data in edges.items():

    print(
        edge,
        data
    )

print(
    "\nCharging Stations:",
    charging_stations
)

print(
    "\nSource:",
    SOURCE
)

print(
    "Destination:",
    DESTINATION
)