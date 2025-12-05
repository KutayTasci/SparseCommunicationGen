import networkit as nk


def rmat_params(skew):
    """
    Returns (a, b, c, d) for R-MAT based on a skew parameter in [0, 1].
    
    skew = 0 → perfectly balanced R-MAT
    skew = 1 → strongly skewed Graph500-like R-MAT
    """

    # Clamp skew into [0, 1]
    skew = max(0.0, min(1.0, float(skew)))

    # Balanced (uniform) parameters at skew = 0
    a0, b0, c0, d0 = 0.25, 0.25, 0.25, 0.25

    # Graph500 / power-law parameters at skew = 1
    a1, b1, c1, d1 = 0.57, 0.19, 0.19, 0.05

    # Linear interpolation
    a = a0 + (a1 - a0) * skew
    b = b0 + (b1 - b0) * skew
    c = c0 + (c1 - c0) * skew
    d = d0 + (d1 - d0) * skew

    # Normalize for safety (sum should be 1)
    total = a + b + c + d
    return a/total, b/total, c/total, d/total

def generate_rmat_graph(scale, edge_factor, a, b, c, d):
    """
    Generates an R-MAT graph using the specified parameters.

    Parameters:
    - scale (int): The logarithm (base 2) of the number of nodes.
    - edge_factor (int): The average degree of the nodes.
    - a, b, c, d (float): The probabilities for the R-MAT model.

    Returns:
    - G (nk.Graph): The generated R-MAT graph.
    """
    generator = nk.generators.RmatGenerator(scale, edge_factor, a, b, c, d)
    G = generator.generate()
    return G

def generate_gnp_graph(n, p, directed=False, seed=None):
    """
    Generates a GNP (Erdős–Rényi G(n, p)) random graph:
        • n nodes
        • Each possible edge exists independently with probability p

    Parameters:
    - n (int): number of vertices
    - p (float): edge probability in [0,1]
    - directed (bool): if True, generates a directed graph
    - seed (int): optional RNG seed

    Returns:
    - G (nk.Graph): Generated random graph
    """
    if seed is not None:
        nk.setSeed(seed, False)

    gen = nk.generators.ErdosRenyiGenerator(n, p, directed)
    G = gen.generate()
    return G