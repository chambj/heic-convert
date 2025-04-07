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
from datetime import datetime

# Update the logging configuration
def setup_logging():
    """Configure logging with different formats for console and file."""
    logger = logging.getLogger('heic_convert')
    logger.setLevel(logging.DEBUG)  # Logger itself keeps all messages
    
    # Clear existing handlers
    for handler in logger.handlers:
        logger.removeHandler(handler)
    
    # Console handler - INFO and above only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Only INFO and above shown on console
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler - DEBUG and above
    log_dir = os.path.join(os.path.expanduser("~"), ".heic_convert", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"heic_convert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Store handlers in logger for later use
    logger.console_handler = console_handler
    logger.file_handler = file_handler
    
    return logger

logger = setup_logging()

def parse_arguments(parser):
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
    resize_group.add_argument("--resize", type=int, help="Resize image by percentage (e.g., 50 for 50%%)")
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
            if png_path:  # Check if path is not None. It won't be in the case of failure (eg file exists)
                png_size = Path(png_path).stat().st_size / (1024 * 1024)
                logger.debug(f"PNG size: {png_size:.2f} MB")
                converted_files.append(png_path)
        
        if args.format in ["jpg", "both"]:
            # Pass args to convert_to_jpg
            jpg_path = heic_converter.convert_to_jpg(heic_file, args)
            if jpg_path:  # Check if path is not None. It won't be in the case of failure (eg file exists)
                jpg_size = Path(jpg_path).stat().st_size / (1024 * 1024)
                logger.debug(f"JPG size: {jpg_size:.2f} MB")
                converted_files.append(jpg_path)
            
        return converted_files
    
    except Exception as e:
        logger.error(f"Failed to convert {heic_file}: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Convert HEIC images to PNG or JPG")

    args = parse_arguments(parser)

    if not args.folder:
        parser.print_help()
        sys.exit("Error: folder is required.")

    
    if args.output is None:
        # Set default output directory as a subdirectory of the source
        args.output = os.path.join(args.folder, args.format)
    else:
        # Only convert to absolute path if not None
        args.output = os.path.abspath(args.output)
    
    args = validate_format_arguments(args)
    
    # Log source and output directories
    logger.info(f"Source directory: {os.path.abspath(args.folder)}")
    if args.output:
        logger.info(f"Output directory: {os.path.abspath(args.output)}")
    logger.info("")  # Empty line for separation
    
    # Validate folder path
    if not os.path.isdir(args.folder):
        logger.error(f"The specified path '{args.folder}' is not a valid directory.")
        return 1

    # Initialize converter
    heic_converter = HeicConvert(output=args.output, jpg_quality=args.jpg_quality, 
                                   existing_mode=args.existing)
    
    try:
        # Get list of HEIC files
        heic_files = heic_converter.list_heic_files(args.folder)
        
        if not heic_files:
            logger.error("No HEIC files found in the specified directory.")
            return 0
        
        logger.info(f"Found {len(heic_files)} HEIC files to convert")
        
        success_count = 0
        failure_count = 0
        skipped_count = 0
        converted_files = []
        skipped_files = []  # New list to track skipped files

        # Convert files with progress bar
        for heic_file in tqdm(heic_files, desc="Converting", unit="file"):
            try:
                heic_size = Path(heic_file).stat().st_size / (1024 * 1024)
                logger.debug(f"Converting file: {heic_file} ({heic_size:.2f} MB)")
                
                file_converted = False
                file_skipped = False
                
                if args.format in ["png", "both"]:
                    png_path = heic_converter.convert_to_png(heic_file, args)
                    if png_path:  # File was actually converted
                        png_size = Path(png_path).stat().st_size / (1024 * 1024)
                        logger.debug(f"PNG size: {png_size:.2f} MB")
                        converted_files.append(png_path)
                        file_converted = True
                    else:
                        # File was skipped due to existing=fail
                        file_skipped = True
                        skipped_count += 1
                
                if args.format in ["jpg", "both"]:
                    jpg_path = heic_converter.convert_to_jpg(heic_file, args)
                    if jpg_path:  # File was actually converted
                        jpg_size = Path(jpg_path).stat().st_size / (1024 * 1024)
                        logger.debug(f"JPG size: {jpg_size:.2f} MB")
                        converted_files.append(jpg_path)
                        file_converted = True
                    else:
                        # Only count as skipped if we haven't already counted it
                        if args.format != "both" or not file_converted:
                            file_skipped = True
                            skipped_count += 1
                
                # If file was skipped, add to skipped files list
                if file_skipped and not file_converted:
                    skipped_files.append(heic_file)  # Store full path instead of basename
                    
                # Only count as success if at least one conversion succeeded
                if file_converted:
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
        logger.info(f"  Successfully converted: {success_count}")
        logger.info(f"  Skipped (already exist): {skipped_count}")
        logger.info(f"  Failed: {failure_count}")
        logger.info(f"  Total original size: {total_original_size:.2f} MB")
        logger.info(f"  Total converted size: {total_converted_size:.2f} MB")

        space_diff = total_original_size - total_converted_size
        if space_diff > 0:
            logger.info(f"  Space saved: {space_diff:.2f} MB")
        else:
            logger.info(f"  Space increased: {-space_diff:.2f} MB")

        if skipped_count > 0:
            if args.existing == "fail":
                logger.info(f"\nNote: {skipped_count} files were skipped because output files already exist.")
                logger.info("Use --existing rename or --existing overwrite to handle existing files differently.")
                
                # Show list of skipped files (display up to 10 files to avoid excessive output)
                max_display = 10
                if skipped_files:
                    logger.info("\nSkipped files:")
                    for i, file in enumerate(skipped_files[:max_display]):
                        logger.info(f"  - {file}")  # This will now show the full path
                    
                    if len(skipped_files) > max_display:
                        logger.info(f"  ... and {len(skipped_files) - max_display} more files")
        
        return 0
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())