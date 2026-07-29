"""
Lightweight HTTP API for the Taboryx AI mobile companion app.
"""

import argparse
import json
import logging
import mimetypes
import secrets
import sys
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from src.database.db import init_database
from src.models.models import StockMovement
from src.services.ai_insights_service import AIInsightsService
from src.services.auth_service import AuthenticationService
from src.services.fridge_monitoring_service import FridgeMonitoringService
from src.services.inventory_service import InventoryService
from src.services.purchase_order_service import PurchaseOrderService
from src.services.room_service import ClinicalRoomService
from src.services.site_service import SiteService
from src.services.supplier_service import SupplierService

logger = logging.getLogger(__name__)


def _resolve_static_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "web"
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "web"
    return Path(__file__).resolve().parent.parent.parent / "web"


STATIC_ROOT = _resolve_static_root()


def _serialize(value: Any):
    if is_dataclass(value):
        return _serialize(asdict(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


class TokenStore:
    def __init__(self):
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def issue(self, user: dict) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = {
                "user_id": user.get("id"),
                "username": user.get("username"),
                "role": user.get("role"),
                "issued_at": datetime.utcnow().isoformat(),
            }
        return token

    def get(self, token: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._tokens.get(token)


TOKENS = TokenStore()


class TaboryxAPIHandler(BaseHTTPRequestHandler):
    server_version = "TaboryxAPI/1.0"

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._write_cors_headers()
        self.end_headers()

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def _route(self, method: str):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        try:
            logger.info("Routing %s %s", method, path)
            if path == "/health":
                self._json_response(HTTPStatus.OK, {"status": "ok", "service": "Taboryx AI API"})
                return

            if path.startswith("/api/"):
                if path == "/api/v1/auth/login" and method == "POST":
                    self._login()
                    return

                auth_context = self._authenticate_request()
                if not auth_context:
                    self._json_response(HTTPStatus.UNAUTHORIZED, {"error": "Authentication required"})
                    return

                if path == "/api/v1/bootstrap" and method == "GET":
                    self._json_response(HTTPStatus.OK, self._bootstrap_payload())
                    return

                if path == "/api/v1/dashboard" and method == "GET":
                    self._json_response(HTTPStatus.OK, self._dashboard_payload())
                    return

                if path == "/api/v1/inventory" and method == "GET":
                    self._json_response(HTTPStatus.OK, self._inventory_payload(query))
                    return

                if path.startswith("/api/v1/inventory/") and method == "GET":
                    self._json_response(HTTPStatus.OK, self._inventory_item_payload(path))
                    return

                if path == "/api/v1/movements" and method == "GET":
                    self._json_response(HTTPStatus.OK, self._movements_payload(query))
                    return

                if path == "/api/v1/purchase-orders" and method == "GET":
                    self._json_response(HTTPStatus.OK, self._purchase_orders_payload(query))
                    return

                if path == "/api/v1/suppliers" and method == "GET":
                    self._json_response(HTTPStatus.OK, self._suppliers_payload())
                    return

                if path == "/api/v1/rooms" and method == "GET":
                    self._json_response(HTTPStatus.OK, self._rooms_payload())
                    return

                if path.startswith("/api/v1/fridges/") and method == "POST":
                    self._fridge_wifi_action(path)
                    return

                if path.startswith("/api/v1/fridges") and method == "GET":
                    self._json_response(HTTPStatus.OK, self._fridges_payload())
                    return

                if path.startswith("/api/v1/fridges") and method == "POST":
                    self._create_fridge()
                    return

                if path.startswith("/api/v1/fridge-readings") and method == "GET":
                    self._json_response(HTTPStatus.OK, self._fridge_readings_payload(query))
                    return

                if path.startswith("/api/v1/fridge-readings") and method == "POST":
                    self._record_fridge_reading(auth_context)
                    return

                if path == "/api/v1/audits" and method == "GET":
                    self._json_response(HTTPStatus.OK, self._audits_payload(query))
                    return

                if path == "/api/v1/ai/forecasts" and method == "GET":
                    self._json_response(HTTPStatus.OK, AIInsightsService().get_usage_forecasts())
                    return

                if path == "/api/v1/ai/expiry-risk" and method == "GET":
                    days = int(query.get("days", ["90"])[0])
                    self._json_response(HTTPStatus.OK, AIInsightsService().get_expiry_risk_items(days))
                    return

                if path == "/api/v1/scan" and method == "POST":
                    self._scan()
                    return

                if path == "/api/v1/stock-movement" and method == "POST":
                    self._stock_movement(auth_context)
                    return

                self._json_response(HTTPStatus.NOT_FOUND, {"error": "Endpoint not found"})
                return

            if path in {"/", "/index.html"}:
                self._serve_static("index.html")
                return

            if path.startswith("/icons/") or path in {"/manifest.json", "/sw.js"}:
                self._serve_static(path.lstrip("/"))
                return

            if path.endswith((".css", ".js", ".json", ".png", ".svg", ".ico")):
                self._serve_static(path.lstrip("/"))
                return

            self._serve_static("index.html")
        except ValueError as exc:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            logger.exception("API request failed")
            self._json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        if not raw.strip():
            return {}
        return json.loads(raw)

    def _login(self):
        payload = self._read_json()
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        if not username or not password:
            raise ValueError("username and password are required")

        success, message, user = AuthenticationService().login(username, password)
        if not success or not user:
            self._json_response(HTTPStatus.UNAUTHORIZED, {"error": message})
            return

        token = TOKENS.issue(user.to_dict())
        self._json_response(
            HTTPStatus.OK,
            {
                "token": token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                },
            },
        )

    def _authenticate_request(self) -> Optional[Dict[str, Any]]:
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[len("Bearer "):].strip()
        return TOKENS.get(token)

    def _bootstrap_payload(self):
        return {
            "dashboard": self._dashboard_payload(),
            "inventory": self._inventory_payload({}),
            "movements": self._movements_payload({}),
            "purchase_orders": self._purchase_orders_payload({}),
            "suppliers": self._suppliers_payload(),
            "rooms": self._rooms_payload(),
            "forecasts": AIInsightsService().get_usage_forecasts(),
            "expiry_risk": AIInsightsService().get_expiry_risk_items(90),
        }

    def _dashboard_payload(self):
        inventory = InventoryService()
        items = inventory.get_all_items()
        movements = inventory.get_stock_movements(limit=300)
        purchase_orders = PurchaseOrderService().get_purchase_orders(status="pending")
        expired_count = sum(1 for item in items if item.is_expired)
        low_stock_count = sum(1 for item in items if item.current_quantity < item.minimum_quantity)
        total_value = inventory.get_total_inventory_value()
        trend = self._build_stock_trend(inventory)
        top_used = self._top_used_items(movements, inventory)
        return {
            "current_stock_value": round(total_value, 2),
            "low_stock_count": low_stock_count,
            "expired_count": expired_count,
            "pending_orders": len(purchase_orders),
            "top_used_items": top_used[:10],
            "stock_trend": trend,
        }

    def _build_stock_trend(self, inventory: InventoryService):
        from collections import defaultdict

        items = inventory.get_all_items()
        value_by_item = {item.id: float(item.purchase_price or 0.0) for item in items if item.id}
        start = date.today().toordinal() - 6
        daily_adjustments = defaultdict(float)
        for movement in inventory.get_stock_movements(limit=1000):
            if not movement.movement_date:
                continue
            day = movement.movement_date.toordinal()
            if day < start:
                continue
            daily_adjustments[day] += float(movement.quantity_change or 0) * value_by_item.get(movement.item_id, 0.0)

        current_value = float(inventory.get_total_inventory_value() or 0.0)
        points = []
        running = current_value
        for ordinal in range(start, date.today().toordinal() + 1):
            points.append(
                {
                    "date": date.fromordinal(ordinal).isoformat(),
                    "value": round(max(0.0, running), 2),
                }
            )
            running -= daily_adjustments.get(ordinal, 0.0)
        return points

    def _top_used_items(self, movements, inventory: InventoryService):
        usage: Dict[int, int] = {}
        for movement in movements:
            if movement.quantity_change >= 0:
                continue
            usage[movement.item_id] = usage.get(movement.item_id, 0) + abs(int(movement.quantity_change or 0))
        rows = []
        for item_id, qty in sorted(usage.items(), key=lambda row: row[1], reverse=True):
            item = inventory.get_item_by_id(item_id)
            if not item:
                continue
            rows.append(
                {
                    "id": item.id,
                    "name": item.item_name,
                    "category": item.category,
                    "barcode": item.barcode,
                    "quantity": qty,
                    "minimum_quantity": item.minimum_quantity,
                    "status": item.stock_status,
                    "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
                }
            )
        return rows

    def _inventory_payload(self, query: Dict[str, Any]):
        inventory = InventoryService()
        search = (query.get("q") or [""])[0].strip()
        limit = int((query.get("limit") or ["0"])[0] or "0")
        items = inventory.search_items(search) if search else inventory.get_all_items(limit or None)
        return {"items": _serialize(items)}

    def _inventory_item_payload(self, path: str):
        item_id = int(path.rsplit("/", 1)[-1])
        item = InventoryService().get_item_by_id(item_id)
        if not item:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Item not found"})
            return
        return {"item": _serialize(item)}

    def _movements_payload(self, query: Dict[str, Any]):
        item_id = query.get("item_id")
        item_id_value = int(item_id[0]) if item_id else None
        movements = InventoryService().get_stock_movements(item_id=item_id_value, limit=200)
        return {"movements": _serialize(movements)}

    def _purchase_orders_payload(self, query: Dict[str, Any]):
        status = (query.get("status") or ["all"])[0]
        orders = PurchaseOrderService().get_purchase_orders(status=status)
        return {"purchase_orders": _serialize(orders)}

    def _suppliers_payload(self):
        return {"suppliers": _serialize(SupplierService().get_all_suppliers())}

    def _rooms_payload(self):
        return {"rooms": _serialize(ClinicalRoomService().get_all_rooms())}

    def _fridges_payload(self):
        return {"fridges": _serialize(FridgeMonitoringService().get_fridges())}

    def _fridge_readings_payload(self, query: Dict[str, Any]):
        fridge_id = query.get("fridge_id")
        fridge_id_value = int(fridge_id[0]) if fridge_id else None
        readings = FridgeMonitoringService().get_readings(fridge_id=fridge_id_value, limit=12)
        return {"readings": _serialize(readings)}

    def _create_fridge(self):
        payload = self._read_json()
        service = FridgeMonitoringService()
        success, message, fridge_id = service.register_fridge(
            device_name=(payload.get("device_name") or "").strip(),
            device_code=(payload.get("device_code") or "").strip() or None,
            location=(payload.get("location") or "").strip() or None,
            room_id=int(payload.get("room_id")) if payload.get("room_id") else None,
            connection_type=(payload.get("connection_type") or "wifi").strip() or "wifi",
            endpoint_url=(payload.get("endpoint_url") or "").strip() or None,
            min_temperature=float(payload.get("min_temperature")) if payload.get("min_temperature") not in {None, ""} else None,
            max_temperature=float(payload.get("max_temperature")) if payload.get("max_temperature") not in {None, ""} else None,
            notes=(payload.get("notes") or "").strip() or None,
        )
        if not success:
            raise ValueError(message)
        return self._json_response(
            HTTPStatus.OK,
            {
                "success": True,
                "fridge_id": fridge_id,
                "fridge": _serialize(service.get_fridge_by_id(fridge_id)),
                "message": message,
            },
        )

    def _record_fridge_reading(self, auth_context: Optional[Dict[str, Any]]):
        payload = self._read_json()
        service = FridgeMonitoringService()
        fridge_id = payload.get("fridge_id")
        if fridge_id is not None:
            try:
                fridge_id = int(fridge_id)
            except (TypeError, ValueError):
                raise ValueError("fridge_id must be an integer")

        success, message, reading_id = service.record_temperature(
            fridge_id=fridge_id,
            device_code=(payload.get("device_code") or "").strip() or None,
            temperature_c=payload.get("temperature_c"),
            source=(payload.get("source") or "wifi").strip() or "wifi",
            notes=(payload.get("notes") or "").strip() or None,
        )
        if not success:
            raise ValueError(message)
        return self._json_response(
            HTTPStatus.OK,
            {
                "success": True,
                "reading_id": reading_id,
                "message": message,
            },
        )

    def _fridge_wifi_action(self, path: str):
        parts = [part for part in path.split("/") if part]
        if len(parts) != 5:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Endpoint not found"})
            return
        try:
            fridge_id = int(parts[3])
        except ValueError:
            raise ValueError("fridge_id must be an integer")
        action = parts[4]
        service = FridgeMonitoringService()

        if action == "wifi-test":
            success, message, details = service.check_wifi_connection(fridge_id=fridge_id)
            status_code = HTTPStatus.OK if success else HTTPStatus.BAD_REQUEST
            self._json_response(
                status_code,
                {
                    "success": success,
                    "message": message,
                    "details": _serialize(details) if details is not None else None,
                },
            )
            return

        if action == "wifi-sync":
            success, message, reading_id = service.pull_temperature_from_wifi_endpoint(fridge_id=fridge_id)
            status_code = HTTPStatus.OK if success else HTTPStatus.BAD_REQUEST
            self._json_response(
                status_code,
                {
                    "success": success,
                    "message": message,
                    "reading_id": reading_id,
                },
            )
            return

        self._json_response(HTTPStatus.NOT_FOUND, {"error": "Endpoint not found"})

    def _audits_payload(self, query: Dict[str, Any]):
        room_id = query.get("room_id")
        audits = []
        if room_id and room_id[0]:
            from src.services.audit_service import AuditService

            audits = AuditService().get_audits(int(room_id[0]))
        else:
            from src.services.audit_service import AuditService

            audits = AuditService().get_audits()
        return {"audits": _serialize(audits)}

    def _scan(self):
        payload = self._read_json()
        code = (payload.get("code") or "").strip()
        if not code:
            raise ValueError("code is required")

        inventory = InventoryService()
        item = inventory.get_item_by_barcode(code) or inventory.get_item_by_qr_code(code)
        if not item:
            self._json_response(HTTPStatus.OK, {"found": False, "code": code, "message": "Item not found"})
            return

        self._json_response(
            HTTPStatus.OK,
            {
                "found": True,
                "code": code,
                "item": _serialize(item),
                "message": f"Found {item.item_name}",
            },
        )

    def _stock_movement(self, auth_context: Optional[Dict[str, Any]]):
        payload = self._read_json()
        inventory = InventoryService()

        item_id = payload.get("item_id")
        item = None
        if item_id:
            try:
                item_id = int(item_id)
            except (TypeError, ValueError):
                raise ValueError("item_id must be an integer")
            item = inventory.get_item_by_id(item_id)
        else:
            code = (payload.get("code") or "").strip()
            if code:
                item = inventory.get_item_by_barcode(code) or inventory.get_item_by_qr_code(code)

        if not item:
            raise ValueError("Item not found")

        movement_type = (payload.get("movement_type") or "ISSUED").upper()
        try:
            quantity = int(payload.get("quantity") or payload.get("transaction_quantity") or 0)
        except (TypeError, ValueError):
            raise ValueError("quantity must be a number")
        if quantity <= 0:
            raise ValueError("quantity must be greater than zero")

        quantity_change = payload.get("quantity_change")
        if quantity_change is None:
            if movement_type in {"ISSUED", "USED", "TRANSFERRED", "DISPOSED", "EXPIRED", "LOST", "DAMAGED"}:
                quantity_change = -abs(quantity)
            else:
                quantity_change = abs(quantity)
        else:
            try:
                quantity_change = int(quantity_change)
            except (TypeError, ValueError):
                raise ValueError("quantity_change must be a number")

        room_name = payload.get("room") or item.clinical_room
        room_id = inventory._get_room_id_by_name(room_name) if room_name else None

        movement = StockMovement(
            item_id=item.id,
            movement_type=movement_type,
            transaction_quantity=abs(quantity),
            quantity_change=quantity_change,
            user_id=auth_context.get("user_id") if auth_context else None,
            movement_date=date.today(),
            movement_time=datetime.now().strftime("%H:%M:%S"),
            reason=payload.get("reason") or f"Mobile {movement_type.lower()} entry",
            patient_area=payload.get("patient_area"),
            room_id=room_id,
        )

        success, message, movement_id = inventory.log_stock_movement(movement)
        if not success:
            raise ValueError(message)

        self._json_response(
            HTTPStatus.OK,
            {
                "success": True,
                "movement_id": movement_id,
                "item": _serialize(item),
                "message": message,
            },
        )

    def _serve_static(self, relative_path: str):
        safe_path = (relative_path or "index.html").lstrip("/")
        if ".." in safe_path.split("/"):
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "File not found"})
            return

        candidate = (STATIC_ROOT / safe_path).resolve()
        if not candidate.is_file() or STATIC_ROOT not in candidate.parents:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "File not found"})
            return

        content_type, _ = mimetypes.guess_type(str(candidate))
        if not content_type:
            content_type = "application/octet-stream"

        body = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self._write_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_response(self, status: HTTPStatus, payload: Any):
        body = json.dumps(_serialize(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._write_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")


def run(host: str = "0.0.0.0", port: int = 8000):
    init_database()
    server = ThreadingHTTPServer((host, port), TaboryxAPIHandler)
    logger.info("Taboryx API running on http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down API server")
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="Run the Taboryx AI API server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    run(args.host, args.port)


if __name__ == "__main__":
    main()
