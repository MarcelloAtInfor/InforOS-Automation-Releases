# Release Packaging Guide

How to package a development project for the release repo. Follow this when adding new projects.

## Principles

1. **End users don't build** — they deploy. No dev tooling, agent docs, or source history.
2. **Every project is self-contained** — a user should be able to deploy from one project folder without reading anything else.
3. **Tenant-specific values are never committed** — use `.example` templates with placeholders.
4. **The README is the product** — if the README doesn't explain it, the user can't do it.

## Packaging Checklist

### Files to Include

| Asset Type | What to Copy | Notes |
|------------|-------------|-------|
| RPA project | `*.xaml`, `project.json`, `config/`, runtime `scripts/` | The importable project |
| Python scripts | Core scripts needed at runtime | Skip dev-only scripts (deploy tools, test harnesses) |
| IDP models | Exported DPF JSON files | Ready to upload to IDP |
| ION workflows | Workflow definition JSONs | Ready to import via ION Desk |
| GenAI specs | Agent/tool definition JSONs | Ready to deploy via GAF CLI or API |
| Sample inputs | 1-2 example request/config files | Enough to test a first run |

### Files to Exclude

| Exclude | Why |
|---------|-----|
| `CLAUDE.md`, `AGENTS.md`, `AGENT_GUIDE.md` | Dev agent instructions |
| `log.md`, `memory/`, `.planning/` | Session history |
| `prepare_deploy.py` | Dev deploy tooling — end users don't run this |
| `deploy.local.json`, `deploy.local.*.json`, `deploy.local.example.json` | All deploy config is dev-side; end users set input args in Studio/tenant |
| `.deploy/` | Generated per-user, not source |
| `__pycache__/`, `*.pyc` | Build artifacts |
| `.kiro/`, `.claude/` | Dev tool configs |
| Test/regression scripts | Unless useful for end-user verification |
| Generated artifacts (PDFs, large outputs) | Users generate their own |

### Sanitization Steps

1. **Grep for tenant IDs** — search all files for known tenant identifiers and replace with placeholders
2. **Grep for personal paths** — search for usernames, OneDrive paths, local machine paths
3. **Check XAML default values** — RPA workflows often have hardcoded tenant URLs and paths in variable defaults
4. **Check project.json** — `filePath` entries and `processId` GUIDs are tenant-specific
5. **Check Python scripts** — look for hardcoded file paths, API endpoints, credential paths
6. **Final sweep** — `grep -rn "your_tenant\|your_username\|your_path" ./ --include="*.py" --include="*.json" --include="*.xaml" --include="*.ps1"`

### README Template

Every project README should follow this structure:

1. **Title and one-line description**
2. **What It Does** — 3-5 bullet points
3. **Prerequisites** — table of requirements
4. **Step-by-step deployment** — numbered steps from download to first run
5. **Configuration Reference** — table of all config fields
6. **Verification** — how to confirm it works
7. **Troubleshooting** — common issues and fixes
8. **What's Included** — file tree with descriptions

### Asset-Specific Notes

#### RPA Projects
- The user's workflow is: download → open in Studio → set input arguments → publish to tenant
- No deploy scripts, no config file editing — all tenant config goes through Studio input arguments or tenant process arguments
- Input arguments should be categorized:
  - **Process arguments** (set once per tenant): `tenantURL`, `site`, `configurationFolder`
  - **User arguments** (set per run by operators): generation parameters like document count, mode, etc.
- XAML variable defaults for paths (`projectPathSource`, `repoRoot`) should auto-resolve at runtime from the workflow's own location — never hardcoded
- `configurationFolder` stays user-configured because it controls where logs/output land on the deployed server
- `processId` in `project.json` should be zeroed (`00000000-...`) — it's assigned on first publish
- If the project depends on Python or other external tools, the workflow should check for availability at runtime and return a clear error message if missing — not a cryptic stack trace
- `prepare_deploy.py` and `deploy.local.*.json` are dev tools — never include them in a release

#### IDP Models (Future)
- Export the DPF model from IDP as JSON
- Include the extraction configuration
- Document which document types it handles
- Note any training data requirements

#### ION Workflows (Future)
- Export workflow definition JSON from ION Desk
- Replace tenant-specific user IDs with placeholders
- Document trigger conditions and expected BOD types
- Note any dependent ION API connections

#### GenAI Agents/Tools (Future)
- Export agent and tool definitions as JSON
- Replace tenant-specific endpoint URLs
- Document required IDO permissions
- Note any dependent ION workflows or IDP flows

## Version Convention

No formal versioning yet. Each project folder represents the current release state. If versioning becomes needed, use GitHub releases with tagged zips.
