import os
import sys
import pytest
import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock, patch
import tempfile
import shutil
from pathlib import Path
import platform

# Add parent directory to path to import GUI
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Proper headless detection for multiple platforms
def is_headless():
    if platform.system() == "Windows":
        # Windows - try to create a test window to see if display works
        try:
            test_root = tk.Tk()
            test_root.destroy()
            return False
        except tk.TclError:
            return True
    else:
        # Linux/Mac - check for DISPLAY variable
        return "DISPLAY" not in os.environ and os.environ.get("PYTEST_XVFB", "0") != "1"

# Skip all tests if we're in a headless environment
pytestmark = pytest.mark.skipif(
    is_headless(),
    reason="GUI tests require a display. Use pytest-xvfb for headless testing."
)

from src.gui import HEICConverterGUI

class TestHEICConverterGUI:
    @pytest.fixture
    def root(self):
        """Create a tkinter root window for testing."""
        root = tk.Tk()
        yield root
        root.destroy()
        
    @pytest.fixture
    def gui(self, root):
        """Create the GUI instance for testing."""
        with patch('gui.setup_logging') as mock_setup_logging:
            mock_logger = MagicMock()
            mock_setup_logging.return_value = mock_logger
            gui = HEICConverterGUI(root)
            # Store mock logger for tests that need to verify logging
            gui.mock_logger = mock_logger
            yield gui
    
    @pytest.fixture
    def test_files_dir(self):
        """Create test files for GUI testing."""
        temp_dir = tempfile.mkdtemp()
        
        # Create subdirectories for input and output
        input_dir = os.path.join(temp_dir, "input")
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(input_dir)
        os.makedirs(output_dir)
        
        # Copy test HEIC files if available or create dummy files
        test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
        if os.path.exists(test_data_dir):
            for test_file in os.listdir(test_data_dir):
                if test_file.lower().endswith(('.heic', '.heif')):
                    src_path = os.path.join(test_data_dir, test_file)
                    dst_path = os.path.join(input_dir, test_file)
                    shutil.copy2(src_path, dst_path)
        else:
            # Create dummy files if no test files are available
            dummy_file = os.path.join(input_dir, "test.heic")
            with open(dummy_file, 'wb') as f:
                f.write(b'Dummy HEIC file for testing')
        
        yield {
            "root_dir": temp_dir,
            "input_dir": input_dir,
            "output_dir": output_dir
        }
        
        # Clean up
        shutil.rmtree(temp_dir)
    
    def test_gui_initialization(self, gui):
        """Test that GUI initializes with all required components."""
        # Check that main components exist
        assert hasattr(gui, 'source_var')
        assert hasattr(gui, 'output_var')
        assert hasattr(gui, 'format_var')
        assert hasattr(gui, 'jpg_quality_var')
        assert hasattr(gui, 'png_compression_var')
        assert hasattr(gui, 'existing_var')
        assert hasattr(gui, 'resize_var')
        assert hasattr(gui, 'width_var')
        assert hasattr(gui, 'height_var')
        assert hasattr(gui, 'progress_var')
        assert hasattr(gui, 'status_var')
        assert hasattr(gui, 'log_text')
        assert hasattr(gui, 'history_text')
    
    def test_source_folder_selection(self, gui, test_files_dir):
        """Test selecting source folder."""
        with patch('tkinter.filedialog.askdirectory') as mock_askdir:
            mock_askdir.return_value = test_files_dir["input_dir"]
            gui.browse_source()
            assert gui.source_var.get() == test_files_dir["input_dir"]
    
    def test_output_folder_selection(self, gui, test_files_dir):
        """Test selecting output folder."""
        with patch('tkinter.filedialog.askdirectory') as mock_askdir:
            mock_askdir.return_value = test_files_dir["output_dir"]
            gui.browse_output()
            assert gui.output_var.get() == test_files_dir["output_dir"]
            
    def test_logging_functionality(self, gui):
        """Test that logging works correctly."""
        # Clear any existing logs
        gui.log_text.delete("1.0", tk.END)
        gui.current_log = []
        
        # Log a test message
        test_message = "Test log message"
        gui.log(test_message)
        
        # Verify it's in the log
        log_content = gui.log_text.get("1.0", tk.END).strip()
        assert test_message in log_content
        assert test_message in gui.current_log
    
    def test_path_formatting_in_logs(self, gui):
        """Test that paths are formatted correctly in logs."""
        gui.log_text.delete("1.0", tk.END)
        gui.current_log = []
        
        # Test a path with arrow format
        test_path = r"C:\path\to\image.heic → C:\output\image.jpg"
        gui.log(test_path)
        
        # Should show just filenames
        log_content = gui.log_text.get("1.0", tk.END).strip()
        assert "image.heic → image.jpg" in log_content
    
    def test_clear_current_log(self, gui):
        """Test clearing the current log."""
        # Add some logs
        gui.current_log = ["Test log 1", "Test log 2"]
        gui.log_text.delete("1.0", tk.END)
        for log in gui.current_log:
            gui.log_text.insert(tk.END, log + "\n")
        
        # Clear log
        with patch('gui.datetime') as mock_datetime:
            # Mock datetime to have stable test
            mock_now = MagicMock()
            mock_now.strftime.return_value = "2025-04-06 12:00:00"
            mock_datetime.now.return_value = mock_now
            
            gui.clear_current_log()
        
        # Current log should be empty
        assert len(gui.current_log) == 0
        assert gui.log_text.get("1.0", tk.END).strip() == ""
        
        # History should have the cleared logs
        assert "Test log 1" in gui.history_log
        assert "Test log 2" in gui.history_log
    
    def test_start_conversion_validates_source(self, gui):
        """Test that start_conversion validates the source folder."""
        # Empty source folder
        gui.source_var.set("")
        with patch('tkinter.messagebox.showerror') as mock_error:
            gui.start_conversion()
            mock_error.assert_called_once()
            args, _ = mock_error.call_args
            assert "source folder" in args[1].lower()
    
    def test_build_args_object(self, gui):
        """Test that build_args_object creates proper arguments."""
        # Set GUI values
        gui.format_var.set("jpg")
        gui.jpg_quality_var.set(85)
        gui.png_compression_var.set(7)
        gui.existing_var.set("rename")
        gui.resize_var.set(50)
        gui.width_var.set(0)
        gui.height_var.set(0)
        
        # Get args
        args = gui.build_args_object()
        
        # Verify values
        assert args.format == "jpg"
        assert args.jpg_quality == 85
        assert args.png_compression == 7
        assert args.existing == "rename"
        assert args.resize == 50
        assert args.width is None
        assert args.height is None
    
    @pytest.mark.parametrize("test_format", ["jpg", "png", "both"])
    def test_format_selection(self, gui, test_format):
        """Test different format selections."""
        gui.format_var.set(test_format)
        args = gui.build_args_object()
        assert args.format == test_format
    
    @patch('threading.Thread')
    def test_conversion_thread_created(self, mock_thread, gui, test_files_dir):
        """Test that conversion starts in a separate thread."""
        # Set up test data
        gui.source_var.set(test_files_dir["input_dir"])
        gui.output_var.set(test_files_dir["output_dir"])
        
        # Mock clear_current_log
        gui.clear_current_log = MagicMock()
        
        # Fix: Mock datetime directly
        with patch('gui.datetime') as mock_datetime:
            # Create a proper datetime mock with a 'now' method
            mock_now = MagicMock()
            mock_now.strftime.return_value = "2025-04-06 12:00:00"
            mock_datetime.now.return_value = mock_now
            
            # Now test the conversion with our mocks in place
            with patch('gui.os.path.isdir', return_value=True):
                gui.start_conversion()
                
                # Check thread was created and started
                mock_thread.assert_called_once()
                mock_thread.return_value.start.assert_called_once()
    
    @patch('gui.HeicConvert')
    def test_convert_files_handles_errors(self, mock_converter, gui, test_files_dir):
        """Test that convert_files handles errors gracefully."""
        # Set up test data
        gui.source_var.set(test_files_dir["input_dir"])
        gui.output_var.set(test_files_dir["output_dir"])
        
        # Set up mock converter to raise exception
        mock_instance = MagicMock()
        mock_instance.list_heic_files.side_effect = Exception("Test exception")
        mock_converter.return_value = mock_instance
        
        # Call convert_files
        with patch('tkinter.messagebox.showerror') as mock_error:
            gui.convert_files()
            
            # Should show error dialog
            mock_error.assert_called_once()
            # Status should be updated
            assert gui.status_var.get() == "Error occurred"
    
    @patch('gui.threading.Thread')
    def test_actual_file_conversion(self, mock_thread, gui, test_files_dir):
        """Test actual conversion with real HEIC files from test_data."""
        # Set up the GUI with real directories
        gui.source_var.set(test_files_dir["input_dir"])
        gui.output_var.set(test_files_dir["output_dir"])
        gui.format_var.set("jpg")  # Test with JPG format
        gui.jpg_quality_var.set(90)
        gui.existing_var.set("overwrite")  # Use overwrite to handle any existing files
        
        # Get initial file count in the output directory
        initial_files = os.listdir(test_files_dir["output_dir"])
        
        # Count HEIC files in input directory
        input_heic_files = [f for f in os.listdir(test_files_dir["input_dir"]) 
                            if f.lower().endswith(('.heic', '.heif'))]
        
        if not input_heic_files:
            pytest.skip("No HEIC files found in test_data to use for conversion test")
        
        # Set up a spy to capture the function passed to Thread
        thread_target_capture = []
        def mock_thread_init(*args, **kwargs):
            thread_mock = MagicMock()
            if 'target' in kwargs:
                thread_target_capture.append(kwargs['target'])
            return thread_mock
        
        mock_thread.side_effect = mock_thread_init
        
        # Mock the asynchronous thread to run synchronously
        with patch('gui.os.path.isdir', return_value=True):
            with patch('gui.datetime', autospec=True) as mock_datetime:
                # Create a proper datetime mock
                mock_now = MagicMock()
                mock_now.strftime.return_value = "2025-04-06 12:00:00"
                mock_datetime.now.return_value = mock_now
                
                # Start conversion
                gui.start_conversion()
                
                # Check thread was created with a target function
                assert len(thread_target_capture) > 0, "No thread target function was captured"
                
                # Now run the captured function (which should be convert_files)
                with patch('tkinter.messagebox.showerror'):  # Prevent error dialogs
                    thread_target_capture[0]()
        
        # Check output directory for new files
        output_files = os.listdir(test_files_dir["output_dir"])
        new_files = [f for f in output_files if f not in initial_files]
        
        # Check that we created the expected number of JPG files
        jpg_files = [f for f in new_files if f.lower().endswith('.jpg')]
        assert len(jpg_files) > 0, "No JPG files were created during conversion"
        
        # Check that the files have actual image content
        for jpg_file in jpg_files:
            jpg_path = os.path.join(test_files_dir["output_dir"], jpg_file)
            file_size = os.path.getsize(jpg_path)
            assert file_size > 0, f"JPG file {jpg_file} is empty"