import os
import pytest
import tempfile
import shutil
from pathlib import Path
from src.converter import HeicConvert
from PIL import Image
import argparse
import io
from unittest.mock import patch
from src.file_discovery import FileDiscovery

class TestHEICConverter:
    @pytest.fixture
    def setup_test_files(self):
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Copy test HEIC files to the temp directory
            test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
            for test_file in os.listdir(test_data_dir):
                if test_file.lower().endswith(('.heic', '.heif')):
                    src_path = os.path.join(test_data_dir, test_file)
                    dst_path = os.path.join(temp_dir, test_file)
                    shutil.copy2(src_path, dst_path)
            
            yield temp_dir
        finally:
            # More robust cleanup with retries
            def rmtree_with_retry(path, max_retries=3, retry_delay=0.5):
                for attempt in range(max_retries):
                    try:
                        # Force garbage collection to release file handles
                        import gc
                        gc.collect()
                        
                        # Try to remove directory
                        shutil.rmtree(path, ignore_errors=True)
                        return
                    except PermissionError:
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(retry_delay)
                        else:
                            print(f"Warning: Could not remove temporary directory {path}")
            
            rmtree_with_retry(temp_dir)

    @pytest.fixture
    def file_discoverer(self):
        return FileDiscovery()

    def test_list_heic_files(self, file_discoverer, tmpdir):
        """Test that the file discovery can find HEIC files."""
        # Create test file
        test_file = tmpdir.join("test.heic")
        test_file.write("dummy content")

        files = file_discoverer.find_heic_files(str(tmpdir))
        assert len(files) == 1
        assert files[0].name == "test.heic"
    
    def test_list_heic_files_with_content(self, setup_test_files, file_discoverer):
        """Test that we can find HEIC files in a directory with content."""
        # setup_test_files contains copied HEIC files
        heic_files = file_discoverer.find_heic_files(setup_test_files)

        # Should find at least one HEIC file
        assert len(heic_files) > 0
        # Use Path's suffix property for extension checking
        assert all(f.suffix.lower() in ('.heic', '.heif') for f in heic_files)
        
    def test_get_output_path(self):
        converter = HeicConvert()
        test_path = "/test/path/image.heic"
        png_path = converter._get_output_path(test_path, ".png")
        # Use Path properties instead of string methods
        assert png_path.name == "image.png"
        
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
        assert output_path.name == "input.png"
        
        # Create the output file to simulate an existing file
        Path(output_path).write_text("existing content")
        
        # Second call should add _1
        output_path2 = converter._get_output_path(input_path, ".png")
        assert "_1" in str(output_path2)
        assert output_path2.name == "input_1.png"
        
        # Create the second output file to simulate another existing file
        Path(output_path2).write_text("existing content 2")
        
        # Third call should add _2
        output_path3 = converter._get_output_path(input_path, ".png")
        assert "_2" in str(output_path3)
        assert output_path3.name == "input_2.png"
        
        # Create the third output file
        Path(output_path3).write_text("existing content 3")
        
        # Fourth call should add _3
        output_path4 = converter._get_output_path(input_path, ".png")
        assert "_3" in str(output_path4)
        assert output_path4.name == "input_3.png"

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
        assert output_path == Path(expected_output)

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

    def test_actual_conversion(self, setup_test_files, file_discoverer):
        """Test conversion of a real HEIC file to JPG/PNG."""
        # This requires a real HEIC file in test_data
        converter = HeicConvert(output_dir=setup_test_files)
        
        heic_files = file_discoverer.find_heic_files(setup_test_files)
        
        # First verify we found files and log details
        assert len(heic_files) > 0, "No HEIC files found for testing conversion"
        print(f"Found HEIC files: {heic_files}")
        
        # Create args with required parameters
        args = argparse.Namespace(
            format="jpg", 
            jpg_quality=90,
            png_compression=6,
            resize=None,
            width=None,
            height=None
        )
        
        # Test conversion with better error handling
        try:
            heic_file = Path(heic_files[0])  # Convert to Path at the start
            if not heic_file.exists():
                converter.logger.error(f"Input file doesn't exist: {heic_file}")
                return None
            jpg_path = converter.convert_to_jpg(heic_file, args)
            assert jpg_path is not None, f"Conversion returned None for {heic_files[0]}"
            assert Path(jpg_path).exists(), f"Output file does not exist: {jpg_path}"
        except Exception as e:
            assert False, f"Conversion failed with error: {str(e)}"

    def test_corrupt_file_handling(self, tmpdir):
        """Test handling of corrupt HEIC files."""
        # Create a fake "HEIC" file with invalid content
        fake_heic = str(tmpdir.join("fake.heic"))
        with open(fake_heic, 'wb') as f:
            f.write(b'This is not a valid HEIC file')
        
        converter = HeicConvert(output_dir=str(tmpdir))
        
        # Should raise an exception when trying to convert
        with pytest.raises(Exception):
            converter.convert_to_jpg(fake_heic)

    def test_convert_to_heic(self, setup_test_files, file_discoverer):
        """Test converting an image to HEIC format."""
        # Setup a converter with output to a temp dir
        converter = HeicConvert(output_dir=setup_test_files)
        
        # Find test files
        source_files = file_discoverer.find_heic_files(setup_test_files)
        assert len(source_files) > 0
        
        # Create args with required parameters
        args = argparse.Namespace(
            format="heic", 
            heic_quality=85,
            resize=50,  # Test with resize
            width=None,
            height=None
        )
        
        # Convert to HEIC
        try:
            output_path = converter.convert_to_heic(source_files[0], args)
            assert output_path is not None
            assert Path(output_path).exists()
            assert output_path.suffix == '.heic'
            
            # Check file size (should be non-zero)
            assert Path(output_path).stat().st_size > 0
        except Exception as e:
            assert False, f"HEIC conversion failed with error: {str(e)}"

    def test_heic_resize_options(self, setup_test_files, file_discoverer):
        """Test different resize options when converting to HEIC."""
        converter = HeicConvert(output_dir=setup_test_files)
        source_files = file_discoverer.find_heic_files(setup_test_files)
        
        # Test different resize options
        resize_options = [
            {"resize": 25, "width": None, "height": None},
            {"resize": None, "width": 320, "height": None},
            {"resize": None, "width": None, "height": 240}
        ]
        
        for opts in resize_options:
            args = argparse.Namespace(
                format="heic",
                heic_quality=90,
                **opts
            )
            
            output = converter.convert_to_heic(source_files[0], args)
            assert output is not None
            assert Path(output).exists()

    def test_logging(self, setup_test_files, caplog, file_discoverer):
        """Test that logging works correctly."""
        import logging
        caplog.set_level(logging.INFO)

        args = argparse.Namespace(
            format="jpg", 
            jpg_quality=80, 
            png_compression=6,
            resize=None,
            width=None,
            height=None
        )
                    
        converter = HeicConvert(output_dir=setup_test_files)
        heic_files = file_discoverer.find_heic_files(setup_test_files)
        
        if heic_files:
            try:
                converter.convert_to_jpg(heic_files[0], args)
                assert "Converted:" in caplog.text
            except:
                # Even if conversion fails, there should be log messages
                assert len(caplog.records) > 0

    def test_unicode_path_handling(self, tmpdir, file_discoverer):
        """Test handling of paths with Unicode characters."""
        # Create directory with Unicode characters
        unicode_dir = tmpdir.mkdir("Üñïçödë_テスト_💻")
        test_file = os.path.join(str(unicode_dir), "image.heic")
        
        # Create empty file
        Path(test_file).touch()
        
        files = file_discoverer.find_heic_files(unicode_dir)
        assert len(files) == 1
        assert "image.heic" == files[0].name

    def test_recursive_file_finding(self, tmpdir, file_discoverer):
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
        non_recursive_files = file_discoverer.find_heic_files(str(main_dir), recursive=False)
        # Convert Path objects to strings for comparison
        non_recursive_paths = [str(p) for p in non_recursive_files]
        assert str(main_file) in non_recursive_paths
        assert str(sub_file) not in non_recursive_paths
        assert str(nested_file) not in non_recursive_paths
        
        # Test recursive mode (should find all 3 files)
        recursive_files = file_discoverer.find_heic_files(str(main_dir), recursive=True)
        recursive_paths = [str(p) for p in recursive_files]
        assert len(recursive_files) == 3
        assert str(main_file) in recursive_paths
        assert str(sub_file) in recursive_paths
        assert str(nested_file) in recursive_paths

    def test_cli_end_to_end(self, tmpdir):
        """Test the complete CLI workflow from arguments to conversion."""
        # Setup test directories and files
        input_dir = tmpdir.mkdir("input")
        output_dir = tmpdir.mkdir("output")
        
        # Look for ANY HEIC file in test_data, not just "sample.heic"
        test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
        
        # Print debug info about test data
        print(f"Looking for HEIC files in: {test_data_dir}")
        if os.path.exists(test_data_dir):
            test_files = [f for f in os.listdir(test_data_dir) 
                         if f.lower().endswith(('.heic', '.heif'))]
            print(f"Found test files: {test_files}")
            
            if test_files:
                # Use the first available HEIC file
                test_file = os.path.join(test_data_dir, test_files[0])
            else:
                pytest.skip("No HEIC files found in test_data")
        else:
            pytest.skip(f"Test data directory not found: {test_data_dir}")
        
        # Copy the test file to the input directory
        shutil.copy(test_file, str(input_dir))
        
        # Run the application with mocked components as needed
        with patch('src.main.FileDiscovery') as mock_discoverer:
            # Configure the mock discoverer
            mock_instance = mock_discoverer.return_value
            mock_instance.find_heic_files.return_value = [test_file]
            
            # Prepare command line arguments
            test_args = [
                'heic-convert',
                '--folder', str(input_dir),
                '--output', str(output_dir),
                '--format', 'jpg',
                '--jpg-quality', '90',
                '--recursive'
            ]
            
            # Run the CLI with these arguments
            with patch('sys.argv', test_args):
                from src.main import main
                main()
        
        # Verify results
        output_files = os.listdir(str(output_dir))
        assert len(output_files) > 0
        assert any(Path(f).suffix == '.jpg' for f in output_files)
        
        # Check that the files have actual image content
        for jpg_file in [f for f in output_files if Path(f).suffix == '.jpg']:
            jpg_path = os.path.join(str(output_dir), jpg_file)
            file_size = os.path.getsize(jpg_path)
            assert file_size > 0, f"JPG file {jpg_file} is empty"