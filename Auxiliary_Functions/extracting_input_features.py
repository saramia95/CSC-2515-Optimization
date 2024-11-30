import pandas as pd
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)


def extract_input_features(instance_data, file_name):
    """
    Extract input features for each commodity based on the given instance data.
    
    Parameters:
    - instance_data: The instance data containing origin-destination information, demand, distances, etc.
    - file_name: The name of the instance file (used as the instance ID).
    
    Returns:
    - A DataFrame where each row corresponds to a commodity and the columns are the input features.
    """
    # Initialize the features list
    features = []

    # Extract relevant data from the instance
    ow = instance_data.ow  # Origin nodes for demands
    dw = instance_data.dw  # Destination nodes for demands
    qw = instance_data.qw  # Demand for each commodity
    od_distances = instance_data.od_dist_matrix  # Origin-destination distances
    V_small_total = instance_data.vcap[0]  # Capacity of small vehicles
    V_big_total = instance_data.vcap[1]  # Capacity of big vehicles
    v_cost_small = instance_data.FC[0]
    v_cost_big = instance_data.FC[1]
    unit_route_small = instance_data.OC[0]* instance_data.speed[0]
    unit_route_big = instance_data.OC[1]* instance_data.speed[1]

    # Compute global statistics
    nonzero_flows = [w for w, flow in enumerate(qw) if flow > 0]
    max_qw = max(qw)
    min_qw = min(q for q in qw if q > 0)
    avg_qw = sum(qw) / len(nonzero_flows)
    total_commodities_nonzero = len(nonzero_flows)

    print(qw)
    print(nonzero_flows)

    # Compute transshipment cost statistics for the entire network
    avg_transshipment_cost = sum(instance_data.Hubs_FC) / len(instance_data.Hubs_FC)
    max_transshipment_cost = max(instance_data.Hubs_FC)
    min_transshipment_cost = min(instance_data.Hubs_FC)

    print(ow)
    print(od_distances.shape)

    # Compute the distance statistics for the network:
    avg_distance = sum(od_distances[ow[i]-1,dw[i]-1] for i in nonzero_flows) / len(nonzero_flows)
    min_distance = min(od_distances[ow[i]-1,dw[i]-1] for i in nonzero_flows)
    max_distance = max(od_distances[ow[i]-1,dw[i]-1] for i in nonzero_flows)

    thresholds = {
        "avg": avg_distance,
        "avg_minus_10": avg_distance * 0.9,
        "avg_plus_10": avg_distance * 1.1,
        "avg_minus_30": avg_distance * 0.7,
        "avg_plus_30": avg_distance * 1.3,
        "avg_minus_50": avg_distance * 0.5,
        "avg_plus_50": avg_distance * 1.5
    }

    # Iterate over each commodity
    for w in nonzero_flows:  # Only consider non-zero demands
        origin = ow[w]-1
        destination = dw[w]-1
        od_distance = od_distances[origin,destination]
        
        commodities_with_same_origin = sum(
            1 for other_w in nonzero_flows
            if ow[other_w] == ow[w] and w != other_w
        )

        commodities_with_same_destination = sum(
            1 for other_w in nonzero_flows
            if dw[other_w] == dw[w] and w != other_w
        )

        for i in range(len(od_distances)):  # Loop over all nodes
            dist_to_origin = od_distances[ow[w]-1, i]
            dist_to_destination = od_distances[dw[w]-1,i]

        # Proximity counts for origin and destination under different thresholds
        proximity_counts_origin = {key: 0 for key in thresholds.keys()}
        proximity_counts_destination = {key: 0 for key in thresholds.keys()}
        
        for key, threshold in thresholds.items():
            if dist_to_origin <= threshold:
                proximity_counts_origin[key] += 1
            if dist_to_destination <= threshold:
                proximity_counts_destination[key] += 1

        # # Count commodities with the same OD distance
        # commodities_with_same_od_distance = sum(
        #     1 for other_w in nonzero_flows
        #     if od_distances[ow[other_w]][dw[other_w]] == od_distance
        # )

        # Transshipment costs for origin and destination
        transshipment_cost_origin = instance_data.Hubs_FC[ow[w] - 1]  # Subtract 1 for zero-based index
        transshipment_cost_destination = instance_data.Hubs_FC[dw[w] - 1]

        # Relative transshipment costs
        relative_transshipment_cost_origin_to_max = transshipment_cost_origin / max_transshipment_cost
        relative_transshipment_cost_origin_to_min = transshipment_cost_origin / min_transshipment_cost
        relative_transshipment_cost_origin_to_avg = transshipment_cost_origin / avg_transshipment_cost

        relative_transshipment_cost_destination_to_max = transshipment_cost_destination / max_transshipment_cost
        relative_transshipment_cost_destination_to_min = transshipment_cost_destination / min_transshipment_cost
        relative_transshipment_cost_destination_to_avg = transshipment_cost_destination / avg_transshipment_cost
        
        # Features for the current commodity
        feature_row = {
            "Instance ID": file_name,  # Use the file name as the instance ID
            "Commodity ID": w,
            "OD Distance": od_distance,
            "Max OD Distance": max_distance,
            "Min OD Distance": min_distance,
            "Avg OD Distance": avg_distance,
            "Total # Commodities in Instance": total_commodities_nonzero,
            "Total Flow (sum qw) in Instance": sum(qw),
            "Max Size (qw)": max_qw,
            "Min Size (qw)": min_qw,
            "Capacity of Small Vehicles": V_small_total,
            "Capacity of Big Vehicles": V_big_total,
            "Cost of Small Vehicles": v_cost_small,
            "Cost of Big Vehicles": v_cost_big,

            "Unit Routing cost small vehicles": unit_route_small,
            "Unit Routing cost big vehicles": unit_route_big,

            "Direct o-d routing cost small vehicle": od_distance* unit_route_small,

            "Direct o-d routing cost big vehicle": od_distance* unit_route_big,

            "Avg Transshipment Cost of All Nodes": avg_transshipment_cost,
            "Max Transshipment Cost of All Nodes": max_transshipment_cost,
            "Min Transshipment Cost of All Nodes": min_transshipment_cost,

            "Demand Size (qw)": qw[w],

            "Total # Commodities with Same Origin": commodities_with_same_origin,
            "Total # Commodities with Same Destination": commodities_with_same_destination,

            "Relative Demand Size to Max": qw[w] / max_qw,
            "Relative Demand Size to Min": qw[w] / min_qw,
            "Relative Demand Size to Total ": qw[w]/ sum(qw),
            "Relative Demand size to small v cap":  qw[w]/V_small_total,
            "Relative Demand size relative to big v cap":  qw[w]/V_big_total,

            "Relative Distance to Max": od_distances[ow[w]-1,dw[w]-1] /max_distance,
            "Relative Distance to Min": od_distances[ow[w]-1,dw[w]-1] /min_distance,
            "Relative Distance to Avg": od_distances[ow[w]-1,dw[w]-1] /avg_distance,

            
            "Relative Transshipment Cost Origin to Max": relative_transshipment_cost_origin_to_max,
            "Relative Transshipment Cost Origin to Min": relative_transshipment_cost_origin_to_min,
            "Relative Transshipment Cost Origin to Avg": relative_transshipment_cost_origin_to_avg,
            "Relative Transshipment Cost Destination to Max": relative_transshipment_cost_destination_to_max,
            "Relative Transshipment Cost Destination to Min": relative_transshipment_cost_destination_to_min,
            "Relative Transshipment Cost Destination to Avg": relative_transshipment_cost_destination_to_avg,
            
            "Relative # Commodities with Same Origin": commodities_with_same_origin/len(nonzero_flows),
            "Relative  # Commodities with Same Destination": commodities_with_same_destination/len(nonzero_flows),

            # "Routing Cost of o-d": 

        }

        # Add proximity counts to the feature dictionary
        for key in thresholds.keys():
            feature_row[f"Nodes Close to Origin ({key})"] = proximity_counts_origin[key]
            feature_row[f"Nodes Close to Destination ({key})"] = proximity_counts_destination[key]
            # Add relative columns
            feature_row[f"Relative Nodes Close to Origin ({key})"] = proximity_counts_origin[key] / len(nonzero_flows)
            feature_row[f"Relative Nodes Close to Destination ({key})"] = proximity_counts_destination[key] / len(nonzero_flows)

        # Add features to the list
        features.append(feature_row)
    
    # Convert to a pandas DataFrame
    features_df = pd.DataFrame(features)
    return features_df