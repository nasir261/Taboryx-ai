# Taboryx AI - Prison Healthcare Inventory Management System

A modern, intelligent inventory management system for prison healthcare settings built with Python and CustomTkinter.

## Features (Phase 1)

- **User Authentication** - Role-based access control with bcrypt password hashing
- **Inventory Management** - Add, edit, delete items with comprehensive fields
- **Barcode Support** - USB barcode scanner integration
- **Stock Movements** - Log all inventory changes with audit trail
- **Dashboard** - View key metrics and recent activities
- **Basic Reporting** - Export inventory data in multiple formats

## Installation

### Prerequisites
- Python 3.11 or higher
- Windows, macOS, or Linux

### Setup

1. Clone the repository:
```bash
cd project.inventory
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python -m src.app
```

## Demo Credentials

For testing, use the following credentials:
- **Username:** admin
- **Password:** password123

## Project Structure

```
src/
├── app.py                    # Main application entry point
├── config.py                 # Configuration and constants
├── database/
│   ├── db.py                # Database connection and management
│   └── schema.py            # Database schema definitions
├── models/
│   └── models.py            # Data models (User, Item, StockMovement, etc.)
├── services/
│   ├── auth_service.py      # Authentication and user management
│   └── inventory_service.py # Inventory operations
├── ui/
│   ├── main_window.py       # Main application window
│   ├── login_window.py      # Login interface
│   ├── dashboard.py         # Dashboard view
│   └── inventory/           # Inventory UI modules
└── utils/
    └── constants.py         # Application constants
```

## Development Phases

### Phase 1: Core Inventory ✓ (In Progress)
- User login and roles
- Inventory database schema
- Add/edit/delete items
- Barcode scanning
- Stock movements logging
- Basic reporting

### Phase 2: Clinical Operations (Planned)
- Room inventories
- Monthly audits
- Stock transfers
- Supplier management
- Purchase recommendations

### Phase 3: AI Features (Planned)
- Usage forecasting
- Expiry prediction
- Smart purchasing
- AI assistant

### Phase 4: Enterprise (Planned)
- Multi-site support
- Cloud synchronization
- NHS integration
- Mobile app

## Technology Stack

- **Frontend:** CustomTkinter
- **Backend:** Python 3.11+
- **Database:** SQLite (PostgreSQL/MSSQL supported with minimal changes)
- **Authentication:** bcrypt
- **Reporting:** ReportLab, openpyxl
- **Barcode:** pyzbar

## Role-Based Permissions

- **Administrator:** Full system access, user management, configuration
- **Pharmacy Staff:** Add/adjust stock, view purchasing reports
- **Doctor:** View stock, record usage, report shortages
- **Nurse:** Record usage, view expiry dates, perform audits
- **Healthcare Assistant:** View stock, record usage
- **Manager:** View reports and inventory

## Database

The system uses SQLite by default with the following key tables:
- **users** - User accounts and roles
- **items** - Inventory items
- **stock_movements** - All inventory transactions
- **suppliers** - Supplier information
- **clinical_rooms** - Room inventory locations
- **room_audits** - Audit records
- **purchase_orders** - Purchase order tracking

## Security Features

- Encrypted password storage (bcrypt)
- Role-based access control
- Audit logging of all changes
- Automatic session timeout
- Account lockout after failed attempts

## Next Steps

1. Create inventory CRUD UI
2. Implement barcode scanner integration
3. Add reporting functionality
4. Create sample data for testing
5. Implement advanced search and filtering

## Contributing

Please follow PEP 8 coding standards and include unit tests for new features.

## License

Copyright © 2026 Taboryx AI

## Support

For issues and questions, please refer to the documentation or contact the development team.
