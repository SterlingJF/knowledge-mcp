"""`kb`: knowledge-mcp's one command.

`kb` is the knowledge (base) tooling for day-to-day knowledge work and carries `kbp`,
knowledge-bus's core: the protocol and the core spec contracts.
"""

from __future__ import annotations

import argparse
import os
import sys
from importlib import metadata
from pathlib import Path

from knowledge_mcp.hosts import HOSTS

DESCRIPTION = """\
kb helps you read, write and bring in knowledge with the universe specs that apply to each file.
Start the knowledge-mcp MCP server for agent apps, register knowledge-mcp with an
agent app, or run kbp, knowledge-bus's protocol checker.
"""


def _version() -> str:
    from knowledge_mcp import bundled
    from knowledge_mcp.main import version

    try:
        package = metadata.version("knowledge-bus")
    except metadata.PackageNotFoundError:
        package = "missing"
    return f"kb {version()} (knowledge-bus {package}; universe specs and skills from {bundled.ref()})"


def parser() -> argparse.ArgumentParser:
    main = argparse.ArgumentParser(prog="kb", description=DESCRIPTION)
    main.add_argument(
        "--version", action="store_true", help="print the versions and exit"
    )
    commands = main.add_subparsers(dest="command", metavar="<command>")
    commands.add_parser("mcp", help="run the stdio MCP server for agent apps")
    setup = commands.add_parser(
        "setup",
        help="register knowledge-mcp with an agent app and link the kb-* and km-* skills",
    )
    setup.add_argument("host", choices=list(HOSTS), help="the agent app")
    setup.add_argument(
        "--remove", action="store_true", help="undo changes from `kb setup <host>`"
    )
    fit = commands.add_parser(
        "fit", help="show matching document types for a local file"
    )
    fit.add_argument("file", type=Path, help="path to an existing or planned file")
    fit.add_argument(
        "--hat", help="the role of the person the file is for, such as maintainer"
    )
    fit.add_argument(
        "--top",
        type=Path,
        help="knowledge base's top folder; defaults to the highest ancestor with .knowledge-bus/, then the nearest .git root, then the parent of the file's folder",
    )
    commands.add_parser("kbp", help="run kbp with the following arguments unchanged")
    commands.add_parser(
        "doctor",
        help="check knowledge-bus, bundled universe specs and skills, and agent app setup",
    )
    return main


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["kbp"]:
        from knowledge_mcp import kbp

        executable = str(kbp.executable())
        os.execv(executable, [executable, *argv[1:]])
    arguments = parser().parse_args(argv)
    if arguments.version:
        print(_version())
        return
    if arguments.command == "mcp":
        from knowledge_mcp.main import main as serve

        serve()
        return
    if arguments.command == "fit":
        from knowledge_mcp import localfit

        try:
            text, refused = localfit.fit(
                arguments.file, top=arguments.top, hat=arguments.hat
            )
        except ValueError as error:
            sys.exit(f"kb fit: {error}")
        print(text)
        sys.exit(1 if refused else 0)
    if arguments.command == "setup":
        from knowledge_mcp import configedit
        from knowledge_mcp import setup as setups

        try:
            if arguments.remove:
                report = setups.remove(arguments.host)
            else:
                report = setups.setup(arguments.host)
        except (setups.SetupError, configedit.ConfigError, OSError) as error:
            sys.exit(f"kb setup: {error}")
        print(report.text())
        sys.exit(1 if report.problems else 0)
    if arguments.command == "doctor":
        from knowledge_mcp import setup as setups

        report = setups.doctor()
        print(report.text())
        sys.exit(1 if report.problems else 0)
    parser().print_help()


if __name__ == "__main__":
    main()
