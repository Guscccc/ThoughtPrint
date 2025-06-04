import unittest
from unittest.mock import patch, MagicMock

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Need QApplication for QObject-based Worker if not already handled by test runner
from PyQt6.QtWidgets import QApplication 
# Initialize QApplication instance for testing QObject signals if not already present
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


from ThoughtPrint.ui.main_window import Worker # Worker class to test
from ThoughtPrint.core import ai_handler, pdf_generator # To mock their functions
from ThoughtPrint.core.ai_handler import AICommunicationError
from ThoughtPrint.core.pdf_generator import PDFGenerationError


class TestWorker(unittest.TestCase):

    def setUp(self):
        self.prompt = "test prompt"
        self.provider_config = {"name": "test_provider", "type": "ollama", "base_url": "url", "model": "model"}
        self.system_prompt = "test system prompt"
        self.worker = Worker(self.prompt, self.provider_config, self.system_prompt)

        # Mock signals to check if they are emitted
        self.worker.success = MagicMock(wraps=self.worker.success)
        self.worker.error = MagicMock(wraps=self.worker.error)
        self.worker.finished = MagicMock(wraps=self.worker.finished)

    @patch('ThoughtPrint.core.ai_handler.get_ai_response')
    @patch('ThoughtPrint.core.pdf_generator.create_pdf')
    def test_worker_run_success(self, mock_create_pdf, mock_get_ai_response):
        mock_get_ai_response.return_value = "mocked AI response"
        mock_create_pdf.return_value = "/path/to/mocked.pdf"

        self.worker.run()

        mock_get_ai_response.assert_called_once_with(self.prompt, self.provider_config, self.system_prompt)
        mock_create_pdf.assert_called_once_with(self.prompt, "mocked AI response")
        self.worker.success.emit.assert_called_once_with("/path/to/mocked.pdf")
        self.worker.error.emit.assert_not_called()
        self.worker.finished.emit.assert_called_once()

    @patch('ThoughtPrint.core.ai_handler.get_ai_response')
    def test_worker_run_ai_communication_error(self, mock_get_ai_response):
        mock_get_ai_response.side_effect = AICommunicationError("AI network issue")

        self.worker.run()

        mock_get_ai_response.assert_called_once_with(self.prompt, self.provider_config, self.system_prompt)
        self.worker.error.emit.assert_called_once_with("AI Error", "Error communicating with AI provider: AI network issue")
        self.worker.success.emit.assert_not_called()
        self.worker.finished.emit.assert_called_once()

    @patch('ThoughtPrint.core.ai_handler.get_ai_response')
    def test_worker_run_ai_value_error(self, mock_get_ai_response):
        mock_get_ai_response.side_effect = ValueError("AI config issue") # e.g. missing key

        self.worker.run()
        
        mock_get_ai_response.assert_called_once_with(self.prompt, self.provider_config, self.system_prompt)
        self.worker.error.emit.assert_called_once_with("AI Configuration Error", "AI configuration error: AI config issue")
        self.worker.success.emit.assert_not_called()
        self.worker.finished.emit.assert_called_once()

    @patch('ThoughtPrint.core.ai_handler.get_ai_response')
    @patch('ThoughtPrint.core.pdf_generator.create_pdf')
    def test_worker_run_pdf_generation_error(self, mock_create_pdf, mock_get_ai_response):
        mock_get_ai_response.return_value = "mocked AI response"
        mock_create_pdf.side_effect = PDFGenerationError("PDF creation failed")

        self.worker.run()

        mock_get_ai_response.assert_called_once_with(self.prompt, self.provider_config, self.system_prompt)
        mock_create_pdf.assert_called_once_with(self.prompt, "mocked AI response")
        self.worker.error.emit.assert_called_once_with("PDF Generation Error", "Error generating PDF: PDF creation failed")
        self.worker.success.emit.assert_not_called()
        self.worker.finished.emit.assert_called_once()

    @patch('ThoughtPrint.core.ai_handler.get_ai_response')
    def test_worker_run_unexpected_ai_error(self, mock_get_ai_response):
        mock_get_ai_response.side_effect = Exception("Unexpected AI problem")

        self.worker.run()

        mock_get_ai_response.assert_called_once_with(self.prompt, self.provider_config, self.system_prompt)
        self.worker.error.emit.assert_called_once_with("Unexpected AI Error", "An unexpected error occurred with the AI handler: Unexpected AI problem")
        self.worker.success.emit.assert_not_called()
        self.worker.finished.emit.assert_called_once()

    @patch('ThoughtPrint.core.ai_handler.get_ai_response')
    @patch('ThoughtPrint.core.pdf_generator.create_pdf')
    def test_worker_run_unexpected_pdf_error(self, mock_create_pdf, mock_get_ai_response):
        mock_get_ai_response.return_value = "mocked AI response"
        mock_create_pdf.side_effect = Exception("Unexpected PDF problem")

        self.worker.run()

        mock_get_ai_response.assert_called_once_with(self.prompt, self.provider_config, self.system_prompt)
        mock_create_pdf.assert_called_once_with(self.prompt, "mocked AI response")
        self.worker.error.emit.assert_called_once_with("Unexpected PDF Error", "An unexpected error occurred during PDF generation: Unexpected PDF problem")
        self.worker.success.emit.assert_not_called()
        self.worker.finished.emit.assert_called_once()


# We could add tests for MainWindow's interaction with QThread here,
# but that often requires pytest-qt or more involved QApplication event loop management.
# For now, testing the Worker's logic directly provides good coverage of the async part's core.

if __name__ == '__main__':
    unittest.main()