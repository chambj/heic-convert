import os
import sys
import pytest
from unittest.mock import patch
import shutil
import argparse

from src.main import parse_arguments

def test_recursive_argument():
    """Test that the --recursive flag is properly processed."""
    # Test with recursive flag present
    with patch('sys.argv', ['heic-convert', '--folder', 'test', '--recursive']):
        # Use a new parser instance each time
        parser = argparse.ArgumentParser()
        args = parse_arguments(parser)
        assert args.recursive == True
    
    # Test without recursive flag (should default to False)
    with patch('sys.argv', ['heic-convert', '--folder', 'test']):
        # Use a new parser instance each time
        parser = argparse.ArgumentParser()
        args = parse_arguments(parser)
        assert args.recursive == False

def test_cli_end_to_end(tmpdir):
    """Test the complete CLI workflow from arguments to conversion."""
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
    assert any(f.endswith('.jpg') for f in output_files)
    
    # Check that the files have actual image content
    for jpg_file in [f for f in output_files if f.endswith('.jpg')]:
        jpg_path = os.path.join(str(output_dir), jpg_file)
        file_size = os.path.getsize(jpg_path)
        assert file_size > 0, f"JPG file {jpg_file} is empty"