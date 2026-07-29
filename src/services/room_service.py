"""
Clinical Room Service
Handles clinical room CRUD and inventory lookups.
"""

import logging
from typing import List, Optional
from src.database.db import get_database
from src.models.models import ClinicalRoom, Item
from src.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class ClinicalRoomService:
    """Service for managing clinical rooms"""

    def __init__(self):
        self.db = get_database()
        self.inventory_service = InventoryService()

    def get_all_rooms(self) -> List[ClinicalRoom]:
        """Fetch all clinical rooms"""
        try:
            rows = self.db.fetch_all("SELECT * FROM clinical_rooms ORDER BY room_name")
            return [self._dict_to_room(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching clinical rooms: {e}")
            return []

    def get_room_by_id(self, room_id: int) -> Optional[ClinicalRoom]:
        """Fetch a single room by ID"""
        try:
            row = self.db.fetch_one("SELECT * FROM clinical_rooms WHERE id = ?", (room_id,))
            return self._dict_to_room(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching clinical room by id: {e}")
            return None

    def create_room(self, room: ClinicalRoom) -> Optional[int]:
        """Create a new clinical room"""
        try:
            if not room.room_name:
                raise ValueError("Room name is required")

            existing = self.db.fetch_one(
                "SELECT id FROM clinical_rooms WHERE room_name = ?", (room.room_name,)
            )
            if existing:
                raise ValueError("A room with that name already exists")

            return self.db.insert("clinical_rooms", room.to_dict())
        except Exception as e:
            logger.error(f"Error creating clinical room: {e}")
            raise

    def update_room(self, room: ClinicalRoom) -> bool:
        """Update an existing clinical room"""
        try:
            if not room.id:
                raise ValueError("Room ID is required")
            data = room.to_dict()
            data.pop("id", None)
            rows = self.db.update("clinical_rooms", data, "id = ?", (room.id,))
            return rows > 0
        except Exception as e:
            logger.error(f"Error updating clinical room: {e}")
            raise

    def delete_room(self, room_id: int) -> bool:
        """Delete a clinical room"""
        try:
            rows = self.db.delete("clinical_rooms", "id = ?", (room_id,))
            return rows > 0
        except Exception as e:
            logger.error(f"Error deleting clinical room: {e}")
            raise

    def get_items_in_room(self, room_name: str) -> List[Item]:
        """Get all inventory items assigned to a room"""
        return self.inventory_service.search_items(room_name, field="clinical_room")

    def get_room_item_count(self, room_name: str) -> int:
        """Get the number of items assigned to a room"""
        items = self.get_items_in_room(room_name)
        return len(items)

    def _dict_to_room(self, row: dict) -> ClinicalRoom:
        if not row:
            return None
        return ClinicalRoom(
            id=row.get("id"),
            room_name=row.get("room_name", ""),
            room_type=row.get("room_type"),
            floor=row.get("floor"),
            location_description=row.get("location_description"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
