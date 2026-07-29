# Installation & Setup Guide

## System Requirements

- **Python 3.11 or higher** (required)
- Windows 10/11, macOS 10.14+, or Linux (any recent distro)
- Minimum 2GB RAM
- 500MB disk space

## Installation Steps

### 1. Install Python

If Python is not installed:

**Windows:**
- Download from https://www.python.org/downloads/
- **IMPORTANT:** Check "Add Python to PATH" during installation
- Verify: Open PowerShell and run `python --version`

**macOS:**
```bash
brew install python3
python3 --version
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install python3 python3-venv python3-pip
python3 --version
```

### 2. Clone/Navigate to Project

```bash
cd project.inventory
```

### 3. Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Expected output: "Successfully installed [packages...]"

### 5. Run the Application

```bash
python -m src.app
```

Or directly:

```bash
python src/app.py
```

The login window should appear.

## Verification Steps

After installation, verify everything is working:

```bash
# Check Python version
python --version

# Check virtual environment is active (you should see (venv) in your prompt)

# Test database initialization
python -c "from src.database.db import init_database; init_database()"

# Run tests
pytest tests/test_models.py -v
```

## Troubleshooting

### Python not found
- Check that Python is installed: `python --version`
- If not, install from https://www.python.org/downloads/
- On Windows, ensure "Add to PATH" was checked during installation
- Try closing and reopening PowerShell/Command Prompt

### Module not found errors
- Ensure virtual environment is activated (see step 3)
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
- Check you're in the project root directory

### Permission denied (Linux/macOS)
- Make app.py executable: `chmod +x src/app.py`
- Run with python explicitly: `python src/app.py`

### Port already in use
- The application runs locally on your machine, not on a network port
- If you get port errors, close other Python processes

### CustomTkinter not loading
- This is a GUI framework issue
- Ensure you're on Windows, macOS, or a Linux system with a display server
- Install: `pip install customtkinter --upgrade`

## Demo Credentials

Use these to test the application:

- **Username:** admin
- **Password:** password123
- **Role:** Administrator

Additional demo users can be created after logging in with admin credentials.

## Next Steps

1. Start the application: `python src/app.py`
2. Login with demo credentials
3. Explore the dashboard
4. Create sample inventory items
5. Test stock movements
6. Check the log files in `logs/` directory

## Development

To contribute or develop:

1. Follow the structure in `README.md`
2. Run tests: `pytest tests/ -v`
3. Check code with linting: `pylint src/`
4. All code should be documented with docstrings

## Support

If you encounter issues:
1. Check the logs in `logs/app.log`
2. Verify Python version: `python --version` (must be 3.11+)
3. Ensure all requirements are installed: `pip list`
4. Try a clean reinstall of dependencies

## Production Deployment

For production use (not recommended yet - still in Phase 1):

1. Use a proper database: PostgreSQL or Microsoft SQL Server
2. Update connection strings in `src/config.py`
3. Run migrations if applicable
4. Set up proper backups and monitoring
5. Use encrypted configuration for secrets
