"""
Tests for site service workflows.
"""

import tempfile
from pathlib import Path

from src.database.db import get_database, init_database
from src.models.models import Site
from src.services.site_service import SiteService


class TestSiteService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_sites.db"
        init_database(self.db_path)
        self.site_service = SiteService()

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_create_and_get_site(self):
        site = Site(site_name="North Healthcare Unit", site_code="NHU", is_active=True)
        success, message, site_id = self.site_service.create_site(site)
        assert success
        assert message == "Site created successfully"
        assert site_id is not None

        stored = self.site_service.get_site_by_id(site_id)
        assert stored is not None
        assert stored.site_id == site_id
        assert stored.site_name == "North Healthcare Unit"
        assert stored.site_code == "NHU"
        assert stored.is_active is True

    def test_update_site(self):
        success, _, site_id = self.site_service.create_site(Site(site_name="South Unit", site_code="SU"))
        assert success

        site = self.site_service.get_site_by_id(site_id)
        site.site_name = "South Unit Updated"
        site.is_active = False
        success, message = self.site_service.update_site(site)
        assert success
        assert message == "Site updated successfully"

        stored = self.site_service.get_site_by_id(site_id)
        assert stored.site_name == "South Unit Updated"
        assert stored.is_active is False

    def test_duplicate_site_code_rejected(self):
        success, _, _ = self.site_service.create_site(Site(site_name="Site One", site_code="DUP"))
        assert success

        success, message, site_id = self.site_service.create_site(Site(site_name="Site Two", site_code="dup"))
        assert not success
        assert message == "Site with this code already exists"
        assert site_id is None

    def test_delete_site(self):
        success, _, site_id = self.site_service.create_site(Site(site_name="Delete Site", site_code="DEL"))
        assert success

        success, message = self.site_service.delete_site(site_id)
        assert success
        assert message == "Site deleted successfully"
        assert self.site_service.get_site_by_id(site_id) is None
