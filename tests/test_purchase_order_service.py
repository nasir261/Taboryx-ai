"""
Tests for purchase order list/filter/receive workflows.
"""

import tempfile
from pathlib import Path

from src.database.db import get_database, init_database
from src.models.models import Supplier
from src.services.auth_service import AuthenticationService
from src.services.inventory_service import InventoryService
from src.services.purchase_order_service import PurchaseOrderService
from src.services.purchasing_service import PurchasingService
from src.services.supplier_service import SupplierService


class TestPurchaseOrderService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_purchase_orders.db"
        init_database(self.db_path)

        self.auth_service = AuthenticationService()
        self.inventory_service = InventoryService()
        self.supplier_service = SupplierService()
        self.purchasing_service = PurchasingService()
        self.purchase_order_service = PurchaseOrderService()

        success, _, self.user_id = self.auth_service.create_user(
            username="poadmin",
            email="poadmin@example.com",
            password="password123",
            full_name="PO Admin",
            role="administrator",
        )
        assert success
        success, _, self.nurse_user_id = self.auth_service.create_user(
            username="ponurse",
            email="ponurse@example.com",
            password="password123",
            full_name="PO Nurse",
            role="nurse",
        )
        assert success

        supplier = Supplier(supplier_name="PO Supplier", lead_time_days=5)
        success, _, self.supplier_id = self.supplier_service.create_supplier(supplier)
        assert success

        success, _, self.item_id = self.inventory_service.add_item(
            name="Test PO Item",
            barcode="PO-ITEM-001",
            category="Medicines",
            supplier_id=self.supplier_id,
            current_quantity=4,
            minimum_quantity=10,
            maximum_quantity=30,
            purchase_price=2.0,
        )
        assert success

        success, _, self.order_id = self.purchasing_service.create_purchase_order_for_item(
            item_id=self.item_id, quantity=12, created_by_user_id=self.user_id
        )
        assert success

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_list_orders_and_filter(self):
        all_orders = self.purchase_order_service.get_purchase_orders()
        assert len(all_orders) == 1
        assert all_orders[0]["status"] == "pending"

        pending_orders = self.purchase_order_service.get_purchase_orders(status="pending")
        assert len(pending_orders) == 1

        received_orders = self.purchase_order_service.get_purchase_orders(status="received")
        assert len(received_orders) == 0

    def test_mark_received_updates_status_and_line_receipts(self):
        success, message = self.purchase_order_service.mark_received(self.order_id)
        assert success

        db = get_database()
        order = db.fetch_one("SELECT status, actual_delivery_date FROM purchase_orders WHERE id = ?", (self.order_id,))
        assert order["status"] == "received"
        assert order["actual_delivery_date"] is not None

        po_item = db.fetch_one(
            "SELECT quantity_ordered, quantity_received FROM purchase_order_items WHERE purchase_order_id = ?",
            (self.order_id,),
        )
        assert po_item["quantity_received"] == po_item["quantity_ordered"]

    def test_get_purchase_order_items_returns_item_metadata(self):
        items = self.purchase_order_service.get_purchase_order_items(self.order_id)
        assert len(items) == 1
        assert items[0]["item_name"] == "Test PO Item"
        assert items[0]["barcode"] == "PO-ITEM-001"

    def test_update_purchase_order_item_requires_admin_password(self):
        items = self.purchase_order_service.get_purchase_order_items(self.order_id)
        po_item_id = items[0]["id"]

        success, message = self.purchase_order_service.update_purchase_order_item(
            po_item_id, quantity_ordered=20, admin_password="wrong-password"
        )
        assert not success
        assert message == "Invalid administrator password"

        success, message = self.purchase_order_service.update_purchase_order_item(
            po_item_id, quantity_ordered=20, admin_password="password123"
        )
        assert success

        db = get_database()
        updated_item = db.fetch_one("SELECT quantity_ordered, line_total FROM purchase_order_items WHERE id = ?", (po_item_id,))
        assert updated_item["quantity_ordered"] == 20
        assert float(updated_item["line_total"]) == 40.0

        trail = self.purchase_order_service.get_purchase_order_item_audit(self.order_id)
        assert len(trail) == 1
        assert trail[0]["action"] == "update"
        assert trail[0]["changed_by_username"] == "poadmin"
        assert '"quantity_ordered": 20' in trail[0]["new_values"]

    def test_delete_purchase_order_item_requires_admin_password(self):
        items = self.purchase_order_service.get_purchase_order_items(self.order_id)
        po_item_id = items[0]["id"]

        success, message = self.purchase_order_service.delete_purchase_order_item(
            po_item_id, admin_password="wrong-password"
        )
        assert not success
        assert message == "Invalid administrator password"

        success, message = self.purchase_order_service.delete_purchase_order_item(
            po_item_id, admin_password="password123"
        )
        assert success

        db = get_database()
        deleted = db.fetch_one("SELECT id FROM purchase_order_items WHERE id = ?", (po_item_id,))
        assert deleted is None

        trail = self.purchase_order_service.get_purchase_order_item_audit(self.order_id)
        assert len(trail) == 1
        assert trail[0]["action"] == "delete"
        assert trail[0]["changed_by_username"] == "poadmin"
        assert trail[0]["new_values"] == "{}"

    def test_cannot_amend_items_after_order_received(self):
        items = self.purchase_order_service.get_purchase_order_items(self.order_id)
        po_item_id = items[0]["id"]

        success, _ = self.purchase_order_service.mark_received(self.order_id)
        assert success

        success, message = self.purchase_order_service.update_purchase_order_item(
            po_item_id, quantity_ordered=10, admin_password="password123"
        )
        assert not success
        assert message == "Cannot amend items for a received purchase order"

    def test_export_purchase_order_item_audit_csv(self):
        items = self.purchase_order_service.get_purchase_order_items(self.order_id)
        po_item_id = items[0]["id"]

        success, _ = self.purchase_order_service.update_purchase_order_item(
            po_item_id, quantity_ordered=18, admin_password="password123"
        )
        assert success

        export_path = Path(self.temp_dir.name) / "po_audit.csv"
        success, message = self.purchase_order_service.export_purchase_order_item_audit_csv(
            self.order_id, export_path
        )
        assert success
        assert export_path.exists()
        content = export_path.read_text(encoding="utf-8").splitlines()
        assert content[0].startswith("Generated at,")
        assert content[2].startswith("audit_id,purchase_order_id,purchase_order_item_id,item_id,action")
        assert any(",update," in line for line in content)

    def test_delete_purchase_order_requires_admin_password(self):
        success, message = self.purchase_order_service.delete_purchase_order(
            self.order_id, admin_password="wrong-password"
        )
        assert not success
        assert message == "Invalid administrator password"

    def test_delete_purchase_order_removes_order_and_items(self):
        success, message = self.purchase_order_service.delete_purchase_order(
            self.order_id, admin_password="password123"
        )
        assert success
        assert message.startswith("Purchase order deleted | Signed at ")

        db = get_database()
        order = db.fetch_one("SELECT id FROM purchase_orders WHERE id = ?", (self.order_id,))
        assert order is None
        items = db.fetch_all("SELECT id FROM purchase_order_items WHERE purchase_order_id = ?", (self.order_id,))
        assert len(items) == 0

    def test_non_admin_user_cannot_delete_purchase_order(self):
        db = get_database()
        db.set_audit_user(self.nurse_user_id)

        success, message = self.purchase_order_service.delete_purchase_order(
            self.order_id, admin_password="password123"
        )
        assert not success
        assert message == "Only administrators can delete transaction records"

    def test_cannot_delete_received_purchase_order(self):
        success, _ = self.purchase_order_service.mark_received(self.order_id)
        assert success

        success, message = self.purchase_order_service.delete_purchase_order(
            self.order_id, admin_password="password123"
        )
        assert not success
        assert message == "Cannot delete a received purchase order"

    def test_non_admin_user_cannot_delete_purchase_order_item(self):
        items = self.purchase_order_service.get_purchase_order_items(self.order_id)
        po_item_id = items[0]["id"]
        db = get_database()
        db.set_audit_user(self.nurse_user_id)

        success, message = self.purchase_order_service.delete_purchase_order_item(
            po_item_id, admin_password="password123"
        )
        assert not success
        assert message == "Only administrators can delete transaction records"
