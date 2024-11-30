import networkx as nx
import matplotlib.pyplot as plt
import math

'''
Extracting path and plotting path for a commodity
(Visuals if needed)
'''

def plot_commodity_paths (instance_data, solution):
    # Extract parameters
    fijvw = solution['solution']['fijvw']
    yi = solution['solution']['yi']
    Vtotal = len(solution['solution']['av'])  # Total vehicles
    ow = instance_data.ow  # Origin nodes for demands
    dw = instance_data.dw  # Destination nodes for demands
    qw = instance_data.qw
    nonzero_flows = [w for w, flow in enumerate(qw) if flow > 0]

    # Create node coordinates (adjusted for offset)
    node_coords = {i + 1: (instance_data.Hub_x[i], instance_data.Hub_y[i]) for i in range(len(instance_data.Hub_x))}
    node_coords[0] = (0, 0)  # Assuming depot coordinates are (0, 0), adjust if needed

    # Set up the figure for multiple plots
    num_commodities = len(nonzero_flows)
    cols = 8 # 3 plots per row
    rows = math.ceil(num_commodities / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(12, rows * 3))
    axes = axes.flatten()

    for idx, w in enumerate(nonzero_flows):
        path = extract_path(w, ow[w], dw[w], fijvw, Vtotal)
        if path:
            plot_path(axes[idx], path, node_coords, yi, title=f"Commodity {w}")
        else:
            axes[idx].axis('off')  # Turn off the axis if no path exists

    # Turn off remaining axes
    for idx in range(num_commodities, len(axes)):
        axes[idx].axis('off')

    plt.tight_layout()
    plt.show()

def extract_path(w, origin, destination, fijvw, Vtotal):
    """
    Extract the path for a given commodity.

    Parameters:
    - w: Demand index.
    - origin: Origin node for the demand.
    - destination: Destination node for the demand.
    - fijvw: Flow variables from the solution.
    - Vtotal: Total number of vehicles.

    Returns:
    - List of tuples representing the path [(i, j, v), ...].
    """
    path = []
    current_node = origin
    current_vehicle = None
    visited = set()

    while current_node != destination:
        visited.add(current_node)
        found_next = False

        for j in range(len(fijvw)):  # Loop over all destination nodes
            for v in range(Vtotal):  # Loop over all vehicles
                if fijvw.get((current_node, j, v, w), 0) == 1:  # If flow exists
                    if current_vehicle is None or current_vehicle == v:
                        # Append the edge with vehicle info to the path
                        path.append((current_node, j, v))
                        current_node = j
                        current_vehicle = v
                        found_next = True
                        break
            if found_next:
                break

        if not found_next:
            # No valid path found
            return None

    return path

def plot_path(ax, path, node_coords, yi, title="Path for Commodity"):
    """
    Plot the path for a commodity on a given axis.

    Parameters:
    - ax: Matplotlib axis to plot on.
    - path: List of edges [(i, j, v), ...] with vehicle numbers.
    - node_coords: Dictionary of node coordinates {node: (x, y)}.
    - yi: Dictionary of transshipment activation {node: 1/0}.
    - title: Title for the subplot.
    """
    G = nx.DiGraph()
    edge_labels = {}

    for i, j, v in path:
        G.add_edge(i, j)
        edge_labels[(i, j)] = f"V{v}"  # Label with vehicle number

    # Extract positions from node_coords
    pos = {node: node_coords[node] for node in G.nodes()}

    # Highlight transshipment nodes in yellow
    node_colors = ["yellow" if yi.get(node, 0) > 0.5 else "lightblue" for node in G.nodes()]

    nx.draw(G, pos, ax=ax, with_labels=True, node_color=node_colors,
            node_size=500, font_size=10, font_weight="bold")
    nx.draw_networkx_edge_labels(G, pos, ax=ax, edge_labels=edge_labels, font_size=8)

    ax.set_title(title)
