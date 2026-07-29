"""
AI Insights Service
Provides forecasting and risk signals from historical stock movements.
"""

import logging
from typing import Dict, List

from src.database.db import get_database
from src.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class AIInsightsService:
    """Service for AI-style analytics on inventory usage and expiry risk."""

    def __init__(self):
        self.db = get_database()
        self.inventory_service = InventoryService()

    def get_usage_forecasts(self) -> List[Dict]:
        """Forecast next month/quarter/year usage per item with confidence."""
        usage_30 = self._usage_totals(30)
        usage_90 = self._usage_totals(90)
        usage_365 = self._usage_totals(365)

        forecasts: List[Dict] = []
        for item in self.inventory_service.get_all_items():
            u30 = float(usage_30.get(item.id, 0.0))
            u90 = float(usage_90.get(item.id, 0.0))
            u365 = float(usage_365.get(item.id, 0.0))

            monthly_from_30 = u30
            monthly_from_90 = u90 / 3.0
            monthly_from_365 = u365 / 12.0
            monthly_forecast = (monthly_from_30 * 0.5) + (monthly_from_90 * 0.3) + (monthly_from_365 * 0.2)
            monthly_forecast = max(0.0, monthly_forecast)

            quarter_forecast = monthly_forecast * 3.0
            yearly_forecast = monthly_forecast * 12.0

            avg_daily_usage = monthly_forecast / 30.0 if monthly_forecast > 0 else 0.0
            days_cover = (item.current_quantity / avg_daily_usage) if avg_daily_usage > 0 else 9999.0
            shortage_risk = "High" if days_cover < 14 else ("Medium" if days_cover < 30 else "Low")

            confidence = self._confidence_level(u30=u30, u90=u90, u365=u365)

            forecasts.append(
                {
                    "item_id": item.id,
                    "item_name": item.item_name,
                    "current_quantity": item.current_quantity,
                    "forecast_next_month": round(monthly_forecast, 1),
                    "forecast_next_quarter": round(quarter_forecast, 1),
                    "forecast_next_year": round(yearly_forecast, 1),
                    "confidence": confidence,
                    "shortage_risk": shortage_risk,
                    "recommended_action": self._recommended_action(shortage_risk, item.current_quantity, item.minimum_quantity),
                }
            )

        forecasts.sort(key=lambda x: (self._risk_rank(x["shortage_risk"]), x["item_name"].lower()))
        return forecasts

    def get_expiry_risk_items(self, threshold_days: int = 90) -> List[Dict]:
        """Return items with upcoming expiries and risk scoring."""
        expiring = self.inventory_service.get_expiring_items(threshold_days)
        rows: List[Dict] = []
        for item in expiring:
            days_to_expiry = (item.expiry_date - self._today()).days if item.expiry_date else 9999
            risk_score = max(0, (threshold_days - days_to_expiry)) + max(0, item.current_quantity - item.minimum_quantity)
            risk_level = "High" if days_to_expiry <= 30 else ("Medium" if days_to_expiry <= 60 else "Low")
            action = "Prioritize use or transfer" if risk_level in {"High", "Medium"} else "Monitor"
            rows.append(
                {
                    "item_id": item.id,
                    "item_name": item.item_name,
                    "current_quantity": item.current_quantity,
                    "days_to_expiry": days_to_expiry,
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                    "action": action,
                }
            )

        rows.sort(key=lambda x: (-x["risk_score"], x["item_name"].lower()))
        return rows

    def _usage_totals(self, days: int) -> Dict[int, float]:
        rows = self.db.fetch_all(
            """
            SELECT item_id, SUM(ABS(quantity_change)) AS total_used
            FROM stock_movements
            WHERE quantity_change < 0
              AND movement_date >= DATE('now', '-' || ? || ' days')
            GROUP BY item_id
            """,
            (days,),
        )
        return {row["item_id"]: float(row["total_used"] or 0.0) for row in rows}

    @staticmethod
    def _confidence_level(u30: float, u90: float, u365: float) -> str:
        if u365 > 0 and u90 > 0 and u30 > 0:
            return "High"
        if u90 > 0 or u30 > 0:
            return "Medium"
        return "Low"

    @staticmethod
    def _recommended_action(shortage_risk: str, current_qty: int, min_qty: int) -> str:
        if shortage_risk == "High":
            return "Order immediately"
        if shortage_risk == "Medium":
            return "Plan reorder this week"
        if current_qty > (min_qty * 3):
            return "Delay order"
        return "Monitor usage"

    @staticmethod
    def _risk_rank(risk: str) -> int:
        if risk == "High":
            return 0
        if risk == "Medium":
            return 1
        return 2

    @staticmethod
    def _today():
        from datetime import date

        return date.today()
