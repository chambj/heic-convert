import os
import logging
from pathlib import Path
from PIL import Image, PngImagePlugin
import pillow_heif
import piexif
from io import BytesIO

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
    
    def _handle_exif_data(self, image, original_size=None):
        """Extract and process EXIF data from an image."""
        result = {'exif_data': None, 'exif_bytes': None}
        
        # Extract EXIF data from original image
        if hasattr(image, "info") and "exif" in image.info:
            try:
                exif_data = image.info["exif"]
                result['exif_bytes'] = exif_data
                
                # If resized, update dimension-related EXIF data
                if original_size and image.size != original_size:
                    try:
                        # Load and validate EXIF dict
                        exif_dict = piexif.load(exif_data)
                        
                        if exif_dict is None:
                            self.logger.debug("No valid EXIF data found to update")
                            return result
                        
                        # Update dimensions if 0th IFD exists
                        if "0th" in exif_dict:
                            # Use try/except for each tag update
                            try:
                                exif_dict["0th"][piexif.ImageIFD.ImageWidth] = image.width
                                exif_dict["0th"][piexif.ImageIFD.ImageLength] = image.height
                                result['exif_bytes'] = piexif.dump(exif_dict)
                            except KeyError as e:
                                self.logger.debug(f"EXIF tag not found: {e}")
                        else:
                            self.logger.debug("EXIF data has no '0th' IFD section")
                    except Exception as e:
                        # Less noisy - change to debug level
                        self.logger.debug(f"Could not update EXIF dimensions: {e}")
                
            except Exception as e:
                self.logger.debug(f"Error processing EXIF data: {e}")
        else:
            self.logger.debug("No EXIF data found in image")
        
        return result
    
    def convert_to_jpg(self, heic_file, args):
        """Convert HEIC file to JPG."""
        try:
            output_path = self._get_output_path(heic_file, ".jpg")
            self.logger.debug(f"Converting {heic_file} to JPG (quality: {self.jpg_quality})")
            
            img = Image.open(heic_file)
            original_size = img.size
            
            # Apply resizing if args is provided
            if args:
                img = self.resize_image(img, args)
            
            # Get and handle EXIF data
            exif_info = self._handle_exif_data(img, original_size)
            
            # Save the image
            img.save(output_path, format="JPEG", quality=self.jpg_quality)
            
            # Insert EXIF data after saving
            if exif_info['exif_bytes']:
                piexif.insert(exif_info['exif_bytes'], output_path)
            
            self._log_conversion(heic_file, output_path)
            
            return output_path
        except FileExistsError:
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
            original_size = img.size
            
            # Apply resizing if args is provided
            if args:
                img = self.resize_image(img, args)
            
            # Get and handle EXIF data (just like in JPG conversion)
            exif_info = self._handle_exif_data(img, original_size)
            
            # Use compression level from args if provided
            compression = args.png_compression if args else 6
            img.save(output_path, format="PNG", compress_level=compression)
            
            # Add EXIF data to PNG using PngImagePlugin
            if exif_info['exif_bytes']:
                # Method 1: Using pillow's built-in PNG metadata support
                with open(output_path, 'rb+') as png_file:
                    img = Image.open(png_file)
                    meta = PngImagePlugin.PngInfo()
                    meta.add(b'eXIf', exif_info['exif_bytes'])
                    img.save(png_file, format="PNG", pnginfo=meta)

            self._log_conversion(heic_file, output_path)
            
            self.logger.debug(f"Saved PNG to {output_path}")
            return output_path
        
        except FileExistsError:
            return None
        except Exception as e:
            self.logger.error(f"Error converting {heic_file} to PNG: {str(e)}")
            return None

    def convert_to_heic(self, image_file, args):
        """Convert an image file to HEIC format."""
        try:
            # Open the source image
            image = Image.open(image_file)
            original_size = image.size
            
            # Apply resizing if needed
            if args:
                image = self.resize_image(image, args)
            
            # Get and handle EXIF data
            exif_info = self._handle_exif_data(image, original_size)
            
            # Get output path
            output_path = self._get_output_path(Path(image_file), '.heic')
            
            # Get quality setting from args
            quality = getattr(args, 'heic_quality', 90)
            
            # Use the correct method for newer pillow-heif versions
            heif = pillow_heif.from_pillow(image)
            heif.save(output_path, quality=quality)  # Use save instead of to_bytes
            
            self._log_conversion(image_file, output_path)
            
            return output_path
        
        except FileExistsError:
            return None
        except Exception as e:
            self.logger.error(f"Error converting {image_file} to HEIC: {str(e)}")
            return None