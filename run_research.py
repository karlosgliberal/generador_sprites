#!/usr/bin/env python
"""Launcher for research runner.

Ensures the parent directory is on sys.path so that 'generador_sprites'
is importable as a proper package (all relative imports work).

Usage:
    python run_research.py run --line L1 --action idle
    python run_research.py test --line L1 --level smoke
"""

import sys
from pathlib import Path

# Add parent of this package to sys.path so 'generador_sprites' is importable
project_root = Path(__file__).resolve().parent
parent_dir = project_root.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from generador_sprites.research.runner import main

main()
