
import networkx as nx
import gurobipy as gp
from gurobipy import GRB
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

"""
MIP FUNCTIONS (To solve optimization problem):
"""

# Define functions for subtour detection and elimination
def build_graph(solution, N, v, threshold=0.005):
    """
    Build a graph for a specific vehicle from the current solution.
    Nodes are connected if xijv > threshold for vehicle v.
    """
    G = nx.Graph()
    for i in range(N):
        for j in range(N):
            if i != j and solution[i, j, v] > threshold:
                G.add_edge(i, j)
    return G

def find_subtours(G):
    """
    Find all connected components (subtours) in the graph.
    """
    components = [list(component) for component in nx.connected_components(G)]
    return [comp for comp in components if len(comp) < nx.number_of_nodes(G)]

def subtour_elimination_callback(model, where):
    """
    Callback function to dynamically add subtour elimination constraints and reverse arc constraints,
    with limits on the number of constraints per vehicle and total constraints per callback.
    """
    if where == GRB.Callback.MIPSOL:
        # Extract current solution
        solution_av = model.cbGetSolution(model._av)
        solution_xijv = model.cbGetSolution(model._xijv)
        solution_zvi = model.cbGetSolution(model._Zvi)

        all_subtours_resolved = True
        total_constraints_added = 0  # Track total constraints added

        for v in range(model._Vtotal):  # Loop over vehicles
            if total_constraints_added >= 10:  # Stop if total constraints limit is reached
                break

            if solution_av[v] > 0.05:  # If vehicle v is active
                vehicle_constraints_added = 0  # Track constraints for this vehicle

                # Reverse Arc Constraint
                for i in range(1, model._N):
                    for j in range(1, model._N):
                        if i != j and solution_xijv[i, j, v] > 0.05 and solution_xijv[j, i, v] > 0.05:
                            # Add constraint to prevent both xij and xji being 1
                            model.cbLazy(model._xijv[i, j, v] + model._xijv[j, i, v] <= 1)
                            all_subtours_resolved = False
                            vehicle_constraints_added += 1
                            total_constraints_added += 1

                            # Stop adding constraints for this vehicle if limit is reached
                            if vehicle_constraints_added >= 3 or total_constraints_added >= 10:
                                break

                if total_constraints_added >= 10:
                    break

                # Subtour Elimination Constraint
                # Identify visited nodes (Zvi = 1)
                visited_nodes = [i for i in range(model._N) if solution_zvi[v, i] > 0.05]

                # Build graph for vehicle v
                G = nx.Graph()
                for i in visited_nodes:
                    for j in visited_nodes:
                        if i != j and solution_xijv[i, j, v] > 0.05:
                            G.add_edge(i, j)

                # Find connected components (subtours)
                components = list(nx.connected_components(G))

                # Add subtour elimination constraints for each disconnected component
                for subtour in components:
                    if 0 in subtour:  # Skip components that involve the depot
                        continue

                    # Arc-based constraint: sum of arcs inside the component must be <= |S| - 1
                    expr_arc = gp.quicksum(
                        model._xijv[i, j, v] for i in subtour for j in subtour if i != j
                    )
                    model.cbLazy(expr_arc <= len(subtour) - 1)
                    all_subtours_resolved = False
                    vehicle_constraints_added += 1
                    total_constraints_added += 1

                    # Stop adding constraints for this vehicle or overall if limits are reached
                    if vehicle_constraints_added >= 3 or total_constraints_added >= 10:
                        break

                if total_constraints_added >= 10:
                    break

        # Record time to first feasible solution if no subtours were added
        if all_subtours_resolved and not hasattr(model, '_first_feasible_time'):
            model._first_feasible_time = model.cbGet(GRB.Callback.RUNTIME)

