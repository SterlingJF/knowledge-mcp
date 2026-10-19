from __future__ import annotations

import contextlib
import difflib
import json
import os
import re
import shlex
import sys
import traceback
from collections.abc import Sequence
from importlib import metadata
from pathlib import Path
from types import ModuleType
from typing import Any, NoReturn, cast

import click

from knowledge_mcp import kbp, log, version
from knowledge_mcp.document_type import ROLE
from knowledge_mcp.errors import REPORT, InstallFault, KbError, ToolFault, UsageFault
from knowledge_mcp.harnesses import HARNESSES

EXIT_CODES = "Exit codes: 0 done, 1 failed, 2 wrong command line."
KBP_EXIT_CODES = "Exit codes: 0 done, 1 kbp found a problem or failed, 2 kb rejected the command line."
HELP_FLAG = "Show this help and exit"

Example = tuple[str, tuple[str, ...]]

# Names retired after kb 0.2.1.
RETIRED_COMMANDS = {"fit": "type"}
RETIRED_FLAGS = {"--hat": "--role", "--top": "--root"}


def _usage_pieces(command: click.Command, ctx: click.Context) -> list[str]:
    """Place subcommands and positional arguments before flags in usage lines."""
    pieces = [
        piece
        for param in command.get_params(ctx)
        if isinstance(param, click.Argument)
        for piece in param.get_usage_pieces(ctx)
    ]
    if isinstance(command, click.Group):
        pieces.insert(0, command.subcommand_metavar)
    if command.options_metavar:
        pieces.append(command.options_metavar)
    return pieces


def _write_help(
    command: click.Command,
    ctx: click.Context,
    formatter: click.HelpFormatter,
    examples: Sequence[Example],
) -> None:
    """Write usage, the description, examples, arguments, commands, flags, then the exit-code line."""
    command.format_usage(ctx, formatter)
    command.format_help_text(ctx, formatter)
    if examples:
        with formatter.section("Examples"):
            for index, (comment, lines) in enumerate(examples):
                if index:
                    formatter.write("\n")
                for line in (f"# {comment}", *lines):
                    formatter.write(f"{'':>{formatter.current_indent}}{line}\n")
    params = command.get_params(ctx)
    arguments = [
        record
        for param in params
        if isinstance(param, click.Argument)
        and (record := param.get_help_record(ctx)) is not None
    ]
    if arguments:
        with formatter.section("Arguments"):
            formatter.write_dl(arguments)
    if isinstance(command, click.Group):
        command.format_commands(ctx, formatter)
    flags = [
        record
        for param in params
        if not isinstance(param, click.Argument)
        and (record := param.get_help_record(ctx)) is not None
    ]
    if flags:
        with formatter.section("Flags"):
            formatter.write_dl(flags)
    if command.epilog:
        formatter.write_paragraph()
        formatter.write(f"{command.epilog}\n")


class SuggestedChoice(click.Choice[str]):
    """Add "Did you mean <choice>?" to Click's error when a wrong value is close to a choice."""

    def convert(
        self, value: Any, param: click.Parameter | None, ctx: click.Context | None
    ) -> str:
        try:
            return super().convert(value, param, ctx)
        except click.BadParameter as error:
            close = difflib.get_close_matches(str(value), self.choices, n=1)
            if not close:
                raise
            message = f"{error.message} Did you mean {close[0]}?"
            raise click.BadParameter(message, ctx=ctx, param=param) from None


class Command(click.Command):
    """Use kb's help layout, print `examples` and suggest the new name for a retired flag."""

    def __init__(
        self, *args: Any, examples: Sequence[Example] = (), **kwargs: Any
    ) -> None:
        kwargs.setdefault("options_metavar", "[flags]")
        kwargs.setdefault("epilog", EXIT_CODES)
        super().__init__(*args, **kwargs)
        self.examples = tuple(examples)

    def get_help_option(self, ctx: click.Context) -> click.Option | None:
        option = super().get_help_option(ctx)
        if option is not None:
            option.help = HELP_FLAG
        return option

    def collect_usage_pieces(self, ctx: click.Context) -> list[str]:
        return _usage_pieces(self, ctx)

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        _write_help(self, ctx, formatter, self.examples)

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        try:
            return super().parse_args(ctx, args)
        except click.NoSuchOption as error:
            new = RETIRED_FLAGS.get(error.option_name)
            flags = {name for param in self.params for name in param.opts}
            if new is None or new not in flags:
                raise
            message = f"No such option {error.option_name!r}. Did you mean {new!r}?"
            raise click.NoSuchOption(error.option_name, message, ctx=ctx) from None


class Group(click.Group):
    """Use the help layout of `Command` and suggest the new name for a retired command."""

    command_class = Command
    group_class = type

    def __init__(
        self, *args: Any, examples: Sequence[Example] = (), **kwargs: Any
    ) -> None:
        kwargs.setdefault("options_metavar", "[flags]")
        kwargs.setdefault("epilog", EXIT_CODES)
        super().__init__(*args, **kwargs)
        self.examples = tuple(examples)

    def get_help_option(self, ctx: click.Context) -> click.Option | None:
        option = super().get_help_option(ctx)
        if option is not None:
            option.help = HELP_FLAG
        return option

    def collect_usage_pieces(self, ctx: click.Context) -> list[str]:
        return _usage_pieces(self, ctx)

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        _write_help(self, ctx, formatter, self.examples)

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        try:
            return super().resolve_command(ctx, args)
        except click.NoSuchCommand as error:
            new = RETIRED_COMMANDS.get(error.command_name)
            if new is None or new not in self.commands:
                raise
            message = f"No such command {error.command_name!r}. Did you mean {new!r}?"
            raise click.NoSuchCommand(error.command_name, message, ctx=ctx) from None


class KbpMode(Command):
    """Parse only a lone --help or -h. Pass every other argument to kbp unparsed."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if args in (["--help"], ["-h"]):
            return super().parse_args(ctx, args)
        ctx.args = args
        return args

    def collect_usage_pieces(self, _ctx: click.Context) -> list[str]:
        return ["[<args>]..."]


class KbpGroup(Group):
    """Load the modes from the installed kbp only when kb kbp runs, so kb --help works without kbp."""

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: click.Context | None = None,
        **extra: Any,
    ) -> click.Context:
        try:
            upstream = kbp.cli()
        except kbp.KbpMissing as error:
            raise InstallFault(str(error)) from error
        self.commands = {
            flag[2:]: _mode_command(flag, upstream)
            for flag in cast("tuple[str, ...]", upstream.MODES)
        }
        return super().make_context(info_name, args, parent, **extra)

    def list_commands(self, _ctx: click.Context) -> list[str]:
        return list(self.commands)

    def format_commands(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        rows = [
            (name, self.commands[name].get_short_help_str(formatter.width))
            for name in self.list_commands(ctx)
        ]
        with formatter.section("Modes"):
            formatter.write_dl(rows)

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        try:
            return super().parse_args(ctx, args)
        except click.NoSuchOption as error:
            modes = difflib.get_close_matches(
                error.option_name.lstrip("-"), self.commands, n=1
            )
            if error.possibilities or not modes:
                raise
            message = f"{error.message} Did you mean kb kbp {modes[0]}?"
            raise click.NoSuchOption(error.option_name, message, ctx=ctx) from None

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        try:
            return super().resolve_command(ctx, args)
        except click.NoSuchCommand as error:
            name = error.command_name
            message = error.message.replace("No such command", "No such mode")
            if error.possibilities or not (
                "/" in name
                or name.startswith(".")
                or Path(name).suffix
                or Path(name).exists()
            ):
                raise click.NoSuchCommand(
                    name, message, possibilities=error.possibilities, ctx=ctx
                ) from None
            message += f" Did you mean kb kbp validate {name}?"
            raise click.NoSuchCommand(name, message, ctx=ctx) from None


def _show(error: KbError) -> None:
    click.echo(f"Error: {error.message.rstrip(chr(46))}.", err=True)
    click.echo(error.fix or REPORT, err=True)


def _json(value: Any) -> None:
    click.echo(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2 if sys.stdout.isatty() else None,
            separators=None if sys.stdout.isatty() else (",", ":"),
        )
    )


def _problem(message: str, code: str = "internal-error") -> None:
    from knowledge_mcp.problems import Error

    click.echo(
        json.dumps(Error(message, code=code).details(), ensure_ascii=False), err=True
    )


def _usage_error(error: click.ClickException) -> None:
    ctx = getattr(error, "ctx", None)
    command = ctx.command_path if ctx else "kb"
    raw = error.format_message()
    suggestions = re.findall(r"Did you mean[^\n]*", raw)
    message = " ".join(re.split(r"Did you mean", raw)[0].split())
    if isinstance(error, click.NoSuchOption):
        message = f"unknown flag {error.option_name} for {command}"
        if not suggestions and error.possibilities:
            suggestions = [f"Did you mean {error.possibilities[0]}?"]
    elif isinstance(error, click.NoSuchCommand):
        noun = "mode" if command == "kb kbp" else "command"
        message = f"unknown {noun} {error.command_name} for {command}"
        if not suggestions and error.possibilities:
            suggestions = [f"Did you mean {error.possibilities[0]}?"]
    if command == "kb mcp" and message.startswith("Got unexpected extra argument ("):
        extra = (
            message.removeprefix("Got unexpected extra argument (")
            .rstrip(".")
            .removesuffix(")")
        )
        message = f'kb mcp takes no arguments, but got "{extra}"'
    if command == "kb":
        help_noun = "commands"
    elif command == "kb kbp" and isinstance(error, click.NoSuchCommand):
        help_noun = "modes"
    else:
        help_noun = "flags"
    click.echo(f"Error: {message.rstrip(chr(46))}.", err=True)
    for suggestion in suggestions:
        click.echo(suggestion.replace("'", ""), err=True)
    click.echo(f"Run {command} --help for the {help_noun}.", err=True)


def _proposal_columns(answer: dict[str, Any], rows: list[list[str]]) -> None:
    proposals = {
        (a["universe_spec"], a["document_type"]): a["proposal"]
        for a in answer.get("filing", [])
    }
    for row in rows:
        proposal = proposals.get((row[1], row[0]))
        row[4:4] = (
            [proposal["folder"], proposal["name"]] if proposal else ["<none>", "<none>"]
        )


def _recorded_type_rows(
    answer: dict[str, Any], catalog: dict[tuple[str, str], dict[str, Any]]
) -> list[list[str]]:
    rows: list[list[str]] = []
    recorded = answer.get("recorded")
    if recorded and not recorded["entry"].get("no_document_type"):
        item = recorded["entry"]
        rows.append(
            [
                item["document_type"],
                item["universe_spec"],
                "record",
                catalog.get((item["universe_spec"], item["document_type"]), {}).get(
                    "actor"
                )
                or "<unset>",
                catalog.get((item["universe_spec"], item["document_type"]), {}).get(
                    "name"
                )
                or item["document_type"],
            ]
        )
    if recorded and recorded["entry"].get("no_document_type"):
        rows.append(["<none>", "<none>", "record", "<unset>", "No document type"])
    return rows


def _type_table(
    answer: dict[str, Any],
    catalog: dict[tuple[str, str], dict[str, Any]],
) -> None:
    rows = []
    for item in answer["candidates"]:
        rows.append(
            [
                item["document_type"],
                item["universe_spec"],
                item["matched_on"],
                item["actor"] or "<unset>",
                item["name"],
            ]
        )
    if answer["every_document_type"] is not None:
        seen = {(row[0], row[1]) for row in rows}
        for group in answer["every_document_type"]:
            for item in group["kinds"]:
                if (item["document_type"], group["universe_spec"]) not in seen:
                    rows.append(
                        [
                            item["document_type"],
                            group["universe_spec"],
                            "<none>",
                            item["actor"] or "<unset>",
                            catalog[(group["universe_spec"], item["document_type"])][
                                "name"
                            ],
                        ]
                    )
    rows.extend(_recorded_type_rows(answer, catalog))
    _proposal_columns(answer, rows)
    if sys.stdout.isatty():
        headers = [
            "TYPE",
            "SPEC",
            "MATCHED-BY",
            "USED-BY",
            "PROPOSED-FOLDER",
            "PROPOSED-NAME",
            "TITLE",
        ]
        widths = [
            max(len(row[index]) for row in [headers, *rows])
            for index in range(len(headers) - 1)
        ]
        for row in [headers, *rows]:
            click.echo(
                "  ".join(
                    [
                        *(
                            value.ljust(width)
                            for value, width in zip(row[:-1], widths, strict=True)
                        ),
                        row[-1],
                    ]
                )
            )
    else:
        for row in rows:
            click.echo(
                "\t".join(value.replace("\t", " ").replace("\n", " ") for value in row)
            )


def _state_warning() -> None:
    value = os.environ.get(log.VARIABLE, "")
    if value and not os.path.isabs(os.path.expanduser(value)):
        click.echo(
            f"Warning: {log.VARIABLE}={value} is not an absolute path, so kb uses {log.directory()}.",
            err=True,
        )


def _print_version(ctx: click.Context, _param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    try:
        bus = metadata.version("knowledge-bus")
    except metadata.PackageNotFoundError:
        bus = "missing"
    click.echo(f"kb {version()}")
    click.echo(f"knowledge-bus {bus}")
    ctx.exit()


@click.group(
    cls=Group,
    invoke_without_command=True,
    subcommand_metavar="<command>",
    context_settings={"help_option_names": ["-h", "--help"]},
    help=(
        "Register knowledge-mcp with a harness, show the document type of a file and "
        "validate .kbp.yaml files with kbp."
    ),
    examples=[
        (
            "Register knowledge-mcp with Claude Code, then check the install",
            ("kb setup claude-code", "kb doctor"),
        ),
        (
            "Validate the .kbp.yaml files in the nearest .knowledge-bus/ folder",
            ("kb kbp validate",),
        ),
    ],
    epilog="Exit codes: 0 done, 1 failed or found a problem, 2 wrong command line.",
)
@click.option(
    "--version",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_print_version,
    help="Show the kb and knowledge-bus versions and exit",
)
@click.pass_context
def kb(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@kb.command(
    short_help="Run the MCP server on stdin and stdout",
    help=(
        "Run the knowledge-mcp MCP server on stdin and stdout. After kb setup <harness>, "
        "the harness starts kb mcp itself."
    ),
    examples=[("Run the MCP server for a harness", ("kb mcp",))],
)
def mcp() -> None:
    from knowledge_mcp.main import main as serve

    if sys.stdin.isatty():
        click.echo(
            "kb mcp serves MCP on stdin and stdout for a harness. To connect a harness, run kb setup <harness>. Ctrl-C stops the server.",
            err=True,
        )
    with contextlib.suppress(KeyboardInterrupt):
        serve()


@kb.command(
    short_help="Register knowledge-mcp with a harness",
    help=(
        "Register knowledge-mcp with a harness. kb adds kb mcp to the harness MCP settings. "
        "It links the bundled skills into the harness skills folder. For claude-desktop, kb "
        "prints the steps to upload the skills instead.\n\nkb backs up existing settings "
        "files in setup/backups under the state folder before editing those files directly."
    ),
    examples=[
        ("Register knowledge-mcp with Codex", ("kb setup codex",)),
        ("Unregister knowledge-mcp from Codex", ("kb setup --remove codex",)),
    ],
)
@click.argument(
    "harness",
    type=SuggestedChoice(list(HARNESSES)),
    metavar="<harness>",
    help=", ".join(list(HARNESSES)[:-1]) + f" or {list(HARNESSES)[-1]}",
)
@click.option(
    "--remove",
    is_flag=True,
    help=(
        "Remove the knowledge-mcp MCP settings entry, and the skill links and settings "
        "backups kb made"
    ),
)
def setup(harness: str, remove: bool) -> None:
    from knowledge_mcp import setup as setups

    command = f"kb setup --remove {harness}" if remove else f"kb setup {harness}"
    fix = f"Fix the file or folder in the error, then run {command} again."
    try:
        report = setups.remove(harness) if remove else setups.setup(harness)
    except setups.SetupError as error:
        if error.fix is None:
            error.fix = fix
        raise
    except OSError as error:
        raise KbError(f"{error}.", fix) from error
    for problem in report.problems:
        _show(problem)
    if report.text():
        click.echo(report.text(), err=True)
    for warning in report.warnings:
        click.echo(f"Warning: {warning}", err=True)
    if report.problems:
        click.get_current_context().exit(1)


@kb.command(
    "type",
    short_help="Show the document type of a file",
    help=(
        "Show the document type of a file. kb reads the .kbp.yaml files in each "
        ".knowledge-bus/ folder across the knowledge-base root, including peer folders. "
        "kb uses an applicable entry from the document-types file. "
        "Otherwise, kb prints ranked candidates. When those folders contain neither "
        ".kbp.yaml files nor workspace.yaml, kb uses the bundled .kbp.yaml files. "
        "kb never opens the file, so the file can be missing. "
        "Its folder must exist. Each lookup adds a line to log.jsonl "
        "in the state folder."
        "\n\nProposed folders and names follow saved conventions or files of the same document type. "
        "Both proposal columns show <none> when no proposal applies."
        "\n\nColumns: TYPE SPEC MATCHED-BY USED-BY PROPOSED-FOLDER PROPOSED-NAME TITLE."
    ),
    examples=[
        (
            "Show the document type of an RFC written for maintainers",
            ("kb type docs/rfcs/0042-cache.md --role maintainer",),
        ),
        (
            "Supply a project property and document title for a saved convention",
            (
                "kb type inbox/cache.md --filing-values "
                "'[" + '{"path":"inbox/cache.md",'
                '"universe_spec":"product-development",'
                '"document_type":"decision-record",'
                '"properties":{"project":"Atlas"},'
                '"content":"Use a shared cache"}' + "]'",
            ),
        ),
    ],
)
@click.argument(
    "path",
    type=click.Path(path_type=Path),
    metavar="<path>",
    help="The file, written or not, in a folder that exists",
)
@click.option("--role", metavar="<role>", help=ROLE)
@click.option(
    "--root",
    type=click.Path(path_type=Path),
    metavar="<folder>",
    help=(
        "Stop the search at this folder. By default, search upward from the file's "
        "folder through .knowledge-bus/ folders. Stop where workspace.yaml omits or "
        "disables from_parent, or at the highest .knowledge-bus/ folder. "
        "The from_parent setting selects universe spec files from parent folders. "
        "With no .knowledge-bus/ folder, use the nearest folder holding .git. "
        "With neither marker, use the parent of the file's folder"
    ),
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Print the kb_get_document_type answer as JSON",
)
@click.option(
    "--filing-values",
    metavar="<json>",
    help="Supply naming properties and content values as a JSON array",
)
def type_(
    path: Path,
    role: str | None,
    root: Path | None,
    as_json: bool,
    filing_values: str | None,
) -> None:
    from knowledge_mcp import local_type

    supplied = None
    if filing_values is not None:
        try:
            supplied = json.loads(filing_values)
        except ValueError:
            message = "Pass --filing-values a JSON array of naming values."
            raise UsageFault(
                message,
                "Correct the JSON array, then resend --filing-values. "
                "Run kb type --help for a complete example.",
            ) from None
        if not isinstance(supplied, list) or any(
            not isinstance(v, dict) for v in supplied
        ):
            message = "Pass --filing-values a JSON array of naming values."
            raise UsageFault(
                message,
                "Correct the JSON array, then resend --filing-values. "
                "Run kb type --help for a complete example.",
            )
    try:
        text, failed = local_type.document_type(
            path, root=root, role=role, filing_values=supplied
        )
    except ValueError as error:
        raise KbError(str(error)) from error
    answer = json.loads(text)
    if failed:
        command = shlex.join(
            [
                "kb",
                "type",
                str(path),
                *(["--root", str(root)] if root else []),
                *(["--role", role] if role else []),
            ]
        )
        fix = (
            REPORT
            if answer["type"].endswith("internal-error")
            else f"Correct the reported file or value, then run {command} again."
        )
        fix = (
            "Correct the naming values and repeat the original command with "
            "--filing-values and the same flags. Run kb type --help for an example."
            if answer["type"].endswith("filing-values-invalid")
            else fix
        )
        raise ToolFault(answer, fix)
    if answer["every_document_type"] is not None:
        click.echo(
            f"No document type matches the file name {path.name}, so kb lists every document type.",
            err=True,
        )
    if as_json:
        _json(answer)
    else:
        for assessment in answer.get("filing", []):
            if assessment["status"] == "values_needed":
                names = [v["name"] for v in assessment["needed"]]
                needed = (
                    names[0]
                    if len(names) == 1
                    else ", ".join(names[:-1]) + " and " + names[-1]
                )
                click.echo(
                    f"Naming needs {needed}. Supply the values with --filing-values.",
                    err=True,
                )
        _type_table(
            answer,
            local_type.type_catalog(path, root, role)
            if answer["every_document_type"] is not None or answer.get("recorded")
            else {},
        )


@kb.command(
    short_help="Check the install and each registration",
    help=(
        "Check the kb install and the knowledge-mcp registration with each harness. kb "
        "doctor reads each harness's settings and changes no file."
    ),
    examples=[
        ("Check the install and each registration", ("kb doctor",)),
        ("Print versions and paths for a bug report", ("kb doctor --verbose",)),
    ],
    epilog="Exit codes: 0 no problem found, 1 found a problem, 2 wrong command line.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help=(
        "Also print paths, registration details, bundled skill names and bundled "
        "universe spec names"
    ),
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as JSON")
def doctor(verbose: bool, as_json: bool) -> None:
    from knowledge_mcp import setup as setups

    report = setups.doctor()
    if as_json:
        _json(report.as_json())
    else:
        click.echo(report.text(verbose=verbose))
    for warning, fix in zip(report.warnings, report.warning_fixes, strict=True):
        click.echo(f"Warning: {warning}", err=True)
        click.echo(fix, err=True)
    for problem in report.problems:
        _show(problem)
    if report.problems:
        if as_json:
            _problem(
                " ".join(
                    problem.message + " " + (problem.fix or "")
                    for problem in report.problems
                )
            )
        click.get_current_context().exit(1)


def _run_kbp(argv: list[str]) -> NoReturn:
    try:
        code = kbp.call(argv)
    except kbp.KbpMissing as error:
        raise InstallFault(str(error)) from error
    # For a kbp crash, kb prints the traceback so the bug report shows the failing kbp code.
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        code = 1
    click.get_current_context().exit(code)


def _kbp_version(ctx: click.Context, _param: click.Parameter, value: bool) -> None:
    if value and not ctx.resilient_parsing:
        _run_kbp(["--version"])


@kb.group(
    "kbp",
    cls=KbpGroup,
    invoke_without_command=True,
    subcommand_metavar="<mode> [<args>]...",
    short_help="Validate and inspect .kbp.yaml files with kbp",
    help=(
        "Run a mode of kbp, the knowledge-bus validator for universe spec files. With no "
        "path, modes other than self-check read the nearest .knowledge-bus/ folder at "
        "or above the working folder. self-check reads the bundled protocol unless "
        "you pass a protocol file."
    ),
    examples=[
        (
            "Validate the universe spec files in the nearest .knowledge-bus/ folder",
            ("kb kbp validate",),
        ),
        (
            "Print the card for the readme document type, as JSON, then as Markdown",
            ("kb kbp card readme", "kb kbp card readme --format markdown"),
        ),
    ],
    epilog=KBP_EXIT_CODES,
)
@click.option(
    "--version",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_kbp_version,
    help="Show the knowledge-bus version and the bundled protocol version and exit",
)
@click.pass_context
def kbp_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


MODE_HELP = {
    "validate": "Validate universe spec files against the knowledge-bus protocol",
    "self-check": "Validate the bundled knowledge-bus protocol or a given protocol file",
    "mint": "Print unused codes for new entries in the universe specs that apply",
    "inspect": "Print the JSON model of a universe spec and its guidance",
    "explore": "Write an offline HTML viewer for a universe spec into the --output folder",
    "card": "Print the card for one document type",
    "kinds": "List the document types in the universe specs that apply",
}


def _mode_command(flag: str, upstream: ModuleType) -> click.Command:
    name = flag[2:]
    summary = MODE_HELP.get(name, f"Run the kbp {flag} mode")
    pointer = (
        f"kb handles a lone --help or -h after kb kbp {name}. "
        f"kb passes other flags and arguments to kbp {flag}."
    )
    if name == "mint":
        pointer += " Code kinds: " + ", ".join(upstream.CODED) + "."
    if name in {"card", "kinds"}:
        pointer += " Output formats for --format: " + ", ".join(upstream.FORMATS) + "."

    @click.pass_context
    def invoke(ctx: click.Context) -> NoReturn:
        _run_kbp([flag, *ctx.args])

    return KbpMode(
        name=name,
        callback=invoke,
        short_help=summary,
        help=f"{summary}. {pointer}",
        epilog=KBP_EXIT_CODES,
        context_settings={"help_option_names": ["-h", "--help"]},
    )


def run(argv: Sequence[str]) -> int:
    """Report ClickException, KbError and unexpected exceptions on stderr, with repair steps.

    Add JSON problem details when --json is present.
    """
    _state_warning()
    try:
        result = kb.main(args=list(argv), prog_name="kb", standalone_mode=False)
    except click.ClickException as error:
        _usage_error(error)
        if "--json" in argv:
            _problem(error.format_message(), "argument-invalid")
        return error.exit_code
    except click.Abort:
        click.echo("Aborted!", err=True)
        return 1
    except KbError as error:
        _show(error)
        if "--json" in argv and isinstance(error, ToolFault):
            click.echo(json.dumps(error.problem, ensure_ascii=False), err=True)
        elif "--json" in argv:
            _problem(
                error.message + " " + (error.fix or ""),
                "argument-invalid"
                if isinstance(error, UsageFault)
                else "internal-error",
            )
        return error.exit_code
    except Exception as error:  # noqa: BLE001
        _show(KbError(f"kb failed: {error}.", REPORT))
        if "--json" in argv:
            _problem(f"kb failed: {error}. {REPORT}")
        return 1
    return result if isinstance(result, int) else 0


def main(argv: Sequence[str] | None = None) -> NoReturn:
    sys.exit(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    main()
