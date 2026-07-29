"""
Purchase Order Service
Handles retrieval and state updates for purchase orders.
"""

import logging
import json
import csv
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.database.db import get_database
from src.services.auth_service import AuthenticationService
from src.services.time_sync_service import get_time_sync_service

logger = logging.getLogger(__name__)


class PurchaseOrderService:
    """Service for purchase order listing and lifecycle updates."""

    def __init__(self):
        self.db = get_database()
        self.time_sync_service = get_time_sync_service()

    def get_purchase_orders(self, status: Optional[str] = None, limit: int = 300) -> List[Dict]:
        """Return purchase orders with supplier and line count metadata."""
        params: List = []
        where_clause = ""
        if status and status.lower() != "all":
            where_clause = "WHERE po.status = ?"
            params.append(status)

        params.append(limit)
        query = f"""
            SELECT
                po.*,
                s.supplier_name,
                COUNT(poi.id) AS item_count
            FROM purchase_orders po
            LEFT JOIN suppliers s ON s.id = po.supplier_id
            LEFT JOIN purchase_order_items poi ON poi.purchase_order_id = po.id
            {where_clause}
            GROUP BY po.id
            ORDER BY po.order_date DESC, po.id DESC
            LIMIT ?
        """
        return self.db.fetch_all(query, tuple(params))

    def get_purchase_order_items(self, purchase_order_id: int) -> List[Dict]:
        """Return line items for a purchase order."""
        return self.db.fetch_all(
            """
            SELECT
                poi.*,
                i.item_name,
                i.barcode
            FROM purchase_order_items poi
            LEFT JOIN items i ON i.id = poi.item_id
            WHERE poi.purchase_order_id = ?
            ORDER BY poi.id
            """,
            (purchase_order_id,),
        )

    def get_purchase_order_item_audit(self, purchase_order_id: int, limit: int = 100) -> List[Dict]:
        """Return amendment audit trail entries for a purchase order."""
        return self.db.fetch_all(
            """
            SELECT *
            FROM purchase_order_item_audit_trail
            WHERE purchase_order_id = ?
            ORDER BY changed_at DESC, id DESC
            LIMIT ?
            """,
            (purchase_order_id, limit),
        )

    def export_purchase_order_item_audit_csv(self, purchase_order_id: int, output_path: Path) -> Tuple[bool, str]:
        """Export amendment audit trail entries for one purchase order to CSV."""
        rows = self.get_purchase_order_item_audit(purchase_order_id, limit=10000)
        signature = self.time_sync_service.get_signature_stamp()
        headers = [
            "audit_id",
            "purchase_order_id",
            "purchase_order_item_id",
            "item_id",
            "action",
            "changed_by_user_id",
            "changed_by_username",
            "change_reason",
            "changed_at",
            "old_values",
            "new_values",
        ]
        try:
            with output_path.open(mode="w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Generated at", signature])
                writer.writerow([])
                writer.writerow(headers)
                for row in rows:
                    writer.writerow(
                        [
                            row.get("id"),
                            row.get("purchase_order_id"),
                            row.get("purchase_order_item_id"),
                            row.get("item_id"),
                            row.get("action"),
                            row.get("changed_by_user_id"),
                            row.get("changed_by_username"),
                            row.get("change_reason"),
                            row.get("changed_at"),
                            row.get("old_values"),
                            row.get("new_values"),
                        ]
                    )
            return True, str(output_path)
        except Exception as e:
            logger.error(f"Failed to export PO audit trail CSV: {e}")
            return False, f"Failed to export PO audit trail CSV: {e}"

    def delete_purchase_order(self, purchase_order_id: int, admin_password: str) -> Tuple[bool, str]:
        """Delete a pending purchase order after validating administrator password."""
        if not self._can_current_user_delete_transactions():
            return False, "Only administrators can delete transaction records"

        admin_user = self._authenticate_admin(admin_password)
        if not admin_user:
            return False, "Invalid administrator password"

        order = self.db.fetch_one("SELECT * FROM purchase_orders WHERE id = ?", (purchase_order_id,))
        if not order:
            return False, "Purchase order not found"

        if (order.get("status") or "").lower() == "received":
            return False, "Cannot delete a received purchase order"

        order_items = self.db.fetch_all(
            "SELECT id, item_id, quantity_ordered, quantity_received, line_total FROM purchase_order_items WHERE purchase_order_id = ?",
            (purchase_order_id,),
        )

        self.db.delete("purchase_order_item_audit_trail", "purchase_order_id = ?", (purchase_order_id,))
        self.db.delete("purchase_order_items", "purchase_order_id = ?", (purchase_order_id,))
        self.db.delete("purchase_orders", "id = ?", (purchase_order_id,))

        self.db.insert(
            "audit_log",
            {
                "user_id": admin_user.get("id"),
                "action": "delete_purchase_order",
                "table_name": "purchase_orders",
                "record_id": purchase_order_id,
                "old_values": json.dumps(
                    {
                        "order": {
                            "id": order.get("id"),
                            "supplier_id": order.get("supplier_id"),
                            "status": order.get("status"),
                            "total_amount": order.get("total_amount"),
                        },
                        "items": order_items,
                    }
                ),
                "new_values": "{}",
            },
        )
        return True, f"Purchase order deleted | {self.time_sync_service.get_signature_stamp()}"

    def mark_received(self, purchase_order_id: int) -> Tuple[bool, str]:
        """Mark a purchase order as received and complete all line receipts."""
        order = self.db.fetch_one("SELECT * FROM purchase_orders WHERE id = ?", (purchase_order_id,))
        if not order:
            return False, "Purchase order not found"

        if (order.get("status") or "").lower() == "received":
            return False, "Purchase order is already marked as received"

        self.db.update(
            "purchase_orders",
            {
                "status": "received",
                "actual_delivery_date": self.time_sync_service.today(),
                "updated_at": self.time_sync_service.now(),
            },
            "id = ?",
            (purchase_order_id,),
        )

        self.db.execute(
            """
            UPDATE purchase_order_items
            SET quantity_received = quantity_ordered
            WHERE purchase_order_id = ?
            """,
            (purchase_order_id,),
        )

        logger.info(f"Purchase order marked received: {purchase_order_id}")
        return True, f"Purchase order marked as received | {self.time_sync_service.get_signature_stamp()}"

    def update_purchase_order_item(
        self, purchase_order_item_id: int, quantity_ordered: int, admin_password: str
    ) -> Tuple[bool, str]:
        """Update PO line quantity after validating administrator password."""
        if quantity_ordered <= 0:
            return False, "Quantity must be greater than zero"

        admin_user = self._authenticate_admin(admin_password)
        if not admin_user:
            return False, "Invalid administrator password"

        row = self.db.fetch_one(
            "SELECT * FROM purchase_order_items WHERE id = ?",
            (purchase_order_item_id,),
        )
        if not row:
            return False, "Purchase order item not found"

        order = self.db.fetch_one("SELECT * FROM purchase_orders WHERE id = ?", (row["purchase_order_id"],))
        if not order:
            return False, "Purchase order not found"
        if (order.get("status") or "").lower() == "received":
            return False, "Cannot amend items for a received purchase order"

        unit_price = float(row["unit_price"] or 0)
        quantity_received = min(int(row.get("quantity_received") or 0), quantity_ordered)
        line_total = unit_price * quantity_ordered
        self.db.update(
            "purchase_order_items",
            {
                "quantity_ordered": quantity_ordered,
                "quantity_received": quantity_received,
                "line_total": line_total,
            },
            "id = ?",
            (purchase_order_item_id,),
        )
        updated_row = self.db.fetch_one("SELECT * FROM purchase_order_items WHERE id = ?", (purchase_order_item_id,))
        self._record_item_audit(
            action="update",
            purchase_order_id=row["purchase_order_id"],
            purchase_order_item_id=purchase_order_item_id,
            item_id=row["item_id"],
            old_values={
                "quantity_ordered": row.get("quantity_ordered"),
                "quantity_received": row.get("quantity_received"),
                "line_total": row.get("line_total"),
            },
            new_values={
                "quantity_ordered": updated_row.get("quantity_ordered") if updated_row else quantity_ordered,
                "quantity_received": updated_row.get("quantity_received") if updated_row else quantity_received,
                "line_total": updated_row.get("line_total") if updated_row else line_total,
            },
            changed_by=admin_user,
            change_reason="PO line item updated",
        )

        self._recalculate_order_total(row["purchase_order_id"])
        return True, f"Purchase order item updated | {self.time_sync_service.get_signature_stamp()}"

    def delete_purchase_order_item(self, purchase_order_item_id: int, admin_password: str) -> Tuple[bool, str]:
        """Delete PO line after validating administrator password."""
        if not self._can_current_user_delete_transactions():
            return False, "Only administrators can delete transaction records"

        admin_user = self._authenticate_admin(admin_password)
        if not admin_user:
            return False, "Invalid administrator password"

        row = self.db.fetch_one(
            "SELECT * FROM purchase_order_items WHERE id = ?",
            (purchase_order_item_id,),
        )
        if not row:
            return False, "Purchase order item not found"

        order = self.db.fetch_one("SELECT * FROM purchase_orders WHERE id = ?", (row["purchase_order_id"],))
        if not order:
            return False, "Purchase order not found"
        if (order.get("status") or "").lower() == "received":
            return False, "Cannot amend items for a received purchase order"

        self._record_item_audit(
            action="delete",
            purchase_order_id=row["purchase_order_id"],
            purchase_order_item_id=purchase_order_item_id,
            item_id=row["item_id"],
            old_values={
                "quantity_ordered": row.get("quantity_ordered"),
                "quantity_received": row.get("quantity_received"),
                "line_total": row.get("line_total"),
            },
            new_values={},
            changed_by=admin_user,
            change_reason="PO line item deleted",
        )
        self.db.delete("purchase_order_items", "id = ?", (purchase_order_item_id,))
        self._recalculate_order_total(row["purchase_order_id"])
        return True, f"Purchase order item deleted | {self.time_sync_service.get_signature_stamp()}"

    def _recalculate_order_total(self, purchase_order_id: int):
        total_row = self.db.fetch_one(
            "SELECT COALESCE(SUM(line_total), 0) AS total FROM purchase_order_items WHERE purchase_order_id = ?",
            (purchase_order_id,),
        )
        total_amount = float(total_row["total"] or 0.0)
        self.db.update(
            "purchase_orders",
            {"total_amount": total_amount, "updated_at": self.time_sync_service.now()},
            "id = ?",
            (purchase_order_id,),
        )

    def _authenticate_admin(self, password: str) -> Optional[Dict]:
        if not password:
            return None
        admins = self.db.fetch_all(
            "SELECT id, username, password_hash FROM users WHERE is_active = 1 AND LOWER(role) = 'administrator'"
        )
        for row in admins:
            if AuthenticationService.verify_password(password, row.get("password_hash", "")):
                return row
        return None

    def _can_current_user_delete_transactions(self) -> bool:
        current_user_id = self.db.get_audit_user()
        if current_user_id is None:
            return True
        row = self.db.fetch_one("SELECT role, is_active FROM users WHERE id = ?", (current_user_id,))
        if not row or not bool(row.get("is_active", 0)):
            return False
        return (row.get("role") or "").lower() == "administrator"

    def _record_item_audit(
        self,
        action: str,
        purchase_order_id: int,
        purchase_order_item_id: int,
        item_id: int,
        old_values: Dict,
        new_values: Dict,
        changed_by: Dict,
        change_reason: str,
    ):
        self.db.insert(
            "purchase_order_item_audit_trail",
            {
                "purchase_order_id": purchase_order_id,
                "purchase_order_item_id": purchase_order_item_id,
                "item_id": item_id,
                "action": action,
                "old_values": json.dumps(old_values),
                "new_values": json.dumps(new_values),
                "changed_by_user_id": changed_by.get("id"),
                "changed_by_username": changed_by.get("username"),
                "change_reason": change_reason,
            },
        )
