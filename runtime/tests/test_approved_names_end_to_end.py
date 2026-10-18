from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from knowledge_mcp import document_types as records
from tests.document_types_harness import Harness, KnowledgeBase
from tests.harness import (
    BUNDLED,
    CODEBASE,
    MODULE,
    PRODUCT,
    header,
    knowledge_base,
    session,
    texts,
    type_arguments,
    write,
)
from tests.kb_cli import (
    COMMANDS,
    EXIT_CODES,
    HARNESSES,
    HELP_PAGES,
    KBP_MODE_FLAGS,
    KBP_MODES,
    KNOWLEDGE_BUS_SKILLS,
    SKILLS,
    did_you_mean,
    example_faults,
    kb_mcp,
    last_line,
    listed_commands,
    listed_flags,
    run_kb,
    run_kbp,
)
from tests.test_conventions_end_to_end import PLACE, stored
from tests.test_filing_end_to_end import typed as convention_entry
from tests.test_kb_end_to_end import fixture_home, snapshot

RFC = "docs/rfcs/0042-cache.md"
PLUGIN = ".knowledge-bus/plugins/knowledge-mcp"
DOCUMENT_TYPES = f"{PLUGIN}/document-types.yaml"
OLD_RECORD = f"{PLUGIN}/record.yaml"
NEW_SKILLS = ["kb-import-document", "kb-track-document-types", "kb-write-document"]
OLD_SKILLS = ["km-bring-in", "km-fit-record", "km-write"]


def test_kb_help_leads_with_examples_and_ends_with_the_exit_codes(tmp_path):
    page = run_kb(tmp_path, "--help").stdout
    [usage] = [line for line in page.splitlines() if line.lower().startswith("usage:")]

    faults = example_faults(
        page,
        ["kb setup claude-code", "kb doctor", "kb kbp validate"],
        before="Commands",
    )

    assert usage.split(":", 1)[1].strip() == "kb <command> [flags]", page
    assert faults == [], page
    assert EXIT_CODES.match(last_line(page)), page


APPROVED_HELP: dict[tuple[str, ...], tuple[set[str], set[str], set[str]]] = {
    (): (set(COMMANDS), {"--help", "--version"}, set()),
    ("mcp",): (set(), {"--help"}, set()),
    ("setup",): (set(), {"--help", "--remove"}, set()),
    ("type",): (
        set(),
        {"--help", "--role", "--root", "--json", "--filing-values"},
        set(),
    ),
    ("doctor",): (set(), {"--help", "--verbose", "--json"}, set()),
    ("kbp",): (set(KBP_MODES), {"--help", "--version"}, set()),
    **{("kbp", mode): (set(), {"--help"}, set()) for mode in KBP_MODE_FLAGS},
}


@pytest.mark.parametrize(
    "page", list(APPROVED_HELP), ids=[" ".join(("kb", *page)) for page in APPROVED_HELP]
)
def test_help_lists_only_the_approved_commands_and_flags(tmp_path, page):
    commands, flags, tolerated = APPROVED_HELP[page]

    done = run_kb(tmp_path, *page, "--help")

    assert done.returncode == 0, done.stderr
    assert listed_commands(done.stdout) == commands, done.stdout
    assert flags <= listed_flags(done.stdout) <= flags | tolerated, done.stdout


def typed(home: Path, *args: str) -> dict[str, Any]:
    page = run_kb(home, "type", "--help").stdout
    flag = ["--json"] if "--json" in listed_flags(page) else []
    done = run_kb(home, "type", *args, *flag)
    assert done.returncode == 0, done.stdout + done.stderr
    return json.loads(done.stdout)


def ranked(answer: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (item["universe_spec"], item.get("document_type", item.get("kind")))
        for item in answer["candidates"]
    ]


def test_kb_type_and_the_get_document_type_tool_rank_by_the_role_given(tmp_path):
    root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE, PRODUCT]})
    rfc = write(root, RFC, "# Cache\n")
    home = tmp_path / "home"
    home.mkdir()

    by_role = {
        role: typed(home, str(rfc), "--role", role)
        for role in ("maintainer", "reviewer")
    }

    async def steps(client):
        found = {}
        for role in by_role:
            result = await client.call_tool(
                "kb_get_document_type",
                {
                    **type_arguments(root, RFC),
                    "role": role,
                    "listing": [{"path": RFC}],
                    "conventions": "",
                },
            )
            assert not result.is_error, texts(result)
            found[role] = json.loads(texts(result)[0])
        return found

    through_tool = session(kb_mcp(tmp_path / "server"), steps)
    assert through_tool == by_role
    assert ranked(by_role["maintainer"])[0] == (CODEBASE, "design-proposal")
    assert ranked(by_role["reviewer"])[0] == (PRODUCT, "design-doc")
    for answer in by_role.values():
        for candidate in answer["candidates"]:
            assert not [key for key in candidate if "hat" in key], candidate


def test_kb_type_defaults_root_to_the_nearest_folder_holding_knowledge_bus(tmp_path):
    outer = knowledge_base(tmp_path / "outer", {"": [PRODUCT], "team": [CODEBASE]})
    team = outer / "team"
    rfc = write(team, RFC, "# Cache\n")
    # Different entries reveal which root supplied the document-types file.
    write(outer, DOCUMENT_TYPES, document_types_file(f"team/{RFC}", NO_DOCUMENT_TYPE))
    write(team, DOCUMENT_TYPES, document_types_file(RFC, design_proposal()))
    home = tmp_path / "home"
    home.mkdir()

    default = typed(home, str(rfc))
    nearest = typed(home, str(rfc), "--root", str(team))
    highest = typed(home, str(rfc), "--root", str(outer))

    assert recorded(highest)["no_document_type"] is True
    assert recorded(nearest)["document_type"] == "design-proposal"
    assert default == nearest


RETIRED_TYPE_LINES = [
    ("kb fit", lambda rfc: (["fit", str(rfc)], ["type", str(rfc)]), "type"),
    (
        "kb type --hat",
        lambda rfc: (
            ["type", str(rfc), "--hat", "maintainer"],
            ["type", str(rfc), "--role", "maintainer"],
        ),
        "--role",
    ),
    (
        "kb type --top",
        lambda rfc: (
            ["type", str(rfc), "--top", str(rfc.parents[2])],
            ["type", str(rfc), "--root", str(rfc.parents[2])],
        ),
        "--root",
    ),
]


@pytest.mark.parametrize(
    ("lines", "suggested"),
    [case[1:] for case in RETIRED_TYPE_LINES],
    ids=[case[0] for case in RETIRED_TYPE_LINES],
)
def test_the_fit_command_and_the_hat_and_top_flags_give_way_to_type_role_and_root(
    tmp_path, lines, suggested
):
    root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE]})
    rfc = write(root, RFC, "# Cache\n")
    home = tmp_path / "home"
    home.mkdir()
    retired, replacement = lines(rfc)

    current = run_kb(home, *replacement)
    before = snapshot(tmp_path)
    done = run_kb(home, *retired)

    assert current.returncode == 0, current.stdout + current.stderr
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    assert did_you_mean(done.stderr, suggested), done.stderr
    assert snapshot(tmp_path) == before


def test_the_kb_type_help_example_runs_where_its_folder_exists(tmp_path):
    root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE, PRODUCT]})
    (root / Path(RFC).parent).mkdir(parents=True)
    (root / "inbox").mkdir()
    write(root, PLACE, stored())
    write(root, DOCUMENT_TYPES, records.dump({"inbox/cache.md": convention_entry()}))
    home = tmp_path / "home"
    home.mkdir()
    page = run_kb(home, "type", "--help").stdout
    flag = ["--json"] if "--json" in listed_flags(page) else []
    examples = [
        line.strip()
        for line in page.splitlines()
        if line.strip().startswith("kb type ")
    ]

    assert "folder must exist" in page, page
    assert examples, page
    for example in examples:
        done = run_kb(home, *shlex.split(example)[1:], *flag, cwd=root)
        assert done.returncode == 0, example + "\n" + done.stdout + done.stderr
        answer = json.loads(done.stdout)
        if "--filing-values" in shlex.split(example):
            assert (
                answer["filing"][0]["proposal"]["path"]
                == "Decisions/Use a shared cache.md"
            )
        else:
            assert answer["candidates"], done.stdout
    assert not (root / RFC).exists()
    assert not (root / "inbox/cache.md").exists()


def test_kb_type_reads_a_path_through_a_parent_folder_as_the_folder_it_names(tmp_path):
    here = knowledge_base(tmp_path / "here", {"": [CODEBASE]})
    there = knowledge_base(tmp_path / "there", {"": [PRODUCT]})
    (there / "docs").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    page = run_kb(home, "type", "--help").stdout
    flag = ["--json"] if "--json" in listed_flags(page) else []

    through_parent = run_kb(home, "type", "../there/docs/plan.md", *flag, cwd=here)
    direct = run_kb(home, "type", str(there / "docs" / "plan.md"), *flag, cwd=here)

    assert through_parent.returncode == 0, through_parent.stdout + through_parent.stderr
    assert direct.returncode == 0, direct.stdout + direct.stderr
    assert json.loads(through_parent.stdout) == json.loads(direct.stdout)
    assert {
        item["universe_spec"] for item in json.loads(direct.stdout)["candidates"]
    } == {PRODUCT}


def test_setup_help_and_errors_call_the_agent_program_a_harness(tmp_path):
    home = fixture_home(tmp_path)
    before = snapshot(home)

    page = run_kb(home, "setup", "--help")
    unknown = run_kb(home, "setup", "nosuch")

    assert page.returncode == 0, page.stderr
    [usage] = [
        line for line in page.stdout.splitlines() if line.lower().startswith("usage:")
    ]
    assert "harness" in usage.lower()
    for name in HARNESSES:
        assert name in page.stdout
    assert unknown.stderr.startswith("Error: ")
    assert "kb setup --help" in unknown.stderr.splitlines()[-1]
    assert unknown.returncode == 2
    assert "harness" in unknown.stderr.lower()
    for text in (page.stdout, unknown.stderr):
        assert not re.search(r"(?i)(?<![\w-])hosts?(?![\w-])|agent apps?", text), text
    assert snapshot(home) == before


@pytest.mark.parametrize(
    "remove",
    [["setup", "--remove", "codex"], ["setup", "codex", "--remove"]],
    ids=["--remove before the harness", "--remove after the harness"],
)
def test_setup_remove_restores_home_with_the_flag_on_either_side(tmp_path, remove):
    home = fixture_home(tmp_path)
    before = snapshot(home)

    added = run_kb(home, "setup", "codex")
    removed = run_kb(home, *remove)

    assert added.returncode == 0, added.stdout + added.stderr
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert snapshot(home) == before


APPROVED_TOOLS = {
    "kb_list_convention_templates",
    "kb_prepare_conventions",
    "kb_prepare_document_move",
    "kb_get_document_type",
    "kb_list_audiences",
    "kb_prepare_import",
    "kb_list_edits",
    "kb_record_edit",
    "kb_prepare_document_types",
    "kbp_validate",
    "kbp_self_check",
    "kbp_version",
    "kbp_mint",
    "kbp_inspect",
    "kbp_explore",
    "kbp_kinds",
    "kbp_card",
}
NAMED_VERBS = {
    "kb_list_convention_templates": "List",
    "kb_prepare_conventions": "Prepare",
    "kb_prepare_document_move": "Prepare",
    "kb_get_document_type": "Get",
    "kb_list_audiences": "List",
    "kb_prepare_import": "Prepare",
    "kb_list_edits": "List",
    "kb_record_edit": "Record",
    "kb_prepare_document_types": "Prepare",
    "kbp_validate": "Validate",
}
VERBS = {
    "Build",
    "Check",
    "Create",
    "Describe",
    "Explain",
    "Explore",
    "Find",
    "Generate",
    "Get",
    "Inspect",
    "List",
    "Mint",
    "Prepare",
    "Print",
    "Read",
    "Record",
    "Show",
    "Split",
    "Validate",
    "Write",
}
QUESTION_WORDS = {"what", "who", "which", "where", "why", "how", "when"}


@pytest.fixture(scope="module")
def server(tmp_path_factory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("server")

    async def steps(client):
        tools = (await client.list_tools()).tools
        return {
            "tools": {listed.name: listed for listed in tools},
            "instructions": client.instructions,
        }

    return session(kb_mcp(root), steps)


def tool(server: dict[str, Any], name: str) -> Any:
    assert name in server["tools"], sorted(server["tools"])
    return server["tools"][name]


def test_mcp_lists_the_approved_tool_names(server):
    assert set(server["tools"]) == APPROVED_TOOLS
    assert (
        tool(server, "kb_list_convention_templates").title
        == "List convention templates"
    )
    assert (
        tool(server, "kb_prepare_conventions").title
        == "Prepare naming and filing conventions"
    )
    assert tool(server, "kb_prepare_document_move").title == "Prepare a document move"


def test_mcp_tool_titles_are_a_verb_and_a_noun(server):
    for name, listed in server["tools"].items():
        title = listed.title or ""
        words = title.split()
        assert len(words) >= 2, (name, title)
        assert not title.endswith("?"), (name, title)
        assert words[0].lower() not in QUESTION_WORDS, (name, title)
        assert words[0] == NAMED_VERBS.get(name, words[0]), (name, title)
        assert words[0] in VERBS, (name, title)
    assert tool(server, "kb_get_document_type").title == "Get the document type"


def test_mcp_tool_descriptions_open_with_the_verb_of_the_action(server):
    for name, listed in server["tools"].items():
        first = (listed.description or "").split()[0]
        assert first == NAMED_VERBS.get(name, first), (name, listed.description)
        assert first in VERBS, (name, listed.description)


def test_the_document_type_tool_takes_role_in_place_of_hat(server):
    arguments = tool(server, "kb_get_document_type").input_schema["properties"]

    assert "role" in arguments
    assert "hat" not in arguments


def enum_values(schema: dict[str, Any], node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        if "$ref" in node:
            found |= enum_values(schema, schema["$defs"][node["$ref"].split("/")[-1]])
        found |= set(node.get("enum", []))
        if "const" in node:
            found.add(node["const"])
        for value in node.values():
            found |= enum_values(schema, value)
    elif isinstance(node, list):
        for value in node:
            found |= enum_values(schema, value)
    return found


@pytest.mark.parametrize("name", ["kb_prepare_document_types", "kb_record_edit"])
def test_basis_is_request_instruction_or_accepted_change(server, name):
    schema = tool(server, name).input_schema
    basis = schema["properties"]["allowed_by"]

    assert enum_values(schema, basis) == {"request", "instruction", "accepted_change"}


def descriptions(node: Any) -> list[str]:
    found = []
    if isinstance(node, dict):
        if isinstance(node.get("description"), str):
            found.append(node["description"])
        for value in node.values():
            found += descriptions(value)
    elif isinstance(node, list):
        for value in node:
            found += descriptions(value)
    return found


@pytest.mark.parametrize("name", ["kb_prepare_document_types", "kb_get_document_type"])
def test_tools_reading_the_document_types_file_name_its_path(server, name):
    listed = tool(server, name)
    text = " ".join([listed.description or "", *descriptions(listed.input_schema)])

    assert DOCUMENT_TYPES in text, text


def versions() -> dict[str, str]:
    return {
        universe: header((BUNDLED / universe / "universe.kbp.yaml").read_text())[
            "version"
        ]
        for universe in (CODEBASE, PRODUCT)
    }


def old_record() -> str:
    """Include every legacy made and basis value to test migration."""
    version = versions()
    return f"""\
# The fit record: which universe spec and document type each file of this knowledge base is.
# Your agent keeps the record through knowledge-mcp as files are created, moved and deleted.
# A person's correction wins over any later fit by the agent.
schema: knowledge-mcp/fit-record/1
files:
  docs/adr/0001-use-dolt.md:
    universe_spec: {PRODUCT}
    version: '{version[PRODUCT]}'
    kind: decision-record
    made: fit
    allowed_by:
      basis: change_row
      text: Record ADRs as decision records.
      location: docs/changes.md
    time: '2026-10-10T09:17:30.500Z'
  docs/product/pricing.md:
    universe_spec: {PRODUCT}
    version: '{version[PRODUCT]}'
    kind: design-doc
    audience:
      value: the product lead
      status: confirmed
    made: correction
    allowed_by:
      basis: request
      text: Pricing is a design doc for the product lead.
    time: '2026-10-10T09:16:40.003Z'
  docs/rfcs/0042-cache.md:
    universe_spec: {CODEBASE}
    version: '{version[CODEBASE]}'
    kind: design-proposal
    made: fit
    allowed_by:
      basis: line
      text: Keep the fit record in .knowledge-bus/plugins/knowledge-mcp/ up to date as you work.
      location: AGENTS.md
    fingerprint: sha256:4f2a6c1e0d9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f
    time: '2026-10-10T09:15:02.118Z'
  vendor-quote.md:
    no_fit: true
    made: fit
    allowed_by:
      basis: request
      text: Record what each file in docs/ is.
    time: '2026-10-10T09:15:02.118Z'
"""


def migrated_entries() -> dict[str, dict[str, Any]]:
    version = versions()
    return {
        "docs/adr/0001-use-dolt.md": {
            "universe_spec": PRODUCT,
            "version": version[PRODUCT],
            "document_type": "decision-record",
            "set_by": "agent",
            "allowed_by": {
                "basis": "accepted_change",
                "text": "Record ADRs as decision records.",
                "location": "docs/changes.md",
            },
            "time": "2026-10-10T09:17:30.500Z",
        },
        "docs/product/pricing.md": {
            "universe_spec": PRODUCT,
            "version": version[PRODUCT],
            "document_type": "design-doc",
            "audience": {"value": "the product lead", "status": "confirmed"},
            "set_by": "person",
            "allowed_by": {
                "basis": "request",
                "text": "Pricing is a design doc for the product lead.",
            },
            "time": "2026-10-10T09:16:40.003Z",
        },
        RFC: {
            "universe_spec": CODEBASE,
            "version": version[CODEBASE],
            "document_type": "design-proposal",
            "set_by": "agent",
            "allowed_by": {
                "basis": "instruction",
                "text": (
                    "Keep the fit record in .knowledge-bus/plugins/knowledge-mcp/ up to date "
                    "as you work."
                ),
                "location": "AGENTS.md",
            },
            "fingerprint": (
                "sha256:4f2a6c1e0d9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f"
            ),
            "time": "2026-10-10T09:15:02.118Z",
        },
        "vendor-quote.md": {
            "no_document_type": True,
            "set_by": "agent",
            "allowed_by": {
                "basis": "request",
                "text": "Record what each file in docs/ is.",
            },
            "time": "2026-10-10T09:15:02.118Z",
        },
    }


NO_DOCUMENT_TYPE = {
    "no_document_type": True,
    "set_by": "person",
    "allowed_by": {"basis": "request", "text": "The cache RFC has no document type."},
    "time": "2026-10-11T09:15:02.118Z",
}


def design_proposal() -> dict[str, Any]:
    return {
        "universe_spec": CODEBASE,
        "version": versions()[CODEBASE],
        "document_type": "design-proposal",
        "set_by": "person",
        "allowed_by": {
            "basis": "request",
            "text": "The cache RFC is a design proposal.",
        },
        "time": "2026-10-11T09:16:02.118Z",
    }


def document_types_file(path: str, entry: dict[str, Any]) -> str:
    return yaml.safe_dump(
        {"schema": "knowledge-mcp/document-types/1", "files": {path: entry}},
        sort_keys=False,
    )


def recorded(answer: dict[str, Any]) -> dict[str, Any]:
    assert answer.get("recorded"), answer
    return answer["recorded"]["entry"]


@pytest.fixture(scope="module")
def migration(tmp_path_factory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("migration")
    base = KnowledgeBase(None)
    base.add_universe_specs("", [CODEBASE, PRODUCT])
    folders = Harness(base).universe_specs()
    basis = {
        "allowed_by": {
            "basis": "request",
            "text": "Keep the document types of this knowledge base up to date.",
        }
    }

    async def call(client, text):
        result = await client.call_tool(
            "kb_prepare_document_types",
            {
                "location": base.location,
                "record": text,
                "knowledge_bus_folders": folders,
                **basis,
            },
        )
        if result.is_error:
            return {"error": texts(result)}
        return json.loads(texts(result)[0])

    async def steps(client):
        first = await call(client, old_record())
        again = await call(client, first["record"]) if first.get("record") else None
        return {"first": first, "again": again}

    return session(kb_mcp(root), steps)


def test_an_old_record_comes_back_as_document_types_content(migration):
    assert "error" not in migration["first"], migration["first"]
    text = migration["first"]["record"]

    assert text, migration["first"]
    data = yaml.safe_load(text)
    assert data["schema"] == "knowledge-mcp/document-types/1"
    assert data["files"] == migrated_entries()


def test_document_types_content_sent_back_reads_unchanged(migration):
    again = migration["again"]

    assert again is not None, migration["first"]
    assert "error" not in again, again
    assert again["record"] is None, again


def test_the_document_type_tool_answers_from_an_old_record_text(tmp_path):
    root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE, PRODUCT]})
    write(root, RFC, "# Cache\n")

    async def steps(client):
        return await client.call_tool(
            "kb_get_document_type",
            {**type_arguments(root, RFC), "record": old_record()},
        )

    result = session(kb_mcp(tmp_path / "server"), steps)

    assert not result.is_error, texts(result)
    assert recorded(json.loads(texts(result)[0])) == migrated_entries()[RFC]


def test_kb_type_answers_from_an_old_record_yaml_until_a_document_types_file_exists(
    tmp_path,
):
    root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE, PRODUCT]})
    rfc = write(root, RFC, "# Cache\n")
    write(root, OLD_RECORD, old_record())
    home = tmp_path / "home"
    home.mkdir()
    before = snapshot(root)

    from_old = typed(home, str(rfc))
    assert snapshot(root) == before
    write(root, DOCUMENT_TYPES, document_types_file(RFC, NO_DOCUMENT_TYPE))
    from_new = typed(home, str(rfc))

    assert recorded(from_old) == migrated_entries()[RFC]
    assert recorded(from_new)["no_document_type"] is True
    assert recorded(from_new)["set_by"] == "person"


def frontmatter(skill: Path) -> dict[str, Any]:
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n"), skill
    return yaml.safe_load(text.split("---\n")[1])


def test_knowledge_mcp_skills_carry_their_new_names():
    own = sorted(
        path.name
        for path in SKILLS.iterdir()
        if path.is_dir() and path.name not in KNOWLEDGE_BUS_SKILLS
    )

    assert own == NEW_SKILLS
    for name in own:
        front = frontmatter(SKILLS / name)
        assert front["name"] == name
        assert front["description"]


def test_setup_links_the_renamed_skills_and_no_old_skill(tmp_path):
    home = fixture_home(tmp_path)

    done = run_kb(home, "setup", "codex")

    assert done.returncode == 0, done.stdout + done.stderr
    linked = {path.name for path in (home / ".agents/skills").iterdir()}
    assert set(NEW_SKILLS) <= linked
    assert not linked & set(OLD_SKILLS)


def test_import_labels_read_answers_partly_answers_conflicts_and_unmatched(server):
    path = SKILLS / "kb-import-document" / "SKILL.md"
    assert path.is_file(), sorted(folder.name for folder in SKILLS.iterdir())
    skill = path.read_text(encoding="utf-8")
    described = tool(server, "kb_prepare_import").description or ""

    for label in ("answers", "partly answers", "conflicts", "unmatched"):
        assert re.search(rf"(?i)\b{label}\b", skill), label
    for text in (skill, described, server["instructions"] or ""):
        old = re.findall(
            r"(?i)\b(settles|answers in part|contradicts|fits nowhere)\b", text
        )
        assert old == [], old


KBP_LINES = [
    (["kinds"], ["--kinds"]),
    (["kinds", "--format", "markdown"], ["--kinds", "--format", "markdown"]),
    (
        ["card", "readme", "--universe", CODEBASE],
        ["--card", "readme", "--universe", CODEBASE],
    ),
    (
        ["card", "no-such-kind", "--universe", CODEBASE],
        ["--card", "no-such-kind", "--universe", CODEBASE],
    ),
    (["inspect", "--universe", CODEBASE], ["--inspect", "--universe", CODEBASE]),
    (["validate"], ["--validate"]),
    (["validate", ".knowledge-bus"], ["--validate", ".knowledge-bus"]),
    (["self-check"], ["--self-check"]),
]


@pytest.mark.parametrize(
    ("through", "direct"),
    KBP_LINES,
    ids=[" ".join(("kb kbp", *through)) for through, _ in KBP_LINES],
)
def test_kbp_subcommands_run_the_kbp_mode_of_the_same_name(tmp_path, through, direct):
    root = knowledge_base(tmp_path / "kb", {"": [CODEBASE, PRODUCT]})
    home = tmp_path / "home"
    home.mkdir()

    via_kb = run_kb(home, "kbp", *through, cwd=root)
    by_kbp = run_kbp(home, *direct, cwd=root)

    assert (via_kb.stdout, via_kb.stderr, via_kb.returncode) == (
        by_kbp.stdout,
        by_kbp.stderr,
        by_kbp.returncode,
    )


def test_kbp_explore_writes_the_explorer_from_the_bundled_viewer(tmp_path):
    root = knowledge_base(tmp_path / "kb", {"": [CODEBASE]})
    home = tmp_path / "home"
    home.mkdir()
    output = tmp_path / "explorer"

    done = run_kb(
        home,
        "kbp",
        "explore",
        "--universe",
        CODEBASE,
        "--output",
        str(output),
        cwd=root,
    )

    assert done.returncode == 0, done.stdout + done.stderr
    assert (output / "index.html").is_file()


BANNED = {
    '"one command"': r"(?i)\bone command\b",
    '"only command"': r"(?i)\bonly command\b",
    '"fit" as a word': r"(?i)(?<![\w-])fit(?:s|ted|ting)?(?![\w-])",
    '"document guidance"': r"(?i)\bdocument guidance\b",
    '"matching document types"': r"(?i)\bmatching document types\b",
    '"checker" for the validator': r"(?i)\bcheckers?\b",
    '"universe" without "spec"': r"(?i)(?<![\w-])universes?(?![\w-])(?!\s+specs?(?![\w-]))",
}
RETIRED = {
    '"host" for the harness': r"(?i)(?<![\w-])hosts?(?![\w-])",
    '"agent app" for the harness': r"(?i)\bagent apps?\b",
    '"Knowledge-MCP" for knowledge-mcp': r"Knowledge[- ]MCP",
    '"refusal" for an error': r"(?i)\brefusals?\b",
    '"hat" for the role': r"(?i)(?<![\w-])hats?(?![\w-])",
    "--hat": r"--hat(?![\w-])",
    "--top": r"--top(?![\w-])",
    "km-* skill names": r"(?<![\w-])km-(?:write|fit-record|bring-in)(?![\w-])",
    "old tool names": (
        r"(?<![\w-])(?:kb_fit|kb_fit_record|kb_audience|kb_mark|kb_edits|kbp_check)(?![\w-])"
    ),
    "old record fields": r"(?<![\w-])no_fit(?![\w-])|`made`",
    '"standing line" and "change row"': r"(?i)\bstanding lines?\b|\bchange rows?\b",
    '"ground" for the basis': r"(?i)(?<![\w-])grounds?(?![\w-])",
    "old basis values": r"`line`|(?<![\w-])change_row(?![\w-])",
    '"file" for applying an edit': (
        r"(?i)\b(?:file|files|filed|filing)\s+(?:the|an|each|this|that|it|its|accepted)\s+"
        r"(?:\w+\s+)?edits?\b"
    ),
}
KNOWLEDGE_BUS_TERMS = {
    '"Knowledge Bus"': r"Knowledge Bus",
    '"universe"': r"(?i)(?<![\w-])universes?(?![\w-])",
    '"kind"': r"(?i)(?<![\w-])kinds?(?![\w-])",
    '"card"': r"(?i)(?<![\w-])cards?(?![\w-])",
    '"element"': r"(?i)(?<![\w-])elements?(?![\w-])",
    '"frame"': r"(?i)(?<![\w-])frames?(?![\w-])",
    '"actor"': r"(?i)(?<![\w-])actors?(?![\w-])",
    '"strength"': r"(?i)(?<![\w-])strengths?(?![\w-])",
    '"guidance"': r"(?i)(?<![\w-])guidance(?![\w-])",
    '"definitions"': r"(?i)(?<![\w-])definitions?(?![\w-])",
}
README_TERMS = {
    name: KNOWLEDGE_BUS_TERMS[name] for name in ('"Knowledge Bus"', '"universe"')
}
COMMAND_OUTPUTS = [
    ["--version"],
    ["doctor"],
    ["doctor", "--verbose"],
    ["setup", "codex"],
    ["setup", "claude-desktop"],
    ["doctor", "--verbose"],
    ["setup", "--remove", "claude-desktop"],
    ["setup", "--remove", "codex"],
]
ERROR_OUTPUTS = [["setpu"], ["--verison"], ["setup", "nosuch"], ["type"]]


def plain(text: str, places: dict[str, str]) -> str:
    for place, label in places.items():
        text = text.replace(place, label)
    return text


def places(tmp_path: Path) -> dict[str, str]:
    return {
        str(tmp_path): "<tmp>",
        str(MODULE.parent): "<repo>",
        sys.prefix: "<python>",
    }


def command_texts(home: Path, lines: list[list[str]]) -> list[tuple[str, str]]:
    found = []
    for args in lines:
        done = run_kb(home, *args)
        found.append((" ".join(("kb", *args)), done.stdout + done.stderr))
    return found


def help_texts(home: Path, pages: list[tuple[str, ...]]) -> list[tuple[str, str]]:
    return command_texts(home, [[*page, "--help"] for page in pages])


def user_facing(
    tmp_path: Path, server: dict[str, Any], migration: dict[str, Any]
) -> list[tuple[str, str]]:
    home = fixture_home(tmp_path)
    found = help_texts(home, HELP_PAGES)
    found += command_texts(home, COMMAND_OUTPUTS + ERROR_OUTPUTS)
    for name, listed in server["tools"].items():
        found.append((f"{name} title", listed.title or ""))
        found.append((f"{name} description", listed.description or ""))
        for text in descriptions(listed.input_schema):
            found.append((f"{name} argument", text))
    found.append(("server instructions", server["instructions"] or ""))
    for folder in SKILLS.iterdir():
        if folder.is_dir() and folder.name not in KNOWLEDGE_BUS_SKILLS:
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    found.append(
                        (
                            str(path.relative_to(MODULE)),
                            path.read_text(encoding="utf-8"),
                        )
                    )
    for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        data = json.loads((MODULE / manifest).read_text(encoding="utf-8"))
        shown = [data.get("description"), *(data.get("interface") or {}).values()]
        found += [(manifest, text) for text in shown if isinstance(text, str)]
    docs = [
        "README.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "runtime/README.md",
        "contracts/README.md",
    ]
    docs += [
        str(path.relative_to(MODULE.parent))
        for path in (MODULE.parent / "docs").glob("*.md")
    ]
    docs.append("docs/assets/knowledge-mcp-flow.svg")
    for name in docs:
        found.append((name, (MODULE.parent / name).read_text(encoding="utf-8")))
    written = migration["first"].get("record") or ""
    comments = [line for line in written.splitlines() if line.startswith("#")]
    found.append(("document-types comments", "\n".join(comments)))
    return [(source, plain(text, places(tmp_path))) for source, text in found]


PATH_TOKEN = re.compile(r"\S*/\S*|\S*\.(?:ya?ml|md|jsonl?|toml)\b\S*")


def hits(
    found: list[tuple[str, str]], patterns: dict[str, str], *, strip_paths: bool
) -> list[str]:
    report = []
    for source, text in found:
        for number, line in enumerate(text.splitlines(), 1):
            checked = PATH_TOKEN.sub("<path>", line) if strip_paths else line
            for rule, pattern in patterns.items():
                # kbp's `universe` argument and `universe:` YAML key are identifiers, not prose.
                scan = (
                    checked.replace("`universe`", "<kbp-spec-selector>").replace(
                        "`universe:`", "<kbp-yaml-key>"
                    )
                    if rule == '"universe" without "spec"'
                    else checked
                )
                for match in re.finditer(pattern, scan):
                    report.append(f"{source}:{number}: {rule}: {match.group(0)!r}")
    return report


def test_user_facing_text_holds_no_banned_wording(tmp_path, server, migration):
    found = hits(user_facing(tmp_path, server, migration), BANNED, strip_paths=True)

    assert found == [], "\n".join(found)


def test_user_facing_text_holds_no_retired_name(tmp_path, server, migration):
    found = hits(user_facing(tmp_path, server, migration), RETIRED, strip_paths=False)

    assert found == [], "\n".join(found)


def test_help_outside_kbp_doctor_and_readme_use_no_knowledge_bus_terms(tmp_path):
    home = fixture_home(tmp_path)
    pages = [page for page in HELP_PAGES if page[:1] != ("kbp",)]
    shown = help_texts(home, pages) + command_texts(home, COMMAND_OUTPUTS)
    shown = [(source, plain(text, places(tmp_path))) for source, text in shown]
    readme = [("README.md", (MODULE.parent / "README.md").read_text(encoding="utf-8"))]

    shown = [
        (
            source,
            text.replace("universe spec names", "spec names")
            if source == "kb doctor --help"
            else text.replace(
                "universe spec files from parent folders",
                "spec files from parent folders",
            )
            if source == "kb type --help"
            else text,
        )
        for source, text in shown
    ]
    found = hits(shown, KNOWLEDGE_BUS_TERMS, strip_paths=True)
    found += hits(readme, README_TERMS, strip_paths=True)

    assert found == [], "\n".join(found)
