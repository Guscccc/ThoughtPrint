import unittest
from unittest.mock import patch, MagicMock
import json

# Add project root to sys.path for robust imports
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ThoughtPrint.core import ai_handler
from ThoughtPrint.core.ai_handler import AICommunicationError

class TestAiHandler(unittest.TestCase):

    def setUp(self):
        self.test_user_input = "Hello, AI!"
        self.test_system_prompt = "You are a test assistant."
        self.ollama_config = {
            "type": "ollama",
            "base_url": "http://localhost:11434",
            "model": "test_ollama_model"
        }
        self.openai_config = {
            "type": "openai_compatible",
            "base_url": "https://api.example.com/v1",
            "api_key": "test_api_key",
            "model": "test_openai_model"
        }
        self.mock_proxies = {"http": "http://mockproxy:8080", "https": "https://mockproxy:8080"}

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    @patch('ThoughtPrint.core.ai_handler.requests.post')
    def test_get_ai_response_ollama_success(self, mock_post, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Ollama's /api/chat non-streaming response structure
        mock_response.json.return_value = {
            "model": "test_ollama_model",
            "created_at": "2023-10-26T10:00:00Z",
            "message": {
                "role": "assistant",
                "content": "Ollama says hello!"
            },
            "done": True
        }
        mock_post.return_value = mock_response

        response = ai_handler.get_ai_response(self.test_user_input, self.ollama_config, self.test_system_prompt)
        self.assertEqual(response, "Ollama says hello!")
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/chat",
            headers={"Content-Type": "application/json"},
            json={
                "model": "test_ollama_model",
                "messages": [
                    {"role": "system", "content": self.test_system_prompt},
                    {"role": "user", "content": self.test_user_input}
                ],
                "stream": False
            },
            timeout=ai_handler.REQUEST_TIMEOUT,
            proxies=None # Ollama is localhost, so proxies should be None
        )

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    @patch('ThoughtPrint.core.ai_handler.requests.post')
    def test_get_ai_response_openai_success(self, mock_post, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "test_openai_model",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "OpenAI compatible says hello!"
                },
                "finish_reason": "stop"
            }]
        }
        mock_post.return_value = mock_response

        response = ai_handler.get_ai_response(self.test_user_input, self.openai_config, self.test_system_prompt)
        self.assertEqual(response, "OpenAI compatible says hello!")
        mock_post.assert_called_once_with(
            "https://api.example.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer test_api_key"
            },
            json={
                "model": "test_openai_model",
                "messages": [
                    {"role": "system", "content": self.test_system_prompt},
                    {"role": "user", "content": self.test_user_input}
                ]
            },
            timeout=ai_handler.REQUEST_TIMEOUT,
            proxies=self.mock_proxies
        )

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    @patch('ThoughtPrint.core.ai_handler.requests.post')
    def test_get_ai_response_network_error(self, mock_post, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        mock_post.side_effect = ai_handler.requests.exceptions.RequestException("Network error")
        with self.assertRaisesRegex(AICommunicationError, "Network or request error: Network error"):
            ai_handler.get_ai_response(self.test_user_input, self.ollama_config, self.test_system_prompt)

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    @patch('ThoughtPrint.core.ai_handler.requests.post')
    def test_get_ai_response_http_error(self, mock_post, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = ai_handler.requests.exceptions.HTTPError("Server error")
        mock_post.return_value = mock_response
        with self.assertRaisesRegex(AICommunicationError, "Network or request error: Server error"):
            ai_handler.get_ai_response(self.test_user_input, self.ollama_config, self.test_system_prompt)

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    @patch('ThoughtPrint.core.ai_handler.requests.post')
    def test_get_ai_response_openai_missing_content(self, mock_post, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"role": "assistant"}}]} # Missing content
        mock_post.return_value = mock_response
        with self.assertRaisesRegex(AICommunicationError, "No valid content found in OpenAI-compatible response."):
            ai_handler.get_ai_response(self.test_user_input, self.openai_config, self.test_system_prompt)

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    @patch('ThoughtPrint.core.ai_handler.requests.post')
    def test_get_ai_response_ollama_missing_content(self, mock_post, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"role": "assistant"}} # Missing content
        mock_post.return_value = mock_response
        with self.assertRaisesRegex(AICommunicationError, "No valid content found in Ollama response."):
            ai_handler.get_ai_response(self.test_user_input, self.ollama_config, self.test_system_prompt)

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    def test_invalid_provider_type(self, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        invalid_config = {"type": "unknown_provider", "base_url": "url", "model": "model"}
        with self.assertRaisesRegex(ValueError, "Unsupported provider type: unknown_provider"):
            ai_handler.get_ai_response(self.test_user_input, invalid_config, self.test_system_prompt)

    def test_missing_config_values(self):
        with self.assertRaisesRegex(ValueError, "Provider config is missing 'type', 'base_url', or 'model'."):
            ai_handler.get_ai_response(self.test_user_input, {"type": "ollama"}, self.test_system_prompt)
        
        openai_missing_key = self.openai_config.copy()
        del openai_missing_key["api_key"]
        with self.assertRaisesRegex(ValueError, "API key is missing for OpenAI-compatible provider."):
            ai_handler.get_ai_response(self.test_user_input, openai_missing_key, self.test_system_prompt)
            
    def test_invalid_provider_config_type(self):
        with self.assertRaisesRegex(ValueError, "Invalid provider_config provided."):
            ai_handler.get_ai_response(self.test_user_input, None, self.test_system_prompt)
        with self.assertRaisesRegex(ValueError, "Invalid provider_config provided."):
            ai_handler.get_ai_response(self.test_user_input, "not_a_dict", self.test_system_prompt)

    # Tests for fetch_available_models
    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    @patch('ThoughtPrint.core.ai_handler.requests.get')
    def test_fetch_models_ollama_success(self, mock_get, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:latest", "modified_at": "...", "size": 0},
                {"name": "mistral:7b", "modified_at": "...", "size": 0}
            ]
        }
        mock_get.return_value = mock_response
        models = ai_handler.fetch_available_models(self.ollama_config)
        self.assertEqual(models, sorted(["llama3:latest", "mistral:7b"]))
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags",
            headers={"Accept": "application/json"},
            timeout=ai_handler.REQUEST_TIMEOUT,
            proxies=None # Ollama is localhost, so proxies should be None
        )

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    @patch('ThoughtPrint.core.ai_handler.requests.get')
    def test_fetch_models_openai_success(self, mock_get, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4", "object": "model", "owned_by": "..."},
                {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "..."}
            ],
            "object": "list"
        }
        mock_get.return_value = mock_response
        models = ai_handler.fetch_available_models(self.openai_config)
        self.assertEqual(models, sorted(["gpt-3.5-turbo", "gpt-4"]))
        mock_get.assert_called_once_with(
            "https://api.example.com/v1/models",
            headers={"Accept": "application/json", "Authorization": "Bearer test_api_key"},
            timeout=ai_handler.REQUEST_TIMEOUT,
            proxies=self.mock_proxies
        )

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    @patch('ThoughtPrint.core.ai_handler.requests.get')
    def test_fetch_models_openai_simple_list_success(self, mock_get, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        # Test for OpenAI compatible servers that return a simple list
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
                {"id": "custom-model-1", "object": "model"},
                {"id": "custom-model-2", "object": "model"}
            ]
        mock_get.return_value = mock_response
        models = ai_handler.fetch_available_models(self.openai_config)
        self.assertEqual(models, sorted(["custom-model-1", "custom-model-2"]))
        # Construct expected endpoint based on logic in ai_handler
        base_url = self.openai_config["base_url"].rstrip('/')
        expected_endpoint = base_url + "/models" if base_url.endswith('/v1') else base_url + "/v1/models"
        mock_get.assert_called_once_with(
            expected_endpoint,
            headers={"Accept": "application/json", "Authorization": "Bearer test_api_key"},
            timeout=ai_handler.REQUEST_TIMEOUT,
            proxies=self.mock_proxies
        )

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    @patch('ThoughtPrint.core.ai_handler.requests.get')
    def test_fetch_models_groq_style_success(self, mock_get, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        # Test for Groq style model list
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "list",
            "data": [
                {"id": "llama3-8b-8192", "object": "model", "owned_by": "groq"},
                {"id": "mixtral-8x7b-32768", "object": "model", "owned_by": "groq"}
            ]
        }
        mock_get.return_value = mock_response
        models = ai_handler.fetch_available_models(self.openai_config)
        self.assertEqual(models, sorted(["llama3-8b-8192", "mixtral-8x7b-32768"]))
        base_url = self.openai_config["base_url"].rstrip('/')
        expected_endpoint = base_url + "/models" if base_url.endswith('/v1') else base_url + "/v1/models"
        mock_get.assert_called_once_with(
            expected_endpoint,
            headers={"Accept": "application/json", "Authorization": "Bearer test_api_key"},
            timeout=ai_handler.REQUEST_TIMEOUT,
            proxies=self.mock_proxies
        )

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    @patch('ThoughtPrint.core.ai_handler.requests.get')
    def test_fetch_models_network_error(self, mock_get, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        mock_get.side_effect = ai_handler.requests.exceptions.RequestException("Fetch network error")
        with self.assertRaisesRegex(AICommunicationError, "Network or request error while fetching models: Fetch network error"):
            ai_handler.fetch_available_models(self.ollama_config)

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    def test_fetch_models_invalid_provider_type(self, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        invalid_config = {"type": "unknown_provider_fetch", "base_url": "url"}
        with self.assertRaisesRegex(ValueError, "Unsupported provider type for fetching models: unknown_provider_fetch"):
            ai_handler.fetch_available_models(invalid_config)

    @patch('ThoughtPrint.core.ai_handler.requests.utils.getproxies')
    def test_fetch_models_missing_config(self, mock_getproxies):
        mock_getproxies.return_value = self.mock_proxies
        with self.assertRaisesRegex(ValueError, "Provider config is missing 'type' or 'base_url' for fetching models."):
            ai_handler.fetch_available_models({"type": "ollama"}) # Missing base_url
        with self.assertRaisesRegex(ValueError, "Invalid provider_config provided for fetching models."):
            ai_handler.fetch_available_models(None)


if __name__ == '__main__':
    unittest.main()