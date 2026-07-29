"""
AI Chat Service
Rule-based assistant for common inventory and pharmacy queries.
"""

import re
from datetime import date
from typing import Dict, List

from src.database.db import get_database
from src.services.inventory_service import InventoryService
from src.services.purchasing_service import PurchasingService


class AIChatService:
    """Handles natural-language assistant queries."""

    def __init__(self):
        self.db = get_database()
        self.inventory_service = InventoryService()
        self.purchasing_service = PurchasingService()

    def ask(self, question: str) -> Dict:
        text = (question or "").strip()
        lower = text.lower()
        if not lower:
            return {"answer": "Please type a question.", "rows": []}

        if "expired" in lower:
            return self._handle_expired_query(lower)
        if "room uses the most" in lower:
            return self._handle_top_room_usage_query(lower)
        if "used this month" in lower or "this month" in lower and "used" in lower:
            return self._handle_monthly_usage_query(lower)
        if "expire next week" in lower or "expiring next week" in lower:
            return self._handle_expire_next_week_query()
        if "purchasing report" in lower or "purchase report" in lower:
            return self._handle_purchasing_report_query()

        return {
            "answer": (
                "I can help with: expired items, top room usage, monthly item usage, items expiring next week, "
                "and purchasing report summaries."
            ),
            "rows": [],
        }

    def _handle_expired_query(self, lower: str) -> Dict:
        term = self._term_after_keyword(lower, "expired")
        items = self.inventory_service.get_expired_items()
        if term:
            items = [item for item in items if term in item.item_name.lower()]

        if not items:
            label = f" matching '{term}'" if term else ""
            return {"answer": f"No expired items found{label}.", "rows": []}

        rows = [
            {
                "item": item.item_name,
                "barcode": item.barcode,
                "expiry_date": item.expiry_date.strftime("%d-%m-%Y") if item.expiry_date else "-",
                "quantity": item.current_quantity,
            }
            for item in items
        ]
        return {"answer": f"Found {len(rows)} expired item(s).", "rows": rows}

    def _handle_top_room_usage_query(self, lower: str) -> Dict:
        term = self._term_after_keyword(lower, "most")
        if not term:
            return {"answer": "Please specify the item, for example: Which room uses the most gloves?", "rows": []}

        row = self.db.fetch_one(
            """
            SELECT
                COALESCE(sm.patient_area, 'Unknown') AS room_name,
                SUM(ABS(sm.quantity_change)) AS total_used
            FROM stock_movements sm
            JOIN items i ON i.id = sm.item_id
            WHERE sm.quantity_change < 0
              AND LOWER(i.item_name) LIKE ?
            GROUP BY COALESCE(sm.patient_area, 'Unknown')
            ORDER BY total_used DESC
            LIMIT 1
            """,
            (f"%{term}%",),
        )
        if not row:
            return {"answer": f"No usage data found for '{term}'.", "rows": []}

        return {
            "answer": f"{row['room_name']} uses the most {term} ({int(row['total_used'])} used).",
            "rows": [{"room": row["room_name"], "item": term, "used": int(row["total_used"])}],
        }

    def _handle_monthly_usage_query(self, lower: str) -> Dict:
        term = self._extract_item_term_for_usage(lower)
        if not term:
            return {"answer": "Please specify the item, for example: How many syringes were used this month?", "rows": []}

        first_day = date.today().replace(day=1).isoformat()
        row = self.db.fetch_one(
            """
            SELECT COALESCE(SUM(ABS(sm.quantity_change)), 0) AS total_used
            FROM stock_movements sm
            JOIN items i ON i.id = sm.item_id
            WHERE sm.quantity_change < 0
              AND sm.movement_date >= ?
              AND LOWER(i.item_name) LIKE ?
            """,
            (first_day, f"%{term}%"),
        )
        total = int(row["total_used"] or 0)
        return {"answer": f"{total} {term} used this month.", "rows": [{"item": term, "used_this_month": total}]}

    def _handle_expire_next_week_query(self) -> Dict:
        items = self.inventory_service.get_expiring_items(7)
        if not items:
            return {"answer": "No items expire in the next week.", "rows": []}

        rows = [
            {
                "item": item.item_name,
                "expiry_date": item.expiry_date.strftime("%d-%m-%Y") if item.expiry_date else "-",
                "quantity": item.current_quantity,
            }
            for item in items
        ]
        return {"answer": f"{len(rows)} item(s) expire next week.", "rows": rows}

    def _handle_purchasing_report_query(self) -> Dict:
        recs = self.purchasing_service.get_purchase_recommendations()
        urgent = [r for r in recs if r["action"] == "Order now"]
        soon = [r for r in recs if r["action"] == "Order soon"]
        rows = [
            {
                "item": rec["item_name"],
                "supplier": rec["supplier_name"],
                "recommended_qty": rec["recommended_qty"],
                "action": rec["action"],
            }
            for rec in recs[:10]
        ]
        return {
            "answer": f"Purchasing summary: {len(urgent)} order-now, {len(soon)} order-soon items.",
            "rows": rows,
        }

    @staticmethod
    def _term_after_keyword(text: str, keyword: str) -> str:
        match = re.search(rf"{re.escape(keyword)}\s+([a-z0-9\s\-]+)", text)
        if not match:
            return ""
        value = match.group(1).strip()
        value = re.sub(r"\b(items?|were|was|is|are|the|most|uses|use|this|month|next|week)\b", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @staticmethod
    def _extract_item_term_for_usage(text: str) -> str:
        match = re.search(r"how many\s+([a-z0-9\s\-]+?)\s+(were|was|are|is)\s+used", text)
        if match:
            return match.group(1).strip()
        match = re.search(r"used\s+([a-z0-9\s\-]+)\s+this month", text)
        if match:
            return match.group(1).strip()
        return ""
