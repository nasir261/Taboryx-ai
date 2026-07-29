"""
Tests for saved credentials service.
"""

import tempfile
import json
import base64
from pathlib import Path

from src.services.encryption_service import EncryptionService
from src.services.saved_credentials_service import SavedCredentialsService


class TestSavedCredentialsService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = SavedCredentialsService()
        self.service.credentials_path = Path(self.temp_dir.name) / "saved_credentials.json"

    def teardown_method(self):
        self.temp_dir.cleanup()

    def test_save_and_load_credentials(self):
        success, message = self.service.save_credentials("admin", "password123")
        assert success
        assert message == "Credentials saved"

        raw_payload = json.loads(self.service.credentials_path.read_text(encoding="utf-8"))
        assert "password_encrypted" in raw_payload
        assert "password_b64" not in raw_payload
        assert "password123" not in raw_payload["password_encrypted"]

        username, password, is_saved = self.service.load_credentials()
        assert is_saved
        assert username == "admin"
        assert password == "password123"

    def test_clear_credentials(self):
        success, _ = self.service.save_credentials("admin", "password123")
        assert success

        success, message = self.service.clear_credentials()
        assert success
        assert message == "Saved credentials cleared"

        username, password, is_saved = self.service.load_credentials()
        assert not is_saved
        assert username is None
        assert password is None

    def test_load_legacy_base64_credentials_and_migrate(self):
        legacy_payload = {
            "username": "legacy_admin",
            "password_b64": base64.b64encode("password123".encode("utf-8")).decode("ascii"),
            "save_password": True,
        }
        self.service.credentials_path.write_text(json.dumps(legacy_payload), encoding="utf-8")

        username, password, is_saved = self.service.load_credentials()
        assert is_saved
        assert username == "legacy_admin"
        assert password == "password123"

        migrated_payload = json.loads(self.service.credentials_path.read_text(encoding="utf-8"))
        assert "password_encrypted" in migrated_payload
        assert "password_b64" not in migrated_payload

    def test_save_and_load_credentials_with_dpapi_fallback(self, monkeypatch):
        monkeypatch.setattr(EncryptionService, "_get_backend", lambda self: "dpapi")
        monkeypatch.setattr(EncryptionService, "_dpapi_protect", lambda self, payload: payload[::-1])
        monkeypatch.setattr(EncryptionService, "_dpapi_unprotect", lambda self, payload: payload[::-1])

        service = SavedCredentialsService()
        service.credentials_path = Path(self.temp_dir.name) / "saved_credentials_dpapi.json"

        success, message = service.save_credentials("admin", "password123")
        assert success
        assert message == "Credentials saved"

        username, password, is_saved = service.load_credentials()
        assert is_saved
        assert username == "admin"
        assert password == "password123"
