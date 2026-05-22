"""
run.py  –  Start the HoriGene Flask backend.

Usage:
    python run.py

The server starts on http://localhost:5000
On first run it automatically ingests all files in ../data/
"""

import os
import sys

# Make sure the backend/ folder is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.loader import load_all

app = create_app()

if __name__ == "__main__":
    print("=" * 60)
    print("  HoriGene Backend")
    print("=" * 60)
    print("[STARTUP] Running initial data load...")
    summary = load_all()
    print(f"[STARTUP] Loaded {summary['proteins_added']} proteins, "
          f"{summary['domains_added']} domains, "
          f"{summary['sites_added']} sites, "
          f"{summary['strains_added']} strains.")
    if summary["errors"]:
        print(f"[STARTUP] Warnings: {summary['errors']}")
    print("[STARTUP] Starting Flask on http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
