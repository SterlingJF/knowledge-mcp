from __future__ import annotations

import shutil
import tomllib
from collections.abc import Callable
from importlib import metadata
from pathlib import Path

import pytest

from tests.harness import CODEBASE, MODULE, knowledge_base, write
from tests.kb_cli import (
    EXIT_CODES,
    HELP_PAGES,
    did_you_mean,
    error_lines,
    example_faults,
    last_line,
    next_line,
    run_kb,
    run_kbp,
)
from tests.test_kb_end_to_end import fixture_home, snapshot

REINSTALL = "brew reinstall knowledge-mcp"
RFC = "docs/rfcs/0042-cache.md"

Line = Callable[[Path, Path], list[str]]


def kb_version() -> str:
    try:
        return metadata.version("knowledge-mcp")
    except metadata.PackageNotFoundError:
        return tomllib.loads((MODULE / "pyproject.toml").read_text())["project"][
            "version"
        ]


def page_id(page: tuple[str, ...]) -> str:
    return " ".join(("kb", *page))


def codebase(root: Path) -> tuple[Path, Path]:
    base = knowledge_base(root / "codebase", {"": [CODEBASE]})
    return base, write(base, RFC, "# Cache\n")


def register(home: Path) -> None:
    done = run_kb(home, "setup", "codex")
    assert done.returncode == 0, done.stdout + done.stderr


def outside_state(found: dict[str, object]) -> dict[str, object]:
    """Commands may write logs under .local during failure tests."""
    return {
        name: value
        for name, value in found.items()
        if name != ".local" and not name.startswith(".local/")
    }


def cases(table: list[tuple[str, Line]]) -> dict[str, object]:
    return {
        "argvalues": [line for _, line in table],
        "ids": [name for name, _ in table],
    }


@pytest.mark.parametrize("page", HELP_PAGES, ids=page_id)
def test_dash_h_and_dash_dash_help_print_the_same_help_on_stdout_with_exit_0(
    tmp_path, page
):
    home = fixture_home(tmp_path)
    before = snapshot(tmp_path)

    long = run_kb(home, *page, "--help")
    short = run_kb(home, *page, "-h")

    for done in (long, short):
        assert done.returncode == 0, done.stderr + done.stdout
        assert done.stderr == ""
        [usage] = [
            line
            for line in done.stdout.splitlines()
            if line.lower().startswith("usage:")
        ]
        assert page_id(page) in usage
    assert short.stdout == long.stdout
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("page", [(), ("kbp",)], ids=page_id)
def test_a_bare_command_group_prints_its_help_with_exit_0(tmp_path, page):
    home = fixture_home(tmp_path)
    base, _ = codebase(tmp_path)

    bare = run_kb(home, *page, cwd=base)
    asked = run_kb(home, *page, "--help", cwd=base)

    assert bare.returncode == 0, bare.stderr + bare.stdout
    assert bare.stderr == ""
    assert bare.stdout == asked.stdout


def test_kbp_help_leads_with_examples_and_ends_with_the_exit_codes(tmp_path):
    page = run_kb(tmp_path, "kbp", "--help").stdout

    faults = example_faults(
        page, ["kb kbp validate", "kb kbp card readme"], before="Modes"
    )

    assert faults == [], page
    assert EXIT_CODES.match(last_line(page)), page


SHORTENED_FLAGS: list[tuple[str, Line]] = [
    ("--vers", lambda _base, _rfc: ["--vers"]),
    ("--hel", lambda _base, _rfc: ["--hel"]),
    ("mcp --hel", lambda _base, _rfc: ["mcp", "--hel"]),
    (
        "setup --remov before the harness",
        lambda _base, _rfc: ["setup", "--remov", "codex"],
    ),
    (
        "setup --remov after the harness",
        lambda _base, _rfc: ["setup", "codex", "--remov"],
    ),
    ("setup --rem", lambda _base, _rfc: ["setup", "--rem", "codex"]),
    ("doctor --verbo", lambda _base, _rfc: ["doctor", "--verbo"]),
    ("doctor --verb", lambda _base, _rfc: ["doctor", "--verb"]),
    ("type --rol", lambda _base, rfc: ["type", str(rfc), "--rol", "maintainer"]),
    ("type --roo", lambda base, rfc: ["type", str(rfc), "--roo", str(base)]),
    ("kbp --hel", lambda _base, _rfc: ["kbp", "--hel"]),
    ("kbp kinds --univ", lambda _base, _rfc: ["kbp", "kinds", "--univ", CODEBASE]),
    (
        "kbp card --form",
        lambda _base, _rfc: ["kbp", "card", "readme", "--form", "markdown"],
    ),
    (
        "kbp explore --outp",
        lambda base, _rfc: ["kbp", "explore", "--outp", str(base / "explorer")],
    ),
    (
        "kbp explore --repl",
        lambda base, _rfc: [
            "kbp",
            "explore",
            "--output",
            str(base / "explorer"),
            "--repl",
        ],
    ),
]


@pytest.mark.parametrize("line", **cases(SHORTENED_FLAGS))
def test_a_shortened_long_flag_is_refused_with_exit_2_and_changes_nothing(
    tmp_path, line
):
    home = fixture_home(tmp_path)
    base, rfc = codebase(tmp_path)
    # Register first so accidental removal changes the snapshot.
    register(home)
    before = snapshot(tmp_path)

    done = run_kb(home, *line(base, rfc), cwd=base)

    argv = line(base, rfc)
    if argv[:1] == ["kbp"] and len(argv) > 1 and not argv[1].startswith("-"):
        # kbp parses arguments after the mode, so compare errors with kbp directly.
        direct = run_kbp(home, "--" + argv[1], *argv[2:], cwd=base)
        assert (done.stdout, done.stderr, done.returncode) == (
            direct.stdout,
            direct.stderr,
            direct.returncode,
        )
        assert snapshot(tmp_path) == before
        return
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    assert done.stderr.startswith("Error: "), done.stderr
    assert "--help" in done.stderr.splitlines()[-1], done.stderr
    assert error_lines(done.stderr), done.stderr
    assert snapshot(tmp_path) == before


SHORTENED_COMMANDS: list[tuple[str, Line]] = [
    ("doc", lambda _base, _rfc: ["doc"]),
    ("set codex", lambda _base, _rfc: ["set", "codex"]),
    ("ty", lambda _base, rfc: ["ty", str(rfc)]),
    ("kbp val", lambda _base, _rfc: ["kbp", "val"]),
    ("kbp self", lambda _base, _rfc: ["kbp", "self"]),
]


@pytest.mark.parametrize("line", **cases(SHORTENED_COMMANDS))
def test_a_shortened_command_is_refused_with_exit_2_and_runs_nothing(tmp_path, line):
    home = fixture_home(tmp_path)
    base, rfc = codebase(tmp_path)
    before = snapshot(tmp_path)

    done = run_kb(home, *line(base, rfc), cwd=base)

    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    assert done.stderr.startswith("Error: "), done.stderr
    assert "--help" in done.stderr.splitlines()[-1], done.stderr
    assert error_lines(done.stderr), done.stderr
    assert snapshot(tmp_path) == before


MISSPELLED_COMMANDS = [
    (["setpu"], "setup"),
    (["doctr"], "doctor"),
    (["tpye"], "type"),
    (["kbp", "valdiate"], "validate"),
    (["kbp", "kind"], "kinds"),
    (["kbp", "self-chek"], "self-check"),
]


@pytest.mark.parametrize(
    ("args", "suggestion"),
    MISSPELLED_COMMANDS,
    ids=[" ".join(args) for args, _ in MISSPELLED_COMMANDS],
)
def test_a_misspelled_command_is_refused_with_did_you_mean_and_exit_2(
    tmp_path, args, suggestion
):
    home = fixture_home(tmp_path)
    base, _ = codebase(tmp_path)
    before = snapshot(tmp_path)

    done = run_kb(home, *args, cwd=base)

    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    assert did_you_mean(done.stderr, suggestion), done.stderr
    assert snapshot(tmp_path) == before


MISSPELLED_FLAGS: list[tuple[str, Line, str]] = [
    ("--verison", lambda _base, _rfc: ["--verison"], "--version"),
    ("setup --remvoe", lambda _base, _rfc: ["setup", "--remvoe", "codex"], "--remove"),
    ("doctor --vrebose", lambda _base, _rfc: ["doctor", "--vrebose"], "--verbose"),
    (
        "type --orle",
        lambda _base, rfc: ["type", str(rfc), "--orle", "maintainer"],
        "--role",
    ),
    (
        "type --rooot",
        lambda base, rfc: ["type", str(rfc), "--rooot", str(base)],
        "--root",
    ),
    (
        "kbp kinds --univrese",
        lambda _base, _rfc: ["kbp", "kinds", "--univrese", CODEBASE],
        "--universe",
    ),
    (
        "kbp explore --otput",
        lambda base, _rfc: ["kbp", "explore", "--otput", str(base / "explorer")],
        "--output",
    ),
]


@pytest.mark.parametrize(
    ("line", "suggestion"),
    [case[1:] for case in MISSPELLED_FLAGS],
    ids=[case[0] for case in MISSPELLED_FLAGS],
)
def test_a_misspelled_flag_is_refused_with_did_you_mean_and_exit_2(
    tmp_path, line, suggestion
):
    home = fixture_home(tmp_path)
    base, rfc = codebase(tmp_path)
    register(home)
    before = snapshot(tmp_path)

    done = run_kb(home, *line(base, rfc), cwd=base)

    argv = line(base, rfc)
    if argv[:1] == ["kbp"] and len(argv) > 1 and not argv[1].startswith("-"):
        # kbp parses arguments after the mode, so compare errors with kbp directly.
        direct = run_kbp(home, "--" + argv[1], *argv[2:], cwd=base)
        assert (done.stdout, done.stderr, done.returncode) == (
            direct.stdout,
            direct.stderr,
            direct.returncode,
        )
        assert snapshot(tmp_path) == before
        return
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    assert did_you_mean(done.stderr, suggestion), done.stderr
    assert snapshot(tmp_path) == before


MISSING: list[tuple[str, Line]] = [
    ("setup without a harness", lambda _base, _rfc: ["setup"]),
    ("setup --remove without a harness", lambda _base, _rfc: ["setup", "--remove"]),
    ("type without a path", lambda _base, _rfc: ["type"]),
    (
        "type --role without a path",
        lambda _base, _rfc: ["type", "--role", "maintainer"],
    ),
    ("type --root without its folder", lambda _base, rfc: ["type", str(rfc), "--root"]),
    ("type --role without its value", lambda _base, rfc: ["type", str(rfc), "--role"]),
    ("kbp card without a document type", lambda _base, _rfc: ["kbp", "card"]),
    ("kbp mint without a category", lambda _base, _rfc: ["kbp", "mint"]),
    ("kbp explore without --output", lambda _base, _rfc: ["kbp", "explore"]),
    (
        "kbp kinds --universe without its id",
        lambda _base, _rfc: ["kbp", "kinds", "--universe"],
    ),
]


@pytest.mark.parametrize("line", **cases(MISSING))
def test_a_missing_argument_exits_2_with_an_error_line_on_stderr(tmp_path, line):
    home = fixture_home(tmp_path)
    base, rfc = codebase(tmp_path)
    before = snapshot(tmp_path)

    done = run_kb(home, *line(base, rfc), cwd=base)

    argv = line(base, rfc)
    if argv[:1] == ["kbp"] and len(argv) > 1 and not argv[1].startswith("-"):
        # kbp parses arguments after the mode, so compare errors with kbp directly.
        direct = run_kbp(home, "--" + argv[1], *argv[2:], cwd=base)
        assert (done.stdout, done.stderr, done.returncode) == (
            direct.stdout,
            direct.stderr,
            direct.returncode,
        )
        assert snapshot(tmp_path) == before
        return
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    assert done.stderr.startswith("Error: "), done.stderr
    assert "--help" in done.stderr.splitlines()[-1], done.stderr
    assert error_lines(done.stderr), done.stderr
    assert "Traceback" not in done.stderr
    assert snapshot(tmp_path) == before


OUTSIDE_CHOICES: list[tuple[str, Line]] = [
    ("setup with an unknown harness", lambda _base, _rfc: ["setup", "nosuch"]),
    (
        "setup --remove with an unknown harness",
        lambda _base, _rfc: ["setup", "--remove", "nosuch"],
    ),
    (
        "kbp mint with an unknown category",
        lambda _base, _rfc: ["kbp", "mint", "widget"],
    ),
    (
        "kbp kinds with an unknown format",
        lambda _base, _rfc: ["kbp", "kinds", "--format", "yaml"],
    ),
    (
        "kbp card with an unknown format",
        lambda _base, _rfc: ["kbp", "card", "readme", "--format", "yaml"],
    ),
]


@pytest.mark.parametrize("line", **cases(OUTSIDE_CHOICES))
def test_a_value_outside_the_choices_exits_2_with_an_error_line_on_stderr(
    tmp_path, line
):
    home = fixture_home(tmp_path)
    base, rfc = codebase(tmp_path)
    before = snapshot(tmp_path)

    done = run_kb(home, *line(base, rfc), cwd=base)

    argv = line(base, rfc)
    if argv[:1] == ["kbp"] and len(argv) > 1 and not argv[1].startswith("-"):
        # kbp parses arguments after the mode, so compare errors with kbp directly.
        direct = run_kbp(home, "--" + argv[1], *argv[2:], cwd=base)
        assert (done.stdout, done.stderr, done.returncode) == (
            direct.stdout,
            direct.stderr,
            direct.returncode,
        )
        assert snapshot(tmp_path) == before
        return
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    assert done.stderr.startswith("Error: "), done.stderr
    assert "--help" in done.stderr.splitlines()[-1], done.stderr
    assert error_lines(done.stderr), done.stderr
    assert snapshot(tmp_path) == before


def test_setup_with_invalid_settings_prints_an_error_line_and_a_fix_and_changes_nothing(
    tmp_path,
):
    home = fixture_home(tmp_path)
    write(home, ".codex/config.toml", "[mcp_servers\n")
    before = outside_state(snapshot(home))

    done = run_kb(home, "setup", "codex")

    assert done.returncode == 1, done.stdout + done.stderr
    assert done.stdout == ""
    assert "Traceback" not in done.stderr
    assert len(error_lines(done.stderr)) == 1, done.stderr
    assert next_line(done.stderr), done.stderr
    assert not done.stderr.startswith("kb setup:")
    assert outside_state(snapshot(home)) == before


def test_type_for_a_file_in_a_missing_folder_prints_an_error_line_on_stderr(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    missing = tmp_path / "missing" / "a.md"

    done = run_kb(home, "type", str(missing))

    assert done.returncode != 0
    assert done.stdout == ""
    assert "Traceback" not in done.stderr
    errors = error_lines(done.stderr)
    assert len(errors) == 1, done.stderr
    assert str(missing.parent) in errors[0]
    assert not done.stderr.startswith(("kb fit:", "kb type:"))


def test_an_unexpected_failure_prints_an_error_line_and_a_fix_without_a_traceback(
    tmp_path,
):
    home = tmp_path / "home"
    home.mkdir()
    _, rfc = codebase(tmp_path)
    # A file at the state directory path prevents logging.
    state = write(tmp_path, "state-is-a-file")

    done = run_kb(home, "type", str(rfc), KNOWLEDGE_MCP_STATE_DIR=str(state))

    assert done.returncode == 1, done.stdout + done.stderr
    assert done.stdout == ""
    assert "Traceback" not in done.stderr
    assert len(error_lines(done.stderr)) == 1, done.stderr
    assert next_line(done.stderr), done.stderr


INSTALL_FAULTS: list[tuple[str, Callable[[Path], list[str]]]] = [
    ("doctor", lambda _root: ["doctor"]),
    ("doctor --verbose", lambda _root: ["doctor", "--verbose"]),
    ("setup codex", lambda _root: ["setup", "codex"]),
    (
        "type in a folder without spec files",
        lambda root: ["type", str(write(root, "plain/README.md", "# Plain\n"))],
    ),
]


@pytest.mark.parametrize(
    "line",
    [case[1] for case in INSTALL_FAULTS],
    ids=[case[0] for case in INSTALL_FAULTS],
)
def test_a_missing_bundled_folder_prints_one_error_line_and_the_reinstall_fix(
    tmp_path, line
):
    home = fixture_home(tmp_path)
    command = line(tmp_path)
    missing = tmp_path / "share" / "knowledge-mcp"
    before = outside_state(snapshot(home))

    done = run_kb(home, *command, KNOWLEDGE_MCP_DATA=str(missing))

    output = done.stdout + done.stderr
    assert done.returncode == 1, output
    assert "Traceback" not in output
    errors = error_lines(done.stderr)
    assert len(errors) == 1, output
    assert str(missing) in errors[0]
    assert REINSTALL in done.stderr
    assert outside_state(snapshot(home)) == before


@pytest.mark.parametrize(
    "args", [["doctor"], ["doctor", "--verbose"]], ids=["doctor", "doctor --verbose"]
)
def test_an_unpinned_bundled_copy_prints_one_error_line_and_the_reinstall_fix(
    tmp_path, args
):
    home = fixture_home(tmp_path)
    data = tmp_path / "share" / "knowledge-mcp"
    shutil.copytree(MODULE / "knowledge-bus", data / "knowledge-bus")
    shutil.copytree(MODULE / "skills", data / "skills", symlinks=True)
    upstream = data / "knowledge-bus" / "UPSTREAM.md"
    upstream.write_text(
        "".join(
            line
            for line in upstream.read_text().splitlines(keepends=True)
            if not line.startswith("- Ref: ")
        )
    )

    done = run_kb(home, *args, KNOWLEDGE_MCP_DATA=str(data))

    output = done.stdout + done.stderr
    assert done.returncode == 1, output
    assert "Traceback" not in output
    assert len(error_lines(done.stderr)) == 1, output
    assert REINSTALL in done.stderr
    # Installed copies cannot run repository maintenance recipes.
    assert "refresh_knowledge_model" not in output


def test_version_prints_kb_then_the_knowledge_bus_version_line(tmp_path):
    done = run_kb(tmp_path, "--version")

    assert done.returncode == 0, done.stderr
    assert done.stderr == ""
    assert done.stdout.splitlines() == [
        f"kb {kb_version()}",
        f"knowledge-bus {metadata.version('knowledge-bus')}",
    ]


def test_version_reads_no_bundled_file(tmp_path):
    missing = tmp_path / "share" / "knowledge-mcp"

    done = run_kb(tmp_path, "--version", KNOWLEDGE_MCP_DATA=str(missing))

    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.splitlines()[0] == f"kb {kb_version()}"


@pytest.mark.parametrize("args", [["-v"], ["version"]], ids=["-v", "version"])
def test_version_has_no_short_flag_and_no_command(tmp_path, args):
    done = run_kb(tmp_path, *args)

    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    assert done.stderr.startswith("Error: "), done.stderr
    assert "--help" in done.stderr.splitlines()[-1], done.stderr
    assert error_lines(done.stderr), done.stderr
