import os
import pytest
from src.file_discovery import FileDiscovery
from pathlib import Path
import tempfile

class TestFileDiscovery:
    @pytest.fixture
    def discoverer(self):
        return FileDiscovery()
        
    def test_find_heic_files(self):
        """Test that find_heic_files returns files with correct extensions."""
        # Create test directory with files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test HEIC file
            test_heic = os.path.join(temp_dir, "test.heic")
            Path(test_heic).touch()
            
            # Create some other files
            Path(os.path.join(temp_dir, "test.txt")).touch()
            Path(os.path.join(temp_dir, "test.jpg")).touch()
            
            # Run the find_heic_files method
            discoverer = FileDiscovery()
            files = discoverer.find_heic_files(temp_dir)
            
            # Check that only .heic files are found
            assert len(files) == 1
            # Check the filename using Path.name
            assert files[0].name == "test.heic"
    
    def test_recursive_file_finding(self, discoverer, tmpdir):
        """Test finding HEIC files recursively vs. non-recursively."""
        # Create test directory structure
        main_dir = Path(tmpdir)
        sub_dir = Path(tmpdir.mkdir("subfolder"))
        sub_sub_dir = Path(tmpdir.mkdir("subfolder/nested"))
        
        # Create HEIC files at different levels
        main_file = main_dir / "main.heic"
        sub_file = sub_dir / "sub.heic"
        nested_file = sub_sub_dir / "nested.heic"
        
        # Create the files
        main_file.write_text("dummy content")
        sub_file.write_text("dummy content")
        nested_file.write_text("dummy content")
        
        # Test non-recursive mode (should only find main.heic)
        non_recursive_files = discoverer.find_heic_files(str(main_dir), recursive=False)
        assert len(non_recursive_files) == 1
        assert non_recursive_files[0].name == "main.heic"
        
        # Test recursive mode (should find all 3 files)
        recursive_files = discoverer.find_heic_files(str(main_dir), recursive=True)
        assert len(recursive_files) == 3
        
        # Get just the filenames for easier comparison
        found_names = {path.name for path in recursive_files}
        
        # Simple set comparison
        assert found_names == {"main.heic", "sub.heic", "nested.heic"}