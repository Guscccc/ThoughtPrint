import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QMessageBox,
    QTextEdit, QListWidget, QListWidgetItem, QStackedWidget, QProgressDialog
)
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal

# Ensure these are available at the module level for ModelFetcher
try:
    from ..core import config_manager
    from ..core import ai_handler as core_ai_handler
    from ..core.ai_handler import AICommunicationError as CoreAICommunicationError
    from ..core.logger import log_info, log_warning, log_error
except ImportError:
    # Fallback for direct execution or different project structure
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..')) # Add project root
    from core import config_manager
    from core import ai_handler as core_ai_handler
    from core.ai_handler import AICommunicationError as CoreAICommunicationError
    from core.logger import log_info, log_warning, log_error


class ModelFetcher(QObject):
    """Worker to fetch models in a separate thread."""
    models_fetched = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, provider_config):
        super().__init__()
        self.provider_config = provider_config

    def run(self):
        try:
            if not self.provider_config or \
               not self.provider_config.get("type") or \
               not self.provider_config.get("base_url"):
                log_warning("ModelFetcher: Insufficient provider config to fetch models.")
                self.models_fetched.emit([])
            else:
                log_info(f"ModelFetcher: Fetching models for {self.provider_config.get('type')} at {self.provider_config.get('base_url')}")
                models = core_ai_handler.fetch_available_models(self.provider_config)
                self.models_fetched.emit(models)
        except CoreAICommunicationError as e:
            log_error(f"ModelFetcher: AICommunicationError - {e}")
            self.error_occurred.emit(f"Could not fetch models: {e}")
        except ValueError as e:
            log_error(f"ModelFetcher: ValueError - {e}")
            self.error_occurred.emit(f"Configuration error for model fetching: {e}")
        except Exception as e:
            log_error(f"ModelFetcher: Unexpected error - {e}")
            self.error_occurred.emit(f"An unexpected error occurred while fetching models: {e}")
        finally:
            self.finished.emit()


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_fetch_thread = None
        self.model_fetch_worker = None
        # self.current_provider_for_models = None # Not strictly needed with new logic
        self.setWindowTitle("AI Provider Settings")
        self.setMinimumWidth(600)

        self.settings = config_manager.load_settings()

        main_layout = QVBoxLayout(self)

        provider_management_layout = QHBoxLayout()
        self.provider_list_widget = QListWidget()
        self.provider_list_widget.itemSelectionChanged.connect(self.on_provider_selected)
        provider_management_layout.addWidget(self.provider_list_widget, 1)

        provider_buttons_layout = QVBoxLayout()
        self.add_provider_button = QPushButton("Add New")
        self.add_provider_button.clicked.connect(self.add_new_provider_ui)
        self.remove_provider_button = QPushButton("Remove Selected")
        self.remove_provider_button.clicked.connect(self.remove_selected_provider_ui)
        provider_buttons_layout.addWidget(self.add_provider_button)
        provider_buttons_layout.addWidget(self.remove_provider_button)
        provider_buttons_layout.addStretch()
        provider_management_layout.addLayout(provider_buttons_layout)
        main_layout.addLayout(provider_management_layout)

        self.provider_config_stack = QStackedWidget()
        self.edit_provider_widget = self._create_provider_form_widget() 
        self.add_provider_widget = self._create_provider_form_widget(is_add_mode=True)
        self.provider_config_stack.addWidget(self.edit_provider_widget) 
        self.provider_config_stack.addWidget(self.add_provider_widget) 
        main_layout.addWidget(self.provider_config_stack)
        
        main_layout.addWidget(QLabel("System Prompt:"))
        self.system_prompt_text_edit = QTextEdit()
        self.system_prompt_text_edit.setPlaceholderText("Enter the system prompt for the AI...")
        main_layout.addWidget(self.system_prompt_text_edit)

        dialog_buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Save All Settings")
        self.save_button.clicked.connect(self.save_all_settings)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        dialog_buttons_layout.addStretch()
        dialog_buttons_layout.addWidget(self.save_button)
        dialog_buttons_layout.addWidget(self.cancel_button)
        main_layout.addLayout(dialog_buttons_layout)

        self.setLayout(main_layout)
        self.populate_provider_list()
        self.load_system_prompt()
        
        if self.provider_list_widget.count() > 0:
            self.provider_list_widget.setCurrentRow(0)
            self.provider_config_stack.setCurrentIndex(0)
        else:
            self.provider_config_stack.setCurrentIndex(1)

    def _create_provider_form_widget(self, is_add_mode=False):
        widget = QDialog() 
        form_layout = QFormLayout(widget)
        form_layout.setContentsMargins(0,0,0,0)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g., My OpenAI Service, Local Ollama")
        
        type_combo = QComboBox()
        type_combo.addItems(["openai_compatible", "ollama"])
        
        base_url_edit = QLineEdit()
        base_url_edit.setPlaceholderText("e.g., https://api.openai.com/v1 or http://localhost:11434")
        
        api_key_edit = QLineEdit()
        api_key_edit.setPlaceholderText("Enter API key (if OpenAI compatible)")
        api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        model_combo = QComboBox()
        model_combo.setEditable(True) 
        model_combo.setPlaceholderText("Click 'Refresh Models' or type manually")
        
        refresh_models_button = QPushButton("Refresh Models")

        form_layout.addRow("Provider Name:", name_edit)
        form_layout.addRow("Type:", type_combo)
        form_layout.addRow("Base URL:", base_url_edit)
        form_layout.addRow("API Key:", api_key_edit)
        
        model_layout = QHBoxLayout()
        model_layout.addWidget(model_combo, 1)
        model_layout.addWidget(refresh_models_button)
        form_layout.addRow("Model:", model_layout)

        widget.name_edit = name_edit
        widget.type_combo = type_combo
        widget.base_url_edit = base_url_edit
        widget.api_key_edit = api_key_edit
        widget.model_combo = model_combo
        widget.refresh_models_button = refresh_models_button
        
        type_combo.currentTextChanged.connect(
            lambda text, form_widget=widget: self._on_provider_detail_changed(form_widget)
        )
        base_url_edit.editingFinished.connect(
            lambda form_widget=widget: self._on_provider_detail_changed(form_widget)
        )
        api_key_edit.editingFinished.connect(
             lambda form_widget=widget: self._on_provider_detail_changed(form_widget)
        )
        refresh_models_button.clicked.connect(
            lambda checked=False, form_widget=widget: self.fetch_models_for_form(form_widget)
        )
        
        api_key_edit.setEnabled(type_combo.currentText() == "openai_compatible")

        if is_add_mode:
            add_button = QPushButton("Add This Provider")
            add_button.clicked.connect(self.save_added_provider_details)
            form_layout.addRow(add_button)
            widget.save_button = add_button
        
        widget.setLayout(form_layout)
        return widget

    def populate_provider_list(self):
        self.provider_list_widget.clear()
        selected_provider_name = self.settings.get("selected_provider_name")
        current_row_to_select = -1
        for index, provider in enumerate(self.settings.get("providers", [])):
            item = QListWidgetItem(provider["name"])
            item.setData(Qt.ItemDataRole.UserRole, provider)
            self.provider_list_widget.addItem(item)
            if provider["name"] == selected_provider_name:
                current_row_to_select = index
        
        if current_row_to_select != -1:
            self.provider_list_widget.setCurrentRow(current_row_to_select)
        elif self.provider_list_widget.count() > 0:
            self.provider_list_widget.setCurrentRow(0)

    def on_provider_selected(self):
        selected_items = self.provider_list_widget.selectedItems()
        if not selected_items:
            self._clear_form(self.edit_provider_widget)
            self.provider_config_stack.setCurrentIndex(1)
            return

        self.provider_config_stack.setCurrentIndex(0)
        provider_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        form = self.edit_provider_widget

        form.name_edit.setText(provider_data.get("name", ""))
        form.type_combo.setCurrentText(provider_data.get("type", "ollama")) # This will trigger _on_provider_detail_changed
        form.base_url_edit.setText(provider_data.get("base_url", ""))
        form.api_key_edit.setText(provider_data.get("api_key", ""))
        
        form.model_combo.clear()
        current_model_name = provider_data.get("model", "")
        if current_model_name:
            form.model_combo.addItem(current_model_name)
            form.model_combo.setCurrentText(current_model_name)
        else:
            form.model_combo.setPlaceholderText("Click 'Refresh Models' or type manually")
        
        form.api_key_edit.setEnabled(form.type_combo.currentText() == "openai_compatible")
        
        # Clear any previous fetch state attributes from the form widget
        if hasattr(form, '_last_fetch_config'): # Using form directly as it is the widget
            delattr(form, '_last_fetch_config')
        if hasattr(form, '_last_successful_fetch_config'):
            delattr(form, '_last_successful_fetch_config')


    def _on_provider_detail_changed(self, form_widget):
        provider_type = form_widget.type_combo.currentText()
        form_widget.api_key_edit.setEnabled(provider_type == "openai_compatible")

        if provider_type == "ollama":
            current_base_url = form_widget.base_url_edit.text().strip()
            default_ollama_url = "http://localhost:11434"
            if not current_base_url or form_widget.property("just_auto_filled_ollama_url") == True: # Check if it was just auto-filled
                 # If user changes type to ollama, and field is empty, or was just auto-filled by a previous type change, set it.
                 # This avoids overwriting a user-entered custom ollama URL unless they switch type away and back.
                if not current_base_url: # If empty, always fill
                    form_widget.base_url_edit.setText(default_ollama_url)
                    form_widget.setProperty("just_auto_filled_ollama_url", True)
            elif current_base_url == default_ollama_url: # If it's already default, mark it as such
                 form_widget.setProperty("just_auto_filled_ollama_url", True)
            else: # User has a custom ollama URL
                 form_widget.setProperty("just_auto_filled_ollama_url", False)

        else: # Not ollama type
            form_widget.setProperty("just_auto_filled_ollama_url", False)
            # If it was previously auto-filled for ollama and type changed, clear it only if it's the default ollama url
            if form_widget.base_url_edit.text().strip() == "http://localhost:11434":
                 # form_widget.base_url_edit.clear() # Optional: clear if switching away from auto-filled ollama
                 pass


        form_widget.model_combo.clear()
        form_widget.model_combo.setPlaceholderText("Provider details changed. Click 'Refresh Models'.")
        
        if hasattr(form_widget, '_last_fetch_config'):
            delattr(form_widget, '_last_fetch_config')
        if hasattr(form_widget, '_last_successful_fetch_config'):
            delattr(form_widget, '_last_successful_fetch_config')


    def fetch_models_for_form(self, form_widget):
        provider_type = form_widget.type_combo.currentText()
        base_url = form_widget.base_url_edit.text().strip()
        api_key = form_widget.api_key_edit.text().strip() if provider_type == "openai_compatible" else None

        if not base_url:
            QMessageBox.warning(form_widget, "Missing Information", "Please enter a Base URL before fetching models.")
            current_combo_text = form_widget.model_combo.currentText()
            if (form_widget.model_combo.count() == 1 and form_widget.model_combo.itemText(0) == "Fetching models...") or \
               form_widget.model_combo.count() == 0:
                form_widget.model_combo.clear()
                form_widget.model_combo.setPlaceholderText("Enter Base URL to fetch models")
            return

        fetch_config = {
            "type": provider_type,
            "base_url": base_url,
            "api_key": api_key
        }
        
        if self.model_fetch_thread and self.model_fetch_thread.isRunning():
            QMessageBox.information(form_widget, "In Progress", "A model fetch operation is already in progress. Please wait.")
            return

        form_widget.model_combo.clear() 
        form_widget.model_combo.addItem("Fetching models...") 
        form_widget.model_combo.setEnabled(False)
        form_widget.refresh_models_button.setEnabled(False)
        
        # form_widget._current_attempt_fetch_config = dict(fetch_config) # Not strictly needed anymore

        self.model_fetch_thread = QThread()
        self.model_fetch_worker = ModelFetcher(fetch_config)
        self.model_fetch_worker.moveToThread(self.model_fetch_thread)

        self.active_model_combo = form_widget.model_combo
        self.active_refresh_button = form_widget.refresh_models_button

        self.model_fetch_worker.models_fetched.connect(self.on_models_fetched)
        self.model_fetch_worker.error_occurred.connect(self.on_model_fetch_error)
        self.model_fetch_worker.finished.connect(self.on_model_fetch_finished)
        
        self.model_fetch_thread.started.connect(self.model_fetch_worker.run)
        self.model_fetch_thread.start()

    def on_models_fetched(self, models):
        active_combo = self.active_model_combo 
        if not active_combo: return

        current_text_before_fetch = "" # Store text that might have been typed by user
        # Check if the current item is the "Fetching models..." placeholder
        if active_combo.count() == 1 and active_combo.itemText(0) == "Fetching models...":
            pass # It was the placeholder, current_text_before_fetch remains empty
        elif active_combo.count() > 0 : # There was some other text or selection
            current_text_before_fetch = active_combo.currentText()
        
        active_combo.clear()
        if models:
            active_combo.addItems(models)
            # Try to restore previous selection or manually typed text if it's in the fetched list
            if current_text_before_fetch and current_text_before_fetch in models:
                active_combo.setCurrentText(current_text_before_fetch)
            elif models: 
                active_combo.setCurrentIndex(0) # Default to first fetched model
            # form_widget_ref = active_combo.parentWidget().parentWidget() # Get the QDialog form_widget
            # if form_widget_ref and hasattr(form_widget_ref, '_current_attempt_fetch_config'):
            #      form_widget_ref._last_successful_fetch_config = dict(form_widget_ref._current_attempt_fetch_config)
            #      delattr(form_widget_ref, '_current_attempt_fetch_config')
        else: # No models fetched
            if current_text_before_fetch and current_text_before_fetch != "Fetching models...":
                 active_combo.addItem(current_text_before_fetch)
                 active_combo.setCurrentText(current_text_before_fetch)
            else: 
                active_combo.setPlaceholderText("No models found or enter manually")
        
        if active_combo.count() == 0: # If after all logic, combo is empty
            active_combo.setPlaceholderText("No models found or enter manually")


    def on_model_fetch_error(self, error_message):
        active_combo = self.active_model_combo 
        if not active_combo: return

        QMessageBox.warning(self, "Model Fetch Error", error_message)
        current_text_before_fetch = ""
        if active_combo.count() == 1 and active_combo.itemText(0) == "Fetching models...":
            pass
        elif active_combo.count() > 0:
            current_text_before_fetch = active_combo.currentText()
            
        active_combo.clear() 
        if current_text_before_fetch and current_text_before_fetch != "Fetching models...":
            active_combo.addItem(current_text_before_fetch) 
            active_combo.setCurrentText(current_text_before_fetch)
        else:
            active_combo.setPlaceholderText("Error fetching models; enter manually")

    def on_model_fetch_finished(self):
        if self.active_model_combo:
            self.active_model_combo.setEnabled(True)
        if self.active_refresh_button:
            self.active_refresh_button.setEnabled(True)
            
        if self.model_fetch_thread:
            self.model_fetch_thread.quit()
            self.model_fetch_thread.wait()
        self.model_fetch_thread = None
        self.model_fetch_worker = None
        self.active_model_combo = None
        self.active_refresh_button = None

    def load_system_prompt(self):
        self.system_prompt_text_edit.setText(self.settings.get("system_prompt", ""))

    def _clear_form(self, form_widget):
        form_widget.name_edit.clear()
        form_widget.type_combo.setCurrentIndex(0) 
        form_widget.base_url_edit.clear()
        form_widget.api_key_edit.clear()
        form_widget.model_combo.clear() 
        form_widget.model_combo.setPlaceholderText("Click 'Refresh Models' or type manually")
        form_widget.api_key_edit.setEnabled(form_widget.type_combo.currentText() == "openai_compatible")

    def add_new_provider_ui(self):
        self.provider_list_widget.clearSelection() 
        self._clear_form(self.add_provider_widget) 
        self.add_provider_widget.name_edit.setFocus() 
        self.provider_config_stack.setCurrentIndex(1) 

    def save_added_provider_details(self):
        form = self.add_provider_widget
        name = form.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Input Error", "Provider Name cannot be empty.")
            return

        if any(p["name"] == name for p in self.settings.get("providers", [])):
            QMessageBox.warning(self, "Input Error", f"Provider with name '{name}' already exists.")
            return

        provider_details = {
            "name": name,
            "type": form.type_combo.currentText(),
            "base_url": form.base_url_edit.text().strip(),
            "api_key": form.api_key_edit.text().strip() if form.type_combo.currentText() == "openai_compatible" else None,
            "model": form.model_combo.currentText().strip() 
        }
        
        self.settings.setdefault("providers", []).append(provider_details)
        if len(self.settings["providers"]) == 1: 
             self.settings["selected_provider_name"] = name

        self.populate_provider_list()
        for i in range(self.provider_list_widget.count()):
            if self.provider_list_widget.item(i).text() == name:
                self.provider_list_widget.setCurrentRow(i)
                break
        self.provider_config_stack.setCurrentIndex(0) 
        QMessageBox.information(self, "Provider Added", f"Provider '{name}' added. Remember to click 'Save All Settings'.")

    def remove_selected_provider_ui(self):
        selected_items = self.provider_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selection Error", "Please select a provider to remove.")
            return

        provider_name_to_remove = selected_items[0].text()
        reply = QMessageBox.question(self, "Confirm Removal",
                                     f"Are you sure you want to remove provider '{provider_name_to_remove}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.settings["providers"] = [p for p in self.settings["providers"] if p["name"] != provider_name_to_remove]
            
            if self.settings.get("selected_provider_name") == provider_name_to_remove:
                if self.settings["providers"]:
                    self.settings["selected_provider_name"] = self.settings["providers"][0]["name"]
                else:
                    self.settings["selected_provider_name"] = None
            
            self.populate_provider_list()
            if self.provider_list_widget.count() > 0:
                 self.provider_list_widget.setCurrentRow(0) 
                 self.provider_config_stack.setCurrentIndex(0) 
            else:
                 self._clear_form(self.edit_provider_widget)
                 self.provider_config_stack.setCurrentIndex(1) 
            QMessageBox.information(self, "Provider Removed", f"Provider '{provider_name_to_remove}' removed. Remember to click 'Save All Settings'.")

    def save_all_settings(self):
        current_selected_items = self.provider_list_widget.selectedItems()
        if current_selected_items and self.provider_config_stack.currentIndex() == 0: 
            selected_provider_original_name = current_selected_items[0].text()
            form = self.edit_provider_widget
            
            edited_name = form.name_edit.text().strip()
            if not edited_name:
                QMessageBox.warning(self, "Input Error", "Provider Name cannot be empty when editing.")
                return

            if edited_name != selected_provider_original_name:
                if any(p["name"] == edited_name for p in self.settings["providers"] if p["name"] != selected_provider_original_name):
                    QMessageBox.warning(self, "Input Error", f"Another provider with name '{edited_name}' already exists.")
                    return

            provider_to_update = next((p for p in self.settings["providers"] if p["name"] == selected_provider_original_name), None)
            if provider_to_update:
                provider_to_update["name"] = edited_name
                provider_to_update["type"] = form.type_combo.currentText()
                provider_to_update["base_url"] = form.base_url_edit.text().strip()
                provider_to_update["api_key"] = form.api_key_edit.text().strip() if form.type_combo.currentText() == "openai_compatible" else None
                provider_to_update["model"] = form.model_combo.currentText().strip() 
                
                if self.settings.get("selected_provider_name") == selected_provider_original_name and edited_name != selected_provider_original_name:
                    self.settings["selected_provider_name"] = edited_name
        
        if self.provider_list_widget.currentItem():
            self.settings["selected_provider_name"] = self.provider_list_widget.currentItem().text()
        elif self.settings["providers"]: 
             self.settings["selected_provider_name"] = self.settings["providers"][0]["name"]
        else: 
            self.settings["selected_provider_name"] = None

        self.settings["system_prompt"] = self.system_prompt_text_edit.toPlainText().strip()

        try:
            config_manager.save_settings(self.settings)
            QMessageBox.information(self, "Settings Saved", "All settings have been saved successfully.")
            self.accept() 
        except Exception as e:
            QMessageBox.critical(self, "Error Saving Settings", f"Could not save settings: {e}")

if __name__ == '__main__':
    # Initialize logging for standalone testing
    try:
        from ..core.logger import init_logging
        init_logging()
    except ImportError:
        from core.logger import init_logging
        init_logging()
    
    app = QApplication(sys.argv)
    if not config_manager.SETTINGS_FILE_PATH.exists():
        log_info(f"Creating dummy settings file at: {config_manager.SETTINGS_FILE_PATH}")
        config_manager.save_settings(config_manager.DEFAULT_SETTINGS)

    dialog = SettingsDialog()
    if dialog.exec():
        log_info("Settings saved.")
        log_info(f"Final settings: {config_manager.load_settings()}")
    else:
        log_info("Settings dialog cancelled.")
    
    # if config_manager.SETTINGS_FILE_PATH.exists():
    #     log_info(f"Removing test settings file: {config_manager.SETTINGS_FILE_PATH}")
    #     os.remove(config_manager.SETTINGS_FILE_PATH)