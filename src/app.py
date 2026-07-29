"""
MediStock AI - Main Application Entry Point
Initializes and runs the application
"""

import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path when launching via src\app.py directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import APP_NAME, APP_VERSION, LOGS_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

from src.database.db import init_database
from src.ui.main_window import MainWindow


def main():
    """Main application entry point"""
    try:
        logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
        
        # Initialize database
        logger.info("Initializing database...")
        init_database()
        
        # Create and run main window
        logger.info("Launching UI...")
        app = MainWindow()
        app.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
