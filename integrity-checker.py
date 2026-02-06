import hashlib
import os

def calculate_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def check_integrity(directory):
    print(f"Checking files in {directory}...")
    for root, dirs, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                file_hash = calculate_hash(filepath)
                print(f"{filename}: {file_hash}")
            except Exception as e:
                print(f"Error reading {filename}: {e}")

check_integrity("./test_directory")
