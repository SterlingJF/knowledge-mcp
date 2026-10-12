"""Manage and diagnose Knowledge-MCP setup.

- `kb` CLI setup
- MCP server registration in agent apps
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from knowledge_mcp import bundled, configedit, log
from knowledge_mcp.hosts import HOSTS, NAME, Env, Host, describe, server_command

STATE_VERSION = 1


class SetupError(RuntimeError):
    """Setup can't go ahead; the message says what to do."""


@dataclass
class Report:
    """What a setup, removal or check did and found, line by line."""

    lines: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    sections: dict[str, list[tuple[str, str | list[str]]]] = field(default_factory=dict)
    steps: list[str] = field(default_factory=list)

    def detail(self, section: str, label: str, value: str | list[str]) -> None:
        self.sections.setdefault(section, []).append((label, value))

    def say(self, line: str) -> None:
        self.lines.append(line)

    def warn(self, line: str) -> None:
        self.warnings.append(line)

    def text(self) -> str:
        blocks = []
        if self.problems:
            blocks.append("\n".join(f"problem: {line}" for line in self.problems))
        if self.warnings:
            blocks.append("\n".join(f"warning: {line}" for line in self.warnings))
        if self.lines:
            blocks.append("\n".join(self.lines))
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
        if self.steps:
            blocks.append(
                "\n".join(["Next steps", *(f"  {step}" for step in self.steps)])
            )
        return "\n\n".join(blocks)


# --- State -------------------------------------------------------------------------------------


def history_folder(env: Env) -> Path:
    """The answer log, the edit record and Explorer folders, as `log.directory` resolves them."""
    return log.directory(env.environ, env.home)


def history_lines(env: Env) -> list[str]:
    """The variable's value, or "not set", and the state folder in use."""
    named = env.environ.get(log.VARIABLE, "") or "not set"
    return [f"{log.VARIABLE}: {named}", f"State folder: {history_folder(env)}"]


def state_folder(env: Env) -> Path:
    return history_folder(env) / "setup"


def _state_path(env: Env) -> Path:
    return state_folder(env) / "state.json"


def load_state(env: Env) -> dict[str, Any]:
    path = _state_path(env)
    if not path.is_file():
        return {"version": STATE_VERSION, "hosts": {}, "created": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(env: Env, state: dict[str, Any]) -> None:
    folder = state_folder(env)
    state["created"] = sorted(set(state["created"]) | set(_make_folder(folder)))
    _write(
        _state_path(env),
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        mode=0o600,
    )


def _make_folder(folder: Path) -> list[str]:
    """Create `folder` and its missing parents; return the folders created, outermost first."""
    missing = []
    for candidate in (folder, *folder.parents):
        if candidate.exists():
            break
        missing.append(candidate)
    folder.mkdir(parents=True, exist_ok=True)
    return [str(path) for path in reversed(missing)]


def _write(path: Path, text: str, mode: int | None = None) -> None:
    """Replace the file in one step, keeping its permissions."""
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
    """Remove each empty folder, innermost first; return the ones still there."""
    kept = []
    for folder in sorted(folders, key=lambda name: name.count(os.sep), reverse=True):
        try:
            Path(folder).rmdir()
        except FileNotFoundError:
            continue
        except OSError:
            kept.append(folder)
    return sorted(kept)


# --- Entries -------------------------------------------------------------------------------------


def command_of(entry: Any) -> list[str] | None:
    """The command line an entry runs, in either entry shape."""
    if not isinstance(entry, dict):
        return None
    command = entry.get("command")
    if isinstance(command, list):
        return [str(part) for part in command]
    if isinstance(command, str):
        return [command, *[str(arg) for arg in entry.get("args", [])]]
    return None


def _edit_add(host: Host, env: Env, command: list[str], record: dict[str, Any]) -> None:
    path = host.config(env)
    created = not path.exists()
    text = "" if created else path.read_text(encoding="utf-8")
    entry = host.entry(command)
    if host.format == "toml":
        new, piece = configedit.toml_insert(text, host.path[0], NAME, entry)
    else:
        new, piece = configedit.json_insert(text, host.path, NAME, entry)
    if created:
        record["created"] += _make_folder(path.parent)
    else:
        backups = state_folder(env) / "backups"
        record["created"] += _make_folder(backups)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup = backups / f"{host.id}-{stamp}-{path.name}"
        shutil.copy2(path, backup)
        record["backups"].append(str(backup))
    _write(path, new, mode=None if not created else 0o600)
    record.update(method="file", config=str(path), piece=piece, created_file=created)


def _edit_remove(host: Host, env: Env, record: dict[str, Any]) -> None:
    path = Path(record["config"])
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    if host.format == "toml":
        new = configedit.toml_remove(text, host.path[0], NAME, record.get("piece"))
    else:
        new = configedit.json_remove(text, host.path, NAME, record.get("piece"))
    empty = not new.strip() or (
        host.format == "json" and configedit.empty_chain(new, host.path)
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
        raise SetupError(
            f"`{Path(cli).name} {' '.join(args)}` failed with exit code {done.returncode}: "
            f"{(done.stderr or done.stdout).strip()}"
        )


def _cli(host: Host, env: Env) -> str | None:
    if host.cli is None:
        return None
    return shutil.which(host.cli, path=env.environ.get("PATH", ""))


# --- Skills --------------------------------------------------------------------------------------


def _ours(link: Path) -> bool:
    """Whether `link` is a symlink to this install's copy of the skill of the same name."""
    return link.is_symlink() and Path(os.readlink(link)) == bundled.SKILLS / link.name


def _recorded(link: Path) -> bool:
    """Whether a link kb recorded still is a symlink to a skill of its name."""
    return link.is_symlink() and Path(os.readlink(link)).name == link.name


@dataclass(frozen=True)
class SkillDuplicate:
    """A skill-name conflict in another folder the app reads."""

    full: str
    brief: str


def _skill_duplicates(
    host: Host, env: Env, linked_into: Path | None
) -> list[SkillDuplicate]:
    """Describe matching skill names from each other folder in one scan."""
    names = sorted(skill.name for skill in bundled.skills())
    found = []
    for folder in host.reads(env):
        if folder == linked_into or not folder.is_dir():
            continue
        ours, other = [], []
        for name in names:
            path = folder / name
            if path.exists() or path.is_symlink():
                (ours if _ours(path) else other).append(name)
        if ours:
            found.append(
                SkillDuplicate(
                    full=(
                        f"{host.title} also reads {folder}, which holds kb links for "
                        f"{', '.join(ours)}; {host.title} may list those skills twice."
                    ),
                    brief=f"{host.title}: duplicate kb skill links in {folder}.",
                )
            )
        if other:
            found.append(
                SkillDuplicate(
                    full=(
                        f"{host.title} also reads {folder}, where {', '.join(other)} came from another "
                        "installer, such as npx skills add; remove one copy."
                    ),
                    brief=(
                        f"{host.title}: duplicate skill names from another installer in "
                        f"{folder}; remove one copy."
                    ),
                )
            )
    return found


def _link_skills(host: Host, env: Env, record: dict[str, Any], report: Report) -> None:
    if host.skills is None:
        report.detail("Skills", "Source", str(bundled.SKILLS))
        report.steps.extend(host.no_skills)
        return
    folder = host.skills(env)
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
            f"{path} already exists and was installed another way; kb leaves the existing path unchanged. Remove the existing copy through its installer to use the copy bundled with knowledge-mcp."
        )


# --- Setup and removal ---------------------------------------------------------------------------


def host_of(name: str) -> Host:
    try:
        return HOSTS[name]
    except KeyError:
        raise SetupError(f"Unknown host {name!r}. Hosts: {', '.join(HOSTS)}.") from None


def setup(name: str, env: Env | None = None) -> Report:
    env = env or Env.current()
    host = host_of(name)
    report = Report()
    state = load_state(env)
    if name in state["hosts"]:
        report.say(f"{host.title} is already set up.")
        report.steps.append(
            f"Run `kb setup --remove {name}` before running setup again."
        )
        return report
    if (
        name == "claude-desktop"
        and not host.config(env).parent.is_dir()
        and os.uname().sysname != "Darwin"
    ):
        raise SetupError(
            "Set up the Claude desktop app on macOS, where the app stores its settings."
        )
    command = server_command(env.environ)
    record: dict[str, Any] = {"links": [], "created": [], "backups": []}
    existing = host.read_entry(env)
    if existing is not None:
        if command_of(existing) != command:
            raise SetupError(
                f"{host.config(env)} already has a {NAME} entry that runs {describe(command_of(existing))}. "
                f"Remove that entry, then run `kb setup {name}` again."
            )
        record.update(method="present", config=str(host.config(env)))
        report.say(f"Kept the existing {NAME} registration for {host.title}.")
    else:
        cli = _cli(host, env)
        if cli is not None and host.cli_add is not None:
            _run(cli, host.cli_add(command), env)
            record.update(method="cli", config=str(host.config(env)), cli=host.cli)
            report.say(f"Registered {NAME} for {host.title}.")
            report.detail(
                "Registration",
                "Registered with",
                shlex.join([host.cli, *host.cli_add(command)]),
            )
        else:
            _edit_add(host, env, command, record)
            report.say(f"Registered {NAME} for {host.title}.")
    report.detail("Registration", "Config", str(host.config(env)))
    report.detail("Registration", "Server", shlex.join(command))
    for backup in record["backups"]:
        report.detail("Registration", "Backup", backup)
    _link_skills(host, env, record, report)
    state["hosts"][name] = record
    _save_state(env, state)
    for duplicate in host.duplicates(env):
        report.warn(
            f"{duplicate} is installed too, so {host.title} gets knowledge-mcp's tools or knowledge-bus's skills twice. Remove either installation."
        )
    for duplicate in _skill_duplicates(
        host, env, host.skills(env) if host.skills else None
    ):
        report.warn(duplicate.full)
    report.steps.append(f"Start a new {host.title} session.")
    return report


def remove(name: str, env: Env | None = None) -> Report:
    env = env or Env.current()
    host = host_of(name)
    report = Report()
    state = load_state(env)
    record = state["hosts"].get(name)
    if record is None:
        report.say(f"No kb setup record for {host.title}; nothing to remove.")
        return report
    method = record.get("method")
    entry_left = False
    if method == "cli":
        entry_left = _cli_remove(host, env, record, report)
    elif method == "file":
        _edit_remove(host, env, record)
        report.say(f"Removed {NAME} from {record['config']}.")
    else:
        report.say(
            f"Preserved the {NAME} entry in {record['config']} because the entry predates setup."
        )
    others = {
        link
        for other, data in state["hosts"].items()
        if other != name
        for link in data["links"]
    }
    removed = 0
    for link in record["links"]:
        path = Path(link)
        if link not in others and _recorded(path):
            path.unlink()
            removed += 1
    if record["links"]:
        report.say(
            f"Removed {removed} skill links; retained links shared with other hosts set up by kb."
        )
    if entry_left:
        # Keep the record so a later `--remove` finishes the job once the entry is gone.
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
    report.say(
        f"Removed recorded setup changes for {host.title}'s {NAME} integration; start a new session to see the change."
    )
    if not state["hosts"]:
        _name_history(env, report)
    return report


def _name_history(env: Env, report: Report) -> None:
    """Name the variable and the history folder it points to; delete nothing."""
    folder = history_folder(env)
    if not folder.is_dir():
        return
    report.say(history_lines(env)[0])
    report.say(
        f"Your answer log, edit record and any Explorer folders stay in {folder}."
    )


def _entry_or_unknown(host: Host, env: Env) -> Any:
    """knowledge-mcp's entry, None when absent, or True when the file can't be read."""
    try:
        return host.read_entry(env)
    except configedit.ConfigError:
        return True


def _cli_remove(host: Host, env: Env, record: dict[str, Any], report: Report) -> bool:
    """Remove an entry the host's CLI added; return True when the entry is still there."""
    command = f"{record['cli']} {' '.join(host.cli_remove or [])}"
    if _entry_or_unknown(host, env) is None:
        report.say(f"The {NAME} entry was already gone from {record['config']}.")
        return False
    cli = _cli(host, env)
    failure = f"`{record['cli']}` is no longer on PATH"
    if cli is not None and host.cli_remove is not None:
        try:
            _run(cli, host.cli_remove, env)
        except SetupError as error:
            failure = str(error)
        else:
            report.say(f"Removed {NAME} with `{command}`.")
            return False
    if _entry_or_unknown(host, env) is None:
        report.say(f"The {NAME} entry is gone from {record['config']}.")
        return False
    report.problems.append(
        f"{failure}; check for the {NAME} entry in {record['config']}. Run `{command}` or delete the entry manually, then run `kb setup --remove {host.id}` again to finish removal."
    )
    return True


# --- Doctor --------------------------------------------------------------------------------------


@dataclass
class DoctorReport(Report):
    """Check outcomes by default; installation facts when requested."""

    checks: list[tuple[str, str]] = field(default_factory=list)
    apps: dict[str, Literal["registered", "not set up", "needs attention"]] = field(
        default_factory=dict
    )

    brief_warnings: list[str] = field(default_factory=list)

    def warn(self, line: str, brief: str | None = None) -> None:
        super().warn(line)
        self.brief_warnings.append(line if brief is None else brief)

    def repair(self, host: str) -> None:
        for command in (f"kb setup --remove {host}", f"kb setup {host}"):
            if command not in self.steps:
                self.steps.append(command)

    def text(self, verbose: bool = False) -> str:
        problems = len(self.problems)
        warnings = len(self.warnings)
        verdict = (
            f"Installation and registration checks: {problems} "
            f"{'problem' if problems == 1 else 'problems'}, {warnings} "
            f"{'warning' if warnings == 1 else 'warnings'}."
        )
        if verbose:
            return verdict + "\n\n" + super().text()
        blocks = [verdict]
        if self.problems:
            blocks.append("\n".join(f"problem: {line}" for line in self.problems))
        if self.warnings:
            blocks.append("\n".join(f"warning: {line}" for line in self.brief_warnings))
        if self.steps:
            blocks.append(
                "\n".join(["Next steps", *(f"  {step}" for step in self.steps)])
            )
        if not self.problems:
            blocks.append(
                "\n".join(
                    [
                        "Checks",
                        *(f"  {label}: {outcome}" for label, outcome in self.checks),
                    ]
                )
            )
        apps = [
            f"  {name}: {outcome}"
            for name, outcome in self.apps.items()
            if outcome == "needs attention"
            or (not self.problems and outcome == "registered")
        ]
        if not self.problems:
            unused = sum(outcome == "not set up" for outcome in self.apps.values())
            if unused:
                apps.append(f"  Apps not set up: {unused}")
        if apps:
            blocks.append("\n".join(["Agent apps", *apps]))
        return "\n\n".join(blocks)


def doctor(env: Env | None = None) -> DoctorReport:
    from importlib import metadata

    from knowledge_mcp import kbp
    from knowledge_mcp.main import version

    env = env or Env.current()
    report = DoctorReport(
        sections={
            "Installation": [],
            "Agent apps": [],
            "Bundled guidance": [],
            "Bundled skills": [],
            "State": [],
        }
    )
    report.detail("Installation", "kb", version())
    try:
        package = metadata.version("knowledge-bus")
    except metadata.PackageNotFoundError:
        package = None
    ref = bundled.ref()
    report.checks.append(
        ("knowledge-bus package", "installed" if package is not None else "missing")
    )
    if package is not None:
        report.checks.append(
            (
                "Bundled release",
                "matches package" if ref == f"v{package}" else "mismatch",
            )
        )
    if package is None:
        report.problems.append("The knowledge-bus package is not installed.")
    elif ref != f"v{package}":
        report.problems.append(
            f"The bundled universe specs and skills come from {ref}, but the knowledge-bus "
            f"package is {package}."
        )
    if package is not None:
        report.detail("Installation", "knowledge-bus", package)
    report.detail("Bundled guidance", "Release", ref)
    try:
        printed = kbp.run(["--version"], Path.cwd())
        if printed.code == 0:
            report.checks.append(("kbp executable", "runs"))
            report.detail("Installation", "kbp", printed.stdout.splitlines())
        else:
            report.checks.append(("kbp executable", "failed"))
            report.problems.append(
                f"`kbp --version` exits {printed.code}: {printed.stderr.strip()}"
            )
    except (OSError, RuntimeError) as error:
        report.checks.append(("kbp executable", "failed"))
        report.problems.append(f"kbp does not run: {error}")
    specs = sorted(path.name for path in bundled.UNIVERSES.iterdir() if path.is_dir())
    skills = bundled.skills()
    report.checks.append(
        ("Bundled guidance and skills", "found" if specs and skills else "missing")
    )
    report.detail("Bundled guidance", "Definitions", specs)
    report.detail("Bundled skills", "Names", [skill.name for skill in skills])
    if not specs or not skills:
        report.problems.append(
            f"The bundled universe specs or skills are missing from {bundled.DATA}."
        )
    report.detail("State", log.VARIABLE, env.environ.get(log.VARIABLE, "") or "not set")
    report.detail("State", "State folder", str(history_folder(env)))
    state = load_state(env)
    command = server_command(env.environ)
    for host in HOSTS.values():
        _check_host(host, env, state, command, report)
    return report


def _check_host(
    host: Host,
    env: Env,
    state: dict[str, Any],
    command: list[str],
    report: DoctorReport,
) -> None:
    record = state["hosts"].get(host.id)
    report.apps[host.title] = "needs attention"
    try:
        entry = host.read_entry(env)
    except configedit.ConfigError as error:
        report.problems.append(
            f"{host.title}: invalid configuration in {host.config(env)}: {error}"
        )
        return
    if record is None and entry is None:
        report.apps[host.title] = "not set up"
        report.detail("Agent apps", host.title, "not set up")
        return
    runs = command_of(entry)
    if entry is None:
        report.problems.append(
            f"{host.title}: kb has a setup record, but {host.config(env)} has no {NAME} entry."
        )
        report.repair(host.id)
    elif runs != command:
        report.problems.append(
            f"{host.title}: {NAME} command is {describe(runs)}; expected {describe(command)}."
        )
    elif runs and not Path(runs[0]).exists():
        report.problems.append(f"{host.title}: {runs[0]} is missing.")
    else:
        report.apps[host.title] = "registered"
        report.detail("Agent apps", host.title, "registered")
    report.detail("Agent apps", f"{host.title} config", str(host.config(env)))
    if record is not None and host.skills is not None:
        folder = host.skills(env)
        missing = [
            skill.name
            for skill in bundled.skills()
            if not (folder / skill.name).is_symlink()
            and str(folder / skill.name) not in record["links"]
        ]
        broken = [link for link in record["links"] if not Path(link).exists()]
        if broken:
            report.apps[host.title] = "needs attention"
            report.repair(host.id)
            report.problems.append(
                f"{host.title}: skill links or targets are missing: {', '.join(broken)}."
            )
        elif missing:
            report.apps[host.title] = "needs attention"
            report.repair(host.id)
            report.problems.append(
                f"{host.title}: missing skill links: {', '.join(missing)}."
            )
        else:
            report.detail(
                "Agent apps", f"{host.title} skill links", str(len(record["links"]))
            )
            report.detail("Agent apps", f"{host.title} skills folder", str(folder))
    for duplicate in host.duplicates(env):
        report.warn(f"{host.title}: {duplicate} is installed too.")
    for duplicate in _skill_duplicates(
        host, env, host.skills(env) if host.skills else None
    ):
        report.warn(duplicate.full, brief=duplicate.brief)
