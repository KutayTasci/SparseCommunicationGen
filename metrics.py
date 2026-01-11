import networkit as nk
import math


# ----------------------------
# Basic Metrics
# ----------------------------

def num_nodes(G):
    return G.numberOfNodes()


def num_edges(G):
    return G.numberOfEdges()


def degrees(G):
    """Return list: degree of each node."""
    return [G.degree(u) for u in G.iterNodes()]


def min_degree(G):
    return min(degrees(G))


def max_degree(G):
    return max(degrees(G))


def avg_degree(G):
    return sum(degrees(G)) /  G.numberOfNodes() / 2


def density(G):
    """
    Density = 2m / (n(n-1)) for undirected graphs.
    """
    n = G.numberOfNodes()
    m = G.numberOfEdges()
    if n <= 1:
        return 0.0
    return 2 * m / (n * (n - 1))


# ----------------------------
# Additional Graph Metrics
# ----------------------------

def num_connected_components(G):
    """
    Number of connected components (for undirected graphs).
    """
    cc = nk.components.ConnectedComponents(G)
    cc.run()
    return cc.numberOfComponents()


def average_clustering_coefficient(G):
    """
    Returns the global clustering coefficient (single float).
    """
    return nk.globals.clustering(G)


def diameter_estimate(G, error=0.01):
    """
    Estimated diameter using the EstimatedRange algorithm.
    'error' controls approximation accuracy (0.1 is typical).
    """
    diam = nk.distance.Diameter(G, 
                                algo=nk.distance.DiameterAlgo.EstimatedRange, 
                                error=error)
    diam.run()
    return diam.getDiameter()


def degree_distribution(G):
    """
    Returns a dictionary: degree -> count.
    """
    dist = {}
    for d in degrees(G):
        dist[d] = dist.get(d, 0) + 1
    return dist


# ----------------------------
# Comprehensive Metrics Printer
# ----------------------------

def print_graph_report(G):
    """
    Print a comprehensive summary of graph statistics.
    """

    n = num_nodes(G)
    m = num_edges(G)
    degs = degrees(G)

    print("========== Graph Metrics ==========")
    print(f"Number of nodes:       {n}")
    print(f"Number of edges:       {m}")
    print(f"Density:               {density(G):.6f}")
    print("")
    print(f"Min degree:            {min(degs)}")
    print(f"Max degree:            {max(degs)}")
    print(f"Average degree:        {sum(degs)/n:.4f}")
    print(f"Degree std. dev.:      {math.sqrt(sum((d - (sum(degs)/n))**2 for d in degs)/n):.4f}")
    print("")
    print(f"Connected components:  {num_connected_components(G)}")
    print(f"Avg clustering coef.:  {average_clustering_coefficient(G):.6f}")
    print("")
    print(f"Diameter (estimate):   {diameter_estimate(G)}")
    print("===================================")

