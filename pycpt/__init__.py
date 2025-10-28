"""pycpt: read and use CPT (Color Palette Table) colormaps in Python."""

from .cpt import Palette, read
from . import files, colors
from .files import CPT_DIRECTORY, update_bundle, get_family, list_families

__all__ = [
    "Palette",
    "read",
    "files",
    "colors",
    "CPT_DIRECTORY",
    "update_bundle",
    "get_family",
    "list_families",
]
