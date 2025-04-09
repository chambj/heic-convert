import os
import pytest
from src.file_discovery import FileDiscovery

class TestFileDiscovery:
    @pytest.fixture
    def discoverer(self):
        return FileDiscovery()
        
    def test_find_heic_files(self, discoverer, tmpdir):
        """Test finding HEIC files in a directory."""
        # Create test file
        test_file = tmpdir.join("test.heic")
        test_file.write("dummy content")
        
        files = discoverer.find_heic_files(str(tmpdir))
        assert len(files) == 1
        assert "test.heic" in files[0]
    
    def test_recursive_file_finding(self, discoverer, tmpdir):
        """Test finding HEIC files recursively vs. non-recursively."""
        # Create test directory structure
        main_dir = tmpdir
        sub_dir = tmpdir.mkdir("subfolder")
        sub_sub_dir = sub_dir.mkdir("nested")
        
        # Create HEIC files at different levels
        main_file = main_dir.join("main.heic")
        sub_file = sub_dir.join("sub.heic")
        nested_file = sub_sub_dir.join("nested.heic")
        
        # Create the files
        main_file.write("dummy content")
        sub_file.write("dummy content")
        nested_file.write("dummy content")
        
        # Test non-recursive mode (should only find main.heic)
        non_recursive_files = discoverer.find_heic_files(str(main_dir), recursive=False)
        assert len(non_recursive_files) == 1
        assert str(main_file) in non_recursive_files
        assert str(sub_file) not in non_recursive_files
        assert str(nested_file) not in non_recursive_files
        
        # Test recursive mode (should find all 3 files)
        recursive_files = discoverer.find_heic_files(str(main_dir), recursive=True)
        assert len(recursive_files) == 3
        assert str(main_file) in recursive_files
        assert str(sub_file) in recursive_files
        assert str(nested_file) in recursive_files