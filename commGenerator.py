import os
import sys
import math
import json
import networkit as nk
from graphGenerators import *
from metrics import *
import random

def mkdir_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def compute_rmat_scale(num_vertices):
    """Return smallest scale such that 2^scale >= num_vertices."""
    return int(math.ceil(math.log2(num_vertices)))

def _sample_trunc_normal_01(mean_01: float, sigma: float, rng=random, max_tries: int = 50) -> float:
    """
    Sample from N(mean_01, sigma^2) truncated to [0,1].
    Falls back to clamping if rejection fails (rare).
    """
    for _ in range(max_tries):
        x = rng.gauss(mean_01, sigma)
        if 0.0 <= x <= 1.0:
            return x
    # fallback: clamp
    return max(0.0, min(1.0, rng.gauss(mean_01, sigma)))

def gen_messages(number_of_processes, average_communication_degree, communication_skew):
    scale = compute_rmat_scale(number_of_processes)
    a, b, c, d = rmat_params(communication_skew)

    G = generate_rmat_graph(
        scale=scale,
        edge_factor=float(average_communication_degree),
        a=a,
        b=b,
        c=c,
        d=d
    )
    return G

def sample_distinct_from_range(rng, start, size, sample_size):
    if size <= 0:
        return []

    # Ensure valid integer sample size
    sample_size = int(sample_size)
    sample_size = max(0, min(sample_size, size))

    return rng.sample(range(start, start + size), sample_size)

def gen_message_volumes(
    G,
    max_volume,
    mode="power",          # "power" or "lognormal" or "pareto"
    skew=1.0,              # 1.0 ~ even-ish; bigger => more skewed
    heavy_tail=False,      # if True, skew toward large volumes instead of small
    target_mean=None,      # optional: enforce average approx
    seed=None
):
    rng = random.Random(seed)

    # First pass: sample unscaled volumes in [1, max_volume]
    raw = []
    edges = []
    for u, v in G.iterEdges():
        edges.append((u, v))

        if mode == "power":
            x = rng.random()  # U(0,1)
            k = max(1e-6, float(skew))
            if heavy_tail:
                x = 1.0 - (1.0 - x) ** k   # pushes toward 1
            else:
                x = x ** k                  # pushes toward 0

            vol = 1 + int(x * (max_volume - 1))

        elif mode == "lognormal":
            # skew controls sigma; larger sigma => more skew
            sigma = max(1e-6, float(skew))
            # mu chosen so median ~ 1 before scaling; we'll scale after if target_mean given
            x = rng.lognormvariate(mu=0.0, sigma=sigma)
            vol = 1 + int(min(x, 50.0) / 50.0 * (max_volume - 1))  # cap to avoid insane outliers

        else:
            raise ValueError("mode must be 'power', 'lognormal'")

        raw.append(vol)

    # Optional: rescale to hit an approximate target mean while respecting [1, max_volume]
    if target_mean is not None and raw:
        cur_mean = sum(raw) / len(raw)
        if cur_mean > 0:
            scale = float(target_mean) / cur_mean
            raw = [max(1, min(max_volume, int(round(vol * scale)))) for vol in raw]

    # Apply weights
    for (u, v), vol in zip(edges, raw):
        G.setWeight(u, v, vol)
        # print(f"Message from {u} to {v}: Volume = {vol}")

    return G

def initialize_graph(
    G_directed_comm,
    mean_position: float = 0.0,  # [-1, 1]: -1 -> min, 0 -> mid, +1 -> max
    skew: float = 0.5,           # >=0: controls stddev/spread (bigger => more variance)
    seed: int | None = None,
):
    rng = random.Random(seed)

    number_of_processes = G_directed_comm.numberOfNodes()
    part_sizes = [0 for _ in range(number_of_processes)]

    # Map mean_position [-1,1] -> mean in [0,1]
    mean_position = max(-1.0, min(1.0, float(mean_position)))
    mean_01 = 0.5 * (mean_position + 1.0)

    # Map skew -> sigma on [0,1]
    # - skew = 0   => very tight around mean
    # - skew ~ 1   => moderate spread
    # - skew > 1   => quite wide (still truncated)
    skew = max(0.0, float(skew))
    sigma = 0.02 + 0.25 * skew   # tweakable but behaves well

    for u in G_directed_comm.iterNodes():
        # For directed graphs, iterNeighbors(u) = out-neighbors in NetworKit
        outgoing_weights = [G_directed_comm.weight(u, v) for v in G_directed_comm.iterNeighbors(u)]

        if outgoing_weights:
            min_weight = min(outgoing_weights)
            max_weight = sum(outgoing_weights)

            if max_weight <= min_weight:
                part_sizes[u] = int(min_weight)
            else:
                x = _sample_trunc_normal_01(mean_01, sigma, rng=rng)
                part_sizes[u] = int(min_weight + x * (max_weight - min_weight))
        else:
            #print(f"Warning: Process {u} has no outgoing communication; assigning partition size 0.")
            part_sizes[u] = 0

    total_vertices = sum(part_sizes)
    G_init = nk.Graph(total_vertices, directed=False)

    return G_init, part_sizes

def generate_edges(G_init, part_sizes, G_directed_comm, edge_connection_prob=0.5, seed=None):
    offset = 0
    part_offsets = []
    for size in part_sizes:
        part_offsets.append(offset)
        offset += size
    
    processed_pairs = set()
    rng = random.Random(seed) 
    for u in G_directed_comm.iterNodes():
        start_u = part_offsets[u]
        size_u = part_sizes[u]

        for v in G_directed_comm.iterNeighbors(u):
            if (u, v) in processed_pairs or (v, u) in processed_pairs:
                continue
            processed_pairs.add((u, v))

            send_vol_uv = G_directed_comm.weight(u, v)
            send_vol_vu = G_directed_comm.weight(v, u) if G_directed_comm.hasEdge(v, u) else 0
            start_v = part_offsets[v]
            size_v = part_sizes[v]

            # This part should sample send_vol_uv distinct vertices from u's partition
            # and send_vol_vu distinct vertices from v's partition, and connect them
            # in a bipartite manner.
            # Every vertex in both samples should connect to at least one vertex in the other sample.
            if size_u == 0 or size_v == 0:
                raise ValueError(f"Cannot generate edges between partitions {u} and {v} with sizes {size_u} and {size_v}.")
            
            sample_size_u = send_vol_uv # This is guaranteed to be <= size_u
            sample_size_v = send_vol_vu

            sampled_vertices_u = sample_distinct_from_range(rng, start_u, size_u, sample_size_u)
            sampled_vertices_v = sample_distinct_from_range(rng, start_v, size_v, sample_size_v)

            for su in sampled_vertices_u:
                # Ensure at least one connection
                sv = rng.choice(sampled_vertices_v)
                G_init.addEdge(su, sv)

            for sv in sampled_vertices_v:
                # Ensure at least one connection
                su = rng.choice(sampled_vertices_u)
                G_init.addEdge(su, sv)
            
            # Add additional edges based on edge_connection_prob
            for su in sampled_vertices_u:
                for sv in sampled_vertices_v:
                    if not G_init.hasEdge(su, sv):
                        if rng.random() < edge_connection_prob:
                            G_init.addEdge(su, sv)

    return G_init

def remove_isolated_nodes(G, part_sizes):
    isolated_nodes = [u for u in G.iterNodes() if G.degree(u) == 0]
    for i in isolated_nodes:
        G.removeNode(i)
    # Update part_sizes to reflect removed nodes
    new_part_sizes = []
    offset = 0
    for size in part_sizes:
        count = 0
        for i in range(size):
            if not G.hasNode(offset + i):
                continue
            count += 1
        new_part_sizes.append(count)
        offset += size

    return G, new_part_sizes

def generate_communication(args):
    """
    Reads args.comm_config JSON and runs:
      gen_messages -> directed+weighted -> gen_message_volumes
      -> initialize_graph -> generate_edges
    Returns: (G_final, part_array)
    """
    config_path = getattr(args, "comm_config", None)
    if not config_path:
        raise ValueError("generate_communication requires args.comm_config")

    with open(config_path, "r") as f:
        cfg = json.load(f)

    # --- required top-level params ---
    number_of_processes = int(cfg["number_of_processes"])
    average_communication_degree = float(cfg["average_communication_degree"])
    communication_skew = float(cfg["communication_skew"])

    # --- sections ---
    msgvol = cfg["message_volumes"]
    initg  = cfg["initialize_graph"]
    edges  = cfg["generate_edges"]

    # --- base communication pattern graph ---
    G = gen_messages(number_of_processes, average_communication_degree, communication_skew)

    # Ensure directed + weighted
    G_directed = nk.Graph(G, directed=True, weighted=True)
    del G

    # --- volumes ---
    G_directed = gen_message_volumes(
        G_directed,
        max_volume=int(msgvol["max_volume"]),
        mode=str(msgvol["mode"]),
        skew=float(msgvol["skew"]),
        target_mean=(None if msgvol.get("target_mean") is None else float(msgvol["target_mean"])),
        heavy_tail=bool(msgvol.get("heavy_tail", False)),
        seed=(None if msgvol.get("seed") is None else int(msgvol["seed"])),
    )

    # --- initialize parts / initial graph ---
    G_init, part_sizes = initialize_graph(
        G_directed,
        mean_position=float(initg["mean_position"]),
        skew=float(initg["skew"]),
        seed=(None if initg.get("seed") is None else int(initg["seed"])),
    )

    # --- final edges ---
    G_final = generate_edges(
        G_init,
        part_sizes,
        G_directed,
        edge_connection_prob=float(edges["edge_connection_prob"]),
        seed=(None if edges.get("seed") is None else int(edges["seed"])),
    )

    G_final, part_sizes = remove_isolated_nodes(G_final, part_sizes)
    print(f"Final graph has {G_final.numberOfNodes()} nodes and {G_final.numberOfEdges()} edges.")

    # Build part_array: length = total vertices
    part_array = [0 for _ in range(G_final.numberOfNodes())]
    offset = 0
    for pid, size in enumerate(part_sizes):
        for i in range(size):
            part_array[offset + i] = pid
        offset += size

    return G_final, part_array