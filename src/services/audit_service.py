"""
Audit Service
Handles room audit workflows and audit item storage.
"""

import logging
from typing import List, Optional, Tuple
from datetime import datetime, date
from src.database.db import get_database
from src.models.models import RoomAudit, AuditItem, Item
from src.services.inventory_service import InventoryService
from src.services.auth_service import AuthenticationService
from src.services.time_sync_service import get_time_sync_service

logger = logging.getLogger(__name__)


class AuditService:
    """Service for room audits"""

    def __init__(self):
        self.db = get_database()
        self.inventory_service = InventoryService()
        self.time_sync_service = get_time_sync_service()

    def get_audits(self, room_id: Optional[int] = None) -> List[RoomAudit]:
        try:
            if room_id:
                rows = self.db.fetch_all(
                    "SELECT * FROM room_audits WHERE room_id = ? ORDER BY audit_date DESC, audit_time DESC",
                    (room_id,)
                )
            else:
                rows = self.db.fetch_all(
                    "SELECT * FROM room_audits ORDER BY audit_date DESC, audit_time DESC"
                )
            return [self._dict_to_audit(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching audits: {e}")
            return []

    def get_audit_by_id(self, audit_id: int) -> Optional[RoomAudit]:
        try:
            row = self.db.fetch_one("SELECT * FROM room_audits WHERE id = ?", (audit_id,))
            return self._dict_to_audit(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching audit by id: {e}")
            return None

    def get_audit_items(self, audit_id: int) -> List[AuditItem]:
        try:
            rows = self.db.fetch_all("SELECT * FROM audit_items WHERE audit_id = ?", (audit_id,))
            return [self._dict_to_audit_item(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching audit items: {e}")
            return []

    def create_audit(self, audit: RoomAudit, audit_items: List[AuditItem]) -> Tuple[bool, str, Optional[int]]:
        try:
            if not audit.room_id:
                return False, "Room is required for an audit", None
            if not audit.audited_by_user_id:
                return False, "Auditor is required", None

            audit.audit_date = audit.audit_date or self.time_sync_service.today()
            audit.audit_time = audit.audit_time or self.time_sync_service.now().strftime("%H:%M:%S")
            audit.status = audit.status or "completed"
            audit.total_items_checked = len(audit_items)
            audit.missing_items_count = sum(1 for item in audit_items if item.is_missing)
            audit.expired_items_count = sum(1 for item in audit_items if item.is_expired)
            audit.quantity_discrepancies_count = sum(1 for item in audit_items if item.quantity_discrepancy and item.quantity_discrepancy != 0)

            audit_id = self.db.insert("room_audits", audit.to_dict())
            if not audit_id:
                return False, "Failed to create audit record", None

            for audit_item in audit_items:
                audit_item.audit_id = audit_id
                self.db.insert("audit_items", audit_item.to_dict())

            logger.info(f"Room audit recorded: {audit_id} for room {audit.room_id}")
            return True, f"Audit created successfully | {self.time_sync_service.get_signature_stamp()}", audit_id
        except Exception as e:
            logger.error(f"Error creating audit: {e}")
            return False, f"Error creating audit: {str(e)}", None

    def complete_audit(self, audit_id: int) -> Tuple[bool, str]:
        try:
            rows = self.db.update("room_audits", {"status": "completed"}, "id = ?", (audit_id,))
            return (True, f"Audit completed | {self.time_sync_service.get_signature_stamp()}") if rows > 0 else (False, "Audit not found")
        except Exception as e:
            logger.error(f"Error completing audit: {e}")
            return False, f"Error completing audit: {str(e)}"

    def delete_audit(self, audit_id: int, admin_password: str) -> Tuple[bool, str]:
        """Delete an audit and its audit items after admin password validation."""
        if not self._can_current_user_delete_transactions():
            return False, "Only administrators can delete transaction records"

        admin_user = self._authenticate_admin(admin_password)
        if not admin_user:
            return False, "Invalid administrator password"

        existing = self.db.fetch_one("SELECT id FROM room_audits WHERE id = ?", (audit_id,))
        if not existing:
            return False, "Audit not found"

        self.db.delete("audit_items", "audit_id = ?", (audit_id,))
        self.db.delete("room_audits", "id = ?", (audit_id,))
        return True, f"Audit deleted | {self.time_sync_service.get_signature_stamp()}"

    def verify_admin_password(self, admin_password: str) -> Tuple[bool, str]:
        """Validate administrator password for protected audit actions."""
        admin_user = self._authenticate_admin(admin_password)
        if not admin_user:
            return False, "Invalid administrator password"
        return True, "Administrator verified"

    def _dict_to_audit(self, row: dict) -> RoomAudit:
        if not row:
            return None
        return RoomAudit(
            id=row.get("id"),
            room_id=row.get("room_id", 0),
            audit_date=row.get("audit_date"),
            audit_time=row.get("audit_time"),
            audited_by_user_id=row.get("audited_by_user_id", 0),
            status=row.get("status", ""),
            total_items_checked=row.get("total_items_checked"),
            missing_items_count=row.get("missing_items_count"),
            expired_items_count=row.get("expired_items_count"),
            quantity_discrepancies_count=row.get("quantity_discrepancies_count"),
            notes=row.get("notes"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _dict_to_audit_item(self, row: dict) -> AuditItem:
        if not row:
            return None
        return AuditItem(
            id=row.get("id"),
            audit_id=row.get("audit_id", 0),
            item_id=row.get("item_id", 0),
            expected_quantity=row.get("expected_quantity"),
            actual_quantity=row.get("actual_quantity"),
            quantity_discrepancy=row.get("quantity_discrepancy"),
            is_expired=bool(row.get("is_expired", 0)),
            is_missing=bool(row.get("is_missing", 0)),
            notes=row.get("notes"),
        )

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

    def _can_current_user_delete_transactions(self) -> bool:
        current_user_id = self.db.get_audit_user()
        if current_user_id is None:
            return True
        row = self.db.fetch_one("SELECT role, is_active FROM users WHERE id = ?", (current_user_id,))
        if not row or not bool(row.get("is_active", 0)):
            return False
        return (row.get("role") or "").lower() == "administrator"
