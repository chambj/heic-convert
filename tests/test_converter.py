import os
import pytest
import tempfile
import shutil
from pathlib import Path
from src.converter import HeicConvert
from PIL import Image
import argparse
import io

class TestHEICConverter:
    @pytest.fixture
    def setup_test_files(self):
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Copy test HEIC files to the temp directory
        test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
        for test_file in os.listdir(test_data_dir):
            if test_file.lower().endswith(('.heic', '.heif')):
                src_path = os.path.join(test_data_dir, test_file)
                dst_path = os.path.join(temp_dir, test_file)
                shutil.copy2(src_path, dst_path)
        
        yield temp_dir
        
        # Cleanup after tests
        shutil.rmtree(temp_dir)
    
    def test_list_heic_files(self, setup_test_files):
        converter = HeicConvert()
        # Test with empty directory
        empty_dir = tempfile.mkdtemp()
        files = converter.list_heic_files(empty_dir)
        assert len(files) == 0
        shutil.rmtree(empty_dir)
    
    def test_list_heic_files_with_content(self, setup_test_files):
        """Test that we can find HEIC files in a directory with content."""
        converter = HeicConvert()
        
        # setup_test_files contains copied HEIC files
        files = converter.list_heic_files(setup_test_files)
        
        # Should find at least one HEIC file
        assert len(files) > 0
        assert all(f.lower().endswith(('.heic', '.heif')) for f in files)
        
    def test_get_output_path(self):
        converter = HeicConvert()
        test_path = "/test/path/image.heic"
        png_path = converter._get_output_path(test_path, ".png")
        assert png_path.endswith("image.png")
        
    def test_jpg_quality_validation(self):
        # Test with invalid quality values
        with pytest.raises(ValueError):
            HeicConvert(jpg_quality=101)
        with pytest.raises(ValueError):
            HeicConvert(jpg_quality=0)
    
    def test_existing_mode_validation(self):
        """Test validation of existing_mode parameter."""
        # Valid modes should work
        HeicConvert(existing_mode="rename")
        HeicConvert(existing_mode="overwrite")
        HeicConvert(existing_mode="fail")
        
        # Invalid mode should raise ValueError
        with pytest.raises(ValueError):
            HeicConvert(existing_mode="invalid_mode")
    
    def test_output_path_handling_rename(self, tmpdir):
        """Test rename behavior with existing files."""
        # Create a temporary file
        test_file = tmpdir.join("output.png")
        test_file.write("test content")
        
        converter = HeicConvert(existing_mode="rename")
        input_path = str(tmpdir.join("input.heic"))
        
        # First call should add the original name
        output_path = converter._get_output_path(input_path, ".png")
        assert output_path.endswith("input.png")
        
        # Create the output file to simulate an existing file
        Path(output_path).write_text("existing content")
        
        # Second call should add _1
        output_path2 = converter._get_output_path(input_path, ".png")
        assert "_1" in output_path2
        assert output_path2.endswith("input_1.png")
        
        # Create the second output file to simulate another existing file
        Path(output_path2).write_text("existing content 2")
        
        # Third call should add _2
        output_path3 = converter._get_output_path(input_path, ".png")
        assert "_2" in output_path3
        assert output_path3.endswith("input_2.png")
        
        # Create the third output file
        Path(output_path3).write_text("existing content 3")
        
        # Fourth call should add _3
        output_path4 = converter._get_output_path(input_path, ".png")
        assert "_3" in output_path4
        assert output_path4.endswith("input_3.png")

    def test_output_path_handling_overwrite(self, tmpdir):
        """Test overwrite behavior with existing files."""
        test_file = tmpdir.join("input.png")
        test_file.write("test content")
        
        converter = HeicConvert(existing_mode="overwrite")
        input_path = str(tmpdir.join("input.heic"))
        
        # Create the output file to simulate an existing file
        expected_output = str(tmpdir.join("input.png"))
        Path(expected_output).write_text("existing content")
        
        # Should return same path without changing it
        output_path = converter._get_output_path(input_path, ".png")
        assert output_path == expected_output

    def test_output_path_handling_fail(self, tmpdir):
        """Test fail behavior with existing files."""
        test_file = tmpdir.join("input.png")
        test_file.write("test content")
        
        converter = HeicConvert(existing_mode="fail")
        input_path = str(tmpdir.join("input.heic"))
        
        # Create the output file to simulate an existing file
        expected_output = str(tmpdir.join("input.png"))
        Path(expected_output).write_text("existing content")
        
        # Should raise FileExistsError
        with pytest.raises(FileExistsError):
            converter._get_output_path(input_path, ".png")
    
    def test_resize_by_percentage(self):
        """Test resizing by percentage."""
        # Create a test image (100x200)
        img = Image.new('RGB', (100, 200))
        
        # Create args with resize=50 (50%)
        args = argparse.Namespace(resize=50, width=None, height=None)
        
        converter = HeicConvert()
        resized = converter.resize_image(img, args)
        
        # Should be 50x100 (50% of original)
        assert resized.width == 50
        assert resized.height == 100

    def test_resize_by_width(self):
        """Test resizing by width."""
        # Create a test image (100x200)
        img = Image.new('RGB', (100, 200))
        
        # Create args with width=200
        args = argparse.Namespace(resize=None, width=200, height=None)
        
        converter = HeicConvert()
        resized = converter.resize_image(img, args)
        
        # Width should be 200, height should be 400 (to maintain aspect ratio)
        assert resized.width == 200
        assert resized.height == 400

    def test_resize_by_height(self):
        """Test resizing by height."""
        # Create a test image (100x200)
        img = Image.new('RGB', (100, 200))
        
        # Create args with height=100
        args = argparse.Namespace(resize=None, width=None, height=100)
        
        converter = HeicConvert()
        resized = converter.resize_image(img, args)
        
        # Height should be 100, width should be 50 (to maintain aspect ratio)
        assert resized.width == 50
        assert resized.height == 100

    def test_resize_priority(self):
        """Test resize priority with multiple options."""
        # Create a test image (100x200)
        img = Image.new('RGB', (100, 200))
        
        # Create args with multiple resize options
        # Priority should be: resize > width > height
        args = argparse.Namespace(resize=50, width=200, height=100)
        
        converter = HeicConvert()
        resized = converter.resize_image(img, args)
        
        # Should follow resize=50% (50x100)
        assert resized.width == 50
        assert resized.height == 100

    def test_png_compression_parameter(self, tmpdir):
        """Test that PNG compression parameter affects output file size."""
        # Create a test image with some colored rectangles (to make compression work)
        img = Image.new('RGB', (300, 300), color='white')
        
        # Add some colored areas to make the compression noticeable
        for x in range(100):
            for y in range(100):
                img.putpixel((x, y), (255, 0, 0))
                img.putpixel((x+100, y+100), (0, 255, 0))
                img.putpixel((x+200, y+200), (0, 0, 255))
        
        # Save with different compression levels
        low_compression = io.BytesIO()
        high_compression = io.BytesIO()
        
        img.save(low_compression, format="PNG", compress_level=1)
        img.save(high_compression, format="PNG", compress_level=9)
        
        # Higher compression should result in a smaller file
        assert len(low_compression.getvalue()) > len(high_compression.getvalue())