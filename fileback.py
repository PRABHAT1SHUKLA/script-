import shutil
import os
from datetime import datetime
import zipfile

source = os.path.expanduser("~/Documents")  # Change source folder
backup_dir = os.path.expanduser("~/Backups")
os.makedirs(backup_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
zip_name = os.path.join(backup_dir, f"backup_{timestamp}.zip")

with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(source):
        for file in files:
            zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), source))
print(f"Backup created: {zip_name}")
