"""Color parsing helpers for CPT files.

This module centralizes color-related utilities used by the CPT reader:
- clamp8(x): clamp to [0, 255]
- is_number(token): robust numeric check for tokens
- resolve_named(name): resolve named/hex colors via Matplotlib
- parse_color_triplet(tokens, model): parse RGB/HSV triplets or a single slash token
- parse_special_color(line, model): parse N-line special color (B/F ignored)

All colors are returned as integer RGB triples in 0–255.
"""

from __future__ import annotations

from typing import Iterable, Tuple

import re
from matplotlib import colors as mcolors


def clamp8(value: float) -> int:
    """Clamp a numeric value to the 8-bit range [0, 255] and return int."""
    return int(max(0, min(255, round(float(value)))))


def is_number(token: str) -> bool:
    """Return True if token looks like a number (int/float)."""
    try:
        float(token)
        return True
    except Exception:
        return False


def resolve_named(name: str) -> Tuple[int, int, int]:
    """Resolve a named or hex color to an (r, g, b) int triple in 0–255.

    Uses Matplotlib's color database for CSS/XKCD names and hex parsing.
    """
    key = name.strip()
    rgbf = mcolors.to_rgb(key)  # raises if not resolvable
    return tuple(clamp8(c * 255.0) for c in rgbf)  # type: ignore[return-value]


def _parse_rgb_tokens(tokens: Iterable[str]) -> Tuple[int, int, int]:
    r, g, b = (float(t) for t in tokens)
    return clamp8(r), clamp8(g), clamp8(b)


def _parse_hsv_tokens(tokens: Iterable[str]) -> Tuple[int, int, int]:
    # Expect H S V in 0–360, 0–1, 0–1 or 0–100, 0–100, 0–100
    h, s, v = (float(t) for t in tokens)
    # Normalize to [0, 1]
    if s > 1 or v > 1:
        s /= 100.0
        v /= 100.0
    if h > 1:
        h = (h % 360.0) / 360.0
    rgbf = mcolors.hsv_to_rgb((h, s, v))
    return tuple(clamp8(c * 255.0) for c in rgbf)  # type: ignore[return-value]


def parse_color_triplet(
    tokens: Iterable[str], model: str
) -> Tuple[int, int, int]:
    """Parse a color from tokens under a color model.

    Accepts:
    - 3 numeric tokens: r g b or h s v depending on model
    - single token with slashes: "r/g/b" or "h/s/v"
    - named/hex color when passed as a single token and model is RGB
    """
    parts = list(tokens)
    color_model = (model or "RGB").upper()

    if len(parts) == 1:
        token = parts[0]
        if "/" in token:
            pieces = token.split("/")
            if len(pieces) != 3:
                raise ValueError(f"Invalid slash color token: {token}")
            return (
                _parse_rgb_tokens(pieces)
                if color_model == "RGB"
                else _parse_hsv_tokens(pieces)
            )
        if color_model == "RGB":
            # Allow named/hex here
            return resolve_named(token)
        raise ValueError(f"Invalid token for HSV model: {token}")

    if len(parts) == 3:
        return (
            _parse_rgb_tokens(parts)
            if color_model == "RGB"
            else _parse_hsv_tokens(parts)
        )

    raise ValueError(f"Unexpected token count for color: {parts}")


def parse_special_color(line: str, model: str) -> Tuple[int, int, int]:
    """Parse an N line specifying the NaN color.

    Example forms:
    - "N r g b"
    - "N r/g/b"
    - "N name" or "N #RRGGBB" (RGB model)
    """
    tokens = line.split()
    if len(tokens) < 2:
        raise ValueError(f"Invalid special color line: {line}")
    return parse_color_triplet(tokens[1:], model)
