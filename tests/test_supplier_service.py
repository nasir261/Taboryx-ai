import tempfile
from pathlib import Path
from src.database.db import init_database, get_database
from src.services.supplier_service import SupplierService
from src.services.inventory_service import InventoryService
from src.models.models import Supplier


def test_supplier_crud_and_item_supplier_link():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_database(db_path)
        try:
            supplier_service = SupplierService()
            inventory_service = InventoryService()

            supplier = Supplier(
                supplier_name="Pharma Supplies Ltd",
                address="1 Healthcare Way",
                telephone="01234 567890",
                email="contact@pharmasupplies.example",
                lead_time_days=7,
                contact_person="Jane Doe",
                notes="Preferred supplier for medicines",
            )

            success, message, supplier_id = supplier_service.create_supplier(supplier)
            assert success is True
            assert supplier_id is not None

            fetched = supplier_service.get_supplier_by_id(supplier_id)
            assert fetched is not None
            assert fetched.supplier_name == "Pharma Supplies Ltd"
            assert fetched.email == "contact@pharmasupplies.example"

            fetched_by_name = supplier_service.get_supplier_by_name("Pharma Supplies Ltd")
            assert fetched_by_name is not None
            assert fetched_by_name.id == supplier_id

            fetched.telephone = "09876 543210"
            success, _ = supplier_service.update_supplier(fetched)
            assert success is True

            updated = supplier_service.get_supplier_by_id(supplier_id)
            assert updated.telephone == "09876 543210"

            success, message, item_id = inventory_service.add_item(
                name="Aspirin",
                generic_name="Acetylsalicylic acid",
                brand="HealthCare",
                barcode="ASP123456",
                category="Medicines",
                manufacturer="Health Labs",
                supplier_id=supplier_id,
                batch_number="BATCH001",
                expiry_date=None,
                date_received=None,
                purchase_price=2.50,
                current_quantity=50,
                minimum_quantity=10,
                maximum_quantity=200,
                storage_location="Pharmacy Shelf 1",
                clinical_room="Pharmacy",
                temperature_requirements="Room temperature",
                controlled_drug=False,
                requires_fridge=False,
                notes="For general pain relief",
            )

            assert success is True
            assert item_id is not None

            item = inventory_service.get_item_by_id(item_id)
            assert item is not None
            assert item.supplier_id == supplier_id
            assert item.item_name == "Aspirin"
        finally:
            get_database().close()
