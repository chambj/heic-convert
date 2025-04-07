import subprocess
import sys

def package_all():
    """Package both GUI and CLI applications."""
    try:
        # Ensure PyInstaller is installed
        import PyInstaller
    except ImportError:
        print("PyInstaller is not installed. Installing it now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Package GUI
    print("\n=== PACKAGING GUI APPLICATION ===\n")
    subprocess.call([sys.executable, "package_gui.py"])
    
    # Package CLI
    print("\n=== PACKAGING CLI APPLICATION ===\n")
    subprocess.call([sys.executable, "package_cli.py"])
    
    print("\nPackaging complete! Your executables are in the 'dist' folder.")
    print("Now you can run the Inno Setup script to create the installer.")

if __name__ == "__main__":
    package_all()