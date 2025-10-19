from PIL import Image
import os
from pathlib import Path

def resize_images(input_folder, output_folder, width=800, height=None, 
                  quality=85):
    """Resize all images in a folder."""
    
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(exist_ok=True)
    
    supported = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
    
    for file in input_path.iterdir():
        if file.suffix.lower() in supported:
            try:
                img = Image.open(file)
                
                # Calculate height maintaining aspect ratio
                if height is None:
                    aspect_ratio = img.height / img.width
                    height = int(width * aspect_ratio)
                
                # Resize
                resized = img.resize((width, height), Image.Resampling.LANCZOS)
                
                # Save
                output_file = output_path / file.name
                resized.save(output_file, quality=quality, optimize=True)
                
                print(f"✓ Resized: {file.name}")
                
            except Exception as e:
                print(f"✗ Error with {file.name}: {e}")
    
    print(f"\n✓ All images resized in: {output_folder}")

if __name__ == "__main__":
    resize_images("./original_images", "./resized_images", width=1920)
