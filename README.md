# HEIC to PNG/JPG Converter

This project is a Python application that scans a specified folder for HEIC image files and converts them to PNG or JPG formats while preserving quality and minimizing file size.

## Features

- Convert HEIC/HEIF files to PNG and/or JPG or HEIC formats 
- Recursive directory searching for batch processing
- Adjustable quality settings
- Progress tracking for batch conversions
- Size comparison between original and converted files
- Detailed logging

## Easiest Option - Using the Windows Installer

### Installation

1. Download the latest installer from the [Releases](https://github.com/chambj/heic-convert/releases) page
2. Run the installer and follow the prompts
3. Optionally check "Add application to PATH" to use from command line

### Using the GUI Application

The GUI provides an intuitive interface for converting HEIC images without using the command line.

1. **Launch the GUI**:
   - Double-click the "HEIC Convert" shortcut on your desktop or in the Start menu.

2. **Select Source and Output Folders**:
   - Click **Browse** next to "Source Folder" to select the folder containing your HEIC files.
   - Click **Browse** next to "Output Folder" to select where converted files will be saved (optional; defaults to a subfolder named after the chosen format).

3. **Choose Conversion Settings**:
   - Select the desired output format (JPG, PNG, HEIC, or Both). Both means JPG and PNG
   - Adjust JPG quality, PNG compression, and HEIC quality settings as needed.
   - Choose how to handle existing files (rename, overwrite, or fail).
   - Enable "Search subdirectories recursively" to process nested folders.

4. **Start Conversion**:
   - Click **Convert Files** to begin processing.
   - Monitor progress via the progress bar and log output.

5. **Cancel Conversion** (if needed):
   - Click **Stop** to cancel the ongoing conversion.


### Using the Command-line Interface

```
heic-convert [OPTIONS]
```

Options:
- `--folder`, `-f`: Folder path containing HEIC files (required)
- `--output`, `-o`: Output folder for converted images (optional)
- `--format`, `-t`: Target format: png, jpg, heic, or both (both emits png and jpg) (default: jpg)
- `--jpg-quality`, `-q`: JPEG quality (1-100, default: 90)
- `--png-compression`: PNG compression level (0-9, default: 6)
- `--existing`, `-e`: How to handle existing files: rename (add number), overwrite, or fail (default: fail)
- `--recursive`, `-r`: Recursively search for files in subdirectories
- `--resize`: Resize image by percentage (e.g., 50 for 50%) (optional)
- `--width`: Resize image to specific width (maintaining aspect ratio) (optional)
- `--height`: Resize image to specific height (maintaining aspect ratio) (optional)
- `--log-file`: File path to store logs in (optional)


```
# Convert all HEIC files in a folder to JPG
heic-convert --folder "c:\path\to\heics"

# Convert to both formats with 80% JPG quality
heic-convert --folder "c:\path\to\heics" --format both --jpg-quality 80

# Resize images to 50% of original size
heic-convert --folder "c:\path\to\heics" --resize 50

# Specify output directory and handle existing files
heic-convert --folder "c:\path\to\heics" --output "c:\output" --existing rename

# Convert all HEIC files in a folder to PNG
heic-convert --folder "c:\path\to\heics" --format png

# Convert all HEIC files in a folder and its subdirectories
heic-convert --folder "c:\path\to\heics" --recursive

```

### Resizing Options

The converter supports three methods for resizing images:

1. **Percentage resize**: `--resize 50` (reduces to 50% of original dimensions)
2. **Width-based resize**: `--width 1920` (sets width to 1920px, height scales proportionally)
3. **Height-based resize**: `--height 1080` (sets height to 1080px, width scales proportionally)

**Note**: If you specify multiple resize options, the following priority will be applied:
1. Percentage resize (`--resize`)
2. Width-based resize (`--width`)
3. Height-based resize (`--height`)

Only one resize option will be applied at a time. Aspect ratio is always preserved.


## From Source

### Setting up a Virtual Environment

1. Clone or download this repository to your local machine
2. Open a command prompt and navigate to the project directory
3. Create a virtual environment:

```bash
# Navigate to project directory
cd path\to\HEICConvert\heic-convert

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
 source venv/bin/activate
```

### Installing Dependencies

for usage:
pillow>=9.0.0
pillow-heif>=0.10.0
tqdm>=4.62.0
psutil>=5.9.0
piexif>=1.1.3

for development
pytest>=7.0.0
pytest-cov>=2.12.1

Once the virtual environment is activated, install the required packages:

```bash
pip install -r requirements.txt
```

or

```bash
pip install -r requirements-dev.txt
```


### Usage Examples

Convert all HEIC files in a folder to JPG:
```bash
python -m src.main --folder "C:\Users\Photos\iPhone"
```

Convert all HEIC files in a folder and its subfolders to JPG:
```bash
python -m src.main --folder "C:\Users\Photos" --recursive
```

Convert all HEIC files in a folder to both PNG and JPG:
```bash
python -m src.main --folder "C:\Users\Photos\iPhone" --format both
```

Convert to JPG only with 85% quality:
```bash
python -m src.main --folder "C:\Users\Photos\iPhone" --format jpg --quality 85
```

Convert to PNG only and save to a specific output folder:
```bash
python -m src.main --folder "C:\Users\Photos\iPhone" --format png --output "C:\Users\Photos\Converted"
```

Resize images to 50% of original size:
```bash
python -m src.main --folder "C:\Users\Photos\iPhone" --resize 50
```

Resize images to specific width (height adjusts proportionally):
```bash
python -m src.main --folder "C:\Users\Photos\iPhone" --width 1920
```

Set PNG compression level (higher = smaller files, slower processing):
```bash
python -m src.main --folder "C:\Users\Photos\iPhone" --format png --png-compression 9
```

Handle existing files by failing conversion if conflicts exist:
```bash
python -m src.main --folder "C:\Users\Photos\iPhone" --existing fail
```

Overwrite any existing files with the same name:
```bash
python -m src.main --folder "C:\Users\Photos\iPhone" --existing overwrite
```

Add a number to the output file if there are any existing files with the same name:
```bash
python -m src.main --folder "C:\Users\Photos\iPhone" --existing rename
```

Create a log file while it runs:
```bash
python -m src.main --folder "C:\Users\Photos\iPhone" --log-file "conversion.log"
```

## Building from Source

### Prerequisites

- Python 3.7+
- PyInstaller
- Inno Setup (for creating installer)

### Build Steps

1. **Install dependencies**
   ```
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **Create executable**
   ```
   pyinstaller heic_convert.spec
   ```
   
3. **Create installer** (optional)
   - Install [Inno Setup](https://jrsoftware.org/isinfo.php)
   - Open Inno Setup Compiler
   - Open the `installer.iss` file
   - Click Build > Compile

The compiled installer will be in the `installer` folder.


## Troubleshooting

- If you encounter `ModuleNotFoundError`, make sure you've activated the virtual environment and installed all dependencies.
- For permission errors, ensure you have write access to the output directory.
- Check the log file `heic_converter.log` for detailed error information.

## Testing

This project uses pytest for testing. To run the tests:

1. Make sure you have activated your virtual environment
2. Install test dependencies:
   ```bash
   pip install pytest
   ```
3. Run the tests:
   ```bash
   pytest
   ```

For more detailed test output:
```bash
pytest -v
```

### Running the GUI Tests

These tests can be run with pytest:

```
pytest tests/test_gui.py -v
```

- The tests above use mocking to avoid real file dialogs and user interaction
- The test_conversion_thread_created test verifies that a thread is created but doesn't run it
- These tests don't verify the visual appearance


## License

This project is licensed under the MIT License - see the LICENSE file for details. Additional terms you must agree to in order to use this project are included in terms.md.


## Contributing

If you would like to contribute to this project, please fork the repository and submit a pull request with your changes.
