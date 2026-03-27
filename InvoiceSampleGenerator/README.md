# InvoiceSampleGenerator — Deployment Guide

Deterministic invoice PDF generator for Infor CloudSuite Industrial. Produces realistic PO-based and non-PO-based invoice PDFs for use with demo workflows, testing, and training.

## What It Does

- Generates batches of invoice PDFs from a simple configuration
- Supports PO-based invoices (goods/materials) and non-PO invoices (services/labor)
- Deterministic: same inputs always produce the same outputs
- Optionally resolves live vendor, item, and numbering data from your CSI tenant
- Emits a machine-readable manifest alongside the PDFs for downstream automation

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Infor RPA Studio | 2024.x or later |
| Infor CloudSuite Industrial tenant | Any active CSI/SyteLine tenant |
| Python 3.11+ | Must be installed and in the system PATH on the machine that runs the RPA process |
| Google Chrome or Microsoft Edge | For browser-backed PDF rendering |

Python package `reportlab` is also required:
```cmd
pip install reportlab
```

> If Python is not installed when the process runs, the workflow will return a clear error message indicating Python is required.

## Deployment

### Step 1: Download

Download the `InvoiceSampleGenerator/` folder from this repo. You need both:
- `rpa/` — the RPA project
- `scripts/` — Python scripts invoked by the RPA workflows

Place them together in a known location on the target machine:
```
C:\InforRPA\InvoiceSampleGenerator\
├── rpa\
├── scripts\
└── samples\
```

### Step 2: Open in RPA Studio

1. Open **Infor RPA Studio**
2. Open the `rpa/` folder as a project
3. You should see `MainPage.xaml` as the root workflow

### Step 3: Configure Input Arguments

The project uses input arguments that you configure either in Studio (for local testing) or on the tenant (after publishing). Set these values:

| Argument | What to Set | Example |
|----------|-------------|---------|
| `configurationFolder` | Folder where logs and output files are written | `C:\InforRPA\InvoiceSampleGenerator` |
| `tenantURL` | Your Infor OS Mingle API base URL (blank = skip CSI lookups) | `https://mingle-ionapi.inforcloudsuite.com/ACME_PRD/` |
| `site` | Your CSI site code | `ACME_PRD_MAIN` |
| `enableDebugMode` | Verbose logging (optional) | `True` or `False` |

> **Tip:** If you leave `tenantURL` blank, the generator runs in fully synthetic mode — no tenant connection needed. This is useful for testing the flow before connecting to a live environment.

### Step 4: Publish to Your Tenant

1. In RPA Studio, select **Publish**
2. Choose your target tenant
3. After publishing, configure the input arguments on the tenant:
   - Set `configurationFolder`, `tenantURL`, and `site` as **process arguments** with your tenant-specific values
   - Set any generation parameters (document count, line count, etc.) as **user arguments** if you want operators to control them at runtime

### Step 5: Run

**From the tenant:** Trigger the published process. The operator will see an input dialog for generation parameters (document count, PO/non-PO mode, vendor/item selection, etc.).

**From Studio (local testing):** Open `MainPage.xaml` and click Run. Fill in the input dialog when prompted.

Generated PDFs and a `manifest.json` appear in the configured output folder.

## Generation Parameters

These are the operator-facing inputs shown at runtime:

| Parameter | Type | Description |
|-----------|------|-------------|
| `docCount` | int | Number of invoices to generate |
| `lineCount` | int | Line items per invoice |
| `isNonPo` | bool | `True` for service invoices, `False` for PO-based |
| `useExistingVendors` | bool | Use real vendor data from CSI |
| `selectedVendor` | string | Specific vendor codes, pipe-delimited (e.g., `VEND001\|VEND002`) |
| `useExistingItems` | bool | Use real item data from CSI |
| `selectedItems` | string | Specific item codes, pipe-delimited |
| `invoicePrefix` | string | Invoice number prefix (e.g., `INVDM`) |
| `invoiceStartNumber` | int | Starting invoice number |
| `poPrefix` | string | PO number prefix (e.g., `PODM`) |
| `poStartNumber` | int | Starting PO number |
| `lookupLatestNumbers` | bool | Query tenant for latest invoice/PO numbers to avoid collisions |
| `seed` | int | Random seed for deterministic generation |

See `samples/` for complete request examples.

## Verification

After a successful run:

1. Check the output folder for PDF files and a `manifest.json`
2. Open a PDF — should look like a realistic invoice with vendor info, line items, and totals
3. The manifest lists all generated documents with their metadata (vendor, items, amounts)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Python is not installed" error | Install Python 3.11+ and ensure `python` is in the system PATH |
| "reportlab not found" error | Run `pip install reportlab` |
| Browser rendering fails | Ensure Chrome or Edge is installed on the machine |
| CSI lookup timeout | Verify `tenantURL` is correct and the tenant is accessible |
| No output generated | Check `configurationFolder` is set and the folder exists with write permissions |

## What's Included

```
InvoiceSampleGenerator/
├── README.md              # This file
├── rpa/                   # RPA project — open in Studio
│   ├── MainPage.xaml      # Root workflow
│   ├── *.xaml             # Supporting workflows
│   ├── project.json       # RPA project manifest
│   ├── config/            # Default request configurations
│   └── scripts/           # PowerShell helpers used by workflows
├── scripts/               # Python rendering and validation
│   ├── render_invoice_batch.py    # Core PDF renderer
│   ├── build_request.py           # Request JSON builder
│   ├── csi_lookup.py              # Live CSI data resolution
│   ├── render_with_csi.py         # CSI-enabled rendering wrapper
│   ├── validate_invoice_math.py   # Math verification
│   └── validate_determinism.py    # Reproducibility verification
└── samples/               # Example request files
    ├── po_sample_request.json      # PO-based invoice request
    └── non_po_sample_request.json  # Non-PO invoice request
```

## Source Code

For development, source code, and contribution: see [InforOS-Automation-Toolkit](https://github.com/MarcelloAtInfor/InforOS-Automation-Toolkit/tree/master/InvoiceSampleGenerator).
