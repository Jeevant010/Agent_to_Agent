#!/usr/bin/env python3
"""
scripts/run_local_audit.py (Root Runner Shim)

Delegates directly to scripts.runners.run_local_audit.
Preserves existing CLI usage: `python scripts/run_local_audit.py`
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from runners.run_local_audit import main

if __name__ == "__main__":
    main()
