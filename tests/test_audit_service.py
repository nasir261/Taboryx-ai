"""
Tests for room audit service workflows.
"""

import tempfile
from pathlib import Path
from datetime import date, datetime
from src.database.db import init_database, get_database
from src.services.audit_service import AuditService
from src.services.room_service import ClinicalRoomService
from src.services.inventory_service import InventoryService
from src.services.auth_service import AuthenticationService
from src.models.models import RoomAudit, ClinicalRoom, StockMovement


class TestAuditService:
    """Test room audit service operations"""

    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_audit.db"
        init_database(self.db_path)
        self.audit_service = AuditService()
        self.room_service = ClinicalRoomService()
        self.inventory_service = InventoryService()
        self.auth_service = AuthenticationService()

        self.user = self.auth_service.create_user(
            username="auditor",
            email="auditor@example.com",
            password="password123",
            full_name="Audit User",
            role="administrator"
        )
        self.audit_user_id = self.user[2] if isinstance(self.user, tuple) else 1
        nurse = self.auth_service.create_user(
            username="auditnurse",
            email="auditnurse@example.com",
            password="password123",
            full_name="Audit Nurse",
            role="nurse",
        )
        self.nurse_user_id = nurse[2] if isinstance(nurse, tuple) else None

        self.room = ClinicalRoom(room_name="Audit Room 1", room_type="Treatment", floor=1)
        self.room.id = self.room_service.create_room(self.room)

        success, _, item_id = self.inventory_service.add_item(
            name="Gloves",
            barcode="GLV123",
            category="PPE",
            current_quantity=20,
            minimum_quantity=5,
            maximum_quantity=100,
            clinical_room=self.room.room_name,
        )
        assert success
        self.item_id = item_id

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_create_and_fetch_audit(self):
        audit = RoomAudit(
            room_id=self.room.id,
            audit_date=date.today(),
            audit_time=datetime.now().strftime("%H:%M:%S"),
            audited_by_user_id=1,
            status="completed",
            notes="Routine check",
        )
        audit_items = [
            self._build_audit_item(self.item_id, 20, 20, False, False, "")
        ]

        success, message, audit_id = self.audit_service.create_audit(audit, audit_items)
        assert success
        assert audit_id is not None

        fetched_audits = self.audit_service.get_audits(self.room.id)
        assert len(fetched_audits) == 1
        assert fetched_audits[0].room_id == self.room.id

        fetched_items = self.audit_service.get_audit_items(audit_id)
        assert len(fetched_items) == 1
        assert fetched_items[0].item_id == 1

    def test_audit_summary_counts(self):
        audit = RoomAudit(
            room_id=self.room.id,
            audit_date=date.today(),
            audit_time=datetime.now().strftime("%H:%M:%S"),
            audited_by_user_id=1,
            status="completed",
        )
        audit_items = [
            self._build_audit_item(self.item_id, 20, 0, False, True, "Missing item"),
            self._build_audit_item(self.item_id, 20, 18, True, False, "Expired")
        ]

        success, message, audit_id = self.audit_service.create_audit(audit, audit_items)
        assert success

        fetched_audit = self.audit_service.get_audit_by_id(audit_id)
        assert fetched_audit.missing_items_count == 1
        assert fetched_audit.expired_items_count == 1
        assert fetched_audit.quantity_discrepancies_count == 2

    def test_complete_audit(self):
        audit = RoomAudit(
            room_id=self.room.id,
            audit_date=date.today(),
            audit_time=datetime.now().strftime("%H:%M:%S"),
            audited_by_user_id=1,
            status="in_progress",
        )
        audit_items = [self._build_audit_item(self.item_id, 20, 20, False, False, "")]
        success, _, audit_id = self.audit_service.create_audit(audit, audit_items)
        assert success

        success, message = self.audit_service.complete_audit(audit_id)
        assert success

        completed = self.audit_service.get_audit_by_id(audit_id)
        assert completed.status == "completed"

    def test_delete_audit_requires_admin_password(self):
        audit = RoomAudit(
            room_id=self.room.id,
            audit_date=date.today(),
            audit_time=datetime.now().strftime("%H:%M:%S"),
            audited_by_user_id=1,
            status="completed",
        )
        audit_items = [self._build_audit_item(self.item_id, 20, 20, False, False, "")]
        success, _, audit_id = self.audit_service.create_audit(audit, audit_items)
        assert success

        success, message = self.audit_service.delete_audit(audit_id, "wrong-password")
        assert not success
        assert message == "Invalid administrator password"

    def test_delete_audit_removes_audit_and_items(self):
        audit = RoomAudit(
            room_id=self.room.id,
            audit_date=date.today(),
            audit_time=datetime.now().strftime("%H:%M:%S"),
            audited_by_user_id=1,
            status="completed",
        )
        audit_items = [self._build_audit_item(self.item_id, 20, 20, False, False, "")]
        success, _, audit_id = self.audit_service.create_audit(audit, audit_items)
        assert success

        success, message = self.audit_service.delete_audit(audit_id, "password123")
        assert success
        assert message.startswith("Audit deleted | Signed at ")

        assert self.audit_service.get_audit_by_id(audit_id) is None
        assert len(self.audit_service.get_audit_items(audit_id)) == 0

    def test_verify_admin_password_for_rerun_action(self):
        success, message = self.audit_service.verify_admin_password("wrong-password")
        assert not success
        assert message == "Invalid administrator password"

        success, message = self.audit_service.verify_admin_password("password123")
        assert success
        assert message == "Administrator verified"

    def test_non_admin_user_cannot_delete_audit(self):
        audit = RoomAudit(
            room_id=self.room.id,
            audit_date=date.today(),
            audit_time=datetime.now().strftime("%H:%M:%S"),
            audited_by_user_id=1,
            status="completed",
        )
        audit_items = [self._build_audit_item(self.item_id, 20, 20, False, False, "")]
        success, _, audit_id = self.audit_service.create_audit(audit, audit_items)
        assert success

        db = get_database()
        db.set_audit_user(self.nurse_user_id)
        success, message = self.audit_service.delete_audit(audit_id, "password123")
        assert not success
        assert message == "Only administrators can delete transaction records"

    def _build_audit_item(self, item_id, expected, actual, expired, missing, notes):
        from src.models.models import AuditItem
        return AuditItem(
            item_id=item_id,
            expected_quantity=expected,
            actual_quantity=actual,
            quantity_discrepancy=actual - expected,
            is_expired=expired,
            is_missing=missing,
            notes=notes,
        )
