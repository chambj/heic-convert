import os
import subprocess
import sys
from pathlib import Path

def package_gui():
    """Package the GUI application as an executable."""
    # Get the root directory of the project
    root_dir = Path(__file__).parent.absolute()
    
    # Icon path
    icon_path = os.path.join(root_dir, "resources", "heic-convert.ico")
    
    # Verify the icon exists first
    if not os.path.exists(icon_path):
        print(f"WARNING: Icon file not found at {icon_path}")
        print("Looking for any .ico files in resources directory:")
        resources_dir = os.path.join(root_dir, "resources")
        if os.path.exists(resources_dir):
            for file in os.listdir(resources_dir):
                if file.endswith('.ico'):
                    print(f"  Found: {file}")
                    icon_path = os.path.join(resources_dir, file)
    
    # Fix the resources path format for Windows
    resources_path = os.path.join(root_dir, "resources")
    resources_spec = f"{resources_path};resources"
    
    # Build the PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",               # Create a single executable
        "--windowed",              # No console window
        f"--icon={icon_path}",     # Use custom icon
        "--name=heic-convert-gui", # GUI executable name
        "--add-data", resources_spec, # Include resources
        os.path.join(root_dir, "src", "gui.py")  # Main GUI script
    ]
    
    print("Creating GUI executable with command:")
    print(" ".join(cmd))
    subprocess.call(cmd)

if __name__ == "__main__":
    package_gui()