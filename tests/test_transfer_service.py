"""
Tests for stock transfer workflows.
"""

import tempfile
from pathlib import Path
from datetime import date, datetime
from src.database.db import init_database, get_database
from src.services.transfer_service import TransferService
from src.services.room_service import ClinicalRoomService
from src.services.inventory_service import InventoryService
from src.services.auth_service import AuthenticationService
from src.models.models import ClinicalRoom, StockTransfer


class TestTransferService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_transfer.db"
        init_database(self.db_path)
        self.transfer_service = TransferService()
        self.room_service = ClinicalRoomService()
        self.inventory_service = InventoryService()
        self.auth_service = AuthenticationService()

        self.user = self.auth_service.create_user(
            username="transporter",
            email="transporter@example.com",
            password="password123",
            full_name="Transfer User",
            role="administrator"
        )
        self.current_user_id = self.user[2] if isinstance(self.user, tuple) else 1

        self.from_room = ClinicalRoom(room_name="Store Room", room_type="Storage")
        self.from_room.id = self.room_service.create_room(self.from_room)
        self.to_room = ClinicalRoom(room_name="Treatment Room", room_type="Treatment")
        self.to_room.id = self.room_service.create_room(self.to_room)

        success, _, item_id = self.inventory_service.add_item(
            name="Syringe",
            barcode="TRN001",
            category="Needles",
            current_quantity=30,
            minimum_quantity=5,
            maximum_quantity=100,
            clinical_room=self.from_room.room_name,
        )
        assert success
        self.item_id = item_id

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_create_transfer(self):
        transfer = self._build_transfer(self.item_id, 10, self.from_room.id, self.to_room.id)
        success, message, transfer_id = self.transfer_service.create_transfer(transfer)
        assert success
        assert transfer_id is not None

        transfers = self.transfer_service.get_transfers(limit=10)
        assert len(transfers) == 1
        assert transfers[0].item_id == self.item_id
        assert transfers[0].quantity == 10

        movements = self.inventory_service.get_stock_movements(item_id=self.item_id, limit=10)
        assert len(movements) == 1
        assert movements[0].transaction_type == "TRANSFERRED"
        assert movements[0].quantity == 10
        assert movements[0].previous_quantity == 30
        assert movements[0].new_quantity == 30
        assert movements[0].from_room_id == self.from_room.id
        assert movements[0].to_room_id == self.to_room.id

    def test_invalid_transfer_quantity(self):
        transfer = self._build_transfer(self.item_id, 0, self.from_room.id, self.to_room.id)
        success, message, transfer_id = self.transfer_service.create_transfer(transfer)
        assert not success
        assert transfer_id is None

    def test_same_room_transfer(self):
        transfer = self._build_transfer(self.item_id, 5, self.from_room.id, self.from_room.id)
        success, message, transfer_id = self.transfer_service.create_transfer(transfer)
        assert not success
        assert transfer_id is None

    def test_full_quantity_room_change(self):
        transfer = self._build_transfer(self.item_id, 30, self.from_room.id, self.to_room.id)
        success, message, transfer_id = self.transfer_service.create_transfer(transfer)
        assert success

        item = self.inventory_service.get_item_by_id(self.item_id)
        assert item.clinical_room == self.to_room.room_name

    def _build_transfer(self, item_id, quantity, from_room_id, to_room_id):
        return StockTransfer(
            item_id=item_id,
            quantity=quantity,
            from_room_id=from_room_id,
            to_room_id=to_room_id,
            transfer_date=date.today(),
            transfer_time=datetime.now().strftime("%H:%M:%S"),
            user_id=self.current_user_id,
            reason="Routine move",
            status="completed",
            notes="Test transfer",
        )
