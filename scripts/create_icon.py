from PIL import Image
import os
from pathlib import Path

def create_ico_file():
    """Create a proper multi-resolution ICO file."""
    resources_dir = Path(__file__).parent / "resources"
    
    # Check if resources dir exists
    if not os.path.exists(resources_dir):
        os.makedirs(resources_dir)
        print(f"Created resources directory: {resources_dir}")
    
    # Find the source image - could be .png, .jpg, etc.
    source_image = None
    for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
        for file in os.listdir(resources_dir):
            if file.endswith(ext) and not file.startswith('heic-convert'):
                source_image = os.path.join(resources_dir, file)
                break
        if source_image:
            break
    
    if not source_image:
        print("No source image found in resources directory.")
        print("Please place an image file in the resources directory.")
        return
    
    # Target ico file
    ico_file = os.path.join(resources_dir, "heic-convert.ico")
    
    # Create the icon with multiple resolutions
    img = Image.open(source_image)
    img.save(ico_file, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
    
    print(f"Created icon file: {ico_file}")
    print(f"With sizes: 16x16, 32x32, 48x48, 64x64, 128x128")

if __name__ == "__main__":
    create_ico_file()