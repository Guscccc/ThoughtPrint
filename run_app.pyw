#!/usr/bin/env python3
"""
ThoughtPrint Application Launcher (No Console)
This .pyw file runs the ThoughtPrint application without showing a console window.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path so we can import ThoughtPrint
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from ThoughtPrint.main import main
    main()
except ImportError as e:
    # Fallback error handling - since we can't print to console, we'll try to show a message box
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        messagebox.showerror("Import Error", f"Failed to import ThoughtPrint: {e}")
    except ImportError:
        # If even tkinter is not available, we can't show an error
        pass
except Exception as e:
    # Handle other errors
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        messagebox.showerror("Application Error", f"An error occurred: {e}")
    except ImportError:
        # If even tkinter is not available, we can't show an error
        pass