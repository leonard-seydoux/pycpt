
<div align="center">

<img src="logo/logo.gif" alt="pycpt logo" width="100"/>

<span style="font-size: 170%;">**PyCPT**</span><br>
Color Palette Tables from <a href="http://seaviewsensing.com/pub/cpt-city/" target="_blank">cpt-city</a> in Python.<br>
Made in 2025 by Léonard Seydoux. 

</div>

## Overview

This package parses common CPT formats (including GMT-style lines) and exposes a simple `Palette` API:
- `palette.cmap`: a `ListedColormap` with one color per CPT segment
- `palette.norm`: a `BoundaryNorm` that preserves original CPT boundaries
- helpers like `plot()`, `reverse()`, `scale(vmin, vmax, at=None)`, `interpolate(n)` and `colorbar(...)`

It also supports flexible path resolution: you can pass either an absolute/relative file path, or a short name underneath a bundled `cpt-city/` data folder (extensionless is fine, `.cpt` is added automatically).

## Quickstart

```python
import pycpt
import matplotlib.pyplot as plt
import numpy as np

# Read by short name relative to the bundled cpt-city data (if present),
# or provide a direct file path to a .cpt on disk.
palette = pycpt.read("cmocean/algae")  # or "/path/to/file.cpt"

# Use cmap+norm to respect CPT boundaries
x = np.linspace(-1, 1, 200)
x, y = np.meshgrid(x, x)
z = 4000 * (x + np.sin(y) + 0.5) + 1000

fig, ax = plt.subplots(figsize=(6, 3))
im = ax.pcolormesh(x, y, z, cmap=palette.cmap, norm=palette.norm)
cb = palette.colorbar(ax=ax, label="z values")
ax.set_title(palette.name)
plt.show()
```

## Installation

This project uses a standard Python packaging layout with `pyproject.toml`.

```bash
pip install -e .
```

## License

See `LICENSE` if applicable.
