"""
Saved Credentials Service
Handles persistent saved-login credentials for the login screen.
"""

import base64
import json
import logging
from typing import Optional, Tuple

from src.config import SAVED_CREDENTIALS_PATH
from src.services.encryption_service import EncryptionService

logger = logging.getLogger(__name__)


class SavedCredentialsService:
    """Service for storing and retrieving saved login credentials."""

    def __init__(self):
        self.credentials_path = SAVED_CREDENTIALS_PATH
        self.encryption_service = EncryptionService()

    def save_credentials(self, username: str, password: str) -> Tuple[bool, str]:
        """Persist credentials for login prefill."""
        if not username or not password:
            return False, "Username and password are required"

        payload = {
            "username": username,
            "save_password": True,
        }
        try:
            payload["password_encrypted"] = self.encryption_service.encrypt_text(password)
        except RuntimeError as exc:
            logger.error(f"Unable to encrypt saved credentials: {exc}")
            return False, "Unable to secure saved credentials on this device"

        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with self.credentials_path.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle)
        return True, "Credentials saved"

    def load_credentials(self) -> Tuple[Optional[str], Optional[str], bool]:
        """Load saved credentials for login prefill."""
        if not self.credentials_path.exists():
            return None, None, False

        try:
            with self.credentials_path.open("r", encoding="utf-8") as file_handle:
                payload = json.load(file_handle)
        except json.JSONDecodeError:
            logger.error("Saved credentials file is invalid JSON. Clearing saved credentials file.")
            self.clear_credentials()
            return None, None, False

        username = payload.get("username")
        password_encrypted = payload.get("password_encrypted")
        password_b64 = payload.get("password_b64")
        save_password = bool(payload.get("save_password", False))

        if not username or not save_password:
            return None, None, False

        if password_encrypted:
            password, err = self.encryption_service.decrypt_text_safe(password_encrypted)
            if err:
                logger.error("Saved encrypted credentials could not be decrypted. Clearing saved credentials file.")
                self.clear_credentials()
                return None, None, False
            return username, password, True

        # Backward-compatible migration for old base64 payloads.
        if password_b64:
            try:
                password = base64.b64decode(password_b64.encode("ascii")).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                logger.error("Saved credentials could not be decoded. Clearing saved credentials file.")
                self.clear_credentials()
                return None, None, False
            self.save_credentials(username, password)
            return username, password, True

        return None, None, False

    def clear_credentials(self) -> Tuple[bool, str]:
        """Remove saved credentials from disk."""
        if not self.credentials_path.exists():
            return True, "No saved credentials found"

        self.credentials_path.unlink()
        return True, "Saved credentials cleared"
