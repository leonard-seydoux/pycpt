"""Read and work with Color Palette Table (CPT).

This module provides a high-level interface for loading and using CPTs in
Matplotlib. The :class:`Palette` class represents a CPT and offers convenient
access to its boundaries, colors, and ready-to-use Matplotlib objects. The
:func:`read` function parses CPT files either from the bundled cpt-city archive
or from arbitrary file paths on disk.

This implementation is designed around the idea of "boundaries first". CPTs
often define unequally spaced segments; by default, the palette's normalization
uses :class:`matplotlib.colors.BoundaryNorm` with the original boundaries so
plots reflect the palette's intended value ranges. For a smoother appearance,
you can increase banding with :meth:`Palette.interpolate` to create more evenly
spaced segments, or build a continuous :class:`matplotlib.colors.LinearSegmentedColormap`
from the palette endpoints directly in your plotting code.

The reader attempts to be robust to common CPT variants. It supports the
standard 8-column segment form (``z0 r0 g0 b0  z1 r1 g1 b1``), GMT-style lines
(``z0 color0  z1 color1``), slash-separated colors (``r/g/b``), named and hex
colors, and the HSV color model (which is converted to RGB during parsing).

Some CPT files may use non-standard formats and are not yet supported.
"""

from typing import Dict, List, Optional, Tuple

from matplotlib.cm import ScalarMappable
from matplotlib.colorbar import Colorbar
from matplotlib.colors import (
    BoundaryNorm,
    LinearSegmentedColormap,
    ListedColormap,
)
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .colors import is_number, parse_color_triplet, parse_special_color
from . import files


class Palette:
    """A CPT colormap with helpful accessors and Matplotlib integration.

    A ``Palette`` stores the piecewise color mapping defined by a CPT file.
    It exposes the natural segment boundaries (often unequally spaced),
    provides a ready-to-use :class:`~matplotlib.colors.ListedColormap` and a
    matching :class:`~matplotlib.colors.BoundaryNorm`, and includes utilities
    for previewing, reversing, interpolating, and (optionally) re-scaling
    levels.

    Attributes
    ----------
    data : numpy.ndarray
        Array of shape ``(n, 8)`` with rows
        ``[z0, r0, g0, b0, z1, r1, g1, b1]`` where ``z0``/``z1`` are segment
        boundaries and colors are endpoint RGB values in 0–255.
    nan_color : tuple of int or None
        Optional color to use for NaN values parsed from an ``N`` line.
    name : str or None
        Palette name (typically the file basename without extension).
    kind : {"sequential", "diverging"}
        Logical type of the palette; affects how :meth:`scale` re-maps
        boundaries.
    diverging_point : float or None
        For ``kind='diverging'``, the value around which the colormap is
        centered. Segments left/right of ``diverging_point`` are re-scaled
        independently to preserve divergence.
    """

    def __init__(
        self,
        data: np.ndarray,
        kind: str = "sequential",
        nan_color: Optional[Tuple[int, int, int]] = None,
        name: Optional[str] = None,
        diverging_point: Optional[float] = 0,
    ):
        """Initialize a palette.

        Parameters
        ----------
        data : numpy.ndarray
            Shape ``(n, 8)`` array with ``[z0, r0, g0, b0, z1, r1, g1, b1]``
            per row (RGB endpoint colors in 0–255).
        nan_color : tuple of int, optional
            Color to represent NaN values if provided by an ``N`` line.
        name : str, optional
            Human-readable name, typically the CPT filename stem.
        kind : {"sequential", "diverging"}, default "sequential"
            Palette type; controls :meth:`scale` behavior when re-mapping
            boundaries to new data ranges.
        diverging_point : float, optional
            For ``kind='diverging'``, the value around which the colormap is
            centered. Segments left/right of ``diverging_point`` are re-scaled
            independently to preserve divergence.
        """
        self.data = data
        self.kind = kind
        self.nan_color = nan_color
        self.name = name
        self.diverging_point = diverging_point

    def __repr__(self):
        return (
            f"Palette('{self.name}', n_colors={len(self.data)}, "
            f"range=[{self.data[0, 0]:.2f}, {self.data[-1, 4]:.2f}], "
            f"kind={self.kind})"
        )

    @property
    def n_colors(self) -> int:
        """Number of color segments in the colormap.

        This equals the number of CPT rows (segments). It is also the number of
        discrete color bands when using ``palette.cmap`` together with
        ``palette.norm`` (BoundaryNorm).
        """
        return len(self.data)

    @property
    def value_range(self) -> Tuple[float, float]:
        """The inclusive numeric range covered by the colormap.

        Returns
        -------
        (float, float)
            ``(z_min, z_max)`` from the first segment start to the last segment end.
        """
        return (float(self.cmin), float(self.cmax))

    @property
    def cmin(self) -> float:
        """Minimum boundary value of the colormap (``z_min``)."""
        return float(self.data[0, 0])

    @property
    def cmax(self) -> float:
        """Maximum boundary value of the colormap (``z_max``)."""
        return float(self.data[-1, 4])

    @property
    def levels(self) -> np.ndarray:
        """All unique boundary values (levels) sorted in ascending order.

        The returned array has length ``n_colors + 1`` (one more boundary than
        segments), suitable for constructing a :class:`BoundaryNorm`.
        """
        return np.unique(np.concatenate((self.data[:, 0], self.data[-1:, 4])))

    @property
    def intervals(self) -> pd.IntervalIndex:
        """Segment intervals as a :class:`pandas.IntervalIndex` (closed="both").

        Each interval corresponds to one CPT segment ``[z0, z1]``.
        """
        return pd.IntervalIndex.from_arrays(
            self.data[:, 0], self.data[:, 4], closed="both"
        )

    @property
    def cmap(self):
        """
        Build a Matplotlib colormap (discrete bands) from this CPT.

        Returns
        -------
        cmap : matplotlib Colormap
            A :class:`~matplotlib.colors.ListedColormap` with one solid color per
            CPT segment, ordered by segment.
        """
        return ListedColormap(self.colors, name=self.name or "cpt_colormap")

    @property
    def norm(self):
        """
        Build a Matplotlib normalization that preserves CPT boundaries.

        Returns
        -------
        norm : matplotlib.colors.BoundaryNorm
            A :class:`BoundaryNorm` with ``boundaries=palette.levels`` and
            ``ncolors=palette.n_colors`` so that each CPT segment maps to a
            constant color band without re-scaling the original CPT range.
        """
        return BoundaryNorm(self.levels, ncolors=self.n_colors, clip=True)

    @property
    def colors(self):
        """
        Get the list of segment-start colors as RGB tuples in 0–1 floats.

        Returns
        -------
        list of tuple of float
            List of ``(r, g, b)`` triplets in the 0–1 range, taken from the
            left endpoint of each segment.
        """
        return [(r, g, b) for (r, g, b) in self.data[:, 1:4] / 255]

    def reverse(self):
        """Reverse the order of segments in place (endpoints preserved).

        Returns
        -------
        Palette
            Self, to allow fluent chaining.
        """
        self.data = self.data[::-1]
        return self

    def plot(
        self,
        ax=None,
        figsize=(4, 0.25),
        height=1.0,
        show_values=True,
        rasterized=False,
    ):
        """
        Plot the palette as a horizontal color bar (discrete bands).

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Axes to plot on. If None, creates a new figure.
        height : float, optional
            Height of the color bar in the plot (default: 1.0)
        show_values : bool, optional
            Whether to show value labels on x-axis (default: True)

        Notes
        -----
        This helper draws one rectangle per CPT segment using the palette's
        discrete colors. It configures useful tick marks (including a 0 line
        when the range spans negative to positive) and titles the bar with the
        palette name. It does not return a value.
        """
        if ax is None:
            _, ax = plt.subplots(figsize=figsize)

        # Plot each color segment
        for interval, color in zip(self.intervals, self.cmap.colors):
            ax.add_patch(
                Rectangle(
                    (interval.left, 0),
                    interval.length,
                    height,
                    facecolor=color,
                    zorder=1,
                )
            )

        # Labels
        if self.n_colors <= 30:
            ax.set_xticks(self.levels, minor=True)
        if self.cmin < 0 < self.cmax:
            xticks = [self.cmin, 0.0, self.cmax]
            ax.set_xticks(xticks)
        else:
            ax.set_xticks(self.value_range)
        ax.set_xlim(*self.value_range)
        ax.set_ylim(0, height)
        ax.set_yticks([])
        ax.set_title(self.name, size="medium")
        ax.tick_params(axis="x", labelsize="small")

        # Rasterize for large number of segments
        if rasterized:
            ax.set_rasterization_zorder(2)

    def scale(self, vmin: float, vmax: float):
        """
        Re-map segment boundaries to a new numeric range in place.

        Parameters
        ----------
        vmin : float
            New minimum boundary value.
        vmax : float
            New maximum boundary value.

        Notes
        -----
        - For ``kind='sequential'``, boundaries are linearly mapped from the
          original ``[cmin, cmax]`` to ``[vmin, vmax]``.
        - For ``kind='diverging'``, boundaries left of ``diverging_point`` map
          to ``[vmin, diverging_point]``, and boundaries right of
          ``diverging_point`` map to ``[diverging_point, vmax]``. Colors are not
          altered; only boundary positions are changed.
        """
        if self.kind == "diverging":
            at = self.diverging_point
            levels = self.levels
            new_levels = np.empty_like(levels, dtype=float)

            left_mask = levels < at
            right_mask = levels > at
            center_mask = ~(left_mask | right_mask)

            # Left side mapping
            if at == self.cmin:
                new_levels[left_mask] = vmin
            else:
                new_levels[left_mask] = vmin + (
                    levels[left_mask] - self.cmin
                ) / (at - self.cmin) * (at - vmin)

            # Right side mapping
            if at == self.cmax:
                new_levels[right_mask] = vmax
            else:
                new_levels[right_mask] = at + (levels[right_mask] - at) / (
                    self.cmax - at
                ) * (vmax - at)

            # Center point remains at 'at'
            new_levels[center_mask] = at

            # Assign new levels to data
            self.data[:, 0] = new_levels[:-1]
            self.data[:, 4] = new_levels[1:]

        elif self.kind == "sequential":
            denom = self.cmax - self.cmin
            if denom == 0:
                # Degenerate case: collapse to endpoints
                self.data[:, 0] = vmin
                self.data[:, 4] = vmax
            else:
                factor = (vmax - vmin) / denom
                self.data[:, 0] = vmin + (self.data[:, 0] - self.cmin) * factor
                self.data[:, 4] = vmin + (self.data[:, 4] - self.cmin) * factor

    def interpolate(self, n: int) -> None:
        """
        Interpolate to ``n`` segments in place (build a smooth version).

        Parameters
        ----------
        n : int
            Desired number of segments in the resulting palette.

        Notes
        -----
        Uses a temporary continuous colormap built from the segment endpoints,
        samples it at ``n+1`` positions, and replaces the internal ``data`` with
        ``n`` evenly spaced segments spanning the original range. Colors are
        stored as new segment endpoints (RGB in 0–255).
        """
        # Create a continuous colormap from the CPT data
        stops = []
        z0 = self.levels[0]
        z1 = self.levels[-1]
        span = (z1 - z0) if (z1 - z0) != 0 else 1.0

        for row in self.data:
            z_start, r0, g0, b0, z_end, r1, g1, b1 = row
            pos0 = (float(z_start) - z0) / span
            stops.append(
                (pos0, (int(r0) / 255.0, int(g0) / 255.0, int(b0) / 255.0))
            )

        # ensure last endpoint is included
        last = self.data[-1]
        pos1 = (float(last[4]) - z0) / span
        stops.append(
            (
                pos1,
                (
                    int(last[5]) / 255.0,
                    int(last[6]) / 255.0,
                    int(last[7]) / 255.0,
                ),
            )
        )

        cmap = LinearSegmentedColormap.from_list(
            self.name or "cpt_colormap", stops
        )

        # Sample the colormap at n
        n = n + 1  # +1 to get n segments
        colors = cmap(np.linspace(0, 1, n))[:, :3] * 255.0

        # Apply to data
        self.data = np.zeros((n - 1, 8))
        for i in range(n - 1):
            self.data[i, 0] = z0 + i * (z1 - z0) / (n - 1)
            self.data[i, 4] = z0 + (i + 1) * (z1 - z0) / (n - 1)
            self.data[i, 1:4] = colors[i]
            self.data[i, 5:8] = colors[i + 1]

    def colorbar(self, ax=None, **kwargs) -> Colorbar:
        """
        Add a Matplotlib colorbar to the provided axes using this palette.

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Target axes to attach the colorbar to. If omitted, ``ax`` is taken
            from ``kwargs['ax']`` for backward compatibility.
        **kwargs
            Additional keyword arguments forwarded to ``figure.colorbar(...)``.

        Notes
        -----
        Configures a reasonable number of major ticks and disables minor ticks.
        Returns the created Colorbar instance.

        Returns
        -------
        matplotlib.colorbar.Colorbar
            The created colorbar instance.
        """
        if ax is None:
            # Backward compatibility: accept ax via kwargs; else use current axes
            ax = kwargs.pop("ax", None)
            if ax is None:
                ax = plt.gca()
        mappable = ScalarMappable(cmap=self.cmap, norm=self.norm)
        cb = ax.figure.colorbar(mappable, ax=ax, **kwargs)

        # Use a locator for nicer ticks and refresh
        cb.locator = MaxNLocator(nbins=7)
        cb.update_ticks()
        cb.set_ticks([], minor=True)
        return cb


def read(
    filepath: str,
    kind: str = "sequential",
    diverging_point: Optional[float] = 0,
) -> Palette:
    """Parse a CPT (Color Palette Table) file into a :class:`Palette`.

    The reader supports commonly encountered CPT formats:

    - Standard 8-token segments: ``z0 r0 g0 b0  z1 r1 g1 b1``
    - GMT-style lines: ``z0 color0  z1 color1`` (colors may be named, hex, or ``r/g/b``)
    - Control points: ``z r g b`` and ``z r/g/b`` (segments are formed between adjacent points)
    - Special lines: ``N`` (NaN color). ``B``/``F`` lines are currently ignored.
    - COLOR_MODEL comments: supports ``RGB`` (default) and ``HSV`` (auto-converted to RGB)

    Path resolution is flexible: ``filepath`` may be absolute, relative, or a
    short path under the bundled cpt-city data; missing ``.cpt`` extensions are
    appended automatically.

    Parameters
    ----------
    filepath : str
        File path or short path to a CPT file.
    kind : {"sequential", "diverging"}, default "sequential"
        Logical type of the palette; stored on the resulting :class:`Palette`
        and used by :meth:`Palette.scale` to determine re-scaling behavior.
    diverging_point : float, optional
        For ``kind='diverging'``, the value around which the colormap is
        centered. Segments left/right of ``diverging_point`` are re-scaled
        independently to preserve divergence.

    Returns
    -------
    Palette
        A palette with segments, boundaries, and optional ``nan_color``.

    Examples
    --------
    Load a palette and preview it:

    >>> pal = read('cmocean/algae')
    >>> pal.n_colors, pal.value_range
    (..., (..., ...))
    """
    # Resolve the file path
    filepath = files.solve(filepath)

    # Storage for parsed data
    color_segments: List[List[float]] = []
    metadata: Dict[str, str] = {}
    nan_color: Optional[Tuple[int, int, int]] = None

    # Parsing helpers now live in pycpt.colors

    with open(filepath, "r") as file:
        prev_z: Optional[float] = None
        prev_rgb: Optional[Tuple[int, int, int]] = None

        # Loop over lines
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue

            # Parse full-line comments (metadata) before removing inline comments
            if stripped.startswith("#"):
                if "COLOR_MODEL" in stripped:
                    parts = stripped.split("=")
                    if len(parts) == 2:
                        metadata["COLOR_MODEL"] = parts[1].strip()
                continue

            # Remove inline comments after values
            line = stripped.split("#", 1)[0].strip()

            # Parse special lines
            if line.startswith("B") or line.startswith("F"):
                continue

            if line.startswith("N"):
                nan_color = parse_special_color(
                    line, metadata.get("COLOR_MODEL", "RGB")
                )
                continue

            # Parse color segment data
            parts = line.split()
            model = metadata.get("COLOR_MODEL", "RGB")

            # Format A: 8 columns (z0 r0 g0 b0 z1 r1 g1 b1)
            if len(parts) == 8:
                try:
                    z0 = float(parts[0])
                    z1 = float(parts[4])
                    r0, g0, b0 = parse_color_triplet(parts[1:4], model)
                    r1, g1, b1 = parse_color_triplet(parts[5:8], model)
                    color_segments.append([z0, r0, g0, b0, z1, r1, g1, b1])
                except Exception:
                    continue

                # Reset prev trackers when explicit segment given
                prev_z = z1
                prev_rgb = (r1, g1, b1)
                continue

            # Format B: 4 columns control point (z r g b) OR 2 columns (z r/g/b)
            if len(parts) in (2, 4):
                try:
                    z = float(parts[0])
                except ValueError:
                    # Not a numeric control point
                    continue
                try:
                    if len(parts) == 2:
                        r, g, b = parse_color_triplet([parts[1]], model)
                    else:
                        # Distinguish 4-value control point vs 'z color z color'
                        if (
                            is_number(parts[1])
                            and is_number(parts[2])
                            and is_number(parts[3])
                        ):
                            # Control point z r g b
                            r, g, b = parse_color_triplet(parts[1:4], model)
                            # Create segment with previous point if available
                            if prev_z is not None and prev_rgb is not None:
                                z0 = prev_z
                                r0, g0, b0 = prev_rgb
                                z1 = z
                                r1, g1, b1 = r, g, b
                                color_segments.append(
                                    [z0, r0, g0, b0, z1, r1, g1, b1]
                                )
                            prev_z = z
                            prev_rgb = (r, g, b)
                            continue
                        else:
                            # This is actually 'z0 color0 z1 color1'
                            z0 = z
                            c0 = parse_color_triplet([parts[1]], model)
                            try:
                                z1 = float(parts[2])
                            except ValueError:
                                continue
                            c1 = parse_color_triplet([parts[3]], model)
                            r0, g0, b0 = c0
                            r1, g1, b1 = c1
                            color_segments.append(
                                [z0, r0, g0, b0, z1, r1, g1, b1]
                            )
                            prev_z = z1
                            prev_rgb = (r1, g1, b1)
                            continue
                except Exception:
                    continue

                # If we reach here for len(parts)==2 case
                if prev_z is not None and prev_rgb is not None:
                    z0 = prev_z
                    r0, g0, b0 = prev_rgb
                    z1 = z
                    r1, g1, b1 = r, g, b
                    color_segments.append([z0, r0, g0, b0, z1, r1, g1, b1])

                prev_z = z
                prev_rgb = (r, g, b)
                continue

    if not color_segments:
        raise ValueError(f"No valid color segments found in {filepath}")

    # Convert to numpy array
    data = np.array(color_segments)

    # Internally we store RGB; record that we parsed to RGB
    if metadata.get("COLOR_MODEL", "RGB").upper() != "RGB":
        metadata["ORIGINAL_COLOR_MODEL"] = metadata.get("COLOR_MODEL")
        metadata["COLOR_MODEL"] = "RGB"

    # Extract palette name from file basename (without extension)
    palette_name = filepath.stem

    return Palette(
        data=data,
        nan_color=nan_color,
        name=palette_name,
        kind=kind,
        diverging_point=diverging_point,
    )
