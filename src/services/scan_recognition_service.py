"""
Scan recognition service.
Resolves barcode and QR scan payloads to inventory items or stock batches.
"""

import re
from typing import Dict, Optional

from src.services.inventory_service import InventoryService
from src.services.stock_batch_service import StockBatchService


class ScanRecognitionService:
    """Resolve scanned barcodes/QR codes into items or stock batches."""

    def __init__(self):
        self.inventory_service = InventoryService()
        self.stock_batch_service = StockBatchService()

    def recognize(self, scanned_code: str) -> Dict[str, object]:
        code = (scanned_code or "").strip()
        if not code:
            return {"found": False, "entity_type": None, "matched_by": None, "item": None, "batch": None}

        batch = self.stock_batch_service.get_batch_by_qr_code(code)
        if batch:
            item = self.inventory_service.get_item_by_id(batch.item_id)
            return self._result(True, "batch", "batch_qr_code", item=item, batch=batch)

        item = self.inventory_service.get_item_by_qr_code(code)
        if item:
            return self._result(True, "item", "item_qr_code", item=item)

        parsed = self._parse_structured_qr_payload(code)
        batch = self._resolve_batch_from_payload(parsed)
        if batch:
            item = self.inventory_service.get_item_by_id(batch.item_id)
            return self._result(True, "batch", "structured_qr_payload", item=item, batch=batch)

        item = self._resolve_item_from_payload(parsed)
        if item:
            return self._result(True, "item", "structured_qr_payload", item=item)

        item = self.inventory_service.get_item_by_barcode(code)
        if item:
            return self._result(True, "item", "barcode", item=item)

        batch = self.stock_batch_service.get_batch_by_batch_number(code)
        if batch:
            item = self.inventory_service.get_item_by_id(batch.item_id)
            return self._result(True, "batch", "batch_number", item=item, batch=batch)

        return self._result(False, None, None)

    @staticmethod
    def _result(found: bool, entity_type: Optional[str], matched_by: Optional[str], item=None, batch=None):
        return {
            "found": found,
            "entity_type": entity_type,
            "matched_by": matched_by,
            "item": item,
            "batch": batch,
        }

    @staticmethod
    def _parse_structured_qr_payload(payload: str) -> Dict[str, str]:
        parsed: Dict[str, str] = {}
        cleaned = payload.strip()

        prefixed_match = re.match(r"^(ITEM|PRODUCT|BATCH)\s*:\s*(.+)$", cleaned, re.IGNORECASE)
        if prefixed_match:
            parsed[prefixed_match.group(1).lower()] = prefixed_match.group(2).strip()

        for key, value in re.findall(r"([A-Za-z_]+)\s*[:=]\s*([^;|,\n]+)", cleaned):
            parsed[key.strip().lower()] = value.strip()

        return parsed

    def _resolve_batch_from_payload(self, parsed: Dict[str, str]):
        batch_id = self._parse_int(parsed.get("batch_id") or parsed.get("batch"))
        if batch_id:
            batch = self.stock_batch_service.get_batch_by_id(batch_id)
            if batch:
                return batch

        batch_number = parsed.get("batch_number")
        if batch_number:
            batch = self.stock_batch_service.get_batch_by_batch_number(batch_number)
            if batch:
                return batch

        qr_code = parsed.get("qr_code")
        if qr_code:
            batch = self.stock_batch_service.get_batch_by_qr_code(qr_code)
            if batch:
                return batch

        return None

    def _resolve_item_from_payload(self, parsed: Dict[str, str]):
        item_id = self._parse_int(parsed.get("item_id") or parsed.get("product_id") or parsed.get("item") or parsed.get("product"))
        if item_id:
            item = self.inventory_service.get_item_by_id(item_id)
            if item:
                return item

        barcode = parsed.get("barcode")
        if barcode:
            item = self.inventory_service.get_item_by_barcode(barcode)
            if item:
                return item

        qr_code = parsed.get("qr_code")
        if qr_code:
            item = self.inventory_service.get_item_by_qr_code(qr_code)
            if item:
                return item

        return None

    @staticmethod
    def _parse_int(value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        value = value.strip()
        return int(value) if value.isdigit() else None
