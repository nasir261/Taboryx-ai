"""
Tests for global trigger-based audit logging.
"""

import tempfile
from pathlib import Path

from src.database.db import get_database, init_database
from src.services.auth_service import AuthenticationService
from src.services.inventory_service import InventoryService
from src.services.room_service import ClinicalRoomService
from src.services.site_service import SiteService
from src.services.stock_batch_service import StockBatchService
from src.models.models import ClinicalRoom, Site, StockBatch


class TestGlobalAuditLog:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_global_audit.db"
        init_database(self.db_path)
        self.db = get_database()
        self.auth_service = AuthenticationService()
        self.inventory_service = InventoryService()
        self.room_service = ClinicalRoomService()
        self.site_service = SiteService()
        self.stock_batch_service = StockBatchService()

        success, _, self.user_id = self.auth_service.create_user(
            username="auditactor",
            email="auditactor@example.com",
            password="password123",
            full_name="Audit Actor",
            role="administrator",
        )
        assert success

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_trigger_logs_insert_update_delete_with_current_user(self):
        self.db.set_audit_user(self.user_id)

        success, _, item_id = self.inventory_service.add_item(
            name="Audit Item",
            barcode="AUDIT-ITEM-001",
            category="Medicines",
            current_quantity=5,
            minimum_quantity=2,
            maximum_quantity=20,
        )
        assert success
        assert item_id is not None

        item = self.inventory_service.get_item_by_id(item_id)
        item.notes = "updated"
        success, _ = self.inventory_service.update_item(item)
        assert success

        success, _ = self.inventory_service.delete_item(item_id)
        assert success

        rows = self.db.fetch_all(
            """
            SELECT user_id, action, table_name, record_id, timestamp
            FROM audit_log
            WHERE table_name = 'items' AND record_id = ?
            ORDER BY id ASC
            """,
            (item_id,),
        )
        actions = [row["action"] for row in rows]
        assert actions == ["insert", "update", "delete"]
        assert all(row["user_id"] == self.user_id for row in rows)
        assert all(row["timestamp"] for row in rows)

    def test_trigger_logs_with_null_user_when_context_cleared(self):
        self.db.clear_audit_user()

        success, _, item_id = self.inventory_service.add_item(
            name="System Item",
            barcode="AUDIT-ITEM-002",
            category="Medicines",
            current_quantity=1,
            minimum_quantity=1,
            maximum_quantity=5,
        )
        assert success
        assert item_id is not None

        row = self.db.fetch_one(
            """
            SELECT user_id, action
            FROM audit_log
            WHERE table_name = 'items' AND record_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (item_id,),
        )
        assert row is not None
        assert row["action"] == "insert"
        assert row["user_id"] is None

    def test_trigger_logs_site_changes(self):
        self.db.set_audit_user(self.user_id)

        success, _, site_id = self.site_service.create_site(Site(site_name="Audit Site", site_code="AS1"))
        assert success
        site = self.site_service.get_site_by_id(site_id)
        site.is_active = False
        success, _ = self.site_service.update_site(site)
        assert success
        success, _ = self.site_service.delete_site(site_id)
        assert success

        rows = self.db.fetch_all(
            """
            SELECT user_id, action, table_name, record_id, timestamp
            FROM audit_log
            WHERE table_name = 'sites' AND record_id = ?
            ORDER BY id ASC
            """,
            (site_id,),
        )
        actions = [row["action"] for row in rows]
        assert actions == ["insert", "update", "delete"]
        assert all(row["user_id"] == self.user_id for row in rows)
        assert all(row["timestamp"] for row in rows)

    def test_trigger_logs_stock_batch_changes(self):
        self.db.set_audit_user(self.user_id)

        success, _, item_id = self.inventory_service.add_item(
            name="Batch Audit Item",
            barcode="AUDIT-BATCH-001",
            category="Medicines",
            current_quantity=10,
            minimum_quantity=2,
            maximum_quantity=20,
        )
        assert success

        room_id = self.room_service.create_room(ClinicalRoom(room_name="Audit Batch Room"))
        assert room_id is not None

        success, _, batch_id = self.stock_batch_service.create_batch(
            StockBatch(
                item_id=item_id,
                room_id=room_id,
                batch_number="BATCH-AUDIT-01",
                quantity_available=6,
                status="Active",
            )
        )
        assert success

        batch = self.stock_batch_service.get_batch_by_id(batch_id)
        batch.status = "Opened"
        success, _ = self.stock_batch_service.update_batch(batch)
        assert success

        success, _ = self.stock_batch_service.delete_batch(batch_id)
        assert success

        rows = self.db.fetch_all(
            """
            SELECT user_id, action, table_name, record_id, timestamp
            FROM audit_log
            WHERE table_name = 'stock_batches' AND record_id = ?
            ORDER BY id ASC
            """,
            (batch_id,),
        )
        actions = [row["action"] for row in rows]
        assert actions == ["insert", "update", "delete"]
        assert all(row["user_id"] == self.user_id for row in rows)
        assert all(row["timestamp"] for row in rows)
