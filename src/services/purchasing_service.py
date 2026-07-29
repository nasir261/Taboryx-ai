"""
Purchasing Service
Generates purchasing recommendations from stock levels and usage.
"""

import logging
from datetime import date, timedelta
from math import ceil, floor
from typing import Dict, List, Optional, Tuple

from src.database.db import get_database
from src.services.inventory_service import InventoryService
from src.services.supplier_service import SupplierService
from src.services.app_settings_service import AppSettingsService
from src.services.time_sync_service import get_time_sync_service

logger = logging.getLogger(__name__)


class PurchasingService:
    """Service for purchase recommendation workflows."""

    def __init__(self):
        self.db = get_database()
        self.inventory_service = InventoryService()
        self.supplier_service = SupplierService()
        self.app_settings_service = AppSettingsService()
        self.time_sync_service = get_time_sync_service()

    def get_purchase_recommendations(self, lookback_days: Optional[int] = None) -> List[Dict]:
        """Build recommendations using usage velocity and supplier lead time."""
        settings = self.get_recommendation_settings()
        if lookback_days is None:
            lookback_days = settings["lookback_days"]
        if lookback_days <= 0:
            raise ValueError("lookback_days must be greater than zero")

        usage_map = self._get_usage_map(lookback_days)
        pending_order_map = self._get_pending_order_map()
        suppliers = self.supplier_service.get_all_suppliers()
        supplier_map = {supplier.id: supplier for supplier in suppliers if supplier.id is not None}

        recommendations: List[Dict] = []
        for item in self.inventory_service.get_all_items():
            usage = usage_map.get(item.id, 0.0)
            supplier = supplier_map.get(item.supplier_id)
            supplier_name = supplier.supplier_name if supplier else "Unassigned"
            lead_time_days = item.lead_time_days if item.lead_time_days is not None else (
                supplier.lead_time_days if supplier and supplier.lead_time_days else 7
            )

            avg_daily_usage = usage / lookback_days
            monthly_usage = avg_daily_usage * 30

            safety_stock = item.safety_stock_quantity if (item.safety_stock_quantity or 0) > 0 else max(
                int(item.minimum_quantity * settings["safety_stock_factor"]), settings["min_safety_stock"]
            )
            reorder_point = max(item.minimum_quantity, ceil((avg_daily_usage * lead_time_days) + safety_stock))
            target_level = max(item.maximum_quantity, reorder_point + ceil(monthly_usage))
            recommended_qty = max(0, target_level - item.current_quantity)
            unit_price = float(item.purchase_price or 0.0)
            estimated_cost = round(recommended_qty * unit_price, 2) if recommended_qty > 0 else 0.0

            action = "Delay order"
            urgency_rank = 2
            if item.current_quantity <= reorder_point and recommended_qty > 0:
                action = "Order now"
                urgency_rank = 0
            elif item.current_quantity <= item.minimum_quantity and recommended_qty > 0:
                action = "Order soon"
                urgency_rank = 1
            elif item.maximum_quantity > 0 and item.current_quantity > item.maximum_quantity:
                action = "Reduce quantity"
                urgency_rank = 1
                recommended_qty = item.current_quantity - item.maximum_quantity
                estimated_cost = 0.0

            budget_limit = settings["budget_limit"]
            if action in {"Order now", "Order soon"} and budget_limit is not None and unit_price > 0 and estimated_cost > budget_limit:
                affordable_qty = floor(budget_limit / unit_price)
                if affordable_qty > 0:
                    recommended_qty = affordable_qty
                    estimated_cost = round(recommended_qty * unit_price, 2)
                action = "Review budget"
                urgency_rank = 1

            recommendations.append(
                {
                    "item_id": item.id,
                    "item_name": item.item_name,
                    "supplier_name": supplier_name,
                    "lead_time_days": lead_time_days,
                    "current_quantity": item.current_quantity,
                    "minimum_quantity": item.minimum_quantity,
                    "maximum_quantity": item.maximum_quantity,
                    "avg_daily_usage": round(avg_daily_usage, 2),
                    "monthly_usage": round(monthly_usage, 2),
                    "reorder_point": reorder_point,
                    "target_level": target_level,
                    "recommended_qty": recommended_qty,
                    "estimated_cost": estimated_cost,
                    "unit_price": unit_price,
                    "pending_purchase_order_id": pending_order_map.get(item.id),
                    "action": action,
                    "urgency_rank": urgency_rank,
                    "reason": self._build_reason(
                        current_quantity=item.current_quantity,
                        minimum_quantity=item.minimum_quantity,
                        maximum_quantity=item.maximum_quantity,
                        reorder_point=reorder_point,
                        lead_time_days=lead_time_days,
                        avg_daily_usage=avg_daily_usage,
                        recommended_qty=recommended_qty,
                        action=action,
                        budget_limit=budget_limit,
                        estimated_cost=estimated_cost,
                    ),
                }
            )

        recommendations.sort(key=lambda rec: (rec["urgency_rank"], -rec["recommended_qty"], rec["item_name"].lower()))
        return recommendations

    def get_recommendation_settings(self) -> Dict:
        lookback_days = self._to_int(self.app_settings_service.get_setting("purchasing.lookback_days", "90"), 90)
        safety_stock_factor = self._to_float(
            self.app_settings_service.get_setting("purchasing.safety_stock_factor", "0.5"), 0.5
        )
        min_safety_stock = self._to_int(self.app_settings_service.get_setting("purchasing.min_safety_stock", "5"), 5)
        budget_limit_raw = self.app_settings_service.get_setting("purchasing.budget_limit", None)
        budget_limit = self._to_float(budget_limit_raw, None) if budget_limit_raw not in (None, "") else None
        return {
            "lookback_days": max(1, lookback_days),
            "safety_stock_factor": max(0.0, safety_stock_factor),
            "min_safety_stock": max(0, min_safety_stock),
            "budget_limit": budget_limit if budget_limit is None or budget_limit > 0 else None,
        }

    def update_recommendation_settings(
        self, lookback_days: int, safety_stock_factor: float, min_safety_stock: int, budget_limit: Optional[float]
    ) -> Tuple[bool, str]:
        if lookback_days <= 0:
            return False, "Lookback days must be greater than zero"
        if safety_stock_factor < 0:
            return False, "Safety stock factor cannot be negative"
        if min_safety_stock < 0:
            return False, "Minimum safety stock cannot be negative"
        if budget_limit is not None and budget_limit <= 0:
            return False, "Budget limit must be greater than zero"

        self.app_settings_service.set_setting("purchasing.lookback_days", str(lookback_days))
        self.app_settings_service.set_setting("purchasing.safety_stock_factor", str(safety_stock_factor))
        self.app_settings_service.set_setting("purchasing.min_safety_stock", str(min_safety_stock))
        self.app_settings_service.set_setting("purchasing.budget_limit", str(budget_limit) if budget_limit else "")
        return True, "Purchasing settings saved"

    def create_purchase_order_for_item(
        self, item_id: int, quantity: int, created_by_user_id: Optional[int] = None, notes: Optional[str] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """Create a purchase order for a single item recommendation."""
        if quantity <= 0:
            return False, "Quantity must be greater than zero", None

        item = self.inventory_service.get_item_by_id(item_id)
        if not item:
            return False, "Item not found", None

        if not item.supplier_id:
            return False, "Item has no assigned supplier", None

        supplier = self.supplier_service.get_supplier_by_id(item.supplier_id)
        if not supplier:
            return False, "Supplier not found", None

        lead_time_days = supplier.lead_time_days if supplier.lead_time_days else 7
        expected_delivery = self.time_sync_service.today() + timedelta(days=lead_time_days)
        unit_price = float(item.purchase_price) if item.purchase_price is not None else 0.0
        line_total = unit_price * quantity

        order_id = self.db.insert(
            "purchase_orders",
            {
                "supplier_id": item.supplier_id,
                "order_date": self.time_sync_service.today(),
                "expected_delivery_date": expected_delivery,
                "status": "pending",
                "total_amount": line_total,
                "notes": notes,
                "created_by_user_id": created_by_user_id,
            },
        )
        if not order_id:
            return False, "Failed to create purchase order", None

        self.db.insert(
            "purchase_order_items",
            {
                "purchase_order_id": order_id,
                "item_id": item.id,
                "quantity_ordered": quantity,
                "quantity_received": 0,
                "unit_price": unit_price,
                "line_total": line_total,
                "notes": notes,
            },
        )

        logger.info(f"Purchase order created: order_id={order_id}, item_id={item.id}, qty={quantity}")
        return True, f"Purchase order created successfully | {self.time_sync_service.get_signature_stamp()}", order_id

    def _get_usage_map(self, lookback_days: int) -> Dict[int, float]:
        rows = self.db.fetch_all(
            """
            SELECT item_id, SUM(ABS(quantity_change)) AS total_used
            FROM stock_movements
            WHERE quantity_change < 0
              AND movement_date >= DATE('now', '-' || ? || ' days')
            GROUP BY item_id
            """,
            (lookback_days,),
        )
        return {row["item_id"]: float(row["total_used"] or 0) for row in rows}

    def _get_pending_order_map(self) -> Dict[int, int]:
        rows = self.db.fetch_all(
            """
            SELECT poi.item_id, MAX(po.id) AS purchase_order_id
            FROM purchase_order_items poi
            JOIN purchase_orders po ON po.id = poi.purchase_order_id
            WHERE LOWER(po.status) = 'pending'
            GROUP BY poi.item_id
            """
        )
        return {
            row["item_id"]: row["purchase_order_id"]
            for row in rows
            if row.get("item_id") is not None and row.get("purchase_order_id") is not None
        }

    @staticmethod
    def _to_int(value: Optional[str], default: Optional[int]) -> Optional[int]:
        try:
            return int(value) if value is not None and value != "" else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_float(value: Optional[str], default: Optional[float]) -> Optional[float]:
        try:
            return float(value) if value is not None and value != "" else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _build_reason(
        current_quantity: int,
        minimum_quantity: int,
        maximum_quantity: int,
        reorder_point: int,
        lead_time_days: int,
        avg_daily_usage: float,
        recommended_qty: int,
        action: str,
        budget_limit: Optional[float],
        estimated_cost: float,
    ) -> str:
        if action == "Reduce quantity":
            return (
                f"Current stock {current_quantity} is above maximum {maximum_quantity}. "
                f"Reduce purchasing pressure and use existing stock before reordering."
            )
        if action == "Delay order":
            return (
                f"Current stock {current_quantity} is above reorder point {reorder_point} and minimum {minimum_quantity}. "
                f"Delay purchasing and review next cycle."
            )
        if action == "Review budget":
            if budget_limit is not None:
                return (
                    f"Estimated cost £{estimated_cost:.2f} exceeds budget cap £{budget_limit:.2f}. "
                    f"Review quantity, budget, or transfer options."
                )
            return "Recommendation needs budget review before order placement."
        if recommended_qty <= 0:
            return "Stock is at or above target level."
        return (
            f"Current stock {current_quantity} is near/below reorder point {reorder_point}. "
            f"Lead time {lead_time_days} days, average daily usage {avg_daily_usage:.2f}; "
            f"recommended order quantity {recommended_qty}."
        )
