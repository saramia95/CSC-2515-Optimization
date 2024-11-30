import numpy as np
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

class InstanceData:
    """Class to hold all extracted parameters."""
    def __init__(self):
        self.BIGM = None
        self.Vtyp = None
        self.S = None
        #VEHICLES
        self.vcap = []
        self.speed = []
        # Operating cost per Vehicle Type
        self.OC = []
        # Fixed cost per Vehicle Type
        self.FC = []
        # Indices of vehicle types
        self.Vind = []
        # Hubs:
        self.Hubs_FC = []
        self.Hub_x = []
        self.Hub_y = []
        # DEMAND
        self.W = None
        self.ow = []
        self.dw = []
        self.qw = []
        self.od_dist = []

        self.od_dist_matrix= []

def read_instance_from_dat(file_path):
    """Parse the .dat file and populate InstanceData."""
    data = InstanceData()
    
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    line_idx = 0

    # Parse Vtyp
    data.Vtyp = int(lines[line_idx].strip())
    line_idx += 1

    # Parse vehicle parameters
    for _ in range(data.Vtyp):
        params = lines[line_idx].strip().split()
        data.vcap.append(float(params[0]))
        data.speed.append(float(params[1]))
        data.OC.append(float(params[2]))
        data.FC.append(float(params[3]))
        data.Vind.append(int(params[4]))
        line_idx += 1

    # Parse number of nodes (S)
    data.S = int(lines[line_idx].strip())
    line_idx += 1

    # Parse hub fixed costs
    for _ in range(data.S):
        data.Hubs_FC.append(float(lines[line_idx].strip()))
        line_idx += 1

    # Parse hub coordinates
    for _ in range(data.S):
        coords = lines[line_idx].strip().split()
        data.Hub_x.append(float(coords[0]))
        data.Hub_y.append(float(coords[1]))
        line_idx += 1

    # Calculate W = S * S
    data.W = data.S * data.S

    # Parse demand matrix (ow, dw, qw, od_dist)
    while line_idx < len(lines):
        row = lines[line_idx].strip().split()
        data.ow.append(int(row[0]))
        data.dw.append(int(row[1]))
        data.qw.append(float(row[2]))
        data.od_dist.append(float(row[3]))
        line_idx += 1
    
    S = data.S  # Number of nodes
    data.od_dist_matrix = np.array(data.od_dist).reshape(S, S)

    return data
