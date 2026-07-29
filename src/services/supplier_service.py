"""
Supplier Service
Handles supplier CRUD and lookup operations.
"""

import logging
from typing import List, Optional, Tuple
from src.database.db import get_database
from src.models.models import Supplier

logger = logging.getLogger(__name__)


class SupplierService:
    """Service for supplier management"""

    def __init__(self):
        self.db = get_database()

    def get_all_suppliers(self) -> List[Supplier]:
        try:
            rows = self.db.fetch_all("SELECT * FROM suppliers ORDER BY supplier_name")
            return [self._dict_to_supplier(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching suppliers: {e}")
            return []

    def get_supplier_by_id(self, supplier_id: int) -> Optional[Supplier]:
        try:
            row = self.db.fetch_one("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
            return self._dict_to_supplier(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching supplier by id: {e}")
            return None

    def get_supplier_by_name(self, name: str) -> Optional[Supplier]:
        try:
            row = self.db.fetch_one(
                "SELECT * FROM suppliers WHERE LOWER(supplier_name) = LOWER(?)",
                (name,)
            )
            return self._dict_to_supplier(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching supplier by name: {e}")
            return None

    def search_suppliers(self, query: str) -> List[Supplier]:
        try:
            rows = self.db.fetch_all(
                "SELECT * FROM suppliers WHERE supplier_name LIKE ? OR email LIKE ? ORDER BY supplier_name",
                (f"%{query}%", f"%{query}%"),
            )
            return [self._dict_to_supplier(row) for row in rows]
        except Exception as e:
            logger.error(f"Error searching suppliers: {e}")
            return []

    def create_supplier(self, supplier: Supplier) -> Tuple[bool, str, Optional[int]]:
        try:
            if not supplier.supplier_name:
                return False, "Supplier name is required", None

            existing = self.get_supplier_by_name(supplier.supplier_name)
            if existing:
                return False, "Supplier with this name already exists", None

            supplier_id = self.db.insert("suppliers", supplier.to_dict())
            return True, "Supplier created successfully", supplier_id
        except Exception as e:
            logger.error(f"Error creating supplier: {e}")
            return False, f"Error creating supplier: {str(e)}", None

    def update_supplier(self, supplier: Supplier) -> Tuple[bool, str]:
        try:
            if not supplier.id:
                return False, "Supplier ID is required"

            data = supplier.to_dict()
            data.pop("id", None)
            rows = self.db.update("suppliers", data, "id = ?", (supplier.id,))
            return (True, "Supplier updated successfully") if rows > 0 else (False, "Supplier not found")
        except Exception as e:
            logger.error(f"Error updating supplier: {e}")
            return False, f"Error updating supplier: {str(e)}"

    def delete_supplier(self, supplier_id: int) -> Tuple[bool, str]:
        try:
            rows = self.db.delete("suppliers", "id = ?", (supplier_id,))
            return (True, "Supplier deleted successfully") if rows > 0 else (False, "Supplier not found")
        except Exception as e:
            logger.error(f"Error deleting supplier: {e}")
            return False, f"Error deleting supplier: {str(e)}"

    def _dict_to_supplier(self, row: dict) -> Supplier:
        if not row:
            return None
        return Supplier(
            id=row.get("id"),
            supplier_name=row.get("supplier_name", ""),
            address=row.get("address"),
            telephone=row.get("telephone"),
            email=row.get("email"),
            website=row.get("website"),
            lead_time_days=row.get("lead_time_days"),
            contact_person=row.get("contact_person"),
            notes=row.get("notes"),
            is_active=bool(row.get("is_active", True)),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
