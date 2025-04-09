import os
import logging

class FileDiscovery:
    """Class responsible for finding files in directories."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def find_heic_files(self, folder, recursive=True):
        """Find all HEIC/HEIF files in the given folder."""
        self.logger.debug(f"Searching for HEIC files in {folder} (recursive={recursive})")
        
        heic_files = []
        
        if recursive:
            # Walk through all subdirectories
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(('.heic', '.heif')):
                        heic_files.append(os.path.join(root, file))
        else:
            # Just search the top directory
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path) and file.lower().endswith(('.heic', '.heif')):
                    heic_files.append(file_path)
        
        self.logger.debug(f"Found {len(heic_files)} HEIC/HEIF files")
        return heic_files