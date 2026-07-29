"""
Unit tests for ReportingService
"""

import tempfile
from pathlib import Path
from datetime import date, datetime

from src.database.db import get_database, init_database
from src.services.inventory_service import InventoryService
from src.services.reporting_service import ReportingService
from src.models.models import StockMovement


class TestReportingService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_reports.db"
        init_database(self.db_path)
        self.inventory_service = InventoryService()
        self.reporting_service = ReportingService()

        self.inventory_service.add_item(
            name="Test Medicine",
            barcode="TEST123",
            category="Medicines",
            current_quantity=20,
            minimum_quantity=5,
            maximum_quantity=50,
            temperature_requirements="Room Temperature",
            controlled_drug=False,
            requires_fridge=False,
        )

        item = self.inventory_service.get_item_by_barcode("TEST123")
        movement = StockMovement(
            item_id=item.id,
            movement_type="issued",
            quantity_change=-5,
            user_id=1,
            movement_date=date.today(),
            movement_time=datetime.now().time(),
            reason="Medication issued",
            patient_area="GP Room 1",
            notes="Sample movement",
        )
        self.inventory_service.log_stock_movement(movement)

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_generate_inventory_csv(self):
        output_path = Path(self.temp_dir.name) / "inventory.csv"
        success, message = self.reporting_service.generate_inventory_csv(output_path)
        assert success
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8").splitlines()
        assert content[0].startswith("Generated at,")
        assert content[2].startswith("ID,Name,Product Code,Barcode")

    def test_generate_inventory_excel(self):
        output_path = Path(self.temp_dir.name) / "inventory.xlsx"
        success, message = self.reporting_service.generate_inventory_excel(output_path)
        assert success
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_inventory_pdf(self):
        output_path = Path(self.temp_dir.name) / "inventory.pdf"
        success, message = self.reporting_service.generate_inventory_pdf(output_path)
        assert success
        assert output_path.exists()
        assert output_path.read_bytes()[:4] == b"%PDF"

    def test_generate_movements_csv(self):
        output_path = Path(self.temp_dir.name) / "movements.csv"
        success, message = self.reporting_service.generate_movements_csv(output_path)
        assert success
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8").splitlines()
        assert content[0].startswith("Generated at,")
        assert content[2].startswith("Transaction ID,Product ID,Batch ID,Room ID,Transaction Type")

    def test_generate_movements_excel(self):
        output_path = Path(self.temp_dir.name) / "movements.xlsx"
        success, message = self.reporting_service.generate_movements_excel(output_path)
        assert success
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_movements_pdf(self):
        output_path = Path(self.temp_dir.name) / "movements.pdf"
        success, message = self.reporting_service.generate_movements_pdf(output_path)
        assert success
        assert output_path.exists()
        assert output_path.read_bytes()[:4] == b"%PDF"
