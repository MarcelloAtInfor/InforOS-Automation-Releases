#!/usr/bin/env python3
"""Render one or many sample invoices from a plain-text request contract."""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

try:
    from csi_lookup import (
        is_csi_enabled,
        lookup_vendor,
        lookup_vendors_all,
        lookup_item,
        lookup_items_all,
        lookup_latest_invoice_number,
        lookup_latest_po_number,
    )
except ImportError:
    def is_csi_enabled() -> bool: return False
    def lookup_vendor(code: str): return None
    def lookup_vendors_all(): return None
    def lookup_item(code: str): return None
    def lookup_items_all(): return None
    def lookup_latest_invoice_number(): return None
    def lookup_latest_po_number(prefix: str = ""): return None
from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


DEFAULT_TERMS = "Net 30 Days"
DEFAULT_SHIPPING_METHOD = "Company Truck"
DEFAULT_SHIPPING_TERMS = "N/A"
DEFAULT_LAYOUT_VARIANT = "html_reference_v1"
DEFAULT_FILE_NAME_PATTERN = "{invoice_number}_{mode}.pdf"
DEFAULT_INVOICE_PREFIX = "INVDM"
DEFAULT_PO_PREFIX = "PODM"
DEFAULT_INVOICE_WIDTH = 3
DEFAULT_PO_WIDTH = 6
DEFAULT_START_NUMBER = 1
FRAME_TEXT_TOP_PADDING = 7.0
HEADER_TEXT_TOP_PADDING = 4.0
TABLE_TEXT_TOP_PADDING = 5.5
TITLE_TOP_NUDGE = -7.0
BROWSER_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
]

SELL_TO = {
    "name": "Progressive Industries",
    "contact": "Robert Penrod",
    "address_lines": ["517 S 2nd Ave", "Dallas, TX 75226"],
    "phone": "214-741-6700",
}

SHIP_TO = {
    "name": "Progressive Industries",
    "contact": "Paul Adams",
    "address_lines": ["517 S 2nd Ave", "Dallas, TX 75226"],
    "phone": "214-741-6721",
}

EXISTING_VENDORS = [
    {
        "code": "BICYCLE_PARTS",
        "name": "Bicycle Parts Company",
        "address_lines": ["7768 E Lincoln Way", "Apple Creek, OH 44606"],
        "phone": "330-684-2607",
        "email": "william.davis@bpc.com",
    },
    {
        "code": "PIONEER_FLUID",
        "name": "Pioneer Fluid Works",
        "address_lines": ["6512 Delta Park Blvd", "Dayton, OH 45414"],
        "phone": "937-555-0199",
        "email": "ap@pioneerfluid.example",
    },
    {
        "code": "ATLAS_CONVEYOR",
        "name": "Atlas Conveyor Supply",
        "address_lines": ["8801 Transit Park Drive", "Columbus, OH 43085"],
        "phone": "614-555-0177",
        "email": "ap@atlasconveyor.example",
    },
    {
        "code": "GRANITE_MOTION",
        "name": "Granite Motion Supply",
        "address_lines": ["1188 Foundry Avenue", "Rockford, IL 61109"],
        "phone": "815-555-2864",
        "email": "orders@granitemotion.com",
    },
    {
        "code": "LONG_ROUTE_LOGISTICS",
        "name": "Long Route Industrial Logistics Group",
        "address_lines": [
            "1450 International Commerce Center",
            "Building 12, Suite 480",
            "North Distribution Annex",
            "Orlando, FL 32809",
        ],
        "phone": "407-555-0184",
        "email": "enterprise.ap@longroute-logistics.example",
    },
]

SYNTHETIC_VENDORS = [
    {
        "code": "SYNTH_A",
        "name": "Harbor Crest Systems",
        "address_lines": ["4108 Harbor Loop Drive", "Erie, PA 16509"],
        "phone": "814-555-0114",
        "email": "ap@harborcrest.example",
    },
    {
        "code": "SYNTH_B",
        "name": "Copper Ridge Motion",
        "address_lines": ["8721 Alloy Point Blvd", "Akron, OH 44312"],
        "phone": "330-555-0188",
        "email": "payables@copperridge.example",
    },
    {
        "code": "SYNTH_C",
        "name": "Meridian Harbor Drives",
        "address_lines": ["6420 Jetty Park Road", "Toledo, OH 43611"],
        "phone": "419-555-0172",
        "email": "ap@meridianharbor.example",
    },
]

PO_ITEM_CATALOG = [
    {"code": "RF-10000", "description": "Reflectors, Rear", "uom": "EA", "unit_price": Decimal("24.50")},
    {"code": "RF-20000", "description": "Reflectors, Front", "uom": "EA", "unit_price": Decimal("22.10")},
    {"code": "RF-30000", "description": "Reflectors, Wheel", "uom": "EA", "unit_price": Decimal("18.75")},
    {"code": "CBL-40010", "description": "Control Cable Assembly", "uom": "EA", "unit_price": Decimal("31.25")},
    {"code": "SNS-50020", "description": "Sensor Mount Plate", "uom": "EA", "unit_price": Decimal("16.80")},
    {"code": "BRG-60030", "description": "Bearing Housing Block", "uom": "EA", "unit_price": Decimal("44.95")},
    {"code": "DRV-70040", "description": "Drive Coupling", "uom": "EA", "unit_price": Decimal("66.30")},
    {"code": "MNT-80050", "description": "Motor Mount Bracket", "uom": "EA", "unit_price": Decimal("28.15")},
    {"code": "VAL-90060", "description": "Valve Core Repair Kit", "uom": "EA", "unit_price": Decimal("13.40")},
    {"code": "PMP-01070", "description": "Pump Housing Assembly", "uom": "EA", "unit_price": Decimal("112.90")},
]

SERVICE_CATALOG = [
    {"code": "ANNUAL-SVC", "description": "Annual equipment service visit", "hours": Decimal("8.0"), "labor_rate": Decimal("35.00")},
    {"code": "SOFT-UPDT", "description": "Software and firmware update", "hours": Decimal("4.0"), "labor_rate": Decimal("42.00")},
    {"code": "CALIBRATE", "description": "Calibration and validation service", "hours": Decimal("3.5"), "labor_rate": Decimal("48.00")},
    {"code": "DIAG-ONSITE", "description": "Onsite diagnostics package", "hours": Decimal("6.0"), "labor_rate": Decimal("38.50")},
    {"code": "TRAIN-USER", "description": "Operator training workshop", "hours": Decimal("5.0"), "labor_rate": Decimal("44.00")},
    {"code": "RETROFIT", "description": "Retrofit labor and commissioning", "hours": Decimal("7.5"), "labor_rate": Decimal("52.00")},
]

# CSI-only pools — populated by _inject_csi_data when request contains csiVendors/csiItems.
# When non-empty, random selection uses these instead of the blended local catalogs.
_CSI_INJECTED_VENDORS: list[dict[str, Any]] = []
_CSI_INJECTED_ITEMS: list[dict[str, Any]] = []


@dataclass
class RuntimeConfig:
    document_count: int
    is_non_po: bool
    output_folder: Path
    random_seed: int
    layout_variant: str
    use_existing_vendors: bool
    selected_vendors: list[str]
    reuse_same_vendor_across_batch: bool
    use_existing_items: bool
    selected_items: list[str]
    line_count_min: int
    line_count_max: int
    qty_min: int
    qty_max: int
    csi_items_pending: bool
    date_mode: str
    fixed_invoice_date: str
    date_offset_days: int
    future_date_allowed: bool
    lookup_latest_numbers: bool
    pair_invoice_and_po_sequence: bool
    invoice_start_value: str
    po_start_value: str
    invoice_prefix: str
    invoice_start_number: int
    invoice_width: int
    po_prefix: str
    po_start_number: int
    po_width: int
    tax_mode: str
    fixed_tax_amount: Decimal | None
    tax_percent: Decimal | None
    write_manifest: bool
    write_per_invoice_json: bool
    file_name_pattern: str
    registry_path: Path
    artifacts_folder: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-json", required=True, help="Path to request JSON file")
    parser.add_argument("--output-folder", help="Optional output override")
    parser.add_argument("--response-json", help="Optional path to a run-summary JSON artifact")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the request contract without rendering PDFs or mutating the number registry",
    )
    return parser.parse_args()


def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def parse_int(value: Any, default: int) -> int:
    if value is None or str(value).strip() == "":
        return default
    return int(str(value).strip())


def _parse_line_range(value: Any, default: int) -> tuple[int, int]:
    """Parse '4' as (4,4) or '2-6' as (2,6)."""
    if value is None or str(value).strip() == "":
        return (default, default)
    s = str(value).strip()
    if "-" in s:
        parts = s.split("-", 1)
        return (int(parts[0].strip()), int(parts[1].strip()))
    n = int(s)
    return (n, n)


def parse_decimal(value: Any) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    return Decimal(str(value).strip())


def dedupe_pipe_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    seen: set[str] = set()
    values: list[str] = []
    for value in str(raw).split("|"):
        candidate = value.strip()
        if not candidate:
            continue
        normalized = candidate.upper()
        if normalized in seen:
            continue
        seen.add(normalized)
        values.append(candidate)
    return values


def money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}"


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def split_number_value(value: str) -> tuple[str, int, int]:
    match = re.match(r"^(.*?)(\d+)$", value.strip())
    if not match:
        raise ValueError(f"Start value must end in digits: {value}")
    prefix, digits = match.groups()
    return prefix, int(digits), len(digits)


def format_number(prefix: str, number: int, width: int) -> str:
    return f"{prefix}{number:0{width}d}"


def _inject_csi_data(raw: dict[str, Any]) -> None:
    """Merge CSI vendor/item detail from the request into the runtime catalogs."""
    _CSI_INJECTED_VENDORS.clear()
    _CSI_INJECTED_ITEMS.clear()

    csi_vendors = raw.get("csiVendors")
    if isinstance(csi_vendors, list) and csi_vendors:
        for v in csi_vendors:
            code = str(v.get("code", "")).upper()
            if not code:
                continue
            entry = {
                "code": code,
                "name": str(v.get("name", code)),
                "address_lines": v.get("address_lines", []),
                "phone": str(v.get("phone", "")),
                "email": str(v.get("email", "")),
            }
            _CSI_INJECTED_VENDORS.append(entry)
            if not any(ev["code"].upper() == code for ev in EXISTING_VENDORS):
                EXISTING_VENDORS.append(entry)

    csi_items = raw.get("csiItems")
    if isinstance(csi_items, list) and csi_items:
        for it in csi_items:
            code = str(it.get("code", "")).upper()
            if not code:
                continue
            entry = {
                "code": code,
                "description": str(it.get("description", code)),
                "uom": str(it.get("uom", "EA")),
                "unit_price": quantize_money(Decimal(str(it.get("unit_price", "0.00")))),
            }
            _CSI_INJECTED_ITEMS.append(entry)
            if not any(pi["code"].upper() == code for pi in PO_ITEM_CATALOG):
                PO_ITEM_CATALOG.append(entry)


def parse_request(path: Path, output_override: str | None) -> RuntimeConfig:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    output_folder = Path(output_override or raw.get("outputFolder") or path.parent / "output").resolve()
    # Keep non-PDF artifacts out of the operator-facing output folder.
    # Use the request file's directory (already under Logs/ for RPA runs).
    artifacts_folder = (path.parent / f"artifacts_{path.stem}").resolve()
    registry_path = artifacts_folder / "number_registry.json"

    # Inject CSI vendor/item data into catalogs if present
    _inject_csi_data(raw)

    return RuntimeConfig(
        document_count=parse_int(raw.get("documentCount"), 1),
        is_non_po=parse_bool(raw.get("isNonPo")),
        output_folder=output_folder,
        random_seed=parse_int(raw.get("randomSeed"), 20260310),
        layout_variant=str(raw.get("layoutVariant") or DEFAULT_LAYOUT_VARIANT),
        use_existing_vendors=parse_bool(raw.get("useExistingVendors")),
        selected_vendors=dedupe_pipe_list(raw.get("selectedVendor")),
        reuse_same_vendor_across_batch=parse_bool(raw.get("reuseSameVendorAcrossBatch")),
        use_existing_items=parse_bool(raw.get("useExistingItems")),
        selected_items=dedupe_pipe_list(raw.get("selectedItems")),
        line_count_min=_parse_line_range(raw.get("lineCount"), 3)[0],
        line_count_max=_parse_line_range(raw.get("lineCount"), 3)[1],
        qty_min=_parse_line_range(raw.get("qtyRange"), 1)[0],
        qty_max=_parse_line_range(raw.get("qtyRange"), 10)[1],
        csi_items_pending=parse_bool(raw.get("useExistingItems")) and not raw.get("csiItems") and not raw.get("selectedItems"),
        date_mode=str(raw.get("dateMode") or "fixed").strip().lower(),
        fixed_invoice_date=str(raw.get("fixedInvoiceDate") or "").strip(),
        date_offset_days=parse_int(raw.get("dateOffsetDays"), 0),
        future_date_allowed=parse_bool(raw.get("futureDateAllowed"), True),
        lookup_latest_numbers=parse_bool(raw.get("lookupLatestNumbers")),
        pair_invoice_and_po_sequence=parse_bool(raw.get("pairInvoiceAndPoSequence")),
        invoice_start_value=str(raw.get("invoiceStartValue") or "").strip(),
        po_start_value=str(raw.get("poStartValue") or "").strip(),
        invoice_prefix=str(raw.get("invoicePrefix") or DEFAULT_INVOICE_PREFIX).strip(),
        invoice_start_number=parse_int(raw.get("invoiceStartNumber"), DEFAULT_START_NUMBER),
        invoice_width=parse_int(raw.get("invoiceWidth"), DEFAULT_INVOICE_WIDTH),
        po_prefix=str(raw.get("poPrefix") or DEFAULT_PO_PREFIX).strip(),
        po_start_number=parse_int(raw.get("poStartNumber"), DEFAULT_START_NUMBER),
        po_width=parse_int(raw.get("poWidth"), DEFAULT_PO_WIDTH),
        tax_mode=str(raw.get("taxMode") or "percent_of_subtotal").strip().lower(),
        fixed_tax_amount=parse_decimal(raw.get("fixedTaxAmount")),
        tax_percent=parse_decimal(raw.get("taxPercent")),
        write_manifest=parse_bool(raw.get("writeManifest"), True),
        write_per_invoice_json=parse_bool(raw.get("writePerInvoiceJson")),
        file_name_pattern=str(raw.get("fileNamePattern") or DEFAULT_FILE_NAME_PATTERN),
        registry_path=registry_path,
        artifacts_folder=artifacts_folder,
    )


def validate_runtime_config(config: RuntimeConfig) -> None:
    allowed_layout_variants = {"html_reference_v1", "reference_v1"}
    allowed_tax_modes = {"fixed_amount", "percent_of_subtotal", "zero_tax"}

    if config.document_count < 1:
        raise ValueError("documentCount must be at least 1.")
    if config.line_count_min < 1:
        raise ValueError("lineCount minimum must be at least 1.")
    if config.line_count_max < config.line_count_min:
        raise ValueError("lineCount maximum cannot be less than minimum.")
    if config.qty_max < config.qty_min:
        raise ValueError("qtyRange maximum cannot be less than minimum.")
    if config.invoice_width < 1:
        raise ValueError("invoiceWidth must be at least 1.")
    if not config.is_non_po and config.po_width < 1:
        raise ValueError("poWidth must be at least 1 for PO runs.")
    if config.invoice_start_number < 0:
        raise ValueError("invoiceStartNumber cannot be negative.")
    if not config.is_non_po and config.po_start_number < 0:
        raise ValueError("poStartNumber cannot be negative for PO runs.")
    if config.layout_variant not in allowed_layout_variants:
        raise ValueError(
            f"Unsupported layoutVariant: {config.layout_variant}. "
            "Expected one of: html_reference_v1, reference_v1."
        )
    if config.tax_mode not in allowed_tax_modes:
        raise ValueError(
            f"Unsupported taxMode: {config.tax_mode}. "
            "Expected one of: fixed_amount, percent_of_subtotal, zero_tax."
        )
    if config.tax_mode == "fixed_amount" and config.fixed_tax_amount is None:
        raise ValueError("fixedTaxAmount is required when taxMode is fixed_amount.")
    if config.fixed_tax_amount is not None and config.fixed_tax_amount < Decimal("0.00"):
        raise ValueError("fixedTaxAmount cannot be negative.")
    if config.tax_percent is not None and config.tax_percent < Decimal("0.00"):
        raise ValueError("taxPercent cannot be negative.")


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_registry(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def parse_invoice_date(config: RuntimeConfig) -> date:
    today = date.today()
    if config.date_mode == "today":
        return today
    if config.date_mode == "offset_from_today":
        resolved = today + timedelta(days=config.date_offset_days)
        if resolved > today and not config.future_date_allowed:
            raise ValueError("Future invoice dates are not allowed by this request.")
        return resolved
    if config.date_mode == "fixed":
        if config.fixed_invoice_date:
            return datetime.strptime(config.fixed_invoice_date, "%Y-%m-%d").date()
        return today
    raise ValueError(f"Unsupported dateMode: {config.date_mode}")


def vendor_from_literal(token: str) -> dict[str, Any]:
    base = token.replace("_", " ").replace("-", " ").title()
    return {
        "code": token,
        "name": base,
        "address_lines": ["100 Demo Parkway", "Alpharetta, GA 30009"],
        "phone": "555-555-0100",
        "email": f"{token.lower()}@example.com",
    }


def build_vendor_map(catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {vendor["code"].upper(): vendor for vendor in catalog}


def build_item_map(catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["code"].upper(): item for item in catalog}


def choose_vendors(config: RuntimeConfig, rng: random.Random) -> list[dict[str, Any]]:
    existing_map = build_vendor_map(EXISTING_VENDORS)
    vendors: list[dict[str, Any]] = []

    if not config.use_existing_vendors and config.selected_vendors:
        raise ValueError("selectedVendor cannot be supplied when useExistingVendors is False.")

    # When CSI is enabled, enrich the existing pool with live data
    csi_vendor_pool: list[dict[str, Any]] | None = None
    if config.use_existing_vendors and is_csi_enabled():
        csi_vendor_pool = lookup_vendors_all()

    if config.selected_vendors:
        for index in range(config.document_count):
            token = config.selected_vendors[index % len(config.selected_vendors)]
            # Try CSI first for the specific vendor, then local catalog
            csi_hit = lookup_vendor(token.upper()) if is_csi_enabled() else None
            vendors.append(csi_hit or existing_map.get(token.upper(), vendor_from_literal(token)))
        return vendors

    if config.use_existing_vendors:
        pool = csi_vendor_pool or (_CSI_INJECTED_VENDORS if _CSI_INJECTED_VENDORS else EXISTING_VENDORS)
        if config.reuse_same_vendor_across_batch:
            chosen = rng.choice(pool)
            return [chosen for _ in range(config.document_count)]
        return [rng.choice(pool) for _ in range(config.document_count)]

    return [SYNTHETIC_VENDORS[index % len(SYNTHETIC_VENDORS)] for index in range(config.document_count)]


def synthesize_po_item(token: str, index: int) -> dict[str, Any]:
    code = token.upper().replace(" ", "-")
    return {
        "code": code,
        "description": token.replace("_", " ").replace("-", " ").title(),
        "uom": "EA",
        "unit_price": quantize_money(Decimal("15.00") + Decimal(index * 3)),
    }


def synthesize_service(token: str, index: int) -> dict[str, Any]:
    code = token.upper().replace(" ", "-")
    return {
        "code": code,
        "description": token.replace("_", " ").replace("-", " ").title(),
        "hours": Decimal("2.0") + Decimal(index),
        "labor_rate": quantize_money(Decimal("30.00") + Decimal(index * 4)),
    }


def select_chunk(values: list[str], chunk_size: int, invoice_index: int) -> list[str]:
    if not values:
        return []
    start = (invoice_index * chunk_size) % len(values)
    result: list[str] = []
    seen: set[str] = set()
    offset = 0
    max_iterations = len(values) + chunk_size
    while len(result) < chunk_size and offset < max_iterations:
        candidate = values[(start + offset) % len(values)]
        offset += 1
        normalized = candidate.upper()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(candidate)
    return result


def choose_line_seeds(config: RuntimeConfig, rng: random.Random) -> list[list[dict[str, Any]]]:
    po_map = build_item_map(PO_ITEM_CATALOG)
    service_map = build_item_map(SERVICE_CATALOG)
    existing_pool = [item["code"] for item in PO_ITEM_CATALOG]
    service_pool = [item["code"] for item in SERVICE_CATALOG]

    # Enrich catalogs with CSI data when enabled
    if is_csi_enabled():
        csi_items = lookup_items_all()
        if csi_items:
            for item in csi_items:
                code = item["code"].upper()
                if code not in po_map:
                    po_map[code] = item
                    existing_pool.append(item["code"])

    lines_by_invoice: list[list[dict[str, Any]]] = []

    if not config.use_existing_items and config.selected_items and not config.is_non_po:
        raise ValueError("selectedItems cannot be supplied when useExistingItems is False.")

    selected = config.selected_items
    if config.is_non_po and not selected and not config.use_existing_items:
        selected = service_pool
    elif not config.is_non_po and not selected and config.use_existing_items:
        csi_pool = [item["code"] for item in _CSI_INJECTED_ITEMS] if _CSI_INJECTED_ITEMS else None
        selected = (csi_pool or existing_pool)[:]
        rng.shuffle(selected)
    elif not config.is_non_po and not selected and not config.use_existing_items:
        selected = [item["code"] for item in PO_ITEM_CATALOG]
    elif config.is_non_po and not selected and config.use_existing_items:
        selected = service_pool[:]
        rng.shuffle(selected)

    if not config.is_non_po and len(set(token.upper() for token in selected)) < config.line_count_max:
        if not config.csi_items_pending:
            raise ValueError("PO runs require at least lineCount (max) unique selected items.")
    if config.is_non_po and not selected:
        selected = service_pool

    for invoice_index in range(config.document_count):
        line_count = rng.randint(config.line_count_min, config.line_count_max)
        tokens = select_chunk(selected, line_count, invoice_index)
        if len(tokens) < line_count:
            raise ValueError(
                f"Invoice {invoice_index + 1}: only {len(tokens)} unique items available "
                f"but lineCount requires {line_count}."
            )
        if config.is_non_po:
            lines: list[dict[str, Any]] = []
            for idx, token in enumerate(tokens, start=1):
                service = service_map.get(token.upper(), synthesize_service(token, idx))
                lines.append(
                    {
                        "line_number": idx,
                        "service_code": service["code"],
                        "description": service["description"],
                        "hours": Decimal(service["hours"]),
                        "labor_rate": quantize_money(Decimal(service["labor_rate"])),
                    }
                )
            lines_by_invoice.append(lines)
        else:
            lines = []
            for idx, token in enumerate(tokens, start=1):
                item = po_map.get(token.upper(), synthesize_po_item(token, idx))
                lines.append(
                    {
                        "line_number": idx,
                        "item_code": item["code"],
                        "description": item["description"],
                        "quantity": Decimal(str(rng.randint(config.qty_min, config.qty_max))),
                        "uom": item["uom"],
                        "unit_price": quantize_money(Decimal(item["unit_price"])),
                    }
                )
            lines_by_invoice.append(lines)

    return lines_by_invoice


def resolve_numeric_seed(
    explicit_value: str,
    lookup_enabled: bool,
    registry: dict[str, Any],
    registry_key: str,
    prefix: str,
    start_number: int,
    width: int,
) -> tuple[str, int, int]:
    if explicit_value:
        return split_number_value(explicit_value)
    if lookup_enabled:
        # Try CSI live lookup first, then fall back to local registry
        if is_csi_enabled():
            csi_number = (lookup_latest_invoice_number() if registry_key == "invoice"
                          else lookup_latest_po_number(prefix=prefix))
            if csi_number is not None:
                return prefix, csi_number + 1, width
        if registry_key in registry:
            payload = registry[registry_key]
            return str(payload["prefix"]), int(payload["last_number"]) + 1, int(payload["width"])
    return prefix, start_number, width


def resolve_sequences(config: RuntimeConfig, registry: dict[str, Any]) -> list[dict[str, str]]:
    if config.is_non_po:
        invoice_prefix, invoice_seed, invoice_width = resolve_numeric_seed(
            explicit_value=config.invoice_start_value,
            lookup_enabled=config.lookup_latest_numbers,
            registry=registry,
            registry_key="invoice",
            prefix=config.invoice_prefix or DEFAULT_INVOICE_PREFIX,
            start_number=config.invoice_start_number,
            width=config.invoice_width,
        )
        return [
            {"invoice_number": format_number(invoice_prefix, invoice_seed + index, invoice_width), "po_number": ""}
            for index in range(config.document_count)
        ]

    if config.pair_invoice_and_po_sequence:
        shared_prefix = config.invoice_prefix or DEFAULT_INVOICE_PREFIX
        shared_width = config.invoice_width
        if config.invoice_start_value and config.po_start_value:
            invoice_prefix, invoice_seed, invoice_width = split_number_value(config.invoice_start_value)
            po_prefix, po_seed, po_width = split_number_value(config.po_start_value)
            if invoice_seed != po_seed:
                raise ValueError("Paired explicit invoice and PO start values must share the same numeric suffix.")
            shared_prefix = invoice_prefix
            shared_width = invoice_width
            shared_seed = invoice_seed
            resolved_po_prefix = po_prefix
            resolved_po_width = po_width
        elif config.invoice_start_value:
            invoice_prefix, shared_seed, invoice_width = split_number_value(config.invoice_start_value)
            shared_prefix = invoice_prefix
            shared_width = invoice_width
            resolved_po_prefix = config.po_prefix or DEFAULT_PO_PREFIX
            resolved_po_width = config.po_width
        elif config.po_start_value:
            po_prefix, shared_seed, po_width = split_number_value(config.po_start_value)
            resolved_po_prefix = po_prefix
            resolved_po_width = po_width
            shared_prefix = config.invoice_prefix or DEFAULT_INVOICE_PREFIX
            shared_width = config.invoice_width
        elif config.lookup_latest_numbers:
            # Try CSI live lookup first, then fall back to local registry
            csi_invoice = None
            csi_po = None
            if is_csi_enabled():
                csi_invoice = lookup_latest_invoice_number()
                csi_po = lookup_latest_po_number(prefix=config.po_prefix or DEFAULT_PO_PREFIX)
            invoice_last = csi_invoice if csi_invoice is not None else int(registry.get("invoice", {}).get("last_number", 0))
            po_last = csi_po if csi_po is not None else int(registry.get("po", {}).get("last_number", 0))
            shared_seed = max(invoice_last, po_last) + 1
            resolved_po_prefix = config.po_prefix or DEFAULT_PO_PREFIX
            resolved_po_width = config.po_width
        else:
            shared_seed = config.invoice_start_number
            resolved_po_prefix = config.po_prefix or DEFAULT_PO_PREFIX
            resolved_po_width = config.po_width

        return [
            {
                "invoice_number": format_number(shared_prefix, shared_seed + index, shared_width),
                "po_number": format_number(resolved_po_prefix, shared_seed + index, resolved_po_width),
            }
            for index in range(config.document_count)
        ]

    invoice_prefix, invoice_seed, invoice_width = resolve_numeric_seed(
        explicit_value=config.invoice_start_value,
        lookup_enabled=config.lookup_latest_numbers,
        registry=registry,
        registry_key="invoice",
        prefix=config.invoice_prefix or DEFAULT_INVOICE_PREFIX,
        start_number=config.invoice_start_number,
        width=config.invoice_width,
    )
    po_prefix, po_seed, po_width = resolve_numeric_seed(
        explicit_value=config.po_start_value,
        lookup_enabled=config.lookup_latest_numbers,
        registry=registry,
        registry_key="po",
        prefix=config.po_prefix or DEFAULT_PO_PREFIX,
        start_number=config.po_start_number,
        width=config.po_width,
    )
    return [
        {
            "invoice_number": format_number(invoice_prefix, invoice_seed + index, invoice_width),
            "po_number": format_number(po_prefix, po_seed + index, po_width),
        }
        for index in range(config.document_count)
    ]


def calculate_tax(config: RuntimeConfig, subtotal: Decimal) -> Decimal:
    if config.tax_mode == "fixed_amount":
        return quantize_money(config.fixed_tax_amount or Decimal("0.00"))
    if config.tax_mode == "zero_tax":
        return Decimal("0.00")
    percent = config.tax_percent if config.tax_percent is not None else Decimal("8.00")
    return quantize_money(subtotal * (percent / Decimal("100")))


def build_invoice_documents(config: RuntimeConfig) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validate_runtime_config(config)
    rng = random.Random(config.random_seed)
    invoice_date = parse_invoice_date(config)
    due_date = invoice_date + timedelta(days=30)
    registry = load_registry(config.registry_path)
    sequences = resolve_sequences(config, registry)
    vendors = choose_vendors(config, rng)
    line_sets = choose_line_seeds(config, rng)

    documents: list[dict[str, Any]] = []
    for index in range(config.document_count):
        lines = line_sets[index]
        subtotal = Decimal("0.00")
        rendered_lines: list[dict[str, Any]] = []
        if config.is_non_po:
            for line in lines:
                line_total = quantize_money(line["hours"] * line["labor_rate"])
                subtotal += line_total
                rendered_lines.append({**line, "discount_amount": Decimal("0.00"), "line_total": line_total})
        else:
            for line in lines:
                line_total = quantize_money(line["quantity"] * line["unit_price"])
                subtotal += line_total
                rendered_lines.append({**line, "discount_amount": Decimal("0.00"), "line_total": line_total})
        subtotal = quantize_money(subtotal)
        tax_amount = calculate_tax(config, subtotal)
        total_amount = quantize_money(subtotal + tax_amount)
        sequence = sequences[index]
        documents.append(
            {
                "document_id": f"DOC-{index + 1:03d}",
                "document_mode": "NON_PO" if config.is_non_po else "PO",
                "layout_variant": config.layout_variant,
                "invoice_number": sequence["invoice_number"],
                "invoice_date": invoice_date.isoformat(),
                "due_date": due_date.isoformat(),
                "po_number": sequence["po_number"],
                "vendor": vendors[index],
                "bill_to": SELL_TO,
                "ship_to": SHIP_TO,
                "payment_terms": DEFAULT_TERMS,
                "shipping_terms": DEFAULT_SHIPPING_TERMS,
                "shipping_method": DEFAULT_SHIPPING_METHOD,
                "line_items": rendered_lines,
                "sub_total": subtotal,
                "tax_amount": tax_amount,
                "tax_percent": config.tax_percent if config.tax_percent is not None else Decimal("8.00"),
                "total_amount": total_amount,
                "notes": "Generated for DemoInvoiceLoaderV2 validation.",
            }
        )
    return documents, registry


def draw_address_block(pdf: canvas.Canvas, x: float, y: float, title: str, block: dict[str, Any]) -> float:
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x, y, title)
    y -= 14
    pdf.setFont("Helvetica", 10)
    for line in [block.get("contact"), block.get("name"), *block.get("address_lines", []), block.get("phone")]:
        if not line:
            continue
        pdf.drawString(x, y, str(line))
        y -= 12
    return y


def draw_vendor_block(pdf: canvas.Canvas, x: float, y: float, vendor: dict[str, Any]) -> float:
    pdf.setFont("Helvetica", 10)
    for line in [vendor["name"], *vendor["address_lines"], vendor["phone"], vendor["email"]]:
        pdf.drawString(x, y, line)
        y -= 12
    return y


def draw_meta_column(pdf: canvas.Canvas, x_label: float, x_value: float, y: float, rows: list[tuple[str, str]]) -> float:
    for label, value in rows:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x_label, y, label)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x_value, y, value)
        y -= 12
    return y


def y_from_top(top_y: float, page_height: float = letter[1]) -> float:
    return page_height - top_y


def baseline_y_from_top(top_y: float, font_size: int, page_height: float = letter[1]) -> float:
    # PyMuPDF word coordinates are top-aligned bounding boxes; reportlab drawString expects a baseline.
    # A simple ascent approximation moves rendered text down into the source boxes instead of through them.
    ascent = font_size * 0.78
    return page_height - top_y - ascent


def draw_top_text(
    pdf: canvas.Canvas,
    x: float,
    top_y: float,
    text: str,
    font: str = "Helvetica",
    size: int = 10,
    top_padding: float = 0.0,
) -> None:
    pdf.setFont(font, size)
    pdf.drawString(x, baseline_y_from_top(top_y + top_padding, size), text)


def draw_top_right(
    pdf: canvas.Canvas,
    right_x: float,
    top_y: float,
    text: str,
    font: str = "Helvetica",
    size: int = 10,
    top_padding: float = 0.0,
) -> None:
    pdf.setFont(font, size)
    pdf.drawRightString(right_x, baseline_y_from_top(top_y + top_padding, size), text)


def draw_top_center(
    pdf: canvas.Canvas,
    center_x: float,
    top_y: float,
    text: str,
    font: str = "Helvetica",
    size: int = 10,
    top_padding: float = 0.0,
) -> None:
    pdf.setFont(font, size)
    pdf.drawCentredString(center_x, baseline_y_from_top(top_y + top_padding, size), text)


def draw_top_line(pdf: canvas.Canvas, x1: float, top_y1: float, x2: float, top_y2: float) -> None:
    pdf.line(x1, y_from_top(top_y1), x2, y_from_top(top_y2))


def draw_top_rect(pdf: canvas.Canvas, x0: float, top_y0: float, x1: float, top_y1: float) -> None:
    left = min(x0, x1)
    right = max(x0, x1)
    top = min(top_y0, top_y1)
    bottom = max(top_y0, top_y1)
    pdf.rect(left, y_from_top(bottom), right - left, bottom - top, stroke=1, fill=0)


def draw_boxed_right_value(
    pdf: canvas.Canvas,
    x0: float,
    top_y0: float,
    x1: float,
    top_y1: float,
    value: str,
    text_top_y: float,
    font: str = "Helvetica",
    size: int = 10,
    padding: float = 2.5,
) -> None:
    draw_top_rect(pdf, x0, top_y0, x1, top_y1)
    draw_top_right(pdf, x1 - padding, text_top_y, value, font, size, top_padding=TABLE_TEXT_TOP_PADDING)


def draw_po_reference_frames(pdf: canvas.Canvas) -> None:
    pdf.setLineWidth(0.7)

    # Top header / address panels.
    draw_top_rect(pdf, 72.0, 72.0, 310.92, 222.0)
    draw_top_rect(pdf, 310.92, 72.0, 540.0, 222.0)

    # SOLD TO / SHIP TO matrix.
    draw_top_rect(pdf, 72.0, 222.0, 540.0, 303.6)

    # PO line table frame taken from the reference page drawing commands.
    draw_top_line(pdf, 70.53, 465.89, 549.33, 465.89)
    draw_top_line(pdf, 75.29, 493.35, 548.90, 493.35)
    draw_top_line(pdf, 69.87, 603.74, 548.67, 603.74)
    draw_top_line(pdf, 66.68, 468.22, 66.68, 603.94)
    draw_top_line(pdf, 549.78, 466.35, 549.78, 603.82)

    # Widget-style value boxes that the reference exposes directly.
    draw_top_rect(pdf, 180.65, 340.36, 290.73, 362.36)  # PO number
    draw_top_rect(pdf, 129.35, 108.0, 239.42, 130.0)  # invoice date
    draw_top_rect(pdf, 128.95, 132.22, 239.02, 154.22)  # invoice number
    draw_top_rect(pdf, 75.93, 497.46, 118.58, 519.46)  # qty1
    draw_top_rect(pdf, 75.93, 522.98, 118.58, 544.98)  # qty2
    draw_top_rect(pdf, 75.93, 548.51, 118.58, 570.51)  # qty3
    draw_top_rect(pdf, 324.0, 497.46, 380.40, 519.46)  # unit price 1
    draw_top_rect(pdf, 323.35, 522.33, 379.75, 544.33)  # unit price 2
    draw_top_rect(pdf, 322.69, 547.20, 379.09, 569.20)  # unit price 3
    draw_top_rect(pdf, 471.88, 610.04, 537.33, 632.29)  # total discount
    draw_top_rect(pdf, 471.88, 634.91, 537.33, 657.17)  # subtotal
    draw_top_rect(pdf, 74.62, 661.75, 121.85, 683.75)  # tax percent
    draw_top_rect(pdf, 471.88, 659.13, 537.33, 681.38)  # tax amount
    draw_top_rect(pdf, 471.88, 682.69, 537.33, 704.95)  # total


def draw_non_po_reference_frames(pdf: canvas.Canvas) -> None:
    pdf.setLineWidth(0.7)

    draw_top_rect(pdf, 72.0, 72.0, 310.92, 222.0)
    draw_top_rect(pdf, 310.92, 72.0, 540.0, 222.0)
    draw_top_rect(pdf, 72.0, 222.0, 540.0, 303.6)

    draw_top_rect(pdf, 127.64, 107.35, 201.05, 129.35)  # invoice date
    draw_top_rect(pdf, 126.98, 132.22, 202.36, 154.22)  # invoice number
    draw_top_rect(pdf, 179.35, 396.0, 250.80, 418.0)  # due date

    # The non-PO sample uses header and body separator lines rather than a full grid.
    draw_top_line(pdf, 68.07, 437.24, 581.89, 437.24)
    draw_top_line(pdf, 69.38, 457.53, 583.20, 457.53)


def find_browser_executable() -> Path:
    for candidate in BROWSER_CANDIDATES:
        if candidate.exists():
            return candidate
    raise RuntimeError("Chrome/Edge executable not found for HTML-to-PDF rendering.")


def format_decimal_text(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def html_lines(lines: list[str]) -> str:
    return "".join(f"<div>{escape(line)}</div>" for line in lines if line)


def render_po_html(document: dict[str, Any]) -> str:
    vendor = document["vendor"]
    bill_to = document["bill_to"]
    ship_to = document["ship_to"]
    invoice_date = datetime.fromisoformat(document["invoice_date"]).strftime("%m/%d/%Y")
    due_date = datetime.fromisoformat(document["due_date"]).strftime("%m/%d/%Y")
    po_rows = []
    for line in document["line_items"]:
        po_rows.append(
            f"""
            <tr>
              <td class="qty boxed">{int(line["quantity"])}</td>
              <td class="item">{escape(line["item_code"])}</td>
              <td class="description">{escape(line["description"])}</td>
              <td class="unit-price boxed right">{escape(money(line["unit_price"]).replace(",", ""))}</td>
              <td class="uom center">{escape(line["uom"])}</td>
              <td class="discount right">{escape(money(line["discount_amount"]).replace(",", ""))}</td>
              <td class="line-total right">{escape(money(line["line_total"]).replace(",", ""))}</td>
            </tr>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(document["invoice_number"])}</title>
  <style>
    @page {{
      size: letter;
      margin: 0.5in 0.55in 0.55in 0.55in;
    }}
    html, body {{
      margin: 0;
      padding: 0;
      background: #fff;
      color: #111;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 14px;
      line-height: 1.15;
    }}
    body {{
      width: 100%;
    }}
    .invoice-page {{
      width: 100%;
    }}
    .top-panels {{
      display: grid;
      grid-template-columns: 1fr 0.94fr;
      border: 1px solid #666;
      min-height: 156px;
    }}
    .top-panels .left {{
      border-right: 1px solid #666;
      padding: 12px 14px 12px 8px;
      position: relative;
    }}
    .top-panels .right {{
      min-height: 156px;
    }}
    .title {{
      font-size: 30px;
      font-weight: 700;
      line-height: 1;
      margin: 0 0 8px 0;
    }}
    .field-grid {{
      display: grid;
      grid-template-columns: 54px 118px;
      row-gap: 7px;
      column-gap: 10px;
      align-items: center;
      width: 190px;
    }}
    .field-label {{
      font-size: 12px;
      white-space: nowrap;
    }}
    .field-box {{
      border: 1px solid #777;
      height: 24px;
      display: flex;
      align-items: center;
      padding: 0 6px;
      font-size: 12px;
    }}
    .party-matrix {{
      display: grid;
      grid-template-columns: 1.02fr 1fr 1fr;
      border: 1px solid #666;
      border-top: none;
      min-height: 106px;
    }}
    .party-cell {{
      padding: 13px 10px 10px 10px;
      font-size: 12px;
    }}
    .party-vendor {{
      padding-left: 8px;
    }}
    .party-heading {{
      display: inline-block;
      font-weight: 700;
      margin-right: 8px;
      vertical-align: top;
    }}
    .party-heading.stack {{
      width: 28px;
      text-align: center;
      line-height: 1.2;
    }}
    .party-text {{
      display: inline-block;
      vertical-align: top;
    }}
    .party-vendor .party-text {{
      display: block;
    }}
    .party-text div,
    .party-vendor div {{
      margin: 0 0 3px 0;
    }}
    .meta {{
      margin-top: 18px;
      width: 56%;
      border-collapse: collapse;
      font-size: 12px;
    }}
    .meta td {{
      padding: 0 0 8px 0;
      vertical-align: middle;
    }}
    .meta .label {{
      width: 112px;
    }}
    .meta .boxed-inline {{
      border: 1px solid #777;
      min-height: 24px;
      display: inline-flex;
      align-items: center;
      min-width: 102px;
      padding: 0 6px;
    }}
    .items {{
      margin-top: 14px;
      width: 100%;
      border-collapse: collapse;
      border: 1px solid #666;
      font-size: 12px;
    }}
    .items thead th {{
      font-weight: 700;
      padding: 8px 8px 9px 8px;
      border-bottom: 1px solid #666;
      white-space: nowrap;
      text-align: left;
    }}
    .items tbody td {{
      padding: 9px 8px;
      vertical-align: middle;
    }}
    .items tbody tr {{
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .items .boxed {{
      border: 1px solid #777;
      padding: 4px 6px;
      background: #fff;
    }}
    .qty {{
      width: 42px;
    }}
    .item {{
      width: 96px;
    }}
    .description {{
      width: 240px;
    }}
    .unit-price {{
      width: 66px;
    }}
    .uom {{
      width: 44px;
    }}
    .discount {{
      width: 62px;
    }}
    .line-total {{
      width: 72px;
    }}
    .right {{
      text-align: right;
    }}
    .center {{
      text-align: center;
    }}
    .items thead th.center {{
      text-align: center;
    }}
    .items thead th.right {{
      text-align: right;
    }}
    .totals-area {{
      margin-top: 8px;
      display: grid;
      grid-template-columns: 1fr 210px;
      align-items: start;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .totals {{
      justify-self: end;
      border-collapse: separate;
      border-spacing: 0 4px;
      font-size: 12px;
    }}
    .totals td {{
      padding: 0;
      vertical-align: middle;
    }}
    .totals .label {{
      text-align: right;
      padding-right: 10px;
      white-space: nowrap;
    }}
    .totals .value {{
      width: 72px;
      border: 1px solid #777;
      height: 22px;
      padding: 0 6px;
      text-align: right;
      font-size: 12px;
    }}
    .totals .total-label {{
      font-weight: 700;
    }}
    .totals .total-value {{
      font-weight: 700;
    }}
    .footer {{
      margin-top: 14px;
      text-align: center;
      font-size: 12px;
      line-height: 1.6;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
  </style>
</head>
<body>
  <div class="invoice-page">
    <section class="top-panels">
      <div class="left">
        <div class="title">INVOICE</div>
        <div class="field-grid">
          <div class="field-label">Date:</div>
          <div class="field-box">{escape(invoice_date)}</div>
          <div class="field-label">Invoice #:</div>
          <div class="field-box">{escape(document["invoice_number"])}</div>
        </div>
      </div>
      <div class="right"></div>
    </section>

    <section class="party-matrix">
      <div class="party-cell party-vendor">
        <div class="party-text">
          {html_lines([vendor["name"], *vendor["address_lines"], vendor["phone"], vendor["email"]])}
        </div>
      </div>
      <div class="party-cell">
        <span class="party-heading stack">SOLD<br>TO</span>
        <span class="party-text">
          {html_lines([bill_to["contact"], bill_to["name"], *bill_to["address_lines"], bill_to["phone"]])}
        </span>
      </div>
      <div class="party-cell">
        <span class="party-heading stack">SHIP<br>TO</span>
        <span class="party-text">
          {html_lines([ship_to["contact"], ship_to["name"], *ship_to["address_lines"], ship_to["phone"]])}
        </span>
      </div>
    </section>

    <table class="meta">
      <tr><td class="label">PO #:</td><td><span class="boxed-inline">{escape(document["po_number"])}</span></td></tr>
      <tr><td class="label">Shipping Method:</td><td>{escape(document["shipping_method"])}</td></tr>
      <tr><td class="label">Shipping Terms:</td><td>{escape(document["shipping_terms"])}</td></tr>
      <tr><td class="label">Delivery Date:</td><td>{escape(invoice_date)}</td></tr>
      <tr><td class="label">Payment Terms:</td><td>{escape(document["payment_terms"])}</td></tr>
      <tr><td class="label">Due Date:</td><td>{escape(due_date)}</td></tr>
    </table>

    <table class="items">
      <thead>
        <tr>
          <th class="qty">Qty</th>
          <th class="item">Item</th>
          <th class="description">Description</th>
          <th class="unit-price right">Unit Price</th>
          <th class="uom center">U/M</th>
          <th class="discount right">Discount</th>
          <th class="line-total right">Line Total</th>
        </tr>
      </thead>
      <tbody>
        {''.join(po_rows)}
      </tbody>
    </table>

    <section class="totals-area">
      <div></div>
      <table class="totals">
        <tr><td class="label">Total Discount:</td><td class="value">0.00</td></tr>
        <tr><td class="label">Subtotal:</td><td class="value">{escape(money(document["sub_total"]).replace(",", ""))}</td></tr>
        <tr><td class="label">Sales Tax:</td><td class="value">{escape(money(document["tax_amount"]).replace(",", ""))}</td></tr>
        <tr><td class="label total-label">Total:</td><td class="value total-value">{escape(money(document["total_amount"]).replace(",", ""))}</td></tr>
      </table>
    </section>

    <footer class="footer">
      <div>Make all checks payable to</div>
      <div>Thank you for your business!</div>
    </footer>
  </div>
</body>
</html>
"""


def render_non_po_html(document: dict[str, Any]) -> str:
    vendor = document["vendor"]
    bill_to = document["bill_to"]
    ship_to = document["ship_to"]
    invoice_date = datetime.fromisoformat(document["invoice_date"]).strftime("%m/%d/%Y")
    due_date = datetime.fromisoformat(document["due_date"]).strftime("%m/%d/%Y")
    non_po_rows = []
    for line in document["line_items"]:
        non_po_rows.append(
            f"""
            <tr>
              <td class="hours right">{escape(format_decimal_text(line["hours"]))}</td>
              <td class="service">{escape(line["service_code"])}</td>
              <td class="description">{escape(line["description"])}</td>
              <td class="labor-rate right">{escape(money(line["labor_rate"]).replace(",", ""))}</td>
              <td class="discount right">{escape(money(line["discount_amount"]).replace(",", ""))}</td>
              <td class="line-total right">{escape(money(line["line_total"]).replace(",", ""))}</td>
            </tr>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(document["invoice_number"])}</title>
  <style>
    @page {{
      size: letter;
      margin: 0.5in 0.55in 0.55in 0.55in;
    }}
    html, body {{
      margin: 0;
      padding: 0;
      background: #fff;
      color: #111;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 14px;
      line-height: 1.15;
    }}
    body {{
      width: 100%;
    }}
    .invoice-page {{
      width: 100%;
    }}
    .top-panels {{
      display: grid;
      grid-template-columns: 1fr 0.94fr;
      border: 1px solid #666;
      min-height: 156px;
    }}
    .top-panels .left {{
      border-right: 1px solid #666;
      padding: 12px 14px 12px 8px;
    }}
    .top-panels .right {{
      min-height: 156px;
    }}
    .title {{
      font-size: 30px;
      font-weight: 700;
      line-height: 1;
      margin: 0 0 8px 0;
    }}
    .field-grid {{
      display: grid;
      grid-template-columns: 54px 118px;
      row-gap: 7px;
      column-gap: 10px;
      align-items: center;
      width: 190px;
    }}
    .field-label {{
      font-size: 12px;
      white-space: nowrap;
    }}
    .field-box {{
      border: 1px solid #777;
      height: 24px;
      display: flex;
      align-items: center;
      padding: 0 6px;
      font-size: 12px;
    }}
    .party-matrix {{
      display: grid;
      grid-template-columns: 1.02fr 1fr 1fr;
      border: 1px solid #666;
      border-top: none;
      min-height: 106px;
    }}
    .party-cell {{
      padding: 13px 10px 10px 10px;
      font-size: 12px;
    }}
    .party-vendor {{
      padding-left: 8px;
    }}
    .party-heading {{
      display: inline-block;
      font-weight: 700;
      margin-right: 8px;
      vertical-align: top;
    }}
    .party-heading.stack {{
      width: 28px;
      text-align: center;
      line-height: 1.2;
    }}
    .party-text {{
      display: inline-block;
      vertical-align: top;
    }}
    .party-vendor .party-text {{
      display: block;
    }}
    .party-text div,
    .party-vendor div {{
      margin: 0 0 3px 0;
    }}
    .meta {{
      margin-top: 18px;
      width: 50%;
      border-collapse: collapse;
      font-size: 12px;
    }}
    .meta td {{
      padding: 0 0 8px 0;
      vertical-align: middle;
    }}
    .meta .label {{
      width: 130px;
    }}
    .items {{
      margin-top: 10px;
      width: 100%;
      border-collapse: collapse;
      border: 1px solid #666;
      font-size: 12px;
    }}
    .items thead th {{
      font-weight: 700;
      padding: 8px 8px 9px 8px;
      border-bottom: 1px solid #666;
      white-space: nowrap;
      text-align: left;
    }}
    .items tbody td {{
      padding: 8px 8px;
      vertical-align: top;
    }}
    .items tbody tr {{
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .hours {{
      width: 58px;
    }}
    .service {{
      width: 98px;
    }}
    .description {{
      width: 256px;
    }}
    .labor-rate {{
      width: 84px;
    }}
    .discount {{
      width: 72px;
    }}
    .line-total {{
      width: 78px;
    }}
    .right {{
      text-align: right;
    }}
    .items thead th.right {{
      text-align: right;
    }}
    .totals-area {{
      margin-top: 10px;
      display: grid;
      grid-template-columns: 1fr 180px;
      justify-items: end;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .totals {{
      border-collapse: separate;
      border-spacing: 0 4px;
      font-size: 12px;
    }}
    .totals td {{
      padding: 0;
      vertical-align: middle;
    }}
    .totals .label {{
      text-align: right;
      padding-right: 10px;
      white-space: nowrap;
    }}
    .totals .value {{
      width: 68px;
      border: 1px solid #777;
      height: 22px;
      padding: 0 6px;
      text-align: right;
    }}
    .totals .total-label,
    .totals .total-value {{
      font-weight: 700;
    }}
    .footer {{
      margin-top: 14px;
      text-align: center;
      font-size: 12px;
      line-height: 1.6;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
  </style>
</head>
<body>
  <div class="invoice-page">
    <section class="top-panels">
      <div class="left">
        <div class="title">INVOICE</div>
        <div class="field-grid">
          <div class="field-label">Date:</div>
          <div class="field-box">{escape(invoice_date)}</div>
          <div class="field-label">Invoice #:</div>
          <div class="field-box">{escape(document["invoice_number"])}</div>
        </div>
      </div>
      <div class="right"></div>
    </section>

    <section class="party-matrix">
      <div class="party-cell party-vendor">
        <div class="party-text">
          {html_lines([vendor["name"], *vendor["address_lines"], vendor["phone"], vendor["email"]])}
        </div>
      </div>
      <div class="party-cell">
        <span class="party-heading stack">SOLD<br>TO</span>
        <span class="party-text">
          {html_lines([bill_to["contact"], bill_to["name"], *bill_to["address_lines"], bill_to["phone"]])}
        </span>
      </div>
      <div class="party-cell">
        <span class="party-heading stack">SHIP<br>TO</span>
        <span class="party-text">
          {html_lines([ship_to["contact"], ship_to["name"], *ship_to["address_lines"], ship_to["phone"]])}
        </span>
      </div>
    </section>

    <table class="meta">
      <tr><td class="label">Shipping Method:</td><td>{escape(document["shipping_method"])}</td></tr>
      <tr><td class="label">Shipping Terms:</td><td>{escape(document["shipping_terms"])}</td></tr>
      <tr><td class="label">Payment Terms:</td><td>{escape(document["payment_terms"])}</td></tr>
      <tr><td class="label">Due Date:</td><td>{escape(due_date)}</td></tr>
    </table>

    <table class="items">
      <thead>
        <tr>
          <th class="hours right">Hours</th>
          <th class="service">Service</th>
          <th class="description">Description</th>
          <th class="labor-rate right">Labor Rate $/Hr</th>
          <th class="discount right">Discount</th>
          <th class="line-total right">Line Total</th>
        </tr>
      </thead>
      <tbody>
        {''.join(non_po_rows)}
      </tbody>
    </table>

    <section class="totals-area">
      <table class="totals">
        <tr><td class="label">Total Discount:</td><td class="value">0.00</td></tr>
        <tr><td class="label">Subtotal:</td><td class="value">{escape(money(document["sub_total"]).replace(",", ""))}</td></tr>
        <tr><td class="label">Sales Tax:</td><td class="value">{escape(money(document["tax_amount"]).replace(",", ""))}</td></tr>
        <tr><td class="label total-label">Total:</td><td class="value total-value">{escape(money(document["total_amount"]).replace(",", ""))}</td></tr>
      </table>
    </section>

    <footer class="footer">
      <div>Make all checks payable to</div>
      <div>Thank you for your business!</div>
    </footer>
  </div>
</body>
</html>
"""


def render_html_to_pdf(html_content: str, output_path: Path) -> None:
    browser = find_browser_executable()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="invoice_html_") as temp_dir:
        html_path = Path(temp_dir) / f"{output_path.stem}.html"
        html_path.write_text(html_content, encoding="utf-8")
        command = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--run-all-compositor-stages-before-draw",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output_path}",
            html_path.as_uri(),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not output_path.exists():
            legacy_command = [
                str(browser),
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={output_path}",
                html_path.as_uri(),
            ]
            completed = subprocess.run(legacy_command, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not output_path.exists():
            raise RuntimeError(
                "HTML-to-PDF rendering failed. "
                f"stdout={completed.stdout.strip()} stderr={completed.stderr.strip()}"
            )


def render_po_invoice_html(document: dict[str, Any], output_path: Path) -> None:
    render_html_to_pdf(render_po_html(document), output_path)


def render_non_po_invoice_html(document: dict[str, Any], output_path: Path) -> None:
    render_html_to_pdf(render_non_po_html(document), output_path)


def render_po_invoice(document: dict[str, Any], output_path: Path) -> None:
    pdf = canvas.Canvas(str(output_path), pagesize=letter)
    width, _height = letter
    pdf.setTitle(document["invoice_number"])
    draw_po_reference_frames(pdf)
    draw_top_text(pdf, 72, 95, "INVOICE", "Helvetica-Bold", 28, top_padding=TITLE_TOP_NUDGE)

    draw_top_text(pdf, 72, 112.58, "Date:", "Helvetica", 10)
    draw_top_text(pdf, 72.65, 136.15, "Invoice #:", "Helvetica", 10)
    draw_top_text(
        pdf,
        131.35,
        108.0,
        datetime.fromisoformat(document["invoice_date"]).strftime("%m/%d/%Y"),
        "Helvetica",
        10,
        top_padding=HEADER_TEXT_TOP_PADDING,
    )
    draw_top_text(pdf, 130.95, 132.22, document["invoice_number"], "Helvetica", 10, top_padding=HEADER_TEXT_TOP_PADDING)

    vendor_lines = [
        document["vendor"]["name"],
        *document["vendor"]["address_lines"],
        document["vendor"]["phone"],
        document["vendor"]["email"],
    ]
    vendor_y = [221.0, 234.68, 248.24, 261.8, 275.36]
    for line, top_y in zip(vendor_lines, vendor_y, strict=False):
        draw_top_text(pdf, 74.88, top_y, line, "Helvetica", 10, top_padding=FRAME_TEXT_TOP_PADDING)

    draw_top_text(pdf, 205.8, 221.0, "SOLD", "Helvetica-Bold", 10, top_padding=FRAME_TEXT_TOP_PADDING)
    draw_top_text(pdf, 221.88, 234.68, "TO", "Helvetica-Bold", 10, top_padding=FRAME_TEXT_TOP_PADDING)
    draw_top_text(pdf, 373.44, 221.0, "SHIP", "Helvetica-Bold", 10, top_padding=FRAME_TEXT_TOP_PADDING)
    draw_top_text(pdf, 384.72, 234.68, "TO", "Helvetica-Bold", 10, top_padding=FRAME_TEXT_TOP_PADDING)

    sold_lines = [
        document["bill_to"]["contact"],
        document["bill_to"]["name"],
        document["bill_to"]["address_lines"][0],
        document["bill_to"]["address_lines"][1],
        document["bill_to"]["phone"],
    ]
    sold_y = [221.0, 234.68, 248.24, 261.8, 275.36]
    for line, top_y in zip(sold_lines, sold_y, strict=False):
        draw_top_text(pdf, 244.2, top_y, line, "Helvetica", 10, top_padding=FRAME_TEXT_TOP_PADDING)

    ship_lines = [
        document["ship_to"]["contact"],
        document["ship_to"]["name"],
        document["ship_to"]["address_lines"][0],
        document["ship_to"]["address_lines"][1],
        document["ship_to"]["phone"],
    ]
    ship_y = [221.0, 234.68, 248.24, 261.8, 275.36]
    for line, top_y in zip(ship_lines, ship_y, strict=False):
        draw_top_text(pdf, 407.04, top_y, line, "Helvetica", 10, top_padding=FRAME_TEXT_TOP_PADDING)

    draw_top_text(pdf, 75.31, 340.87, "PO #:", "Helvetica", 10)
    draw_top_text(pdf, 182.65, 342.92, document["po_number"], "Helvetica", 10)
    draw_top_text(pdf, 75.27, 362.5, "Shipping Method:", "Helvetica", 10)
    draw_top_text(pdf, 183.27, 362.5, document["shipping_method"], "Helvetica", 10)
    draw_top_text(pdf, 75.27, 382.06, "Shipping Terms:", "Helvetica", 10)
    draw_top_text(pdf, 183.27, 380.65, document["shipping_terms"], "Helvetica", 10)
    draw_top_text(pdf, 75.27, 399.62, "Delivery Date:", "Helvetica", 10)
    draw_top_text(pdf, 183.27, 398.8, datetime.fromisoformat(document["invoice_date"]).strftime("%m/%d/%Y"), "Helvetica", 10)
    draw_top_text(pdf, 75.27, 417.3, "Payment Terms:", "Helvetica", 10)
    draw_top_text(pdf, 183.27, 416.95, document["payment_terms"], "Helvetica", 10)
    draw_top_text(pdf, 75.27, 434.86, "Due Date:", "Helvetica", 10)
    draw_top_text(pdf, 183.27, 435.11, datetime.fromisoformat(document["due_date"]).strftime("%m/%d/%Y"), "Helvetica", 10)

    header_positions = [
        ("Qty", 75.27),
        ("Item", 147.27),
        ("Description", 219.27),
        ("Unit Price", 327.27),
        ("Discount", 430.27),
        ("Line Total", 488.27),
        ("U/M", 394.04),
    ]
    for label, x in header_positions:
        draw_top_text(
            pdf,
            x,
            471.98 if label != "U/M" else 471.33,
            label,
            "Helvetica-Bold",
            10,
            top_padding=TABLE_TEXT_TOP_PADDING,
        )

    row_y = [498.11, 524.29, 549.17]
    for top_y, line in zip(row_y, document["line_items"], strict=False):
        draw_top_text(pdf, 77.93, top_y, str(int(line["quantity"])), "Helvetica", 10, top_padding=TABLE_TEXT_TOP_PADDING)
        draw_top_text(pdf, 147.27, top_y, line["item_code"], "Helvetica", 10, top_padding=TABLE_TEXT_TOP_PADDING)
        draw_top_text(pdf, 219.3, top_y, line["description"], "Helvetica", 10, top_padding=TABLE_TEXT_TOP_PADDING)
        draw_top_text(pdf, 398.0, top_y, line["uom"], "Helvetica", 10, top_padding=TABLE_TEXT_TOP_PADDING)
        draw_top_right(
            pdf,
            349.35,
            top_y,
            money(line["unit_price"]).replace(",", ""),
            "Helvetica",
            10,
            top_padding=TABLE_TEXT_TOP_PADDING,
        )
        draw_top_right(
            pdf,
            465.94,
            top_y,
            money(line["discount_amount"]).replace(",", ""),
            "Helvetica",
            10,
            top_padding=TABLE_TEXT_TOP_PADDING,
        )
        draw_top_right(
            pdf,
            536.65,
            top_y,
            money(line["line_total"]).replace(",", ""),
            "Helvetica",
            10,
            top_padding=TABLE_TEXT_TOP_PADDING,
        )

    draw_top_text(pdf, 380.45, 618.55, "Total Discount:", "Helvetica", 10)
    draw_top_right(pdf, 535.34, 618.59, "0.00", "Helvetica", 10, top_padding=TABLE_TEXT_TOP_PADDING)
    draw_top_text(pdf, 382.09, 640.97, "Subtotal:", "Helvetica", 10)
    draw_top_right(pdf, 535.34, 637.59, money(document["sub_total"]).replace(",", ""), "Helvetica", 10, top_padding=TABLE_TEXT_TOP_PADDING)
    draw_top_text(pdf, 382.33, 663.38, "Sales Tax:", "Helvetica", 10)
    draw_top_right(pdf, 121.85, 661.81, f"{document['tax_percent']}", "Helvetica", 10, top_padding=TABLE_TEXT_TOP_PADDING)
    draw_top_right(pdf, 535.34, 661.81, money(document["tax_amount"]).replace(",", ""), "Helvetica", 10, top_padding=TABLE_TEXT_TOP_PADDING)
    draw_top_text(pdf, 382.41, 685.8, "Total:", "Helvetica-Bold", 10)
    draw_top_right(
        pdf,
        535.34,
        684.24,
        money(document["total_amount"]).replace(",", ""),
        "Helvetica-Bold",
        10,
        top_padding=TABLE_TEXT_TOP_PADDING,
    )

    draw_top_text(pdf, 237.39, 720.7, "Make all checks payable to", "Helvetica", 10)
    draw_top_text(pdf, 232.35, 739.3, "Thank you for your business!", "Helvetica", 10)
    pdf.save()


def render_non_po_invoice(document: dict[str, Any], output_path: Path) -> None:
    pdf = canvas.Canvas(str(output_path), pagesize=letter)
    _width, _height = letter
    pdf.setTitle(document["invoice_number"])
    draw_non_po_reference_frames(pdf)
    draw_top_text(pdf, 73, 96, "INVOICE", "Helvetica-Bold", 28)
    draw_top_text(pdf, 73.0, 112.58, "Date:", "Helvetica", 10)
    draw_top_text(pdf, 73.0, 133.29, "Invoice #:", "Helvetica", 10)
    draw_top_text(pdf, 129.64, 111.31, datetime.fromisoformat(document["invoice_date"]).strftime("%m/%d/%Y"), "Helvetica", 10)
    draw_top_text(pdf, 128.98, 136.18, document["invoice_number"], "Helvetica", 10)

    vendor_lines = [
        document["vendor"]["name"],
        *document["vendor"]["address_lines"],
        document["vendor"]["phone"],
        document["vendor"]["email"],
    ]
    vendor_y = [221.0, 234.68, 248.24, 261.8, 275.36]
    for line, top_y in zip(vendor_lines, vendor_y, strict=False):
        draw_top_text(pdf, 74.88, top_y, line, "Helvetica", 10)

    draw_top_text(pdf, 205.8, 221.0, "SOLD", "Helvetica-Bold", 10)
    draw_top_text(pdf, 221.88, 234.68, "TO", "Helvetica-Bold", 10)
    draw_top_text(pdf, 373.44, 221.0, "SHIP", "Helvetica-Bold", 10)
    draw_top_text(pdf, 384.72, 234.68, "TO", "Helvetica-Bold", 10)

    sold_lines = [
        document["bill_to"]["contact"],
        document["bill_to"]["name"],
        document["bill_to"]["address_lines"][0],
        document["bill_to"]["address_lines"][1],
        document["bill_to"]["phone"],
    ]
    sold_y = [221.0, 234.68, 248.24, 261.8, 275.36]
    for line, top_y in zip(sold_lines, sold_y, strict=False):
        draw_top_text(pdf, 244.2, top_y, line, "Helvetica", 10)

    ship_lines = [
        document["ship_to"]["contact"],
        document["ship_to"]["name"],
        document["ship_to"]["address_lines"][0],
        document["ship_to"]["address_lines"][1],
        document["ship_to"]["phone"],
    ]
    ship_y = [221.0, 234.68, 248.24, 261.8, 275.36]
    for line, top_y in zip(ship_lines, ship_y, strict=False):
        draw_top_text(pdf, 407.04, top_y, line, "Helvetica", 10)

    draw_top_text(pdf, 72.0, 338.28, "Shipping Method:", "Helvetica", 10)
    draw_top_text(pdf, 180.0, 339.28, document["shipping_method"], "Helvetica", 10)
    draw_top_text(pdf, 72.0, 356.84, "Shipping Terms:", "Helvetica", 10)
    draw_top_text(pdf, 180.0, 356.84, document["shipping_terms"], "Helvetica", 10)
    draw_top_text(pdf, 72.0, 378.08, "Payment Terms:", "Helvetica", 10)
    draw_top_text(pdf, 180.0, 378.08, document["payment_terms"], "Helvetica", 10)
    draw_top_text(pdf, 72.0, 397.64, "Due Date:", "Helvetica", 10)
    draw_top_text(pdf, 181.35, 399.96, datetime.fromisoformat(document["due_date"]).strftime("%m/%d/%Y"), "Helvetica", 10)

    header_positions = [
        ("Hours", 72.0, 424.76),
        ("Service", 143.83, 424.76),
        ("Description", 189.82, 424.11),
        ("Labor Rate $/Hr", 359.17, 420.84),
        ("Discount", 463.8, 420.84),
        ("Line Total", 523.64, 421.49),
    ]
    for label, x, top_y in header_positions:
        draw_top_text(pdf, x, top_y, label, "Helvetica-Bold", 10)

    base_y = 439.88
    row_step = 18
    for idx, line in enumerate(document["line_items"]):
        top_y = base_y + (idx * row_step)
        draw_top_text(pdf, 72.0, top_y, f"{line['hours']}", "Helvetica", 10)
        draw_top_text(pdf, 144.04, top_y + 0.05, line["service_code"], "Helvetica", 10)
        draw_top_text(pdf, 225.0, top_y + 0.05, line["description"], "Helvetica", 9)
        draw_top_right(pdf, 417.84, top_y - 1.96, money(line["labor_rate"]).replace(",", ""), "Helvetica", 10)
        draw_top_right(pdf, 500.0, top_y - 1.0, money(line["discount_amount"]).replace(",", ""), "Helvetica", 10)
        draw_top_right(pdf, 564.5, top_y, money(line["line_total"]).replace(",", ""), "Helvetica", 10)

    draw_top_text(pdf, 428.73, 482.12, "Total Discount:", "Helvetica", 10)
    draw_boxed_right_value(pdf, 526.0, 478.0, 564.0, 496.8, "00.00", 481.47)
    draw_top_text(pdf, 461.96, 497.65, "Subtotal:", "Helvetica", 10)
    draw_boxed_right_value(pdf, 526.0, 494.0, 564.0, 512.4, money(document["sub_total"]).replace(",", ""), 494.38)
    draw_top_text(pdf, 452.18, 515.14, "Sales Tax:", "Helvetica", 10)
    draw_boxed_right_value(pdf, 526.0, 513.2, 564.0, 530.9, money(document["tax_amount"]).replace(",", ""), 515.79)
    draw_top_text(pdf, 479.41, 535.24, "Total:", "Helvetica-Bold", 10)
    draw_boxed_right_value(pdf, 526.0, 532.1, 564.0, 547.9, money(document["total_amount"]).replace(",", ""), 532.62, "Helvetica-Bold")

    draw_top_text(pdf, 234.12, 560.48, "Make all checks payable to", "Helvetica", 10)
    draw_top_text(pdf, 229.08, 579.08, "Thank you for your business!", "Helvetica", 10)
    pdf.save()


def render_documents(config: RuntimeConfig, documents: list[dict[str, Any]]) -> Path | None:
    config.output_folder.mkdir(parents=True, exist_ok=True)
    config.artifacts_folder.mkdir(parents=True, exist_ok=True)
    manifest_documents: list[dict[str, Any]] = []
    use_html_layout = config.layout_variant == "html_reference_v1"

    for document in documents:
        output_name = config.file_name_pattern.format(
            invoice_number=document["invoice_number"],
            mode=document["document_mode"].lower(),
            document_id=document["document_id"].lower(),
        )
        output_path = config.output_folder / output_name
        if document["document_mode"] == "PO":
            if use_html_layout:
                render_po_invoice_html(document, output_path)
            else:
                render_po_invoice(document, output_path)
        else:
            if use_html_layout:
                render_non_po_invoice_html(document, output_path)
            else:
                render_non_po_invoice(document, output_path)

        if config.write_per_invoice_json:
            json_path = config.artifacts_folder / output_path.with_suffix(".json").name
            json_path.write_text(json.dumps(serialize_document(document), indent=2), encoding="utf-8")

        manifest_documents.append(
            {
                "documentId": document["document_id"],
                "filePath": str(output_path),
                "documentMode": document["document_mode"],
                "invoiceNumber": document["invoice_number"],
                "poNumber": document["po_number"],
                "vendorExpected": document["vendor"]["code"],
                "lineExpectations": [line["service_code"] if document["document_mode"] == "NON_PO" else line["item_code"] for line in document["line_items"]],
                "moneyExpectations": {
                    "subTotal": money(document["sub_total"]),
                    "taxAmount": money(document["tax_amount"]),
                    "totalAmount": money(document["total_amount"]),
                },
            }
        )

    if not config.write_manifest:
        return None

    manifest = {
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "requestEcho": {
            "documentCount": config.document_count,
            "isNonPo": config.is_non_po,
            "outputFolder": str(config.output_folder),
            "randomSeed": config.random_seed,
        },
        "documentCount": len(documents),
        "documents": manifest_documents,
    }
    manifest_path = config.artifacts_folder / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def serialize_document(document: dict[str, Any]) -> dict[str, Any]:
    payload = dict(document)
    payload["sub_total"] = money(document["sub_total"])
    payload["tax_amount"] = money(document["tax_amount"])
    payload["total_amount"] = money(document["total_amount"])
    payload["tax_percent"] = str(document["tax_percent"])
    payload["line_items"] = []
    for line in document["line_items"]:
        serialized = dict(line)
        for key, value in list(serialized.items()):
            if isinstance(value, Decimal):
                serialized[key] = str(value)
        payload["line_items"].append(serialized)
    return payload


def update_registry(config: RuntimeConfig, documents: list[dict[str, Any]], registry: dict[str, Any]) -> None:
    if not documents:
        return
    last_invoice_prefix, last_invoice_number, last_invoice_width = split_number_value(documents[-1]["invoice_number"])
    registry["invoice"] = {
        "prefix": last_invoice_prefix,
        "last_number": last_invoice_number,
        "width": last_invoice_width,
    }
    if not config.is_non_po and documents[-1]["po_number"]:
        po_prefix, po_number, po_width = split_number_value(documents[-1]["po_number"])
        registry["po"] = {
            "prefix": po_prefix,
            "last_number": po_number,
            "width": po_width,
        }
    save_registry(config.registry_path, registry)


def write_run_summary(
    response_path: Path,
    request_json_path: Path,
    config: RuntimeConfig,
    documents: list[dict[str, Any]],
    manifest_path: Path | None,
) -> None:
    response_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "operationStatus": "SUCCEEDED",
        "errorMessage": "",
        "requestJsonPath": str(request_json_path),
        "documentCount": len(documents),
        "documentMode": "NON_PO" if config.is_non_po else "PO",
        "layoutVariant": config.layout_variant,
        "resolvedOutputFolder": str(config.output_folder),
        "manifestPath": str(manifest_path) if manifest_path else "",
        "registryPath": str(config.registry_path),
        "generatedFiles": [
            str(config.output_folder / config.file_name_pattern.format(
                invoice_number=document["invoice_number"],
                mode=document["document_mode"].lower(),
                document_id=document["document_id"].lower(),
            ))
            for document in documents
        ],
    }
    response_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_validation(args: argparse.Namespace) -> int:
    request_path = Path(args.request_json)
    config = parse_request(request_path, args.output_folder)
    
    # If CSI items are pending, skip document building - just validate config
    if config.csi_items_pending:
        mode = "NON_PO" if config.is_non_po else "PO"
        print("Validation: VALID")
        print(f"RequestJsonPath: {request_path.resolve()}")
        print(f"DocumentMode: {mode}")
        print(f"DocumentCount: {config.document_count}")
        print(f"LayoutVariant: {config.layout_variant}")
        print(f"ResolvedOutputFolder: {config.output_folder}")
        print("Note: CSI items pending - full validation deferred until after CSI resolution.")
        return 0
    
    documents, _registry = build_invoice_documents(config)
    mode = "NON_PO" if config.is_non_po else "PO"
    sample_document = documents[0] if documents else None

    print("Validation: VALID")
    print(f"RequestJsonPath: {request_path.resolve()}")
    print(f"DocumentMode: {mode}")
    print(f"DocumentCount: {len(documents)}")
    print(f"LayoutVariant: {config.layout_variant}")
    print(f"ResolvedOutputFolder: {config.output_folder}")
    if sample_document is not None:
        print(f"SampleInvoiceNumber: {sample_document['invoice_number']}")
        if sample_document["po_number"]:
            print(f"SamplePoNumber: {sample_document['po_number']}")
    return 0


def main() -> int:
    args = parse_args()
    try:
        if args.validate_only:
            return run_validation(args)

        config = parse_request(Path(args.request_json), args.output_folder)
        documents, registry = build_invoice_documents(config)
        manifest_path = render_documents(config, documents)
        update_registry(config, documents, registry)
        if args.response_json:
            write_run_summary(Path(args.response_json), Path(args.request_json), config, documents, manifest_path)

        print(f"Generated {len(documents)} invoice(s) in {config.output_folder}")
        if manifest_path:
            print(f"Manifest: {manifest_path}")
        print(f"Registry: {config.registry_path}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
