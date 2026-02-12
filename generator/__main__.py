"""Entry point: python -m generator"""

from __future__ import annotations

import argparse
from pathlib import Path

from generator.codegen import render_server
from generator.context_builder import build_context
from generator.loader import load_inventory

ROOT = Path(__file__).parent.parent
INVENTORY_PATH = ROOT / "spec" / "endpoint-inventory.json"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_PATH = ROOT / "generated" / "server.py"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Loki MCP server")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print tool list without generating",
    )
    args = parser.parse_args()

    print("Loading endpoint inventory...")
    inventory = load_inventory(INVENTORY_PATH)
    print(f"  Loki version: {inventory.loki_version}")
    print(f"  Endpoints: {len(inventory.endpoints)}")
    print(f"  High-level tools: {len(inventory.high_level_tools)}")
    print(f"  Modules: {', '.join(inventory.modules.keys())}")

    print("\nBuilding template context...")
    ctx = build_context(inventory)
    print(f"  Total tools: {ctx['tool_count']}")

    if args.dry_run:
        print("\n=== Tool List (dry run) ===")
        print("\nDirect API tools:")
        for ep in ctx["endpoints"]:
            mut = " [MUTATION]" if ep["mutation"] else ""
            danger = " [DANGER]" if ep["danger"] else ""
            print(f"  {ep['tool_name']:40s} {ep['module']:10s} {ep['method']:6s} {ep['path']}{mut}{danger}")
        print("\nHigh-level tools:")
        for t in ctx["high_level_tools"]:
            mod = t["module"] or "global"
            print(f"  {t['tool_name']:40s} {mod:10s} {t['description'][:60]}")
        return

    print(f"\nRendering server.py to {OUTPUT_PATH}...")
    tool_count = render_server(ctx, TEMPLATES_DIR, OUTPUT_PATH)
    print(f"  Generated {tool_count} tool functions")
    print("\n=== Generation Complete ===")


if __name__ == "__main__":
    main()
