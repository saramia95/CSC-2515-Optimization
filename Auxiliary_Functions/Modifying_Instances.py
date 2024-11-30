import os
import sys

# Add the parent directory (project root) to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from Auxiliary_Functions.Reading_Instances import read_instance_from_dat
from Auxiliary_Functions.Reading_Instances import InstanceData
import numpy as np
import random


def save_instance_to_file(data, file_path):
    """
    Save the modified InstanceData back to a .dat file.
    
    Parameters:
    - data: InstanceData object to save.
    - file_path: Path to the output file.
    """
    with open(file_path, 'w') as file:
        # Write vehicle data
        file.write(f"{data.Vtyp}\n")
        for i in range(data.Vtyp):
            file.write(f"{data.vcap[i]} {data.speed[i]} {data.OC[i]} {data.FC[i]} {data.Vind[i]}\n")
        
        # Write node data
        file.write(f"{data.S}\n")
        for fc in data.Hubs_FC:
            file.write(f"{fc}\n")
        for x, y in zip(data.Hub_x, data.Hub_y):
            file.write(f"{x} {y}\n")
        
        # Write demand data
        for ow, dw, qw, od in zip(data.ow, data.dw, data.qw, data.od_dist):
            file.write(f"{ow} {dw} {qw} {od}\n")

def modify_flow(data, percentage):
    """
    Modify the flow data to match a given percentage by randomly selecting destinations for each origin.
    
    Parameters:
    - data: InstanceData object containing the demand data.
    - percentage: Percentage of flow to retain (e.g., 10, 20, ... 90).
    
    Returns:
    - modified_data: A new InstanceData object with modified flow data.
    """
    S = data.S  # Number of nodes
    total_pairs = S * S

    # Reshape qw into S x S matrix for easier manipulation
    qw_matrix = np.array(data.qw).reshape(S, S)

    # Set self-loops to zero
    np.fill_diagonal(qw_matrix, 0)

    # Determine how many destinations to keep per origin
    num_to_keep = int(S * (percentage / 100.0))
    
    # Randomly modify flows
    for i in range(S):
        destinations = list(range(S))
        destinations.remove(i)  # Exclude self-loops
        
        # Randomly select destinations to keep
        keep = random.sample(destinations, num_to_keep)
        
        # Set flows to zero for non-selected destinations
        for j in destinations:
            if j not in keep:
                qw_matrix[i, j] = 0

    # Flatten modified flow matrix back into the qw list
    modified_qw = qw_matrix.flatten().tolist()

    # Create a modified InstanceData object
    modified_data = InstanceData()
    modified_data.__dict__.update(data.__dict__)  # Copy original data
    modified_data.qw = modified_qw  # Replace qw with modified flows

    return modified_data



def batch_modify_and_save(file_names, output_folder):
    """
    Modify and save multiple files with different flow percentages (10%-90%).
    
    Parameters:
    - file_names: List of input .dat file paths to process.
    - output_folder: Root folder where subfolders for each file will be created.
    """
    percentages = [10, 20, 30, 40, 50, 60, 70, 80, 90]  # Flow percentages to apply

    # Ensure the root output folder exists
    os.makedirs(output_folder, exist_ok=True)

    for file_name in file_names:
        # Parse the original file
        sample_data = read_instance_from_dat(file_name)
        
        # Extract base name (without extension) for subfolder creation
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        
        # Create a subfolder for the current file
        file_output_folder = os.path.join(output_folder, base_name)
        os.makedirs(file_output_folder, exist_ok=True)

        print(f"Processing {file_name}, saving results in {file_output_folder}")
        
        for perc in percentages:
            # Modify flow for the current percentage
            modified_data = modify_flow(sample_data, perc)

            # Construct the output file name
            output_file_name = os.path.join(file_output_folder, f"{base_name}_{perc}perc.dat")
            
            # Save the modified data to the file
            save_instance_to_file(modified_data, output_file_name)
            print(f"Saved {perc}% flow modification to {output_file_name}")

def modify_hub_costs(data, percentage):
    """
    Modify hub costs to reduce them by a specified percentage.
    
    Parameters:
    - data: InstanceData object containing the hub data.
    - percentage: Percentage by which to reduce the hub costs (e.g., 1, 5, 10, ... 50).
    
    Returns:
    - modified_data: A new InstanceData object with modified hub costs.
    """
    # Calculate the reduction factor
    reduction_factor = (percentage) / 100.0

    # Apply the reduction to each hub cost
    modified_hubs_fc = [fc * reduction_factor for fc in data.Hubs_FC]

    # Create a modified InstanceData object
    modified_data = InstanceData()
    modified_data.__dict__.update(data.__dict__)  # Copy original data
    modified_data.Hubs_FC = modified_hubs_fc  # Replace Hubs_FC with modified values

    return modified_data

def batch_modify_hub_costs_and_save(file_names, output_folder):
    """
    Modify and save multiple files with different hub cost percentages (1%-50%).
    
    Parameters:
    - file_names: List of input .dat file paths to process.
    - output_folder: Root folder where subfolders for each file will be created.
    """
    percentages = [1, 5, 10, 20, 30, 40, 50]  # Hub cost reduction percentages

    # Ensure the root output folder exists
    os.makedirs(output_folder, exist_ok=True)

    for file_name in file_names:
        # Parse the original file
        sample_data = read_instance_from_dat(file_name)
        
        # Extract base name (without extension) for subfolder creation
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        
        # Create a subfolder for the current file
        file_output_folder = os.path.join(output_folder, f"{base_name}_HubCosts")
        os.makedirs(file_output_folder, exist_ok=True)

        print(f"Processing {file_name} for hub cost reductions, saving results in {file_output_folder}")
        
        for perc in percentages:
            # Modify hub costs for the current percentage
            modified_data = modify_hub_costs(sample_data, perc)

            # Construct the output file name
            output_file_name = os.path.join(file_output_folder, f"{base_name}_HubCosts_{perc}perc.dat")
            
            # Save the modified data to the file
            save_instance_to_file(modified_data, output_file_name)
            print(f"Saved {perc}% hub cost reduction to {output_file_name}")