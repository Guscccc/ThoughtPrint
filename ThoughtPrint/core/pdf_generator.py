import subprocess
import tempfile
import os
import sys
from pathlib import Path
import shutil # For checking if pandoc is available
import uuid
from .logger import log_info, log_warning, log_error

class PDFGenerationError(Exception):
    """Custom exception for PDF generation errors."""
    pass

def _sanitize_filename_segment(segment):
    """Basic sanitization for a filename segment."""
    # Remove characters not typically allowed or problematic in filenames.
    # This is a basic list; more comprehensive sanitization might be needed.
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        segment = segment.replace(char, '')
    return segment.strip()

def get_pdf_output_path(user_prompt):
    """
    Determines the output directory and filename for the PDF.
    Filename is based on the first 5 words of the user_prompt.
    Output directory is 'User's Documents Folder / ThoughtPrint /'.
    """
    # Determine user's Documents folder
    documents_dir = Path.cwd() # Default fallback to current working directory

    try:
        home_dir = Path.home()
        documents_candidate = home_dir / "Documents"
        
        if documents_candidate.is_dir():
            documents_dir = documents_candidate
        else:
            # Check XDG_DOCUMENTS_DIR for Linux
            xdg_docs_path = os.environ.get("XDG_DOCUMENTS_DIR")
            if xdg_docs_path:
                xdg_docs_candidate = Path(xdg_docs_path)
                if xdg_docs_candidate.is_dir():
                    documents_dir = xdg_docs_candidate
            
            # If "Documents" doesn't exist or is not a directory, and XDG_DOCUMENTS_DIR also failed,
            # then fallback to the user's home directory.
            if not documents_dir and home_dir.is_dir():
                documents_dir = home_dir

    except Exception as e:
        log_warning(f"Error determining user's Documents directory: {e}. Falling back to current working directory.")
        # documents_dir is already Path.cwd() from initialization

    # Ensure the final documents_dir is indeed a directory
    if not documents_dir.is_dir():
        log_warning(f"Final determined documents path '{documents_dir}' is not a directory. Using current working directory as fallback.")
        documents_dir = Path.cwd()

    output_dir_name = "ThoughtPrint"
    output_base_dir = documents_dir / output_dir_name
    
    try:
        output_base_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise PDFGenerationError(f"Could not create output directory '{output_base_dir}': {e}")
    
    # Generate a random filename using UUID
    base_filename_segment = uuid.uuid4().hex
    
    # Sanitization might not be strictly necessary for a UUID hex string,
    # but keeping it doesn't hurt and maintains consistency if the
    # sanitization logic were to become more complex.
    sanitized_base_filename = _sanitize_filename_segment(base_filename_segment)
    
    # Return the directory and the sanitized (or in this case, already safe) base filename
    return output_base_dir, sanitized_base_filename


def check_pandoc_and_xelatex():
    """Checks if pandoc and a common xelatex command are available."""
    if not shutil.which("pandoc"):
        return False, "Pandoc not found in system PATH."
    # Checking for xelatex is trickier as it's part of a TeX distribution.
    # A simple check for `xelatex --version` might suffice.
    try:
        # Use a common command that xelatex should respond to without processing a file.
        # On Windows, subprocess might need shell=True for PATH resolution sometimes,
        # but it's generally safer to avoid it if possible.
        # For non-Windows, shell=False is fine.
        # Let's try without shell=True first.
        
        # Prepare subprocess arguments to hide terminal window on Windows
        subprocess_kwargs = {
            'capture_output': True,
            'text': True,
            'encoding': 'utf-8',
            'errors': 'replace',
            'check': False,
            'timeout': 10
        }
        
        # Hide terminal window on Windows
        if sys.platform == "win32":
            subprocess_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        process = subprocess.run(["xelatex", "--version"], **subprocess_kwargs)
        if process.returncode != 0 or "XeTeX" not in process.stdout:
             # Try with shell=True as a fallback for some environments, especially Windows
            subprocess_kwargs_shell = subprocess_kwargs.copy()
            subprocess_kwargs_shell['shell'] = True
            process_shell = subprocess.run("xelatex --version", **subprocess_kwargs_shell)
            if process_shell.returncode != 0 or "XeTeX" not in process_shell.stdout:
                return False, "XeLaTeX not found or not working correctly. Ensure a TeX distribution (like TeX Live or MiKTeX) with xelatex is installed."
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e: # OSError for other execution issues
        return False, f"XeLaTeX check failed: {e}. Ensure a TeX distribution is installed and in PATH."
    return True, "Pandoc and XeLaTeX seem to be available."


def create_pdf(user_prompt, ai_response_markdown):
    """
    Creates a PDF from the AI's Markdown response using pandoc.
    Supports math and Chinese characters via xelatex.

    Args:
        user_prompt (str): The original user prompt (used for filename).
        ai_response_markdown (str): The AI's response in Markdown format.

    Returns:
        str: The path to the generated PDF file.

    Raises:
        PDFGenerationError: If PDF creation fails.
    """
    pandoc_ok, pandoc_msg = check_pandoc_and_xelatex()
    if not pandoc_ok:
        raise PDFGenerationError(f"Dependency check failed: {pandoc_msg}")

    output_dir, base_filename = get_pdf_output_path(user_prompt) # Changed to get_output_path
    
    md_file_path = output_dir / (base_filename + ".md")
    pdf_file_path = output_dir / (base_filename + ".pdf")

    # 1. Save the raw Markdown response to a .md file
    try:
        with open(md_file_path, "w", encoding="utf-8") as md_file:
            md_file.write(ai_response_markdown)
        log_info(f"Markdown response saved to: {md_file_path}")
    except IOError as e:
        raise PDFGenerationError(f"Could not save Markdown file to '{md_file_path}': {e}")

    # 2. Convert the saved .md file to .pdf using pandoc
    try:
        pandoc_command = [
            "pandoc",
            "-s",  # Standalone document
            "-f", "gfm",  # Input format: GitHub Flavored Markdown
            str(md_file_path), # Input file
            "-o", str(pdf_file_path), # Output file
            "--pdf-engine=xelatex",
            f"--metadata=title:{base_filename.replace('_', ' ')}", # Add title metadata
            "--lua-filter", ".\\no-remote-images.lua",
            "-V", "CJKmainfont=SimSun",
        ]
        
        # Prepare subprocess arguments to hide terminal window on Windows
        subprocess_kwargs = {
            'capture_output': True,
            'text': True,
            'encoding': 'utf-8',
            'errors': 'replace',
            'check': False,
            'timeout': 60
        }
        
        # Hide terminal window on Windows
        if sys.platform == "win32":
            subprocess_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        process = subprocess.run(pandoc_command, **subprocess_kwargs)

        if process.returncode != 0:
            error_message = f"Pandoc execution failed (return code {process.returncode}).\n"
            error_message += f"Stdout: {process.stdout}\nStderr: {process.stderr}\n"
            error_message += "Ensure Pandoc, XeLaTeX, and required fonts (e.g., SimSun) are installed and configured."
            # Optionally, attempt to remove the successfully created .md file if PDF fails
            # or leave it for debugging. For now, leave it.
            raise PDFGenerationError(error_message)
        
        log_info(f"PDF generated successfully: {pdf_file_path}")
        # Return path to the PDF, .md is already saved.
        return str(pdf_file_path)

    except subprocess.TimeoutExpired:
        raise PDFGenerationError("Pandoc command timed out. The document might be too large or complex.")
    except FileNotFoundError:
        raise PDFGenerationError("Pandoc executable not found. Please ensure it's installed and in PATH.")
    except Exception as e:
        raise PDFGenerationError(f"An unexpected error occurred during PDF generation via Pandoc: {e}")
    # No temporary file to clean up here as we are writing directly to the target .md file.


if __name__ == '__main__':
    # Initialize logging for standalone testing
    from .logger import init_logging
    init_logging()
    
    log_info("Testing PDF Generator...")
    
    # Check dependencies first
    available, message = check_pandoc_and_xelatex()
    log_info(f"Dependency Check: {message}")

    if not available:
        log_warning("Cannot run PDF generation test due to missing dependencies.")
    else:
        test_prompt = "你好世界 first five words example"
        test_markdown_content = """
# Hello, 世界!

This is a test document with **Markdown** formatting.

## Math Examples

Inline math: $E = mc^2$

Display math:
$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
$$

## Chinese Text

这是一段中文测试文字，包含一些常用字词。
希望能够正确渲染。

你好，Pandoc！
"""
        log_info(f"\nAttempting to generate PDF for prompt: '{test_prompt}'")
        try:
            pdf_path = create_pdf(test_prompt, test_markdown_content)
            log_info(f"PDF generated successfully: {pdf_path}")
            log_info(f"Please check the file at the location above (likely in your Documents/ThoughtPrint folder).")
        except PDFGenerationError as e:
            log_error(f"PDF Generation Error: {e}")
        except Exception as e:
            log_error(f"An unexpected error occurred: {e}")

        # Test with a very short prompt for filename generation
        short_prompt = "Test"
        log_info(f"\nAttempting to generate PDF for short prompt: '{short_prompt}'")
        try:
            pdf_path_short = create_pdf(short_prompt, "Simple content for short prompt.")
            log_info(f"PDF for short prompt generated successfully: {pdf_path_short}")
        except PDFGenerationError as e:
            log_error(f"PDF Generation Error (short prompt): {e}")