import unittest
from unittest.mock import patch, MagicMock

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from ThoughtPrint.ui.settings_dialog import ModelFetcher # Worker class to test
from ThoughtPrint.core import ai_handler # To mock its functions
from ThoughtPrint.core.ai_handler import AICommunicationError

class TestModelFetcher(unittest.TestCase):

    def setUp(self):
        self.ollama_provider_config = {
            "type": "ollama",
            "base_url": "http://localhost:11434",
            "api_key": None # Ollama doesn't use API key for model listing
        }
        self.openai_provider_config = {
            "type": "openai_compatible",
            "base_url": "https://api.example.com/v1",
            "api_key": "test_key"
        }
        self.fetcher = None # To be instantiated in each test with specific config

        # Mock signals for the fetcher instance
        self.mock_models_fetched_signal = MagicMock()
        self.mock_error_occurred_signal = MagicMock()
        self.mock_finished_signal = MagicMock()

    def _setup_fetcher_and_signals(self, config):
        self.fetcher = ModelFetcher(config)
        self.fetcher.models_fetched = self.mock_models_fetched_signal
        self.fetcher.error_occurred = self.mock_error_occurred_signal
        self.fetcher.finished = self.mock_finished_signal

    @patch('ThoughtPrint.core.ai_handler.fetch_available_models')
    def test_model_fetcher_ollama_success(self, mock_fetch_available_models):
        self._setup_fetcher_and_signals(self.ollama_provider_config)
        expected_models = ["ollama_model1", "ollama_model2"]
        mock_fetch_available_models.return_value = expected_models

        self.fetcher.run()

        mock_fetch_available_models.assert_called_once_with(self.ollama_provider_config)
        self.mock_models_fetched_signal.emit.assert_called_once_with(expected_models)
        self.mock_error_occurred_signal.emit.assert_not_called()
        self.mock_finished_signal.emit.assert_called_once()

    @patch('ThoughtPrint.core.ai_handler.fetch_available_models')
    def test_model_fetcher_openai_success(self, mock_fetch_available_models):
        self._setup_fetcher_and_signals(self.openai_provider_config)
        expected_models = ["openai_model1", "openai_model2"]
        mock_fetch_available_models.return_value = expected_models

        self.fetcher.run()

        mock_fetch_available_models.assert_called_once_with(self.openai_provider_config)
        self.mock_models_fetched_signal.emit.assert_called_once_with(expected_models)
        self.mock_error_occurred_signal.emit.assert_not_called()
        self.mock_finished_signal.emit.assert_called_once()

    @patch('ThoughtPrint.core.ai_handler.fetch_available_models')
    def test_model_fetcher_ai_communication_error(self, mock_fetch_available_models):
        self._setup_fetcher_and_signals(self.ollama_provider_config)
        error_message = "Network down"
        mock_fetch_available_models.side_effect = AICommunicationError(error_message)

        self.fetcher.run()

        mock_fetch_available_models.assert_called_once_with(self.ollama_provider_config)
        self.mock_error_occurred_signal.emit.assert_called_once_with(f"Could not fetch models: {error_message}")
        self.mock_models_fetched_signal.emit.assert_not_called()
        self.mock_finished_signal.emit.assert_called_once()

    @patch('ThoughtPrint.core.ai_handler.fetch_available_models')
    def test_model_fetcher_value_error(self, mock_fetch_available_models):
        self._setup_fetcher_and_signals(self.ollama_provider_config) # Config is valid here
        error_message = "Invalid config in underlying call"
        mock_fetch_available_models.side_effect = ValueError(error_message)

        self.fetcher.run()
        
        mock_fetch_available_models.assert_called_once_with(self.ollama_provider_config)
        self.mock_error_occurred_signal.emit.assert_called_once_with(f"Configuration error for model fetching: {error_message}")
        self.mock_models_fetched_signal.emit.assert_not_called()
        self.mock_finished_signal.emit.assert_called_once()

    def test_model_fetcher_insufficient_config_type_missing(self):
        insufficient_config = {"base_url": "http://someurl"} # Missing type
        self._setup_fetcher_and_signals(insufficient_config)
        
        with patch('ThoughtPrint.core.ai_handler.fetch_available_models') as mock_fetch_call:
            self.fetcher.run()
            mock_fetch_call.assert_not_called() # Should not attempt to call ai_handler.fetch
            self.mock_models_fetched_signal.emit.assert_called_once_with([]) # Emits empty list
            self.mock_error_occurred_signal.emit.assert_not_called()
            self.mock_finished_signal.emit.assert_called_once()

    def test_model_fetcher_insufficient_config_base_url_missing(self):
        insufficient_config = {"type": "ollama"} # Missing base_url
        self._setup_fetcher_and_signals(insufficient_config)

        with patch('ThoughtPrint.core.ai_handler.fetch_available_models') as mock_fetch_call:
            self.fetcher.run()
            mock_fetch_call.assert_not_called()
            self.mock_models_fetched_signal.emit.assert_called_once_with([])
            self.mock_error_occurred_signal.emit.assert_not_called()
            self.mock_finished_signal.emit.assert_called_once()
            
    def test_model_fetcher_empty_config(self):
        self._setup_fetcher_and_signals({}) # Empty config
        with patch('ThoughtPrint.core.ai_handler.fetch_available_models') as mock_fetch_call:
            self.fetcher.run()
            mock_fetch_call.assert_not_called()
            self.mock_models_fetched_signal.emit.assert_called_once_with([])
            self.mock_error_occurred_signal.emit.assert_not_called()
            self.mock_finished_signal.emit.assert_called_once()

    @patch('ThoughtPrint.core.ai_handler.fetch_available_models')
    def test_model_fetcher_unexpected_error(self, mock_fetch_available_models):
        self._setup_fetcher_and_signals(self.ollama_provider_config)
        error_message = "Something totally unexpected"
        mock_fetch_available_models.side_effect = Exception(error_message)

        self.fetcher.run()

        mock_fetch_available_models.assert_called_once_with(self.ollama_provider_config)
        self.mock_error_occurred_signal.emit.assert_called_once_with(f"An unexpected error occurred while fetching models: {error_message}")
        self.mock_models_fetched_signal.emit.assert_not_called()
        self.mock_finished_signal.emit.assert_called_once()

if __name__ == '__main__':
    unittest.main()