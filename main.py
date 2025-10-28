import numpy as np
import matplotlib.pyplot as plt

import pycpt


def demo():
    """Small demo using a CPT palette."""
    try:
        # Adjust the palette name or path as needed. If the bundled cpt-city
        # folder is not available, point to a local .cpt file on disk.
        palette = pycpt.read("cmocean/algae")
    except Exception as exc:
        print("Could not load sample palette:", exc)
        print("Provide a path to a local .cpt file instead.")
        return

    x = np.linspace(-1, 1, 200)
    x, y = np.meshgrid(x, x)
    z = 4000 * (x + np.sin(y) + 0.5) + 1000

    fig, ax = plt.subplots(figsize=(6, 3))
    img = ax.pcolormesh(x, y, z, cmap=palette.cmap, norm=palette.norm)
    palette.colorbar(ax=ax, label="z values")
    ax.set_title(palette.name)
    plt.show()


if __name__ == "__main__":
    demo()
