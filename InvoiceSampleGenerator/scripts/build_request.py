#!/usr/bin/env python3
"""Build a generation request JSON file from command-line arguments.

Provides a simpler operator interface than editing JSON by hand.
Outputs a request file compatible with render_invoice_batch.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DEFAULTS = {
    "documentCount": "1",
    "isNonPo": "False",
    "outputFolder": "",
    "randomSeed": "20260310",
    "layoutVariant": "html_reference_v1",
    "useExistingVendors": "True",
    "selectedVendor": "",
    "reuseSameVendorAcrossBatch": "False",
    "useExistingItems": "True",
    "selectedItems": "",
    "lineCount": "3",
    "dateMode": "fixed",
    "fixedInvoiceDate": "",
    "dateOffsetDays": "0",
    "futureDateAllowed": "True",
    "lookupLatestNumbers": "False",
    "pairInvoiceAndPoSequence": "True",
    "invoiceStartValue": "",
    "poStartValue": "",
    "invoicePrefix": "INVDM",
    "invoiceStartNumber": "1",
    "invoiceWidth": "3",
    "poPrefix": "PODM",
    "poStartNumber": "1",
    "poWidth": "6",
    "taxMode": "percent_of_subtotal",
    "taxPercent": "8.00",
    "fixedTaxAmount": "",
    "writeManifest": "True",
    "writePerInvoiceJson": "True",
    "fileNamePattern": "{invoice_number}_{mode}.pdf",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a generation request JSON file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Simple 1-PO request
  python build_request.py -o request.json --invoice-start INVDM100 --po-start PODM000100

  # 5 PO invoices with specific vendors
  python build_request.py -o request.json --count 5 --vendors "BICYCLE_PARTS|ATLAS_CONVEYOR" --invoice-start INVDM200 --po-start PODM000200

  # Non-PO batch
  python build_request.py -o request.json --count 3 --non-po --invoice-start INVDM300 --tax-mode zero_tax
""",
    )
    parser.add_argument("-o", "--output", required=True, help="Output request JSON path")
    parser.add_argument("--count", type=int, help="Number of invoices")
    parser.add_argument("--non-po", action="store_true", help="Generate non-PO invoices")
    parser.add_argument("--output-folder", help="Renderer output folder")
    parser.add_argument("--seed", help="Random seed")
    parser.add_argument("--layout", choices=["html_reference_v1", "reference_v1"], help="Layout variant")
    parser.add_argument("--vendors", help="Pipe-delimited vendor codes")
    parser.add_argument("--no-existing-vendors", action="store_true", help="Use synthetic vendors")
    parser.add_argument("--items", help="Pipe-delimited item/service codes")
    parser.add_argument("--no-existing-items", action="store_true", help="Use synthetic items")
    parser.add_argument("--lines", type=int, help="Lines per invoice")
    parser.add_argument("--date", help="Fixed invoice date (YYYY-MM-DD)")
    parser.add_argument("--invoice-start", help="Full invoice start value (e.g. INVDM100)")
    parser.add_argument("--po-start", help="Full PO start value (e.g. PODM000100)")
    parser.add_argument("--no-pair", action="store_true", help="Don't pair invoice/PO numbering")
    parser.add_argument("--tax-mode", choices=["percent_of_subtotal", "zero_tax", "fixed_amount"])
    parser.add_argument("--tax-percent", help="Tax percent")
    parser.add_argument("--fixed-tax", help="Fixed tax amount")

    args = parser.parse_args()
    request = dict(DEFAULTS)

    if args.count is not None:
        request["documentCount"] = str(args.count)
    if args.non_po:
        request["isNonPo"] = "True"
    if args.output_folder:
        request["outputFolder"] = args.output_folder
    if args.seed:
        request["randomSeed"] = args.seed
    if args.layout:
        request["layoutVariant"] = args.layout
    if args.vendors:
        request["selectedVendor"] = args.vendors
    if args.no_existing_vendors:
        request["useExistingVendors"] = "False"
    if args.items:
        request["selectedItems"] = args.items
    if args.no_existing_items:
        request["useExistingItems"] = "False"
    if args.lines is not None:
        request["lineCount"] = str(args.lines)
    if args.date:
        request["fixedInvoiceDate"] = args.date
    if args.invoice_start:
        request["invoiceStartValue"] = args.invoice_start
    if args.po_start:
        request["poStartValue"] = args.po_start
    if args.no_pair:
        request["pairInvoiceAndPoSequence"] = "False"
    if args.tax_mode:
        request["taxMode"] = args.tax_mode
    if args.tax_percent:
        request["taxPercent"] = args.tax_percent
    if args.fixed_tax:
        request["fixedTaxAmount"] = args.fixed_tax

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(request, indent=2), encoding="utf-8")
    print(f"Request written to: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
