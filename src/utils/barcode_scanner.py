"""
Barcode Scanner Module
Handles USB barcode scanner input and processing
"""

import threading
import logging
from typing import Optional, Callable
from pyzbar.pyzbar import decode
from PIL import Image
import io

logger = logging.getLogger(__name__)


class BarcodeScanner:
    """Handles barcode scanning from USB scanner or webcam"""

    def __init__(self, on_barcode_scanned: Optional[Callable[[str], None]] = None):
        """
        Initialize barcode scanner
        
        Args:
            on_barcode_scanned: Callback function when barcode is scanned
        """
        self.on_barcode_scanned = on_barcode_scanned
        self.is_listening = False
        self.listen_thread = None
        self.last_barcode = None
        self.last_barcode_time = None

    def start_listening(self):
        """Start listening for barcode input"""
        if self.is_listening:
            logger.warning("Barcode scanner already listening")
            return

        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        logger.info("Barcode scanner listening started")

    def stop_listening(self):
        """Stop listening for barcode input"""
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=1)
        logger.info("Barcode scanner listening stopped")

    def _listen_loop(self):
        """Background thread for listening to scanner input"""
        # This is a placeholder - actual USB scanner input handling would go here
        # For now, this demonstrates the interface
        pass

    def process_barcode(self, barcode_string: str) -> bool:
        """
        Process a barcode string
        
        Args:
            barcode_string: The barcode value to process
            
        Returns:
            True if barcode was processed, False otherwise
        """
        if not barcode_string or not barcode_string.strip():
            return False

        barcode = barcode_string.strip()

        # Avoid duplicate rapid scans
        import time
        current_time = time.time()
        if (
            self.last_barcode == barcode
            and self.last_barcode_time
            and (current_time - self.last_barcode_time) < 1
        ):
            logger.debug(f"Duplicate barcode scan ignored: {barcode}")
            return False

        self.last_barcode = barcode
        self.last_barcode_time = current_time

        logger.info(f"Barcode scanned: {barcode}")

        if self.on_barcode_scanned:
            self.on_barcode_scanned(barcode)

        return True

    @staticmethod
    def extract_barcode_from_image(image_path: str) -> Optional[str]:
        """
        Extract barcode from image file
        
        Args:
            image_path: Path to image file
            
        Returns:
            Barcode string or None if not found
        """
        try:
            image = Image.open(image_path)
            barcodes = decode(image)

            if barcodes:
                return barcodes[0].data.decode("utf-8")
            return None
        except Exception as e:
            logger.error(f"Error extracting barcode from image: {e}")
            return None

    @staticmethod
    def extract_barcode_from_bytes(image_bytes: bytes) -> Optional[str]:
        """
        Extract barcode from image bytes
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Barcode string or None if not found
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            barcodes = decode(image)

            if barcodes:
                return barcodes[0].data.decode("utf-8")
            return None
        except Exception as e:
            logger.error(f"Error extracting barcode from bytes: {e}")
            return None
