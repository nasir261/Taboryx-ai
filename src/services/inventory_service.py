"""
Inventory Service
Handles all inventory-related operations (CRUD, stock movements, etc.)
"""

import logging
import shutil
from datetime import datetime, date
from typing import Optional, List, Tuple
from pathlib import Path
from src.database.db import get_database
from src.models.models import Item, StockMovement
from src.config import StockMovementType, ATTACHMENTS_DIR, MAJOR_STOCK_ADJUSTMENT_CONFIRM_THRESHOLD
from src.services.auth_service import AuthenticationService
from src.services.stock_batch_service import StockBatchService
from src.services.time_sync_service import get_time_sync_service

logger = logging.getLogger(__name__)


class InventoryService:
    """Service for inventory management"""

    VALID_MOVEMENT_TYPES = {
        "RECEIVED",
        "USED",
        "ISSUED",
        "TRANSFERRED",
        "ADJUSTED",
        "QUARANTINED",
        "RETURNED",
        "DISPOSED",
        "EXPIRED",
        "LOST",
        "DAMAGED",
    }

    def __init__(self):
        self.db = get_database()
        self.stock_batch_service = StockBatchService()
        self.time_sync_service = get_time_sync_service()

    def get_item_by_barcode(self, barcode: str) -> Optional[Item]:
        """Fetch item by barcode"""
        try:
            item_dict = self.db.fetch_one(
                "SELECT * FROM items WHERE barcode = ?",
                (barcode,)
            )
            return self._dict_to_item(item_dict) if item_dict else None
        except Exception as e:
            logger.error(f"Error fetching item by barcode: {e}")
            return None

    def get_item_by_qr_code(self, qr_code: str) -> Optional[Item]:
        """Fetch item by QR code"""
        try:
            item_dict = self.db.fetch_one(
                "SELECT * FROM items WHERE qr_code = ?",
                (qr_code,)
            )
            return self._dict_to_item(item_dict) if item_dict else None
        except Exception as e:
            logger.error(f"Error fetching item by QR code: {e}")
            return None

    def get_item_by_id(self, item_id: int) -> Optional[Item]:
        """Fetch item by ID"""
        try:
            item_dict = self.db.fetch_one(
                "SELECT * FROM items WHERE id = ?",
                (item_id,)
            )
            return self._dict_to_item(item_dict) if item_dict else None
        except Exception as e:
            logger.error(f"Error fetching item by ID: {e}")
            return None

    def search_items(self, query: str, field: str = "item_name") -> List[Item]:
        """Search items by various fields"""
        try:
            allowed_fields = ["barcode", "item_name", "category", "supplier_id",
                            "batch_number", "clinical_room", "manufacturer", "product_code",
                            "supplier_product_code", "unit_of_measurement"]
            
            if field not in allowed_fields:
                field = "item_name"

            search_query = f"SELECT * FROM items WHERE {field} LIKE ? ORDER BY item_name"
            items_dict = self.db.fetch_all(search_query, (f"%{query}%",))
            
            return [self._dict_to_item(item) for item in items_dict]
        except Exception as e:
            logger.error(f"Error searching items: {e}")
            return []

    def get_all_items(self, limit: int = None) -> List[Item]:
        """Fetch all items"""
        try:
            query = "SELECT * FROM items ORDER BY item_name"
            if limit:
                query += f" LIMIT {limit}"
            
            items_dict = self.db.fetch_all(query)
            return [self._dict_to_item(item) for item in items_dict]
        except Exception as e:
            logger.error(f"Error fetching all items: {e}")
            return []

    def create_item(self, item: Item) -> Tuple[bool, str, Optional[int]]:
        """Create a new item"""
        try:
            if not item.barcode:
                return False, "Barcode is required", None

            # Check if barcode already exists
            existing = self.get_item_by_barcode(item.barcode)
            if existing:
                return False, "Item with this barcode already exists", None

            if item.qr_code:
                existing_qr = self.get_item_by_qr_code(item.qr_code)
                if existing_qr:
                    return False, "Item with this QR code already exists", None

            item_id = self.db.insert("items", item.to_dict())
            logger.info(f"Item created: {item.item_name} (ID: {item_id}, Barcode: {item.barcode})")
            return True, "Item created successfully", item_id

        except Exception as e:
            logger.error(f"Error creating item: {e}")
            return False, f"Error creating item: {str(e)}", None

    def add_item(self, name: str, generic_name: Optional[str] = None, brand: Optional[str] = None,
               barcode: Optional[str] = None, qr_code: Optional[str] = None, category: Optional[str] = None,
               manufacturer: Optional[str] = None, supplier_id: Optional[int] = None,
                batch_number: Optional[str] = None, expiry_date: Optional[date] = None,
                date_received: Optional[date] = None, purchase_price: Optional[float] = None,
                current_quantity: int = 0, minimum_quantity: int = 10, maximum_quantity: int = 100,
                storage_location: Optional[str] = None, clinical_room: Optional[str] = None,
                temperature_requirements: Optional[str] = None,
                controlled_drug: bool = False, requires_fridge: bool = False,
                notes: Optional[str] = None, product_code: Optional[str] = None,
                supplier_product_code: Optional[str] = None, unit_of_measurement: Optional[str] = None,
                lead_time_days: Optional[int] = None, safety_stock_quantity: int = 0,
                is_active: bool = True) -> Tuple[bool, str, Optional[int]]:
        """Add a new item (convenience method for UI)"""
        item = Item(
            item_name=name,
            generic_name=generic_name,
            brand=brand,
            barcode=barcode or "",
            qr_code=qr_code,
            product_code=product_code,
            category=category or "",
            manufacturer=manufacturer,
            supplier_id=supplier_id,
            supplier_product_code=supplier_product_code,
            batch_number=batch_number,
            expiry_date=expiry_date,
            date_received=date_received,
            purchase_price=purchase_price,
            unit_of_measurement=unit_of_measurement,
            current_quantity=current_quantity,
            minimum_quantity=minimum_quantity,
            maximum_quantity=maximum_quantity,
            lead_time_days=lead_time_days,
            safety_stock_quantity=safety_stock_quantity,
            storage_location=storage_location,
            clinical_room=clinical_room,
            temperature_requirement=temperature_requirements,
            is_controlled_drug=controlled_drug,
            requires_fridge=requires_fridge,
            is_active=is_active,
            notes=notes
        )
        return self.create_item(item)

    def update_item(self, item: Item) -> Tuple[bool, str]:
        """Update an existing item"""
        try:
            if not item.id:
                return False, "Item ID is required"

            if item.qr_code:
                existing_qr = self.get_item_by_qr_code(item.qr_code)
                if existing_qr and existing_qr.id != item.id:
                    return False, "Item with this QR code already exists"

            existing_item = self.get_item_by_id(item.id)
            if not existing_item:
                return False, "Item not found"

            quantity_delta = item.current_quantity - existing_item.current_quantity
            if quantity_delta != 0 and not self.db.get_audit_user():
                return False, "Quantity changes require an authenticated user transaction"

            data = item.to_dict()
            data.pop('id', None)
            data['updated_at'] = self.time_sync_service.now()
            if quantity_delta != 0:
                data['current_quantity'] = existing_item.current_quantity

            rows_updated = self.db.update("items", data, "id = ?", (item.id,))
            
            if rows_updated > 0:
                if quantity_delta != 0:
                    movement = StockMovement(
                        item_id=item.id,
                        movement_type="ADJUSTED",
                        transaction_quantity=abs(quantity_delta),
                        quantity_change=quantity_delta,
                        user_id=self.db.get_audit_user(),
                        movement_date=self.time_sync_service.today(),
                        movement_time=self.time_sync_service.now().strftime("%H:%M:%S"),
                        reason="Quantity updated from item record",
                        room_id=self._get_room_id_by_name(item.clinical_room),
                    )
                    success, message, _ = self.log_stock_movement(movement)
                    if not success:
                        return False, message
                logger.info(f"Item updated: {item.item_name} (ID: {item.id})")
                return True, "Item updated successfully"
            else:
                return False, "Item not found"

        except Exception as e:
            logger.error(f"Error updating item: {e}")
            return False, f"Error updating item: {str(e)}"

    def delete_item(self, item_id: int) -> Tuple[bool, str]:
        """Delete an item"""
        try:
            attachments = self.get_item_attachments(item_id)
            for attachment in attachments:
                self._delete_attachment_file(attachment.get("file_path"))
            self.db.delete("item_attachments", "item_id = ?", (item_id,))

            rows_deleted = self.db.delete("items", "id = ?", (item_id,))
            
            if rows_deleted > 0:
                logger.info(f"Item deleted (ID: {item_id})")
                return True, "Item deleted successfully"
            else:
                return False, "Item not found"

        except Exception as e:
            logger.error(f"Error deleting item: {e}")
            return False, f"Error deleting item: {str(e)}"

    def get_item_attachments(self, item_id: int) -> List[dict]:
        """Get attachments linked to an item."""
        return self.db.fetch_all(
            """
            SELECT *
            FROM item_attachments
            WHERE item_id = ?
            ORDER BY uploaded_at DESC, id DESC
            """,
            (item_id,),
        )

    def add_item_attachment(
        self,
        item_id: int,
        file_path: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        file_type: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """Copy a file to managed storage and link it to an item."""
        item = self.get_item_by_id(item_id)
        if not item:
            return False, "Item not found", None

        source_path = Path(file_path)
        if not source_path.exists() or not source_path.is_file():
            return False, "Attachment file not found", None

        item_dir = ATTACHMENTS_DIR / f"item_{item_id}"
        item_dir.mkdir(parents=True, exist_ok=True)
        copied_file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{source_path.name}"
        target_path = item_dir / copied_file_name
        shutil.copy2(source_path, target_path)

        resolved_type = (file_type or source_path.suffix.lstrip(".")).lower() or "file"
        attachment_id = self.db.insert(
            "item_attachments",
            {
                "item_id": item_id,
                "file_name": source_path.name,
                "file_path": str(target_path),
                "file_type": resolved_type,
                "title": title,
                "notes": notes,
            },
        )
        return True, "Attachment added", attachment_id

    def delete_item_attachment(self, attachment_id: int) -> Tuple[bool, str]:
        """Delete an item attachment record and managed file."""
        row = self.db.fetch_one("SELECT * FROM item_attachments WHERE id = ?", (attachment_id,))
        if not row:
            return False, "Attachment not found"

        self._delete_attachment_file(row.get("file_path"))
        rows_deleted = self.db.delete("item_attachments", "id = ?", (attachment_id,))
        if rows_deleted > 0:
            return True, "Attachment deleted"
        return False, "Attachment not found"

    def delete_item_with_admin_password(self, item_id: int, admin_password: str) -> Tuple[bool, str]:
        """Delete an item after validating administrator password."""
        admin_user = self._authenticate_admin(admin_password)
        if not admin_user:
            return False, "Invalid administrator password"

        return self.delete_item(item_id)

    def log_stock_movement(self, movement: StockMovement) -> Tuple[bool, str, Optional[int]]:
        """Log a stock movement"""
        try:
            if not movement.item_id or not movement.user_id:
                return False, "Item ID and User ID are required", None

            movement_type = (movement.movement_type or "").upper()
            if movement_type not in self.VALID_MOVEMENT_TYPES:
                return False, "Invalid transaction type", None
            movement.movement_type = movement_type

            # Get current item quantity
            item = self.get_item_by_id(movement.item_id)
            if not item:
                return False, "Item not found", None

            batch = None
            if movement.batch_id:
                batch = self.stock_batch_service.get_batch_by_id(movement.batch_id)
                if not batch:
                    return False, "Batch not found", None
                if batch.item_id != movement.item_id:
                    return False, "Batch does not belong to this product", None
            elif movement.batch_number:
                batch = self.stock_batch_service.get_batch_by_batch_number(movement.batch_number)
                if batch and batch.item_id == movement.item_id:
                    movement.batch_id = batch.id
                else:
                    batch = None

            if movement.transaction_quantity <= 0:
                movement.transaction_quantity = abs(movement.quantity_change)
            if movement.transaction_quantity <= 0:
                return False, "Transaction quantity must be greater than zero", None

            movement.quantity_before = item.current_quantity
            movement.quantity_after = max(0, item.current_quantity + movement.quantity_change)
            movement.movement_date = movement.movement_date or self.time_sync_service.today()
            movement.movement_time = movement.movement_time or self.time_sync_service.now().strftime("%H:%M:%S")
            if batch:
                movement.batch_number = movement.batch_number or batch.batch_number
                movement.room_id = movement.room_id or batch.room_id
            if movement.room_id is None:
                movement.room_id = self._get_room_id_by_name(item.clinical_room)

            # Insert movement record
            movement_id = self.db.insert("stock_movements", movement.to_dict())

            # Update item quantity
            self.db.update("items", {"current_quantity": movement.quantity_after}, "id = ?", (movement.item_id,))

            if batch:
                updated_batch_qty = max(0, batch.quantity_available + movement.quantity_change)
                batch.quantity_available = updated_batch_qty
                if movement.to_room_id is not None:
                    batch.room_id = movement.to_room_id
                elif movement.room_id is not None:
                    batch.room_id = movement.room_id
                if movement.to_location:
                    batch.storage_location = movement.to_location
                if movement_type == "QUARANTINED":
                    batch.status = "Quarantined"
                elif movement_type == "DISPOSED":
                    batch.status = "Disposed"
                elif movement_type == "RETURNED":
                    batch.status = "Returned"
                elif movement_type == "RECEIVED":
                    batch.status = "Active"
                batch_success, batch_message = self.stock_batch_service.update_batch(batch)
                if not batch_success:
                    return False, batch_message, None

            logger.info(f"Stock movement logged: Item {movement.item_id}, Type: {movement.movement_type}, "
                       f"Change: {movement.quantity_change}, User: {movement.user_id}")
            
            return True, f"Stock movement recorded successfully | {self.time_sync_service.get_signature_stamp()}", movement_id

        except Exception as e:
            logger.error(f"Error logging stock movement: {e}")
            return False, f"Error logging movement: {str(e)}", None

    def requires_movement_confirmation(self, movement_type: str, quantity: int) -> bool:
        normalized_type = (movement_type or "").upper()
        if normalized_type in {"DISPOSED", "TRANSFERRED"}:
            return True
        if normalized_type == "ADJUSTED" and abs(quantity) >= MAJOR_STOCK_ADJUSTMENT_CONFIRM_THRESHOLD:
            return True
        return False

    def get_low_stock_items(self, threshold_percent: int = 25) -> List[Item]:
        """Get items that are below minimum quantity threshold"""
        try:
            items = self.get_all_items()
            low_stock = []
            
            for item in items:
                if item.current_quantity <= item.minimum_quantity:
                    low_stock.append(item)
            
            return sorted(low_stock, key=lambda x: x.current_quantity)

        except Exception as e:
            logger.error(f"Error getting low stock items: {e}")
            return []

    def get_expired_items(self) -> List[Item]:
        """Get expired items"""
        try:
            items_dict = self.db.fetch_all(
                "SELECT * FROM items WHERE expiry_date < ? AND expiry_date IS NOT NULL",
                (date.today(),)
            )
            return [self._dict_to_item(item) for item in items_dict]
        except Exception as e:
            logger.error(f"Error getting expired items: {e}")
            return []

    def get_expiring_items(self, days: int) -> List[Item]:
        """Get items expiring within specified days"""
        try:
            items_dict = self.db.fetch_all(
                "SELECT * FROM items WHERE expiry_date BETWEEN DATE('now') AND DATE('now', '+' || ? || ' days')",
                (days,)
            )
            return [self._dict_to_item(item) for item in items_dict]
        except Exception as e:
            logger.error(f"Error getting expiring items: {e}")
            return []

    def get_stock_movements(self, item_id: Optional[int] = None, 
                           limit: int = 100) -> List[StockMovement]:
        """Get stock movements"""
        try:
            if item_id:
                query = "SELECT * FROM stock_movements WHERE item_id = ? ORDER BY movement_date DESC, movement_time DESC LIMIT ?"
                movements_dict = self.db.fetch_all(query, (item_id, limit))
            else:
                query = "SELECT * FROM stock_movements ORDER BY movement_date DESC, movement_time DESC LIMIT ?"
                movements_dict = self.db.fetch_all(query, (limit,))
            
            return [self._dict_to_movement(mov) for mov in movements_dict]
        except Exception as e:
            logger.error(f"Error getting stock movements: {e}")
            return []

    @staticmethod
    def _coerce_numeric_value(value) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            try:
                return float(stripped)
            except ValueError:
                return None
        return None

    def get_item_stock_value(self, item_id: int) -> float:
        """Calculate total stock value for an item"""
        try:
            item = self.get_item_by_id(item_id)
            if not item:
                return 0.0

            quantity = self._coerce_numeric_value(item.current_quantity)
            price = self._coerce_numeric_value(item.purchase_price)
            if quantity is None or price is None:
                return 0.0
            return quantity * price
        except Exception as e:
            logger.error(f"Error calculating stock value: {e}")
            return 0.0

    def get_total_inventory_value(self) -> float:
        """Calculate total inventory value"""
        try:
            items = self.get_all_items()
            total = sum(self.get_item_stock_value(item.id) for item in items if item.id)
            return total
        except Exception as e:
            logger.error(f"Error calculating total inventory value: {e}")
            return 0.0

    @staticmethod
    def _dict_to_item(item_dict: dict) -> Item:
        """Convert database row to Item object"""
        if not item_dict:
            return None
 
        expiry_date = item_dict.get('expiry_date')
        if isinstance(expiry_date, str):
            try:
                expiry_date = datetime.fromisoformat(expiry_date).date()
            except Exception:
                expiry_date = None
 
        date_received = item_dict.get('date_received')
        if isinstance(date_received, str):
            try:
                date_received = datetime.fromisoformat(date_received).date()
            except Exception:
                date_received = None
 
        return Item(
            id=item_dict.get('id'),
            barcode=item_dict.get('barcode', ''),
            product_code=item_dict.get('product_code'),
            qr_code=item_dict.get('qr_code'),
            item_name=item_dict.get('item_name', ''),
            generic_name=item_dict.get('generic_name'),
            brand=item_dict.get('brand'),
            category=item_dict.get('category', ''),
            manufacturer=item_dict.get('manufacturer'),
            supplier_id=item_dict.get('supplier_id'),
            supplier_product_code=item_dict.get('supplier_product_code'),
            batch_number=item_dict.get('batch_number'),
            expiry_date=expiry_date,
            date_received=date_received,
            purchase_price=item_dict.get('purchase_price'),
            unit_of_measurement=item_dict.get('unit_of_measurement'),
            current_quantity=item_dict.get('current_quantity', 0),
            minimum_quantity=item_dict.get('minimum_quantity', 10),
            maximum_quantity=item_dict.get('maximum_quantity', 100),
            lead_time_days=item_dict.get('lead_time_days'),
            safety_stock_quantity=item_dict.get('safety_stock_quantity', 0),
            storage_location=item_dict.get('storage_location'),
            clinical_room=item_dict.get('clinical_room'),
            shelf=item_dict.get('shelf'),
            cabinet=item_dict.get('cabinet'),
            temperature_requirement=item_dict.get('temperature_requirement'),
            is_controlled_drug=bool(item_dict.get('is_controlled_drug', False)),
            requires_fridge=bool(item_dict.get('requires_fridge', False)),
            is_active=bool(item_dict.get('is_active', True)),
            photo_path=item_dict.get('photo_path'),
            notes=item_dict.get('notes'),
            created_at=item_dict.get('created_at'),
            updated_at=item_dict.get('updated_at')
        )

    @staticmethod
    def _dict_to_movement(mov_dict: dict) -> StockMovement:
        """Convert database row to StockMovement object"""
        if not mov_dict:
            return None

        movement_date = mov_dict.get('movement_date')
        if isinstance(movement_date, str):
            try:
                movement_date = datetime.fromisoformat(movement_date).date()
            except Exception:
                movement_date = None

        movement_time = mov_dict.get('movement_time')
        if isinstance(movement_time, str):
            movement_time = movement_time

        return StockMovement(
            id=mov_dict.get('id'),
            item_id=mov_dict.get('item_id', 0),
            movement_type=mov_dict.get('movement_type', ''),
            transaction_quantity=mov_dict.get('transaction_quantity', 0),
            quantity_change=mov_dict.get('quantity_change', 0),
            quantity_before=mov_dict.get('quantity_before'),
            quantity_after=mov_dict.get('quantity_after'),
            batch_id=mov_dict.get('batch_id'),
            room_id=mov_dict.get('room_id'),
            from_room_id=mov_dict.get('from_room_id'),
            to_room_id=mov_dict.get('to_room_id'),
            user_id=mov_dict.get('user_id', 0),
            movement_date=movement_date,
            movement_time=movement_time,
            reason=mov_dict.get('reason'),
            patient_area=mov_dict.get('patient_area'),
            from_location=mov_dict.get('from_location'),
            to_location=mov_dict.get('to_location'),
            batch_number=mov_dict.get('batch_number'),
            notes=mov_dict.get('notes'),
            created_at=mov_dict.get('created_at')
        )

    def _authenticate_admin(self, password: str):
        if not password:
            return None
        admins = self.db.fetch_all(
            "SELECT id, username, password_hash FROM users WHERE is_active = 1 AND LOWER(role) = 'administrator'"
        )
        for row in admins:
            if AuthenticationService.verify_password(password, row.get("password_hash", "")):
                return row
        return None

    @staticmethod
    def _delete_attachment_file(file_path: Optional[str]):
        if not file_path:
            return
        path = Path(file_path)
        if path.exists() and path.is_file():
            path.unlink()

    def _get_room_id_by_name(self, room_name: Optional[str]) -> Optional[int]:
        if not room_name:
            return None
        row = self.db.fetch_one(
            "SELECT id FROM clinical_rooms WHERE LOWER(room_name) = LOWER(?)",
            (room_name,),
        )
        return row.get("id") if row else None
