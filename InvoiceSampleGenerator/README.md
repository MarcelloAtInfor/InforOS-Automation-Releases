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
| Python | 3.11 or later, installed on the RPA server or local machine |
| Google Chrome or Microsoft Edge | For browser-backed PDF rendering |
| Python packages | `reportlab` (install via `pip install reportlab`) |
| OAuth credentials (optional) | `.ionapi` file for CSI lookups — only needed if resolving live tenant data |

## Step 1: Download the Project

Download or clone this folder to your local machine. You need both:
- `rpa/` — the RPA project to import into Studio
- `scripts/` — Python scripts invoked by the RPA workflows

Place them in a known location, for example:
```
C:\InforRPA\InvoiceSampleGenerator\
├── rpa\
└── scripts\
```

## Step 2: Install Python Dependencies

Open a command prompt and run:

```cmd
pip install reportlab
```

Verify Python is accessible from the command line:
```cmd
python --version
```

## Step 3: Configure Your Tenant

1. Copy `rpa/deploy.local.example.json` to `rpa/deploy.local.json`
2. Edit `deploy.local.json` with your tenant details:

```json
{
  "tenant_id": "<YOUR_TENANT_ID>",
  "site": "<YOUR_SITE>",
  "tenant_url": "https://mingle-ionapi.inforcloudsuite.com/<YOUR_TENANT_ID>/",
  "configuration_folder": "C:\\InforRPA\\InvoiceSampleGenerator",
  "enable_debug_mode": true,
  "output_dir": ""
}
```

| Field | Description |
|-------|-------------|
| `tenant_id` | Your Infor OS tenant identifier (e.g., `ACME_PRD`) |
| `site` | Your CSI site code (e.g., `ACME_PRD_MAIN`) |
| `tenant_url` | Your Infor OS Mingle API base URL |
| `configuration_folder` | Local folder where the project is stored |
| `enable_debug_mode` | Set to `true` for verbose logging during initial setup |
| `output_dir` | Leave empty to use the default temp directory, or set a specific output path |

## Step 4: Prepare the RPA Deploy Package

From the `rpa/` folder, run the deploy preparation script using **Windows Python** (not WSL):

```cmd
cd C:\InforRPA\InvoiceSampleGenerator\rpa
python scripts\prepare_deploy.py deploy.local.json
```

This creates a `.deploy/` folder with tenant-specific copies of the project files, ready for Studio import.

## Step 5: Import into RPA Studio

1. Open **Infor RPA Studio**
2. Select **File > Open Project**
3. Navigate to the `.deploy/` folder created in Step 4
4. Open `project.json`
5. Studio will load the project with all workflows

## Step 6: Publish to Your Tenant

1. In RPA Studio, select **Publish**
2. Choose your target tenant
3. Confirm the publish

After the first publish, the tenant assigns a `processId`. Subsequent runs of `prepare_deploy.py` will auto-discover this ID.

## Step 7: Run a Test Generation

### From RPA Studio (Attended Mode)

1. Open `MainPage.xaml`
2. Click **Run**
3. The input dialog will prompt for generation parameters:
   - **Document count** — how many invoices to generate
   - **Lines per invoice** — line items per document
   - **PO or Non-PO mode** — type of invoice
   - **Vendor/Item selection** — use existing CSI data or generate synthetic
4. Generated PDFs and manifest appear in the output folder

### From the Command Line (Python Only)

You can also run the renderer directly without RPA:

```cmd
cd C:\InforRPA\InvoiceSampleGenerator

python scripts\render_invoice_batch.py --request-json samples\po_sample_request.json --output-folder C:\temp\invoices
```

This generates PO-based invoice PDFs using the sample request.

For non-PO invoices:
```cmd
python scripts\render_invoice_batch.py --request-json samples\non_po_sample_request.json --output-folder C:\temp\invoices
```

### With Live CSI Data (Optional)

To resolve vendors, items, and numbering from your tenant:

```cmd
python scripts\render_with_csi.py --ionapi "C:\path\to\your\OAUTH.ionapi" --request-json samples\po_sample_request.json --output-folder C:\temp\invoices
```

## Configuration Reference

### Request JSON Fields

| Field | Type | Description |
|-------|------|-------------|
| `docCount` | int | Number of invoices to generate |
| `lineCount` | int | Line items per invoice |
| `isNonPo` | bool | `true` for service invoices, `false` for PO-based |
| `useExistingVendors` | bool | Use real vendor data (CSI or selected) |
| `selectedVendor` | string | Pipe-delimited vendor codes (e.g., `VEND001\|VEND002`) |
| `useExistingItems` | bool | Use real item data (CSI or selected) |
| `selectedItems` | string | Pipe-delimited item codes |
| `invoicePrefix` | string | Invoice number prefix (e.g., `INVDM`) |
| `invoiceStartNumber` | int | Starting invoice number |
| `invoiceWidth` | int | Zero-padded width of invoice number |
| `poPrefix` | string | PO number prefix (e.g., `PODM`) |
| `poStartNumber` | int | Starting PO number |
| `poWidth` | int | Zero-padded width of PO number |
| `layoutVariant` | string | `html_reference_v1` (default, browser-backed) or `reference_v1` (ReportLab) |
| `lookupLatestNumbers` | bool | Query tenant for latest invoice/PO numbers |
| `pairInvoiceAndPoSequence` | bool | Shared numeric suffix across invoice and PO |
| `seed` | int | Random seed for deterministic generation |

See `samples/` for complete request examples.

## Verification

After generating invoices, verify the output:

1. **Check the output folder** — should contain PDF files and a `manifest.json`
2. **Open a PDF** — should look like a realistic invoice with vendor, items, totals
3. **Check the manifest** — JSON file listing all generated documents with their metadata

For automated verification:
```cmd
python scripts\validate_invoice_math.py --artifacts-folder C:\temp\invoices
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `python` not found | Ensure Python 3.11+ is in your system PATH |
| Browser rendering fails | Install Chrome or Edge; ensure it's accessible from the command line |
| CSI lookup timeout | Verify your `.ionapi` file is valid and the tenant is accessible |
| `prepare_deploy.py` fails | Run with Windows Python, not WSL. Ensure `deploy.local.json` exists |
| Studio can't open project | Make sure you're opening from the `.deploy/` folder, not the source `rpa/` folder |

## What's Included

```
InvoiceSampleGenerator/
├── README.md              # This file
├── rpa/                   # RPA project for Studio import
│   ├── MainPage.xaml      # Root workflow (start here)
│   ├── *.xaml             # Supporting workflows
│   ├── project.json       # RPA project manifest
│   ├── config/            # Default request configurations
│   ├── scripts/           # PowerShell helpers used by workflows
│   └── deploy.local.example.json  # Tenant config template
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
