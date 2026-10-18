"""`kb setup`, `kb setup --remove` and `kb doctor`, with the setup state file."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, Literal

from knowledge_mcp import bundled, configedit, kbp, log, version
from knowledge_mcp.errors import REINSTALL, KbError
from knowledge_mcp.harnesses import (
    HARNESSES,
    NAME,
    Env,
    Harness,
    server_command,
)

STATE_VERSION = 1


class SetupError(KbError):
    pass


class CommandFailed(SetupError):
    def __init__(self, cli: str, args: list[str], output: str) -> None:
        super().__init__(f"{Path(cli).name} {' '.join(args)} failed: {output.strip()}")


class UnknownHarness(SetupError):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Unknown harness {name!r}. Choose {', '.join(list(HARNESSES)[:-1])} "
            f"or {list(HARNESSES)[-1]}."
        )


class UnsupportedDesktop(SetupError):
    def __init__(self) -> None:
        super().__init__(
            "The Claude desktop app settings folder is missing on this system.",
            "Run kb setup claude-desktop on macOS.",
        )


class ConflictingRegistration(SetupError):
    def __init__(self, path: Path, command: list[str], harness: str) -> None:
        super().__init__(
            f"{path} already has a {NAME} entry that runs {shlex.join(command)}.",
            f"Remove that entry, then run kb setup {harness} again.",
        )


@dataclass
class Report:
    lines: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    problems: list[KbError] = field(default_factory=list)
    sections: dict[str, list[tuple[str, str | list[str]]]] = field(default_factory=dict)
    steps: list[str] = field(default_factory=list)

    def detail(self, section: str, label: str, value: str | list[str]) -> None:
        self.sections.setdefault(section, []).append((label, value))

    def say(self, line: str) -> None:
        self.lines.append(line)

    def warn(self, line: str) -> None:
        self.warnings.append(line)

    def problem(self, message: str, fix: str | None = None) -> None:
        self.problems.append(KbError(message, fix))

    def text(self) -> str:
        return "\n".join([*self.lines, *self.steps])

    def details(self) -> str:
        blocks = []
        for title, facts in self.sections.items():
            if not facts:
                continue
            lines = [title]
            for label, value in facts:
                if isinstance(value, list):
                    lines.append(f"  {label}:")
                    lines.extend(f"    {item}" for item in value)
                else:
                    lines.append(f"  {label}: {value}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)


def state_folder(env: Env) -> Path:
    return log.directory(env.environ, env.home)


def state_lines(env: Env) -> list[str]:
    named = env.environ.get(log.VARIABLE, "") or "<unset>"
    return [f"{log.VARIABLE}: {named}", f"State directory: {state_folder(env)}"]


def setup_folder(env: Env) -> Path:
    return state_folder(env) / "setup"


def _state_path(env: Env) -> Path:
    return setup_folder(env) / "state.json"


def load_state(env: Env) -> dict[str, Any]:
    path = _state_path(env)
    if not path.is_file():
        return {"version": STATE_VERSION, "hosts": {}, "created": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(data)
    return data


def _save_state(env: Env, state: dict[str, Any]) -> None:
    folder = setup_folder(env)
    state["created"] = sorted(set(state["created"]) | set(_make_folder(folder)))
    _write(
        _state_path(env),
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        mode=0o600,
    )


def _make_folder(folder: Path) -> list[str]:
    """Create `folder` and any missing parents. Return the created folders, outermost first."""
    missing = []
    for candidate in (folder, *folder.parents):
        if candidate.exists():
            break
        missing.append(candidate)
    folder.mkdir(parents=True, exist_ok=True)
    return [str(path) for path in reversed(missing)]


def _write(path: Path, text: str, mode: int | None = None) -> None:
    """Replace the file atomically. Keep its permissions unless `mode` is given."""
    if mode is None:
        mode = path.stat().st_mode & 0o7777 if path.exists() else 0o644
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _prune(folders: list[str]) -> list[str]:
    """Remove empty folders, innermost first. Return the folders left in place."""
    kept = []
    for folder in sorted(folders, key=lambda name: name.count(os.sep), reverse=True):
        try:
            Path(folder).rmdir()
        except FileNotFoundError:
            continue
        except OSError:
            kept.append(folder)
    return sorted(kept)


def command_of(entry: Any) -> list[str] | None:
    """Read `command` as a list (OpenCode) or as a string followed by `args`."""
    if not isinstance(entry, dict):
        return None
    command = entry.get("command")
    if isinstance(command, list):
        return [str(part) for part in command]
    if isinstance(command, str):
        return [command, *[str(arg) for arg in entry.get("args", [])]]
    return None


def _edit_add(
    harness: Harness, env: Env, command: list[str], record: dict[str, Any]
) -> None:
    path = harness.config(env)
    created = not path.exists()
    text = "" if created else path.read_text(encoding="utf-8")
    entry = harness.entry(command)
    if harness.format == "toml":
        new, piece = configedit.toml_insert(text, harness.path[0], NAME, entry)
    else:
        new, piece = configedit.json_insert(text, harness.path, NAME, entry)
    if created:
        record["created"] += _make_folder(path.parent)
    else:
        backups = setup_folder(env) / "backups"
        record["created"] += _make_folder(backups)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup = backups / f"{harness.id}-{stamp}-{path.name}"
        shutil.copy2(path, backup)
        record["backups"].append(str(backup))
    _write(path, new, mode=None if not created else 0o600)
    record.update(method="file", config=str(path), piece=piece, created_file=created)


def _edit_remove(harness: Harness, _env: Env, record: dict[str, Any]) -> None:
    path = Path(record["config"])
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    if harness.format == "toml":
        new = configedit.toml_remove(text, harness.path[0], NAME, record.get("piece"))
    else:
        new = configedit.json_remove(text, harness.path, NAME, record.get("piece"))
    empty = not new.strip() or (
        harness.format == "json" and configedit.empty_chain(new, harness.path)
    )
    if record.get("created_file") and empty:
        path.unlink()
    elif new != text:
        _write(path, new)


def _run(cli: str, args: list[str], env: Env) -> None:
    done = subprocess.run(
        [cli, *args], env=env.environ, capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        raise CommandFailed(cli, args, done.stderr or done.stdout)


def _cli(harness: Harness, env: Env) -> str | None:
    if harness.cli is None:
        return None
    return shutil.which(harness.cli, path=env.environ.get("PATH", ""))


def _ours(link: Path) -> bool:
    """True when `link` is a symlink to the bundled skill with the same name in this install."""
    return link.is_symlink() and Path(os.readlink(link)) == bundled.SKILLS / link.name


def _links_to_same_name(link: Path) -> bool:
    """Return True when `link` is a symlink whose stored target has the same basename."""
    return link.is_symlink() and Path(os.readlink(link)).name == link.name


def _skill_duplicates(
    harness: Harness, env: Env, linked_into: Path | None
) -> list[str]:
    names = sorted(skill.name for skill in bundled.skills())
    found = []
    for folder in harness.reads(env):
        if folder == linked_into or not folder.is_dir():
            continue
        ours: list[str] = []
        other: list[str] = []
        for name in names:
            path = folder / name
            if path.exists() or path.is_symlink():
                (ours if _ours(path) else other).append(name)
        if ours:
            found.append(
                f"{harness.title} also reads {folder}, where kb setup linked {', '.join(ours)}. "
                f"{harness.title} may list each of these skills twice."
            )
        if other:
            found.append(
                f"{harness.title} also reads {folder}, which already holds skills named "
                f"{', '.join(other)}. Remove one copy of each skill."
            )
    return found


def _link_skills(
    harness: Harness, env: Env, record: dict[str, Any], report: Report
) -> None:
    if harness.skills is None:
        report.detail("Skills", "Source", str(bundled.SKILLS))
        report.steps.extend(
            [
                "mkdir -p ~/Downloads/knowledge-mcp-skills && (cd "
                + shlex.quote(str(bundled.SKILLS))
                + ' && for d in */; do zip -qr ~/Downloads/knowledge-mcp-skills/"${d%/}.zip" "$d"; done)',
                "Upload each ZIP in ~/Downloads/knowledge-mcp-skills through Customize → Skills in Claude.",
            ]
        )
        return
    folder = harness.skills(env)
    record["created"] += _make_folder(folder)
    linked, kept = [], []
    for skill in bundled.skills():
        link = folder / skill.name
        if _ours(link):
            record["links"].append(str(link))
            linked.append(skill.name)
            continue
        if link.exists() or link.is_symlink():
            kept.append(str(link))
            continue
        link.symlink_to(bundled.SKILLS / skill.name, target_is_directory=True)
        record["links"].append(str(link))
        linked.append(skill.name)
    report.detail("Skills", "Skill links", str(len(linked)))
    report.detail("Skills", "Folder", str(folder))
    report.detail("Skills", "Names", linked)
    for path in kept:
        report.warn(
            f"{path} already exists, so kb left it unchanged. To link the bundled skill, remove "
            f"{path}, then run kb setup --remove {harness.id} and kb setup {harness.id}."
        )


def harness_of(name: str) -> Harness:
    try:
        return HARNESSES[name]
    except KeyError:
        raise UnknownHarness(name) from None


def _unreadable(
    path: Path, harness: Harness, error: configedit.ConfigError, command: str
) -> SetupError:
    if error.line is None:
        return SetupError(
            f"kb can't change {path}: {error}.",
            f"Fix {path}, then run {command} again.",
        )
    return SetupError(
        f"{path} is not valid {harness.format.upper()}: {error}.",
        f"Fix line {error.line}, then run {command} again.",
    )


def setup(name: str, env: Env | None = None) -> Report:
    env = env or Env.current()
    harness = harness_of(name)
    bundled.require()
    try:
        return _setup(name, harness, env)
    except configedit.ConfigError as error:
        raise _unreadable(
            harness.config(env), harness, error, f"kb setup {name}"
        ) from None


def _register(
    harness: Harness, env: Env, command: list[str], report: Report
) -> dict[str, Any]:
    record: dict[str, Any] = {"links": [], "created": [], "backups": []}
    existing = harness.read_entry(env)
    if existing is not None:
        if command_of(existing) != command:
            raise ConflictingRegistration(
                harness.config(env), command_of(existing) or [], harness.id
            )
        record.update(method="present", config=str(harness.config(env)))
    else:
        cli = _cli(harness, env)
        if cli is not None and harness.cli_add is not None:
            _run(cli, harness.cli_add(command), env)
            record.update(
                method="cli", config=str(harness.config(env)), cli=harness.cli
            )
            report.detail(
                "Registration",
                "Registered with",
                shlex.join([harness.cli or cli, *harness.cli_add(command)]),
            )
        else:
            _edit_add(harness, env, command, record)
    return record


def _setup(name: str, harness: Harness, env: Env) -> Report:
    report = Report()
    state = load_state(env)
    if name in state["hosts"]:
        report.say(
            f"kb setup already registered knowledge-mcp with {harness.title}. Nothing changed."
        )
        report.steps.append(
            f"To register again, run kb setup --remove {name}, then kb setup {name}."
        )
        return report
    if (
        name == "claude-desktop"
        and not harness.config(env).parent.is_dir()
        and os.uname().sysname != "Darwin"
    ):
        raise UnsupportedDesktop()
    command = server_command(env.environ)
    record = _register(harness, env, command, report)
    report.detail("Registration", "Config", str(harness.config(env)))
    report.detail("Registration", "Server", shlex.join(command))
    for backup in record["backups"]:
        report.detail("Registration", "Backup", backup)
    _link_skills(harness, env, record, report)
    state["hosts"][name] = record
    _save_state(env, state)
    path = harness.config(env)
    for duplicate in harness.duplicates(env):
        report.warn(
            f"{harness.title} has both the knowledge-mcp entry in {path} and {duplicate}, "
            "so tools or skills may appear twice. Remove one installation."
        )
    for skill_duplicate in _skill_duplicates(
        harness, env, harness.skills(env) if harness.skills else None
    ):
        report.warn(skill_duplicate)
    if record["method"] == "present":
        report.say(
            f"Kept the existing knowledge-mcp entry for {harness.title} in {path}."
        )
    else:
        suffix = f"; backup at {record['backups'][-1]}" if record["backups"] else ""
        report.say(f"Registered knowledge-mcp with {harness.title} in {path}{suffix}.")
    if harness.skills is not None:
        count = len(record["links"])
        noun = "skill" if count == 1 else "skills"
        report.say(f"Linked {count} {noun} into {harness.skills(env)}.")
    executable = {
        "claude-code": "claude",
        "codex": "codex",
        "pi": "pi",
        "opencode": "opencode",
    }.get(name)
    missing = (
        (not shutil.which(executable, path=env.environ.get("PATH", "")))
        if executable
        else not Path("/Applications/Claude.app").exists()
    )
    if missing:
        reason = (
            f"{executable} is not on PATH"
            if executable
            else "Claude.app is not in /Applications"
        )
        report.warn(
            f"{reason}. Install {harness.title} to use the knowledge-mcp entry in {path}."
        )
    report.steps.append(f"{_restart(harness)} to load knowledge-mcp.")
    return report


def _restart(harness: Harness) -> str:
    # The desktop app starts its MCP servers only at launch.
    if harness.id == "claude-desktop":
        return "Restart the Claude desktop app"
    return f"Start a new {harness.title} session"


def _remove_entry(
    harness: Harness, env: Env, record: dict[str, Any], report: Report
) -> bool:
    method = record.get("method")
    if method == "cli":
        return _cli_remove(harness, env, record, report)
    if method == "file":
        try:
            _edit_remove(harness, env, record)
        except configedit.ConfigError as error:
            raise _unreadable(
                Path(record["config"]),
                harness,
                error,
                f"kb setup --remove {harness.id}",
            ) from None
    return False


def remove(name: str, env: Env | None = None) -> Report:
    env = env or Env.current()
    harness = harness_of(name)
    report = Report()
    state = load_state(env)
    record = state["hosts"].get(name)
    if record is None:
        report.say(
            f"kb did not register knowledge-mcp with {harness.title}. Nothing changed."
        )
        found = _entry_or_unknown(harness, env)
        if found is True:
            report.say(f"kb can't parse {harness.config(env)}.")
        elif found is not None:
            fix = removal_fix(harness, env)
            report.say(
                f"{harness.config(env)} has a knowledge-mcp entry that kb did not add. {fix}"
            )
        return report
    entry_left = _remove_entry(harness, env, record, report)
    others = {
        link
        for other, data in state["hosts"].items()
        if other != name
        for link in data["links"]
    }
    removed = 0
    for link in record["links"]:
        path = Path(link)
        if link not in others and _links_to_same_name(path):
            path.unlink()
            removed += 1
    _removal_feedback(harness, record, state, removed, report)
    if entry_left:
        noun = "skill link" if removed == 1 else "skill links"
        report.lines = [f"Removed {removed} {noun}."]
        # Keep the record so a later --remove can finish once the entry is gone.
        record["links"] = [link for link in record["links"] if Path(link).is_symlink()]
        _save_state(env, state)
        return report
    for backup in record["backups"]:
        Path(backup).unlink(missing_ok=True)
    del state["hosts"][name]
    created = sorted(set(state["created"]) | set(record["created"]))
    if state["hosts"]:
        state["created"] = created
        _save_state(env, state)
        state["created"] = _prune(state["created"])
        _save_state(env, state)
    else:
        _state_path(env).unlink(missing_ok=True)
        _prune(created)
    report.say(f"{_restart(harness)}.")
    if not state["hosts"]:
        _name_state_folder(env, report)
    return report


def _removal_feedback(
    harness: Harness,
    record: dict[str, Any],
    state: dict[str, Any],
    removed: int,
    report: Report,
) -> None:
    name = harness.id
    others = {
        link
        for other, data in state["hosts"].items()
        if other != name
        for link in data["links"]
    }
    method = record.get("method")
    kept = [
        other
        for other, data in state["hosts"].items()
        if other != name and set(record["links"]) & set(data["links"])
    ]
    noun = "skill link" if removed == 1 else "skill links"
    report.lines = [
        f"Removed the setup record for {harness.title}. Check {record['config']} for any remaining knowledge-mcp entry."
        if method in {"cli", "file"}
        else f"Kept the knowledge-mcp entry in {record['config']} because kb setup did not add it."
    ]
    if harness.skills is not None:
        report.say(f"Removed {removed} {noun}.")
    if kept:
        count = len(set(record["links"]) & others)
        noun = "skill link" if count == 1 else "skill links"
        titles = [HARNESSES[other].title for other in kept]
        users = (
            ", ".join(titles[:-1]) + " and " + titles[-1] if titles[1:] else titles[0]
        )
        report.say(f"Kept {count} {noun} also used by {users}.")


def _name_state_folder(env: Env, report: Report) -> None:
    folder = state_folder(env)
    if not folder.is_dir():
        return
    report.say(state_lines(env)[0])
    report.say(f"log.jsonl, edits.jsonl and the explorer folder stay in {folder}.")


def _entry_or_unknown(harness: Harness, env: Env) -> Any:
    """Return the entry, None when absent, or True on `ConfigError`. Other exceptions propagate."""
    try:
        return harness.read_entry(env)
    except configedit.ConfigError:
        return True


def _cli_remove(
    harness: Harness, env: Env, record: dict[str, Any], report: Report
) -> bool:
    """Return True when removal fails and the entry remains or the settings cannot be parsed."""
    if _entry_or_unknown(harness, env) is None:
        return False
    cli = _cli(harness, env)
    failure = f"{record['cli']} is no longer on PATH"
    if cli is not None and harness.cli_remove is not None:
        try:
            _run(cli, harness.cli_remove, env)
        except SetupError as error:
            failure = str(error)
        else:
            return False
    if _entry_or_unknown(harness, env) is None:
        return False
    report.problem(
        failure.rstrip(".") + ".",
        f"Delete the knowledge-mcp entry from {record['config']}, then run kb setup --remove {harness.id} again.",
    )
    return True


@dataclass
class DoctorReport(Report):
    checks: list[tuple[str, str]] = field(default_factory=list)
    apps: dict[str, Literal["registered", "not registered", "needs attention"]] = field(
        default_factory=dict
    )

    warning_fixes: list[str] = field(default_factory=list)
    registrations: list[dict[str, Any]] = field(default_factory=list)
    kb_version: str | None = None
    bus_version: str | None = None
    state_dir: str = ""

    def warn_with_fix(self, line: str, fix: str) -> None:
        super().warn(line)
        self.warning_fixes.append(fix)

    def repair(self, harness: str) -> None:
        fix = f"Run kb setup --remove {harness}, then kb setup {harness}."
        if self.problems and self.problems[-1].fix is None:
            self.problems[-1].fix = fix

    def as_json(self) -> dict[str, Any]:
        return {
            "schema": "knowledge-mcp/doctor/1",
            "kb": self.kb_version,
            "knowledge_bus": self.bus_version,
            "checks": [
                {
                    "name": name,
                    "ok": value in {"runs", "installed", "matches package", "found"},
                }
                for name, value in self.checks
            ],
            "registrations": self.registrations,
            "problems": [{"message": p.message, "fix": p.fix} for p in self.problems],
            "warnings": [
                {"message": message, "fix": fix}
                for message, fix in zip(self.warnings, self.warning_fixes, strict=True)
            ],
            "state_dir": self.state_dir,
        }

    def text(self, verbose: bool = False) -> str:
        kbp_runs = next(
            (
                outcome == "runs"
                for name, outcome in self.checks
                if name == "kbp executable"
            ),
            False,
        )
        lines = [
            f"Install:  kb {self.kb_version or '<unset>'}, knowledge-bus {self.bus_version or '<unset>'}, kbp {'runs' if kbp_runs else 'failed'}"
        ]
        for registration in self.registrations:
            title = HARNESSES[registration["name"]].title
            status = registration["status"].replace("-", " ")
            count = registration["skills"]
            suffix = (
                f", {count} skill{'' if count == 1 else 's'} linked"
                if status == "registered" and count is not None
                else ""
            )
            lines.append(f"{title}:  {status}{suffix}")
        problems, warnings = len(self.problems), len(self.warnings)
        if problems or warnings:
            p_noun = "problem" if problems == 1 else "problems"
            w_noun = "warning" if warnings == 1 else "warnings"
            lines.append(f"Found {problems} {p_noun} and {warnings} {w_noun}.")
        else:
            lines.append("No problems found.")
        if all(r["status"] == "not-registered" for r in self.registrations):
            *others, last = HARNESSES
            lines.append(
                f"To register knowledge-mcp, run kb setup with {', '.join(others)} or {last}."
            )
        text = "\n".join(lines)
        return text + "\n\n" + self.details() if verbose else text


def removal_fix(harness: Harness, env: Env) -> str:
    if harness.cli_remove:
        return (
            "Remove the entry with "
            + shlex.join([harness.cli or harness.id, *harness.cli_remove])
            + "."
        )
    if harness.id == "codex":
        return "Remove the entry with codex mcp remove knowledge-mcp."
    return f"Delete the knowledge-mcp entry from {harness.config(env)}."


def _kbp_version(printed: str) -> str:
    """Format `kbp --version` output as `<release> (protocol <protocol>)`, such as
    `0.10.0 (protocol kbp/0.9)`.
    """
    lines = printed.splitlines()
    release = lines[0].rsplit(" ", 1)[-1] if lines else ""
    protocol = lines[1].split(": ", 1)[-1] if len(lines) > 1 else ""
    return f"{release} (protocol {protocol})" if protocol else release


def _check_kbp(report: DoctorReport) -> None:
    try:
        printed = kbp.run(["--version"], Path.cwd())
        if printed.code == 0:
            report.checks.append(("kbp executable", "runs"))
            report.detail("Installation", "kbp", _kbp_version(printed.stdout))
        else:
            report.checks.append(("kbp executable", "failed"))
            report.problem(
                f"kbp --version exits {printed.code}: {printed.stderr.strip()}.",
                REINSTALL,
            )
    except (OSError, RuntimeError) as error:
        report.checks.append(("kbp executable", "failed"))
        report.problem(f"kbp does not run: {str(error).rstrip('.')}.", REINSTALL)


def doctor(env: Env | None = None) -> DoctorReport:
    env = env or Env.current()
    report = DoctorReport(
        sections={
            "Installation": [],
            "Harnesses": [],
            "Bundled spec files": [],
            "Bundled skills": [],
            "State": [],
        }
    )
    report.kb_version = version()
    report.state_dir = str(state_folder(env))
    report.detail("Installation", "kb", report.kb_version)
    try:
        package = metadata.version("knowledge-bus")
    except metadata.PackageNotFoundError:
        package = None
    report.bus_version = package
    fault = bundled.fault()
    ref = bundled.ref() if fault is None else None
    report.checks.append(
        ("knowledge-bus package", "installed" if package is not None else "missing")
    )
    if package is not None and ref is not None:
        report.checks.append(
            (
                "Bundled release",
                "matches package" if ref == f"v{package}" else "mismatch",
            )
        )
    if package is None:
        report.problem("The knowledge-bus package is not installed.", REINSTALL)
    elif ref is not None and ref != f"v{package}":
        report.problem(
            f"The bundled spec files come from {ref}, but the knowledge-bus "
            f"package is {package}.",
            REINSTALL,
        )
    if package is not None:
        report.detail("Installation", "knowledge-bus", package)
    if ref is not None:
        report.detail("Bundled spec files", "Release", ref)
    _check_kbp(report)
    specs = (
        sorted(path.name for path in bundled.UNIVERSES.iterdir() if path.is_dir())
        if bundled.UNIVERSES.is_dir()
        else []
    )
    skills = bundled.skills()
    report.checks.append(
        (
            "Bundled spec files and skills",
            "found" if specs and skills else "missing",
        )
    )
    report.detail("Bundled spec files", "Names", specs)
    report.detail("Bundled skills", "Names", [skill.name for skill in skills])
    if fault is not None:
        report.problems.append(fault)
    report.detail("State", log.VARIABLE, env.environ.get(log.VARIABLE, "") or "<unset>")
    report.detail("State", "State directory", str(state_folder(env)))
    state = load_state(env)
    command = server_command(env.environ)
    for harness in HARNESSES.values():
        _check_harness(harness, env, state, command, report)
        _registration(harness, env, state, report)
    return report


def _registration(
    harness: Harness, env: Env, state: dict[str, Any], report: DoctorReport
) -> None:
    status = {
        "registered": "registered",
        "not registered": "not-registered",
        "needs attention": "needs-attention",
    }[report.apps[harness.title]]
    record = state["hosts"].get(harness.id)
    report.registrations.append(
        {
            "name": harness.id,
            "status": status,
            "settings": str(harness.config(env)),
            "skills": len(record["links"]) if record and harness.skills else None,
        }
    )


def _check_harness(
    harness: Harness,
    env: Env,
    state: dict[str, Any],
    command: list[str],
    report: DoctorReport,
) -> None:
    record = state["hosts"].get(harness.id)
    report.apps[harness.title] = "needs attention"
    try:
        entry = harness.read_entry(env)
    except configedit.ConfigError as error:
        path = harness.config(env)
        report.problem(
            f"kb can't read {path}: {error}.",
            f"Fix {path}, then run kb doctor again."
            if error.line is None
            else f"Fix line {error.line} of {path}, then run kb doctor again.",
        )
        return
    if record is None and entry is None:
        report.apps[harness.title] = "not registered"
        report.detail("Harnesses", harness.title, "not registered")
        return
    runs = command_of(entry)
    if entry is None:
        report.problem(
            f"{harness.title}: kb has a setup record, but {harness.config(env)} has no {NAME} entry."
        )
        report.repair(harness.id)
    elif runs != command:
        report.problem(
            f"{harness.title}: the knowledge-mcp entry runs {shlex.join(runs)}, but kb expects {shlex.join(command)}."
            if runs
            else f"{harness.title}: the knowledge-mcp entry has no command, but kb expects {shlex.join(command)}."
        )
    elif runs and not Path(runs[0]).exists():
        report.problem(f"{harness.title}: {runs[0]} is missing.")
    else:
        report.apps[harness.title] = "registered"
        report.detail("Harnesses", harness.title, "registered")
    if report.apps[harness.title] == "needs attention":
        report.repair(harness.id)
    report.detail("Harnesses", f"{harness.title} config", str(harness.config(env)))
    _check_skill_links(harness, env, record, report)
    for duplicate in harness.duplicates(env):
        report.warn_with_fix(
            f"{harness.title} has both the knowledge-mcp entry in {harness.config(env)} and "
            f"{duplicate}, so tools or skills may appear twice.",
            (
                "Run kb setup --remove codex, or run codex plugin remove knowledge-mcp@knowledge-mcp."
                if harness.id == "codex" and "knowledge-mcp@knowledge-mcp" in duplicate
                else f"Run kb setup --remove {harness.id}, or remove {duplicate}."
            ),
        )
    for skill_duplicate in _skill_duplicates(
        harness, env, harness.skills(env) if harness.skills else None
    ):
        report.warn_with_fix(
            skill_duplicate,
            f"Run kb setup --remove {harness.id}, or remove the duplicate skills from the other skills folder.",
        )


def _check_skill_links(
    harness: Harness, env: Env, record: dict[str, Any] | None, report: DoctorReport
) -> None:
    if record is not None and harness.skills is not None:
        folder = harness.skills(env)
        missing = [
            skill.name
            for skill in bundled.skills()
            if not (folder / skill.name).is_symlink()
            and str(folder / skill.name) not in record["links"]
        ]
        broken = [link for link in record["links"] if not Path(link).exists()]
        if broken:
            report.apps[harness.title] = "needs attention"
            report.problem(
                f"These {harness.title} skill links are missing or point to missing folders: "
                f"{', '.join(broken)}."
            )
            report.repair(harness.id)
        elif missing:
            report.apps[harness.title] = "needs attention"
            report.problem(
                f"{harness.title} has no skill links for {', '.join(missing)}."
            )
            report.repair(harness.id)
        else:
            report.detail(
                "Harnesses", f"{harness.title} skill links", str(len(record["links"]))
            )
            report.detail("Harnesses", f"{harness.title} skills folder", str(folder))
