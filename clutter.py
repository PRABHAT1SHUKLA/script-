import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

desktop = Path.home() / "Desktop"
clutter_dir = desktop / "Clutter"
clutter_dir.mkdir(exist_ok=True)
cutoff = datetime.now() - timedelta(days=7)

for file in desktop.iterdir():
    if file.is_file() and file.stat().st_mtime < cutoff.timestamp():
        shutil.move(str(file), clutter_dir / file.name)
        print(f"Moved {file.name} to Clutter")
