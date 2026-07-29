"""
Tests for app settings encryption behavior.
"""

import tempfile
from pathlib import Path

from src.database.db import get_database, init_database
from src.services.app_settings_service import AppSettingsService


class TestAppSettingsService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_app_settings.db"
        init_database(self.db_path)
        self.service = AppSettingsService()
        self.db = get_database()

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_sensitive_key_is_stored_encrypted_and_returned_decrypted(self):
        self.service.set_setting("security.api_token", "secret-token-123")
        stored = self.db.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("security.api_token",))
        assert stored is not None
        assert stored["value"] != "secret-token-123"
        assert str(stored["value"]).startswith("ENC::")

        loaded = self.service.get_setting("security.api_token")
        assert loaded == "secret-token-123"

    def test_non_sensitive_key_remains_plaintext(self):
        self.service.set_setting("purchasing.lookback_days", "90")
        stored = self.db.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("purchasing.lookback_days",))
        assert stored is not None
        assert stored["value"] == "90"

    def test_voice_typing_microphone_setting_remains_plaintext(self):
        self.service.set_setting("voice_typing.selected_microphone_name", "iPhone Microphone")
        stored = self.db.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("voice_typing.selected_microphone_name",))
        assert stored is not None
        assert stored["value"] == "iPhone Microphone"
