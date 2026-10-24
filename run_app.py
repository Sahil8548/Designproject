#!/usr/bin/env python3
"""Convenience launcher for the UniTime Streamlit application."""
import sys
from pathlib import Path

# Add project root to sys.path so unitime_app can be imported directly
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from unitime_app.app import main

if __name__ == "__main__":
    main()
