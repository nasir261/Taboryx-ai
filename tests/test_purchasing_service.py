"""
Tests for purchasing recommendation workflows.
"""

import tempfile
from datetime import date, timedelta
from pathlib import Path

from src.database.db import get_database, init_database
from src.models.models import StockMovement, Supplier
from src.services.auth_service import AuthenticationService
from src.services.inventory_service import InventoryService
from src.services.purchasing_service import PurchasingService
from src.services.supplier_service import SupplierService


class TestPurchasingService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_purchasing.db"
        init_database(self.db_path)

        self.auth_service = AuthenticationService()
        self.inventory_service = InventoryService()
        self.supplier_service = SupplierService()
        self.purchasing_service = PurchasingService()

        success, _, user_id = self.auth_service.create_user(
            username="purchaser",
            email="purchaser@example.com",
            password="password123",
            full_name="Purchasing User",
            role="administrator",
        )
        assert success
        self.user_id = user_id

        supplier = Supplier(supplier_name="MediSupply", lead_time_days=12)
        success, _, supplier_id = self.supplier_service.create_supplier(supplier)
        assert success
        self.supplier_id = supplier_id

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_recommendations_prioritize_low_stock_item(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Paracetamol",
            barcode="PCM-001",
            category="Medicines",
            supplier_id=self.supplier_id,
            current_quantity=8,
            minimum_quantity=10,
            maximum_quantity=100,
        )
        assert success

        for days_ago, issued_qty in [(5, -6), (15, -5), (40, -4), (70, -7)]:
            movement = StockMovement(
                item_id=item_id,
                movement_type="issued",
                quantity_change=issued_qty,
                user_id=self.user_id,
                movement_date=date.today() - timedelta(days=days_ago),
            )
            self.inventory_service.log_stock_movement(movement)

        recommendations = self.purchasing_service.get_purchase_recommendations()
        match = [rec for rec in recommendations if rec["item_id"] == item_id]
        assert len(match) == 1
        assert match[0]["recommended_qty"] > 0
        assert match[0]["action"] in {"Order now", "Order soon"}
        assert match[0]["supplier_name"] == "MediSupply"

    def test_unassigned_supplier_defaults_to_unassigned(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Ibuprofen",
            barcode="IBU-001",
            category="Medicines",
            current_quantity=50,
            minimum_quantity=10,
            maximum_quantity=100,
        )
        assert success

        recommendations = self.purchasing_service.get_purchase_recommendations()
        match = [rec for rec in recommendations if rec["item_id"] == item_id]
        assert len(match) == 1
        assert match[0]["supplier_name"] == "Unassigned"

    def test_create_purchase_order_for_supplier_item(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Amoxicillin",
            barcode="AMX-001",
            category="Medicines",
            supplier_id=self.supplier_id,
            current_quantity=5,
            minimum_quantity=20,
            maximum_quantity=80,
            purchase_price=1.2,
        )
        assert success

        success, message, order_id = self.purchasing_service.create_purchase_order_for_item(
            item_id=item_id,
            quantity=30,
            created_by_user_id=self.user_id,
            notes="Auto-generated in test",
        )
        assert success
        assert order_id is not None

        db = get_database()
        order = db.fetch_one("SELECT * FROM purchase_orders WHERE id = ?", (order_id,))
        assert order is not None
        assert order["supplier_id"] == self.supplier_id
        assert order["status"] == "pending"

        po_item = db.fetch_one("SELECT * FROM purchase_order_items WHERE purchase_order_id = ?", (order_id,))
        assert po_item is not None
        assert po_item["item_id"] == item_id
        assert po_item["quantity_ordered"] == 30

    def test_create_purchase_order_rejects_unassigned_supplier(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Gloves",
            barcode="GLV-001",
            category="PPE",
            current_quantity=5,
            minimum_quantity=20,
            maximum_quantity=80,
        )
        assert success

        success, message, order_id = self.purchasing_service.create_purchase_order_for_item(
            item_id=item_id,
            quantity=15,
            created_by_user_id=self.user_id,
        )
        assert not success
        assert order_id is None
        assert message == "Item has no assigned supplier"

    def test_update_settings_changes_recommended_quantity(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Cefalexin",
            barcode="CEF-001",
            category="Medicines",
            supplier_id=self.supplier_id,
            current_quantity=3,
            minimum_quantity=10,
            maximum_quantity=60,
            purchase_price=1.0,
        )
        assert success

        baseline = [rec for rec in self.purchasing_service.get_purchase_recommendations() if rec["item_id"] == item_id][0]
        baseline_qty = baseline["recommended_qty"]

        success, message = self.purchasing_service.update_recommendation_settings(
            lookback_days=90, safety_stock_factor=1.2, min_safety_stock=15, budget_limit=None
        )
        assert success
        assert message == "Purchasing settings saved"

        updated = [rec for rec in self.purchasing_service.get_purchase_recommendations() if rec["item_id"] == item_id][0]
        assert updated["recommended_qty"] >= baseline_qty
        assert "recommended order quantity" in updated["reason"]

    def test_budget_limit_changes_action_to_review_budget(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Insulin",
            barcode="INS-001",
            category="Medicines",
            supplier_id=self.supplier_id,
            current_quantity=1,
            minimum_quantity=10,
            maximum_quantity=120,
            purchase_price=25.0,
        )
        assert success

        success, _ = self.purchasing_service.update_recommendation_settings(
            lookback_days=90, safety_stock_factor=0.5, min_safety_stock=5, budget_limit=100.0
        )
        assert success

        match = [rec for rec in self.purchasing_service.get_purchase_recommendations() if rec["item_id"] == item_id]
        assert len(match) == 1
        assert match[0]["action"] == "Review budget"
        assert match[0]["recommended_qty"] == 4
        assert "budget cap" in match[0]["reason"]

    def test_item_level_lead_time_and_safety_stock_override_supplier_defaults(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Meropenem",
            barcode="MER-001",
            category="Medicines",
            supplier_id=self.supplier_id,
            current_quantity=5,
            minimum_quantity=10,
            maximum_quantity=20,
            lead_time_days=20,
            safety_stock_quantity=25,
        )
        assert success

        recommendations = self.purchasing_service.get_purchase_recommendations()
        match = [rec for rec in recommendations if rec["item_id"] == item_id]
        assert len(match) == 1
        assert match[0]["lead_time_days"] == 20
        assert match[0]["reorder_point"] >= 25
