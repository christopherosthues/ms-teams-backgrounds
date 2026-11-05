"""Pytest configuration and shared helpers for the test suite."""

import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def make_image():
    """Return a factory that writes a small solid-color PNG to ``path``."""

    def write(path: Path, color=(200, 30, 30)) -> None:
        """Write a small solid-color PNG to ``path``."""
        Image.new("RGB", (16, 12), color).save(path)

    return write
