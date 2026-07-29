# Development Guide

## Project Overview

MediStock AI is a modular, layered application using:
- **Presentation Layer:** CustomTkinter UI
- **Business Logic:** Service classes (AuthenticationService, InventoryService)
- **Data Access:** Database module with models
- **Storage:** SQLite (upgradeable to PostgreSQL/MSSQL)

## Architecture

```
┌─────────────────────┐
│   UI Layer (CTk)    │  <- User Interface (login, dashboard, inventory)
├─────────────────────┤
│  Service Layer      │  <- Business logic (auth, inventory, reporting)
├─────────────────────┤
│   Model Layer       │  <- Data structures (User, Item, StockMovement)
├─────────────────────┤
│   Database Layer    │  <- SQLite connection and queries
└─────────────────────┘
```

## Code Organization

### src/config.py
Central configuration file containing:
- Application constants
- Database paths
- UI dimensions and fonts
- Role definitions and permissions
- Stock levels and warnings
- Item categories

### src/database/
- `db.py` - Database connection, context managers, CRUD operations
- `schema.py` - SQL schema definitions and table creation

### src/models/
- `models.py` - Dataclass definitions for all entities (User, Item, etc.)

### src/services/
Business logic layer - implement features here:
- `auth_service.py` - Authentication, user management, password hashing
- `inventory_service.py` - Inventory CRUD, stock movements, queries

### src/ui/
CustomTkinter-based UI components:
- `main_window.py` - Application window and navigation
- `login_window.py` - Login form
- `dashboard.py` - Main dashboard view
- `inventory/` - Inventory management UI (to be implemented)

## Development Workflow

### 1. Adding a New Feature

**Example: Add supplier management UI**

1. Create the service class (`src/services/supplier_service.py`):
```python
class SupplierService:
    def __init__(self):
        self.db = get_database()
    
    def create_supplier(self, supplier: Supplier) -> Tuple[bool, str]:
        # Implementation
        pass
```

2. Create the UI component (`src/ui/supplier_list.py`):
```python
class SupplierListFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.supplier_service = SupplierService()
        # Implementation
```

3. Integrate into dashboard (`src/ui/dashboard.py`):
```python
def _show_suppliers(self):
    # Clear and show supplier frame
    pass
```

### 2. Database Changes

**Adding a new table:**

1. Update `src/database/schema.py` - add table SQL
2. Create corresponding model in `src/models/models.py`
3. Create service in `src/services/` with CRUD methods
4. The database will auto-initialize on first run

### 3. Testing Changes

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### 4. Code Style

Follow PEP 8:
```python
# Good
def create_inventory_item(self, item: Item) -> Tuple[bool, str]:
    """Create a new inventory item with validation."""
    pass

# Avoid
def createItem(self,i):
    pass
```

## Key Design Patterns

### Service Layer Pattern
Services handle business logic and interact with the database:
```python
class InventoryService:
    def __init__(self):
        self.db = get_database()  # Single responsibility
    
    def get_low_stock_items(self):
        # Business logic here
        pass
```

### Tuple Return Pattern
Services return `(success: bool, message: str, result: Optional[Any])`:
```python
success, message, item_id = service.create_item(item)
if success:
    show_success(message)
else:
    show_error(message)
```

### Context Manager Pattern
Database operations use context managers:
```python
with database.get_cursor() as cursor:
    cursor.execute(query)
    # Auto-commit or rollback
```

## Common Tasks

### Add a New UI Tab

1. Create frame class in `src/ui/`:
```python
class NewFeatureFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self._create_widgets()
    
    def _create_widgets(self):
        # Build UI
        pass
```

2. Add to dashboard navigation:
```python
# In dashboard.py
nav_buttons.append(("New Feature", self._show_new_feature))

def _show_new_feature(self):
    self._clear_frame()
    self.current_frame = NewFeatureFrame(self)
```

### Add a New Permission

1. Add to `UserRole` enum in `config.py`:
```python
class UserRole(Enum):
    NEW_ROLE = "new_role"
```

2. Add to `ROLE_PERMISSIONS` dict:
```python
ROLE_PERMISSIONS = {
    UserRole.NEW_ROLE: [
        "permission_1",
        "permission_2"
    ]
}
```

3. Check permissions in service:
```python
def restricted_operation(self, user: User):
    if "permission_1" not in ROLE_PERMISSIONS[UserRole(user.role)]:
        return False, "Permission denied"
```

### Add Database Migration

The current system auto-creates tables from `schema.py`.

For backward compatibility with existing data:
1. Add migration scripts in `src/database/migrations/`
2. Call in `db.py` initialization
3. Track schema version in a `schema_version` table

### Performance Optimization

1. **Database Indexes** - Already in schema.py for common queries
2. **Lazy Loading** - Load data only when displayed
3. **Caching** - Cache frequently accessed data like all items
4. **Batch Operations** - Use `execute_many()` for bulk inserts

## Debugging

### Enable Detailed Logging

In `src/app.py`, change log level:
```python
logging.basicConfig(level=logging.DEBUG)  # More verbose
```

View logs:
```bash
# Windows
Get-Content logs/app.log -Tail 50

# Linux/macOS
tail -50 logs/app.log
```

### Interactive Debugging

```python
# Add breakpoints with pdb
import pdb; pdb.set_trace()

# Or use breakpoint() in Python 3.7+
breakpoint()
```

## Phase 1 Roadmap

Status: **In Progress - Foundation Complete**

- [x] Database schema
- [x] User authentication
- [x] Core data models
- [x] UI framework
- [ ] Inventory CRUD UI
- [ ] Barcode scanner integration
- [ ] Stock movements UI
- [ ] Basic reports (PDF/Excel)
- [ ] Unit tests (80%+ coverage)

## Next Phase (Phase 2)

- Room inventory management
- Clinical audit workflow
- Stock transfer tracking
- Supplier management UI
- Purchase order generation

## Useful Commands

```bash
# Format code
black src/

# Check code quality
pylint src/

# Type checking
mypy src/

# Run application
python -m src.app

# Run tests
pytest tests/ -v

# Generate test coverage report
pytest --cov=src --cov-report=html
```

## Resources

- [CustomTkinter Docs](https://github.com/TomSchimansky/CustomTkinter)
- [Python SQLite](https://docs.python.org/3/library/sqlite3.html)
- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

## Contact & Questions

For development questions or issues, refer to this guide or check existing code comments.
