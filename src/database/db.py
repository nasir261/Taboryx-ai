"""
Database Module
Handles SQLite database initialization, connection, and queries
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import date, datetime, time
import bcrypt
from src.config import DATABASE_PATH, DB_TIMEOUT
from src.database.schema import SCHEMA

# Register adapters for SQLite to handle Python date/time objects
sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_adapter(time, lambda t: t.isoformat())

logger = logging.getLogger(__name__)


class Database:
    """SQLite Database connection and management"""

    def __init__(self, db_path: Optional[Path] = None, seed_default_admin: Optional[bool] = None, seed_demo_data: Optional[bool] = None):
        self.db_path = db_path or DATABASE_PATH
        self.connection = None
        self._should_seed_default_admin = db_path is None if seed_default_admin is None else seed_default_admin
        self._should_seed_demo_data = db_path is None if seed_demo_data is None else seed_demo_data
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database with schema"""
        try:
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create connection
            self.connection = sqlite3.connect(
                str(self.db_path),
                timeout=DB_TIMEOUT,
                check_same_thread=False
            )
            self.connection.row_factory = sqlite3.Row

            # Enable foreign keys
            self.connection.execute("PRAGMA foreign_keys = ON")

            # Create schema
            self.connection.executescript(SCHEMA)
            self._ensure_schema_updates()
            if self._should_seed_default_admin:
                self._ensure_default_admin_user()
            if self._should_seed_demo_data:
                self._seed_demo_inventory()
            self.connection.commit()
 
            logger.info(f"Database initialized: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def _ensure_schema_updates(self):
        item_columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(items)").fetchall()}
        required_item_columns = {
            "product_code": "ALTER TABLE items ADD COLUMN product_code TEXT",
            "supplier_product_code": "ALTER TABLE items ADD COLUMN supplier_product_code TEXT",
            "unit_of_measurement": "ALTER TABLE items ADD COLUMN unit_of_measurement TEXT",
            "lead_time_days": "ALTER TABLE items ADD COLUMN lead_time_days INTEGER",
            "safety_stock_quantity": "ALTER TABLE items ADD COLUMN safety_stock_quantity INTEGER DEFAULT 0",
            "is_active": "ALTER TABLE items ADD COLUMN is_active BOOLEAN DEFAULT 1",
        }
        for column_name, statement in required_item_columns.items():
            if column_name not in item_columns:
                self.connection.execute(statement)

        self.connection.execute(
            """
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
            )
            """
        )
        batch_columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(stock_batches)").fetchall()}
        required_batch_columns = {
            "qr_code": "ALTER TABLE stock_batches ADD COLUMN qr_code TEXT",
        }
        for column_name, statement in required_batch_columns.items():
            if column_name not in batch_columns:
                self.connection.execute(statement)

        movement_columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(stock_movements)").fetchall()}
        required_movement_columns = {
            "transaction_quantity": "ALTER TABLE stock_movements ADD COLUMN transaction_quantity INTEGER DEFAULT 0",
            "batch_id": "ALTER TABLE stock_movements ADD COLUMN batch_id INTEGER",
            "room_id": "ALTER TABLE stock_movements ADD COLUMN room_id INTEGER",
            "from_room_id": "ALTER TABLE stock_movements ADD COLUMN from_room_id INTEGER",
            "to_room_id": "ALTER TABLE stock_movements ADD COLUMN to_room_id INTEGER",
        }
        for column_name, statement in required_movement_columns.items():
            if column_name not in movement_columns:
                self.connection.execute(statement)

        self.connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_audit_stock_batches_insert
            AFTER INSERT ON stock_batches
            BEGIN
                INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
                VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'insert', 'stock_batches', NEW.id, CURRENT_TIMESTAMP);
            END;
            """
        )
        self.connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_audit_stock_batches_update
            AFTER UPDATE ON stock_batches
            BEGIN
                INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
                VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'update', 'stock_batches', NEW.id, CURRENT_TIMESTAMP);
            END;
            """
        )
        self.connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_audit_stock_batches_delete
            AFTER DELETE ON stock_batches
            BEGIN
                INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp)
                VALUES ((SELECT current_user_id FROM audit_context WHERE id = 1), 'delete', 'stock_batches', OLD.id, CURRENT_TIMESTAMP);
            END;
            """
        )
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_stock_batches_item ON stock_batches(item_id)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_stock_batches_room ON stock_batches(room_id)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_stock_batches_expiry ON stock_batches(expiry_date)")
        self.connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_batches_qr_code ON stock_batches(qr_code)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_stock_movements_batch ON stock_movements(batch_id)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_stock_movements_room ON stock_movements(room_id)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_stock_movements_from_room ON stock_movements(from_room_id)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_stock_movements_to_room ON stock_movements(to_room_id)")

    def _ensure_default_admin_user(self):
        """Create the default admin account when the database is first initialized."""
        user_count = self.connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()[0]
        if user_count > 0:
            return

        password_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt(rounds=12)).decode("utf-8")
        self.connection.execute(
            """
            INSERT INTO users (
                username, email, password_hash, full_name, role, is_active, failed_login_attempts, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            ("admin", "admin@Taboryx.local", password_hash, "System Administrator", "administrator", True),
        )
        self.connection.commit()
        logger.info("Seeded default admin user 'admin' with password 'password123'")

    def _seed_demo_inventory(self):
        """Populate a small starter inventory when the app is first used."""
        item_count = self.connection.execute("SELECT COUNT(*) AS count FROM items").fetchone()[0]
        if item_count > 0:
            return

        sample_items = [
            {
                "barcode": "MED-1001",
                "item_name": "Insulin",
                "category": "Medicines",
                "current_quantity": 40,
                "minimum_quantity": 10,
                "maximum_quantity": 100,
                "purchase_price": 18.5,
                "clinical_room": "Treatment Room",
                "storage_location": "Fridge A",
                "notes": "Starter sample stock",
            },
            {
                "barcode": "PPE-2001",
                "item_name": "Exam Gloves",
                "category": "PPE",
                "current_quantity": 120,
                "minimum_quantity": 40,
                "maximum_quantity": 250,
                "purchase_price": 0.85,
                "clinical_room": "Nurse Room A",
                "storage_location": "Shelf 2",
                "notes": "Starter sample stock",
            },
            {
                "barcode": "CANN-3001",
                "item_name": "IV Cannula",
                "category": "Cannulas",
                "current_quantity": 80,
                "minimum_quantity": 20,
                "maximum_quantity": 150,
                "purchase_price": 1.25,
                "clinical_room": "Emergency Room",
                "storage_location": "Cabinet 1",
                "notes": "Starter sample stock",
            },
            {
                "barcode": "SYR-4001",
                "item_name": "Syringes",
                "category": "Syringes",
                "current_quantity": 60,
                "minimum_quantity": 15,
                "maximum_quantity": 120,
                "purchase_price": 0.35,
                "clinical_room": "GP Room 1",
                "storage_location": "Shelf 3",
                "notes": "Starter sample stock",
            },
        ]

        for item in sample_items:
            self.connection.execute(
                """
                INSERT INTO items (
                    barcode, item_name, category, current_quantity, minimum_quantity, maximum_quantity,
                    purchase_price, clinical_room, storage_location, notes, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    item["barcode"],
                    item["item_name"],
                    item["category"],
                    item["current_quantity"],
                    item["minimum_quantity"],
                    item["maximum_quantity"],
                    item["purchase_price"],
                    item["clinical_room"],
                    item["storage_location"],
                    item["notes"],
                ),
            )

        self.connection.commit()
        logger.info("Seeded starter inventory items for the first-run dashboard")

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single query"""
        with self.get_cursor() as cursor:
            return cursor.execute(query, params)

    def execute_many(self, query: str, params_list: List[tuple]):
        """Execute multiple queries with different parameters"""
        with self.get_cursor() as cursor:
            return cursor.executemany(query, params_list)

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch one record"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all records"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insert a record and return the last insert id"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        with self.get_cursor() as cursor:
            cursor.execute(query, tuple(data.values()))
            return cursor.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: str, where_params: tuple = ()):
        """Update records"""
        set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        values = tuple(data.values()) + where_params

        with self.get_cursor() as cursor:
            cursor.execute(query, values)
            return cursor.rowcount

    def delete(self, table: str, where: str, params: tuple = ()):
        """Delete records"""
        query = f"DELETE FROM {table} WHERE {where}"

        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def set_audit_user(self, user_id: Optional[int]):
        """Set current user context used by audit triggers."""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit_context (id, current_user_id, updated_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET current_user_id=excluded.current_user_id, updated_at=CURRENT_TIMESTAMP
                """,
                (user_id,),
            )

    def clear_audit_user(self):
        """Clear current audit user context."""
        self.set_audit_user(None)

    def get_audit_user(self) -> Optional[int]:
        """Return current user id stored in audit context."""
        row = self.fetch_one("SELECT current_user_id FROM audit_context WHERE id = 1")
        if not row:
            return None
        return row.get("current_user_id")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global database instance
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """Get or create the global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def init_database(db_path: Optional[Path] = None, seed_default_admin: Optional[bool] = None, seed_demo_data: Optional[bool] = None) -> Database:
    """Initialize the database"""
    global _db_instance
    _db_instance = Database(db_path, seed_default_admin=seed_default_admin, seed_demo_data=seed_demo_data)
    return _db_instance
