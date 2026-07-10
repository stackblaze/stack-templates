#!/usr/bin/env python3
"""Thin wrapper — delegates to the template-bundled seeder."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "services" / "mattermost" / "seed-demo.py"

if __name__ == "__main__":
    sys.argv[0] = str(TARGET)
    runpy.run_path(str(TARGET), run_name="__main__")
