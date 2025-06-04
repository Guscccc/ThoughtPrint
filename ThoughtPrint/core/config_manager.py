import json
import os
from pathlib import Path
from .logger import log_info, log_warning, log_error

SETTINGS_FILE_NAME = "settings.json"
# Determine settings file path in the application's directory or a user-specific config location.
# For simplicity, let's place it next to the script or in a dedicated config folder within the app's structure.
# Assuming the script is run from the root of ThoughtPrint or its parent.
# More robust would be to use appdirs or similar for platform-agnostic config paths.
# For now, let's assume settings.json will be in the same directory as main.py's parent if run as a module,
# or in a 'config' subfolder. Let's aim for a 'config' subfolder within the app's deployed location.
# However, the plan states "settings.json             # Stores user settings (created on first run or if not exists)"
# at the root of ThoughtPrint. Let's stick to that for now.
SETTINGS_FILE_PATH = Path(__file__).resolve().parent.parent / SETTINGS_FILE_NAME # Puts settings.json in ThoughtPrint/

DEFAULT_SETTINGS = {
    "providers": [
        {
            "name": "Ollama Local Llama3",
            "type": "ollama",
            "base_url": "http://localhost:11434",
            "api_key": None,
            "model": "llama3"
        }
    ],
    "selected_provider_name": "Ollama Local Llama3",
    "system_prompt": "You are a helpful assistant. Please format your response in Markdown."
}

def load_settings():
    """Loads settings from settings.json. If not found, creates it with defaults."""
    if not SETTINGS_FILE_PATH.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    try:
        with open(SETTINGS_FILE_PATH, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            # Basic validation or migration could be added here
            if "providers" not in settings or "selected_provider_name" not in settings or "system_prompt" not in settings:
                # If file exists but is malformed or old, overwrite with default (or attempt migration)
                save_settings(DEFAULT_SETTINGS)
                return DEFAULT_SETTINGS
            return settings
    except (json.JSONDecodeError, IOError) as e:
        log_error(f"Error loading settings file '{SETTINGS_FILE_PATH}': {e}. Using default settings.")
        # Attempt to save defaults if loading failed catastrophically
        try:
            save_settings(DEFAULT_SETTINGS)
        except IOError as save_e:
            log_error(f"Could not even save default settings: {save_e}")
        return DEFAULT_SETTINGS

def save_settings(settings_data):
    """Saves the given settings data to settings.json."""
    try:
        # Ensure the directory exists (though Path.parent / file should handle this if parent exists)
        SETTINGS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        log_error(f"Error saving settings to '{SETTINGS_FILE_PATH}': {e}")
        raise # Re-raise to make calling code aware of failure

def get_selected_provider():
    """Returns the configuration for the currently selected AI provider."""
    settings = load_settings()
    selected_name = settings.get("selected_provider_name")
    if not selected_name:
        return None
    for provider in settings.get("providers", []):
        if provider.get("name") == selected_name:
            return provider
    return None # Or perhaps the first provider if selected is invalid

def get_system_prompt():
    """Returns the current system prompt."""
    settings = load_settings()
    return settings.get("system_prompt", DEFAULT_SETTINGS["system_prompt"])

def add_provider(provider_details):
    """Adds a new provider to the list and saves settings."""
    settings = load_settings()
    # Prevent duplicates by name
    if any(p["name"] == provider_details["name"] for p in settings["providers"]):
        log_warning(f"Provider with name '{provider_details['name']}' already exists. Use update_provider instead.")
        return False # Indicate failure or handle as update
    settings["providers"].append(provider_details)
    save_settings(settings)
    return True

def update_provider(provider_name, updated_details):
    """Updates an existing provider's details."""
    settings = load_settings()
    provider_found = False
    for i, provider in enumerate(settings["providers"]):
        if provider["name"] == provider_name:
            settings["providers"][i] = updated_details # Assumes updated_details includes the name
            provider_found = True
            break
    if not provider_found:
        log_warning(f"Provider '{provider_name}' not found for update.")
        return False
    save_settings(settings)
    return True

def remove_provider(provider_name):
    """Removes a provider by name."""
    settings = load_settings()
    initial_len = len(settings["providers"])
    settings["providers"] = [p for p in settings["providers"] if p["name"] != provider_name]
    if len(settings["providers"]) == initial_len:
        log_warning(f"Provider '{provider_name}' not found for removal.")
        return False
    
    # If the removed provider was the selected one, select another or none
    if settings.get("selected_provider_name") == provider_name:
        if settings["providers"]:
            settings["selected_provider_name"] = settings["providers"][0]["name"]
        else:
            settings["selected_provider_name"] = None # Or a default placeholder
    
    save_settings(settings)
    return True

def set_selected_provider(provider_name):
    """Sets the currently selected provider by name."""
    settings = load_settings()
    if not any(p["name"] == provider_name for p in settings["providers"]):
        log_warning(f"Cannot select provider '{provider_name}': not found.")
        return False
    settings["selected_provider_name"] = provider_name
    save_settings(settings)
    return True

def update_system_prompt(prompt_text):
    """Updates the system prompt and saves settings."""
    settings = load_settings()
    settings["system_prompt"] = prompt_text
    save_settings(settings)

if __name__ == '__main__':
    # Initialize logging for standalone testing
    from .logger import init_logging
    init_logging()
    
    # Example usage and testing
    log_info(f"Current settings: {load_settings()}")
    
    selected_provider = get_selected_provider()
    if selected_provider:
        log_info(f"Selected provider: {selected_provider['name']} ({selected_provider['model']})")
    else:
        log_info("No provider selected or found.")
        
    log_info(f"System prompt: '{get_system_prompt()}'")

    # Test adding a new provider
    new_provider_details = {
        "name": "My OpenAI Test",
        "type": "openai_compatible",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-testkey123",
        "model": "gpt-4"
    }
    if add_provider(new_provider_details):
        log_info(f"Added provider: {new_provider_details['name']}")
        set_selected_provider(new_provider_details['name'])
        log_info(f"New selected provider: {get_selected_provider()['name']}")

    # Test updating system prompt
    new_prompt = "You are an expert Python programmer. Respond in Markdown."
    update_system_prompt(new_prompt)
    log_info(f"Updated system prompt: '{get_system_prompt()}'")

    # Test removing a provider
    # remove_provider("Ollama Local Llama3")
    # log_info(f"Settings after removing Ollama Local Llama3: {load_settings()}")
    # log_info(f"Selected provider after removal: {get_selected_provider()}")

    # Clean up test settings file if it was created by this test run
    # if SETTINGS_FILE_PATH.exists() and load_settings() != DEFAULT_SETTINGS:
    #     log_info("Reverting to default settings for next run...")
    #     save_settings(DEFAULT_SETTINGS)