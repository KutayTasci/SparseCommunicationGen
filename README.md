# Graph Generation Toolkit

This repository provides a modular command-line toolkit for generating sparse graphs for benchmarking, research, and experimentation.  
It supports multiple graph generation models including:

- R-MAT (skew-based and custom parameters)
- GNP (Erdős–Rényi G(n, p))
- Extensible modular design for adding new models

The tool exports graphs in Matrix Market (.mtx) format and provides summary metrics for each generated graph.

## Features

- Modular architecture with pluggable generation modes  
- R-MAT graph generation with selectable skewness  
- R-MAT with manually defined probabilities  
- Erdős–Rényi G(n, p) generator  
- Output in Matrix Market format  
- Automatic graph statistics (degree distribution metrics, density, clustering coefficient, diameter estimate)  
- Clean CLI interface with comprehensive usage information  

## Installation

Clone the repository:

```
git clone https://github.com/yourusername/yourrepo.git
cd yourrepo
```

Install Python dependencies:

```
pip install networkit numpy
```

## Repository Structure

```
.
├── main.py                Entry point for CLI graph generation
├── graphGenerators.py     Graph generator implementations (R-MAT, GNP, etc.)
├── metrics.py             Functions for computing graph statistics
├── in_out.py              Utility functions for file writing and output handling
├── output/                Default output directory for .mtx files
└── README.md              Documentation
```

## Usage

To view the usage guide, run:

```
python main.py
```

## Generation Modes

### 1. R-MAT (Skew Mode)

```
python main.py --mode rmat_skew --vertices 10000 --avg_degree 16 --skew 0.4
```

### 2. R-MAT (Custom Parameters)

```
python main.py --mode rmat_custom --vertices 8192 --avg_degree 12 \
    --a 0.57 --b 0.19 --c 0.19 --d 0.05
```

### 3. GNP (Erdős–Rényi G(n, p))

```
python main.py --mode gnp --vertices 10000 --p 0.0005
```

## Output

Graphs are written in `.mtx` format to the output directory.  
If `--out_name` is not provided, filenames are generated automatically.

## Graph Metrics

After generation, the script prints:

- Number of nodes and edges  
- Minimum, maximum, and average degree  
- Graph density  
- Number of connected components  
- Clustering coefficient  
- Estimated diameter  

## Extending the Toolkit

To add a new graph generation mode:

1. Write a new handler function in `main.py`.
2. Implement the generator in `graphGenerators.py`.
3. Register it inside `MODE_HANDLERS`.

## License

Specify your project license here.

## Contact

Add your contact information here.
