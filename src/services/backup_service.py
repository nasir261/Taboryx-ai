"""
Backup Service
Handles database backup and restore workflows.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from src.config import BACKUP_DIR
from src.database.db import get_database, init_database
from src.services.app_settings_service import AppSettingsService
from src.services.auth_service import AuthenticationService
from src.services.encryption_service import EncryptionService
from src.services.time_sync_service import get_time_sync_service

try:
    from cryptography.fernet import InvalidToken
except ImportError:
    InvalidToken = ValueError


class BackupService:
    """Service for database backup and restore operations."""

    AUTO_BACKUP_ENABLED_KEY = "backup.auto.enabled"
    AUTO_BACKUP_TIME_KEY = "backup.auto.time"
    AUTO_BACKUP_LAST_RUN_DATE_KEY = "backup.auto.last_run_date"
    AUTO_BACKUP_DEFAULT_TIME = "02:00"

    def __init__(self):
        self.db = get_database()
        self.backup_dir = BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.app_settings_service = AppSettingsService()
        self.encryption_service = EncryptionService()
        self.time_sync_service = get_time_sync_service()

    def create_backup(self, label: Optional[str] = None) -> Tuple[bool, str, Optional[Path]]:
        """Create a timestamped backup of the active database file."""
        db_path = self.db.db_path
        if not db_path.exists():
            return False, "Database file not found", None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_label = f"_{label.strip().replace(' ', '_')}" if label and label.strip() else ""
        backup_path = self.backup_dir / f"medistock_backup_{timestamp}{safe_label}.db.enc"

        self.db.connection.commit()
        try:
            encrypted_payload = self.encryption_service.encrypt_bytes(db_path.read_bytes())
        except RuntimeError as exc:
            return False, f"Backup encryption unavailable: {exc}", None
        backup_path.write_bytes(encrypted_payload)
        return True, f"Backup created successfully | {self.time_sync_service.get_signature_stamp()}", backup_path

    def list_backups(self) -> List[Path]:
        """List available backups, newest first."""
        encrypted_backups = list(self.backup_dir.glob("medistock_backup_*.db.enc"))
        legacy_backups = list(self.backup_dir.glob("medistock_backup_*.db"))
        backups = sorted(encrypted_backups + legacy_backups, key=lambda p: p.stat().st_mtime, reverse=True)
        return backups

    def restore_backup(self, backup_path: Path) -> Tuple[bool, str]:
        """Restore database from a backup file."""
        if not backup_path or not Path(backup_path).exists():
            return False, "Backup file not found"

        active_db = get_database()
        db_path = active_db.db_path
        active_db.close()

        source_path = Path(backup_path)
        if source_path.suffix.lower() == ".enc":
            encrypted_payload = source_path.read_bytes()
            try:
                decrypted = self.encryption_service.decrypt_bytes(encrypted_payload)
            except RuntimeError as exc:
                return False, f"Backup decryption unavailable: {exc}"
            except (InvalidToken, ValueError):
                return False, "Backup decryption failed"
            db_path.write_bytes(decrypted)
        else:
            shutil.copy2(source_path, db_path)
        self.db = init_database(db_path)
        self.time_sync_service = get_time_sync_service()
        return True, f"Backup restored successfully | {self.time_sync_service.get_signature_stamp()}"

    def delete_backup(self, backup_path: Path, admin_password: str) -> Tuple[bool, str]:
        """Delete a backup file after validating administrator password."""
        admin_user = self._authenticate_admin(admin_password)
        if not admin_user:
            return False, "Invalid administrator password"

        if not backup_path:
            return False, "Backup file not found"

        backup = Path(backup_path)
        if not backup.exists():
            return False, "Backup file not found"

        if backup.parent.resolve() != self.backup_dir.resolve():
            return False, "Invalid backup file location"

        if not backup.name.startswith("medistock_backup_"):
            return False, "Invalid backup file"
        if backup.suffix.lower() not in {".db", ".enc"} and not backup.name.endswith(".db.enc"):
            return False, "Invalid backup file"

        backup.unlink()
        return True, f"Backup deleted successfully | {self.time_sync_service.get_signature_stamp()}"

    def get_auto_backup_settings(self) -> Dict:
        enabled_raw = self.app_settings_service.get_setting(self.AUTO_BACKUP_ENABLED_KEY, "0")
        schedule_time = self.app_settings_service.get_setting(self.AUTO_BACKUP_TIME_KEY, self.AUTO_BACKUP_DEFAULT_TIME)
        if not self._is_valid_schedule_time(schedule_time):
            schedule_time = self.AUTO_BACKUP_DEFAULT_TIME
        return {
            "enabled": enabled_raw == "1",
            "schedule_time": schedule_time,
        }

    def update_auto_backup_settings(self, enabled: bool, schedule_time: str) -> Tuple[bool, str]:
        normalized_time = (schedule_time or "").strip()
        if not self._is_valid_schedule_time(normalized_time):
            return False, "Backup time must use 24-hour HH:MM format"

        self.app_settings_service.set_setting(self.AUTO_BACKUP_ENABLED_KEY, "1" if enabled else "0")
        self.app_settings_service.set_setting(self.AUTO_BACKUP_TIME_KEY, normalized_time)
        return True, "Automatic backup settings saved"

    def run_scheduled_backup_if_due(self, now: Optional[datetime] = None) -> Tuple[bool, str, Optional[Path]]:
        current_time = now or datetime.now()
        if not self.is_scheduled_backup_due(current_time):
            return False, "No scheduled backup due", None

        success, message, backup_path = self.create_backup(label="auto")
        if not success:
            return False, message, None

        self._set_last_auto_backup_run_date(current_time.date().isoformat())
        return True, f"Automatic backup created successfully | {self.time_sync_service.get_signature_stamp()}", backup_path

    def is_scheduled_backup_due(self, now: Optional[datetime] = None) -> bool:
        current_time = now or datetime.now()
        settings = self.get_auto_backup_settings()
        if not settings["enabled"]:
            return False

        schedule_time = settings["schedule_time"]
        hour, minute = [int(part) for part in schedule_time.split(":")]
        scheduled_for_today = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if current_time < scheduled_for_today:
            return False

        last_run_date = self.app_settings_service.get_setting(self.AUTO_BACKUP_LAST_RUN_DATE_KEY, "")
        return last_run_date != current_time.date().isoformat()

    @staticmethod
    def _is_valid_schedule_time(value: str) -> bool:
        if not value:
            return False
        try:
            parsed = datetime.strptime(value, "%H:%M")
            return parsed.strftime("%H:%M") == value
        except ValueError:
            return False

    def _set_last_auto_backup_run_date(self, iso_date: str):
        self.app_settings_service.set_setting(self.AUTO_BACKUP_LAST_RUN_DATE_KEY, iso_date)

    def _authenticate_admin(self, password: str):
        if not password:
            return None
        admins = self.db.fetch_all(
            "SELECT id, username, password_hash FROM users WHERE is_active = 1 AND LOWER(role) = 'administrator'"
        )
        for row in admins:
            if AuthenticationService.verify_password(password, row.get("password_hash", "")):
                return row
        return None
