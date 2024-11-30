import os
import random
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from Auxiliary_Functions.Reading_Instances import read_instance_from_dat
from Auxiliary_Functions.Modifying_Instances import (
    modify_flow,
    modify_hub_costs,
    save_instance_to_file,
)

def generate_instances(input_folder, output_folder, modify_flow_only=False, modify_hub_costs_only=False, modify_both=True):
    """
    Generate modified instances from .dat files in the input folder and save them to appropriate subfolders.
    
    Parameters:
    - input_folder: Path to the folder containing the original .dat files.
    - output_folder: Path to the root folder for saving modified files.
    - modify_flow_only: If True, only modify flows.
    - modify_hub_costs_only: If True, only modify hub costs.
    - modify_both: If True, first modify flows, then apply hub cost changes to the flow-modified files.
    """
    # Ensure output subfolders exist
    flow_folder = os.path.join(output_folder, "Flow Modifications")
    hub_cost_folder = os.path.join(output_folder, "Hub Cost Modifications")
    both_folder = os.path.join(output_folder, "BOTH")
    os.makedirs(flow_folder, exist_ok=True)
    os.makedirs(hub_cost_folder, exist_ok=True)
    os.makedirs(both_folder, exist_ok=True)

    # List all .dat files in the input folder
    input_files = [
        os.path.join(input_folder, f)
        for f in os.listdir(input_folder)
        if f.endswith(".dat")
    ]

    if not input_files:
        print("No .dat files found in the input folder.")
        return

    print(f"Found {len(input_files)} files to process.")
    
    percentages_flow = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    percentages_hub = [1, 5, 10, 20, 30, 40, 50]

    for file_path in input_files:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        print(f"Processing {base_name}.dat")

        # Read instance data
        data = read_instance_from_dat(file_path)

        if not modify_hub_costs_only:
            # Modify flows and save in "Flow Modifications"
            for perc in percentages_flow:
                modified_data = modify_flow(data, perc)
                output_file = os.path.join(
                    flow_folder, f"{base_name}_Flow_{perc}perc.dat"
                )
                save_instance_to_file(modified_data, output_file)
                print(f"Saved {perc}% flow modification to {output_file}")

                # If modifying both, apply hub cost modifications to flow-modified data
                if modify_both:
                    for hub_perc in percentages_hub:
                        both_modified_data = modify_hub_costs(modified_data, hub_perc)
                        both_output_file = os.path.join(
                            both_folder, f"{base_name}_Flow_{perc}perc_HubCosts_{hub_perc}perc.dat"
                        )
                        save_instance_to_file(both_modified_data, both_output_file)
                        print(f"Saved BOTH (Flow {perc}%, HubCosts {hub_perc}%) to {both_output_file}")

        if not modify_flow_only and not modify_both:
            # Modify hub costs and save in "Hub Cost Modifications"
            for perc in percentages_hub:
                modified_data = modify_hub_costs(data, perc)
                output_file = os.path.join(
                    hub_cost_folder, f"{base_name}_HubCosts_{perc}perc.dat"
                )
                save_instance_to_file(modified_data, output_file)
                print(f"Saved {perc}% hub cost reduction to {output_file}")


if __name__ == "__main__":
    # Define input and output folders
    input_folder = "DATA/Luisa Data"  # Folder containing .dat files
    output_folder = "DATA/Modified"  # Root folder for modified files

    random = 54321

    # Choose what to modify
    modify_flow_only = False
    modify_hub_costs_only = False

    # Generate modified instances
    generate_instances(
        input_folder, output_folder, modify_flow_only, modify_hub_costs_only
    )
