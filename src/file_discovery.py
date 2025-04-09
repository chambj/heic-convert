import os
from pathlib import Path
import logging

class FileDiscovery:
    """Class responsible for finding files in directories."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def find_heic_files(self, folder, recursive=True):
        """Find all HEIC/HEIF files in the given folder."""
        self.logger.debug(f"Searching for HEIC files in {folder} (recursive={recursive})")
        
        folder_path = Path(folder)  # Convert to Path object
        
        # Use a case-insensitive approach with set() to deduplicate
        if recursive:
            # Only use lowercase patterns and convert to a set to remove duplicates
            heic_files = set(folder_path.rglob("*.heic")) | set(folder_path.rglob("*.heif"))
            # Convert back to list
            heic_files = list(heic_files)
        else:
            # Same for non-recursive search
            heic_files = set(folder_path.glob("*.heic")) | set(folder_path.glob("*.heif"))
            # Convert back to list
            heic_files = list(heic_files)
        
        self.logger.debug(f"Found {len(heic_files)} HEIC/HEIF files")
        return heic_files