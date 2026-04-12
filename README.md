# InforOS Automation Releases

Deployment-ready assets and step-by-step guides for Infor OS automation projects built on CloudSuite Industrial (SyteLine).

## Who This Is For

Operators and tenant administrators who want to deploy pre-built automation into their Infor CloudSuite Industrial environment. No development tools, LLM agents, or source code knowledge required.

## Available Projects

| Project | Description | Assets |
|---------|-------------|--------|
| [InvoiceDataAutomation](InvoiceDataAutomation/) | Deterministic invoice processing — OCR extraction, vendor/item/PO creation, and verification in CSI | RPA, IDP, ION |
| [InvoiceSampleGenerator](InvoiceSampleGenerator/) | Deterministic invoice PDF generator for demo and testing workflows | RPA |

## General Prerequisites

Most projects require:

- **Infor RPA Studio** — 2024.x or later, to import and publish RPA projects
- **Infor CloudSuite Industrial tenant** — target environment for deployment (some projects can run without one)
- **Windows 10/11** — for automatic dependency installation

Each project README lists its specific requirements.

## How Deployment Works

Every project follows the same general pattern:

1. **Download** the zip from the project folder
2. **Import** into RPA Studio (File > Import)
3. **Configure** input arguments in Studio (tenant URL, site, etc.)
4. **Run** from Studio to test
5. **Publish** to your tenant (optional)

## Project Structure Convention

```
ProjectName/
├── README.md                  # Deployment guide (start here)
├── ProjectName.zip            # Import into RPA Studio
└── samples/                   # Example inputs for testing (if applicable)
```

Projects with multiple components (e.g., RPA + IDP + ION) may include additional folders.

## Release Notes

See individual project READMEs for version history and known limitations.
