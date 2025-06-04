import json
import requests
from .logger import log_info, log_warning, log_error

# Default timeout for requests
REQUEST_TIMEOUT = 300  # seconds

class AICommunicationError(Exception):
    """Custom exception for AI communication errors."""
    pass

def get_ai_response(user_input, provider_config, system_prompt):
    """
    Sends the user input and system prompt to the specified AI provider
    and returns the AI's response.

    Args:
        user_input (str): The text input from the user.
        provider_config (dict): Configuration for the selected AI provider.
                                Must include 'type', 'base_url', 'model'.
                                'api_key' is needed for 'openai_compatible'.
        system_prompt (str): The system prompt to send to the AI.

    Returns:
        str: The content of the AI's response.

    Raises:
        AICommunicationError: If there's an issue with the API request or response.
        ValueError: If provider_config is invalid.
    """
    if not provider_config or not isinstance(provider_config, dict):
        raise ValueError("Invalid provider_config provided.")

    provider_type = provider_config.get("type")
    base_url = provider_config.get("base_url")
    model = provider_config.get("model")

    if not all([provider_type, base_url, model]):
        raise ValueError("Provider config is missing 'type', 'base_url', or 'model'.")

    headers = {
        "Content-Type": "application/json"
    }
    
    # Get system proxies
    system_proxies = requests.utils.getproxies()
    proxies_to_use = system_proxies
    if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
        proxies_to_use = None
    
    try:
        if provider_type == "openai_compatible":
            api_key = provider_config.get("api_key")
            if not api_key:
                raise ValueError("API key is missing for OpenAI-compatible provider.")
            
            headers["Authorization"] = f"Bearer {api_key}"
            # Ensure base_url ends with /v1 if it's a typical OpenAI-like API
            # Some custom endpoints might not follow this, so be cautious.
            # For now, assume user provides the full path to chat/completions if needed,
            # or we append it if it's a standard base_url.
            # The plan implies `provider_config['base_url'] + '/chat/completions'`
            # Let's ensure base_url doesn't have trailing slash if we append.
            endpoint = base_url.rstrip('/') + "/chat/completions"
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
                # "stream": False, # Not streaming as per requirements
            }
            response = requests.post(endpoint, headers=headers, json=payload, timeout=REQUEST_TIMEOUT, proxies=proxies_to_use)
            response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
            response_data = response.json()
            
            # Extract content from choices
            if response_data.get("choices") and len(response_data["choices"]) > 0:
                message = response_data["choices"][0].get("message")
                if message and message.get("content"):
                    return message["content"].strip()
            raise AICommunicationError("No valid content found in OpenAI-compatible response.")

        elif provider_type == "ollama":
            # Ollama's API endpoint for chat is typically /api/chat
            # For generation (non-chat), it's /api/generate
            # Let's use /api/chat for consistency with system/user roles
            endpoint = base_url.rstrip('/') + "/api/chat"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                "stream": False # Not streaming
            }
            response = requests.post(endpoint, headers=headers, json=payload, timeout=REQUEST_TIMEOUT, proxies=proxies_to_use)
            response.raise_for_status()
            response_data = response.json() # Ollama's non-streaming chat returns a single JSON object

            if response_data and response_data.get("message") and response_data["message"].get("content"):
                return response_data["message"]["content"].strip()
            # Fallback for /api/generate if /api/chat structure isn't matched (older Ollama or different model)
            # elif response_data and response_data.get("response"): # This is for /api/generate
            #    return response_data["response"].strip()
            raise AICommunicationError("No valid content found in Ollama response.")
            
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    except requests.exceptions.RequestException as e:
        raise AICommunicationError(f"Network or request error: {e}")
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # KeyError for missing keys in response, TypeError for unexpected structure
        raise AICommunicationError(f"Error parsing AI response or unexpected response structure: {e}")
    except ValueError as e: # Catch our own ValueErrors from config checks
        raise e


def fetch_available_models(provider_config):
    """
    Fetches available models from the specified AI provider.

    Args:
        provider_config (dict): Configuration for the AI provider.
                                Must include 'type' and 'base_url'.
                                'api_key' is needed for 'openai_compatible'.
    Returns:
        list: A list of model name strings.
    Raises:
        AICommunicationError: If there's an issue with the API request or response.
        ValueError: If provider_config is invalid.
    """
    if not provider_config or not isinstance(provider_config, dict):
        raise ValueError("Invalid provider_config provided for fetching models.")

    provider_type = provider_config.get("type")
    base_url = provider_config.get("base_url")

    if not provider_type or not base_url:
        raise ValueError("Provider config is missing 'type' or 'base_url' for fetching models.")

    headers = {"Accept": "application/json"} # Usually GET requests don't need Content-Type: application/json

    # Get system proxies
    system_proxies = requests.utils.getproxies()
    proxies_to_use = system_proxies
    if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
        proxies_to_use = None

    try:
        if provider_type == "openai_compatible":
            api_key = provider_config.get("api_key")
            # Some model endpoints might not require auth, but usually they do.
            if api_key: # API key might be optional for listing models on some open endpoints
                headers["Authorization"] = f"Bearer {api_key}"

            # Construct endpoint carefully
            stripped_base_url = base_url.rstrip('/')
            if stripped_base_url.endswith('/v1'):
                endpoint = stripped_base_url + "/models"
            else:
                endpoint = stripped_base_url + "/v1/models"
            
            response = requests.get(endpoint, headers=headers, timeout=REQUEST_TIMEOUT, proxies=proxies_to_use)
            response.raise_for_status()
            response_data = response.json()
            
            # Check for typical OpenAI/Groq style response: a dict with a "data" key containing a list of models
            if isinstance(response_data, dict) and response_data.get("data") and isinstance(response_data["data"], list):
                 return sorted([model.get("id") for model in response_data["data"] if model.get("id")])
            # Fallback for simpler list of models if the response_data itself is a list of model objects
            elif isinstance(response_data, list):
                 return sorted([model_dict.get("id") for model_dict in response_data if isinstance(model_dict, dict) and model_dict.get("id")])

            raise AICommunicationError("Unexpected response structure for OpenAI-compatible models list.")

        elif provider_type == "ollama":
            # Ollama's endpoint for listing local models is /api/tags
            endpoint = base_url.rstrip('/') + "/api/tags"
            response = requests.get(endpoint, headers=headers, timeout=REQUEST_TIMEOUT, proxies=proxies_to_use)
            response.raise_for_status()
            response_data = response.json()
            
            # Ollama /api/tags format is {"models": [{"name": "model_name:tag", ...}, ...]}
            if response_data.get("models") and isinstance(response_data["models"], list):
                # Return only the base model name, without the tag, for consistency if needed,
                # or full name including tag. For now, full name.
                return sorted([model.get("name") for model in response_data["models"] if model.get("name")])
            raise AICommunicationError("Unexpected response structure for Ollama models list.")
            
        else:
            raise ValueError(f"Unsupported provider type for fetching models: {provider_type}")

    except requests.exceptions.RequestException as e:
        raise AICommunicationError(f"Network or request error while fetching models: {e}")
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise AICommunicationError(f"Error parsing models list or unexpected response structure: {e}")
    except ValueError as e: # Catch our own ValueErrors from config checks
        raise e

if __name__ == '__main__':
    # Initialize logging for standalone testing
    from .logger import init_logging
    init_logging()
    
    # Example Usage (requires running Ollama or having an OpenAI-compatible endpoint)
    # Note: This test block will likely fail without a running server or valid config.
    
    log_info("Testing AI Handler (requires a running AI service)...")

    # Test Ollama (assuming Ollama is running with llama3 model)
    ollama_config_test = {
        "name": "Test Ollama",
        "type": "ollama",
        "base_url": "http://localhost:11434", # Default Ollama URL
        "model": "llama3" # Make sure this model is pulled in Ollama
    }
    test_system_prompt = "You are a concise assistant. Respond in one sentence."
    test_user_input = "What is the capital of France?"

    log_info(f"\n--- Testing Ollama ({ollama_config_test['model']}) ---")
    try:
        ollama_response = get_ai_response(test_user_input, ollama_config_test, test_system_prompt)
        log_info(f"Ollama Prompt: {test_user_input}")
        log_info(f"Ollama Response: {ollama_response}")
    except AICommunicationError as e:
        log_error(f"Ollama AI Error: {e}")
    except ValueError as e:
        log_error(f"Ollama Config Error: {e}")
    except Exception as e:
        log_error(f"An unexpected error occurred with Ollama: {e}")

    # Test OpenAI-compatible (replace with your actual endpoint, key, and model if testing)
    # WARNING: Using real API keys in code is risky. This is for local testing only.
    # Consider environment variables for real use.
    openai_config_test = {
        "name": "Test OpenAI Compatible",
        "type": "openai_compatible",
        "base_url": "YOUR_OPENAI_COMPATIBLE_BASE_URL", # e.g., https://api.openai.com/v1
        "api_key": "YOUR_API_KEY",
        "model": "YOUR_MODEL_NAME" # e.g., gpt-3.5-turbo
    }

    if openai_config_test["base_url"] != "YOUR_OPENAI_COMPATIBLE_BASE_URL" and openai_config_test["api_key"] != "YOUR_API_KEY":
        log_info(f"\n--- Testing OpenAI-compatible ({openai_config_test['model']}) ---")
        try:
            openai_response = get_ai_response(test_user_input, openai_config_test, test_system_prompt)
            log_info(f"OpenAI Prompt: {test_user_input}")
            log_info(f"OpenAI Response: {openai_response}")
        except AICommunicationError as e:
            log_error(f"OpenAI AI Error: {e}")
        except ValueError as e:
            log_error(f"OpenAI Config Error: {e}")
        except Exception as e:
            log_error(f"An unexpected error occurred with OpenAI: {e}")
    else:
        log_info("\nSkipping OpenAI-compatible test: Please configure base_url, api_key, and model for testing.")

    # Test invalid config
    log_info("\n--- Testing Invalid Config ---")
    try:
        get_ai_response("test", {"type": "unknown"}, "test") # Test get_ai_response
    except ValueError as e:
        log_info(f"Caught expected ValueError for invalid config (get_ai_response): {e}")
    except Exception as e:
        log_error(f"Unexpected error during invalid config test (get_ai_response): {e}")

    log_info("\n--- Testing Model Fetching ---")
    if ollama_config_test["base_url"] == "http://localhost:11434": # Assuming default is testable
        log_info(f"\n--- Fetching Ollama Models ({ollama_config_test['base_url']}) ---")
        try:
            ollama_models = fetch_available_models(ollama_config_test)
            log_info(f"Ollama Models: {ollama_models}")
        except Exception as e:
            log_error(f"Error fetching Ollama models: {e}")
    
    if openai_config_test["base_url"] != "YOUR_OPENAI_COMPATIBLE_BASE_URL":
        log_info(f"\n--- Fetching OpenAI-compatible Models ({openai_config_test['base_url']}) ---")
        try:
            openai_models = fetch_available_models(openai_config_test)
            log_info(f"OpenAI-compatible Models: {openai_models}")
        except Exception as e:
            log_error(f"Error fetching OpenAI-compatible models: {e}")
    else:
        log_info("\nSkipping OpenAI-compatible model fetch test: Please configure base_url for testing.")