import argparse
import os
import sys

from in_out import *
from metrics import *
from graphGenerators import *


# ============================================================
# MAIN FUNCTION
# ============================================================

def main():

    if len(sys.argv) == 1:
        print_usage_message()

    parser = argparse.ArgumentParser(description="Modular Graph Generation Tool")

    parser.add_argument("--mode", type=str, required=True,
                        help=f"Graph generation mode. Available: {list(MODE_HANDLERS.keys())}")
    
    parser.add_argument("--comm_config", type=str, default=None, help="Path to communication generator JSON config (required for mode=communication)")

    parser.add_argument("--vertices", type=int,
                        help="Number of vertices (R-MAT will round to power of 2)")

    parser.add_argument("--avg_degree", type=float,
                        help="Desired average degree (required by R-MAT modes)")

    parser.add_argument("--skew", type=float, help="Skew parameter for rmat_skew")

    parser.add_argument("--a", type=float)
    parser.add_argument("--b", type=float)
    parser.add_argument("--c", type=float)
    parser.add_argument("--d", type=float)

    parser.add_argument("--p", type=float, help="Edge probability for GNP model")

    parser.add_argument("--out_dir", type=str, default="output/")
    parser.add_argument("--out_name", type=str, default=None)

    args = parser.parse_args()

    if args.mode not in MODE_HANDLERS:
        print(f"\nERROR: Unknown mode '{args.mode}'")
        print(f"Available: {list(MODE_HANDLERS.keys())}\n")
        sys.exit(1)

    mkdir_if_not_exists(args.out_dir)
    set_output_path(args.out_dir)
    if args.mode != "communication":
        G = MODE_HANDLERS[args.mode](args)
    else:
        G, part_array = MODE_HANDLERS[args.mode](args)
        

    out_path = os.path.join(args.out_dir, args.out_name)
    print(f"\nWriting graph to: {out_path}")
    write_mtx(G, args.out_name)

    if args.mode != "communication":
        print("\n=== Graph Metrics ===")
        print_graph_report(G)
        print("=====================\n")
    else: 
        # Write partition array if needed
        part_out_path = os.path.join(args.out_dir, args.out_name.replace(".mtx", ".parts"))
        print(f"\nWriting partition array to: {part_out_path}")
        write_partitions(part_array, args.out_name.replace(".mtx", ".parts"))

if __name__ == "__main__":
    main()
