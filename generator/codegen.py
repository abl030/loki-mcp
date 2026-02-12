"""Render the Jinja2 template to produce generated/server.py."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def render_server(context: dict, templates_dir: Path, output_path: Path) -> int:
    """Render server.py from template and context.

    Returns the number of tool functions generated.
    """
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template("server.py.j2")
    code = template.render(**context)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(code)

    # Count tool functions
    import re

    return len(re.findall(r"^async def loki_", code, re.MULTILINE))
