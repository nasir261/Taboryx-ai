"""
Tests for barcode and QR scan recognition.
"""

import tempfile
from pathlib import Path

from src.database.db import get_database, init_database
from src.models.models import ClinicalRoom, StockBatch
from src.services.inventory_service import InventoryService
from src.services.room_service import ClinicalRoomService
from src.services.scan_recognition_service import ScanRecognitionService
from src.services.stock_batch_service import StockBatchService


class TestScanRecognitionService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_scan_recognition.db"
        init_database(self.db_path)
        self.inventory_service = InventoryService()
        self.room_service = ClinicalRoomService()
        self.stock_batch_service = StockBatchService()
        self.scan_recognition_service = ScanRecognitionService()

        success, _, self.item_id = self.inventory_service.add_item(
            name="Morphine",
            barcode="ITEM-BAR-001",
            qr_code="ITEM-QR-001",
            category="Medicines",
            current_quantity=25,
            minimum_quantity=5,
            maximum_quantity=50,
        )
        assert success

        self.room_id = self.room_service.create_room(ClinicalRoom(room_name="Secure Drug Room"))
        assert self.room_id is not None

        success, _, self.batch_id = self.stock_batch_service.create_batch(
            StockBatch(
                item_id=self.item_id,
                room_id=self.room_id,
                qr_code="BATCH-QR-001",
                batch_number="BATCH-NO-001",
                quantity_available=10,
                status="Active",
            )
        )
        assert success

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_recognizes_item_by_qr_code(self):
        result = self.scan_recognition_service.recognize("ITEM-QR-001")
        assert result["found"] is True
        assert result["entity_type"] == "item"
        assert result["matched_by"] == "item_qr_code"
        assert result["item"].id == self.item_id
        assert result["batch"] is None

    def test_recognizes_batch_by_qr_code(self):
        result = self.scan_recognition_service.recognize("BATCH-QR-001")
        assert result["found"] is True
        assert result["entity_type"] == "batch"
        assert result["matched_by"] == "batch_qr_code"
        assert result["batch"].id == self.batch_id
        assert result["item"].id == self.item_id

    def test_recognizes_structured_batch_qr_payload(self):
        result = self.scan_recognition_service.recognize(f"batch_id={self.batch_id};product_id={self.item_id}")
        assert result["found"] is True
        assert result["entity_type"] == "batch"
        assert result["matched_by"] == "structured_qr_payload"
        assert result["batch"].id == self.batch_id

    def test_recognizes_barcode_as_item(self):
        result = self.scan_recognition_service.recognize("ITEM-BAR-001")
        assert result["found"] is True
        assert result["entity_type"] == "item"
        assert result["matched_by"] == "barcode"
        assert result["item"].id == self.item_id

    def test_recognizes_batch_number_fallback(self):
        result = self.scan_recognition_service.recognize("BATCH-NO-001")
        assert result["found"] is True
        assert result["entity_type"] == "batch"
        assert result["matched_by"] == "batch_number"
        assert result["batch"].id == self.batch_id

    def test_returns_not_found_for_unknown_code(self):
        result = self.scan_recognition_service.recognize("UNKNOWN-CODE")
        assert result["found"] is False
        assert result["entity_type"] is None
        assert result["item"] is None
        assert result["batch"] is None
