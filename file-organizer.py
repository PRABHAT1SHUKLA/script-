import os
import shutil
from pathlib import Path

def organize_files(directory="."):
    """Organize files in directory by extension."""
    
    # File type categories
    categories = {
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
        "Documents": [".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx"],
        "Videos": [".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv"],
        "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
        "Code": [".py", ".js", ".java", ".cpp", ".html", ".css", ".json"],
        "Others": []
    }
    
    directory = Path(directory)
    
    for file in directory.iterdir():
        if file.is_file():
            extension = file.suffix.lower()
            
            # Find category
            category = "Others"
            for cat, exts in categories.items():
                if extension in exts:
                    category = cat
                    break
            
            # Create category folder
            category_path = directory / category
            category_path.mkdir(exist_ok=True)
            
            # Move file
            try:
                shutil.move(str(file), str(category_path / file.name))
                print(f"Moved: {file.name} → {category}/")
            except Exception as e:
                print(f"Error moving {file.name}: {e}")
    
    print("\n✓ Organization complete!")

if __name__ == "__main__":
    # Organize Downloads folder
    downloads = Path.home() / "Downloads"
    organize_files(downloads)
