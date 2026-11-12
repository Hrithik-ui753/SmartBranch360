#!/usr/bin/env python3
"""SmartBranch360 Network Assurance & Security Engine CLI (Compatibility wrapper)."""

import argparse
from pathlib import Path
import sys

# Add parent directory to path so assurance_engine is accessible
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from check_network import main

if __name__ == "__main__":
    sys.exit(main())
