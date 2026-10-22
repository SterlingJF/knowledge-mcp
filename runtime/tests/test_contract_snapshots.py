from __future__ import annotations

import json
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

import anyio
import pytest
import yaml
from mcp.client import Client

from knowledge_mcp import document_types as records
from knowledge_mcp.main import build_server
from knowledge_mcp.scope import Workspace
from tests.harness import BUNDLED, CODEBASE, MODULE, PRODUCT, header
from tests.test_document_moves_end_to_end import apply, arguments
from tests.test_folder_filing_end_to_end import six_notes
from tests.test_import_end_to_end import THREAD
from tests.test_proposal_end_to_end import DEMO as PROPOSAL
from tests.test_proposal_end_to_end import REVISED
from tests.test_session_start_filing_end_to_end import (
    configuration,
    five_events,
)
from tests.test_session_start_filing_end_to_end import inputs as session_inputs
from tests.test_team_conventions_end_to_end import CONTRACT
from tests.test_team_conventions_end_to_end import config as team_config
from tests.test_team_conventions_end_to_end import files as team_files
from tests.test_team_conventions_end_to_end import folders as team_folders
from tests.test_template_workflow_end_to_end import folders, proposal

CONTRACTS = MODULE.parent / "contracts" / "extensions" / "mcp" / "v1"
TOOLS_JSON = CONTRACTS / "tools.json"
PASS = CONTRACTS / "conformance" / "pass"
FIX = "run just generate_contract_snapshots"

NOTES = "~/notes"
RFC = "docs/rfcs/0042-cache.md"
MOVED = "docs/rfcs/0042-caching.md"
IDEAS = "ideas.txt"
DESIGN = "DESIGN.md"
MASKED = "<masked>"
RECORD = ".knowledge-bus/plugins/knowledge-mcp/document-types.yaml"
FIXTURES = Path(__file__).parent / "fixtures"
BEFORE = (FIXTURES / "design-before-overview-insertion.md").read_text()
AFTER = (FIXTURES / "design-after-overview-insertion.md").read_text()
INSTRUCTION = {
    "basis": "instruction",
    "text": "Keep the document types in .knowledge-bus/plugins/knowledge-mcp/ up to date as you work.",
    "location": "AGENTS.md",
}


@pytest.fixture
def write_snapshots(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--write-snapshots"))


@pytest.fixture(autouse=True)
def state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate server logs and edit history from the user's state directory."""
    monkeypatch.setenv("KNOWLEDGE_MCP_STATE_DIR", str(tmp_path / "state"))
    return tmp_path / "state"


def in_process(tmp_path: Path, steps: Callable[[Client], Any]) -> Any:
    async def main() -> Any:
        async with Client(
            build_server(Workspace(tmp_path / "work")), mode="legacy"
        ) as client:
            return await steps(client)

    return anyio.run(main)


def listed_tools(tmp_path: Path) -> str:

    async def steps(client: Client) -> list[Any]:
        return (await client.list_tools()).tools

    tools = sorted(in_process(tmp_path, steps), key=lambda tool: tool.name)
    listing = {
        "tools": [
            tool.model_dump(mode="json", by_alias=True, exclude_none=True)
            for tool in tools
        ]
    }
    return json.dumps(listing, indent=2, ensure_ascii=False) + "\n"


def test_tools_json_is_the_listed_tools(tmp_path, write_snapshots):
    listed = listed_tools(tmp_path)
    if write_snapshots:
        TOOLS_JSON.parent.mkdir(parents=True, exist_ok=True)
        TOOLS_JSON.write_text(listed)

    assert TOOLS_JSON.is_file(), f"{TOOLS_JSON} is missing: {FIX}."
    assert TOOLS_JSON.read_text() == listed, f"{TOOLS_JSON} is stale: {FIX}."


def root_folder() -> dict[str, Any]:
    files = []
    for universe_id in (CODEBASE, PRODUCT):
        for source in sorted((BUNDLED / universe_id).glob("*.kbp.yaml")):
            name = source.name.replace("universe.kbp.yaml", "kbp.yaml")
            files.append(
                {"name": f"{universe_id}.{name}", **header(source.read_text())}
            )
    return {"folder": "", "files": files}


def document(path: str) -> dict[str, Any]:
    return {
        "location": f"{NOTES}/{path}",
        "folders": list(Path(path).parts[:-1]),
        "knowledge_bus_folders": [root_folder()],
    }


def story(client: Client) -> Any:

    async def steps() -> dict[str, Any]:
        answers: dict[str, Any] = {}

        async def ask(sample: str, tool: str, arguments: dict[str, Any]) -> Any:
            result = await client.call_tool(tool, arguments)
            answers[sample] = result.structured_content
            return result.structured_content or {}

        await ask(
            "document-type.candidates",
            "kb_get_document_type",
            {**document(RFC), "name": Path(RFC).name},
        )
        await ask(
            "document-type.every-document-type",
            "kb_get_document_type",
            {**document(IDEAS), "name": IDEAS},
        )
        update = {"location": NOTES, "knowledge_bus_folders": [root_folder()]}
        await ask(
            "document-types-update.first-listing",
            "kb_prepare_document_types",
            {**update, "record": "", "listing": [{"path": RFC}, {"path": IDEAS}]},
        )
        saved = await ask(
            "document-types-update.saved",
            "kb_prepare_document_types",
            {
                **update,
                "record": "",
                "allowed_by": INSTRUCTION,
                "entries": [
                    {
                        "path": RFC,
                        "set_by": "agent",
                        "universe_spec": CODEBASE,
                        "document_type": "design-proposal",
                    },
                    {"path": IDEAS, "set_by": "agent", "no_document_type": True},
                ],
            },
        )
        record = saved.get("record") or ""
        answers["document-types.saved"] = yaml.safe_load(record) if record else None
        await ask(
            "document-type.from-the-document-types-file",
            "kb_get_document_type",
            {**document(RFC), "name": Path(RFC).name, "record": record},
        )
        await ask(
            "document-types-update.move",
            "kb_prepare_document_types",
            {
                **update,
                "record": record,
                "allowed_by": INSTRUCTION,
                "changes": [{"change": "moved", "path": MOVED, "old_path": RFC}],
            },
        )
        move = {
            "location": NOTES,
            "old_path": RFC,
            "path": MOVED,
            "listing": [{"path": RFC}],
            "documents": [{"path": RFC, "text": "# Cache\n"}],
            "case_mode": "sensitive",
            "record": record,
            "knowledge_bus_folders": [root_folder()],
            "allowed_by": INSTRUCTION,
        }
        needed = await ask(
            "document-move.texts-needed", "kb_prepare_document_move", move
        )
        await ask(
            "document-move.ready",
            "kb_prepare_document_move",
            {
                **move,
                "searched": True,
                "search": needed["search"],
            },
        )
        empty = await ask(
            "conventions-update.empty",
            "kb_prepare_conventions",
            {"location": NOTES, "conventions": ""},
        )
        answers["conventions.empty"] = {
            "schema": "knowledge-mcp/conventions/1",
            "from_parent": [],
            "conventions": empty["current"],
        }
        convention = {
            "change": "upsert",
            "universe_spec": CODEBASE,
            "document_type": "design-proposal",
            "folder": ["Proposals"],
            "name": {"separator": " ", "parts": [{"part": "content"}]},
            "content": {
                "label": "document title",
                "instruction": "Read the first document heading.",
            },
            "set_by": "person",
        }
        convention_args = {**update, "conventions": "", "changes": [convention]}
        await ask(
            "conventions-update.permission-needed",
            "kb_prepare_conventions",
            convention_args,
        )
        saved_conventions = await ask(
            "conventions-update.saved",
            "kb_prepare_conventions",
            {**convention_args, "allowed_by": INSTRUCTION},
        )
        conventions_text = saved_conventions["record"]
        answers["conventions.saved"] = yaml.safe_load(conventions_text)
        naming = {
            "conventions": conventions_text,
            "filing_values": [
                {
                    "path": RFC,
                    "universe_spec": CODEBASE,
                    "document_type": "design-proposal",
                    "content": "Shared Cache",
                }
            ],
        }
        await ask(
            "document-type.convention",
            "kb_get_document_type",
            {
                **document(RFC),
                "name": Path(RFC).name,
                "record": record,
                "listing": [{"path": RFC}],
                **naming,
            },
        )
        await ask(
            "document-type.convention-values-needed",
            "kb_get_document_type",
            {
                **document(RFC),
                "name": Path(RFC).name,
                "record": record,
                "listing": [{"path": RFC}],
                "conventions": conventions_text,
            },
        )
        await ask(
            "document-types-update.convention",
            "kb_prepare_document_types",
            {
                **update,
                "record": record,
                "listing": [{"path": RFC}, {"path": IDEAS}],
                **naming,
            },
        )
        await ask(
            "conventions-update.removed",
            "kb_prepare_conventions",
            {
                **update,
                "conventions": conventions_text,
                "changes": [
                    {
                        "change": "remove",
                        "universe_spec": CODEBASE,
                        "document_type": "design-proposal",
                    }
                ],
                "allowed_by": INSTRUCTION,
            },
        )
        await ask(
            "audiences.frame",
            "kb_list_audiences",
            {**document(RFC), "document_type": "design-doc"},
        )
        await ask(
            "audiences.actor-only",
            "kb_list_audiences",
            {**document(RFC), "document_type": "design-proposal"},
        )
        await ask(
            "import.thread",
            "kb_prepare_import",
            {
                "location": "pasted in chat",
                "text": THREAD,
                "folders": [],
                "knowledge_bus_folders": [root_folder()],
            },
        )
        await ask(
            "edit.request",
            "kb_record_edit",
            {
                "location": f"{NOTES}/{DESIGN}",
                "allowed_by": {
                    "basis": "request",
                    "text": "Add an Overview section to DESIGN.md.",
                },
                "before": BEFORE,
                "after": AFTER,
            },
        )
        await ask("edits.one-edit", "kb_list_edits", {"location": f"{NOTES}/{DESIGN}"})
        await ask("proposal.demo", "kb_prepare_proposal", PROPOSAL)
        await ask("proposal.revised", "kb_prepare_proposal", REVISED)
        await problem_stories(ask)
        template_catalog = await ask(
            "convention-templates.catalog",
            "kb_list_convention_templates",
            {"location": NOTES},
        )
        template_proposal = partial(proposal, catalog_data=template_catalog)
        daily = template_proposal()
        custom = template_proposal(
            name="atlas-title", kind="knowledge-note", folder=["Atlas (general notes)"]
        )
        project = template_proposal(
            "para",
            "projects-title",
            "project-note",
            ["Projects", {"part": "property", "property": "project"}],
        )
        numbered = template_proposal(
            "johnny-decimal",
            "id-date-title",
            "meeting-note",
            ["10-19 Work", "12 Meetings", "12.03 Product reviews"],
        )
        decision = template_proposal(
            name="atlas-title", kind="decision-record", folder=["Atlas", "Decisions"]
        )
        decision["name"]["parts"].insert(
            0, {"part": "property", "property": "decision_number"}
        )
        for name, changes in [
            ("ace", [daily]),
            ("customized-ace", [custom]),
            ("para", [project]),
            ("johnny-decimal", [numbered]),
            ("mixed", [daily, project, decision]),
        ]:
            result = await client.call_tool(
                "kb_prepare_conventions",
                {
                    "location": NOTES,
                    "conventions": "",
                    "knowledge_bus_folders": folders(),
                    "changes": changes,
                    "allowed_by": INSTRUCTION,
                },
            )
            assert not result.is_error, result.structured_content
            answers["conventions.template-" + name] = yaml.safe_load(
                result.structured_content["record"]
            )
        await team_stories(ask)
        return answers

    return steps()


async def problem_stories(ask):
    await ask(
        "problem.argument-invalid",
        "kb_get_document_type",
        {**document(RFC), "name": Path(RFC).name, "digest": "sha256:" + "1" * 64},
    )
    await ask(
        "problem.document-type-unknown",
        "kb_list_audiences",
        {**document(RFC), "document_type": "no-such-type"},
    )
    await ask(
        "problem.digest-unknown",
        "kb_get_document_type",
        {
            **document(RFC),
            "name": Path(RFC).name,
            "record_digest": "sha256:" + "2" * 64,
        },
    )


async def session_start_stories(ask):
    args = session_inputs()
    args.update(five_events())
    await ask("document-types-update.session-start", "kb_prepare_document_types", args)
    args.pop("filing_values")
    await ask(
        "document-types-update.session-start-values-needed",
        "kb_prepare_document_types",
        args,
    )
    nested = configuration()[0]
    nested["folder"] = "Inbox"
    nested["files"][0]["text"] = nested["files"][0]["text"].replace(
        "session-notes", "other-notes"
    )
    nested["files"][0]["id"] = "other-notes"
    args["knowledge_bus_folders"].append(nested)
    args.pop("entries")
    await ask(
        "document-types-update.session-start-move-conflict",
        "kb_prepare_document_types",
        args,
    )


async def team_stories(ask):
    await batch_stories(ask)
    await session_start_stories(ask)
    for name, folder, inputs in [
        ("company", "", team_files()),
        ("finance", "Finance", team_files()),
        ("engineering", "Engineering", team_files()),
        ("descendant", "Finance/Planning", team_files()),
        ("empty", "Finance", team_files(team_config())),
        (
            "inactive",
            "Engineering",
            [
                dict(folder="", text=team_files()[0]["text"]),
                dict(folder="Engineering", text=""),
            ],
        ),
    ]:
        await ask(
            "folder-conventions." + name,
            "kb_list_conventions",
            dict(
                location=NOTES,
                folder=folder,
                knowledge_bus_folders=team_folders(),
                conventions_files=inputs,
            ),
        )
    await ask(
        "conventions-update.parent-selection",
        "kb_prepare_conventions",
        dict(
            location=NOTES,
            folder="Finance",
            conventions=team_config(),
            conventions_files=[team_files()[0]],
            knowledge_bus_folders=team_folders(),
            from_parent=[dict(universe_spec=CONTRACT[0], document_type=CONTRACT[1])],
            allowed_by=INSTRUCTION,
        ),
    )


def masked(sample: str, answer: Any) -> Any:
    """Ignore generated timestamps, edit IDs and values derived from timestamps during snapshot comparisons."""
    stem = sample.split(".", maxsplit=1)[0]

    def mask(node: Any, top: bool) -> Any:
        if isinstance(node, list):
            return [mask(item, top=False) for item in node]
        if not isinstance(node, dict):
            return node
        found = {}
        for key, value in node.items():
            changes = key == "time"
            changes |= key == "id" and stem == "edit" and top
            changes |= key == "id" and stem == "edits" and not top
            changes |= (
                key in ("record", "digest", "based_on")
                and stem in ("document-types-update", "conventions-update")
                and top
            )
            changes |= stem in ("document-move", "document-moves") and (
                (top and key in ("record", "digest")) or key == "record_digest"
            )
            changes |= key == "digest" and (
                node.get("name")
                in (RECORD, ".knowledge-bus/plugins/knowledge-mcp/conventions.yaml")
                or node.get("file")
                == ".knowledge-bus/plugins/knowledge-mcp/conventions.yaml"
            )
            found[key] = (
                MASKED if changes and value is not None else mask(value, top=False)
            )
        return found

    if stem == "edits" and isinstance(answer, dict):
        return {**answer, "edits": [mask(edit, top=False) for edit in answer["edits"]]}
    return mask(answer, top=True)


class SampleDumper(yaml.SafeDumper):
    pass


def sample_string(dumper, value):
    return dumper.represent_scalar(
        "tag:yaml.org,2002:str", value, style="|" if "\n" in value else None
    )


SampleDumper.add_representer(str, sample_string)


def sample_yaml(answer):
    return yaml.dump(answer, Dumper=SampleDumper, sort_keys=False, allow_unicode=True)


def test_pass_samples_are_real_answers(tmp_path, write_snapshots):
    answers = in_process(tmp_path, story)
    if write_snapshots:
        PASS.mkdir(parents=True, exist_ok=True)
        for sample, answer in answers.items():
            text = sample_yaml(answer)
            (PASS / f"{sample}.yaml").write_text("---\n" + text)

    empty = [sample for sample, answer in answers.items() if answer is None]
    assert not empty, f"no structured content in the answers for {empty}."
    on_disk = {path.name.removesuffix(".yaml") for path in PASS.glob("*.yaml")}
    assert on_disk == set(answers), f"pass samples differ from the story: {FIX}."
    for sample, answer in answers.items():
        written = yaml.safe_load((PASS / f"{sample}.yaml").read_text())
        assert masked(sample, written) == masked(sample, answer), (
            f"{sample} is stale: {FIX}."
        )


def test_move_snapshot_masks_record_time_and_retains_document_digests():
    first = {
        "record": "first timestamp",
        "digest": "first digest",
        "based_on": {
            "record_digest": "first record",
            "listing_digest": "inventory",
            "documents": [{"path": "a.md", "digest": "content"}],
        },
    }
    second = {
        **first,
        "record": "second timestamp",
        "digest": "second digest",
        "based_on": {**first["based_on"], "record_digest": "second record"},
    }
    assert masked("document-move.ready", first) == masked("document-move.ready", second)
    second["based_on"]["documents"] = [{"path": "a.md", "digest": "changed content"}]
    assert masked("document-move.ready", first) != masked("document-move.ready", second)


async def batch_stories(ask):
    docs = {"A.md": "[[B#Heading]]", "B.md": "[[A#^block]]", "Index.md": "[[A]] [[B]]"}
    moves = [("A.md", "Decisions/Alpha.md"), ("B.md", "Decisions/Beta.md")]
    args = arguments(docs, moves)
    before_record = args["record"]
    needed = await ask("document-moves.texts-needed", "kb_prepare_document_moves", args)
    args.update(searched=True, search=needed["search"])
    await ask("document-moves.permission-needed", "kb_prepare_document_moves", args)
    ready = await ask(
        "document-moves.linked-notes",
        "kb_prepare_document_moves",
        {**args, "allowed_by": INSTRUCTION},
    )
    after = apply(docs, ready)
    inverse = arguments(after, [(b, a) for a, b in moves], allowed_by=INSTRUCTION)
    needed = await ask(
        "document-moves.undo-texts-needed", "kb_prepare_document_moves", inverse
    )
    await ask(
        "document-moves.undo",
        "kb_prepare_document_moves",
        {**inverse, "searched": True, "search": needed["search"]},
    )
    for name, mapping in [
        ("swap", [("A.md", "B.md"), ("B.md", "A.md")]),
        ("blocked", [("A.md", "B.md")]),
    ]:
        args = arguments(docs, mapping, allowed_by=INSTRUCTION)
        result = await ask(
            "document-moves." + name + "-texts-needed",
            "kb_prepare_document_moves",
            args,
        )
        await ask(
            "document-moves." + name,
            "kb_prepare_document_moves",
            {**args, "searched": True, "search": result["search"]},
        )
    names, files, conventions, values = six_notes()
    await ask(
        "document-types-update.folder-review",
        "kb_prepare_document_types",
        dict(
            location=NOTES,
            record=records.dump(files),
            listing=[dict(path=p) for p in [*files, names[-1]]],
            filing_review=dict(folder="Inbox"),
            conventions=conventions,
            filing_values=values,
        ),
    )
    for index, write in enumerate(ready["writes"], 1):
        await ask(
            "edit.grouped-move-" + str(index),
            "kb_record_edit",
            dict(
                location="batch-vault",
                allowed_by=INSTRUCTION,
                before=docs[write["old_path"]],
                after=write["text"],
                whole_file=True,
                operation=dict(
                    id="batch-example",
                    index=index,
                    count=len(ready["writes"]) + 1,
                    old_path=write["old_path"],
                    path=write["path"],
                ),
            ),
        )
    await ask(
        "edit.grouped-document-types",
        "kb_record_edit",
        dict(
            location="batch-vault",
            allowed_by=INSTRUCTION,
            before=before_record,
            after=ready["record"],
            whole_file=True,
            operation=dict(
                id="batch-example",
                index=len(ready["writes"]) + 1,
                count=len(ready["writes"]) + 1,
                old_path=RECORD,
                path=RECORD,
            ),
        ),
    )
    await ask("edits.grouped-moves", "kb_list_edits", dict(location="batch-vault"))


def test_generated_multiline_sample_keeps_yaml_line_lengths():
    text = "    fingerprint: sha256:" + "a" * 64 + "\n"
    sample = {"after": "# Saved document types.\n" + text}
    rendered = sample_yaml(sample)
    assert yaml.safe_load(rendered) == sample
    assert max(map(len, rendered.splitlines())) <= 120
    assert "after: |" in rendered
