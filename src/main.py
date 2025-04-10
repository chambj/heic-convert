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
from src.file_discovery import FileDiscovery
from src.conversion_manager import perform_conversion
from src.version import VERSION
from PIL import Image


# Initialize logger at module level
logger = logging.getLogger("heic_convert")
logger.setLevel(logging.DEBUG)

# Add a default console handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(console)

# Update the logging configuration
def setup_logging(args=None):
    """Configure logging with file handler if needed."""
    global logger
    
    # Clear existing handlers to avoid duplicates
    logger.handlers = []
    
    # Re-add console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console)
    
    # Add file handler if log file specified
    if args and args.log_file:
        try:
            log_path = Path(args.log_file)
            log_path.parent.mkdir(exist_ok=True, parents=True)
                
            file_handler = logging.FileHandler(str(log_path), mode='w')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
            logger.addHandler(file_handler)
            logger.debug(f"Log file created at: {args.log_file}")
        except Exception as e:
            logger.error(f"Failed to create log file: {e}")
    
    return logger

def parse_arguments(parser):
    parser.add_argument("--folder", "-f", help="Folder path containing HEIC files to convert")
    parser.add_argument("--output", "-o", 
                        help="Output folder path for converted images (default: creates a subfolder named after the format in the source folder)")
    parser.add_argument("--format", "-t", choices=["png", "jpg", "heic", "both"], default="jpg",
                        help="Target format: png, jpg, heic. HEIC is experimental. (default: jpg)")
    parser.add_argument("--jpg-quality", "-q", type=int, default=90, 
                        help="JPEG quality (1-100, default: 90)")
    parser.add_argument("--png-compression", type=int, default=6, choices=range(10),
                        help="PNG compression level (0-9, default: 6)")
    parser.add_argument("--heic-quality", type=int, default=90,
                   help="Quality for HEIC files (1-100, higher is better quality)")
    parser.add_argument("--existing", "-e", choices=["rename", "overwrite", "fail"], default="fail",
                        help="How to handle existing files: rename (add number), overwrite, or fail (default: fail)")
    parser.add_argument("--log-file", help="Save logs to specified file (default: no file logging)")
    parser.add_argument("--recursive", "-r", action="store_true", 
                        help="Recursively search for HEIC files in subdirectories")
    parser.add_argument('--version', action='version', 
                       version=f'HEIC Converter v{VERSION}')
    parser.add_argument("--resampling_filter",  
                        choices=["nearest", "box", "bilinear", "hamming", "bicubic", "lanczos"],
                        default="lanczos",
                        help="Resampling filter for resizing. lanczoz is best but slowest. bicubic is a good option too. (default: lanczos)")
    
    
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
    
    if args.format == "png" and args.heic_quality != 90:  # 90 is the default
        logger.warning("--heic-quality parameter was specified but will be ignored since format is 'png'")
    
    if args.format == "jpg" and args.heic_quality != 90:  # 90 is the default
        logger.warning("--heic-quality parameter was specified but will be ignored since format is 'jpg'")
    
    return args

def process_filter_args(args):
    """Process filter arguments and set resize dimensions."""

    if args.resampling_filter:
        filter_map = {
            'nearest': Image.Resampling.NEAREST,
            'box': Image.Resampling.BOX,
            'bilinear': Image.Resampling.BILINEAR,
            'hamming': Image.Resampling.HAMMING,
            'bicubic': Image.Resampling.BICUBIC,
            'lanczos': Image.Resampling.LANCZOS,
        }
        resampling_filter = filter_map.get(
            args.resampling_filter.lower(), 
            Image.Resampling.LANCZOS
            )
    else:
        # Default to LANCZOS if not specified
        resampling_filter = Image.Resampling.LANCZOS

    return resampling_filter

def check_system_resources():
    """Check if system has enough resources to continue."""
    import psutil
    # If available memory is less than 500MB, warn the user
    # this has never been tested. so YMMV.
    if psutil.virtual_memory().available < 500 * 1024 * 1024:
        logger.warning("System is low on memory. Conversion of large files may fail.")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Convert HEIC images to PNG or JPG")
    args = parse_arguments(parser)

    if not args.folder and not args.output:
        parser.print_help()
        sys.exit("Error: folder and output are required.")

    setup_logging(args)
    logger.info(f"HEIC Converter v{VERSION}")
    
    if not check_system_resources():
        logger.warning("Continuing with limited resources, large files may fail.")
    
    if args.output is None:
        # Set default output directory as a subdirectory of the source
        args.output = str(Path(args.folder) / args.format)
    else:
        args.output = Path(args.output).absolute()

    args.resampling_filter = process_filter_args(args)
    
    # Now validate arguments (after logger is set up)
    validate_format_arguments(args)
    
    # Log source and output directories
    logger.info(f"Source directory: {Path(args.folder).absolute()}")
    if args.output:
        logger.info(f"Output directory: {Path(args.folder).absolute()}")
    logger.info("")  # Empty line for separation
    
    # Validate folder path
    if not Path(args.folder).is_dir():
        logger.error(f"The specified path '{args.folder}' is not a valid directory.")
        return 1

    file_discoverer = FileDiscovery()
    heic_converter = HeicConvert(output_dir=args.output, jpg_quality=args.jpg_quality, png_compression=args.png_compression, 
                                 heic_quality=args.heic_quality, resampling_filter=args.resampling_filter ,existing_mode=args.existing)
    
    try:
        # Find HEIC files
        heic_files = file_discoverer.find_heic_files(args.folder, recursive=args.recursive)        
        if not heic_files:
            logger.error("No HEIC files found in the specified directory.")
            return 0
        
        logger.info(f"Found {len(heic_files)} HEIC files to convert")
        
        # Use the common conversion function with a progress wrapper for tqdm
        def tqdm_progress(i, total):
            # This function does nothing - tqdm handles its own progress
            pass
        
        results = perform_conversion(heic_files, args, heic_converter, logger, tqdm_progress)
        
        # Display conversion summary
        logger.info("Conversion summary:")
        logger.info(f"  Files processed: {len(heic_files)}")
        logger.info(f"  Successfully converted: {results['success_count']}")
        logger.info(f"  Skipped (already exist): {results['skipped_count']}")
        logger.info(f"  Failed: {results['failure_count']}")
        logger.info(f"  Total original size: {results['total_original_size']:.2f} MB")
        logger.info(f"  Total converted size: {results['total_converted_size']:.2f} MB")

        space_diff = results['space_diff']
        if space_diff > 0:
            logger.info(f"  Space saved: {space_diff:.2f} MB")
        else:
            logger.info(f"  Space increased: {-space_diff:.2f} MB")

        if results['skipped_count'] > 0:
            if args.existing == "fail":
                logger.info(f"\nNote: {results['skipped_count']} files were skipped because output files already exist.")
                logger.info("Use --existing rename or --existing overwrite to handle existing files differently.")
                
                # Show list of skipped files (display up to 10 files to avoid excessive output)
                max_display = 10
                if results['skipped_files']:
                    logger.info("\nSkipped files:")
                    for i, file in enumerate(results['skipped_files'][:max_display]):
                        logger.info(f"  - {file}")  # This will now show the full path
                    
                    if len(results['skipped_files']) > max_display:
                        logger.info(f"  ... and {len(results['skipped_files']) - max_display} more files")
        
        return 0
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())