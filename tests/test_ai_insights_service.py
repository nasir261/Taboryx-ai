"""
Tests for AI insights forecasting and expiry risk workflows.
"""

import tempfile
from datetime import date, timedelta
from pathlib import Path

from src.database.db import get_database, init_database
from src.models.models import StockMovement
from src.services.ai_insights_service import AIInsightsService
from src.services.auth_service import AuthenticationService
from src.services.inventory_service import InventoryService


class TestAIInsightsService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_ai_insights.db"
        init_database(self.db_path)

        self.auth_service = AuthenticationService()
        self.inventory_service = InventoryService()
        self.ai_service = AIInsightsService()

        success, _, self.user_id = self.auth_service.create_user(
            username="aiadmin",
            email="aiadmin@example.com",
            password="password123",
            full_name="AI Admin",
            role="administrator",
        )
        assert success

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_usage_forecasts_include_confidence_and_risk(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Doxycycline",
            barcode="AI-DOX-001",
            category="Medicines",
            current_quantity=8,
            minimum_quantity=10,
            maximum_quantity=80,
        )
        assert success

        for days_ago, qty in [(5, -4), (15, -3), (35, -3), (100, -8)]:
            movement = StockMovement(
                item_id=item_id,
                movement_type="issued",
                quantity_change=qty,
                user_id=self.user_id,
                movement_date=date.today() - timedelta(days=days_ago),
            )
            ok, _, _ = self.inventory_service.log_stock_movement(movement)
            assert ok

        forecasts = self.ai_service.get_usage_forecasts()
        matched = [row for row in forecasts if row["item_id"] == item_id]
        assert len(matched) == 1
        row = matched[0]
        assert row["forecast_next_month"] > 0
        assert row["confidence"] in {"High", "Medium", "Low"}
        assert row["shortage_risk"] in {"High", "Medium", "Low"}
        assert isinstance(row["recommended_action"], str)

    def test_expiry_risk_returns_expiring_item(self):
        success, _, item_id = self.inventory_service.add_item(
            name="Insulin",
            barcode="AI-INS-001",
            category="Medicines",
            current_quantity=30,
            minimum_quantity=5,
            maximum_quantity=100,
            expiry_date=date.today() + timedelta(days=20),
        )
        assert success

        risk_rows = self.ai_service.get_expiry_risk_items(90)
        matched = [row for row in risk_rows if row["item_id"] == item_id]
        assert len(matched) == 1
        row = matched[0]
        assert row["days_to_expiry"] <= 30
        assert row["risk_level"] in {"High", "Medium", "Low"}
        assert isinstance(row["risk_score"], int)
