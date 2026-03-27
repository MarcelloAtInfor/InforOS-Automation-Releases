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

Python package `reportlab` is also required. Run once on the target machine:
```cmd
pip install reportlab
```

> If Python is not installed when the process runs, the workflow will display a clear error message with installation instructions.

## Deployment

### Step 1: Download

Download `InvoiceSampleGenerator.zip` from this folder.

### Step 2: Import into RPA Studio

1. Open **Infor RPA Studio**
2. Select **File > Import**
3. Select `InvoiceSampleGenerator.zip`
4. Choose where to extract the project (e.g., `C:\InforRPA\`)
5. Studio extracts and opens the project — all workflows and scripts are included

### Step 3: Configure Input Arguments

Set these values in Studio (for local testing) or on the tenant after publishing (as process arguments):

| Argument | What to Set | Example |
|----------|-------------|---------|
| `configurationFolder` | The folder where Studio extracted the project | `C:\InforRPA\InvoiceSampleGenerator` |
| `tenantURL` | Your Infor OS Mingle API base URL (blank = skip CSI lookups) | `https://mingle-ionapi.inforcloudsuite.com/ACME_PRD/` |
| `site` | Your CSI site code | `ACME_PRD_MAIN` |
| `enableDebugMode` | Verbose logging (optional) | `True` or `False` |

> **Tip:** Leave `tenantURL` blank to run in fully synthetic mode — no tenant connection needed. Useful for testing before connecting to a live environment.

### Step 4: Publish to Your Tenant

1. In RPA Studio, select **Publish**
2. Choose your target tenant
3. After publishing, configure the input arguments on the tenant:
   - Set `configurationFolder`, `tenantURL`, and `site` as **process arguments**
   - Set generation parameters (document count, line count, etc.) as **user arguments** if operators should control them at runtime

### Step 5: Run

**From the tenant:** Trigger the published process. The operator sees an input dialog for generation parameters.

**From Studio (local testing):** Open `MainPage.xaml` and click Run.

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

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Python is not installed" error | Install Python 3.11+ and ensure `python` is in the system PATH |
| "reportlab not found" error | Run `pip install reportlab` on the target machine |
| Browser rendering fails | Ensure Chrome or Edge is installed on the machine |
| CSI lookup timeout | Verify `tenantURL` is correct and the tenant is accessible |
| No output generated | Check `configurationFolder` is set and the folder exists with write permissions |

## What's Included

```
InvoiceSampleGenerator/
├── README.md                      # This file
├── InvoiceSampleGenerator.zip     # Import this into RPA Studio
└── samples/                       # Example request files for reference
    ├── po_sample_request.json
    └── non_po_sample_request.json
```

The zip contains the complete RPA project and all Python scripts. After import, everything is in one folder on your machine.

## Source Code

For development, source code, and contribution: see [InforOS-Automation-Toolkit](https://github.com/MarcelloAtInfor/InforOS-Automation-Toolkit/tree/master/InvoiceSampleGenerator).
