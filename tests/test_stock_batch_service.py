"""
Tests for stock batch service workflows.
"""

import tempfile
from datetime import date
from pathlib import Path

from src.database.db import get_database, init_database
from src.models.models import ClinicalRoom, StockBatch
from src.services.inventory_service import InventoryService
from src.services.room_service import ClinicalRoomService
from src.services.stock_batch_service import StockBatchService


class TestStockBatchService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_stock_batches.db"
        init_database(self.db_path)
        self.inventory_service = InventoryService()
        self.room_service = ClinicalRoomService()
        self.batch_service = StockBatchService()

        success, _, self.item_id = self.inventory_service.add_item(
            name="Amoxicillin",
            barcode="AMOX-BATCH-001",
            category="Medicines",
            current_quantity=50,
            minimum_quantity=10,
            maximum_quantity=100,
        )
        assert success

        self.room_id = self.room_service.create_room(
            ClinicalRoom(room_name="Treatment Room", room_type="Clinical")
        )
        assert self.room_id is not None

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_create_and_get_stock_batch(self):
        batch = StockBatch(
            item_id=self.item_id,
            room_id=self.room_id,
            qr_code="QR-BATCH-001",
            batch_number="BATCH-001",
            expiry_date=date(2030, 6, 30),
            quantity_available=24,
            date_received=date(2030, 1, 1),
            opened_date=date(2030, 1, 3),
            expiry_period_after_opening=30,
            storage_location="Cabinet A",
            status="Opened",
        )

        success, message, batch_id = self.batch_service.create_batch(batch)
        assert success
        assert message == "Stock batch created successfully"
        assert batch_id is not None

        stored = self.batch_service.get_batch_by_id(batch_id)
        assert stored is not None
        assert stored.batch_id == batch_id
        assert stored.product_id == self.item_id
        assert stored.room_id == self.room_id
        assert stored.qr_code == "QR-BATCH-001"
        assert stored.batch_number == "BATCH-001"
        assert stored.quantity_available == 24
        assert stored.expiry_period_after_opening == 30
        assert stored.status == "Opened"

    def test_update_stock_batch(self):
        success, _, batch_id = self.batch_service.create_batch(
            StockBatch(
                item_id=self.item_id,
                room_id=self.room_id,
                batch_number="BATCH-UPDATE",
                quantity_available=10,
                status="Active",
            )
        )
        assert success

        batch = self.batch_service.get_batch_by_id(batch_id)
        batch.quantity_available = 8
        batch.storage_location = "Shelf 2"
        batch.status = "Opened"

        success, message = self.batch_service.update_batch(batch)
        assert success
        assert message == "Stock batch updated successfully"

        stored = self.batch_service.get_batch_by_id(batch_id)
        assert stored.quantity_available == 8
        assert stored.storage_location == "Shelf 2"
        assert stored.status == "Opened"

    def test_get_batches_by_item_and_room(self):
        success, _, first_batch_id = self.batch_service.create_batch(
            StockBatch(item_id=self.item_id, room_id=self.room_id, batch_number="BATCH-A", quantity_available=5)
        )
        assert success

        success, _, second_batch_id = self.batch_service.create_batch(
            StockBatch(item_id=self.item_id, room_id=self.room_id, batch_number="BATCH-B", quantity_available=7)
        )
        assert success

        by_item = self.batch_service.get_batches_by_item(self.item_id)
        by_room = self.batch_service.get_batches_by_room(self.room_id)

        batch_ids_by_item = {batch.id for batch in by_item}
        batch_ids_by_room = {batch.id for batch in by_room}
        assert {first_batch_id, second_batch_id}.issubset(batch_ids_by_item)
        assert {first_batch_id, second_batch_id}.issubset(batch_ids_by_room)

    def test_delete_stock_batch(self):
        success, _, batch_id = self.batch_service.create_batch(
            StockBatch(item_id=self.item_id, room_id=self.room_id, batch_number="BATCH-DEL", quantity_available=1)
        )
        assert success

        success, message = self.batch_service.delete_batch(batch_id)
        assert success
        assert message == "Stock batch deleted successfully"
        assert self.batch_service.get_batch_by_id(batch_id) is None

    def test_rejects_unknown_product(self):
        success, message, batch_id = self.batch_service.create_batch(
            StockBatch(item_id=999999, room_id=self.room_id, batch_number="BAD-BATCH", quantity_available=1)
        )
        assert not success
        assert message == "Product not found"
        assert batch_id is None

    def test_get_batch_by_qr_code(self):
        success, _, batch_id = self.batch_service.create_batch(
            StockBatch(
                item_id=self.item_id,
                room_id=self.room_id,
                qr_code="QR-BATCH-LOOKUP",
                batch_number="BATCH-QR",
                quantity_available=3,
            )
        )
        assert success

        batch = self.batch_service.get_batch_by_qr_code("QR-BATCH-LOOKUP")
        assert batch is not None
        assert batch.id == batch_id
