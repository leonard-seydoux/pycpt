
<div align="center">

<img src="logo/logo.gif" alt="pycpt logo" width="100"/>

**PyCPT**<br>
Color Palette Tables from <a href="http://seaviewsensing.com/pub/cpt-city/" target="_blank">cpt-city</a> in Python.<br>
Made in 2025 by Léonard Seydoux. 

</div>

## What is cpt-city?

CPT is short for Color Palette Table, a file format popularized by the [Generic Mapping Tools](https://www.generic-mapping-tools.org/) (GMT) for defining colormaps as piecewise-constant color bands between numeric boundaries.

The [cpt-city](http://seaviewsensing.com/pub/cpt-city/) website maintained by J. J. Green is a community-curated archive of color palettes collected from many projects (e.g., GMT, cmocean, Matplotlib, and more). Palettes are organized in family folders and typically include metadata files like `DESC.xml` and `COPYING.xml` that describe provenance and licensing.

This package is shipped with a `cpt-city/` directory that contains the entire archive obtained from the website. Be mindful that individual palettes may carry different licenses—refer to the accompanying `COPYING.xml` files. Learn more at on the [cpt-city](http://seaviewsensing.com/pub/cpt-city/) website.


## Overview

This package parses common CPT formats (including GMT-style lines) and exposes a simple `Palette` API that you can read from a CPT file with

```python
import pycpt
palette = pycpt.read("wiki-2.0")
palette.plot()
```

with the name of a palette from the bundled `cpt-city/` folder, or a path to any CPT file. The reader supports flexible path resolution: you can pass either an absolute/relative file path, or a short name underneath a bundled `cpt-city/` data folder (extensionless is fine, `.cpt` is added automatically). 
Once loaded, the `Palette` object provides several useful attributes and methods, such as:
- `palette.cmap` to be used with Matplotlib plotting functions
- `palette.norm` to preserve original CPT boundaries

And many helpers to inspect, scale and interpolate the palette, or plot colorbars and previews.
.

## Quickstart

```python
import pycpt
import matplotlib.pyplot as plt
# pycpt

Boundary-first CPT (Color Palette Table) colormaps for Matplotlib.

`pycpt` reads CPT files (including common GMT variants) and exposes a small, pragmatic API centered on preserving the original palette boundaries. You get a `ListedColormap` (one color per segment) and a matching `BoundaryNorm` so plots honor the authored banding.

## Features

- Robust CPT reader: supports 8-token segments (`z0 r0 g0 b0  z1 r1 g1 b1`), GMT-style (`z0 color0  z1 color1`), `r/g/b` tokens, named/hex colors, and HSV (auto-converted to RGB)
- Discrete by design: `palette.cmap` (ListedColormap) and `palette.norm` (BoundaryNorm) align with the original levels
- Handy helpers on `Palette`:
	- `levels`, `intervals`, `colors`, `n_colors`, `value_range`
	- `plot()`, `reverse()`, `scale(vmin, vmax, at=None)`, `interpolate(n)`, `colorbar(...)`
- Path resolution utilities in `pycpt.files`:
	- `solve(path)`: absolute/relative paths or short names under a bundled `cpt-city/` folder (adds `.cpt` when missing)
	- `get_family(name)`: list CPTs under a family

Note: If the `cpt-city/` data directory isn’t present, short names won’t resolve. Use explicit file paths to `.cpt` files instead.

## Quickstart

```python
import pycpt
import matplotlib.pyplot as plt
import numpy as np

# Read by short name (requires bundled cpt-city/) or by path
palette = pycpt.read("cmocean/algae")  # or "/path/to/file.cpt"

# Use cmap + norm to preserve CPT boundaries
x = np.linspace(-1, 1, 200)
x, y = np.meshgrid(x, x)
z = 4000 * (x + np.sin(y) + 0.5) + 1000

fig, ax = plt.subplots(figsize=(6, 3))
img = ax.pcolormesh(x, y, z, cmap=palette.cmap, norm=palette.norm)
cb = palette.colorbar(ax=ax, label="z values")
ax.set_title(palette.name)
plt.show()
```

### Smoother look without losing intent

```python
# Re-map boundaries to a new range and densify bands
palette.scale(-5000, 10000)
palette.interpolate(n=64)

fig, ax = plt.subplots(figsize=(6, 3))
ax.pcolormesh(x, y, z, cmap=palette.cmap, norm=palette.norm)
palette.colorbar(ax=ax, label="z values")
ax.set_title("Scaled + interpolated")
plt.show()
```

## Installation

With uv (recommended for reproducible environments):

```bash
uv sync
```

Or with pip in an active virtual environment:

```bash
pip install -e .
```

## Notebooks

- `notebooks/example.ipynb`: guided tour (reading, inspecting, plotting; cmap vs cmap+norm; scaling and interpolation)
- `notebooks/02_playground.ipynb`: a scratchpad to try palettes, compare rendering modes, and optionally browse a family


## API overview

```python
import pycpt

pal = pycpt.read("family/name")             # or a .cpt path
pal.cmap, pal.norm                          # Matplotlib-ready
pal.levels, pal.intervals, pal.colors       # Anatomy
pal.reverse().plot()                        # Chainable reverse + preview
pal.scale(vmin=-5000, vmax=10000, at=0)     # Diverging center supported
pal.interpolate(n=256)                      # Densify bands
cb = pal.colorbar(ax=ax)                    # Proper ticks and handle

from pycpt import files
files.solve("family/name")                  # Resolve path
files.get_family("wkp")                     # List CPTs in a family
```

## Notes & limitations

- The `N` (NaN) line is parsed and stored as `nan_color`; `B`/`F` lines are currently ignored
- Named and hex colors are supported; HSV is converted to RGB during parsing
- Short-name reads require a local `cpt-city/` folder (not included in the repo)

## License

See `LICENSE` if present.
