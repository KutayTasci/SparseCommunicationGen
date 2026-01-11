import os
import sys
import math
import networkit as nk

from in_out import *
from metrics import *
from graphGenerators import *
from commGenerator import generate_communication
global output_path


# ============================================================
# Utility helpers
# ============================================================

def mkdir_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def compute_rmat_scale(num_vertices):
    """Return smallest scale such that 2^scale >= num_vertices."""
    return int(math.ceil(math.log2(num_vertices)))


def print_usage_message():
    print("""
===============================================================
 GRAPH GENERATION TOOL — USAGE GUIDE
===============================================================

Supported modes:

    • rmat_skew      : R-MAT with skew parameter in [0,1]
    • rmat_custom    : R-MAT with manually defined a,b,c,d
    • gnp            : Erdős–Rényi G(n,p) random graph
    • communication  : Synthetic communication graph (JSON-driven)

The tool is modular: new graph generators can be added easily
by registering a new mode handler.

---------------------------------------------------------------
 BASIC EXAMPLES
---------------------------------------------------------------

  python main.py --mode rmat_skew --vertices 10000 --avg_degree 16 --skew 0.4

  python main.py --mode rmat_custom --vertices 8192 --avg_degree 12 \\
         --a 0.57 --b 0.19 --c 0.19 --d 0.05

  python main.py --mode gnp --vertices 10000 --p 0.0005

---------------------------------------------------------------
 COMMUNICATION GRAPH EXAMPLE
---------------------------------------------------------------

  python main.py --mode communication \\
         --comm_config configs/comm_example.json \\
         --out_name comm_graph.mtx

The communication mode reads all parameters from a JSON file,
including:
  • number of processes
  • communication degree and skew
  • message volume distributions
  • partition initialization
  • edge generation probabilities

---------------------------------------------------------------
 OPTIONAL PARAMETERS
---------------------------------------------------------------

  --out_dir OUT/         Output directory        (default: output/)
  --out_name FILE        Output file name        (default: auto-generated)
  --comm_config FILE     JSON config file        (required for communication)

---------------------------------------------------------------
 NOTES
---------------------------------------------------------------

• For R-MAT modes, --vertices is rounded up to the nearest power of 2.
• For communication mode, --vertices is ignored and may be set to any value.
• Output graphs are written in MatrixMarket (.mtx) format.

===============================================================
""")
    sys.exit(0)


# ============================================================
# MODE HANDLERS
# ============================================================

def handle_rmat_skew(args):
    """Generate graph using R-MAT with skew parameter."""
    
    scale = compute_rmat_scale(args.vertices)
    num_nodes = 2 ** scale
    edge_factor = args.avg_degree / 2.0

    if args.skew is None:
        raise ValueError("Mode 'rmat_skew' requires --skew argument.")

    a, b, c, d = rmat_params(args.skew)

    if args.out_name is None:
        args.out_name = f"rmat_skew_n{num_nodes}_deg{args.avg_degree}_sk{args.skew}.mtx"

    print("\n=== R-MAT (Skew Mode) ===")
    print(f"Nodes:       {num_nodes}  (scale={scale})")
    print(f"Avg degree:  {args.avg_degree}")
    print(f"a,b,c,d:     {a:.3f}, {b:.3f}, {c:.3f}, {d:.3f}")

    G = generate_rmat_graph(scale, edge_factor, a, b, c, d)
    return G


def handle_rmat_custom(args):
    """Generate graph using user-specified R-MAT parameters."""
    
    scale = compute_rmat_scale(args.vertices)
    num_nodes = 2 ** scale
    edge_factor = args.avg_degree / 2.0

    if None in (args.a, args.b, args.c, args.d):
        raise ValueError("Mode 'rmat_custom' requires --a --b --c --d")

    total = args.a + args.b + args.c + args.d
    a = args.a / total
    b = args.b / total
    c = args.c / total
    d = args.d / total

    if args.out_name is None:
        args.out_name = (
            f"rmat_custom_n{num_nodes}_deg{args.avg_degree}_"
            f"a{a:.2f}_b{b:.2f}_c{c:.2f}_d{d:.2f}.mtx"
        )

    print("\n=== R-MAT (Custom Mode) ===")
    print(f"Nodes:      {num_nodes}  (scale={scale})")
    print(f"Avg degree: {args.avg_degree}")
    print(f"a,b,c,d:    {a:.3f}, {b:.3f}, {c:.3f}, {d:.3f}")

    G = generate_rmat_graph(scale, edge_factor, a, b, c, d)
    return G


def handle_gnp(args):
    """Generate Erdős–Rényi G(n,p) random graph."""
    
    if args.p is None:
        raise ValueError("Mode 'gnp' requires --p for edge probability.")

    n = args.vertices
    p = args.p

    if args.out_name is None:
        args.out_name = f"gnp_n{n}_p{p}.mtx"

    print("\n=== GNP MODEL (Erdős–Rényi G(n,p)) ===")
    print(f"Nodes:      {n}")
    print(f"Edge prob:  p = {p}")

    G = generate_gnp_graph(n=n, p=p)
    return G

def handle_communication(args):
    """Generate a synthetic communication graph using JSON config."""
    if args.comm_config is None:
        raise ValueError("Mode 'communication' requires --comm_config <path_to_json>")

    # Optionally auto-name if user didn't provide one
    if args.out_name is None:
        base = os.path.splitext(os.path.basename(args.comm_config))[0]
        args.out_name = f"comm_{base}.mtx"

    print("\n=== COMMUNICATION GRAPH MODE ===")
    print(f"Config: {args.comm_config}")

    G_final, part_array = generate_communication(args)  # returns (Graph, part_array)

    # If you want, you can write part_array too (optional)
    # write_partitions(part_array, args.out_name.replace(".mtx", ".parts"))

    return G_final, part_array

# ============================================================
# REGISTER MODES HERE
# ============================================================

MODE_HANDLERS = {
    "rmat_skew": handle_rmat_skew,
    "rmat_custom": handle_rmat_custom,
    "gnp": handle_gnp,
    "communication": handle_communication,
}

def set_output_path(path):
    global output_path
    output_path = path

    # Ensure the path ends with a slash
    if not output_path.endswith("/"):
        output_path += "/"
    
    # Ensure the directory exists
    os.makedirs(output_path, exist_ok=True)

def write_mtx(G, filename):
    n = G.numberOfNodes()
    m = G.numberOfEdges()

    filename = output_path + filename

    # MatrixMarket header
    with open(filename, "w") as f:
        f.write("%%MatrixMarket matrix coordinate pattern symmetric\n")
        f.write(f"{n} {n} {m}\n")

        # Networkit edge iterator gives each edge once
        for (u, v) in G.iterEdges():
            f.write(f"{u+1} {v+1}\n")   # MTX format is 1-based indexing

def write_partitions(part_array, filename):
    filename = output_path + filename
    with open(filename, "w") as f:
        for part in part_array:
            f.write(f"{part}\n")