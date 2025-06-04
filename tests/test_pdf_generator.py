import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import shutil
import os
import uuid

# Add project root to sys.path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ThoughtPrint.core import pdf_generator
from ThoughtPrint.core.pdf_generator import PDFGenerationError

class TestPdfGenerator(unittest.TestCase):

    def setUp(self):
        self.test_user_prompt = "This is a test user prompt for PDF generation"
        self.test_ai_response_markdown = "# Test Markdown\nHello, PDF!"
        
        # Create a temporary directory for any file outputs during tests
        self.test_output_dir_base = Path(__file__).resolve().parent / "test_pdf_output_temp"
        self.test_output_dir_base.mkdir(exist_ok=True)

        # Mock Path.home() to control where "Documents" is located for tests
        self.mock_home_patcher = patch('ThoughtPrint.core.pdf_generator.Path.home')
        self.mock_home = self.mock_home_patcher.start()
        self.mock_home.return_value = self.test_output_dir_base / "mock_user_home"
        
        # Ensure the mocked "Documents" directory can be created
        (self.test_output_dir_base / "mock_user_home" / "Documents").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.mock_home_patcher.stop()
        if self.test_output_dir_base.exists():
            shutil.rmtree(self.test_output_dir_base)

    @patch('ThoughtPrint.core.pdf_generator.uuid.uuid4')
    def test_get_pdf_output_path(self, mock_uuid4):
        mock_uuid4.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        # Corrected expected_dir
        expected_dir = self.test_output_dir_base / "mock_user_home" / "Documents" / "ThoughtPrint"
        expected_base_filename = "12345678123456781234567812345678"
        
        actual_dir, actual_base_filename = pdf_generator.get_pdf_output_path(self.test_user_prompt)
        
        # Directory is created by the function, so we check actual_dir against expected_dir
        self.assertEqual(actual_dir, expected_dir)
        self.assertTrue(actual_dir.exists()) # Verify it was created
        self.assertEqual(actual_base_filename, expected_base_filename)

    @patch('ThoughtPrint.core.pdf_generator.uuid.uuid4')
    def test_get_pdf_output_path_short_prompt(self, mock_uuid4):
        mock_uuid4.return_value = uuid.UUID('abcdef12-abcd-ef12-abcd-ef12abcdef12')
        short_prompt = "Hi"
        # Corrected expected_dir
        expected_dir = self.test_output_dir_base / "mock_user_home" / "Documents" / "ThoughtPrint"
        expected_base_filename = "abcdef12abcdef12abcdef12abcdef12"
        actual_dir, actual_base_filename = pdf_generator.get_pdf_output_path(short_prompt)
        self.assertEqual(actual_dir, expected_dir)
        self.assertTrue(actual_dir.exists())
        self.assertEqual(actual_base_filename, expected_base_filename)

    @patch('ThoughtPrint.core.pdf_generator.uuid.uuid4')
    def test_get_pdf_output_path_empty_prompt(self, mock_uuid4):
        mock_uuid4.return_value = uuid.UUID('11223344-aabb-ccdd-eeff-11223344aabb')
        empty_prompt = ""
        # Corrected expected_dir
        expected_dir = self.test_output_dir_base / "mock_user_home" / "Documents" / "ThoughtPrint"
        expected_base_filename = "11223344aabbccddeeff11223344aabb"
        actual_dir, actual_base_filename = pdf_generator.get_pdf_output_path(empty_prompt)
        self.assertEqual(actual_dir, expected_dir)
        self.assertTrue(actual_dir.exists())
        self.assertEqual(actual_base_filename, expected_base_filename)

    def test_sanitize_filename_segment(self):
        self.assertEqual(pdf_generator._sanitize_filename_segment("a<b>c:d*e?f\"g<h>i|j"), "abcdefghij")
        self.assertEqual(pdf_generator._sanitize_filename_segment("  leading and trailing spaces  "), "leading and trailing spaces")

    @patch('ThoughtPrint.core.pdf_generator.shutil.which')
    def test_check_pandoc_and_xelatex_pandoc_not_found(self, mock_shutil_which):
        mock_shutil_which.return_value = None # Simulate pandoc not found
        available, msg = pdf_generator.check_pandoc_and_xelatex()
        self.assertFalse(available)
        self.assertIn("Pandoc not found", msg)
        mock_shutil_which.assert_called_once_with("pandoc")

    @patch('ThoughtPrint.core.pdf_generator.shutil.which', return_value="path/to/pandoc") # pandoc found
    @patch('ThoughtPrint.core.pdf_generator.subprocess.run')
    def test_check_pandoc_and_xelatex_xelatex_not_found(self, mock_subprocess_run, mock_shutil_which):
        # Simulate xelatex check failing (e.g., return code non-zero or FileNotFoundError)
        mock_subprocess_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="xelatex not found error"), # First attempt
            MagicMock(returncode=1, stdout="", stderr="xelatex not found error")  # Second attempt (with shell=True)
        ]
        available, msg = pdf_generator.check_pandoc_and_xelatex()
        self.assertFalse(available)
        self.assertIn("XeLaTeX not found or not working correctly", msg)
        self.assertEqual(mock_subprocess_run.call_count, 2) # Both attempts made

    @patch('ThoughtPrint.core.pdf_generator.shutil.which', return_value="path/to/pandoc")
    @patch('ThoughtPrint.core.pdf_generator.subprocess.run')
    def test_check_pandoc_and_xelatex_all_found(self, mock_subprocess_run, mock_shutil_which):
        # Simulate xelatex check succeeding
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="XeTeX, Version 3.14...", stderr="")
        available, msg = pdf_generator.check_pandoc_and_xelatex()
        self.assertTrue(available)
        self.assertIn("Pandoc and XeLaTeX seem to be available", msg)

    @patch('ThoughtPrint.core.pdf_generator.uuid.uuid4')
    @patch('ThoughtPrint.core.pdf_generator.check_pandoc_and_xelatex', return_value=(True, "Dependencies OK"))
    @patch('ThoughtPrint.core.pdf_generator.subprocess.run')
    @patch('builtins.open') # Changed from new_callable=mock_open
    # @patch('ThoughtPrint.core.pdf_generator.Path.mkdir') # mkdir is called within get_pdf_output_path
    def test_create_pdf_success(self, mock_builtin_open_function, mock_subprocess_run, mock_check_deps, mock_uuid4):
        # Ensure mkdir doesn't raise errors - it's implicitly tested by get_pdf_output_path
        # mock_mkdir.return_value = None
        fixed_uuid_str = "fedcba9876543210fedcba9876543210"
        mock_uuid4.return_value = uuid.UUID(fixed_uuid_str)

        # Mock subprocess.run for pandoc
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

        # Determine expected paths based on the mocked UUID
        expected_output_dir = self.test_output_dir_base / "mock_user_home" / "Documents" / "ThoughtPrint"
        expected_base_filename = fixed_uuid_str
        expected_md_path = expected_output_dir / (expected_base_filename + ".md")
        expected_pdf_path = expected_output_dir / (expected_base_filename + ".pdf")

        # Setup specific mock for the markdown file handle and a side_effect for builtins.open
        md_file_write_mock = MagicMock()
        md_context_manager_mock = MagicMock()
        md_context_manager_mock.__enter__.return_value = md_file_write_mock

        # Generic mock for log file openings
        log_file_write_mock = MagicMock()
        log_context_manager_mock = MagicMock()
        log_context_manager_mock.__enter__.return_value = log_file_write_mock
        
        generic_write_mock = MagicMock()
        generic_context_manager_mock = MagicMock()
        generic_context_manager_mock.__enter__.return_value = generic_write_mock


        def custom_open_side_effect(path_arg, mode_arg, encoding=None, **kwargs):
            # Convert path_arg to Path for consistent comparison if it's a string
            # Path() constructor handles both string and Path objects
            opened_path = Path(path_arg)
            if opened_path == expected_md_path and mode_arg == "w":
                self.assertEqual(encoding, "utf-8", "Encoding for MD file should be utf-8")
                return md_context_manager_mock
            # Check if it's a log file (crude check, adjust if more .txt files are handled)
            elif opened_path.suffix == ".txt" and "logs" in str(opened_path.parent) and mode_arg == "a":
                self.assertEqual(encoding, "utf-8", "Encoding for log file should be utf-8")
                return log_context_manager_mock
            # Fallback for any other open call
            return generic_context_manager_mock

        mock_builtin_open_function.side_effect = custom_open_side_effect
        
        pdf_path_str = pdf_generator.create_pdf(self.test_user_prompt, self.test_ai_response_markdown)

        # 1. Assert that builtins.open was called for the markdown file
        mock_builtin_open_function.assert_any_call(expected_md_path, "w", encoding="utf-8")
        
        # 2. Assert that the markdown content was written to the specific handle for the MD file
        md_file_write_mock.write.assert_called_once_with(self.test_ai_response_markdown)
        
        # Verify pandoc command
        self.assertEqual(Path(pdf_path_str), expected_pdf_path)
        
        # The title metadata will now also be based on the UUID
        expected_title = expected_base_filename # UUID hex string has no underscores
        
        expected_pandoc_command = [
            "pandoc",
            "-s",
            "-f", "gfm",
            str(expected_md_path),
            "-o", str(expected_pdf_path),
            "--pdf-engine=xelatex",
            f"--metadata=title:{expected_title}",
            "--lua-filter", ".\\no-remote-images.lua", # Ensure this matches the actual call
            "-V", "CJKmainfont=SimSun",
        ]
        # Check the subprocess call with the new parameters including Windows-specific ones
        import sys
        expected_kwargs = {
            'capture_output': True,
            'text': True,
            'encoding': 'utf-8',
            'errors': 'replace',
            'check': False,
            'timeout': 60
        }
        
        # Add Windows-specific parameter if on Windows
        if sys.platform == "win32":
            import subprocess
            expected_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        mock_subprocess_run.assert_called_once_with(expected_pandoc_command, **expected_kwargs)

    @patch('ThoughtPrint.core.pdf_generator.check_pandoc_and_xelatex', return_value=(False, "Pandoc missing"))
    def test_create_pdf_dependency_check_fails(self, mock_check_deps):
        with self.assertRaisesRegex(PDFGenerationError, "Dependency check failed: Pandoc missing"):
            pdf_generator.create_pdf(self.test_user_prompt, self.test_ai_response_markdown)

    @patch('ThoughtPrint.core.pdf_generator.check_pandoc_and_xelatex', return_value=(True, "Dependencies OK"))
    @patch('ThoughtPrint.core.pdf_generator.subprocess.run')
    @patch('builtins.open', new_callable=mock_open) # Mock open for writing .md file
    @patch('ThoughtPrint.core.pdf_generator.Path.mkdir') # Mock mkdir
    def test_create_pdf_pandoc_fails(self, mock_mkdir, mock_open_file, mock_subprocess_run, mock_check_deps):
        mock_mkdir.return_value = None
        mock_subprocess_run.return_value = MagicMock(returncode=1, stdout="Error output", stderr="Pandoc error details")
        
        with self.assertRaisesRegex(PDFGenerationError, "Pandoc execution failed"):
            pdf_generator.create_pdf(self.test_user_prompt, self.test_ai_response_markdown)

    @patch('ThoughtPrint.core.pdf_generator.check_pandoc_and_xelatex', return_value=(True, "Dependencies OK"))
    @patch('ThoughtPrint.core.pdf_generator.subprocess.run')
    @patch('builtins.open', side_effect=IOError("Disk full")) # Simulate IOError for writing MD
    @patch('ThoughtPrint.core.pdf_generator.Path.mkdir')
    def test_create_pdf_md_write_fails(self, mock_mkdir, mock_open_file, mock_subprocess_run, mock_check_deps):
        mock_mkdir.return_value = None
        with self.assertRaisesRegex(PDFGenerationError, "Could not save Markdown file"):
            pdf_generator.create_pdf(self.test_user_prompt, self.test_ai_response_markdown)
        mock_subprocess_run.assert_not_called() # Pandoc should not be called if MD write fails

if __name__ == '__main__':
    unittest.main()