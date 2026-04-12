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
2. Click **Import Project** on the start screen
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

After the setup check, a configuration dialog appears with the following options:

| Setting | Description | Default |
|---------|-------------|---------|
| Document Count | Number of invoice PDFs to generate | `3` |
| Document Mode | `PO` for purchase-order-based invoices, `Non-PO` for service/labor invoices | `PO` |
| Lines Per Invoice | Number of line items per invoice. Use a range like `2-6` for variation | `4` |
| Quantity Per Line | Quantity per line item. Use a range like `1-10` for variation | `1-10` |
| Output Folder | Where generated PDFs are saved | `C:\InforRPA\InvoiceSampleGenerator\Output\DefaultRun` |
| Invoice Date | Date printed on the invoices (YYYY-MM-DD) | Today's date |
| Tax Percent | Tax rate applied to each invoice subtotal | `8.00` |
| Invoice Prefix | Prefix for invoice numbers (e.g., `INV` produces `INV001`, `INV002`, ...) | `INV` |
| PO Prefix | Prefix for PO numbers (e.g., `PO` produces `PO000001`, `PO000002`, ...) | `PO` |
| Use live CSI vendors and items | When checked, pulls real vendor and item data from your CSI tenant instead of using synthetic data. Requires `tenantURL` to be configured. | Enabled if tenant connected |
| Reuse same vendor across batch | When checked, all invoices in the batch use the same vendor. When unchecked, each invoice gets a different vendor. | Unchecked |
| Selected Vendors | Pipe-delimited list of specific vendor codes to use (e.g., `V001\|V002`). Leave blank to pick randomly from CSI. | Blank |
| Selected Items | Pipe-delimited list of specific item codes to use (e.g., `ITEM01\|ITEM02`). Leave blank to pick randomly from CSI. | Blank |
| Lookup latest PO/invoice numbers from CSI | When checked, queries CSI for the highest existing PO with your prefix and starts numbering from the next value. Prevents duplicate PO numbers. | Enabled if tenant connected |
| Pair invoice and PO number sequences | When checked, invoice and PO numbers increment together (e.g., `INVDM007` pairs with `PODM000007`). | Checked |

Generated PDFs appear in the configured output folder. Manifests and logs are saved in the `configurationFolder`.

### Step 5: Publish (Optional)

To run from the tenant instead of Studio:

1. In RPA Studio, select **Publish**
2. Choose your target tenant
3. Configure `configurationFolder`, `tenantURL`, and `site` as process arguments on the tenant

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Infor RPA Studio | 2026.01 or later |
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
