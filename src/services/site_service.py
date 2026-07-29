"""
Site service.
Handles site CRUD and lookup operations.
"""

import logging
from typing import List, Optional, Tuple

from src.database.db import get_database
from src.models.models import Site

logger = logging.getLogger(__name__)


class SiteService:
    """Service for site management."""

    def __init__(self):
        self.db = get_database()

    def get_all_sites(self) -> List[Site]:
        try:
            rows = self.db.fetch_all("SELECT * FROM sites ORDER BY site_name")
            return [self._dict_to_site(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching sites: {e}")
            return []

    def get_site_by_id(self, site_id: int) -> Optional[Site]:
        try:
            row = self.db.fetch_one("SELECT * FROM sites WHERE id = ?", (site_id,))
            return self._dict_to_site(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching site by id: {e}")
            return None

    def get_site_by_code(self, site_code: str) -> Optional[Site]:
        try:
            row = self.db.fetch_one("SELECT * FROM sites WHERE LOWER(site_code) = LOWER(?)", (site_code,))
            return self._dict_to_site(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching site by code: {e}")
            return None

    def create_site(self, site: Site) -> Tuple[bool, str, Optional[int]]:
        try:
            validation_message = self._validate_site(site)
            if validation_message:
                return False, validation_message, None

            existing_code = self.get_site_by_code(site.site_code)
            if existing_code:
                return False, "Site with this code already exists", None

            site_id = self.db.insert("sites", site.to_dict())
            return True, "Site created successfully", site_id
        except Exception as e:
            logger.error(f"Error creating site: {e}")
            return False, f"Error creating site: {str(e)}", None

    def update_site(self, site: Site) -> Tuple[bool, str]:
        try:
            if not site.id:
                return False, "Site ID is required"

            validation_message = self._validate_site(site)
            if validation_message:
                return False, validation_message

            existing_code = self.get_site_by_code(site.site_code)
            if existing_code and existing_code.id != site.id:
                return False, "Site with this code already exists"

            data = site.to_dict()
            data.pop("id", None)
            rows = self.db.update("sites", data, "id = ?", (site.id,))
            return (True, "Site updated successfully") if rows > 0 else (False, "Site not found")
        except Exception as e:
            logger.error(f"Error updating site: {e}")
            return False, f"Error updating site: {str(e)}"

    def delete_site(self, site_id: int) -> Tuple[bool, str]:
        try:
            rows = self.db.delete("sites", "id = ?", (site_id,))
            return (True, "Site deleted successfully") if rows > 0 else (False, "Site not found")
        except Exception as e:
            logger.error(f"Error deleting site: {e}")
            return False, f"Error deleting site: {str(e)}"

    @staticmethod
    def _validate_site(site: Site) -> Optional[str]:
        if not (site.site_name or "").strip():
            return "Site name is required"
        if not (site.site_code or "").strip():
            return "Site code is required"
        return None

    @staticmethod
    def _dict_to_site(row: dict) -> Optional[Site]:
        if not row:
            return None
        return Site(
            id=row.get("id"),
            site_name=row.get("site_name", ""),
            site_code=row.get("site_code", ""),
            is_active=bool(row.get("is_active", True)),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
