"""
Utility functions shared between CLI and GUI interfaces.
"""
import os
from pathlib import Path

def perform_conversion(heic_files, args, heic_converter, logger, progress_callback=None):
    """
    Process HEIC files with the specified converter and settings.
    
    Args:
        heic_files: List of HEIC file paths to convert
        args: Namespace or object with conversion parameters
        heic_converter: HeicConvert instance
        logger: Logger instance
        progress_callback: Optional callback function for GUI progress updates
        
    Returns:
        dict: Results with statistics and file lists
    """
    success_count = 0
    failure_count = 0
    skipped_count = 0
    converted_files = []
    skipped_files = []
    errors = []
    total_files = len(heic_files)

    # Process each file
    for i, heic_file in enumerate(heic_files):
        # Update progress if callback provided (for GUI)
        if progress_callback:
            progress_callback(i, total_files)
            
        try:
            heic_size = Path(heic_file).stat().st_size / (1024 * 1024)
            logger.debug(f"Converting file: {heic_file} ({heic_size:.2f} MB)")
            
            file_converted = False
            file_skipped = False
            
            if args.format == "png":
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
            
            if args.format == "jpg":
                jpg_path = heic_converter.convert_to_jpg(heic_file, args)
                if jpg_path:  # File was actually converted
                    jpg_size = Path(jpg_path).stat().st_size / (1024 * 1024)
                    logger.debug(f"JPG size: {jpg_size:.2f} MB")
                    converted_files.append(jpg_path)
                    file_converted = True
                else:
                    file_skipped = True
                    skipped_count += 1
            
            if args.format in ["heic"]:
                heic_path = heic_converter.convert_to_heic(heic_file, args)
                if heic_path:  # File was actually converted
                    heic_size = Path(heic_path).stat().st_size / (1024 * 1024)
                    logger.debug(f"HEIC size: {heic_size:.2f} MB")
                    converted_files.append(heic_path)
                    file_converted = True
                else:
                    file_skipped = True
                    skipped_count += 1
            
            # If file was skipped, add to skipped files list
            if file_skipped and not file_converted:
                skipped_files.append(heic_file)
                
            # Only count as success if at least one conversion succeeded
            if file_converted:
                success_count += 1
                
        except Exception as e:
            error_msg = f"Failed to convert {heic_file}: {str(e)}"
            logger.error(error_msg)
            errors.append((heic_file, str(e)))
            failure_count += 1
            continue
    
    # Calculate statistics
    total_original_size = sum(Path(f).stat().st_size for f in heic_files) / (1024 * 1024)
    total_converted_size = sum(Path(f).stat().st_size for f in converted_files) / (1024 * 1024) if converted_files else 0
    space_diff = total_original_size - total_converted_size

    # Final progress update
    if progress_callback:
        progress_callback(total_files, total_files)
    
    # Return results
    return {
        'success_count': success_count,
        'failure_count': failure_count,
        'skipped_count': skipped_count,
        'converted_files': converted_files,
        'skipped_files': skipped_files,
        'errors': errors,
        'total_original_size': total_original_size,
        'total_converted_size': total_converted_size,
        'space_diff': space_diff
    }