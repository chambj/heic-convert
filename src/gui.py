import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
from datetime import datetime  
import platform
from src.converter import HeicConvert
from src.main import setup_logging, validate_format_arguments
from src.file_discovery import FileDiscovery
from src.conversion_manager import perform_conversion
import argparse
import ctypes
import webbrowser 
from src.version import VERSION

# Windows-specific application ID
if platform.system() == "Windows":
    myappid = 'jc.heic-convert.5E31-4C6A-8F0E-BFA7EA4D2433'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

class HEICConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HEIC Converter")
        self.root.geometry("1000x550")  # Increase initial window size
        self.root.minsize(900, 450)     # Set minimum window size
        self.root.resizable(True, True)
        
        # Conversion state tracking
        self.conversion_running = False
        self.conversion_cancelled = False
        
        # Initialize all container lists first - before any UI setup
        self.settings_widgets = []  # Must be initialized before setup_ui
        self.current_log = []
        self.history_log = []
        
        # Add the application icon/logo with platform-specific handling
        self.set_application_icon()
        
        self.logger = setup_logging()
        
        # Now that all containers are initialized, set up the UI
        self.setup_ui()
    
    def set_application_icon(self):
        """Set application icon with platform-specific handling."""
        # Special handling for PyInstaller bundles
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running as compiled executable
            base_path = sys._MEIPASS
            resources_dir = Path(base_path) / "resources"
        else:
            # Running as script
            resources_dir = Path(__file__).absolute().parent.parent / "resources"
        
        print(f"Resources directory: {resources_dir}")
        
        try:
            if platform.system() == "Windows":
                # On Windows, use .ico file for best integration
                ico_path = Path(resources_dir / "heic-convert.ico")
                if Path(ico_path).exists():
                    print(f"Found ICO file at: {ico_path}")
                    try:
                        # Try the standard method first
                        self.root.iconbitmap(default=ico_path)
                        print("Icon set using iconbitmap method")
                        return
                    except Exception as ico_error:
                        print(f"Error setting icon with iconbitmap: {ico_error}")
                else:
                    print(f"ICO file not found at: {ico_path}")
                    # List files in resources dir to help debugging
                    if Path(resources_dir).exists():
                        print(f"Files in resources directory:")
                        for file in os.listdir(resources_dir):
                            print(f"  - {file}")
                    else:
                        print("  Resources directory does not exist")
            
            # For non-Windows or as fallback, use PNG
            png_path = Path(resources_dir / "heic-convert.png")
            if Path(png_path).exists():
                print(f"Found PNG file at: {png_path}")
                try:
                    logo_img = tk.PhotoImage(file=png_path)
                    self.root.iconphoto(True, logo_img)
                    # Store the image to prevent garbage collection
                    self.logo_img = logo_img
                    print("Icon set using PhotoImage and iconphoto")
                    return
                except Exception as png_error:
                    print(f"Error setting icon with PNG: {png_error}")
            else:
                print(f"PNG file not found at: {png_path}")
        except Exception as e:
            print(f"Could not load application icon: {e}")
    
    def setup_ui(self):
        # Create main paned window for side-by-side layout
        main_paned = ttk.PanedWindow(self.root, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left frame for settings
        settings_container = ttk.Frame(main_paned, width=350)  # Set preferred width
        settings_container.pack_propagate(False)  # Prevent shrinking
        
        # Right frame for logs
        log_container = ttk.Frame(main_paned)
        
        # Add frames to paned window with weights
        main_paned.add(settings_container, weight=1)  
        main_paned.add(log_container, weight=3)       
        
        # Position the sash (divider) at 45% of the window width
        def position_sash(event=None):
            main_paned.sashpos(0, int(self.root.winfo_width() * 0.45))
        
        # Position sash after window appears
        self.root.update_idletasks()
        self.root.after(100, position_sash)
        
        # Set up settings in the left frame
        self.setup_settings(settings_container)
        
        # Set up logs in the right frame
        self.setup_logs(log_container)

        # Add footer with GitHub link
        self.setup_footer()
    
    def setup_settings(self, parent):
        # Settings frame
        settings_frame = ttk.LabelFrame(parent, text="Settings")
        settings_frame.pack(fill="x", padx=5, pady=5)
        
        # Source folder selection
        ttk.Label(settings_frame, text="Source Folder:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.source_var = tk.StringVar()
        source_entry = ttk.Entry(settings_frame, textvariable=self.source_var)
        source_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew") 
        self.settings_widgets.append(source_entry)
        browse_source_button = ttk.Button(settings_frame, text="Browse...", command=self.browse_source)
        browse_source_button.grid(row=0, column=2, padx=5, pady=5)
        self.settings_widgets.append(browse_source_button)
        
        # Output folder selection
        ttk.Label(settings_frame, text="Output Folder:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(settings_frame, textvariable=self.output_var)
        output_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew") 
        self.settings_widgets.append(output_entry)
        browse_output_button = ttk.Button(settings_frame, text="Browse...", command=self.browse_output)
        browse_output_button.grid(row=1, column=2, padx=5, pady=5)
        self.settings_widgets.append(browse_output_button)
                
        # Configure column weights to allow horizontal expansion
        settings_frame.columnconfigure(1, weight=1)

        # Format selection
        ttk.Label(settings_frame, text="Output Format:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.format_var = tk.StringVar(value="jpg")
        format_frame = ttk.Frame(settings_frame)
        format_frame.grid(row=2, column=1, sticky="w", padx=5, pady=5, columnspan=2)
        jpg_radio = ttk.Radiobutton(format_frame, text="JPG", variable=self.format_var, value="jpg")
        jpg_radio.pack(side="left", padx=5)
        self.settings_widgets.append(jpg_radio)
        png_radio = ttk.Radiobutton(format_frame, text="PNG", variable=self.format_var, value="png")
        png_radio.pack(side="left", padx=5)
        self.settings_widgets.append(png_radio)
        heic_radio = ttk.Radiobutton(format_frame, text="HEIC", variable=self.format_var, value="heic")
        heic_radio.pack(side="left", padx=5)
        self.settings_widgets.append(heic_radio)
        
        # JPG Quality
        ttk.Label(settings_frame, text="JPG Quality (1-100):").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.jpg_quality_var = tk.IntVar(value=90)
        jpg_quality_spinbox = ttk.Spinbox(settings_frame, from_=1, to=100, textvariable=self.jpg_quality_var, width=5)
        jpg_quality_spinbox.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        self.settings_widgets.append(jpg_quality_spinbox)
        
        # PNG Compression
        ttk.Label(settings_frame, text="PNG Compression (0-9):").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.png_compression_var = tk.IntVar(value=6)
        png_compression_spinbox = ttk.Spinbox(settings_frame, from_=0, to=9, textvariable=self.png_compression_var, width=5)
        png_compression_spinbox.grid(row=4, column=1, sticky="w", padx=5, pady=5)
        self.settings_widgets.append(png_compression_spinbox)
        
        # Existing file handling
        ttk.Label(settings_frame, text="If File Exists:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
        self.existing_var = tk.StringVar(value="fail")
        existing_combobox = ttk.Combobox(settings_frame, textvariable=self.existing_var, values=["fail", "rename", "overwrite"], width=10)
        existing_combobox.grid(row=5, column=1, sticky="w", padx=5, pady=5)
        self.settings_widgets.append(existing_combobox)
        
        # Recursive search option
        self.recursive_var = tk.BooleanVar(value=False)
        recursive_check = ttk.Checkbutton(settings_frame, text="Search subdirectories recursively", 
                                          variable=self.recursive_var)
        recursive_check.grid(row=6, column=0, columnspan=3, padx=5, pady=5, sticky="w")
        
        # Log file selection
        ttk.Label(settings_frame, text="Log File:").grid(row=7, column=0, sticky="w", padx=5, pady=5)
        self.log_file_var = tk.StringVar()
        log_file_entry = ttk.Entry(settings_frame, textvariable=self.log_file_var)
        log_file_entry.grid(row=7, column=1, padx=5, pady=5, sticky="ew") 
        self.settings_widgets.append(log_file_entry)
        browse_log_button = ttk.Button(settings_frame, text="Browse...", command=self.browse_log_file)
        browse_log_button.grid(row=7, column=2, padx=5, pady=5)

        # Resize options
        resize_frame = ttk.LabelFrame(parent, text="Resize Options")
        resize_frame.pack(fill="x", padx=5, pady=5)
        
        # Resize by percentage
        ttk.Label(resize_frame, text="Resize By Percentage:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.resize_var = tk.IntVar(value=0)
        resize_spinbox = ttk.Spinbox(resize_frame, from_=0, to=100, textvariable=self.resize_var, width=5)
        resize_spinbox.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.settings_widgets.append(resize_spinbox)
        ttk.Label(resize_frame, text="% (0 = no resize)").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        
        # Resize by width
        ttk.Label(resize_frame, text="Width:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.width_var = tk.IntVar(value=0)
        width_spinbox = ttk.Spinbox(resize_frame, from_=0, to=10000, textvariable=self.width_var, width=5)
        width_spinbox.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.settings_widgets.append(width_spinbox)
        ttk.Label(resize_frame, text="pixels (0 = don't set width)").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        
        # Resize by height
        ttk.Label(resize_frame, text="Height:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.height_var = tk.IntVar(value=0)
        height_spinbox = ttk.Spinbox(resize_frame, from_=0, to=10000, textvariable=self.height_var, width=5)
        height_spinbox.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        self.settings_widgets.append(height_spinbox)
        ttk.Label(resize_frame, text="pixels (0 = don't set height)").grid(row=2, column=2, sticky="w", padx=5, pady=5)
        
        # Convert button
        self.convert_button = ttk.Button(parent, text="Convert Files", command=self.start_conversion)
        self.convert_button.pack(pady=10)
        self.settings_widgets.append(self.convert_button)
        
        # Stop button
        self.stop_button = ttk.Button(parent, text="Stop Conversion", command=self.stop_conversion)
        self.stop_button.pack(pady=10)
        self.stop_button.configure(state="disabled")
        
        # Progress information
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill="x", padx=5, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress.pack(fill="x", side="left", expand=True)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(parent, textvariable=self.status_var).pack(pady=5)
    
    def setup_logs(self, parent):
        # Create a notebook with tabs for current and history logs
        self.log_notebook = ttk.Notebook(parent)
        self.log_notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Current run tab
        current_frame = ttk.Frame(self.log_notebook)
        self.log_notebook.add(current_frame, text="Current Run")
        
        # History tab
        history_frame = ttk.Frame(self.log_notebook)
        self.log_notebook.add(history_frame, text="Previous Runs")
        
        # Set up the current log text widget
        self.log_text = tk.Text(current_frame, wrap="word")
        self.log_text.pack(fill="both", expand=True, side="left")
        
        current_scrollbar = ttk.Scrollbar(current_frame, command=self.log_text.yview)
        current_scrollbar.pack(fill="y", side="right")
        self.log_text.config(yscrollcommand=current_scrollbar.set)
        
        # Set up the history log text widget
        self.history_text = tk.Text(history_frame, wrap="word")
        self.history_text.pack(fill="both", expand=True, side="left")
        
        history_scrollbar = ttk.Scrollbar(history_frame, command=self.history_text.yview)
        history_scrollbar.pack(fill="y", side="right")
        self.history_text.config(yscrollcommand=history_scrollbar.set)

    def setup_footer(self):
        """Set up footer with GitHub link and license information."""
        footer_frame = ttk.Frame(self.root)
        footer_frame.pack(side="bottom", fill="x", padx=10, pady=5)
        
        # Create a style for hyperlink
        link_style = ttk.Style()
        link_style.configure("Link.TLabel", foreground="blue", font=("", 9, "underline"))
        
        # GitHub link label
        github_link = ttk.Label(
            footer_frame, 
            text="View License and Terms on GitHub", 
            style="Link.TLabel",
            cursor="hand2"  # Hand cursor on hover
        )
        github_link.pack(side="right", padx=5)
        
        # Version info on the left
        version_label = ttk.Label(footer_frame, text=f"HEIC Converter v{VERSION}")
        version_label.pack(side="left", padx=5)
        
        # Bind click event
        github_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/chambj/heic-convert"))
    
    def browse_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_var.set(folder)
    
    def browse_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_var.set(folder)
    
    def browse_log_file(self):
        log_file = filedialog.asksaveasfilename(
            title="Select Log File",
            defaultextension=".log",
            filetypes=[("Log Files", "*.log"), ("All Files", "*.*")]
        )
        if log_file:
            self.log_file_var.set(log_file)
    
    def log(self, message):
        """Add message to the current log text widget and to the file logger."""
        # For file paths, try to extract just the filename for display
        display_message = message
        if '\\' in message or '/' in message:
            # This is likely a path - check if it contains a conversion arrow
            if ' → ' in message:
                parts = message.split(' → ')
                input_file = Path(parts[0]).name
                output_file = Path(parts[1]).name
                display_message = f"{input_file} → {output_file}"
        
        # Store in current log
        self.current_log.append(display_message)
        
        # Also log to the file logger
        self.logger.info(message)
        
        # Update display
        self.log_text.insert(tk.END, display_message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_current_log(self):
        """Clear the current log and move its contents to history."""
        if self.current_log:
            # Add a separator to the history
            self.history_log.append("\n" + "-" * 50)
            self.history_log.append(f"Run completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.history_log.append("-" * 50)
            
            # Add current log to history
            self.history_log.extend(self.current_log)
            
            # Update history text
            self.history_text.delete("1.0", tk.END)
            for line in self.history_log:
                self.history_text.insert(tk.END, line + "\n")
            self.history_text.see(tk.END)
            
            # Clear current log
            self.current_log = []
            self.log_text.delete("1.0", tk.END)
    
    def start_conversion(self):
        """Prepare and start the conversion process."""
        source_folder = self.source_var.get()
        if not source_folder:
            messagebox.showerror("Error", "Please select a source folder")
            return
        
        if not Path(source_folder).is_dir():
            messagebox.showerror("Error", "Source folder does not exist")
            return
        
        output_folder = self.output_var.get()
        if not output_folder:
            messagebox.showerror("Error", "Please select an output folder")
            return

        if not Path(output_folder).is_dir():
            messagebox.showerror("Error", "Output folder does not exist")
            return
        
        # Build args object with current settings
        args = self.build_args_object()
    
        # Re-configure logger with current log file setting
        self.logger = setup_logging(args)
        self.log(f"HEIC Converter v{VERSION}")

        # Clear current log and move to history before starting new conversion
        self.clear_current_log()
        
        # Select the current run tab
        self.log_notebook.select(0)
        
        # Set conversion state
        self.conversion_running = True
        self.conversion_cancelled = False
        
        # Disable settings during conversion
        self.disable_settings()
        
        # Update UI to show we're starting
        self.status_var.set("Converting...")
        self.progress_var.set(0)
        self.root.update_idletasks()
        
        # Log the start of conversion with source/destination info
        self.log(f"Starting conversion: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Source folder: {source_folder}")
        output_folder = self.output_var.get() or Path(source_folder / self.format_var.get())
        self.log(f"Output folder: {output_folder}")
        self.log(f"Format: {self.format_var.get()}")
        self.log("-" * 30)
        
        # Start conversion in a separate thread to keep UI responsive
        self.conversion_thread = threading.Thread(target=self.convert_files)
        self.conversion_thread.daemon = True
        self.conversion_thread.start()
        
        # Schedule a check to update the UI with conversion progress
        self.root.after(100, self.check_conversion_progress)

    def stop_conversion(self):
        """Trigger cancellation of the conversion process."""
        if hasattr(self, 'conversion_running') and self.conversion_running:
            self.conversion_cancelled = True
            self.status_var.set("Cancelling...")
            self.log("Cancelling conversion... (this may take a moment)")

    def check_conversion_progress(self):
        """Check if conversion is still running and update UI accordingly."""
        if hasattr(self, 'conversion_thread') and self.conversion_thread.is_alive():
            # If still running, check again in 100ms
            self.root.after(100, self.check_conversion_progress)
        else:
            # Conversion is done
            if hasattr(self, 'conversion_cancelled') and self.conversion_cancelled:
                self.status_var.set("Conversion cancelled")
            else:
                self.status_var.set("Conversion complete")
            
            self.progress_var.set(100)  # Set progress to 100%
            
            # Re-enable settings
            self.enable_settings()
            
            # Reset conversion state
            self.conversion_running = False
            self.conversion_cancelled = False

    def disable_settings(self):
        """Disable all settings widgets during conversion."""
        for widget in self.settings_widgets:
            widget.configure(state="disabled")
        
        # Toggle control buttons
        self.convert_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

    def enable_settings(self):
        """Enable all settings widgets after conversion."""
        for widget in self.settings_widgets:
            widget.configure(state="normal")
        
        # Toggle control buttons
        self.convert_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def convert_files(self):
        """Actual conversion process that runs in a separate thread."""
        try:
            # Get the output folder
            output_folder = self.output_var.get() or Path(self.source_var.get() / self.format_var.get())
            
            # Build args
            args = self.build_args_object()
            
            # Create converter with current settings
            heic_converter = HeicConvert(
                output_dir=output_folder,
                jpg_quality=args.jpg_quality,
                existing_mode=args.existing
            )
            
            file_discoverer = FileDiscovery()
            heic_files = file_discoverer.find_heic_files(
                self.source_var.get(), 
                recursive=args.recursive
            )
            
            # No files found
            if not heic_files:
                self.log("No HEIC files found in the selected directory.")
                self.update_status("No HEIC files found")
                return
            
            self.log(f"Found {len(heic_files)} HEIC files to convert")
            
            # Update progress bar and status
            def update_progress(current, total):
                progress = int((current / total) * 100)
                self.progress_var.set(progress)
                self.update_status(f"Converting file {current}/{total}")
            
            # Run the common conversion function
            results = perform_conversion(heic_files, args, heic_converter, self.logger, update_progress)
            
            # Display summary
            self.log(f"Conversion complete: {results['success_count']} files converted, {results['failure_count']} failed, {results['skipped_count']} skipped.")
            self.log(f"Total original size: {results['total_original_size']:.2f} MB")
            self.log(f"Total converted size: {results['total_converted_size']:.2f} MB")
            
            space_diff = results['space_diff']
            if space_diff > 0:
                self.log(f"Space saved: {space_diff:.2f} MB")
            else:
                self.log(f"Space increased: {-space_diff:.2f} MB")
            
            # Update status
            self.update_status("Conversion complete")
            
        except Exception as e:
            self.log(f"Error during conversion: {str(e)}")
            self.update_status("Conversion failed")
            messagebox.showerror("Error", f"An error occurred during conversion: {str(e)}")

    def build_args_object(self):
        """Build an argparse.Namespace object with GUI settings."""
        args = argparse.Namespace()
        args.format = self.format_var.get()
        args.jpg_quality = self.jpg_quality_var.get()
        args.png_compression = self.png_compression_var.get()
        args.existing = self.existing_var.get()
        
        # Handle resize options
        args.resize = self.resize_var.get() if self.resize_var.get() > 0 else None
        args.width = self.width_var.get() if self.width_var.get() > 0 else None
        args.height = self.height_var.get() if self.height_var.get() > 0 else None
        args.recursive = self.recursive_var.get()
        
        # Add log file path
        args.log_file = self.log_file_var.get() if self.log_file_var.get() else None
        
        return args

    def update_status(self, message):
        """Update the status label with a new message."""
        self.status_var.set(message)
        self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = HEICConverterGUI(root)
    root.mainloop()