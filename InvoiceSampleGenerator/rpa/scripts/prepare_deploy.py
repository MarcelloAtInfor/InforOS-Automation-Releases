#!/usr/bin/env python3
"""Build a tenant-specific, Studio-ready copy of InvoiceSampleGenerator from repo-safe sources."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_CONFIG_PATH = PROJECT_DIR / "deploy.local.json"
PUBLISHED_PROJECT_NAME = "InvoiceSampleGenerator"

# Add shared module to path
REPO_ROOT = PROJECT_DIR.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared.rpa_deploy import lookup_rpa_process_id


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing local config: {config_path}")
    config = read_json(config_path)
    
    # Try API lookup if no process_id configured
    if not config.get("process_id"):
        try:
            found = lookup_rpa_process_id(
                PUBLISHED_PROJECT_NAME,
                config["tenant_id"],
                config["tenant_url"],
            )
        except Exception as e:
            print(f"Note: Could not lookup processId from tenant ({e})")
        else:
            if found:
                config["process_id"] = found
                print(f"Found processId from tenant: {found}")
    
    # Generate new GUID if still missing (first publish)
    if not config.get("process_id"):
        import uuid
        config["process_id"] = str(uuid.uuid4()).upper()
        print(f"Generated new processId for first publish: {config['process_id']}")
    
    return config


def build_output_dir(config: dict) -> Path:
    if config.get("output_dir"):
        return Path(config["output_dir"])
    return PROJECT_DIR / ".deploy" / f"{PUBLISHED_PROJECT_NAME}_{config['tenant_id']}"


def copy_project_tree(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir, onerror=lambda f, p, _: (os.chmod(p, stat.S_IWRITE), f(p)))

    def ignore(_src: str, names: list[str]) -> set[str]:
        return {n for n in names if n in {".deploy", "__pycache__"} or n.startswith("deploy.local")}

    shutil.copytree(PROJECT_DIR, output_dir, ignore=ignore)


def patch_project_json(output_dir: Path, config: dict) -> None:
    path = output_dir / "project.json"
    data = read_json(path)
    meta = data.get("tenantMetadata", [{}])
    meta[0]["tenantId"] = config["tenant_id"]
    meta[0]["processId"] = config["process_id"]
    data["name"] = PUBLISHED_PROJECT_NAME
    for entry in data.get("sourceFiles", []):
        entry["filePath"] = str(output_dir)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def replace_activity_attr(content: str, attr_name: str, value: str) -> str:
    pattern = rf'({re.escape(attr_name)}=\")([^\"]*)(\")'
    updated, count = re.subn(pattern, lambda m: f"{m.group(1)}{value}{m.group(3)}", content, count=1)
    if count != 1:
        raise ValueError(f"Could not replace Activity attribute {attr_name}")
    return updated


def patch_mainpage(output_dir: Path, config: dict) -> None:
    path = output_dir / "MainPage.xaml"
    content = path.read_text(encoding="utf-8")

    for attr, val in {
        "this:Workflow.configurationFolder": config["configuration_folder"],
        "this:Workflow.tenantURL": config["tenant_url"],
        "this:Workflow.site": config["site"],
        "this:Workflow.enableDebugMode": str(config.get("enable_debug_mode", False)),
    }.items():
        content = replace_activity_attr(content, attr, val)

    content, count = re.subn(
        r'(<Variable x:TypeArguments="x:String" Default=")([^"]*)(" Name="projectPathSource" />)',
        lambda m: f"{m.group(1)}{output_dir}{m.group(3)}", content, count=1)
    if count != 1:
        raise ValueError("Could not replace projectPathSource")

    content, count = re.subn(
        r'(<Variable x:TypeArguments="x:String" Default=")([^"]*)(" Name="repoRoot" />)',
        lambda m: f"{m.group(1)}{PROJECT_DIR.parent.parent}{m.group(3)}", content, count=1)
    if count != 1:
        raise ValueError("Could not replace repoRoot")

    path.write_text(content, encoding="utf-8")


def patch_ido_load(output_dir: Path, config: dict) -> None:
    path = output_dir / "ExecuteIdoLoad.xaml"
    if path.exists():
        path.write_text(path.read_text(encoding="utf-8").replace("[site]", config["site"]), encoding="utf-8")


def validate_output(output_dir: Path) -> None:
    data = read_json(output_dir / "project.json")
    if {e["filePath"] for e in data.get("sourceFiles", [])} != {str(output_dir)}:
        raise ValueError("project.json has unexpected source paths")


def main() -> int:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    if not config_path.is_absolute():
        config_path = PROJECT_DIR / config_path
    
    config = load_config(config_path)
    output_dir = build_output_dir(config)
    copy_project_tree(output_dir)
    patch_project_json(output_dir, config)
    patch_mainpage(output_dir, config)
    patch_ido_load(output_dir, config)
    validate_output(output_dir)
    print(f"Prepared deployable project at: {output_dir}")
    print("Open that folder in RPA Studio for tenant-specific deployment/testing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
