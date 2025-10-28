import matplotlib.pyplot as plt
import numpy as np

import pycpt


def get_invader():
    invader = [
        "X     X",
        "X     X",
        " XXXXX ",
        " XXXXX ",
        " X X X ",
        " X X X ",
        "XXXXXXX",
        " X   X ",
    ]
    return np.array([[1 if x == "X" else np.nan for x in l] for l in invader])


def trait_invader(invader, ax):
    ax.matshow(invader, line="k", lw=2)


def plot_invader(invader, ax, palette="wiki-france"):
    palette = pycpt.read(palette)
    palette.scale(np.nanmin(invader), np.nanmax(invader))
    ax.matshow(invader, cmap=palette.cmap, norm=palette.norm)


def canvas():
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
    invader = invader * np.linspace(-10, 10, invader.shape[1])
    trait_invader(invader, ax)
    plot_invader(invader, ax, palette="jet")

    # Save logo
    fig.savefig("logo/logo.png", bbox_inches="tight", pad_inches=0)


if __name__ == "__main__":
    main()
