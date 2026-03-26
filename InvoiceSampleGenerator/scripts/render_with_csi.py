#!/usr/bin/env python3
"""Render invoices with live CSI lookups enabled.

Sets the required environment variables and delegates to render_invoice_batch.py.
All arguments are passed through.

Usage:
  python scripts/render_with_csi.py --ionapi <path> --request-json <path> --output-folder <path>
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RENDERER = Path(__file__).resolve().parent / "render_invoice_batch.py"


def main() -> int:
    args = list(sys.argv[1:])

    # --ionapi is required; extract it from args
    ionapi_path: str | None = os.environ.get("IONAPI_FILE")
    if "--ionapi" in args:
        idx = args.index("--ionapi")
        ionapi_path = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if not ionapi_path:
        print("ERROR: --ionapi <path> argument or IONAPI_FILE env var is required", file=sys.stderr)
        return 1

    os.environ["CSI_LOOKUP_ENABLED"] = "1"
    os.environ["IONAPI_FILE"] = ionapi_path

    return subprocess.call([sys.executable, str(RENDERER)] + args)


if __name__ == "__main__":
    sys.exit(main())
