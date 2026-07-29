"""
Tests for AI chat assistant query handling.
"""

import tempfile
from datetime import date, timedelta
from pathlib import Path

from src.database.db import get_database, init_database
from src.models.models import StockMovement, Supplier
from src.services.ai_chat_service import AIChatService
from src.services.auth_service import AuthenticationService
from src.services.inventory_service import InventoryService
from src.services.purchasing_service import PurchasingService
from src.services.supplier_service import SupplierService


class TestAIChatService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_ai_chat.db"
        init_database(self.db_path)

        self.auth_service = AuthenticationService()
        self.inventory_service = InventoryService()
        self.supplier_service = SupplierService()
        self.purchasing_service = PurchasingService()
        self.ai_chat = AIChatService()

        success, _, self.user_id = self.auth_service.create_user(
            username="chatadmin",
            email="chatadmin@example.com",
            password="password123",
            full_name="Chat Admin",
            role="administrator",
        )
        assert success

        success, _, supplier_id = self.supplier_service.create_supplier(Supplier(supplier_name="ChatSupplier", lead_time_days=7))
        assert success
        self.supplier_id = supplier_id

        self._seed_inventory_and_movements()

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def _seed_inventory_and_movements(self):
        ok, _, insulin_id = self.inventory_service.add_item(
            name="Insulin",
            barcode="CHAT-INS-001",
            category="Medicines",
            supplier_id=self.supplier_id,
            current_quantity=20,
            minimum_quantity=10,
            maximum_quantity=80,
            expiry_date=date.today() - timedelta(days=1),
        )
        assert ok
        self.insulin_id = insulin_id

        ok, _, glove_id = self.inventory_service.add_item(
            name="Gloves",
            barcode="CHAT-GLV-001",
            category="PPE",
            supplier_id=self.supplier_id,
            current_quantity=100,
            minimum_quantity=20,
            maximum_quantity=300,
        )
        assert ok
        self.glove_id = glove_id

        ok, _, syringe_id = self.inventory_service.add_item(
            name="Syringes",
            barcode="CHAT-SYR-001",
            category="Needles",
            supplier_id=self.supplier_id,
            current_quantity=40,
            minimum_quantity=15,
            maximum_quantity=150,
        )
        assert ok
        self.syringe_id = syringe_id

        for area, qty in [("GP Room 1", -12), ("GP Room 1", -5), ("Nurse Room A", -8)]:
            movement = StockMovement(
                item_id=self.glove_id,
                movement_type="issued",
                quantity_change=qty,
                user_id=self.user_id,
                movement_date=date.today() - timedelta(days=2),
                patient_area=area,
            )
            success, _, _ = self.inventory_service.log_stock_movement(movement)
            assert success

        movement = StockMovement(
            item_id=self.syringe_id,
            movement_type="issued",
            quantity_change=-9,
            user_id=self.user_id,
            movement_date=date.today() - timedelta(days=1),
            patient_area="Treatment Room",
        )
        success, _, _ = self.inventory_service.log_stock_movement(movement)
        assert success

    def test_show_expired_insulin(self):
        result = self.ai_chat.ask("Show expired insulin")
        assert "Found" in result["answer"]
        assert any("Insulin" in str(row.get("item")) for row in result["rows"])

    def test_room_uses_most_gloves(self):
        result = self.ai_chat.ask("Which room uses the most gloves?")
        assert "uses the most gloves" in result["answer"].lower()
        assert "GP Room 1" in result["answer"]

    def test_syringes_used_this_month(self):
        result = self.ai_chat.ask("How many syringes were used this month?")
        assert "used this month" in result["answer"].lower()
        assert result["rows"][0]["used_this_month"] >= 9

    def test_items_expire_next_week(self):
        result = self.ai_chat.ask("Which items expire next week?")
        assert isinstance(result["rows"], list)

    def test_generate_purchasing_report(self):
        result = self.ai_chat.ask("Generate purchasing report")
        assert "purchasing summary" in result["answer"].lower()
