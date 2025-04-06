import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
from datetime import datetime  
import platform
from src.converter import HeicConvert
from src.main import setup_logging, validate_format_arguments
import argparse
import ctypes

# Windows-specific application ID
if platform.system() == "Windows":
    myappid = 'jacquesc.heic-convert'
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
        # Get absolute path to the resources directory
        # Fix: Use only one dirname call to get the correct directory
        resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
        print(f"Resources directory: {resources_dir}")
        
        try:
            if platform.system() == "Windows":
                # On Windows, use .ico file for best integration
                ico_path = os.path.join(resources_dir, "heic-convert.ico")
                if os.path.exists(ico_path):
                    print(f"Found ICO file at: {ico_path}")
                    try:
                        # Try the standard method first
                        self.root.iconbitmap(default=ico_path)
                        print("Icon set using iconbitmap method")
                        return
                    except Exception as ico_error:
                        print(f"Error setting icon with iconbitmap: {ico_error}")
                        
                        # Fallback: Try loading with PIL and converting to PhotoImage
                        try:
                            from PIL import Image, ImageTk
                            pil_img = Image.open(ico_path)
                            icon_img = ImageTk.PhotoImage(pil_img)
                            self.root.iconphoto(True, icon_img)
                            self.icon_img = icon_img  # Keep reference
                            print("Icon set using PIL and iconphoto")
                            return
                        except Exception as pil_error:
                            print(f"PIL fallback also failed: {pil_error}")
                else:
                    print(f"ICO file not found at: {ico_path}")
                    
                    # List files in resources dir to help debugging
                    print(f"Files in resources directory:")
                    if os.path.exists(resources_dir):
                        for file in os.listdir(resources_dir):
                            print(f"  - {file}")
                    else:
                        print("  Resources directory does not exist")
            
            # For non-Windows or as fallback, use PNG
            png_path = os.path.join(resources_dir, "heic-convert.png")
            if os.path.exists(png_path):
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
        main_paned.add(log_container, weight=2)       
        
        # Position the sash (divider) at 60% of the window width
        def position_sash(event=None):
            main_paned.sashpos(0, int(self.root.winfo_width() * 0.45))
        
        # Position sash after window appears
        self.root.update_idletasks()
        self.root.after(100, position_sash)
        
        # Set up settings in the left frame
        self.setup_settings(settings_container)
        
        # Set up logs in the right frame
        self.setup_logs(log_container)
    
    def setup_settings(self, parent):
        # Settings frame
        settings_frame = ttk.LabelFrame(parent, text="Settings")
        settings_frame.pack(fill="x", padx=5, pady=5)
        
        # Source folder selection
        ttk.Label(settings_frame, text="Source Folder:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.source_var = tk.StringVar()
        source_entry = ttk.Entry(settings_frame, textvariable=self.source_var, width=25)
        source_entry.grid(row=0, column=1, padx=5, pady=5)
        self.settings_widgets.append(source_entry)
        browse_source_button = ttk.Button(settings_frame, text="Browse...", command=self.browse_source)
        browse_source_button.grid(row=0, column=2, padx=5, pady=5)
        self.settings_widgets.append(browse_source_button)
        
        # Output folder selection
        ttk.Label(settings_frame, text="Output Folder:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(settings_frame, textvariable=self.output_var, width=25)
        output_entry.grid(row=1, column=1, padx=5, pady=5)
        self.settings_widgets.append(output_entry)
        browse_output_button = ttk.Button(settings_frame, text="Browse...", command=self.browse_output)
        browse_output_button.grid(row=1, column=2, padx=5, pady=5)
        self.settings_widgets.append(browse_output_button)
        
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
        both_radio = ttk.Radiobutton(format_frame, text="Both", variable=self.format_var, value="both")
        both_radio.pack(side="left", padx=5)
        self.settings_widgets.append(both_radio)
        
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
    
    def browse_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_var.set(folder)
    
    def browse_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_var.set(folder)
    
    def log(self, message):
        """Add message to the current log text widget."""
        # For file paths, try to extract just the filename for display
        display_message = message
        if '\\' in message or '/' in message:
            # This is likely a path - check if it contains a conversion arrow
            if ' → ' in message:
                parts = message.split(' → ')
                input_file = os.path.basename(parts[0])
                output_file = os.path.basename(parts[1])
                display_message = f"{input_file} → {output_file}"
        
        # Store in current log
        self.current_log.append(display_message)
        
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
        
        if not os.path.isdir(source_folder):
            messagebox.showerror("Error", "Source folder does not exist")
            return
        
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
        output_folder = self.output_var.get() or os.path.join(source_folder, self.format_var.get())
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
            # Build args object similar to CLI version
            args = self.build_args_object()
            
            # Create converter instance
            converter = HeicConvert(
                output_dir=self.output_var.get(),
                jpg_quality=self.jpg_quality_var.get(),
                existing_mode=self.existing_var.get()
            )
            
            # Get HEIC files
            heic_files = converter.list_heic_files(self.source_var.get())
            
            if not heic_files:
                self.log("No HEIC files found in the selected directory.")
                return
            
            self.log(f"Found {len(heic_files)} HEIC files")
            total_files = len(heic_files)
            conversion_counter = 0
            
            # Convert each file
            for i, heic_file in enumerate(heic_files):
                # Check if conversion was cancelled
                if hasattr(self, 'conversion_cancelled') and self.conversion_cancelled:
                    self.log("Conversion was cancelled by user")
                    return
                    
                # Update progress
                progress_pct = (i / total_files) * 100
                self.progress_var.set(progress_pct)
                self.root.update_idletasks()
                
                try:
                    # Show which file we're processing
                    self.log(f"Converting: {os.path.basename(heic_file)}")
                    
                    # Convert the file
                    results = []
                    if self.format_var.get() in ["jpg", "both"]:
                        jpg_path = converter.convert_to_jpg(heic_file, args)
                        if jpg_path:
                            results.append(jpg_path)
                            self.log(f"  → Created: {os.path.basename(jpg_path)}")
                            conversion_counter += 1
                    
                    if self.format_var.get() in ["png", "both"]:
                        png_path = converter.convert_to_png(heic_file, args)
                        if png_path:
                            results.append(png_path)
                            self.log(f"  → Created: {os.path.basename(png_path)}")
                            conversion_counter += 1
                    
                    if not results:
                        self.log(f"  → Skipped (already exists)")
                        
                except Exception as e:
                    self.log(f"Error converting {os.path.basename(heic_file)}: {str(e)}")
            
            # Update progress to 100% at the end
            self.progress_var.set(100)
            self.log(f"Conversion completed! {conversion_counter} files created.")
            
        except Exception as e:
            self.log(f"Error during conversion: {str(e)}")
            self.status_var.set("Error occurred")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

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
        
        return args

if __name__ == "__main__":
    root = tk.Tk()
    app = HEICConverterGUI(root)
    root.mainloop()