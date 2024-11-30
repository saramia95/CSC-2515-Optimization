
def check_feasibility(instance_data, solution):
    """
    Feasibility check function for a vehicle routing and transshipment problem.
    """
    # Extract instance parameters
    N = instance_data.S + 1 # Total number of nodes
    W = instance_data.W  # Number of demands
    V_small_total = instance_data.Vind[0]
    V_big_total = instance_data.Vind[1]
    Vtotal = V_small_total + V_big_total # Number of vehicles
    ow = instance_data.ow # Origins of demands
    dw = instance_data.dw  # Destinations of demands
    qw = instance_data.qw # Demand quantities
    vcapacity = instance_data.vcap  # Vehicle capacities
    # si = instance_data.si  # Indicator for transshipment nodes
    # tawv = instance_data.tawv  # Vehicle weights
    
    # Extract solution variables
    fijvw = solution['fijvw']  # Flow variables
    xijv = solution['xijv']  # Arc usage
    av = solution['av']  # Vehicle acquisition
    Zvi = solution['Zvi']  # Node visit
    yi = solution['yi']  # Hub/transshipment node activation

    # Initialize flags and error list
    feasible = True
    errors = []

    nonzero_flows = [w for w, flow in enumerate(qw) if flow > 0]

    # (2) Flow balance at origin
    for w in nonzero_flows:
        sum_flow = sum(
            fijvw[ow[w], j, v, w] for v in range(Vtotal) for j in range(1, N)
        )
        if sum_flow != 1:  # Allow a small tolerance for floating-point errors
            feasible = False
            errors.append(f"Flow balance violated at origin for demand {w}.")

    # (3) Flow balance at destination
    for w in nonzero_flows:
        sum_flow = sum(
            fijvw[i, dw[w], v, w] for v in range(Vtotal) for i in range(1, N)
        )
        if sum_flow != 1:
            feasible = False
            errors.append(f"Flow balance violated at destination for demand {w}.")

    # (4) Flow balance at intermediate nodes
    for w in nonzero_flows:
        for i in range(1, N):
            if i != ow[w] and i != dw[w]:
                sum_out = sum(
                    fijvw[i, j, v, w] for v in range(Vtotal) for j in range(1, N) if j != i
                )
                sum_in = sum(
                    fijvw[j, i, v, w] for v in range(Vtotal) for j in range(1, N) if j != i
                )
                if not abs(sum_out - sum_in) < 1e-6:
                    feasible = False
                    errors.append(f"Flow conservation violated at node {i} for demand {w}.")

    # (5) Flow implies arc usage
    for v in range(Vtotal):
        for w in nonzero_flows:
            for i in range(1, N):
                for j in range(1, N):
                    if fijvw[i, j, v, w] > xijv[i, j, v] + 1e-6:
                        feasible = False
                        errors.append(f"Flow on arc ({i}, {j}) in vehicle {v} without arc usage.")

    # (6) Transshipment vehicle changes
    for v in range(Vtotal):
        for w in nonzero_flows:
            for j in range(1, N):
                if j != ow[w] and j != dw[w] and yi[j] == 0:
                    sum_flow = sum(
                        fijvw[i, j, v, w] - fijvw[j, i, v, w] for i in range(1, N) if i != j
                    )
                    if not abs(sum_flow) < 1e-6:
                        feasible = False
                        errors.append(f"Flow balance at non-transshipment node {j} violated for demand {w}.")

    # (7) Vehicle capacity constraints
    for v in range(Vtotal):
        for i in range(1, N):
            for j in range(1, N):
                total_flow = sum(qw[w] * fijvw[i, j, v, w] for w in nonzero_flows)
                if v in range (V_small_total):
                    if total_flow > vcapacity[0] * xijv[i, j, v]:
                        feasible = False
                        errors.append(f"Capacity constraint violated on arc ({i}, {j}) for vehicle {v}.")
                
                if v in range (V_small_total):
                    if total_flow > vcapacity[1] * xijv[i, j, v]:
                        feasible = False
                        errors.append(f"Capacity constraint violated on arc ({i}, {j}) for vehicle {v}.")

    # (8) Node balance for vehicles
    for v in range(Vtotal):
        for i in range(N):
            sum_out = sum(xijv[i, j, v] for j in range(N) if i != j)
            sum_in = sum(xijv[j, i, v] for j in range(N) if i != j)
            if not abs(sum_out - sum_in) < 1e-6:
                feasible = False
                errors.append(f"Node balance violated for vehicle {v} at node {i}.")

    # (12) Vehicle acquisition
    for v in range(Vtotal):
        if av[v] < 0.5:  # Vehicle not acquired
            for i in range(N):
                for j in range(N):
                    if xijv[i, j, v] > 1e-6:
                        feasible = False
                        errors.append(f"Vehicle {v} traverses arc ({i}, {j}) without being acquired.")

    # Final check for continuous paths
    for w in nonzero_flows:
        if not check_continuous_path(w, ow[w], dw[w], fijvw, xijv, Vtotal, yi):
            feasible = False
            # errors.append(f"No continuous feasible path for demand {w}.")******** (checking this error is not accurate)

    # Return feasibility and errors
    return feasible, errors

def check_continuous_path(w, origin, destination, fijvw, xijv, Vtotal, yi):
    """
    Check if there is a continuous path from origin to destination for a demand.
    Vehicle changes are allowed only at transshipment nodes.
    
    Parameters:
    - origin: Origin node for the demand.
    - destination: Destination node for the demand.
    - fijvw: Flow variables.
    - xijv: Arc usage variables.
    - Vtotal: Total number of vehicles.
    - si: Indicator for transshipment nodes.
    - yi: Hub/transshipment activation variables.

    Returns:
    - True if a continuous path exists, False otherwise.
    """
    visited = set()  # Keep track of visited nodes
    stack = [(origin, None)]  # Stack for DFS: (current node, current vehicle)

    while stack:
        current_node, current_vehicle = stack.pop()

        # If we reach the destination, the path is valid
        if current_node == destination:
            return True

        # Skip already visited nodes or the depot (if not relevant)
        if current_node in visited:
            continue
        visited.add(current_node)

        # Check all possible outgoing arcs
        for j in range(len(xijv)):  # Assuming `xijv` has dimensions for all nodes
            for v in range(Vtotal):  # Loop over all vehicles
                if fijvw.get((current_node, j, v, w), 0) > 0.05:  # Check if flow exists
                    if current_vehicle is None or current_vehicle == v:
                        # Continue along the same vehicle
                        stack.append((j, v))
                    elif yi.get(current_node, 0) > 0.5:  # Change vehicle only at transshipment nodes
                        stack.append((j, v))

    # If we exit the loop without reaching the destination, the path is invalid
    return False

# Load instance data and solution from the .pkl file
def load_solution_and_check_feasibility(instance_data, solution):
    # Check if the solution exists in the file
    if 'solution' in solution and solution['solution']:
        # Run the feasibility check
        feasible, errors = check_feasibility(instance_data, solution['solution'])

        # Print results
        if feasible:
            print("Solution is feasible.")
        else:
            print("Solution is infeasible. Errors:")
            for error in errors:
                print(error)
    else:
        print("No valid solution found in the file.")