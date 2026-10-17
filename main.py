#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for Rose (delegates to main package)
"""

import sys
from pathlib import Path

# Ensure the project root is in sys.path for proper package resolution
# This fixes import issues when running from different directories
# Only needed in development mode (PyInstaller handles paths automatically)
if not getattr(sys, 'frozen', False):
    _project_root = Path(__file__).parent.absolute()
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

# Renderer process must never initialize app locks, Pengu, skins or configuration.
if __name__ == '__main__' and sys.argv[1:] == ['--overlay-worker']:
    from sexo2.overlay.worker_entry import entry as overlay_worker
    raise SystemExit(overlay_worker())

# Import from the modularized main package
from main import main

if __name__ == "__main__":
        main()
