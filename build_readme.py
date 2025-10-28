#!/usr/bin/env python3
"""
Build README.md from README.ipynb with GitHub URLs for images.
"""
import os
import re
import subprocess
import sys

# GitHub repository info
GITHUB_USER = "leonard-seydoux"
GITHUB_REPO = "pycpt-city"
GITHUB_BRANCH = "main"
BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"


def convert_notebook():
    """Convert notebook to markdown with SVG output."""
    print("Converting notebook to markdown (SVG format)...")

    # Use jupyter from the same environment as this script
    venv_jupyter = os.path.join(os.path.dirname(sys.executable), "jupyter")

    # Convert without executing (uses existing cell outputs with SVG format)
    result = subprocess.run(
        [
            venv_jupyter,
            "nbconvert",
            "--to",
            "markdown",
            "README.ipynb",
            "--output",
            "README.md",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print("✓ Notebook converted")
    return True


def replace_image_urls():
    """Replace local image paths with GitHub raw URLs."""
    print("Replacing image URLs...")

    with open("README.md", "r") as f:
        content = f.read()

    # Replace logo
    content = re.sub(
        r'src="logo/logo\.gif"', f'src="{BASE_URL}/logo/logo.gif"', content
    )

    # Replace README_files images (support both .svg and .png, but prefer .svg)
    content = re.sub(
        r"!\[(.*?)\]\(README_files/(.*?)\.(png|svg)\)",
        rf"![\1]({BASE_URL}/README_files/\2.svg)",
        content,
    )

    with open("README.md", "w") as f:
        f.write(content)

    print("✓ Image URLs replaced")


def main():
    """Main build process."""
    if convert_notebook():
        replace_image_urls()
        print("\n✅ README.md built successfully!")
        print(f"Images will be served from: {BASE_URL}")
    else:
        print("\n❌ Build failed")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
