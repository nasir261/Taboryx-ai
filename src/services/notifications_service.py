"""
Notifications Service
Builds operational alerts for inventory, audits, and purchasing.
"""

from datetime import date, datetime
from typing import Dict, List

from src.database.db import get_database
from src.services.inventory_service import InventoryService
from src.services.purchase_order_service import PurchaseOrderService


class NotificationsService:
    """Service for aggregating actionable notifications."""

    def __init__(self):
        self.db = get_database()
        self.inventory_service = InventoryService()
        self.purchase_order_service = PurchaseOrderService()

    def get_notifications(self, audit_overdue_days: int = 30) -> List[Dict]:
        notifications: List[Dict] = []
        notifications.extend(self._build_low_stock_notifications())
        notifications.extend(self._build_expiry_notifications())
        notifications.extend(self._build_overdue_audit_notifications(audit_overdue_days))
        notifications.extend(self._build_pending_purchase_order_notifications())
        notifications.extend(self._build_update_notifications())
        notifications.sort(key=lambda row: (row["priority"], row["title"]))
        return notifications

    def _build_update_notifications(self) -> List[Dict]:
        """Check for a pending software update and surface it as a notification."""
        try:
            from src.services.update_service import UpdateService
            svc = UpdateService()
            available, manifest, _err = svc.check_for_update(timeout=5)
            if available and manifest:
                latest = manifest.get("version", "?")
                return [
                    {
                        "type": "software_update",
                        "severity": "info",
                        "priority": 1,
                        "title": f"MediStock AI update available: v{latest}",
                        "message": (
                            f"A new version ({latest}) is available. "
                            "Go to System → Updates to download and install."
                        ),
                        "reference": "System › Updates",
                    }
                ]
        except Exception:
            pass
        return []

    def _build_low_stock_notifications(self) -> List[Dict]:
        notifications: List[Dict] = []
        low_stock_items = self.inventory_service.get_low_stock_items()
        for item in low_stock_items:
            is_out = item.current_quantity <= 0
            notifications.append(
                {
                    "type": "low_stock",
                    "severity": "critical" if is_out else "warning",
                    "priority": 0 if is_out else 1,
                    "title": f"{item.item_name} stock {'out' if is_out else 'low'}",
                    "message": (
                        f"Current quantity {item.current_quantity} is below minimum {item.minimum_quantity}."
                    ),
                    "reference": f"Item #{item.id}",
                }
            )
        return notifications

    def _build_expiry_notifications(self) -> List[Dict]:
        notifications: List[Dict] = []
        expired_items = self.inventory_service.get_expired_items()
        for item in expired_items:
            expiry_text = item.expiry_date.strftime("%d-%m-%Y") if item.expiry_date else "unknown"
            notifications.append(
                {
                    "type": "expiry",
                    "severity": "critical",
                    "priority": 0,
                    "title": f"{item.item_name} expired",
                    "message": f"Item expired on {expiry_text}. Remove and dispose per policy.",
                    "reference": f"Item #{item.id}",
                }
            )

        for days, severity, priority in [(30, "warning", 1), (60, "info", 2), (90, "info", 2)]:
            expiring_items = self.inventory_service.get_expiring_items(days)
            for item in expiring_items:
                if item.expiry_date and item.expiry_date < date.today():
                    continue
                expiry_text = item.expiry_date.strftime("%d-%m-%Y") if item.expiry_date else "unknown"
                notifications.append(
                    {
                        "type": "expiry",
                        "severity": severity,
                        "priority": priority,
                        "title": f"{item.item_name} expiring in {days} days",
                        "message": f"Expiry date {expiry_text}. Review stock rotation/transfer.",
                        "reference": f"Item #{item.id}",
                    }
                )
        return notifications

    def _build_overdue_audit_notifications(self, audit_overdue_days: int) -> List[Dict]:
        notifications: List[Dict] = []
        rows = self.db.fetch_all(
            """
            SELECT
                cr.id AS room_id,
                cr.room_name,
                MAX(CASE WHEN LOWER(ra.status) = 'completed' THEN ra.audit_date END) AS last_completed_audit_date
            FROM clinical_rooms cr
            LEFT JOIN room_audits ra ON ra.room_id = cr.id
            GROUP BY cr.id, cr.room_name
            ORDER BY cr.room_name
            """
        )

        today = date.today()
        for row in rows:
            last_audit_text = row.get("last_completed_audit_date")
            if not last_audit_text:
                notifications.append(
                    {
                        "type": "audit_overdue",
                        "severity": "warning",
                        "priority": 1,
                        "title": f"Audit overdue: {row.get('room_name')}",
                        "message": "No completed audit found for this room.",
                        "reference": f"Room #{row.get('room_id')}",
                    }
                )
                continue

            try:
                last_audit = datetime.fromisoformat(str(last_audit_text)).date()
            except ValueError:
                continue

            age_days = (today - last_audit).days
            if age_days > audit_overdue_days:
                notifications.append(
                    {
                        "type": "audit_overdue",
                        "severity": "warning",
                        "priority": 1,
                        "title": f"Audit overdue: {row.get('room_name')}",
                        "message": f"Last completed audit was {age_days} days ago.",
                        "reference": f"Room #{row.get('room_id')}",
                    }
                )
        return notifications

    def _build_pending_purchase_order_notifications(self) -> List[Dict]:
        notifications: List[Dict] = []
        pending_orders = self.purchase_order_service.get_purchase_orders(status="pending")
        for order in pending_orders:
            notifications.append(
                {
                    "type": "purchase_order",
                    "severity": "info",
                    "priority": 2,
                    "title": f"Pending purchase order #{order.get('id')}",
                    "message": (
                        f"Supplier: {order.get('supplier_name') or 'Unknown'} | "
                        f"Expected: {self._fmt_date(order.get('expected_delivery_date'))}"
                    ),
                    "reference": f"PO #{order.get('id')}",
                }
            )
        return notifications

    @staticmethod
    def _fmt_date(value) -> str:
        if not value:
            return "-"
        text = str(value)
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return f"{text[8:10]}-{text[5:7]}-{text[0:4]}"
        return text
