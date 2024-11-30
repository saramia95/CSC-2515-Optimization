import pandas as pd
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

'''
Extracting solution features:
'''
def count_shared_arcs(w, fijvw, total_nodes, od_distances, Vtotal, nonzero_flows):
    """
    Count the number of arcs and their total length shared with other commodities.

    Parameters:
    - w: Commodity index to analyze.
    - fijvw: Flow variables from the solution.
    - total_nodes: Total number of nodes.
    - Vtotal: Total number of vehicles.
    - nonzero_flows: List of non-zero demand commodities.

    Returns:
    - shared_arcs_count: Total number of arcs shared with other commodities.
    - shared_arcs_length: Total length of shared arcs.
    """
    shared_arcs_count = 0
    shared_arcs_length = 0
    # od_distances = instance_data.od_dist_matrix  # Use the OD distance matrix

    # Loop over all arcs (i, j) and vehicles (v) for the given commodity (w)
    for i in range(1,total_nodes):
        for j in range(1,total_nodes):
            if i != j:  # Exclude self-loops
                for v in range(Vtotal):
                    if fijvw.get((i, j, v, w), 0) == 1:  # Arc is used by commodity w
                        # Check if this arc is shared with other commodities
                        shared_by_others = False
                        for other_w in nonzero_flows:
                            if other_w != w and fijvw.get((i, j, v, other_w), 0) > 0:
                                shared_by_others = True
                                break

                        if shared_by_others:
                            shared_arcs_count += 1
                            shared_arcs_length += od_distances[i-1][j-1]

    return shared_arcs_count, shared_arcs_length



def extract_solution_features(instance_data, full_solution, file_name):
    """
    Add solution-based features to the input feature table.
    """
    solution = full_solution['solution']
    features = []

    fijvw = solution['fijvw']
    xijv = solution['xijv']
    av = solution['av']
    yi = solution['yi']

    # Instance data
    ow = instance_data.ow  # Origins
    dw = instance_data.dw  # Destinations
    qw = instance_data.qw  # Demands
    od_distances = instance_data.od_dist_matrix
    operational_costs = instance_data.OC  # Operational costs
    speeds = instance_data.speed  # Speeds
    V_small_total = instance_data.Vind[0]
    V_big_total = instance_data.Vind[1]
    total_commodities_nonzero = sum(1 for flow in qw if flow > 0)
    total_nodes = instance_data.S + 1

    # Identify non-zero commodities
    nonzero_flows = [w for w in range(len(qw)) if qw[w] > 0]

 

    for w in range (len(qw)):
        if qw[w] > 0:

            origin = ow[w]
            destination = dw[w]

            # Determine vehicles used for the commodity
            small_vehicles_used = 0
            big_vehicles_used = 0
            total_vehicles_used = 0
            nodes_with_vehicle_change = set()
            route_arcs = []
            total_route_length = 0 
          

            current_vehicle = None
            current_node = origin
            visited_states = set()  # Track (node, vehicle) pairs to prevent infinite loops

            while current_node != destination:
                found_next = False

                for j in range(1, total_nodes):  # Loop over all destination nodes
                    if found_next:
                        break  # Exit early if the next node has already been found

                    for v in range(V_small_total + V_big_total):  # Loop over all vehicles
                        if av[v] == 1:  # Check if vehicle v is active
                            if fijvw.get((current_node, j, v, w), 0) > 0:  # Flow exists on this arc for vehicle v and commodity w
                                 # Prevent revisiting the same (node, vehicle) state
                                if (j, v) in visited_states:
                                    continue

                                if current_vehicle is None:
                                    # Assign the current vehicle if not already assigned
                                    current_vehicle = v
                                elif current_vehicle != v:
                                    #Vehicle change detected
                                    nodes_with_vehicle_change.add(current_node)
                                    current_vehicle = v  # Update the current vehicle to the new one

                                # Record the arc
                                route_arcs.append((current_node, j))
                                total_route_length += od_distances[current_node - 1][j - 1]

                                # Mark the current state as visited
                                visited_states.add((j, v))

                                # Update the current node
                                current_node = j
                                found_next = True
                                break

                if not found_next:
                    raise ValueError(f"No valid path found from node {current_node} to destination {destination} for commodity {w}.")


            # Number of  vehicles used for commodity 

            # Vehicle usage counts
            small_vehicles_used = sum(1 for v in range(V_small_total) if any(fijvw.get((i, j, v, w), 0) > 0 for i in range(total_nodes) for j in range(total_nodes)))
            big_vehicles_used = sum(1 for v in range(V_small_total, V_small_total + V_big_total) if any(fijvw.get((i, j, v, w), 0) > 0 for i in range(total_nodes) for j in range(total_nodes)))
            total_vehicles_used = small_vehicles_used + big_vehicles_used

            # Check for shared arcs
            shared_arcs_count, shared_arcs_length = count_shared_arcs(w, fijvw, total_nodes, od_distances, V_big_total+ V_small_total, nonzero_flows)


            # If a commodity changes vehicles then I want to store the nodes where it changed vehicles

            # Mode of delivery (if 1 vehicle should be direct) if more then transhipped
            mode_of_delivery = "Direct" if total_vehicles_used == 1 else "Transshipment"
            
            #  Number of arcs between orgin and destination (length of route)
            number_of_arcs = len(route_arcs)

            # is origin a hub
            is_origin_hub = yi.get(origin, 0)
            is_destination_hub = yi.get(destination, 0)

              # Add features for this commodity
            features.append({
                "Instance ID": file_name,  # Use the file name as the instance ID
                "Optimization status": full_solution['status'],
                "Optimality Gap": full_solution['optimality_gap'],
                "OFV - Total Costs": full_solution['objective_value'],
                "Time to first feasible solution ": full_solution['time_to_first_feasible'],
                "Total Solving Time ": full_solution['total_solving_time'],
                "Commodity ID": w,
                "Number of Small Vehicles Used": small_vehicles_used,
                "Number of Big Vehicles Used": big_vehicles_used,
                "Total Number of Vehicles Used": total_vehicles_used,
                "Nodes with Vehicle Change": list(nodes_with_vehicle_change),
                "Mode of Delivery": mode_of_delivery,
                "Number of Arcs (Route Length)": number_of_arcs,
                "Total Route Length (Units)": total_route_length,
                "Is Origin Hub": is_origin_hub,
                "Is Destination Hub": is_destination_hub,
                "Number of Shared Arcs": shared_arcs_count,
                "Total Length of Shared Arcs (Units)": shared_arcs_length,
            })
    return features


def extract_OFV_solution_features(instance_data, full_solution, file_name):
    """
    Add solution-based features to the input feature table.
    """
    solution = full_solution['solution']
    # Extract only the file name (without the full path)
    instance_name = os.path.basename(file_name)

    features = []
    # Add features for this commodity
    features.append({
        "Instance ID": instance_name,  # Use the file name as the instance ID
        "ML_Optimization status": full_solution['status'],
        "ML_Optimality Gap": full_solution['optimality_gap'],
        "ML_OFV - Total Costs": full_solution['objective_value'],
        "ML_Total Solving Time": full_solution['total_solving_time'],
    })
             
    return features