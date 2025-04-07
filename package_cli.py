import os
import subprocess
import sys
from pathlib import Path

def package_cli():
    """Package the CLI application as an executable."""
    # Get the root directory of the project
    root_dir = Path(__file__).parent.absolute()
    
    # Icon path
    icon_path = os.path.join(root_dir, "resources", "heic-convert.ico")
    
    # Build the PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",               # Create a single executable
        "--console",               # Include console window for CLI
        f"--icon={icon_path}",     # Use custom icon
        "--name=heic-convert",     # CLI executable name
        "--add-data", f"{os.path.join(root_dir, 'resources')}:resources", # Include resources
        os.path.join(root_dir, "src", "main.py")  # Main CLI script
    ]
    
    print("Creating CLI executable...")
    subprocess.call(cmd)

if __name__ == "__main__":
    package_cli()