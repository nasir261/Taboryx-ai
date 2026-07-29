"""
Application Settings Service
Stores and retrieves key-value app settings.
"""

from typing import Optional

from src.database.db import get_database
from src.config import SENSITIVE_APP_SETTING_PREFIXES
from src.services.encryption_service import EncryptionService


class AppSettingsService:
    """Service for persisted application settings."""

    def __init__(self):
        self.db = get_database()
        self.encryption_service = EncryptionService()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self.db.fetch_one("SELECT value FROM app_settings WHERE key = ?", (key,))
        if not row:
            return default
        value = row.get("value", default)
        if value is None:
            return default
        if self.encryption_service.is_encrypted_text(value):
            decrypted, err = self.encryption_service.decrypt_text_safe(value)
            if err:
                return default
            return decrypted
        return value

    def set_setting(self, key: str, value: Optional[str], encrypt: Optional[bool] = None):
        encrypt_value = self._should_encrypt(key) if encrypt is None else bool(encrypt)
        stored_value = self.encryption_service.encrypt_text(value) if (encrypt_value and value not in (None, "")) else value
        existing = self.db.fetch_one("SELECT key FROM app_settings WHERE key = ?", (key,))
        if existing:
            self.db.update("app_settings", {"value": stored_value}, "key = ?", (key,))
        else:
            self.db.insert("app_settings", {"key": key, "value": stored_value})

    @staticmethod
    def _should_encrypt(key: str) -> bool:
        normalized = (key or "").lower()
        return normalized.startswith(SENSITIVE_APP_SETTING_PREFIXES)
