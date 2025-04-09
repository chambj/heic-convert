import os
import logging
from pathlib import Path
from PIL import Image
import pillow_heif
import piexif

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()

class HeicConvert:
    """Class responsible for converting HEIC/HEIF files to other formats."""
    
    def __init__(self, output_dir=None, jpg_quality=90, existing_mode="rename"):
        """Initialize the HEIC converter."""
        # Validate inputs
        if jpg_quality < 1 or jpg_quality > 100:
            raise ValueError(f"JPEG quality must be between 1-100, got {jpg_quality}")
        
        if existing_mode not in ["rename", "overwrite", "fail"]:
            raise ValueError(f"Invalid existing_mode: {existing_mode}. Must be 'rename', 'overwrite', or 'fail'")
        
        self.output_dir = output_dir
        self.jpg_quality = jpg_quality
        self.existing_mode = existing_mode
        self.logger = logging.getLogger(__name__)
    
    def _get_output_path(self, input_path, extension):
        """Generate output path for converted file."""
        input_path = Path(input_path)
        filename = input_path.stem + extension
        
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, filename)
        else:
            output_path = os.path.join(input_path.parent, filename)
        
        # Handle existing files based on chosen mode
        if os.path.exists(output_path):
            if self.existing_mode == "fail":
                self.logger.info(f"Skipping: {os.path.basename(output_path)} (file already exists)")
                self.logger.debug(f"Output file already exists and 'fail' mode selected: {output_path}")
                # Raise a specialized exception that can be handled differently
                raise FileExistsError(f"Output file already exists: {output_path}")
            
            elif self.existing_mode == "overwrite":
                self.logger.debug(f"Overwriting existing file: {output_path}")
                return output_path
            
            elif self.existing_mode == "rename":
                # Current behavior: add numbering
                counter = 1
                original_path = output_path
                while os.path.exists(output_path):
                    path_obj = Path(original_path)
                    new_name = f"{path_obj.stem}_{counter}{path_obj.suffix}"
                    output_path = os.path.join(path_obj.parent, new_name)
                    counter += 1
                
                self.logger.debug(f"Renamed output to avoid conflict: {output_path}")
        
        return output_path
    
    def resize_image(self, img, args):
        """Resize image based on provided arguments."""
        original_width, original_height = img.size
        resize_options = 0
        
        # Count how many resize options were specified
        if args.resize:
            resize_options += 1
        if args.width:
            resize_options += 1
        if args.height:
            resize_options += 1
        
        # Warn about multiple options
        if resize_options > 1:
            self.logger.warning("Multiple resize options specified. Using priority: resize > width > height")
        
        # Apply resize with the established priority
        if args.resize:
            # Resize by percentage
            percentage = max(1, min(100, args.resize)) / 100
            new_width = int(original_width * percentage)
            new_height = int(original_height * percentage)
            return img.resize((new_width, new_height), Image.LANCZOS)
        
        elif args.width:
            # Resize by width, maintain aspect ratio
            ratio = args.width / original_width
            new_height = int(original_height * ratio)
            return img.resize((args.width, new_height), Image.LANCZOS)
        
        elif args.height:
            # Resize by height, maintain aspect ratio
            ratio = args.height / original_height
            new_width = int(original_width * ratio)
            return img.resize((new_width, args.height), Image.LANCZOS)
        
        return img  # No resizing if no arguments provided
    
    def _log_conversion(self, input_file, output_file):
        """Log conversion with appropriate path formatting."""
        # Log full paths for debug level (typically goes to file)
        self.logger.debug(f"Converted: {input_file} → {output_file}")
        
        # Log just filenames for info level (typically shows in console)
        input_name = os.path.basename(input_file)
        output_name = os.path.basename(output_file)
        self.logger.info(f"Converted: {input_name} → {output_name}")
    
    def convert_to_jpg(self, heic_file, args):
        """Convert HEIC file to JPG."""
        try:
            output_path = self._get_output_path(heic_file, ".jpg")
            self.logger.debug(f"Converting {heic_file} to JPG (quality: {self.jpg_quality})")
            
            img = Image.open(heic_file)
            
            # Apply resizing if args is provided
            if args:
                img = self.resize_image(img, args)
            
            # Add EXIF data if available
            exif_data = img.info.get("exif") if hasattr(img, "info") else None
            if exif_data is not None:
                piexif.insert(exif_data, output_path)
            
            img.save(output_path, format="JPEG", quality=self.jpg_quality)
            
            self._log_conversion(heic_file, output_path)
            
            self.logger.debug(f"Saved JPG to {output_path}")
            return output_path
        except FileExistsError:
            # This is an expected condition when mode="fail", so just return None
            return None
        except Exception as e:
            self.logger.error(f"Error converting {heic_file} to JPG: {str(e)}")
            return None

    def convert_to_png(self, heic_file, args):
        """Convert HEIC file to PNG."""
        try:
            output_path = self._get_output_path(heic_file, ".png")
            self.logger.debug(f"Converting {heic_file} to PNG")
            
            img = Image.open(heic_file)
            
            # Apply resizing if args is provided
            if args:
                img = self.resize_image(img, args)
            
            # Use compression level from args if provided
            compression = args.png_compression if args else 6
            img.save(output_path, format="PNG", compress_level=compression)
            
            self._log_conversion(heic_file, output_path)
            
            self.logger.debug(f"Saved PNG to {output_path}")
            return output_path
        except Exception as e:
            self.logger.debug(f"Error converting {heic_file} to PNG: {str(e)}")
            raise