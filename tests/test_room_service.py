"""
Tests for clinical room service and room inventory queries.
"""

import tempfile
from pathlib import Path
from src.database.db import init_database, get_database
from src.services.room_service import ClinicalRoomService
from src.services.inventory_service import InventoryService
from src.models.models import ClinicalRoom


class TestClinicalRoomService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_rooms.db"
        init_database(self.db_path)
        self.room_service = ClinicalRoomService()
        self.inventory_service = InventoryService()

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_create_and_get_room(self):
        room = ClinicalRoom(room_name="GP Room 1", room_type="GP", floor=1, location_description="First floor")
        room_id = self.room_service.create_room(room)
        assert room_id is not None

        stored = self.room_service.get_room_by_id(room_id)
        assert stored is not None
        assert stored.room_name == "GP Room 1"
        assert stored.room_type == "GP"

    def test_update_room(self):
        room = ClinicalRoom(room_name="Nurse Room A", room_type="Nurse", floor=2)
        room.id = self.room_service.create_room(room)
        room.room_name = "Nurse Room B"
        updated = self.room_service.update_room(room)
        assert updated

        stored = self.room_service.get_room_by_id(room.id)
        assert stored.room_name == "Nurse Room B"

    def test_delete_room(self):
        room = ClinicalRoom(room_name="Treatment Room", room_type="Treatment")
        room.id = self.room_service.create_room(room)
        deleted = self.room_service.delete_room(room.id)
        assert deleted

        stored = self.room_service.get_room_by_id(room.id)
        assert stored is None

    def test_room_items_count(self):
        room_name = "Emergency Room"
        self.room_service.create_room(ClinicalRoom(room_name=room_name))
        self.inventory_service.add_item(
            name="Bandage",
            barcode="BAND123",
            category="Dressings",
            current_quantity=50,
            minimum_quantity=10,
            maximum_quantity=100,
            clinical_room=room_name,
        )

        count = self.room_service.get_room_item_count(room_name)
        assert count == 1

    def test_get_items_in_room(self):
        room_name = "Treatment Room"
        self.room_service.create_room(ClinicalRoom(room_name=room_name))
        self.inventory_service.add_item(
            name="Syringe",
            barcode="SYR001",
            category="Needles",
            current_quantity=30,
            minimum_quantity=5,
            maximum_quantity=100,
            clinical_room=room_name,
        )

        items = self.room_service.get_items_in_room(room_name)
        assert len(items) == 1
        assert items[0].clinical_room == room_name
