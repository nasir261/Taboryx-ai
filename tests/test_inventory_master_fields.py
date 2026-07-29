"""
Tests for additional inventory master fields.
"""

import tempfile
from pathlib import Path

from src.database.db import get_database, init_database
from src.services.inventory_service import InventoryService
from src.services.supplier_service import SupplierService
from src.models.models import Supplier


class TestInventoryMasterFields:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_inventory_master_fields.db"
        init_database(self.db_path)
        self.inventory_service = InventoryService()
        self.supplier_service = SupplierService()

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_item_round_trip_with_additional_master_fields(self):
        success, _, supplier_id = self.supplier_service.create_supplier(
            Supplier(supplier_name="Master Field Supplier", lead_time_days=9)
        )
        assert success

        success, message, item_id = self.inventory_service.add_item(
            name="Ceftriaxone",
            barcode="INV-MASTER-001",
            qr_code="QR-CEF-001",
            product_code="MED-CEF-001",
            category="Medicines",
            manufacturer="Acme Pharma",
            supplier_id=supplier_id,
            supplier_product_code="SUP-CEF-9",
            unit_of_measurement="vial",
            minimum_quantity=10,
            maximum_quantity=30,
            lead_time_days=9,
            safety_stock_quantity=6,
            is_active=False,
        )
        assert success
        assert message == "Item created successfully"
        assert item_id is not None

        item = self.inventory_service.get_item_by_id(item_id)
        assert item is not None
        assert item.product_id == item_id
        assert item.qr_code == "QR-CEF-001"
        assert item.product_code == "MED-CEF-001"
        assert item.supplier_product_code == "SUP-CEF-9"
        assert item.unit_of_measurement == "vial"
        assert item.minimum_stock_level == 10
        assert item.target_stock_level == 30
        assert item.lead_time_days == 9
        assert item.safety_stock_quantity == 6
        assert item.active_status is False
