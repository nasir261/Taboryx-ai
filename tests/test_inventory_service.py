"""
Tests for inventory service delete authorization.
"""

import tempfile
from pathlib import Path

from src.database.db import get_database, init_database
from src.services.auth_service import AuthenticationService
from src.services.inventory_service import InventoryService
from src.services.room_service import ClinicalRoomService
from src.services.stock_batch_service import StockBatchService
from src.models.models import ClinicalRoom, StockBatch, StockMovement


class TestInventoryService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_inventory_service.db"
        init_database(self.db_path)

        self.auth_service = AuthenticationService()
        self.inventory_service = InventoryService()
        self.room_service = ClinicalRoomService()
        self.stock_batch_service = StockBatchService()

        success, _, self.user_id = self.auth_service.create_user(
            username="inventoryadmin",
            email="inventoryadmin@example.com",
            password="password123",
            full_name="Inventory Admin",
            role="administrator",
        )
        assert success

        self.room = ClinicalRoom(room_name="Inventory Test Room", room_type="Clinical")
        self.room.id = self.room_service.create_room(self.room)

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_delete_item_requires_admin_password(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Delete Test Item",
            barcode="DEL-INV-001",
            category="Medicines",
            current_quantity=10,
            minimum_quantity=2,
            maximum_quantity=30,
        )
        assert success
        assert item_id is not None

        success, message = self.inventory_service.delete_item_with_admin_password(item_id, "wrong-password")
        assert not success
        assert message == "Invalid administrator password"
        assert self.inventory_service.get_item_by_id(item_id) is not None

        success, message = self.inventory_service.delete_item_with_admin_password(item_id, "password123")
        assert success
        assert message == "Item deleted successfully"
        assert self.inventory_service.get_item_by_id(item_id) is None

    def test_add_and_delete_item_attachment(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Attachment Item",
            barcode="ATT-INV-001",
            category="Medicines",
            current_quantity=5,
            minimum_quantity=1,
            maximum_quantity=20,
        )
        assert success

        source_file = Path(self.temp_dir.name) / "safety_doc.pdf"
        source_file.write_text("test attachment", encoding="utf-8")

        success, message, attachment_id = self.inventory_service.add_item_attachment(item_id, str(source_file))
        assert success
        assert message == "Attachment added"
        assert attachment_id is not None

        attachments = self.inventory_service.get_item_attachments(item_id)
        assert len(attachments) == 1
        managed_path = Path(attachments[0]["file_path"])
        assert managed_path.exists()
        assert attachments[0]["file_type"] == "pdf"

        success, message = self.inventory_service.delete_item_attachment(attachment_id)
        assert success
        assert message == "Attachment deleted"
        assert not managed_path.exists()
        assert len(self.inventory_service.get_item_attachments(item_id)) == 0

    def test_delete_item_also_removes_item_attachments(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Attachment Cleanup Item",
            barcode="ATT-INV-002",
            category="Medicines",
            current_quantity=5,
            minimum_quantity=1,
            maximum_quantity=20,
        )
        assert success

        source_file = Path(self.temp_dir.name) / "manual.txt"
        source_file.write_text("manual data", encoding="utf-8")
        success, _, _ = self.inventory_service.add_item_attachment(item_id, str(source_file))
        assert success

        attachments = self.inventory_service.get_item_attachments(item_id)
        assert len(attachments) == 1
        managed_path = Path(attachments[0]["file_path"])
        assert managed_path.exists()

        success, message = self.inventory_service.delete_item(item_id)
        assert success
        assert message == "Item deleted successfully"
        assert not managed_path.exists()
        assert len(self.inventory_service.get_item_attachments(item_id)) == 0

    def test_get_inventory_value_handles_string_numeric_fields(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Valued Item",
            barcode="VAL-INV-001",
            category="Medicines",
            current_quantity=4,
            minimum_quantity=1,
            maximum_quantity=20,
            purchase_price="12.50",
        )
        assert success

        assert self.inventory_service.get_item_stock_value(item_id) == 50.0
        assert self.inventory_service.get_total_inventory_value() == 50.0

    def test_requires_movement_confirmation_for_high_risk_actions(self):
        assert self.inventory_service.requires_movement_confirmation("DISPOSED", -1)
        assert self.inventory_service.requires_movement_confirmation("TRANSFERRED", 5)
        assert self.inventory_service.requires_movement_confirmation("ADJUSTED", 20)
        assert not self.inventory_service.requires_movement_confirmation("ADJUSTED", 5)
        assert not self.inventory_service.requires_movement_confirmation("ISSUED", -20)

    def test_log_stock_movement_persists_transaction_fields_and_updates_batch(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Tracked Item",
            barcode="TRX-INV-001",
            category="Medicines",
            current_quantity=20,
            minimum_quantity=2,
            maximum_quantity=30,
            clinical_room=self.room.room_name,
        )
        assert success

        success, _, batch_id = self.stock_batch_service.create_batch(
            StockBatch(
                item_id=item_id,
                room_id=self.room.id,
                batch_number="TRX-BATCH-1",
                quantity_available=12,
                status="Active",
            )
        )
        assert success

        movement = StockMovement(
            item_id=item_id,
            movement_type="USED",
            transaction_quantity=4,
            quantity_change=-4,
            batch_id=batch_id,
            room_id=self.room.id,
            user_id=self.user_id,
            reason="Patient use",
        )
        success, _, movement_id = self.inventory_service.log_stock_movement(movement)
        assert success
        assert movement_id is not None

        stored_movement = self.inventory_service.get_stock_movements(item_id=item_id, limit=1)[0]
        assert stored_movement.transaction_id == movement_id
        assert stored_movement.product_id == item_id
        assert stored_movement.batch_id == batch_id
        assert stored_movement.room_id == self.room.id
        assert stored_movement.transaction_type == "USED"
        assert stored_movement.quantity == 4
        assert stored_movement.previous_quantity == 20
        assert stored_movement.new_quantity == 16

        updated_item = self.inventory_service.get_item_by_id(item_id)
        assert updated_item.current_quantity == 16

        updated_batch = self.stock_batch_service.get_batch_by_id(batch_id)
        assert updated_batch.quantity_available == 8

    def test_update_item_quantity_creates_adjustment_transaction(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Editable Quantity Item",
            barcode="TRX-INV-002",
            category="Medicines",
            current_quantity=10,
            minimum_quantity=2,
            maximum_quantity=30,
            clinical_room=self.room.room_name,
        )
        assert success

        db = get_database()
        db.set_audit_user(self.user_id)
        item = self.inventory_service.get_item_by_id(item_id)
        item.current_quantity = 15
        success, message = self.inventory_service.update_item(item)
        assert success
        assert message == "Item updated successfully"

        movements = self.inventory_service.get_stock_movements(item_id=item_id, limit=10)
        assert len(movements) == 1
        assert movements[0].transaction_type == "ADJUSTED"
        assert movements[0].quantity == 5
        assert movements[0].previous_quantity == 10
        assert movements[0].new_quantity == 15
