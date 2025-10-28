#!/usr/bin/env python3
"""
.ipynb -> .md exporter (no external runtime deps).
- Writes Markdown to a target file (e.g., README.md)
- Saves embedded output images (image/png, image/jpeg) to a target images directory
- Includes text/plain outputs for code cells

CLI usage examples:
  python -m pycpt.export_md notebooks/example.ipynb --out README.md --images-dir images

Notes:
- Attachments in markdown cells are not handled.
- Rich HTML outputs are ignored; consider nbconvert if you need full fidelity.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_ipynb(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(text)


def cell_to_markdown(
    cell: Dict[str, Any], assets_dir: Path, link_base: Path, idx: int
) -> str:
    ctype = cell.get("cell_type")
    source = cell.get("source", [])
    if isinstance(source, list):
        src = "".join(source)
    else:
        src = str(source or "")

    if ctype == "markdown":
        return src if src.endswith("\n") else src + "\n"

    if ctype == "code":
        lines: List[str] = []
        # Source block
        lines.append("```python\n")
        lines.append(src)
        if not src.endswith("\n"):
            lines.append("\n")
        lines.append("```\n\n")

        # Outputs (text/plain + images)
        outputs = cell.get("outputs", [])
        img_count = 0
        for out in outputs:
            # Text
            text = None
            if "text" in out:
                if isinstance(out["text"], list):
                    text = "".join(out["text"]) if out["text"] else None
                else:
                    text = str(out["text"]) if out["text"] else None
            elif "data" in out and isinstance(out["data"], dict):
                data = out["data"]
                if "text/plain" in data:
                    t = data["text/plain"]
                    if isinstance(t, list):
                        text = "".join(t)
                    else:
                        text = str(t)

            if text:
                lines.append("```text\n")
                lines.append(text)
                if not text.endswith("\n"):
                    lines.append("\n")
                lines.append("```\n\n")

            # Images
            if "data" in out and isinstance(out["data"], dict):
                data = out["data"]
                for mime in ("image/png", "image/jpeg"):
                    if mime in data:
                        b64 = data[mime]
                        if isinstance(b64, list):
                            b64 = "".join(b64)
                        try:
                            raw = base64.b64decode(b64)
                        except Exception:
                            continue
                        ext = ".png" if mime == "image/png" else ".jpg"
                        img_name = f"cell{idx:03d}_{img_count}{ext}"
                        img_path = assets_dir / img_name
                        ensure_dir(assets_dir)
                        with img_path.open("wb") as imgf:
                            imgf.write(raw)
                        rel = os.path.relpath(img_path, start=link_base)
                        lines.append(f"![output]({rel})\n\n")
                        img_count += 1

        return "".join(lines)

    # Other cell types ignored
    return ""


def convert_notebook(
    ipynb_path: Path,
    out_md: Path | None = None,
    assets_dir: Path | None = None,
) -> Path:
    nb = read_ipynb(ipynb_path)
    base = ipynb_path.stem
    if out_md is None:
        out_md = Path("docs") / f"{base}.md"
        ensure_dir(out_md.parent)
    else:
        ensure_dir(out_md.parent)

    if assets_dir is None:
        assets_dir = out_md.parent / f"{base}_files"

    parts: List[str] = []
    parts.append(f"<!-- Auto-generated from {ipynb_path} -->\n\n")

    cells = nb.get("cells", [])
    for i, cell in enumerate(cells, start=1):
        md = cell_to_markdown(cell, assets_dir, out_md.parent, i)
        parts.append(md)

    write_text(out_md, "".join(parts))
    return out_md


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Export .ipynb to Markdown")
    parser.add_argument("notebooks", nargs="+", help="Notebook paths (.ipynb)")
    parser.add_argument(
        "--out",
        help="Output Markdown file (only valid when a single notebook is provided)",
    )
    parser.add_argument(
        "--images-dir",
        help="Directory to place extracted images (default: alongside output as <base>_files)",
    )
    args = parser.parse_args(argv[1:])

    if args.out and len(args.notebooks) != 1:
        print(
            "--out is only supported when exporting a single notebook",
            file=sys.stderr,
        )
        return 2

    for nb_path in args.notebooks:
        path = Path(nb_path)
        if not path.exists():
            print(f"Skipping missing: {path}", file=sys.stderr)
            continue

        out_md = Path(args.out) if args.out else None
        assets_dir = Path(args.images_dir) if args.images_dir else None
        out = convert_notebook(path, out_md=out_md, assets_dir=assets_dir)
        print(f"Wrote {out}")
    return 0


def cli() -> None:
    raise SystemExit(main(sys.argv))
