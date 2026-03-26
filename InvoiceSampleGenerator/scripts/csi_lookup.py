"""Live CSI lookup seams for vendor, item, and numbering resolution.

Uses the shared/ auth and config infrastructure from the parent project.
Gated by CSI_LOOKUP_ENABLED=1 environment variable.

When disabled or when a lookup fails, all functions return None so the
renderer falls back to local catalogs and registries.

Required environment:
  CSI_LOOKUP_ENABLED=1
  IONAPI_FILE=<path-to-.ionapi>   (or pass ionapi_path explicitly)
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

# Add repo root to path so shared/ is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    import requests
    from shared.auth import get_auth_headers
    from shared.config import IDO_URL
    from shared.tenant import get_site
    _SHARED_AVAILABLE = True
except ImportError:
    _SHARED_AVAILABLE = False


# ── Configuration ────────────────────────────────────────────────

_IONAPI_PATH = os.environ.get("IONAPI_FILE", "")

# IDO property lists
_VENDOR_PROPS = "VendNum,Name,VadAddr_1,VadAddr_2,VadAddr_3,VadAddr_4,VadCity,VadState,VadZip,VadCountry,Phone,ExternalEmailAddr"
_ITEM_PROPS = "Item,Description,UM,UnitCost"
_PO_PROPS = "PoNum"


def is_csi_enabled() -> bool:
    return os.environ.get("CSI_LOOKUP_ENABLED", "").strip() == "1" and _SHARED_AVAILABLE


def _get_headers() -> dict[str, str]:
    headers = get_auth_headers(ionapi_path=_IONAPI_PATH or None)
    headers["X-Infor-MongooseConfig"] = get_site()
    return headers


def _ido_load(ido_name: str, properties: str, filter_str: str = "",
              record_cap: int = 100) -> list[dict[str, str]] | None:
    """Generic IDO load. Returns list of property dicts or None on failure."""
    if not is_csi_enabled():
        return None
    try:
        headers = _get_headers()
        url = f"{IDO_URL()}/load/{ido_name}"
        params: dict[str, Any] = {"properties": properties, "recordCap": record_cap}
        if filter_str:
            params["filter"] = filter_str
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Response may be a list of flat dicts or {"Items": [...]} with nested Properties
        if isinstance(data, list):
            return data
        items = data.get("Items") or []
        if not items:
            return []
        # Check if items are flat dicts or nested Property arrays
        first = items[0]
        if "Properties" in first:
            results = []
            for item in items:
                row = {}
                for prop in item.get("Properties", []):
                    row[prop["Name"]] = prop.get("Value", "")
                results.append(row)
            return results
        # Already flat key-value dicts
        return items
    except Exception as e:
        print(f"[csi_lookup] IDO load {ido_name} failed: {e}", file=sys.stderr)
        return None


def _build_address_lines(row: dict[str, str]) -> list[str]:
    """Assemble address lines from IDO vendor address fields."""
    lines = []
    for key in ("VadAddr_1", "VadAddr_2", "VadAddr_3", "VadAddr_4"):
        val = (row.get(key) or "").strip()
        if val:
            lines.append(val)
    city = (row.get("VadCity") or "").strip()
    state = (row.get("VadState") or "").strip()
    zip_code = (row.get("VadZip") or "").strip()
    parts = [p for p in [city, state] if p]
    city_line = ", ".join(parts)
    if zip_code:
        city_line = f"{city_line} {zip_code}".strip()
    if city_line:
        lines.append(city_line)
    return lines


def _vendor_from_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "code": (row.get("VendNum") or "").strip(),
        "name": (row.get("Name") or "").strip(),
        "address_lines": _build_address_lines(row),
        "phone": (row.get("Phone") or "").strip(),
        "email": (row.get("ExternalEmailAddr") or "").strip(),
    }


def _item_from_row(row: dict[str, str]) -> dict[str, Any]:
    raw_cost = str(row.get("UnitCost") or "0").replace(",", "")
    try:
        cost = Decimal(raw_cost).quantize(Decimal("0.01"))
    except Exception:
        cost = Decimal("0.00")
    return {
        "code": (row.get("Item") or "").strip(),
        "description": (row.get("Description") or "").strip(),
        "uom": (row.get("UM") or "EA").strip(),
        "unit_price": cost,
    }


# ── Vendor lookup ────────────────────────────────────────────────

def lookup_vendor(vendor_code: str) -> dict[str, Any] | None:
    """Return a vendor dict matching the renderer shape, or None."""
    rows = _ido_load("SLVendors", _VENDOR_PROPS, f"VendNum = '{vendor_code}'", 1)
    if rows:
        return _vendor_from_row(rows[0])
    return None


def lookup_vendors_all() -> list[dict[str, Any]] | None:
    """Return active vendor list, or None."""
    rows = _ido_load("SLVendors", _VENDOR_PROPS, "", 200)
    if rows:
        return [_vendor_from_row(r) for r in rows]
    return None


# ── Item lookup ──────────────────────────────────────────────────

def lookup_item(item_code: str) -> dict[str, Any] | None:
    """Return an item dict matching the renderer shape, or None."""
    rows = _ido_load("SLItems", _ITEM_PROPS, f"Item = '{item_code}'", 1)
    if rows:
        return _item_from_row(rows[0])
    return None


def lookup_items_all() -> list[dict[str, Any]] | None:
    """Return active item list, or None."""
    rows = _ido_load("SLItems", _ITEM_PROPS, "", 500)
    if rows:
        return [_item_from_row(r) for r in rows]
    return None


# ── Numbering lookup ─────────────────────────────────────────────

def _extract_trailing_number(value: str) -> int | None:
    """Extract trailing digits from a string like 'PODM000103' -> 103."""
    digits = ""
    for ch in reversed(value):
        if ch.isdigit():
            digits = ch + digits
        else:
            break
    return int(digits) if digits else None


def lookup_latest_po_number(prefix: str = "") -> int | None:
    """Return the highest PO numeric suffix matching prefix, or None.

    Fetches a page of POs with prefix filter and finds the max in Python,
    since the IDO does not guarantee ordering.
    """
    po_filter = f"PoNum LIKE '{prefix}%'" if prefix else ""
    rows = _ido_load("SLPos", _PO_PROPS, po_filter, 200)
    if not rows:
        return None
    best = None
    for row in rows:
        po_num = (row.get("PoNum") or "").strip()
        num = _extract_trailing_number(po_num)
        if num is not None and (best is None or num > best):
            best = num
    return best


def lookup_latest_invoice_number() -> int | None:
    """Return the last-used invoice numeric suffix, or None.

    Invoice numbers are generator-assigned, not CSI-tracked,
    so this returns None to fall back to the local registry.
    """
    return None
