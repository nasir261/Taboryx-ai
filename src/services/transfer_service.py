"""
Stock Transfer Service
Handles stock transfers between clinical rooms.
"""

import logging
from datetime import datetime, date
from typing import List, Optional, Tuple
from src.database.db import get_database
from src.models.models import StockTransfer, StockMovement
from src.services.inventory_service import InventoryService
from src.services.room_service import ClinicalRoomService
from src.services.time_sync_service import get_time_sync_service

logger = logging.getLogger(__name__)


class TransferService:
    """Service for stock transfer operations"""

    def __init__(self):
        self.db = get_database()
        self.inventory_service = InventoryService()
        self.room_service = ClinicalRoomService()
        self.time_sync_service = get_time_sync_service()

    def get_transfers(self, limit: int = 100) -> List[StockTransfer]:
        try:
            rows = self.db.fetch_all(
                "SELECT * FROM stock_transfers ORDER BY transfer_date DESC, transfer_time DESC LIMIT ?",
                (limit,)
            )
            return [self._dict_to_transfer(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching transfers: {e}")
            return []

    def create_transfer(self, transfer: StockTransfer) -> Tuple[bool, str, Optional[int]]:
        try:
            if transfer.quantity <= 0:
                return False, "Transfer quantity must be greater than zero", None

            if not transfer.item_id:
                return False, "Item ID is required", None

            if transfer.from_room_id is None or transfer.to_room_id is None:
                return False, "Both source and destination rooms are required", None

            if transfer.from_room_id == transfer.to_room_id:
                return False, "Source and destination rooms must be different", None

            item = self.inventory_service.get_item_by_id(transfer.item_id)
            if not item:
                return False, "Item not found", None

            from_room = self.room_service.get_room_by_id(transfer.from_room_id)
            to_room = self.room_service.get_room_by_id(transfer.to_room_id)
            if not from_room or not to_room:
                return False, "Source or destination room not found", None

            # Set transfer date and time if missing
            transfer.transfer_date = transfer.transfer_date or self.time_sync_service.today()
            transfer.transfer_time = transfer.transfer_time or self.time_sync_service.now().strftime("%H:%M:%S")
            transfer.status = transfer.status or "completed"

            transfer_id = self.db.insert("stock_transfers", transfer.to_dict())
            if not transfer_id:
                return False, "Failed to record transfer", None

            movement = StockMovement(
                item_id=transfer.item_id,
                movement_type="TRANSFERRED",
                transaction_quantity=transfer.quantity,
                quantity_change=0,
                user_id=transfer.user_id,
                room_id=transfer.to_room_id,
                from_room_id=transfer.from_room_id,
                to_room_id=transfer.to_room_id,
                movement_date=transfer.transfer_date,
                movement_time=transfer.transfer_time,
                reason=transfer.reason,
                patient_area=to_room.room_name,
                from_location=from_room.room_name,
                to_location=to_room.room_name,
                notes=transfer.notes,
            )
            success, message, _ = self.inventory_service.log_stock_movement(movement)
            if not success:
                return False, message, None

            # Update item location if whole item moved or if the item currently belongs to source room
            if from_room and to_room and item.clinical_room == from_room.room_name:
                if transfer.quantity >= item.current_quantity:
                    item.clinical_room = to_room.room_name
                    self.inventory_service.update_item(item)
            logger.info(
                f"Stock transfer recorded: item {item.id}, qty {transfer.quantity}, from {transfer.from_room_id} to {transfer.to_room_id}"
            )
            return True, f"Stock transfer recorded successfully | {self.time_sync_service.get_signature_stamp()}", transfer_id
        except Exception as e:
            logger.error(f"Error creating transfer: {e}")
            return False, f"Error creating transfer: {str(e)}", None

    def _dict_to_transfer(self, row: dict) -> StockTransfer:
        if not row:
            return None
        return StockTransfer(
            id=row.get("id"),
            item_id=row.get("item_id", 0),
            quantity=row.get("quantity", 0),
            from_room_id=row.get("from_room_id"),
            to_room_id=row.get("to_room_id"),
            transfer_date=row.get("transfer_date"),
            transfer_time=row.get("transfer_time"),
            user_id=row.get("user_id", 0),
            reason=row.get("reason"),
            status=row.get("status", ""),
            notes=row.get("notes"),
            created_at=row.get("created_at"),
        )
