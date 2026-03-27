# InforOS Automation Releases

Deployment-ready assets and step-by-step guides for Infor OS automation projects built on CloudSuite Industrial (SyteLine).

## Who This Is For

Operators and tenant administrators who want to deploy pre-built automation into their Infor CloudSuite Industrial environment. No development tools, LLM agents, or source code knowledge required.

For source code and development, see [InforOS-Automation-Toolkit](https://github.com/MarcelloAtInfor/InforOS-Automation-Toolkit).

## Available Projects

| Project | Description | Assets |
|---------|-------------|--------|
| [InvoiceSampleGenerator](InvoiceSampleGenerator/) | Deterministic invoice PDF generator for demo and testing workflows | RPA, Python |

## General Prerequisites

Most projects require some combination of:

- **Infor RPA Studio** — to import and publish RPA projects
- **Infor CloudSuite Industrial tenant** — target environment for deployment
- **Python 3.11+** — for projects that include Python scripts
- **OAuth credentials** — `.ionapi` file for your tenant (from Infor OS Portal > Infor ION API)

Each project README lists its specific requirements.

## How Deployment Works

Every project follows the same general pattern:

1. **Download** the project folder from this repo
2. **Configure** your tenant details using the provided template (`deploy.local.example.json`)
3. **Import** into the appropriate Infor tool (RPA Studio, IDP, ION, etc.)
4. **Publish** to your tenant
5. **Verify** using the provided test steps

## Project Structure Convention

Each project folder follows this layout:

```
ProjectName/
├── README.md                  # Deployment guide (start here)
├── ProjectName.zip            # Import into the appropriate Infor tool
└── samples/                   # Example inputs/outputs for reference (if applicable)
```

The zip is the deliverable. It contains everything needed to deploy — RPA workflows, scripts, configs — in the format the target tool expects for import.

Not every project uses every asset type. Projects with multiple components (e.g., RPA + IDP + ION) may include multiple zips.

## Release Notes

See individual project READMEs for version history and known limitations.
