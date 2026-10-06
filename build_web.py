"""Rebuild the webplayer using only main.py as the game payload."""
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parent
staging = root / "build" / "crazy-asteroids"
staging.mkdir(parents=True, exist_ok=True)
shutil.copy2(root / "main.py", staging / "main.py")
subprocess.run([sys.executable, "-m", "pygbag", "--build", str(staging)], check=True)
for path in (staging / "build" / "web").iterdir():
    if path.is_file():
        shutil.copy2(path, root / path.name)
