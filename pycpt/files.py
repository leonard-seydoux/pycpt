"""Path resolution helpers for CPT assets bundled with pycpt.

This module centralizes convenience utilities for locating CPT files in the
bundled ``cpt-city`` archive as well as resolving arbitrary user-provided
paths. These helpers are used transparently by :func:`pycpt.read` but can also
be called directly when building custom workflows.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    # Python 3.11+
    from importlib.resources import files as _pkg_files
except Exception:  # pragma: no cover
    _pkg_files = None  # type: ignore

CPT_BUNDLE_URL = (
    "http://seaviewsensing.com/pub/cpt-city/pkg/cpt-city-cpt-2.27.zip"
)


def _discover_bundle_dir() -> Path:
    """Discover the on-disk location of the bundled cpt-city directory.

    Resolution priority:
    1. Explicit override via environment variable ``PYCPT_BUNDLE_DIR``.
    2. A directory named ``cpt-city`` shipped alongside the installed package
       (i.e., inside the ``pycpt`` package directory).
    3. A repository/development layout: two levels up from this file joined
       with ``cpt-city`` (repo_root/cpt-city).

    Returns
    -------
    pathlib.Path
        Path to the discovered bundle directory.

    Raises
    ------
    FileNotFoundError
        If no plausible bundle directory could be found.
    """
    # 1) Environment override
    env_dir = os.environ.get("PYCPT_BUNDLE_DIR")
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        if p.exists() and p.is_dir():
            return p

    # 2) Inside the installed package (pycpt/cpt-city)
    if _pkg_files is not None:
        try:
            traversable = _pkg_files(__package__).joinpath("cpt-city")
            # Convert to filesystem Path if backed by the filesystem
            p = Path(str(traversable))
            if p.exists() and p.is_dir():
                return p
        except Exception:
            pass

    # 3) Development layout: repo_root/cpt-city
    dev_candidate = Path(__file__).resolve().parent.parent / "cpt-city"
    if dev_candidate.exists() and dev_candidate.is_dir():
        return dev_candidate

    raise FileNotFoundError(
        "Could not locate bundled 'cpt-city' directory. Set PYCPT_BUNDLE_DIR "
        "to override, or install a distribution that includes the data."
    )


# Public entry point for users
def bundle_location() -> Path:
    """Return the absolute path to the bundled cpt-city directory.

    This path can be used to browse families, inspect licenses, or point other
    tools at the on-disk CPT archive.
    """
    return _discover_bundle_dir()


# Backward-compatible alias used internally
CPT_DIRECTORY = bundle_location()


def update_bundle(
    url: str = CPT_BUNDLE_URL, families: str | None = None
) -> None:
    """Update the bundled CPT_DIRECTORY from a remote URL.

    This function downloads and extracts a ZIP archive from the specified URL,
    replacing the existing CPT_DIRECTORY contents. It is intended for updating
    the bundled cpt-city archive to a newer version.

    Parameters
    ----------
    url : str
        URL of the ZIP archive containing the updated cpt-city files.

    Raises
    ------
    Exception
        If the download or extraction fails.
    """
    import requests
    import zipfile
    import io
    import shutil

    # Download the ZIP archive
    response = requests.get(url)
    response.raise_for_status()

    # Check that the user has rights to modify the CPT_DIRECTORY
    if not CPT_DIRECTORY.parent.exists() or not CPT_DIRECTORY.parent.is_dir():
        raise PermissionError(
            f"Cannot write to directory: {CPT_DIRECTORY.parent}"
        )

    # Extract the ZIP archive to a temporary location
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        # directory = CPT_DIRECTORY.parent
        if CPT_DIRECTORY.exists():
            shutil.rmtree(CPT_DIRECTORY)
        if families is not None:
            members = []
            for member in zip_file.namelist():
                for family in families:
                    if family in member:
                        members.append(member)
            zip_file.extractall(CPT_DIRECTORY.parent, members)
        else:
            zip_file.extractall(CPT_DIRECTORY.parent)


def solve(filepath: str | Path) -> Path:
    """Resolve a CPT filepath robustly.

    The function tries several strategies, in order:

    1. Use ``filepath`` as-is if it exists.
    2. Append the ``.cpt`` extension if missing.
    3. Look relative to the bundled :data:`CPT_DIRECTORY`.
    4. Look relative to :data:`CPT_DIRECTORY` with ``.cpt`` appended.
    5. As a last resort, glob under :data:`CPT_DIRECTORY` for the first match
       whose filename starts with the provided stem.

    Parameters
    ----------
    filepath : str or pathlib.Path
        Absolute path, relative path, or short path under :data:`CPT_DIRECTORY`.

    Returns
    -------
    pathlib.Path
        A resolved existing path to a CPT file.

    Raises
    ------
    FileNotFoundError
        If no matching file can be found using the strategies above.
    """
    # Convert to Path if it's a string
    if isinstance(filepath, str):
        filepath = Path(filepath)

    # Check if path exist
    if filepath.exists():
        return filepath

    # Try adding .cpt extension
    alt_path = filepath.with_suffix(".cpt")
    if alt_path.exists():
        return alt_path

    # Try relative to CPT_DIRECTORY
    alt_path = CPT_DIRECTORY / filepath
    if alt_path.exists():
        return alt_path

    # Try relative to CPT_DIRECTORY with .cpt extension
    alt_path = CPT_DIRECTORY / filepath.with_suffix(".cpt")
    if alt_path.exists():
        return alt_path

    # Try check the first file that matches the name in CPT_DIRECTORY and its subdirectories
    matches = list(CPT_DIRECTORY.rglob(f"{filepath.name}*"))
    if matches:
        return matches[0]

    # If none of the above worked, raise an error
    raise FileNotFoundError(f"Could not find file: {filepath}")


def get_family(family: str) -> list[Path]:
    """List CPT files within a specific subdirectory of :data:`CPT_DIRECTORY`.

    Parameters
    ----------
    family : str
        Name of a subdirectory under :data:`CPT_DIRECTORY` (e.g., ``"wkp"``).

    Returns
    -------
    list of str
        Filepaths (as strings) to all ``.cpt`` files found recursively under
        the family directory.

    Raises
    ------
    FileNotFoundError
        If the family directory does not exist or is not a directory.
    """
    family_dir = CPT_DIRECTORY / family
    if not family_dir.exists() or not family_dir.is_dir():
        raise FileNotFoundError(f"Family directory not found: {family_dir}")
    cpt_files = list(family_dir.rglob("*.cpt"))
    return [str(f) for f in cpt_files]


def list_families() -> list[str]:
    """List available CPT families (subdirectories) in :data:`CPT_DIRECTORY`.

    Returns
    -------
    list of str
        Names of all subdirectories under :data:`CPT_DIRECTORY` that contain
        CPT files.
    """
    families = []
    for item in CPT_DIRECTORY.iterdir():
        if item.is_dir():
            families.append(item.name)
    return families
