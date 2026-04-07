# InvoiceSampleGenerator — Deployment Guide

Deterministic invoice PDF generator for Infor CloudSuite Industrial. Produces realistic PO-based and non-PO-based invoice PDFs for use with demo workflows, testing, and training.

## What It Does

- Generates batches of invoice PDFs from a simple configuration dialog
- Supports PO-based invoices (goods/materials) and non-PO invoices (services/labor)
- Deterministic: same inputs always produce the same outputs
- Optionally resolves live vendor, item, and numbering data from your CSI tenant
- Emits a machine-readable manifest alongside the PDFs for downstream automation

## Deployment

### Step 1: Download

Download `InvoiceSampleGenerator.zip` from this folder.

### Step 2: Import into RPA Studio

1. Open **Infor RPA Studio**
2. Select **File > Import**
3. Select `InvoiceSampleGenerator.zip`
4. Choose where to extract the project (e.g., `C:\InforRPA\`)
5. Studio extracts and opens the project

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

Click **Run** on `MainPage.xaml`. A configuration dialog appears where you can set:

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

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Python is not installed" error | Install Python 3.11+ and ensure `python` is in the system PATH (see Prerequisites below) |
| Browser rendering fails | Ensure Google Chrome or Microsoft Edge is installed on the machine |
| CSI lookup timeout | Verify `tenantURL` is correct and the tenant is accessible |
| No output generated | Check `configurationFolder` is set and the folder exists with write permissions |

## What's Included

```
InvoiceSampleGenerator/
├── README.md                      # This file
└── InvoiceSampleGenerator.zip     # Import this into RPA Studio
```

## Prerequisites

The RPA project uses Python internally to render invoice PDFs. The following must be installed on the machine that runs the process:

| Requirement | Details |
|-------------|---------|
| Infor RPA Studio | 2024.x or later |
| Infor CloudSuite Industrial tenant | Any active CSI/SyteLine tenant (optional — synthetic mode works without one) |
| Python 3.11+ | Must be installed and in the system PATH |
| `reportlab` Python package | Run `pip install reportlab` once from a command prompt |
| Google Chrome or Microsoft Edge | For browser-backed PDF rendering |

## Source Code

For development, source code, and contribution: see [InforOS-Automation-Toolkit](https://github.com/MarcelloAtInfor/InforOS-Automation-Toolkit/tree/master/InvoiceSampleGenerator).
