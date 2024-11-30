
import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from MIP_Models.Subtours import subtour_elimination_callback


def solve_flow_aware_location_decisions(instance_data, ml_data, use_ml_guidance, use_direct,use_transhipment):
    # Problem dimensions
    N = int(instance_data.S) + 1  # Add depot
    W = int(instance_data.W)

    # Determine which commodities to consider
    if use_transhipment:
        # Use ML predictions
        direct_commodities = ml_data.loc[ml_data['Predictions'] == 0, 'Commodity ID'].tolist()
        transshipment_commodities = ml_data.loc[ml_data['Predictions'] == 1, 'Commodity ID'].tolist()
        considered_commodities = transshipment_commodities
    else:
        # Consider all commodities
        considered_commodities = [w for w, flow in enumerate(instance_data.qw) if flow > 0]

    # Gurobi model
    model = gp.Model("FlowAwareHubLocation")
    model.setParam("TimeLimit", 120)

    # Decision variables
    yi = model.addVars(N, vtype=GRB.BINARY, name="yi")  # Hub selection
    viw = model.addVars(N, W, vtype=GRB.BINARY, name="viw")  # Assignment of commodities to hubs

    # Objective function: Minimize total distance of commodities to hubs
    total_distance = gp.quicksum(
        viw[i, w] * (instance_data.od_dist_matrix[instance_data.ow[w] - 1][i - 1] + instance_data.od_dist_matrix[i-1][instance_data.dw[w] - 1]) * instance_data.qw[w]
        for i in range(1, N) for w in considered_commodities
    )

    model.setObjective(total_distance, GRB.MINIMIZE)

     # Constraints
    # Each commodity must be assigned to exactly one hub
    model.addConstrs(
        gp.quicksum(viw[i, w] for i in range(1, N)) == 1
        for w in considered_commodities
    )

    # Commodities can only be assigned to active hubs
    model.addConstrs(
        viw[i, w] <= yi[i]
        for i in range(1, N) for w in considered_commodities
    )

    # Limit the number of hubs that can be opened
    max_hubs = N/2  # Adjust as needed
    min_hubs = 2  # Adjust as needed
    model.addConstr(gp.quicksum(yi[i] for i in range(1, N)) <= max_hubs, name="MaxHubs")
    model.addConstr(gp.quicksum(yi[i] for i in range(1, N)) >= min_hubs, name="MinHubs")

    # Solve model
    model.optimize()

    # Extract selected hubs
    selected_hubs = [i for i in range(1, N) if yi[i].X > 0.5]

    model.reset()
    del model

    return selected_hubs




def solve_all_or_routing_decisions(instance_data, ml_data, fixed_hubs, use_ml_guidance, use_location_first,use_direct,use_transhipment):
    # Problem dimensions
    N = int(instance_data.S) + 1  # Add depot
    W = int(instance_data.W)
    V_small_total = instance_data.Vind[0]
    V_big_total = instance_data.Vind[1]
    Vtotal = V_small_total + V_big_total

    # Non-zero flows
    nonzero_flows = [w for w, flow in enumerate(instance_data.qw) if flow > 0]

    # ML Decisions
    direct_commodities = ml_data.loc[ml_data['Predictions'] == 0, 'Commodity ID'].tolist()
    transshipment_commodities = ml_data.loc[ml_data['Predictions'] == 1, 'Commodity ID'].tolist()

    # Gurobi model
    model = gp.Model("RoutingDecision")
    model.setParam("TimeLimit", 1800)

    # Decision variables
    av = model.addVars(Vtotal, vtype=GRB.BINARY, name="av")
    xijv = model.addVars(N, N, Vtotal, vtype=GRB.BINARY, name="xijv")
    fijvw = model.addVars(N, N, Vtotal, W, vtype=GRB.BINARY, name="fijvw")
    Zvi = model.addVars(Vtotal, N, vtype=GRB.BINARY, name="Zvi")
    yi = model.addVars(N, vtype=GRB.BINARY, name="yi")

    
    hub_costs = gp.quicksum(instance_data.Hubs_FC[i - 1] * yi[i] for i in range(1, N))
    # Objective function: Minimize routing and vehicle costs
    veh_costs_term1 = gp.quicksum(instance_data.FC[0] * av[v] for v in range(V_small_total))
    veh_costs_term2 = gp.quicksum(instance_data.FC[1] * av[v] for v in range(V_small_total, Vtotal))
    route_term1 = gp.quicksum(
        (instance_data.OC[0] * instance_data.od_dist_matrix[i - 1][j - 1] / instance_data.speed[0]) * xijv[i, j, v]
        for i in range(1, N) for j in range(1, N) if i != j for v in range(V_small_total)
    )
    route_term2 = gp.quicksum(
        (instance_data.OC[1] * instance_data.od_dist_matrix[i - 1][j - 1] / instance_data.speed[1]) * xijv[i, j, v]
        for i in range(1, N) for j in range(1, N) if i != j for v in range(V_small_total, Vtotal)
    )
    model.setObjective(veh_costs_term1 + veh_costs_term2 + route_term1 + route_term2, GRB.MINIMIZE)

    # Fix location decisions
    if use_location_first:
        for i in range(1, N):
            if i in fixed_hubs:
                model.addConstr(yi[i] == 1, name=f"FixHub_{i}")
            else:
                model.addConstr(yi[i] == 0, name=f"FixNoHub_{i}")

  
    # Add routing constraints (as in your original routing model)
    # Constraints

    # (1) Flow conservation at origins
    model.addConstrs(
        gp.quicksum(fijvw[instance_data.ow[w], j, v, w] for j in range(1, N) if j != instance_data.ow[w] for v in range(Vtotal)) 
        - gp.quicksum(fijvw[j, instance_data.ow[w], v, w] for j in range(1, N) if j != instance_data.ow[w] for v in range(Vtotal)) 
        == 1
        for w in nonzero_flows
    )

    if use_ml_guidance and use_direct: 
        model.addConstrs(
        gp.quicksum(fijvw[i, j, v, w] for v in range(Vtotal))  
        <= 1
        for i in range (1,N)
        for j in range (1,N)
        if i !=j 
        for w in direct_commodities 
    )
        
    
    # (2) Flow conservation at destinations
    model.addConstrs(
        gp.quicksum(fijvw[j, instance_data.dw[w], v, w] for j in range(1, N) if j != instance_data.dw[w] for v in range(Vtotal)) 
        -  gp.quicksum(fijvw[instance_data.dw[w],j, v, w] for j in range(1, N) if j != instance_data.dw[w] for v in range(Vtotal)) 
        == 1
        for w in nonzero_flows
    )

    # (3) Flow conservation at intermediate nodes
    for w in nonzero_flows:
        for i in range(1, N):
            if i != instance_data.ow[w] and i != instance_data.dw[w]:
                outgoing = gp.quicksum(fijvw[i, j, v, w] for j in range(1, N) if j != i for v in range(Vtotal))
                incoming = gp.quicksum(fijvw[j, i, v, w] for j in range(1, N) if j != i for v in range(Vtotal))
                model.addConstr(incoming == outgoing, name=f"flow_conservation_{i}_{w}")
                    

    # (4) Flow arc and vehicle usage relationship
    model.addConstrs(
        fijvw[i, j, v, w] <= xijv[i, j, v]
        for w in nonzero_flows for v in range(Vtotal) for i in range(1, N) for j in range(1, N) if i != j
    )

    ''''Would need to seperate between transhipment and non transhipment balance if I have both nodes on  the graph'''
    # Can only change vehicle at transhipment nodes:
    if use_ml_guidance and use_transhipment:
         model.addConstrs(
        gp.quicksum(
            fijvw[i, j, v, w]
                for i in range(1,N) if i != j
            )
        -
        gp.quicksum(
            fijvw[j, i, v, w]
            for i in range(1,N) if i != j
            )
        <= yi[j]
        for v in range(Vtotal)
        for w in transshipment_commodities  
        for j in range(1, N) 
        if j != instance_data.ow[w]
        if j!= instance_data.dw[w]
    )
    else:
         model.addConstrs(
        gp.quicksum(
            fijvw[i, j, v, w]
                for i in range(1,N) if i != j
            )
        -
        gp.quicksum(
            fijvw[j, i, v, w]
            for i in range(1,N) if i != j
            )
        <= yi[j]
        for v in range(Vtotal) 
        for w in nonzero_flows
        for j in range(1, N) 
        if j != instance_data.ow[w]
        if j!= instance_data.dw[w]

        )



    
    if use_ml_guidance and use_direct:
        # Direct Commodities no vehicle change:
        model.addConstrs(
        gp.quicksum(
            fijvw[i, j, v, w]
                for i in range(1,N) if i != j
            )
        -
        gp.quicksum(
            fijvw[j, i, v, w]
            for i in range(1,N) if i != j
            )
        <= 0
        for v in range(Vtotal)
        for w in direct_commodities
        for j in range(1, N) 
        if j != instance_data.ow[w]
        if j!= instance_data.dw[w]
        )
    
    if use_ml_guidance and use_transhipment:
        # Transhipment Commodities at least one vehicle change:
        model.addConstrs(
        gp.quicksum(
            fijvw[instance_data.ow[w], j, v, w]
                for j in range(1,N) if instance_data.ow[w] != j
            )
        +
        gp.quicksum(
            fijvw[i, instance_data.dw[w], v, w]
            for i in range(1,N) if i != instance_data.dw[w]
            )
        <= 1
        for v in range(Vtotal)
        for w in transshipment_commodities
        )

    # (5) Capacity constraints per vehicle
    model.addConstrs(
        gp.quicksum(fijvw[i, j, v, w] * instance_data.qw[w] for w in nonzero_flows) <= instance_data.vcap[0] * xijv[i, j, v]
        for v in range(V_small_total) for i in range(1, N) for j in range(1, N) if i != j
    )

    # (6) Vehicle arrival and departure balance
    model.addConstrs(
        gp.quicksum(xijv[i, j, v] for j in range(N) if i != j) ==
        gp.quicksum(xijv[j, i, v] for j in range(N) if i != j)
        for v in range(Vtotal) for i in range(N)
    )

    # (7) Depot constraints
    model.addConstrs(
        gp.quicksum(xijv[0, j, v] for j in range(1, N)) == av[v]
        for v in range(Vtotal)
    )

# Vehicles must end at the depot
    model.addConstrs(
        gp.quicksum(xijv[j, 0, v] for j in range(1, N)) == av[v]
        for v in range(Vtotal)
    )

    model.addConstrs(
        Zvi[v,0] == av[v]
        for v in range(Vtotal)
    )

    model.addConstrs(
        Zvi[v,i] <= av[v]
        for v in range(Vtotal) for i in range (N)
    )

    # Vehicles visit a node only if it's included in the solution
    model.addConstrs(
        gp.quicksum(xijv[i, j, v] for j in range(N) if i != j) == Zvi[v, i]
        for v in range(Vtotal) for i in range(N)
    )

    # Prevent self-loops
    model.addConstrs(
        xijv[i, i, v] == 0
        for v in range(Vtotal) for i in range(N)
    )

    # Lazy constraints parameter
    model.Params.LazyConstraints = 1

    # Register callback and optimize
    model._xijv = xijv
    model._Zvi = Zvi
    model._av = av
    model._N = N
    model._Vtotal = Vtotal

    first_feasible_time = None
    start_time = model.Runtime  # Get the start time

    model.optimize(subtour_elimination_callback)

    # Collect results
    result = {
        'solution': None,
        'objective_value': None,
        'optimality_gap': None,
        'status': model.Status,
        'time_to_first_feasible': None,
        'total_solving_time': model.Runtime,
        'solution_count': model.SolCount
    }

    # Check model status
    if model.Status in [GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.INTERRUPTED]:
        print(f"Model solved with status {model.Status}.")


    # Print results
    if model.Status == GRB.OPTIMAL:
        print("Optimal solution found.")
        for v in range(Vtotal):
            print(f"Vehicle {v}:")
            for i in range(N):
                for j in range(N):
                    if xijv[i, j, v].X > 0.05:
                        print(f"  Arc ({i}, {j})")
    
    if model.Status == GRB.OPTIMAL:
        print("Optimal solution found.")

    model._xijv = xijv
    model._Zvi = Zvi
    model._av = av
    model._yi = yi
    model._fijvw = fijvw
    model._N = N
    model._W = W
    model._Vtotal = Vtotal

    # Check model status
    if model.Status in [GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.INTERRUPTED]:
        print(f"Model solved with status {model.Status}.")
        
        # Get the best feasible solution if available
        if model.SolCount > 0:
            result['time_to_first_feasible']: model._first_feasible_time
            # Helper function to threshold values
            def to_binary(value):
                return 1 if value > 0.05 else 0

            # Extract and threshold the solution values
            solution = {
                'fijvw': { (i, j, v, w): to_binary(model._fijvw[i, j, v, w].X)
                           for i in range(model._N) for j in range(model._N)
                           for v in range(model._Vtotal) for w in range(model._W) },
                'xijv': { (i, j, v): to_binary(model._xijv[i, j, v].X)
                          for i in range(model._N) for j in range(model._N)
                          for v in range(model._Vtotal) },
                'av': { v: to_binary(model._av[v].X) for v in range(model._Vtotal) },
                'Zvi': { (v, i): to_binary(model._Zvi[v, i].X)
                         for v in range(model._Vtotal) for i in range(model._N) },
                'yi': { i: to_binary(model._yi[i].X) for i in range(len(model._yi)) }
            }

            # Update result dictionary
            result['solution'] = solution
            result['objective_value'] = model.ObjVal
            result['optimality_gap'] = model.MIPGap
        else:
            print("No feasible solution found.")

    elif model.Status == GRB.INFEASIBLE:
        print("Model is infeasible.")
    elif model.Status == GRB.UNBOUNDED:
        print("Model is unbounded.")
    
    model.reset()
    del model
    
    return result




