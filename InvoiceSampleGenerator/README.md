# InvoiceSampleGenerator — Deployment Guide

Deterministic invoice PDF generator for Infor CloudSuite Industrial. Produces realistic PO-based and non-PO-based invoice PDFs for use with demo workflows, testing, and training.

## What It Does

- Generates batches of invoice PDFs from a simple configuration dialog
- Supports PO-based invoices (goods/materials) and non-PO invoices (services/labor)
- Deterministic: same inputs always produce the same outputs
- Optionally resolves live vendor, item, and numbering data from your CSI tenant
- Emits a machine-readable manifest alongside the PDFs for downstream automation
- Automatically installs Python and required packages on first run

## Deployment

### Step 1: Download

Download `InvoiceSampleGenerator.zip` from this folder.

### Step 2: Import into RPA Studio

1. Open **Infor RPA Studio**
2. Select **File > Import**
3. Select `InvoiceSampleGenerator.zip`
4. Studio imports and opens the project

### Step 3: Configure Input Arguments

Set these values in Studio's input arguments panel:

| Argument | What to Set | Example |
|----------|-------------|---------|
| `configurationFolder` | The folder where Studio extracted the project | `C:\InforRPA\InvoiceSampleGenerator` |
| `tenantURL` | Your Infor OS Mingle API base URL (blank = skip CSI lookups) | `https://mingle-ionapi.inforcloudsuite.com/ACME_PRD/` |
| `site` | Your CSI site code | `ACME_PRD_MAIN` |
| `enableDebugMode` | Verbose logging (optional) | `True` or `False` |

> **Tip:** Leave `tenantURL` blank to run in fully synthetic mode — no tenant connection needed. Useful for testing before connecting to a live environment.

### Step 4: Run

Click **Run** on `MainPage.xaml`.

On first run, the project automatically checks for Python and required packages:
- If Python is not installed, it will attempt to install it automatically via `winget`
- If the `reportlab` package is missing, it will install it automatically via `pip`
- If Python was just installed, you will be prompted to restart RPA Studio once so it can detect Python

After the setup check, a configuration dialog appears where you can set:

- Number of invoices to generate
- Document mode (PO or Non-PO)
- Output folder
- Whether to use live CSI vendors and items
- Invoice and PO number prefixes
- Tax settings

Generated PDFs and a `manifest.json` appear in the configured output folder.

### Step 5: Publish (Optional)

To run from the tenant instead of Studio:

1. In RPA Studio, select **Publish**
2. Choose your target tenant
3. Configure `configurationFolder`, `tenantURL`, and `site` as process arguments on the tenant

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Infor RPA Studio | 2024.x or later |
| Infor CloudSuite Industrial tenant | Any active CSI/SyteLine tenant (optional — synthetic mode works without one) |
| Windows 10/11 | Required for automatic Python installation via `winget` |
| Google Chrome or Microsoft Edge | For browser-backed PDF rendering |

> **Note:** Python 3.11+ and the `reportlab` package are required but are installed automatically on first run. No manual setup needed.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Restart RPA Studio" message on first run | Python was just installed. Close and reopen Studio, then run again. This only happens once. |
| Python auto-install fails | Install Python 3.11+ manually from [python.org](https://www.python.org/downloads/) or the Windows Store, restart Studio, and run again |
| reportlab install fails | Open a command prompt and run `pip install reportlab`, then run again |
| Browser rendering fails | Ensure Google Chrome or Microsoft Edge is installed on the machine |
| CSI lookup timeout | Verify `tenantURL` is correct and uses `mingle-ionapi.inforcloudsuite.com` (not `mingle-portal`) |
| No output generated | Check `configurationFolder` is set and the folder exists with write permissions |

## What's Included

```
InvoiceSampleGenerator/
├── README.md                      # This file
└── InvoiceSampleGenerator.zip     # Import this into RPA Studio
```
