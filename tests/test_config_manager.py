import unittest
import os
import json
from pathlib import Path
import shutil

# Adjust the path to import config_manager from the ThoughtPrint.core package
# This assumes 'tests' is a top-level directory alongside 'ThoughtPrint'
# or that the PYTHONPATH is set up correctly.
# For robust testing, it's common to adjust sys.path or use a test runner that handles this.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent)) # Add project root to sys.path

from ThoughtPrint.core import config_manager

class TestConfigManager(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for test settings files
        self.test_dir = Path(__file__).resolve().parent / "test_config_temp"
        self.test_dir.mkdir(exist_ok=True)
        
        # Override the SETTINGS_FILE_PATH in config_manager for testing
        self.original_settings_path = config_manager.SETTINGS_FILE_PATH
        self.test_settings_file = self.test_dir / "test_settings.json"
        config_manager.SETTINGS_FILE_PATH = self.test_settings_file
        
        # Ensure no pre-existing test file interferes
        if self.test_settings_file.exists():
            self.test_settings_file.unlink()

    def tearDown(self):
        # Restore original settings path
        config_manager.SETTINGS_FILE_PATH = self.original_settings_path
        # Clean up the temporary directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_01_load_settings_creates_default_if_not_exists(self):
        self.assertFalse(self.test_settings_file.exists())
        settings = config_manager.load_settings()
        self.assertTrue(self.test_settings_file.exists())
        self.assertEqual(settings, config_manager.DEFAULT_SETTINGS)

    def test_02_save_and_load_settings(self):
        custom_settings = {
            "providers": [{"name": "TestProvider", "type": "test", "base_url": "test_url", "model": "test_model"}],
            "selected_provider_name": "TestProvider",
            "system_prompt": "Test prompt"
        }
        config_manager.save_settings(custom_settings)
        loaded_settings = config_manager.load_settings()
        self.assertEqual(loaded_settings, custom_settings)

    def test_03_load_settings_handles_malformed_json(self):
        # Create a malformed JSON file
        with open(self.test_settings_file, 'w', encoding='utf-8') as f:
            f.write("{'invalid_json': True,") # Malformed
        
        settings = config_manager.load_settings()
        # Should return default settings and overwrite the malformed file with defaults
        self.assertEqual(settings, config_manager.DEFAULT_SETTINGS)
        
        # Verify the file was corrected
        with open(self.test_settings_file, 'r', encoding='utf-8') as f:
            corrected_data = json.load(f)
        self.assertEqual(corrected_data, config_manager.DEFAULT_SETTINGS)

    def test_04_load_settings_handles_incomplete_json_structure(self):
        incomplete_settings = {"providers": [{"name": "OnlyProvider"}]} # Missing other keys
        with open(self.test_settings_file, 'w', encoding='utf-8') as f:
            json.dump(incomplete_settings, f)
        
        settings = config_manager.load_settings()
        # Should return default settings and overwrite the incomplete file
        self.assertEqual(settings, config_manager.DEFAULT_SETTINGS)
        with open(self.test_settings_file, 'r', encoding='utf-8') as f:
            corrected_data = json.load(f)
        self.assertEqual(corrected_data, config_manager.DEFAULT_SETTINGS)


    def test_05_get_selected_provider(self):
        config_manager.save_settings(config_manager.DEFAULT_SETTINGS)
        provider = config_manager.get_selected_provider()
        self.assertIsNotNone(provider)
        self.assertEqual(provider["name"], config_manager.DEFAULT_SETTINGS["selected_provider_name"])

    def test_06_get_system_prompt(self):
        config_manager.save_settings(config_manager.DEFAULT_SETTINGS)
        prompt = config_manager.get_system_prompt()
        self.assertEqual(prompt, config_manager.DEFAULT_SETTINGS["system_prompt"])

    def test_07_add_provider(self):
        config_manager.load_settings() # Ensure default settings are loaded/created
        new_provider = {"name": "NewProvider", "type": "new_type", "base_url": "new_url", "model": "new_model"}
        self.assertTrue(config_manager.add_provider(new_provider))
        settings = config_manager.load_settings()
        self.assertIn(new_provider, settings["providers"])
        # Test adding duplicate
        self.assertFalse(config_manager.add_provider(new_provider))


    def test_08_update_provider(self):
        config_manager.save_settings(config_manager.DEFAULT_SETTINGS) # Start with defaults
        provider_name_to_update = config_manager.DEFAULT_SETTINGS["providers"][0]["name"]
        updated_details = {
            "name": provider_name_to_update, # Name must match for update
            "type": "updated_ollama",
            "base_url": "http://newhost:12345",
            "api_key": None,
            "model": "llama_updated"
        }
        self.assertTrue(config_manager.update_provider(provider_name_to_update, updated_details))
        settings = config_manager.load_settings()
        # Find the updated provider
        found_provider = next((p for p in settings["providers"] if p["name"] == provider_name_to_update), None)
        self.assertIsNotNone(found_provider)
        self.assertEqual(found_provider["model"], "llama_updated")
        self.assertEqual(found_provider["base_url"], "http://newhost:12345")
        
        # Test updating non-existent provider
        self.assertFalse(config_manager.update_provider("NonExistent", updated_details))

    def test_09_remove_provider(self):
        # Setup with two providers
        settings_data = {
            "providers": [
                {"name": "Provider1", "type": "ollama", "base_url": "url1", "model": "model1"},
                {"name": "Provider2", "type": "openai", "base_url": "url2", "api_key": "key2", "model": "model2"}
            ],
            "selected_provider_name": "Provider1",
            "system_prompt": "Test"
        }
        config_manager.save_settings(settings_data)
        
        self.assertTrue(config_manager.remove_provider("Provider1"))
        current_settings = config_manager.load_settings()
        self.assertEqual(len(current_settings["providers"]), 1)
        self.assertEqual(current_settings["providers"][0]["name"], "Provider2")
        self.assertEqual(current_settings["selected_provider_name"], "Provider2") # Should select remaining

        # Test removing non-existent
        self.assertFalse(config_manager.remove_provider("NonExistent"))

        # Test removing last provider
        self.assertTrue(config_manager.remove_provider("Provider2"))
        current_settings = config_manager.load_settings()
        self.assertEqual(len(current_settings["providers"]), 0)
        self.assertIsNone(current_settings["selected_provider_name"])


    def test_10_set_selected_provider(self):
        config_manager.save_settings(config_manager.DEFAULT_SETTINGS)
        # Add another provider to select from
        new_prov = {"name": "Selectable", "type": "test", "base_url": "select_url", "model": "select_model"}
        config_manager.add_provider(new_prov)
        
        self.assertTrue(config_manager.set_selected_provider("Selectable"))
        settings = config_manager.load_settings()
        self.assertEqual(settings["selected_provider_name"], "Selectable")

        # Test selecting non-existent
        self.assertFalse(config_manager.set_selected_provider("NonExistentProvider"))

    def test_11_update_system_prompt(self):
        config_manager.save_settings(config_manager.DEFAULT_SETTINGS)
        new_prompt_text = "This is an updated system prompt."
        config_manager.update_system_prompt(new_prompt_text)
        settings = config_manager.load_settings()
        self.assertEqual(settings["system_prompt"], new_prompt_text)

if __name__ == '__main__':
    unittest.main()