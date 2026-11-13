"""@file contract_tester.py
@brief CLI: validate a plugin against the Nexara plugin contract.

Usage: ``python plugins/contract_tester.py PLUGIN_DIR [--test CAT]... [--format json|text]
[--strict]``. Exit codes: 0 ok, 1 failures (or warnings with --strict), 2 warnings only.
Run inside the backend environment (imports ``app.plugins``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent / "backend"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from contract_tests import CATEGORIES  # noqa: E402
from contract_tests.common import Check  # noqa: E402
from contract_tests.reporting import to_dict, to_text  # noqa: E402


def run_checks(plugin_dir: Path, categories: list[str] | None = None) -> list[Check]:
    """@brief Run selected (default all) categories.
    @param plugin_dir Plugin directory.
    @param categories Category names or None.
    @return Check list.
    """
    out: list[Check] = []
    for name in categories or list(CATEGORIES):
        out.extend(CATEGORIES[name](plugin_dir))
    return out


def exit_code(checks: list[Check], strict: bool = False) -> int:
    """@brief 1 on failures (or warnings if strict), 2 on warnings only, else 0."""
    if any(c.status == "fail" for c in checks):
        return 1
    if any(c.status == "warn" for c in checks):
        return 1 if strict else 2
    return 0


def main(argv: list[str] | None = None) -> int:
    """@brief CLI entry point. @return Process exit code."""
    ap = argparse.ArgumentParser(description="Nexara plugin contract tester")
    ap.add_argument("plugin_dir", type=Path)
    ap.add_argument("--test", action="append", choices=list(CATEGORIES), dest="tests")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    if not args.plugin_dir.is_dir():
        print(f"not a directory: {args.plugin_dir}", file=sys.stderr)
        return 1
    checks = run_checks(args.plugin_dir, args.tests)
    if args.format == "json":
        print(json.dumps(to_dict(checks), indent=2))
    else:
        print(to_text(checks, color=sys.stdout.isatty()))
    return exit_code(checks, args.strict)


if __name__ == "__main__":
    sys.exit(main())
