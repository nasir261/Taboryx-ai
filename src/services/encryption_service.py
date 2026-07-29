"""
Encryption service for sensitive local data at rest.
"""

import base64
import ctypes
import os
from pathlib import Path

from src.config import ENCRYPTION_KEY_PATH


class EncryptionService:
    """Provides symmetric encryption/decryption utilities."""

    ENCRYPTED_PREFIX = "ENC::"
    FERNET_MARKER = "fernet"
    DPAPI_MARKER = "dpapi"

    def __init__(self):
        self.key_path = ENCRYPTION_KEY_PATH
        self._fernet = None
        self._backend = None
        self._backend_error = None

    def encrypt_text(self, plain_text: str) -> str:
        backend = self._get_backend()
        if backend == self.DPAPI_MARKER:
            encrypted = self._dpapi_protect(plain_text.encode("utf-8"))
            token = base64.b64encode(encrypted).decode("ascii")
            return f"{self.ENCRYPTED_PREFIX}{self.DPAPI_MARKER}:{token}"

        token = self._get_fernet().encrypt(plain_text.encode("utf-8")).decode("ascii")
        return f"{self.ENCRYPTED_PREFIX}{self.FERNET_MARKER}:{token}"

    def decrypt_text(self, encrypted_text: str) -> str:
        if not self.is_encrypted_text(encrypted_text):
            return encrypted_text
        token = encrypted_text[len(self.ENCRYPTED_PREFIX):]
        plain_bytes = self._decrypt_token(token)
        return plain_bytes.decode("utf-8")

    def encrypt_bytes(self, payload: bytes) -> bytes:
        backend = self._get_backend()
        if backend == self.DPAPI_MARKER:
            encrypted = self._dpapi_protect(payload)
            return f"{self.ENCRYPTED_PREFIX}{self.DPAPI_MARKER}:".encode("ascii") + base64.b64encode(encrypted)
        token = self._get_fernet().encrypt(payload).decode("ascii")
        return f"{self.ENCRYPTED_PREFIX}{self.FERNET_MARKER}:{token}".encode("ascii")

    def decrypt_bytes(self, payload: bytes) -> bytes:
        prefix = f"{self.ENCRYPTED_PREFIX}{self.FERNET_MARKER}:".encode("ascii")
        dpapi_prefix = f"{self.ENCRYPTED_PREFIX}{self.DPAPI_MARKER}:".encode("ascii")
        if payload.startswith(prefix):
            token = payload[len(prefix):]
            return self._get_fernet().decrypt(token)
        if payload.startswith(dpapi_prefix):
            token = payload[len(dpapi_prefix):]
            return self._dpapi_unprotect(base64.b64decode(token))
        return self._get_fernet().decrypt(payload)

    def is_encrypted_text(self, value: str) -> bool:
        return isinstance(value, str) and value.startswith(self.ENCRYPTED_PREFIX)

    def is_backend_available(self) -> bool:
        try:
            self._get_backend()
            return True
        except RuntimeError:
            return False

    def decrypt_text_safe(self, encrypted_text: str):
        invalid_token_error = ValueError
        try:
            from cryptography.fernet import InvalidToken

            invalid_token_error = InvalidToken
        except ImportError:
            pass

        try:
            return self.decrypt_text(encrypted_text), None
        except (RuntimeError, invalid_token_error, UnicodeDecodeError, ValueError) as exc:
            return None, str(exc)

    def _decrypt_token(self, token: str) -> bytes:
        if token.startswith(f"{self.FERNET_MARKER}:"):
            return self._get_fernet().decrypt(token.split(":", 1)[1].encode("ascii"))
        if token.startswith(f"{self.DPAPI_MARKER}:"):
            raw = base64.b64decode(token.split(":", 1)[1].encode("ascii"))
            return self._dpapi_unprotect(raw)
        try:
            return self._get_fernet().decrypt(token.encode("ascii"))
        except RuntimeError:
            raw = base64.b64decode(token.encode("ascii"))
            return self._dpapi_unprotect(raw)

    def _get_or_create_key(self, Fernet) -> bytes:
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        if self.key_path.exists():
            key = self.key_path.read_bytes().strip()
            if key:
                return key

        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        return key

    def _get_backend(self) -> str:
        if self._backend is not None:
            return self._backend

        try:
            from cryptography.fernet import Fernet

            self._get_or_create_key(Fernet)
            self._backend = self.FERNET_MARKER
            return self._backend
        except Exception:
            if os.name == "nt":
                self._backend = self.DPAPI_MARKER
                return self._backend
            self._backend_error = "Encryption backend unavailable. Install dependency: cryptography."
            raise RuntimeError(self._backend_error)

    def _get_fernet(self):
        if self._fernet is not None:
            return self._fernet

        if self._get_backend() != self.FERNET_MARKER:
            self._backend_error = "Encryption backend unavailable. Install dependency: cryptography."
            raise RuntimeError(self._backend_error)

        from cryptography.fernet import Fernet

        key = self._get_or_create_key(Fernet)
        self._fernet = Fernet(key)
        return self._fernet

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.c_uint), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    @staticmethod
    def _bytes_to_blob(payload: bytes):
        buffer = ctypes.create_string_buffer(payload, len(payload))
        blob = EncryptionService._DATA_BLOB(len(payload), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
        return blob, buffer

    @staticmethod
    def _blob_to_bytes(blob) -> bytes:
        if not blob.pbData or blob.cbData == 0:
            return b""
        return ctypes.string_at(blob.pbData, blob.cbData)

    def _dpapi_protect(self, payload: bytes) -> bytes:
        if os.name != "nt":
            raise RuntimeError("Encryption backend unavailable. Install dependency: cryptography.")
        in_blob, in_buffer = self._bytes_to_blob(payload)
        out_blob = self._DATA_BLOB()
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        if not crypt32.CryptProtectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
            raise RuntimeError("Windows encryption backend failed")
        try:
            return self._blob_to_bytes(out_blob)
        finally:
            if out_blob.pbData:
                kernel32.LocalFree(out_blob.pbData)

    def _dpapi_unprotect(self, payload: bytes) -> bytes:
        if os.name != "nt":
            raise RuntimeError("Encryption backend unavailable. Install dependency: cryptography.")
        in_blob, in_buffer = self._bytes_to_blob(payload)
        out_blob = self._DATA_BLOB()
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        if not crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
            raise RuntimeError("Windows decryption backend failed")
        try:
            return self._blob_to_bytes(out_blob)
        finally:
            if out_blob.pbData:
                kernel32.LocalFree(out_blob.pbData)
