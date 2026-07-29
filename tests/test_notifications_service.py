"""
Tests for notifications service.
"""

import tempfile
from datetime import date, timedelta
from pathlib import Path

from src.database.db import get_database, init_database
from src.models.models import ClinicalRoom, Supplier
from src.services.auth_service import AuthenticationService
from src.services.inventory_service import InventoryService
from src.services.notifications_service import NotificationsService
from src.services.purchasing_service import PurchasingService
from src.services.room_service import ClinicalRoomService
from src.services.supplier_service import SupplierService


class TestNotificationsService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_notifications.db"
        init_database(self.db_path)
        self.db = get_database()

        self.auth_service = AuthenticationService()
        self.inventory_service = InventoryService()
        self.room_service = ClinicalRoomService()
        self.supplier_service = SupplierService()
        self.purchasing_service = PurchasingService()
        self.notifications_service = NotificationsService()

        success, _, self.user_id = self.auth_service.create_user(
            username="notifyadmin",
            email="notifyadmin@example.com",
            password="password123",
            full_name="Notify Admin",
            role="administrator",
        )
        assert success

        supplier = Supplier(supplier_name="Alert Supplier", lead_time_days=7)
        success, _, self.supplier_id = self.supplier_service.create_supplier(supplier)
        assert success

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_notifications_include_inventory_and_po_alerts(self):
        success, _, low_item_id = self.inventory_service.add_item(
            name="Low Stock Item",
            barcode="NOTIFY-LOW-001",
            category="Medicines",
            supplier_id=self.supplier_id,
            current_quantity=2,
            minimum_quantity=10,
            maximum_quantity=60,
        )
        assert success

        success, _, expired_item_id = self.inventory_service.add_item(
            name="Expired Item",
            barcode="NOTIFY-EXP-001",
            category="Medicines",
            supplier_id=self.supplier_id,
            expiry_date=date.today() - timedelta(days=1),
            current_quantity=5,
            minimum_quantity=2,
            maximum_quantity=20,
        )
        assert success

        success, _, _ = self.purchasing_service.create_purchase_order_for_item(
            item_id=low_item_id, quantity=20, created_by_user_id=self.user_id
        )
        assert success

        notifications = self.notifications_service.get_notifications()
        types = {row["type"] for row in notifications}
        assert "low_stock" in types
        assert "expiry" in types
        assert "purchase_order" in types

        low = [row for row in notifications if row["type"] == "low_stock" and f"Item #{low_item_id}" == row["reference"]]
        assert len(low) == 1
        expired = [
            row for row in notifications if row["type"] == "expiry" and f"Item #{expired_item_id}" == row["reference"]
        ]
        assert len(expired) >= 1

    def test_notifications_include_overdue_audit_for_room(self):
        room = ClinicalRoom(room_name="Overdue Room", room_type="Treatment")
        room_id = self.room_service.create_room(room)
        assert room_id is not None

        self.db.insert(
            "room_audits",
            {
                "room_id": room_id,
                "audit_date": date.today() - timedelta(days=45),
                "audit_time": "09:00:00",
                "audited_by_user_id": self.user_id,
                "status": "completed",
                "total_items_checked": 1,
            },
        )

        notifications = self.notifications_service.get_notifications(audit_overdue_days=30)
        overdue = [row for row in notifications if row["type"] == "audit_overdue" and row["reference"] == f"Room #{room_id}"]
        assert len(overdue) == 1
        assert overdue[0]["severity"] == "warning"
