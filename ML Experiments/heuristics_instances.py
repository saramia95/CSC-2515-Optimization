import os
import pandas as pd
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from Auxiliary_Functions.Reading_Instances import read_instance_from_dat
from Auxiliary_Functions.extracting_input_features import extract_input_features

def process_instances_and_save_combined(instance_files, data_folders, output_file):
    """
    Process instance files by extracting ML input features for all commodities and saving them into one combined file.
    
    Parameters:
    - instance_files: List of instance file names to process (e.g., ['file.dat']).
    - data_folders: List of folders to search for instance files (in order).
    - output_file: Path to the combined output CSV file.
    """
    combined_features = []  # List to hold features for all instances and commodities

    for idx, instance_file in enumerate(instance_files, start=1):
        print(f"Processing instance {idx}: {instance_file}")

        # Search for the instance file in the data folders
        instance_path = None
        for folder in data_folders:
            potential_path = os.path.join(folder, instance_file)
            if os.path.isfile(potential_path):
                instance_path = potential_path
                break

        if instance_path is None:
            print(f"Error: Instance file '{instance_file}' not found in any data folder.")
            continue

        print(f"Found instance file at: {instance_path}")

        # Load instance data
        instance_data = read_instance_from_dat(instance_path)

        # Extract only the file name (without the full path) to use as the Instance ID
        instance_name = os.path.splitext(instance_file)[0]

        # Extract input features
        input_features_df = extract_input_features(instance_data, instance_name)

        # Append the features for the current instance to the combined list
        combined_features.append(input_features_df)

    # Combine all extracted features into a single DataFrame
    if combined_features:
        combined_df = pd.concat(combined_features, ignore_index=True)

        # Save the combined DataFrame to a CSV file
        combined_df.to_csv(output_file, index=False)
        print(f"Combined input features saved to: {output_file}")
    else:
        print("No features extracted. Combined file not created.")


if __name__ == "__main__":
    # List of instance files to process
    instance_files = [
        # Add more files here as needed
        '8R-alpha=021_Flow_50perc_HubCosts_5perc.dat',
        '8R-alpha=021_Flow_60perc_HubCosts_5perc.dat',
        '8R-alpha=021_Flow_50perc_HubCosts_20perc.dat',
        '8R-alpha=021_Flow_60perc_HubCosts_20perc.dat',
        '9R-alpha=021_Flow_50perc_HubCosts_5perc.dat',
        '9R-alpha=021_Flow_60perc_HubCosts_5perc.dat',
        '9R-alpha=021_Flow_50perc_HubCosts_20perc.dat',
        '9R-alpha=021_Flow_60perc_HubCosts_20perc.dat',
    ]

    # List of folders to search for instance files
    data_folders = [
        'DATA/Luisa Data',
        'DATA/Modified/Flow Modifications',
        'DATA/Modified/Hub Cost Modifications',
        'DATA/Modified/BOTH',
    ]

    # Path to the combined output file
    combined_output_file = 'ML Experiments/ML Input Data/combined_input_features.csv'

    # Process the instances and save combined results
    process_instances_and_save_combined(instance_files, data_folders, combined_output_file)

