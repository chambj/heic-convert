# Save this as a script in your project directory and run it
from PIL import Image
import os

# Folder containing the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Source image (PNG or other format)
source_image = os.path.join(script_dir, "resources", "heic-convert.png")

# Target ICO file path
target_ico = os.path.join(script_dir, "resources", "heic-convert.ico") 

# Open source image
img = Image.open(source_image)

# Create a multi-resolution ICO file
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)]
img.save(target_ico, format='ICO', sizes=icon_sizes)

print(f"Created ICO file at: {target_ico}")