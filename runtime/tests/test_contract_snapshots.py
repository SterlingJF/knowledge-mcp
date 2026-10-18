from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import anyio
import pytest
import yaml
from mcp.client import Client

from knowledge_mcp.main import build_server
from knowledge_mcp.scope import Workspace
from tests.harness import BUNDLED, CODEBASE, MODULE, PRODUCT, header
from tests.test_import_end_to_end import THREAD

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
        return answers

    return steps()


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
                and stem == "document-types-update"
                and top
            )
            changes |= stem == "document-move" and (
                (top and key in ("record", "digest")) or key == "record_digest"
            )
            changes |= key == "digest" and node.get("name") == RECORD
            found[key] = (
                MASKED if changes and value is not None else mask(value, top=False)
            )
        return found

    if stem == "edits" and isinstance(answer, dict):
        return {**answer, "edits": [mask(edit, top=False) for edit in answer["edits"]]}
    return mask(answer, top=True)


def test_pass_samples_are_real_answers(tmp_path, write_snapshots):
    answers = in_process(tmp_path, story)
    if write_snapshots:
        PASS.mkdir(parents=True, exist_ok=True)
        for sample, answer in answers.items():
            text = yaml.safe_dump(answer, sort_keys=False, allow_unicode=True)
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
