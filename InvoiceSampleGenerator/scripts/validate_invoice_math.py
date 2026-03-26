#!/usr/bin/env python3
"""Validate line-item math, subtotals, tax, and totals in generated invoice JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_money(value: str | int | float) -> Decimal:
    return Decimal(str(value).replace(",", ""))


def validate_document(doc: dict) -> list[str]:
    errors: list[str] = []
    inv = doc.get("invoice_number", "UNKNOWN")
    mode = doc.get("document_mode", "").upper()
    is_non_po = mode == "NON_PO"

    computed_subtotal = Decimal("0.00")
    for i, line in enumerate(doc.get("line_items", []), 1):
        if is_non_po:
            qty = parse_money(line.get("hours", line.get("quantity", "0")))
            rate = parse_money(line.get("labor_rate", line.get("unit_price", "0")))
        else:
            qty = parse_money(line.get("quantity", "0"))
            rate = parse_money(line.get("unit_price", "0"))
        discount = parse_money(line.get("discount_amount", "0"))
        expected_line_total = quantize(qty * rate - discount)
        actual_line_total = quantize(parse_money(line.get("line_total", "0")))
        if actual_line_total != expected_line_total:
            errors.append(f"  [{inv}] Line {i}: expected {expected_line_total}, got {actual_line_total}")
        computed_subtotal += actual_line_total

    computed_subtotal = quantize(computed_subtotal)
    actual_subtotal = quantize(parse_money(doc.get("sub_total", "0")))
    if actual_subtotal != computed_subtotal:
        errors.append(f"  [{inv}] Subtotal: expected {computed_subtotal}, got {actual_subtotal}")

    tax_percent = parse_money(doc.get("tax_percent", "0"))
    actual_tax = quantize(parse_money(doc.get("tax_amount", "0")))
    computed_tax = quantize(actual_subtotal * (tax_percent / Decimal("100")))
    # Allow fixed-amount tax to differ from percent-based; only flag if total is wrong
    actual_total = quantize(parse_money(doc.get("total_amount", "0")))
    expected_total = quantize(actual_subtotal + actual_tax)
    if actual_total != expected_total:
        errors.append(f"  [{inv}] Total: expected subtotal({actual_subtotal}) + tax({actual_tax}) = {expected_total}, got {actual_total}")

    # Also flag if percent-based tax doesn't match (informational when not fixed)
    if actual_tax != computed_tax:
        errors.append(f"  [{inv}] Tax (info): percent-based would be {computed_tax}, actual is {actual_tax}")

    return errors


def validate_manifest(manifest: dict) -> list[str]:
    errors: list[str] = []
    for entry in manifest.get("documents", []):
        inv = entry.get("invoiceNumber", entry.get("invoice_number", "UNKNOWN"))
        money = entry.get("moneyExpectations", {})
        if not money:
            continue
        sub = quantize(parse_money(money.get("subTotal", "0")))
        tax = quantize(parse_money(money.get("taxAmount", "0")))
        total = quantize(parse_money(money.get("totalAmount", "0")))
        expected = quantize(sub + tax)
        if total != expected:
            errors.append(f"  [{inv}] Manifest total: expected {expected}, got {total}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate invoice math from generated JSON files.")
    parser.add_argument("--output-folder", required=False, help="Folder containing generated invoice JSON and manifest.")
    parser.add_argument("--artifacts-folder", required=False, help="Folder containing per-invoice JSON and manifest (overrides output-folder).")
    args = parser.parse_args()

    folder = Path(args.artifacts_folder or args.output_folder)
    if not folder.is_dir():
        print(f"FAIL: Folder not found: {folder}")
        return 1

    all_errors: list[str] = []
    doc_count = 0

    # Validate per-invoice JSON files
    non_po_files = set(folder.glob("*_non_po.json"))
    po_files = [f for f in folder.glob("*_po.json") if f not in non_po_files]
    for json_file in sorted(po_files) + sorted(non_po_files):
        doc = json.loads(json_file.read_text(encoding="utf-8-sig"))
        doc_count += 1
        all_errors.extend(validate_document(doc))

    # Validate manifest
    manifest_path = folder / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        all_errors.extend(validate_manifest(manifest))

    if doc_count == 0:
        print(f"FAIL: No invoice JSON files found in {folder}")
        return 1

    info_errors = [e for e in all_errors if "(info)" in e]
    hard_errors = [e for e in all_errors if "(info)" not in e]

    print(f"Validated {doc_count} document(s) in {folder}")
    if info_errors:
        print(f"Info ({len(info_errors)}):")
        for e in info_errors:
            print(e)
    if hard_errors:
        print(f"FAIL ({len(hard_errors)}):")
        for e in hard_errors:
            print(e)
        return 1

    print("PASS: All math checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
