"""
Data Models
Core data classes for the application
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from enum import Enum


@dataclass
class User:
    """User model"""
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    password_hash: str = ""
    full_name: str = ""
    role: str = ""
    is_active: bool = True
    failed_login_attempts: int = 0
    lockout_until: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'failed_login_attempts': self.failed_login_attempts,
            'lockout_until': self.lockout_until,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class Item:
    """Item (Inventory) model"""
    id: Optional[int] = None
    barcode: str = ""
    product_code: Optional[str] = None
    qr_code: Optional[str] = None
    item_name: str = ""
    generic_name: Optional[str] = None
    brand: Optional[str] = None
    category: str = ""
    manufacturer: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_product_code: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    date_received: Optional[date] = None
    purchase_price: Optional[float] = None
    unit_of_measurement: Optional[str] = None
    current_quantity: int = 0
    minimum_quantity: int = 10
    maximum_quantity: int = 100
    lead_time_days: Optional[int] = None
    safety_stock_quantity: int = 0
    storage_location: Optional[str] = None
    clinical_room: Optional[str] = None
    shelf: Optional[str] = None
    cabinet: Optional[str] = None
    temperature_requirement: Optional[str] = None
    is_controlled_drug: bool = False
    requires_fridge: bool = False
    is_active: bool = True
    photo_path: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def name(self) -> str:
        """Alias for item_name"""
        return self.item_name

    @name.setter
    def name(self, value: str):
        """Set item_name via alias"""
        self.item_name = value

    @property
    def controlled_drug(self) -> bool:
        """Alias for is_controlled_drug"""
        return self.is_controlled_drug

    @controlled_drug.setter
    def controlled_drug(self, value: bool):
        """Set is_controlled_drug via alias"""
        self.is_controlled_drug = value

    @property
    def product_id(self) -> Optional[int]:
        return self.id

    @property
    def minimum_stock_level(self) -> int:
        return self.minimum_quantity

    @minimum_stock_level.setter
    def minimum_stock_level(self, value: int):
        self.minimum_quantity = value

    @property
    def target_stock_level(self) -> int:
        return self.maximum_quantity

    @target_stock_level.setter
    def target_stock_level(self, value: int):
        self.maximum_quantity = value

    @property
    def active_status(self) -> bool:
        return self.is_active

    @active_status.setter
    def active_status(self, value: bool):
        self.is_active = value

    @property
    def temperature_requirements(self) -> Optional[str]:
        """Alias for temperature_requirement"""
        return self.temperature_requirement

    @temperature_requirements.setter
    def temperature_requirements(self, value: Optional[str]):
        """Set temperature_requirement via alias"""
        self.temperature_requirement = value

    @property
    def stock_status(self) -> str:
        """Determine stock status"""
        if self.current_quantity <= 0:
            return "OUT_OF_STOCK"
        elif self.current_quantity < self.minimum_quantity:
            return "LOW_STOCK"
        elif self.current_quantity > self.maximum_quantity:
            return "OVERSTOCK"
        return "NORMAL"

    @property
    def is_expired(self) -> bool:
        """Check if item is expired"""
        if not self.expiry_date:
            return False
        return date.today() >= self.expiry_date

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'barcode': self.barcode,
            'product_code': self.product_code,
            'qr_code': self.qr_code,
            'item_name': self.item_name,
            'generic_name': self.generic_name,
            'brand': self.brand,
            'category': self.category,
            'manufacturer': self.manufacturer,
            'supplier_id': self.supplier_id,
            'supplier_product_code': self.supplier_product_code,
            'batch_number': self.batch_number,
            'expiry_date': self.expiry_date,
            'date_received': self.date_received,
            'purchase_price': self.purchase_price,
            'unit_of_measurement': self.unit_of_measurement,
            'current_quantity': self.current_quantity,
            'minimum_quantity': self.minimum_quantity,
            'maximum_quantity': self.maximum_quantity,
            'lead_time_days': self.lead_time_days,
            'safety_stock_quantity': self.safety_stock_quantity,
            'storage_location': self.storage_location,
            'clinical_room': self.clinical_room,
            'shelf': self.shelf,
            'cabinet': self.cabinet,
            'temperature_requirement': self.temperature_requirement,
            'is_controlled_drug': self.is_controlled_drug,
            'requires_fridge': self.requires_fridge,
            'is_active': self.is_active,
            'photo_path': self.photo_path,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class StockMovement:
    """Stock movement record"""
    id: Optional[int] = None
    item_id: int = 0
    movement_type: str = ""
    transaction_quantity: int = 0
    quantity_change: int = 0
    quantity_before: Optional[int] = None
    quantity_after: Optional[int] = None
    batch_id: Optional[int] = None
    room_id: Optional[int] = None
    from_room_id: Optional[int] = None
    to_room_id: Optional[int] = None
    user_id: int = 0
    movement_date: Optional[date] = None
    movement_time: Optional[str] = None
    reason: Optional[str] = None
    patient_area: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    batch_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        movement_date = self.movement_date.isoformat() if self.movement_date else None
        movement_time = self.movement_time
        if movement_time and not isinstance(movement_time, str):
            movement_time = movement_time.strftime("%H:%M:%S")

        return {
            'id': self.id,
            'item_id': self.item_id,
            'movement_type': self.movement_type,
            'transaction_quantity': self.transaction_quantity,
            'quantity_change': self.quantity_change,
            'quantity_before': self.quantity_before,
            'quantity_after': self.quantity_after,
            'batch_id': self.batch_id,
            'room_id': self.room_id,
            'from_room_id': self.from_room_id,
            'to_room_id': self.to_room_id,
            'user_id': self.user_id,
            'movement_date': movement_date,
            'movement_time': movement_time,
            'reason': self.reason,
            'patient_area': self.patient_area,
            'from_location': self.from_location,
            'to_location': self.to_location,
            'batch_number': self.batch_number,
            'notes': self.notes,
            'created_at': self.created_at
        }

    @property
    def transaction_id(self) -> Optional[int]:
        return self.id

    @property
    def product_id(self) -> int:
        return self.item_id

    @product_id.setter
    def product_id(self, value: int):
        self.item_id = value

    @property
    def transaction_type(self) -> str:
        return self.movement_type

    @transaction_type.setter
    def transaction_type(self, value: str):
        self.movement_type = value

    @property
    def quantity(self) -> int:
        if self.transaction_quantity:
            return self.transaction_quantity
        return abs(self.quantity_change)

    @quantity.setter
    def quantity(self, value: int):
        self.transaction_quantity = value

    @property
    def previous_quantity(self) -> Optional[int]:
        return self.quantity_before

    @previous_quantity.setter
    def previous_quantity(self, value: Optional[int]):
        self.quantity_before = value

    @property
    def new_quantity(self) -> Optional[int]:
        return self.quantity_after

    @new_quantity.setter
    def new_quantity(self, value: Optional[int]):
        self.quantity_after = value

    @property
    def user(self) -> int:
        return self.user_id

    @user.setter
    def user(self, value: int):
        self.user_id = value


@dataclass
class Supplier:
    """Supplier model"""
    id: Optional[int] = None
    supplier_name: str = ""
    address: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    lead_time_days: Optional[int] = None
    contact_person: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'supplier_name': self.supplier_name,
            'address': self.address,
            'telephone': self.telephone,
            'email': self.email,
            'website': self.website,
            'lead_time_days': self.lead_time_days,
            'contact_person': self.contact_person,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class ClinicalRoom:
    """Clinical room model"""
    id: Optional[int] = None
    room_name: str = ""
    room_type: Optional[str] = None
    floor: Optional[int] = None
    location_description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'room_name': self.room_name,
            'room_type': self.room_type,
            'floor': self.floor,
            'location_description': self.location_description,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class Site:
    """Site model"""
    id: Optional[int] = None
    site_name: str = ""
    site_code: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def site_id(self) -> Optional[int]:
        return self.id

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'site_name': self.site_name,
            'site_code': self.site_code,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


@dataclass
class StockBatch:
    """Stock batch model"""
    id: Optional[int] = None
    item_id: int = 0
    room_id: Optional[int] = None
    qr_code: Optional[str] = None
    batch_number: str = ""
    expiry_date: Optional[date] = None
    quantity_available: int = 0
    date_received: Optional[date] = None
    opened_date: Optional[date] = None
    expiry_period_after_opening: Optional[int] = None
    storage_location: Optional[str] = None
    status: str = "Active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def batch_id(self) -> Optional[int]:
        return self.id

    @property
    def product_id(self) -> int:
        return self.item_id

    @product_id.setter
    def product_id(self, value: int):
        self.item_id = value

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'item_id': self.item_id,
            'room_id': self.room_id,
            'qr_code': self.qr_code,
            'batch_number': self.batch_number,
            'expiry_date': self.expiry_date,
            'quantity_available': self.quantity_available,
            'date_received': self.date_received,
            'opened_date': self.opened_date,
            'expiry_period_after_opening': self.expiry_period_after_opening,
            'storage_location': self.storage_location,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


@dataclass
class RoomAudit:
    """Room audit record"""
    id: Optional[int] = None
    room_id: int = 0
    audit_date: Optional[date] = None
    audit_time: Optional[str] = None
    audited_by_user_id: int = 0
    status: str = "in_progress"
    total_items_checked: Optional[int] = None
    missing_items_count: Optional[int] = None
    expired_items_count: Optional[int] = None
    quantity_discrepancies_count: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'room_id': self.room_id,
            'audit_date': self.audit_date,
            'audit_time': self.audit_time,
            'audited_by_user_id': self.audited_by_user_id,
            'status': self.status,
            'total_items_checked': self.total_items_checked,
            'missing_items_count': self.missing_items_count,
            'expired_items_count': self.expired_items_count,
            'quantity_discrepancies_count': self.quantity_discrepancies_count,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


@dataclass
class AuditItem:
    """Item record for a room audit"""
    id: Optional[int] = None
    audit_id: int = 0
    item_id: int = 0
    expected_quantity: Optional[int] = None
    actual_quantity: Optional[int] = None
    quantity_discrepancy: Optional[int] = None
    is_expired: bool = False
    is_missing: bool = False
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'audit_id': self.audit_id,
            'item_id': self.item_id,
            'expected_quantity': self.expected_quantity,
            'actual_quantity': self.actual_quantity,
            'quantity_discrepancy': self.quantity_discrepancy,
            'is_expired': int(self.is_expired),
            'is_missing': int(self.is_missing),
            'notes': self.notes,
        }


@dataclass
class StockTransfer:
    """Stock transfer record"""
    id: Optional[int] = None
    item_id: int = 0
    quantity: int = 0
    from_room_id: Optional[int] = None
    to_room_id: Optional[int] = None
    transfer_date: Optional[date] = None
    transfer_time: Optional[str] = None
    user_id: int = 0
    reason: Optional[str] = None
    status: str = "completed"
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'item_id': self.item_id,
            'quantity': self.quantity,
            'from_room_id': self.from_room_id,
            'to_room_id': self.to_room_id,
            'transfer_date': self.transfer_date,
            'transfer_time': self.transfer_time,
            'user_id': self.user_id,
            'reason': self.reason,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at,
        }


@dataclass
class PurchaseOrder:
    """Purchase order model"""
    id: Optional[int] = None
    supplier_id: int = 0
    order_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    status: str = "pending"
    total_amount: Optional[float] = None
    notes: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'order_date': self.order_date,
            'expected_delivery_date': self.expected_delivery_date,
            'actual_delivery_date': self.actual_delivery_date,
            'status': self.status,
            'total_amount': self.total_amount,
            'notes': self.notes,
            'created_by_user_id': self.created_by_user_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
