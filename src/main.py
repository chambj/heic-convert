"""
HEIC Converter CLI

A command-line utility to convert HEIC/HEIF images to JPG or PNG formats.
"""
import os
import sys
import logging
import argparse
from pathlib import Path
from tqdm import tqdm
from src.converter import HeicConvert  
from concurrent.futures import ThreadPoolExecutor

# Update the logging configuration
def setup_logging(log_file=None):
    """
    Configure logging with different levels for console and file.
    
    Args:
        log_file: Path to log file or None to disable file logging
    """
    # Create formatters
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_formatter = logging.Formatter("%(message)s")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything
    
    # Clear any existing handlers (important for repeated calls)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler - only INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler only if a log file is specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    return logging.getLogger(__name__)

logger = setup_logging()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Convert HEIC images to PNG or JPG")
    parser.add_argument("--folder", "-f", help="Folder path containing HEIC files")
    parser.add_argument("--output", "-o", help="Output folder for converted images")
    parser.add_argument("--format", "-t", choices=["png", "jpg", "both"], default="jpg",
                        help="Target format: png, jpg, or both (default: jpg)")
    parser.add_argument("--jpg-quality", "-q", type=int, default=90, 
                        help="JPEG quality (1-100, default: 90)")
    parser.add_argument("--png-compression", type=int, default=6, choices=range(10),
                        help="PNG compression level (0-9, default: 6)")
    parser.add_argument("--existing", "-e", choices=["rename", "overwrite", "fail"], default="fail",
                        help="How to handle existing files: rename (add number), overwrite, or fail (default: fail)")
    parser.add_argument("--log-file", help="Save logs to specified file (default: no file logging)")
    
    resize_group = parser.add_mutually_exclusive_group()
    resize_group.add_argument("--resize", type=int, help="Resize image by percentage (e.g., 50 for 50%)")
    resize_group.add_argument("--width", type=int, help="Resize image to specific width (maintaining aspect ratio)")
    resize_group.add_argument("--height", type=int, help="Resize image to specific height (maintaining aspect ratio)")
    
    return parser.parse_args()

# Add this function after parse_arguments in main.py
def validate_format_arguments(args):
    """Validate that format-specific arguments match the selected format."""
    if args.format == "png" and args.jpg_quality != 90:  # 90 is the default
        logger.warning("--jpg-quality parameter was specified but will be ignored since format is 'png'")
    
    if args.format == "jpg" and args.png_compression != 6:  # 6 is the default
        logger.warning("--png-compression parameter was specified but will be ignored since format is 'jpg'")
    
    return args

def check_system_resources():
    """Check if system has enough resources to continue."""
    import psutil
    # If available memory is less than 500MB, warn the user
    # this has never been tested. so YMMV.
    if psutil.virtual_memory().available < 500 * 1024 * 1024:
        logger.warning("System is low on memory. Conversion of large files may fail.")
        return False
    return True

def convert_file(heic_file, args, heic_converter):
    """Convert a single HEIC file."""
    try:
        heic_size = Path(heic_file).stat().st_size / (1024 * 1024)
        logger.debug(f"Converting file: {heic_file} ({heic_size:.2f} MB)")
        
        converted_files = []
        
        if args.format in ["png", "both"]:
            # Pass args to convert_to_png
            png_path = heic_converter.convert_to_png(heic_file, args)
            png_size = Path(png_path).stat().st_size / (1024 * 1024)
            logger.debug(f"PNG size: {png_size:.2f} MB")
            converted_files.append(png_path)
        
        if args.format in ["jpg", "both"]:
            # Pass args to convert_to_jpg
            jpg_path = heic_converter.convert_to_jpg(heic_file, args)
            jpg_size = Path(jpg_path).stat().st_size / (1024 * 1024)
            logger.debug(f"JPG size: {jpg_size:.2f} MB")
            converted_files.append(jpg_path)
            
        return converted_files
    
    except Exception as e:
        logger.error(f"Failed to convert {heic_file}: {str(e)}")
        return []

def main():
    """Main function to convert HEIC files."""
    args = parse_arguments()
    
    # Setup logging - only log to file if specified
    global logger
    logger = setup_logging(args.log_file)
    
    args = validate_format_arguments(args)
    
    # Get folder path from arguments or user input
    folder_path = args.folder
    if not folder_path:
        folder_path = input("Enter the folder path to scan for HEIC files: ")
    
    # Validate folder path
    if not os.path.isdir(folder_path):
        logger.error(f"The specified path '{folder_path}' is not a valid directory.")
        return 1

    # Initialize converter
    heic_converter = HeicConvert(output_dir=args.output, jpg_quality=args.jpg_quality, 
                                   existing_mode=args.existing)
    
    try:
        # Get list of HEIC files
        heic_files = heic_converter.list_heic_files(folder_path)
        
        if not heic_files:
            logger.error("No HEIC files found in the specified directory.")
            return 0
        
        logger.info(f"Found {len(heic_files)} HEIC files to convert")
        
        success_count = 0
        failure_count = 0
        converted_files = []
        
        # Convert files with progress bar
        for heic_file in tqdm(heic_files, desc="Converting", unit="file"):
            try:
                heic_size = Path(heic_file).stat().st_size / (1024 * 1024)
                logger.debug(f"Converting file: {heic_file} ({heic_size:.2f} MB)")
                
                if args.format in ["png", "both"]:
                    png_path = heic_converter.convert_to_png(heic_file, args)
                    png_size = Path(png_path).stat().st_size / (1024 * 1024)
                    logger.debug(f"PNG size: {png_size:.2f} MB")
                    converted_files.append(png_path)
                
                if args.format in ["jpg", "both"]:
                    jpg_path = heic_converter.convert_to_jpg(heic_file, args)
                    jpg_size = Path(jpg_path).stat().st_size / (1024 * 1024)
                    logger.debug(f"JPG size: {jpg_size:.2f} MB")
                    converted_files.append(jpg_path)
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to convert {heic_file}: {str(e)}")
                failure_count += 1
                continue
        
        # Display conversion summary
        total_original_size = sum(Path(f).stat().st_size for f in heic_files) / (1024 * 1024)
        total_converted_size = sum(Path(f).stat().st_size for f in converted_files) / (1024 * 1024)
        
        logger.info("Conversion summary:")
        logger.info(f"  Files processed: {len(heic_files)}")
        logger.info(f"  Total original size: {total_original_size:.2f} MB")
        logger.info(f"  Total converted size: {total_converted_size:.2f} MB")
        
        space_diff = total_original_size - total_converted_size
        if space_diff > 0:
            logger.info(f"  Space saved: {space_diff:.2f} MB")
        else:
            logger.info(f"  Space increased: {-space_diff:.2f} MB")
        
        logger.info(f"Conversion completed. Success: {success_count}, Failed: {failure_count}")
        
        return 0
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())