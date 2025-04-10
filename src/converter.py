import os
import logging
from pathlib import Path
from PIL import Image, PngImagePlugin, ImageOps
import pillow_heif
import piexif
from io import BytesIO

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()

class HeicConvert:
    """Class responsible for converting HEIC/HEIF files to other formats."""
    
    def __init__(self, output_dir=None, jpg_quality=90, png_compression=6, heic_quality=90, resampling_filter = Image.Resampling.LANCZOS, existing_mode="rename"):
        """Initialize the HEIC converter."""
        # Validate inputs
        if jpg_quality < 1 or jpg_quality > 100:
            raise ValueError(f"JPEG quality must be between 1-100, got {jpg_quality}")
        
        if png_compression < 0 or png_compression > 9:
            raise ValueError(f"PNG compression must be between 0-9, got {png_compression}")
        
        if heic_quality < 1 or heic_quality > 100:
            raise ValueError(f"HEIC quality must be between 1-100, got {heic_quality}")
        
        if existing_mode not in ["rename", "overwrite", "fail"]:
            raise ValueError(f"Invalid existing_mode: {existing_mode}. Must be 'rename', 'overwrite', or 'fail'")
        
        self.output_dir = output_dir
        self.jpg_quality = jpg_quality
        self.png_compression = png_compression
        self.heic_quality = heic_quality
        self.resampling_filter = resampling_filter
        self.existing_mode = existing_mode
        self.logger = logging.getLogger(__name__)
    
    def _get_output_path(self, input_path, extension):
        """Generate output path for converted file."""
        input_path = Path(input_path)  # Ensure input_path is a Path object
        output_filename = input_path.stem + extension
        
        if self.output_dir:
            # Make sure output_dir is a Path object
            output_dir = Path(self.output_dir)
            os.makedirs(output_dir, exist_ok=True)
            output_path = output_dir / output_filename
        else:
            # this is a fallback if output_dir is not set
            # Create a subfolder in the input directory named after the format
            # should not be hit cause of the check that the arg output_dir is set in main
            output_path = input_path.parent / output_filename
            self.logger.warning(f"Output directory not set, using input directory: {output_path}")
        
        # Handle existing files based on chosen mode
        if Path(output_path).exists():
            if self.existing_mode == "fail":
                self.logger.info(f"Skipping: {Path(output_path).name} (file already exists)")
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
                while Path(output_path).exists():
                    path_obj = Path(original_path)
                    new_name = f"{path_obj.stem}_{counter}{path_obj.suffix}"
                    output_path = Path(path_obj.parent / new_name)
                    counter += 1
                
                self.logger.debug(f"Renamed output to avoid conflict: {output_path}")
        
        return output_path
    
    def resize_image(self, img, args):
        """Resize image based on provided arguments."""

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
            percentage = args.resize / 100
            return ImageOps.scale(img, percentage, self.resampling_filter)
        
        elif args.width:
            # Resize by width, maintain aspect ratio
            return ImageOps.contain(img, (args.width, 100000000), self.resampling_filter)

        elif args.height:
            # Resize by height, maintain aspect ratio
            return ImageOps.contain(img, (100000000, args.height), self.resampling_filter)
        
        return img  # No resizing if no arguments provided
    
    def _log_conversion(self, input_file, output_file):
        """Log conversion with appropriate path formatting."""
        # Log full paths for debug level (typically goes to file)
        self.logger.debug(f"Converted: {input_file} → {output_file}")
        
        # Log just filenames for info level (typically shows in console)
        input_name = Path(input_file).name
        output_name = Path(output_file).name
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
    
    def _get_image_and_resize(self, heic_file, args):
        """Get image from HEIC file."""
        try:
            # When opening with pillow-heif or other libraries, convert Path to string
            heif_file = pillow_heif.open_heif(str(heic_file))  # Convert Path to string here
            
            # Convert to PIL Image
            image = Image.frombytes(
                heif_file.mode, 
                heif_file.size, 
                heif_file.data,
                "raw", 
                heif_file.mode, 
                0, 0
            )

            # Apply resizing if args is provided
            if args:
                image = self.resize_image(image, args)
            
        except Exception as e:
            self.logger.error(f"Error opening HEIC file: {e}")
            return None
        return image
    
    def convert_to_jpg(self, heic_file, args):
        """Convert HEIC file to JPG format."""
        # Ensure heic_file is a Path object
        heic_file = Path(heic_file)
        
        try:
            # Get output path for JPG
            output_path = self._get_output_path(heic_file, ".jpg")
            
            heic_image = self._get_image_and_resize(heic_file, args)
                       
            # Get and handle EXIF data
            exif_info = self._handle_exif_data(heic_image, heic_image.size)
            
            # Save the image
            heic_image.save(output_path, format="JPEG", quality=self.jpg_quality)
            
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
        
        heic_file = Path(heic_file)
        try:
            output_path = self._get_output_path(heic_file, ".png")
            self.logger.debug(f"Converting {heic_file} to PNG")
            
            heic_image = self._get_image_and_resize(heic_file, args)
            
            # Get and handle EXIF data (just like in JPG conversion)
            exif_info = self._handle_exif_data(heic_image, heic_image.size)
            
            heic_image.save(output_path, format="PNG", compress_level=self.png_compression)
            
            # Add EXIF data to PNG using PngImagePlugin
            if exif_info['exif_bytes']:
                # Using pillow's built-in PNG metadata support
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

    def convert_to_heic(self, heic_file, args):
        """Convert an image file to HEIC format."""

        heic_file = Path(heic_file)
        try:
            output_path = self._get_output_path(heic_file, ".heic")
            self.logger.debug(f"Converting {heic_file} to HEIC")
            
            heic_image = self._get_image_and_resize(heic_file, args)
                        
            # Get output path
            output_path = self._get_output_path(Path(heic_image), '.heic')
            
            heif = pillow_heif.from_pillow(heic_image)
            heif.save(output_path, quality=self.heic_quality)  
            
            self._log_conversion(heic_image, output_path)
            
            return output_path
        
        except FileExistsError:
            return None
        except Exception as e:
            self.logger.error(f"Error converting {heic_image} to HEIC: {str(e)}")
            return None