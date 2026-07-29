"""
Stock batch service.
Handles stock batch CRUD and lookup operations.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from src.database.db import get_database
from src.models.models import StockBatch
from src.services.time_sync_service import get_time_sync_service

logger = logging.getLogger(__name__)


class StockBatchService:
    """Service for stock batch management."""

    def __init__(self):
        self.db = get_database()
        self.time_sync_service = get_time_sync_service()

    def get_all_batches(self) -> List[StockBatch]:
        try:
            rows = self.db.fetch_all(
                """
                SELECT *
                FROM stock_batches
                ORDER BY
                    CASE WHEN expiry_date IS NULL THEN 1 ELSE 0 END,
                    expiry_date ASC,
                    batch_number ASC,
                    id ASC
                """
            )
            return [self._dict_to_stock_batch(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching stock batches: {e}")
            return []

    def get_batch_by_id(self, batch_id: int) -> Optional[StockBatch]:
        try:
            row = self.db.fetch_one("SELECT * FROM stock_batches WHERE id = ?", (batch_id,))
            return self._dict_to_stock_batch(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching stock batch by id: {e}")
            return None

    def get_batch_by_qr_code(self, qr_code: str) -> Optional[StockBatch]:
        try:
            row = self.db.fetch_one("SELECT * FROM stock_batches WHERE qr_code = ?", (qr_code,))
            return self._dict_to_stock_batch(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching stock batch by QR code: {e}")
            return None

    def get_batch_by_batch_number(self, batch_number: str) -> Optional[StockBatch]:
        try:
            row = self.db.fetch_one(
                "SELECT * FROM stock_batches WHERE batch_number = ? ORDER BY id DESC LIMIT 1",
                (batch_number,),
            )
            return self._dict_to_stock_batch(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching stock batch by batch number: {e}")
            return None

    def get_batches_by_item(self, item_id: int) -> List[StockBatch]:
        try:
            rows = self.db.fetch_all(
                "SELECT * FROM stock_batches WHERE item_id = ? ORDER BY expiry_date ASC, id ASC",
                (item_id,),
            )
            return [self._dict_to_stock_batch(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching stock batches by product: {e}")
            return []

    def get_batches_by_room(self, room_id: int) -> List[StockBatch]:
        try:
            rows = self.db.fetch_all(
                "SELECT * FROM stock_batches WHERE room_id = ? ORDER BY expiry_date ASC, id ASC",
                (room_id,),
            )
            return [self._dict_to_stock_batch(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching stock batches by room: {e}")
            return []

    def create_batch(self, batch: StockBatch) -> Tuple[bool, str, Optional[int]]:
        try:
            validation_message = self._validate_batch(batch)
            if validation_message:
                return False, validation_message, None

            batch_id = self.db.insert("stock_batches", batch.to_dict())
            return True, "Stock batch created successfully", batch_id
        except Exception as e:
            logger.error(f"Error creating stock batch: {e}")
            return False, f"Error creating stock batch: {str(e)}", None

    def update_batch(self, batch: StockBatch) -> Tuple[bool, str]:
        try:
            if not batch.id:
                return False, "Batch ID is required"

            validation_message = self._validate_batch(batch)
            if validation_message:
                return False, validation_message

            data = batch.to_dict()
            data.pop("id", None)
            data.pop("created_at", None)
            data["updated_at"] = self.time_sync_service.now()

            rows = self.db.update("stock_batches", data, "id = ?", (batch.id,))
            return (True, "Stock batch updated successfully") if rows > 0 else (False, "Stock batch not found")
        except Exception as e:
            logger.error(f"Error updating stock batch: {e}")
            return False, f"Error updating stock batch: {str(e)}"

    def delete_batch(self, batch_id: int) -> Tuple[bool, str]:
        try:
            rows = self.db.delete("stock_batches", "id = ?", (batch_id,))
            return (True, "Stock batch deleted successfully") if rows > 0 else (False, "Stock batch not found")
        except Exception as e:
            logger.error(f"Error deleting stock batch: {e}")
            return False, f"Error deleting stock batch: {str(e)}"

    def _validate_batch(self, batch: StockBatch) -> Optional[str]:
        if not batch.item_id:
            return "Product ID is required"
        if not (batch.batch_number or "").strip():
            return "Batch number is required"
        if batch.quantity_available < 0:
            return "Quantity available cannot be negative"
        if batch.expiry_period_after_opening is not None and batch.expiry_period_after_opening < 0:
            return "Expiry period after opening cannot be negative"
        if not (batch.status or "").strip():
            return "Status is required"
        if batch.qr_code:
            existing_batch = self.get_batch_by_qr_code(batch.qr_code)
            if existing_batch and existing_batch.id != batch.id:
                return "Batch with this QR code already exists"

        item = self.db.fetch_one("SELECT id FROM items WHERE id = ?", (batch.item_id,))
        if not item:
            return "Product not found"

        if batch.room_id is not None:
            room = self.db.fetch_one("SELECT id FROM clinical_rooms WHERE id = ?", (batch.room_id,))
            if not room:
                return "Room not found"

        return None

    @staticmethod
    def _dict_to_stock_batch(row: dict) -> Optional[StockBatch]:
        if not row:
            return None

        return StockBatch(
            id=row.get("id"),
            item_id=row.get("item_id", 0),
            room_id=row.get("room_id"),
            qr_code=row.get("qr_code"),
            batch_number=row.get("batch_number", ""),
            expiry_date=StockBatchService._parse_date(row.get("expiry_date")),
            quantity_available=row.get("quantity_available", 0),
            date_received=StockBatchService._parse_date(row.get("date_received")),
            opened_date=StockBatchService._parse_date(row.get("opened_date")),
            expiry_period_after_opening=row.get("expiry_period_after_opening"),
            storage_location=row.get("storage_location"),
            status=row.get("status") or "Active",
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    @staticmethod
    def _parse_date(value):
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).date()
            except Exception:
                return None
        return value
