"""
Tests for backup and restore workflows.
"""

import tempfile
from datetime import datetime
from pathlib import Path

from src.database.db import get_database, init_database
from src.services.auth_service import AuthenticationService
from src.services.backup_service import BackupService
from src.services.inventory_service import InventoryService


class TestBackupService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_backup.db"
        init_database(self.db_path)

        self.inventory_service = InventoryService()
        self.auth_service = AuthenticationService()
        self.backup_service = BackupService()
        self.backup_service.backup_dir = Path(self.temp_dir.name) / "backups"
        self.backup_service.backup_dir.mkdir(parents=True, exist_ok=True)
        success, _, _ = self.auth_service.create_user(
            username="backupadmin",
            email="backupadmin@example.com",
            password="password123",
            full_name="Backup Admin",
            role="administrator",
        )
        assert success

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_create_backup_and_list_backups(self):
        success, message, backup_path = self.backup_service.create_backup(label="manual")
        assert success
        assert message.startswith("Backup created successfully | Signed at ")
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.name.endswith(".db.enc")
        assert not backup_path.read_bytes().startswith(b"SQLite format 3")

        backups = self.backup_service.list_backups()
        assert len(backups) == 1
        assert backups[0].name == backup_path.name

    def test_restore_backup_reverts_database_state(self):
        success, _, _ = self.inventory_service.add_item(
            name="Paracetamol",
            barcode="PCM-RESTORE-001",
            category="Medicines",
            current_quantity=10,
            minimum_quantity=5,
            maximum_quantity=30,
        )
        assert success

        success, _, backup_path = self.backup_service.create_backup()
        assert success
        assert backup_path is not None

        success, _, _ = self.inventory_service.add_item(
            name="Ibuprofen",
            barcode="IBU-RESTORE-001",
            category="Medicines",
            current_quantity=20,
            minimum_quantity=5,
            maximum_quantity=40,
        )
        assert success
        assert len(self.inventory_service.get_all_items()) == 2

        success, message = self.backup_service.restore_backup(backup_path)
        assert success
        assert message.startswith("Backup restored successfully | Signed at ")

        restored_inventory_service = InventoryService()
        restored_items = restored_inventory_service.get_all_items()
        assert len(restored_items) == 1
        assert restored_items[0].item_name == "Paracetamol"

    def test_delete_backup_requires_admin_password(self):
        success, _, backup_path = self.backup_service.create_backup()
        assert success
        assert backup_path is not None

        success, message = self.backup_service.delete_backup(backup_path, "wrong-password")
        assert not success
        assert message == "Invalid administrator password"
        assert backup_path.exists()

        success, message = self.backup_service.delete_backup(backup_path, "password123")
        assert success
        assert message.startswith("Backup deleted successfully | Signed at ")
        assert not backup_path.exists()

    def test_auto_backup_settings_defaults_and_save(self):
        settings = self.backup_service.get_auto_backup_settings()
        assert settings["enabled"] is False
        assert settings["schedule_time"] == "02:00"

        success, message = self.backup_service.update_auto_backup_settings(True, "03:30")
        assert success
        assert message == "Automatic backup settings saved"

        updated = self.backup_service.get_auto_backup_settings()
        assert updated["enabled"] is True
        assert updated["schedule_time"] == "03:30"

    def test_auto_backup_settings_reject_invalid_time(self):
        success, message = self.backup_service.update_auto_backup_settings(True, "3:30")
        assert not success
        assert message == "Backup time must use 24-hour HH:MM format"

    def test_scheduled_backup_runs_once_per_day(self):
        success, _ = self.backup_service.update_auto_backup_settings(True, "03:30")
        assert success

        due_time = datetime(2026, 7, 26, 3, 31, 0)
        not_due_time = datetime(2026, 7, 26, 3, 29, 59)

        assert not self.backup_service.is_scheduled_backup_due(not_due_time)
        assert self.backup_service.is_scheduled_backup_due(due_time)

        ran, message, backup_path = self.backup_service.run_scheduled_backup_if_due(due_time)
        assert ran
        assert message.startswith("Automatic backup created successfully | Signed at ")
        assert backup_path is not None
        assert backup_path.exists()

        second_ran, second_message, second_path = self.backup_service.run_scheduled_backup_if_due(due_time)
        assert not second_ran
        assert second_message == "No scheduled backup due"
        assert second_path is None
