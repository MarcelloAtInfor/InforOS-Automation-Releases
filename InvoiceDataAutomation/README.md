# InvoiceDataAutomation — Deployment Guide

Deterministic invoice processing automation for Infor CloudSuite Industrial. Extracts invoice data from PDF documents via OCR, then creates or reuses vendors, items, and purchase orders in CSI with full verification.

## What It Does

- Extracts invoice data from PDF documents using Infor IDP (OCR)
- Deterministically matches or creates vendors in CSI using scored candidate selection
- Creates or reuses items and purchase orders with line-level detail
- Verifies all persisted data in CSI after every write
- Sends operator notifications through ION workflows (per-document, batch summary, or error)
- Supports PO-based and non-PO (review-center handoff) document modes

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Infor RPA Studio | 2026.01 or later |
| Infor CloudSuite Industrial | Active CSI/SyteLine tenant |
| IDP Access | To import the invoice extraction model |
| ION Desk Access | To import and activate notification workflows |
| ION API Connection | RPA uses ION API for CSI IDO calls and workflow triggers |

## Deployment

Assets must be deployed in this order because of dependencies between them.

### Step 1: Import IDP Model

1. Open the IDP UI in your Infor OS tenant
2. Navigate to Document Processor Flows
3. Import the provided DPF file from the `IDP/` folder
4. Note the DPF name — you will need it when binding OCR in the RPA project

### Step 2: Import ION Workflows

1. Open ION Desk > Workflows
2. Import each XML file from the `ION/` folder:
   - `RPA_Invoice_Notification.xml` — sends a notification per processed invoice
   - `RPA_Invoice_Batch_Notification.xml` — sends a batch summary after all documents
   - `RPA_Error_Notification.xml` — sends a notification on unhandled RPA exceptions
3. Activate each workflow after import

No manual GUID configuration is needed — the RPA process dynamically looks up the notification recipient from the email address you provide at runtime.

### Step 3: Import RPA Project

1. Open Infor RPA Studio
2. Click **Import Project** on the start screen
3. Select `DemoInvoiceLoader_V4.zip` from the `RPA/` folder
4. Studio imports and opens the project

### Step 4: Configure Input Arguments

Set these values in Studio's input arguments panel before running:

| Argument | What to Set | Example |
|----------|-------------|---------|
| `configurationFolder` | The folder where Studio extracted the project | `C:\InforRPA\DemoInvoiceLoader_V4` |
| `inputFolderPath` | Folder containing invoice PDFs to process | `C:\InforRPA\DemoInvoiceLoader_V4\Input` |
| `tenantURL` | Your Infor OS Mingle API base URL | `https://mingle-ionapi.inforcloudsuite.com/ACME_PRD/` |
| `site` | Your CSI site code | `ACME_PRD_MAIN` |
| `warehouse` | Default warehouse | `MAIN` |
| `terms` | Default payment terms | `N30` |
| `userEmail` | Notification recipient email | `operator@company.com` |
| `enableNotifications` | Enable ION notifications | `True` / `False` |
| `enableDebugMode` | Verbose logging | `True` / `False` |
| `documentMode` | `PO` for full processing, `NON_PO` for review-center handoff | `PO` |

### Step 5: Bind OCR

The OCR binding is tenant-specific and must be done manually after import:

1. Open `ExtractOCRData.xaml` in Studio
2. Find the placeholder OCR activity
3. Reconnect it to the IDP model you imported in Step 1 (`CSI_APInvoice_Extract`)
4. Save the project

### Step 6: Test

1. Place a sample invoice PDF in the input folder (samples are provided in `samples/`)
2. Run `MainPage.xaml` from Studio
3. Verify: vendor created/reused, items created/reused, PO created with correct lines, notification received

### Step 7: Publish (Optional)

To run from the tenant instead of Studio:

1. In RPA Studio, select **Publish**
2. Choose your target tenant
3. Configure the process arguments on the tenant (same values as Step 4)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| OCR extraction fails | Verify IDP model was imported and OCR activity is bound in `ExtractOCRData.xaml` |
| Notification not received | Check ION workflows are activated and `userEmail` is a valid tenant user |
| CSI write fails | Verify `tenantURL` and `site` are correct, ION API connection is active |
| Vendor not found or duplicated | Check CSI vendor data — the flow uses deterministic scoring to match |
| PO lines missing or incorrect | Verify items exist in CSI and UOM is supported (the flow auto-maps common UOMs like PR→EA) |

## What's Included

```
InvoiceDataAutomation/
├── README.md                          # This file
├── RPA/
│   └── DemoInvoiceLoader_V4.zip      # Import into RPA Studio
├── IDP/
│   └── CSI_APInvoice_Extract.*       # Import into IDP UI
├── ION/
│   ├── RPA_Invoice_Notification.xml       # Per-document notification
│   ├── RPA_Invoice_Batch_Notification.xml # Batch summary notification
│   └── RPA_Error_Notification.xml         # Error notification
└── samples/
    ├── PO_Invoice_Sample.pdf          # Sample PO-based invoice for testing
    └── Non_PO_Invoice_Sample.pdf      # Sample non-PO invoice for testing
```

## Related Projects

- [InvoiceSampleGenerator](../InvoiceSampleGenerator/) — Generate test invoice PDFs for this workflow
