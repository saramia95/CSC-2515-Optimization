# %%
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import networkx as nx
import matplotlib.pyplot as plt
import pickle
import math
import os
import sys

# current_dir = os.path.dirname(os.path.abspath(__file__))
current_dir = os.getcwd()
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from Auxiliary_Functions.Reading_Instances import read_instance_from_dat
from MIP_Models.MIP import solve_flow_aware_location_decisions, solve_all_or_routing_decisions
from MIP_Models.MIPs import solve_location_decisions, solve_routing_decisions
from Auxiliary_Functions.extracting_solution_features import extract_OFV_solution_features



# %%
def main(data_folders, ml_input_file, heuristic_output_folder):
    # Load the ML combined input file
    try:
        ml_combined_data = pd.read_csv(ml_input_file)
    except FileNotFoundError:
        print(f"Error: File '{ml_input_file}' not found. Please check the path.")
        return

    # Extract unique instance IDs
    unique_instance_ids = ml_combined_data["Instance ID"].unique()

    # Create heuristic output folder if it doesn't exist
    os.makedirs(heuristic_output_folder, exist_ok=True)

    # Dynamically create the output file name based on the input file
    input_csv_name = os.path.basename(ml_input_file)
    output_csv_name = f"Heuristic_output_{input_csv_name}"
    output_file = os.path.join(heuristic_output_folder, output_csv_name)

    # Define CSV column structure
    columns = [
        "Instance ID", "use_ml_guidance", "use_location_first", "use_ML_direct", "use_ML_transhipment",
        "ML_Optimization status", "ML_Optimality Gap", "ML_OFV - Total Costs", "ML_Total Solving Time",
        "Stage 1 Feasibility", "Stage 2 Feasibility"
    ]

    # Create the output file if it doesn’t exist
    if not os.path.exists(output_file):
        pd.DataFrame(columns=columns).to_csv(output_file, index=False)

    # Define all configurations for solving
    configurations = [
        (False, False, False, False),# No ML guidance, no location first
        # (False, True, False, False),# No ML guidance, location first**
        (True, False, True, True),  # ML-guided (both, no location first)
        (True, False, True, False), # ML-guided (direct only, no location first)
        (True, False, False, True), # ML-guided (transshipment only, no location first)
        # (True, True, True, False),   # ML-guided (direct only, location first)**
        # (True, True, False, True),  # ML-guided (transshipment only, location first)**
        # (True, True, True, True),   # ML-guided (both, location first)**
    ]

    # Loop through each instance
    for instance_id in unique_instance_ids:
        # Search for the instance file in the data folders
        instance_file = None
        for folder in data_folders:
            potential_path = os.path.join(folder, f"{instance_id}.dat")
            if os.path.isfile(potential_path):
                instance_file = potential_path
                break

        if instance_file is None:
            print(f"Instance file '{instance_id}.dat' not found in any data folder.")
            continue

        print(f"Processing instance: {instance_id}")

        # Load instance data
        instance_data = read_instance_from_dat(instance_file)

        # Filter ML data for the current instance
        ml_data = ml_combined_data[ml_combined_data["Instance ID"] == instance_id]

        # Loop through each configuration
        for use_ml_guidance, use_location_first, use_ML_direct, use_ML_transhipment in configurations:
            # Ensure at least one of use_ML_direct or use_ML_transhipment is True if use_ml_guidance is True
            if use_ml_guidance and not (use_ML_direct or use_ML_transhipment):
                print("Skipping invalid configuration.")
                continue

            print(f"Configuration: use_ml_guidance={use_ml_guidance}, use_location_first={use_location_first}, "
                  f"use_ML_direct={use_ML_direct}, use_ML_transhipment={use_ML_transhipment}")

            fixed_hubs = []  # Default value if not solving location decisions
            stage1_status = "Not Solved"
            stage2_status = "Not Solved"
            optimization_status = None
            optimality_gap = None
            objective_value = None
            solving_time = None

            # Stage 1: Solve flow-aware location decisions
            if use_location_first:
                print("Solving location decisions...")
                fixed_hubs,sln_count,flag = solve_location_decisions(instance_data, ml_data, use_ml_guidance,use_ML_direct, use_ML_transhipment)
                if sln_count > 0:
                    stage1_status = "Feasible"
                elif not flag:
                    stage1_status = "Feasible-Not Solved"
                    
                elif sln_count == 0 and flag:
                    stage1_status = "Infeasible"
                
            else:
                print("Skipping location decisions... Using all hubs as candidates.")
                fixed_hubs = list(range(1, int(instance_data.S) + 1))  # Use all hubs as candidates
                stage1_status = "Skipped"

            # Stage 2: Solve routing decisions
            try:
                print("Solving routing decisions...")
                result = solve_routing_decisions(
                    instance_data, ml_data, fixed_hubs, use_ml_guidance, use_location_first, use_ML_direct, use_ML_transhipment
                )

                if result['status'] in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
                    stage2_status = "Feasible"
                    optimization_status = "Optimal" if result['status'] == GRB.OPTIMAL else "Time Limit"
                    optimality_gap = result.get("optimality_gap", None)
                    objective_value = result.get("objective_value", None)
                    solving_time = result.get("total_solving_time", None)

                else:
                    stage2_status = "Infeasible"
                    optimization_status = "Infeasible"

            except Exception as e:
                print(f"Error in Stage 2: {e}")
                stage2_status = "Error"
                optimization_status = "Error"

            # Create a row of results
            result_row = {
                "Instance ID": instance_id,
                "use_ml_guidance": use_ml_guidance,
                "use_location_first": use_location_first,
                "use_ML_direct": use_ML_direct,
                "use_ML_transhipment": use_ML_transhipment,
                "ML_Optimization status": optimization_status,
                "ML_Optimality Gap": optimality_gap,
                "ML_OFV - Total Costs": objective_value,
                "ML_Total Solving Time": solving_time,
                "Stage 1 Feasibility": stage1_status,
                "Stage 2 Feasibility": stage2_status
            }

            # Append to the CSV
            pd.DataFrame([result_row]).to_csv(output_file, mode='a', header=False, index=False)

            print(f"Saved configuration result for instance: {instance_id}")

    print(f"All results saved to {output_file}")


# %%
if __name__ == "__main__":
    # Define data folders to search for instance files
    data_folders = [
        "DATA/Luisa Data",
        "DATA/Modified/Flow Modifications",
        "DATA/Modified/Hub Cost Modifications",
        "DATA/Modified/BOTH",
    ]

    # Path to the ML combined output file
    ml_input_file = "ML Experiments/XG_BOOST Predictions/ML_combined_output_features_1.csv"

    # Path to the heuristic output folder
    heuristic_output_folder = "ML Experiments/Heuristic Results"

    # Run the main function
    main(data_folders, ml_input_file, heuristic_output_folder)

