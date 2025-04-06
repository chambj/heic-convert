import os
import glob
import logging
from pathlib import Path
from PIL import Image
import pillow_heif

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()

class HeicConvert:
    def __init__(self, output_dir=None, jpg_quality=90, existing_mode="rename"):
        """
        Initialize the HEIC converter.
        
        Args:
            output_dir: Directory to save converted images (default: same as source)
            jpg_quality: Quality for JPG conversion (1-100)
            existing_mode: How to handle existing files: rename, overwrite, or fail
        """
        self.output_dir = output_dir
        
        # Validate quality setting
        if not 1 <= jpg_quality <= 100:
            raise ValueError("JPEG quality must be between 1 and 100")
        self.jpg_quality = jpg_quality
        
        # Validate existing_mode
        if existing_mode not in ["rename", "overwrite", "fail"]:
            raise ValueError("existing_mode must be 'rename', 'overwrite', or 'fail'")
        self.existing_mode = existing_mode
        
        self.logger = logging.getLogger(__name__)
    
    def list_heic_files(self, folder_path):
        """Find all HEIC files in the specified folder."""
        self.logger.info(f"Scanning for HEIC files in {folder_path}")
        heic_pattern = os.path.join(folder_path, "*.heic")
        heif_pattern = os.path.join(folder_path, "*.heif")
        return glob.glob(heic_pattern, recursive=False) + glob.glob(heif_pattern, recursive=False)
    
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
                self.logger.error(f"Output file already exists: {output_path}")
                raise FileExistsError(f"Output file already exists: {output_path}")
            
            elif self.existing_mode == "overwrite":
                self.logger.warning(f"Overwriting existing file: {output_path}")
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
                
                self.logger.info(f"Renamed output to avoid conflict: {output_path}")
        
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
    
    def convert_to_jpg(self, heic_path, args=None):
        """Convert HEIC file to JPG format with optional resizing."""
        try:
            output_path = self._get_output_path(heic_path, ".jpg")
            self.logger.info(f"Converting {heic_path} to JPG (quality: {self.jpg_quality})")
            
            img = Image.open(heic_path)
            
            # Apply resizing if args is provided
            if args:
                img = self.resize_image(img, args)
            
            img.save(output_path, format="JPEG", quality=self.jpg_quality)
            
            self.logger.info(f"Saved JPG to {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Error converting {heic_path} to JPG: {str(e)}")
            raise

    def convert_to_png(self, heic_path, args=None):
        """Convert HEIC file to PNG format with optional resizing."""
        try:
            output_path = self._get_output_path(heic_path, ".png")
            self.logger.info(f"Converting {heic_path} to PNG")
            
            img = Image.open(heic_path)
            
            # Apply resizing if args is provided
            if args:
                img = self.resize_image(img, args)
            
            # Use compression level from args if provided
            compression = args.png_compression if args else 6
            img.save(output_path, format="PNG", compress_level=compression)
            
            self.logger.info(f"Saved PNG to {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Error converting {heic_path} to PNG: {str(e)}")
            raise