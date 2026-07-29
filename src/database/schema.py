"""
Database Schema Definitions
Contains all SQL statements for creating tables and indexes
"""

SCHEMA = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    failed_login_attempts INTEGER DEFAULT 0,
    lockout_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Items (Inventory) table
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT UNIQUE NOT NULL,
    product_code TEXT,
    qr_code TEXT UNIQUE,
    item_name TEXT NOT NULL,
    generic_name TEXT,
    brand TEXT,
    category TEXT NOT NULL,
    manufacturer TEXT,
    supplier_id INTEGER,
    supplier_product_code TEXT,
    batch_number TEXT,
    expiry_date DATE,
    date_received DATE,
    purchase_price REAL,
    unit_of_measurement TEXT,
    current_quantity INTEGER DEFAULT 0,
    minimum_quantity INTEGER DEFAULT 10,
    maximum_quantity INTEGER DEFAULT 100,
    lead_time_days INTEGER,
    safety_stock_quantity INTEGER DEFAULT 0,
    storage_location TEXT,
    clinical_room TEXT,
    shelf TEXT,
    cabinet TEXT,
    temperature_requirement TEXT,
    is_controlled_drug BOOLEAN DEFAULT 0,
    requires_fridge BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    photo_path TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

-- Stock Movements table
CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    transaction_quantity INTEGER DEFAULT 0,
    quantity_change INTEGER NOT NULL,
    quantity_before INTEGER,
    quantity_after INTEGER,
    batch_id INTEGER,
    room_id INTEGER,
    from_room_id INTEGER,
    to_room_id INTEGER,
    user_id INTEGER NOT NULL,
    movement_date DATE DEFAULT CURRENT_DATE,
    movement_time TIME DEFAULT CURRENT_TIME,
    reason TEXT,
    patient_area TEXT,
    from_location TEXT,
    to_location TEXT,
    batch_number TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (batch_id) REFERENCES stock_batches(id),
    FOREIGN KEY (room_id) REFERENCES clinical_rooms(id),
    FOREIGN KEY (from_room_id) REFERENCES clinical_rooms(id),
    FOREIGN KEY (to_room_id) REFERENCES clinical_rooms(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Suppliers table
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL UNIQUE,
    address TEXT,
    telephone TEXT,
    email TEXT,
    website TEXT,
    lead_time_days INTEGER,
    contact_person TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clinical Rooms table
CREATE TABLE IF NOT EXISTS clinical_rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT NOT NULL UNIQUE,
    room_type TEXT,
    floor INTEGER,
    location_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sites table
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name TEXT NOT NULL,
    site_code TEXT NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stock Batches table
CREATE TABLE IF NOT EXISTS stock_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    room_id INTEGER,
    qr_code TEXT UNIQUE,
    batch_number TEXT NOT NULL,
    expiry_date DATE,
    quantity_available INTEGER DEFAULT 0,
    date_received DATE,
    opened_date DATE,
    expiry_period_after_opening INTEGER,
    storage_location TEXT,
    status TEXT DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES clinical_rooms(id) ON DELETE SET NULL
);

-- Fridge devices (Wi-Fi connected pharmacy fridges)
CREATE TABLE IF NOT EXISTS fridge_devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_name TEXT NOT NULL,
    device_code TEXT UNIQUE,
    location TEXT,
    room_id INTEGER,
    connection_type TEXT DEFAULT 'wifi',
    endpoint_url TEXT,
    min_temperature REAL,
    max_temperature REAL,
    notes TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES clinical_rooms(id)
);

CREATE TABLE IF NOT EXISTS fridge_temperature_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fridge_device_id INTEGER NOT NULL,
    temperature_c REAL NOT NULL,
    status TEXT DEFAULT 'normal',
    source TEXT DEFAULT 'wifi',
    notes TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fridge_device_id) REFERENCES fridge_devices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_fridge_devices_room ON fridge_devices(room_id);
CREATE INDEX IF NOT EXISTS idx_fridge_readings_device ON fridge_temperature_readings(fridge_device_id, recorded_at DESC);

-- Room Audits table
CREATE TABLE IF NOT EXISTS room_audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    audit_date DATE DEFAULT CURRENT_DATE,
    audit_time TIME DEFAULT CURRENT_TIME,
    audited_by_user_id INTEGER NOT NULL,
    status TEXT DEFAULT 'in_progress',
    total_items_checked INTEGER,
    missing_items_count INTEGER,
    expired_items_count INTEGER,
    quantity_discrepancies_count INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES clinical_rooms(id),
    FOREIGN KEY (audited_by_user_id) REFERENCES users(id)
);

-- Audit Items (items checked in an audit)
CREATE TABLE IF NOT EXISTS audit_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    expected_quantity INTEGER,
    actual_quantity INTEGER,
    quantity_discrepancy INTEGER,
    is_expired BOOLEAN DEFAULT 0,
    is_missing BOOLEAN DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (audit_id) REFERENCES room_audits(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

-- Stock Transfers table
CREATE TABLE IF NOT EXISTS stock_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    from_room_id INTEGER,
    to_room_id INTEGER,
    transfer_date DATE DEFAULT CURRENT_DATE,
    transfer_time TIME DEFAULT CURRENT_TIME,
    user_id INTEGER NOT NULL,
    reason TEXT,
    status TEXT DEFAULT 'completed',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (from_room_id) REFERENCES clinical_rooms(id),
    FOREIGN KEY (to_room_id) REFERENCES clinical_rooms(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Purchase Orders table
CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    order_date DATE DEFAULT CURRENT_DATE,
    expected_delivery_date DATE,
    actual_delivery_date DATE,
    status TEXT DEFAULT 'pending',
    total_amount REAL,
    notes TEXT,
    created_by_user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
);

-- Purchase Order Items table
CREATE TABLE IF NOT EXISTS purchase_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_order_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity_ordered INTEGER NOT NULL,
    quantity_received INTEGER DEFAULT 0,
    unit_price REAL,
    line_total REAL,
    notes TEXT,
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

-- Purchase Order Item Amendment Audit Trail
CREATE TABLE IF NOT EXISTS purchase_order_item_audit_trail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_order_id INTEGER NOT NULL,
    purchase_order_item_id INTEGER,
    item_id INTEGER,
    action TEXT NOT NULL,
    old_values TEXT,
    new_values TEXT,
    changed_by_user_id INTEGER,
    changed_by_username TEXT,
    change_reason TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id),
    FOREIGN KEY (changed_by_user_id) REFERENCES users(id)
);

-- Item Attachments
CREATE TABLE IF NOT EXISTS item_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT,
    title TEXT,
    notes TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

-- Audit Log table
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    table_name TEXT,
    record_id INTEGER,
    old_values TEXT,
    new_values TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Session tokens table (for tracking active sessions)
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    login_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Application settings (key-value)
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Active audit actor context (single-row table)
CREATE TABLE IF NOT EXISTS audit_context (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_user_id INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_user_id) REFERENCES users(id)
);
INSERT OR IGNORE INTO audit_context (id, current_user_id) VALUES (1, NULL);

-- Restrict transaction record deletion to administrators only when a user context exists
CREATE TRIGGER IF NOT EXISTS trg_protect_delete_stock_movements
BEFORE DELETE ON stock_movements
WHEN (SELECT current_user_id FROM audit_context WHERE id = 1) IS NOT NULL
 AND COALESCE(
    (SELECT LOWER(role) FROM users WHERE id = (SELECT current_user_id FROM audit_context WHERE id = 1)),
    ''
 ) != 'administrator'
BEGIN
    SELECT RAISE(ABORT, 'Only administrators can delete transaction records');
END;

CREATE TRIGGER IF NOT EXISTS trg_protect_delete_stock_transfers
BEFORE DELETE ON stock_transfers
WHEN (SELECT current_user_id FROM audit_context WHERE id = 1) IS NOT NULL
 AND COALESCE(
    (SELECT LOWER(role) FROM users WHERE id = (SELECT current_user_id FROM audit_context WHERE id = 1)),
    ''
 ) != 'administrator'
BEGIN
    SELECT RAISE(ABORT, 'Only administrators can delete transaction records');
END;

CREATE TRIGGER IF NOT EXISTS trg_protect_delete_room_audits
BEFORE DELETE ON room_audits
WHEN (SELECT current_user_id FROM audit_context WHERE id = 1) IS NOT NULL
 AND COALESCE(
    (SELECT LOWER(role) FROM users WHERE id = (SELECT current_user_id FROM audit_context WHERE id = 1)),
    ''
 ) != 'administrator'
BEGIN
    SELECT RAISE(ABORT, 'Only administrators can delete transaction records');
END;

CREATE TRIGGER IF NOT EXISTS trg_protect_delete_audit_items
BEFORE DELETE ON audit_items
WHEN (SELECT current_user_id FROM audit_context WHERE id = 1) IS NOT NULL
 AND COALESCE(
    (SELECT LOWER(role) FROM users WHERE id = (SELECT current_user_id FROM audit_context WHERE id = 1)),
    ''
 ) != 'administrator'
BEGIN
    SELECT RAISE(ABORT, 'Only administrators can delete transaction records');
END;

CREATE TRIGGER IF NOT EXISTS trg_protect_delete_purchase_orders
BEFORE DELETE ON purchase_orders
WHEN (SELECT current_user_id FROM audit_context WHERE id = 1) IS NOT NULL
 AND COALESCE(
    (SELECT LOWER(role) FROM users WHERE id = (SELECT current_user_id FROM audit_context WHERE id = 1)),
    ''
 ) != 'administrator'
BEGIN
    SELECT RAISE(ABORT, 'Only administrators can delete transaction records');
END;

CREATE TRIGGER IF NOT EXISTS trg_protect_delete_purchase_order_items
BEFORE DELETE ON purchase_order_items
WHEN (SELECT current_user_id FROM audit_context WHERE id = 1) IS NOT NULL
 AND COALESCE(
    (SELECT LOWER(role) FROM users WHERE id = (SELECT current_user_id FROM audit_context WHERE id = 1)),
    ''
 ) != 'administrator'
BEGIN
    SELECT RAISE(ABORT, 'Only administrators can delete transaction records');
END;

CREATE TRIGGER IF NOT EXISTS trg_protect_delete_purchase_order_item_audit
BEFORE DELETE ON purchase_order_item_audit_trail
WHEN (SELECT current_user_id FROM audit_context WHERE id = 1) IS NOT NULL
 AND COALESCE(
    (SELECT LOWER(role) FROM users WHERE id = (SELECT current_user_id FROM audit_context WHERE id = 1)),
    ''
 ) != 'administrator'
BEGIN
    SELECT RAISE(ABORT, 'Only administrators can delete transaction records');
END;

-- Global change auditing triggers (records who/when for core data changes)
CREATE TRIGGER IF NOT EXISTS trg_audit_users_insert
AFTER INSERT ON users
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'users', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_users_update
AFTER UPDATE ON users
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'users', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_users_delete
AFTER DELETE ON users
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'users', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_items_insert
AFTER INSERT ON items
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'items', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_items_update
AFTER UPDATE ON items
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'items', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_items_delete
AFTER DELETE ON items
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'items', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_suppliers_insert
AFTER INSERT ON suppliers
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'suppliers', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_suppliers_update
AFTER UPDATE ON suppliers
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'suppliers', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_suppliers_delete
AFTER DELETE ON suppliers
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'suppliers', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_clinical_rooms_insert
AFTER INSERT ON clinical_rooms
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'clinical_rooms', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_clinical_rooms_update
AFTER UPDATE ON clinical_rooms
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'clinical_rooms', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_clinical_rooms_delete
AFTER DELETE ON clinical_rooms
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'clinical_rooms', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_sites_insert
AFTER INSERT ON sites
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'sites', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_sites_update
AFTER UPDATE ON sites
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'sites', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_sites_delete
AFTER DELETE ON sites
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'sites', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_stock_batches_insert
AFTER INSERT ON stock_batches
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'stock_batches', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_stock_batches_update
AFTER UPDATE ON stock_batches
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'stock_batches', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_stock_batches_delete
AFTER DELETE ON stock_batches
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'stock_batches', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_room_audits_insert
AFTER INSERT ON room_audits
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'room_audits', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_room_audits_update
AFTER UPDATE ON room_audits
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'room_audits', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_room_audits_delete
AFTER DELETE ON room_audits
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'room_audits', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_audit_items_insert
AFTER INSERT ON audit_items
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'audit_items', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_audit_items_update
AFTER UPDATE ON audit_items
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'audit_items', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_audit_items_delete
AFTER DELETE ON audit_items
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'audit_items', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_stock_transfers_insert
AFTER INSERT ON stock_transfers
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'stock_transfers', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_stock_transfers_update
AFTER UPDATE ON stock_transfers
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'stock_transfers', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_stock_transfers_delete
AFTER DELETE ON stock_transfers
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'stock_transfers', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_stock_movements_insert
AFTER INSERT ON stock_movements
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'stock_movements', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_stock_movements_update
AFTER UPDATE ON stock_movements
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'stock_movements', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_stock_movements_delete
AFTER DELETE ON stock_movements
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'stock_movements', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_purchase_orders_insert
AFTER INSERT ON purchase_orders
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'purchase_orders', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_purchase_orders_update
AFTER UPDATE ON purchase_orders
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'purchase_orders', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_purchase_orders_delete
AFTER DELETE ON purchase_orders
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'purchase_orders', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_purchase_order_items_insert
AFTER INSERT ON purchase_order_items
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'purchase_order_items', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_purchase_order_items_update
AFTER UPDATE ON purchase_order_items
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'purchase_order_items', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_purchase_order_items_delete
AFTER DELETE ON purchase_order_items
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'purchase_order_items', OLD.id, CURRENT_TIMESTAMP);
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_item_attachments_insert
AFTER INSERT ON item_attachments
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'item_attachments', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_item_attachments_update
AFTER UPDATE ON item_attachments
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'item_attachments', NEW.id, CURRENT_TIMESTAMP);
END;
CREATE TRIGGER IF NOT EXISTS trg_audit_item_attachments_delete
AFTER DELETE ON item_attachments
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
    VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'item_attachments', OLD.id, CURRENT_TIMESTAMP);
END;

-- Create Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_items_barcode ON items(barcode);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
CREATE INDEX IF NOT EXISTS idx_items_supplier ON items(supplier_id);
CREATE INDEX IF NOT EXISTS idx_items_expiry ON items(expiry_date);
CREATE INDEX IF NOT EXISTS idx_items_room ON items(clinical_room);
CREATE INDEX IF NOT EXISTS idx_stock_movements_item ON stock_movements(item_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_user ON stock_movements(user_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_date ON stock_movements(movement_date);
CREATE INDEX IF NOT EXISTS idx_stock_movements_type ON stock_movements(movement_type);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_room_audits_room ON room_audits(room_id);
CREATE INDEX IF NOT EXISTS idx_room_audits_date ON room_audits(audit_date);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_po_item_audit_order ON purchase_order_item_audit_trail(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_po_item_audit_item ON purchase_order_item_audit_trail(purchase_order_item_id);
CREATE INDEX IF NOT EXISTS idx_app_settings_updated_at ON app_settings(updated_at);
CREATE INDEX IF NOT EXISTS idx_item_attachments_item ON item_attachments(item_id);
CREATE INDEX IF NOT EXISTS idx_stock_batches_item ON stock_batches(item_id);
CREATE INDEX IF NOT EXISTS idx_stock_batches_room ON stock_batches(room_id);
CREATE INDEX IF NOT EXISTS idx_stock_batches_expiry ON stock_batches(expiry_date);
"""

# Individual table creation statements for flexibility
USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    failed_login_attempts INTEGER DEFAULT 0,
    lockout_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT UNIQUE NOT NULL,
    qr_code TEXT UNIQUE,
    item_name TEXT NOT NULL,
    generic_name TEXT,
    brand TEXT,
    category TEXT NOT NULL,
    manufacturer TEXT,
    supplier_id INTEGER,
    batch_number TEXT,
    expiry_date DATE,
    date_received DATE,
    purchase_price REAL,
    current_quantity INTEGER DEFAULT 0,
    minimum_quantity INTEGER DEFAULT 10,
    maximum_quantity INTEGER DEFAULT 100,
    storage_location TEXT,
    clinical_room TEXT,
    shelf TEXT,
    cabinet TEXT,
    temperature_requirement TEXT,
    is_controlled_drug BOOLEAN DEFAULT 0,
    requires_fridge BOOLEAN DEFAULT 0,
    photo_path TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
)
"""
