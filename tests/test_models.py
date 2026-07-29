"""
Unit Tests for MediStock AI
Test suite for core functionality
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, date

# These tests are designed to run with pytest
# Install with: pip install pytest pytest-cov


class TestAuthenticationService:
    """Test authentication service"""

    def test_hash_password(self):
        """Test password hashing"""
        from src.services.auth_service import AuthenticationService
        
        password = "test_password_123"
        hashed = AuthenticationService.hash_password(password)
        
        assert hashed != password
        assert AuthenticationService.verify_password(password, hashed)
        assert not AuthenticationService.verify_password("wrong_password", hashed)

    def test_hash_password_too_short(self):
        """Test that short passwords are rejected"""
        from src.services.auth_service import AuthenticationService
        
        with pytest.raises(ValueError):
            AuthenticationService.hash_password("short")


class TestInventoryService:
    """Test inventory service"""

    def test_item_stock_status(self):
        """Test item stock status calculation"""
        from src.models.models import Item
        
        item = Item(
            id=1,
            barcode="TEST001",
            item_name="Test Item",
            current_quantity=5,
            minimum_quantity=10
        )
        
        assert item.stock_status == "LOW_STOCK"
        
        item.current_quantity = 0
        assert item.stock_status == "OUT_OF_STOCK"
        
        item.current_quantity = 100
        item.maximum_quantity = 100
        assert item.stock_status == "NORMAL"

    def test_item_expiry_check(self):
        """Test item expiry check"""
        from src.models.models import Item
         
        item = Item(
            id=1,
            barcode="TEST001",
            item_name="Test Item",
            expiry_date=date.today()
        )
         
        assert item.is_expired
 
    def test_item_dict_to_model_parses_date_strings(self):
        """Ensure expiry_date strings from the database are converted to dates"""
        from src.services.inventory_service import InventoryService
        service = InventoryService()
        item = service._dict_to_item({
            'id': 1,
            'barcode': 'TEST001',
            'item_name': 'Test Item',
            'category': 'Medicines',
            'current_quantity': 5,
            'expiry_date': '2030-12-31',
            'date_received': '2025-01-01'
        })
 
        assert item.expiry_date.year == 2030
        assert item.expiry_date.month == 12
        assert item.expiry_date.day == 31
        assert item.date_received.year == 2025
        assert item.date_received.month == 1
        assert item.date_received.day == 1
 
 
class TestDatabase:
    """Test database functionality"""

    def test_database_initialization(self):
        """Test database initialization"""
        from src.database.db import Database
        from src.database.schema import SCHEMA
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            assert db.db_path.exists()
            db.close()


class TestModels:
    """Test data models"""

    def test_user_model(self):
        """Test User model"""
        from src.models.models import User
        
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            role="doctor"
        )
        
        user_dict = user.to_dict()
        assert user_dict['username'] == 'testuser'
        assert user_dict['role'] == 'doctor'

    def test_item_model(self):
        """Test Item model"""
        from src.models.models import Item
        
        item = Item(
            id=1,
            barcode="ITEM001",
            item_name="Aspirin",
            category="Medicines",
            current_quantity=100,
            product_code="PRD-001",
            supplier_product_code="SUP-001",
            unit_of_measurement="box",
            lead_time_days=7,
            safety_stock_quantity=12,
            is_active=True,
        )
        
        item_dict = item.to_dict()
        assert item_dict['barcode'] == 'ITEM001'
        assert item_dict['product_code'] == 'PRD-001'
        assert item_dict['category'] == 'Medicines'
        assert item.product_id == 1
        assert item.target_stock_level == item.maximum_quantity

    def test_stock_movement_model(self):
        """Test StockMovement model"""
        from src.models.models import StockMovement
        
        movement = StockMovement(
            id=1,
            item_id=1,
            movement_type="issued",
            transaction_quantity=10,
            quantity_change=-10,
            batch_id=2,
            room_id=3,
            from_room_id=3,
            to_room_id=4,
            user_id=1
        )
        
        mov_dict = movement.to_dict()
        assert movement.transaction_id == 1
        assert movement.product_id == 1
        assert movement.quantity == 10
        assert mov_dict['quantity_change'] == -10
        assert mov_dict['transaction_quantity'] == 10
        assert mov_dict['batch_id'] == 2
        assert mov_dict['movement_type'] == 'issued'

    def test_stock_batch_model(self):
        """Test StockBatch model"""
        from src.models.models import StockBatch

        batch = StockBatch(
            id=5,
            item_id=9,
            room_id=3,
            qr_code="QR-B-001",
            batch_number="B-001",
            quantity_available=12,
            expiry_period_after_opening=28,
            status="Active",
        )

        batch_dict = batch.to_dict()
        assert batch.batch_id == 5
        assert batch.product_id == 9
        assert batch_dict["room_id"] == 3
        assert batch_dict["qr_code"] == "QR-B-001"
        assert batch_dict["batch_number"] == "B-001"
        assert batch_dict["quantity_available"] == 12


# Run tests with: pytest tests/test_models.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
