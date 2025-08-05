#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(script):
    path = ROOT / script
    print(f"\n▶ {script}")
    # always call with the same Python interpreter running this file
    result = subprocess.run([sys.executable, str(path)], cwd=ROOT)
    if result.returncode == 0:
        print(f"✓ {script} done")
    else:
        print(f"✗ {script} failed (exit {result.returncode})")

if __name__ == "__main__":
    for s in [
        "garmin-activities2.py",
        "personal-records.py",
        "sleep-data.py",
        "daily-steps.py",
        "health-data.py",
    ]:
        run(s)
