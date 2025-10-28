"""This file creates the logo for the pycpt package.

The logo is a space invader colored with different color palettes from the pycpt
package. The dynamic logo is saved as a gif file. It cycles through different color
palettes with blinking effects (including the forbidden "jet" palette, muhaha).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import PIL

import pycpt

# Palettes to cycle through
PALETTES = ["bhw3_01", "thermal", "jet", "rainfall", "aurora"]
BLINK = ["005-random"]
SAVE_DIRECTORY = Path(__file__).parent
SAVE_PNG_DIR = SAVE_DIRECTORY / "palettes"
SAVE_PNG_DIR.mkdir(exist_ok=True)


# Make figure background transparent
plt.rcParams["figure.facecolor"] = "none"
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["savefig.transparent"] = True
plt.rcParams["savefig.pad_inches"] = 0.1


def get_invader():
    """Return a 2D array representing a space invader shape."""
    invader = [
        " X   X ",
        "  XXX  ",
        " XXXXX ",
        " X X X ",
        "XX X XX",
        " XXXXX ",
        " X   X ",
    ]
    return np.flipud(
        np.array([[1 if x == "X" else np.nan for x in l] for l in invader])
    )


def plot_invader(invader, ax, palette="wiki-france", vmin=0, vmax=1):
    """Plot the space invader on the axis using the color palette."""
    palette = pycpt.read(palette)
    palette.scale(vmin, vmax)
    ax.pcolormesh(invader, cmap=palette.cmap, norm=palette.norm)


def canvas():
    """Create a figure and axis for plotting."""
    fig = plt.figure(figsize=(2, 2), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def main():

    # Create canvas
    fig, ax = canvas()

    # Plot invader
    invader = get_invader()
    invader = invader * np.linspace(0, 1, invader.shape[1])

    # Empty save png dir
    for file in SAVE_PNG_DIR.iterdir():
        if file.suffix == ".png":
            file.unlink()

    # Save images for each palette
    for palette_name in PALETTES + BLINK:
        plot_invader(invader, ax, palette=palette_name)
        fig.savefig(SAVE_PNG_DIR / f"logo_{palette_name}.png")

    # Make gif from saved images (using imagemagick)
    images = []
    palette_list = []
    for palette in PALETTES:
        palette_list += 100 * [palette]
        palette_list += 2 * [BLINK[0], palette, BLINK[0]]

    # Load images
    for palette_name in palette_list:
        img = PIL.Image.open(SAVE_PNG_DIR / f"logo_{palette_name}.png")
        images.append(img)

    # Save as gif
    images[0].save(
        SAVE_DIRECTORY / "logo.gif",
        save_all=True,
        append_images=images[1:],
        duration=60,  # duration of each frame in milliseconds
        loop=0,  # loop forever
    )


if __name__ == "__main__":
    main()
