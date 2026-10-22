from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import anyio
import pytest
import yaml
from kbp_conform.card import build_card, render_card
from mcp.client import Client

from knowledge_mcp import bundled
from knowledge_mcp.main import build_server
from knowledge_mcp.models import ScopeRequest
from knowledge_mcp.scope import Workspace
from tests.harness import (
    BUNDLED,
    CODEBASE,
    PRODUCT,
    checked,
    knowledge_base,
    scope_arguments,
    server_parameters,
    session,
    texts,
    write,
)
from tests.kb_cli import KBP, kbp_env
from tests.test_edits import ask, digest
from tests.test_kb_end_to_end import snapshot

RFC = "docs/rfcs/0042-cache.md"
RECORD = ".knowledge-bus/plugins/knowledge-mcp/record.yaml"


@pytest.fixture(autouse=True)
def state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return tmp_path / "state"


@pytest.fixture
def codebase(tmp_path: Path) -> Path:
    root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE, PRODUCT]})
    write(root, RFC, "# Cache\n")
    return root


def in_process(workspace: Workspace, calls: list[tuple[str, dict[str, Any]]]) -> list:
    async def main():
        async with Client(build_server(workspace), mode="legacy") as client:
            return [
                await client.call_tool(name, arguments) for name, arguments in calls
            ]

    return anyio.run(main)


def printed(
    workspace: Workspace, arguments: dict[str, Any], argv: list[str], **env: str
):
    request = ScopeRequest.model_validate(
        {k: arguments[k] for k in ("folders", "knowledge_bus_folders")}
    )
    with workspace.rebuilt(request) as rebuilt:
        done = subprocess.run(
            [str(KBP), *argv],
            cwd=rebuilt.cwd,
            capture_output=True,
            text=True,
            check=False,
            env=kbp_env(**env),
        )
    return done.stdout, done.stderr, done.returncode


def streams(result) -> tuple[str, str, int]:
    out = "".join(
        b.text for b in result.content if (b.meta or {}).get("stream") == "stdout"
    )
    err = "".join(
        b.text for b in result.content if (b.meta or {}).get("stream") == "stderr"
    )
    return out, err, result.meta["exit_code"]


CASES = [
    ("kbp_validate", {}, [], True),
    ("kbp_inspect", {"universe": PRODUCT}, ["--inspect", "--universe", PRODUCT], False),
    ("kbp_kinds", {}, ["--kinds"], False),
    ("kbp_kinds", {"format": "markdown"}, ["--kinds", "--format", "markdown"], False),
    (
        "kbp_card",
        {"kind": "design-proposal", "universe": CODEBASE},
        ["--card", "design-proposal", "--universe", CODEBASE, "--format", "markdown"],
        False,
    ),
    *[
        (
            "kbp_card",
            {"kind": "design-proposal", "universe": CODEBASE, "format": format},
            [
                "--card",
                "design-proposal",
                "--universe",
                CODEBASE,
                "--format",
                format or "markdown",
            ],
            False,
        )
        for format in ("json", "markdown", None)
    ],
    (
        "kbp_card",
        {"kind": "no-such-type", "universe": CODEBASE},
        ["--card", "no-such-type", "--universe", CODEBASE, "--format", "markdown"],
        False,
    ),
]


@pytest.mark.parametrize("case", CASES)
def test_kbp_tool_matches_cli_streams_and_exit_status(codebase, tmp_path, case):
    tool, extra, argv, send_text = case
    workspace = Workspace(tmp_path / "work")
    arguments = {
        **scope_arguments(codebase, RFC, send_text=send_text),
        "location": str(codebase / RFC),
        **extra,
    }

    [result] = in_process(workspace, [(tool, arguments)])

    scope = {key: arguments[key] for key in ("folders", "knowledge_bus_folders")}
    assert streams(result) == printed(workspace, scope, argv)
    assert result.is_error is (result.meta["exit_code"] != 0)


def test_card_json_preserves_upstream_guidance_ids_and_source_receipts(tmp_path):
    root = knowledge_base(tmp_path / "kb", {"": [CODEBASE]})
    arguments = {
        **scope_arguments(root, "DESIGN.md", send_text=True),
        "location": str(root / "DESIGN.md"),
        "kind": "design-proposal",
        "universe": CODEBASE,
        "format": "json",
    }
    files = arguments["knowledge_bus_folders"][0]["files"]
    documents = [yaml.safe_load(file["text"]) for file in files]
    universe = next(doc for doc in documents if "universe" in doc)
    guidance = next(doc for doc in documents if "guidance" in doc)
    expected = build_card(universe, guidance, arguments["kind"])
    workspace = Workspace(tmp_path / "work")

    [result, markdown] = in_process(
        workspace,
        [("kbp_card", arguments), ("kbp_card", {**arguments, "format": "markdown"})],
    )

    assert not result.is_error
    assert json.loads(streams(result)[0]) == expected
    assert streams(markdown) == (render_card(expected), "", 0)
    assert expected["sections"] and expected["conditions"]
    assert any(section["guidance"] for section in expected["sections"])
    note = result.structured_content["note"]
    assert note == {
        "received": [
            {"name": file["name"], "digest": digest(file["text"])} for file in files
        ]
    }
    reused = json.loads(json.dumps(arguments))
    for file, receipt in zip(
        reused["knowledge_bus_folders"][0]["files"], note["received"], strict=True
    ):
        del file["text"]
        file["digest"] = receipt["digest"]
    [again] = in_process(workspace, [("kbp_card", reused)])
    assert streams(again) == streams(result)


def test_card_json_reports_bundled_source_files(codebase, tmp_path):
    arguments = {
        **scope_arguments(codebase, RFC),
        "location": str(codebase / RFC),
        "kind": "design-proposal",
        "universe": CODEBASE,
        "format": "json",
    }
    [result] = in_process(Workspace(tmp_path / "work"), [("kbp_card", arguments)])
    assert not result.is_error
    assert result.structured_content["note"] == {
        "source": bundled.label(),
        "bundled": [
            file["name"]
            for folder in arguments["knowledge_bus_folders"]
            for file in folder["files"]
        ],
    }


def test_mint_matches_cli_code_shape_and_count(codebase, tmp_path):
    workspace = Workspace(tmp_path / "work")
    arguments = {
        **scope_arguments(codebase, RFC),
        "location": str(codebase / RFC),
        "kind": "element",
        "count": 3,
    }

    [result] = in_process(workspace, [("kbp_mint", arguments)])

    scope = {key: arguments[key] for key in ("folders", "knowledge_bus_folders")}
    out, err, code = streams(result)
    kbp_out, kbp_err, kbp_code = printed(workspace, scope, ["--mint", "element", "3"])
    # Random codes prevent comparisons of exact output.
    shape = [(line[0], len(line)) for line in out.splitlines()]
    assert shape == [(line[0], len(line)) for line in kbp_out.splitlines()]
    assert len(shape) == 3
    assert (err, code) == (kbp_err, kbp_code) == ("", 0)


def test_version_and_self_check_match_cli_output(tmp_path):
    workspace = Workspace(tmp_path / "work")
    version, self_check = in_process(
        workspace, [("kbp_version", {}), ("kbp_self_check", {})]
    )

    for result, argv in ((version, ["--version"]), (self_check, ["--self-check"])):
        done = subprocess.run(
            [str(KBP), *argv], capture_output=True, text=True, check=False
        )
        assert streams(result) == (done.stdout, done.stderr, done.returncode)


def test_explore_writes_index_and_returns_explorer_path(codebase, state):
    arguments = {
        **scope_arguments(codebase, RFC),
        "location": str(codebase / RFC),
        "universe": PRODUCT,
    }

    async def steps(client):
        return await client.call_tool("kbp_explore", arguments)

    result = session(server_parameters(state), steps)

    assert not result.is_error, texts(result)
    out, _, code = streams(result)
    assert code == 0
    receipt = json.loads(out)
    assert receipt["universe"]["id"] == PRODUCT
    [written] = list((state / "knowledge-mcp" / "explorer").iterdir())
    assert (written / "index.html").is_file()
    assert str(written) in texts(result)[-1]


def test_validate_rejects_bundled_copies(codebase, tmp_path):
    workspace = Workspace(tmp_path / "work")
    arguments = {**scope_arguments(codebase, RFC), "location": str(codebase / RFC)}

    [result] = in_process(workspace, [("kbp_validate", arguments)])

    assert result.is_error
    assert "Send the text" in texts(result)[0]


def test_check_runs_on_text_sent_earlier_by_digest(codebase, tmp_path):
    workspace = Workspace(tmp_path / "work")
    first = {
        **scope_arguments(codebase, RFC, send_text=True),
        "location": str(codebase / RFC),
    }
    [checked] = in_process(workspace, [("kbp_validate", first)])
    digests = json.loads(texts(checked)[-1])["received"]
    by_name = {item["name"]: item["digest"] for item in digests}
    second = json.loads(json.dumps(first))
    for scope in second["knowledge_bus_folders"]:
        for entry in scope["files"]:
            del entry["text"]
            entry["digest"] = by_name[entry["name"]]

    [again] = in_process(workspace, [("kbp_validate", second)])

    assert streams(again) == streams(checked)
    assert again.meta["exit_code"] == 0


def test_unknown_spec_digest_returns_text_request(codebase, tmp_path):
    workspace = Workspace(tmp_path / "work")
    arguments = {**scope_arguments(codebase, RFC), "location": str(codebase / RFC)}
    arguments["knowledge_bus_folders"][0]["files"][0] |= {
        "id": "mine",
        "digest": "sha256:00",
    }

    [result] = in_process(workspace, [("kbp_kinds", arguments)])

    assert result.is_error
    assert "Send the text of" in texts(result)[0]


def test_validate_ignores_document_types_plugin_directory(codebase, tmp_path):
    workspace = Workspace(tmp_path / "work")

    def check_both() -> tuple[tuple[str, str, int], tuple[str, str, int]]:
        arguments = {
            **scope_arguments(codebase, RFC, send_text=True),
            "location": str(codebase / RFC),
        }
        [result] = in_process(workspace, [("kbp_validate", arguments)])
        done = subprocess.run(
            [str(KBP)],
            cwd=codebase / "docs" / "rfcs",
            capture_output=True,
            text=True,
            check=False,
            env=kbp_env(),
        )
        return streams(result), (done.stdout, done.stderr, done.returncode)

    without = check_both()
    write(codebase, RECORD, "schema: knowledge-mcp/document-types/1\nfiles: {}\n")
    with_record = check_both()

    assert with_record == without
    assert without[0][2] == 0 and without[1][2] == 0


def test_validate_document_types_only_scope_preserves_error(tmp_path):
    root = tmp_path / "plain"
    write(root, RFC, "# Cache\n")
    workspace = Workspace(tmp_path / "work")

    def check() -> tuple[bool, list[str]]:
        arguments = {**scope_arguments(root, RFC), "location": str(root / RFC)}
        [result] = in_process(workspace, [("kbp_validate", arguments)])
        return result.is_error, texts(result)

    without = check()
    write(root, RECORD, "schema: knowledge-mcp/document-types/1\nfiles: {}\n")
    assert scope_arguments(root, RFC)["knowledge_bus_folders"] == [
        {"folder": "", "files": []}
    ]
    with_record = check()

    assert with_record[0] and with_record == without


def test_missing_parent_definitions_preserve_kbp_error(
    tmp_path,
):
    root = tmp_path / "plain"
    write(root, RECORD, "schema: knowledge-mcp/document-types/1\nfiles: {}\n")
    write(root, "team/.knowledge-bus/workspace.yaml", f"from_parent:\n  - {PRODUCT}\n")
    document = "team/notes/pricing.md"
    write(root, document, "# Pricing\n")
    workspace = Workspace(tmp_path / "work")
    scope = scope_arguments(root, document)
    assert scope["knowledge_bus_folders"] == [
        {"folder": "", "files": []},
        {
            "folder": "team",
            "files": [],
            "workspace_yaml": f"from_parent:\n  - {PRODUCT}\n",
        },
    ]
    located = {**scope, "location": str(root / document)}

    fitted, listed = in_process(
        workspace,
        [
            ("kb_get_document_type", {**located, "name": "pricing.md"}),
            ("kbp_kinds", located),
        ],
    )

    done = subprocess.run(
        [str(KBP), "--kinds"],
        cwd=root / "team" / "notes",
        capture_output=True,
        text=True,
        check=False,
        env=kbp_env(),
    )
    direct = (done.stdout, done.stderr, done.returncode)
    assert done.returncode == 1
    assert json.loads(done.stderr)["schema"] == "knowledge-bus/inspection-error/1"
    assert "from_parent" in json.loads(done.stderr)["message"]
    assert fitted.is_error and listed.is_error
    assert streams(fitted) == direct
    assert streams(listed) == direct


def release_host_apply(plan, evidence, *, accepted):
    """QA host writer used by these physical plans; no server persistence API."""
    if not accepted:
        return "declined"
    if any(path.read_bytes() != before for path, before in evidence.items()):
        return "stale"
    if any(path.read_bytes() != before for path, before, _ in plan):
        return "stale"
    if all(before == after for _, before, after in plan):
        return "no-change"
    for path, _, after in plan:
        path.write_bytes(after)
    return "applied"


def release_bytes(data):
    return yaml.safe_dump(data, sort_keys=False).replace("\n", "\r\n").encode()


def release_card(claim):
    # Independent expected Markdown, not an earlier response or planner rendering.
    return (
        "# Release guide\n\n"
        "Document type in the Product development universe spec (product-development 0.10).\n\n"
        "- Helps you: verify a fictional release and retain failure evidence\n"
        "- Who uses it: new maintainer\n"
        "- When it is used: after installing a candidate\n"
        "- No document needed when time-separation is none and reversibility is reversible. "
        "Depends on: Who has to reconstruct this reasoning without the author present? "
        "(time-separation); Can this step be undone, and at what cost? (reversibility)\n\n"
        "## How to write it well\n\n"
        f"- Convention: {claim}\n\n"
        "## Sections\n\n### Release verification\n\n"
        "Answers: Which installed version was verified and what evidence was retained?\n"
        "Required.\n"
    )


@pytest.mark.parametrize("adapt", [False, True], ids=["create", "adapt"])
def test_saved_release_instructions_reload_for_second_guide(tmp_path, adapt):  # noqa: PLR0915 - one physical save/reload journey.
    """Staged physical coverage; human usefulness and approvals remain untested."""
    root = knowledge_base(tmp_path / "release", {"": [PRODUCT]})
    spec_path = root / ".knowledge-bus" / f"{PRODUCT}.kbp.yaml"
    guidance_path = root / ".knowledge-bus" / f"{PRODUCT}.type-guidance.kbp.yaml"
    first = write(root, "guides/release-one.md", "")
    second = write(root, "guides/release-two.md", "")
    first.write_bytes(b"# Release one\r\nCandidate: QA-1.\r\n")
    second.write_bytes(b"# Release two\r\nCandidate: QA-2.\r\n")
    source = write(root, "sources/example.md", "")
    source.write_bytes(
        b"Fictional QA example: verify installed version; retain evidence on failure.\r\n"
    )
    questions = write(root, "sources/questions.md", "")
    questions.write_bytes(
        b"How do I verify the installed result? What if verification fails?\r\n"
    )
    evolution = write(root, ".knowledge-bus/evolve-log.md", "")
    prior = b"# QA history\r\nPrior refusal: provider mandate lacks evidence.\r\n"
    evolution.write_bytes(prior)
    state = tmp_path / "physical-state"

    def located():
        return {
            **scope_arguments(root, "guides/release-two.md", send_text=True),
            "location": str(second),
        }

    originals = snapshot(root)
    minted, element = ask(
        state,
        ("kbp_mint", {**located(), "kind": "artifact", "count": 1}),
        ("kbp_mint", {**located(), "kind": "element", "count": 1}),
    )
    assert streams(minted)[1:] == streams(element)[1:] == ("", 0)
    assert snapshot(root) == originals  # These two mint calls leave host files intact.
    code, element_code = streams(minted)[0].strip(), streams(element)[0].strip()
    data = yaml.safe_load(spec_path.read_bytes())
    data["universe"]["version"] = "0.10"
    data["elements"].append(
        {
            "id": "release-verification",
            "code": element_code,
            "question": "Which installed version was verified and what evidence was retained?",
            "phase": "validation",
            "cardinality": "per-effort",
        }
    )
    data["artifacts"].append(
        {
            "id": "release-guide",
            "code": code,
            "enablement": {
                "action": "verify a fictional release and retain failure evidence",
                "actor": "new maintainer",
                "timing": "after installing a candidate",
            },
            "alias": {"kind": "none", "reason": "no-aligned-form"},
            "composition": {"core": ["release-verification"], "situational": []},
        }
    )
    guidance = yaml.safe_load(
        (BUNDLED / PRODUCT / "type-guidance.kbp.yaml").read_bytes()
    )
    guidance["guidance"]["version"] = "0.9"
    guidance["sources"]["qa-example"] = {
        "cite": "Fictional QA example: sources/example.md",
        "url": "https://example.invalid/qa-release",
        "checked": "2026-10-20",
    }
    old_claim = "Omit installed-version verification and discard failure evidence."
    claim = "Verify the installed version; retain evidence when verification fails."
    guidance["artifacts"]["release-guide"] = [
        {
            "kind": "convention",
            "source": "qa-example",
            "claim": old_claim if adapt else claim,
        }
    ]
    # Fixture setup, not a model decision: the adapt instruction is registered and consumed.
    spec_path.write_bytes(release_bytes(data))
    if adapt:
        guidance_path.write_bytes(release_bytes(guidance))
        [initial] = ask(
            state,
            ("kbp_card", {**located(), "universe": PRODUCT, "kind": "release-guide"}),
        )
        assert streams(initial) == (release_card(old_claim), "", 0)
    before_guidance = guidance_path.read_bytes()
    guidance["artifacts"]["release-guide"][0]["claim"] = claim
    plan = [
        (guidance_path, before_guidance, release_bytes(guidance)),
        (
            evolution,
            prior,
            prior
            + b"QA applied fixture row: example.md; questions.md; release-guide.\r\n",
        ),
    ]
    assert (
        release_host_apply(
            plan,
            {source: source.read_bytes(), questions: questions.read_bytes()},
            accepted=True,
        )
        == "applied"
    )
    assert guidance_path.read_bytes() != before_guidance
    saved = snapshot(root)
    # Broken reference refusal must leave all physical instructions/history/documents intact.
    valid_guidance = guidance_path.read_bytes()
    guidance["artifacts"]["release-guide"][0]["source"] = "missing-qa-source"
    guidance_path.write_bytes(release_bytes(guidance))
    invalid = snapshot(root)
    [refused] = ask(state, ("kbp_validate", located()))
    assert streams(refused)[2] != 0
    assert "missing-qa-source" in "".join(texts(refused))
    assert snapshot(root) == invalid
    guidance_path.write_bytes(valid_guidance)
    # ask() opens a new native SDK/server session; physical saved text is sent anew.
    validated, inspected, card = ask(
        state,
        ("kbp_validate", located()),
        ("kbp_inspect", {**located(), "universe": PRODUCT}),
        ("kbp_card", {**located(), "universe": PRODUCT, "kind": "release-guide"}),
    )
    assert streams(validated)[2] == streams(inspected)[2] == 0
    assert streams(card) == (release_card(claim), "", 0)
    model = json.loads(streams(inspected)[0])
    # Full independently specified definitions, including every composition/enablement field.
    expected_artifact = {
        "id": "release-guide",
        "code": code,
        "alias": {"kind": "none", "reason": "no-aligned-form"},
        "enablement": {
            "actor": "new maintainer",
            "timing": "after installing a candidate",
            "action": "verify a fictional release and retain failure evidence",
        },
        "composition": {"core": ["release-verification"], "situational": []},
    }
    expected_element = {
        "id": "release-verification",
        "code": element_code,
        "phase": "validation",
        "cardinality": "per-effort",
        "question": "Which installed version was verified and what evidence was retained?",
    }
    expected_source = yaml.safe_load(
        (BUNDLED / PRODUCT / "universe.kbp.yaml").read_bytes()
    )
    expected_source["universe"]["version"] = "0.10"
    expected_source["artifacts"].append(expected_artifact)
    expected_source["elements"].append(expected_element)
    assert model["source"] == expected_source
    assert model["universe"] == expected_source["universe"]
    for kind, definition, index in [
        ("artifact", expected_artifact, len(expected_source["artifacts"]) - 1),
        ("element", expected_element, len(expected_source["elements"]) - 1),
    ]:
        entity = next(
            x for x in model["entities"] if x["id"] == f"{kind}:{definition['id']}"
        )
        assert entity["raw"] == definition
        assert entity["sourceId"] == definition["id"]
        assert entity["sourcePath"] == f"{kind}s[{index}]"
    entries = [
        x
        for x in model["guidance"]["entries"]
        if x["subject"] == "artifact:release-guide"
    ]
    assert len(entries) == 1
    assert {k: v for k, v in entries[0].items() if k != "id"} == {
        "subject": "artifact:release-guide",
        "kind": "convention",
        "source": "qa-example",
        "sourcePath": "artifacts.release-guide[0]",
        "claim": claim,
        "when": None,
    }
    assert model["guidance"]["sources"]["qa-example"] == {
        "cite": "Fictional QA example: sources/example.md",
        "checked": "2026-10-20",
    }
    assert yaml.safe_load(guidance_path.read_bytes())["sources"]["qa-example"] == {
        "cite": "Fictional QA example: sources/example.md",
        "checked": "2026-10-20",
        "url": "https://example.invalid/qa-release",
    }
    assert (
        model["guidance"]["id"],
        model["guidance"]["guides"],
        model["guidance"]["version"],
    ) == (
        "product-development-guidance",
        PRODUCT,
        "0.9",
    )
    assert [
        (x["role"], x["id"], x["version"]) for x in model["input"]["documents"]
    ] == [
        ("protocol", "kbp", "0.9"),
        ("universe", PRODUCT, "0.10"),
        ("guidance", "product-development-guidance", "0.9"),
    ]
    arguments = located()
    assert arguments["folders"] == ["guides"]
    [scope] = arguments["knowledge_bus_folders"]
    assert scope["folder"] == ""
    assert {f["name"] for f in scope["files"]} == {spec_path.name, guidance_path.name}
    expected_received = [
        {"name": f["name"], "digest": digest(f["text"])} for f in scope["files"]
    ]
    note = json.loads(texts(inspected)[-1])
    assert note == {"received": expected_received}
    # Check the actual existing scope rebuilder's declaring base, not a shadow mapper.
    with Workspace(tmp_path / "scope-check").rebuilt(
        ScopeRequest.model_validate(
            {k: arguments[k] for k in ("folders", "knowledge_bus_folders")}
        )
    ) as rebuilt:
        assert rebuilt.cwd.name == "guides"
        assert rebuilt.sources == {
            PRODUCT: "sent by the harness",
            "product-development-guidance": "sent by the harness",
        }
        for f in scope["files"]:
            assert (rebuilt.cwd.parent / ".knowledge-bus" / f["name"]).read_text() == f[
                "text"
            ]
        assert not (rebuilt.cwd / ".knowledge-bus").exists()
    assert snapshot(root) == saved
    expected = (
        b"# Release two\r\nCandidate: QA-2.\r\n"
        b"Verify the installed version against QA-2.\r\n"
        b"On failure retain evidence; recovery action remains unconfirmed.\r\n"
        b"Source: ../sources/example.md\r\n"
    )
    before = second.read_bytes()
    assert (
        release_host_apply(
            [(second, before, expected)], {guidance_path: valid_guidance}, accepted=True
        )
        == "applied"
    )
    allowed = {
        "basis": "request",
        "text": "QA fixture operation: install fixed second-guide bytes.",
    }
    [recorded] = ask(
        state,
        (
            "kb_record_edit",
            {
                "location": str(second),
                "allowed_by": allowed,
                "before": before.decode(),
                "after": expected.decode(),
                "whole_file": True,
            },
        ),
    )
    receipt = checked(recorded, "edit")
    reloaded, history = ask(
        state,
        ("kbp_card", {**located(), "universe": PRODUCT, "kind": "release-guide"}),
        ("kb_list_edits", {"location": str(second)}),
    )
    assert streams(reloaded) == (release_card(claim), "", 0)
    listing = checked(history, "edits")
    assert listing["location"] == str(second)
    [edit] = listing["edits"]
    expected_edit = {
        "location": str(second),
        "allowed_by": allowed,
        "whole_file": True,
        "before": before.decode(),
        "after": expected.decode(),
        "before_digest": "sha256:" + hashlib.sha256(before).hexdigest(),
        "after_digest": "sha256:" + hashlib.sha256(expected).hexdigest(),
    }
    assert {k: v for k, v in edit.items() if k not in {"id", "time"}} == expected_edit
    assert {k: v for k, v in receipt.items() if k != "card"} == {
        "schema": "knowledge-mcp/edit/2",
        **{k: v for k, v in edit.items() if k not in {"before", "after"}},
    }
    assert len(edit["id"]) == 32 and edit["time"]
    assert second.read_bytes() == expected
    for path in (first, source, questions):
        assert path.read_bytes() == originals[path.relative_to(root).as_posix()][1]
    assert (
        evolution.read_bytes()
        == prior
        + b"QA applied fixture row: example.md; questions.md; release-guide.\r\n"
    )
    assert sorted(p.name for p in second.parent.iterdir()) == [
        "release-one.md",
        "release-two.md",
    ]


@pytest.mark.parametrize(
    "outcome", ["stale-source", "stale-target", "declined", "no-change"]
)
def test_release_host_plan_refusals_preserve_raw_files(tmp_path, outcome):
    root = knowledge_base(tmp_path / "release", {"": [PRODUCT]})
    instruction = root / ".knowledge-bus" / f"{PRODUCT}.type-guidance.kbp.yaml"
    for path in root.rglob("*.kbp.yaml"):
        path.write_bytes(
            path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        )
    if outcome == "stale-source":
        instruction.write_bytes(instruction.read_bytes() + b"# Local definition\r\n")
    source = write(root, "sources/example.md", "")
    source.write_bytes(b"QA verification evidence.\r\n")
    history = write(root, ".knowledge-bus/evolve-log.md", "")
    history.write_bytes(b"# Prior history\r\nRefused: unsupported mandate.\r\n")
    document = write(root, "guides/release-two.md", "")
    document.write_bytes(b"# Release two\r\nCandidate: QA-2.\r\n")
    data = yaml.safe_load(instruction.read_bytes())
    data["guidance"]["version"] = "0.9"
    # Actual proposed physical plan includes instruction, evolution and document writes.
    plan = [
        (instruction, instruction.read_bytes(), release_bytes(data)),
        (
            history,
            history.read_bytes(),
            history.read_bytes() + b"QA fixture revision.\r\n",
        ),
        (document, document.read_bytes(), document.read_bytes() + b"Verify QA-2.\r\n"),
    ]
    state = tmp_path / "refusal-state"
    [recorded] = ask(
        state,
        (
            "kb_record_edit",
            {
                "location": str(document),
                "allowed_by": {"basis": "request", "text": "QA fixture seed only."},
                "before": "",
                "after": document.read_bytes().decode(),
                "whole_file": True,
            },
        ),
    )
    checked(recorded, "edit")
    durable_history = state / "knowledge-mcp/edits.jsonl"
    history_bytes = durable_history.read_bytes()
    evidence = {source: source.read_bytes()}
    if outcome == "stale-source":
        source.write_bytes(b"QA evidence changed after preview.\r\n")
    elif outcome == "stale-target":
        instruction.write_bytes(instruction.read_bytes() + b"# Concurrent change\r\n")
    elif outcome == "no-change":
        plan = [(path, before, before) for path, before, _ in plan]
    before_attempt = snapshot(root)
    if outcome == "stale-source":
        arguments = {
            **scope_arguments(root, "guides/release-two.md", send_text=True),
            "location": str(document),
        }
        [validated] = ask(state, ("kbp_validate", arguments))
        assert streams(validated)[2] == 0
        received = {
            x["name"]: x["digest"] for x in json.loads(texts(validated)[-1])["received"]
        }
        for scope in arguments["knowledge_bus_folders"]:
            for entry in scope["files"]:
                del entry["text"]
                entry["digest"] = received[entry["name"]]
        # A fresh server cannot reuse custom session evidence, even though files exist.
        [stale] = ask(
            state,
            ("kbp_card", {**arguments, "universe": PRODUCT, "kind": "decision-record"}),
        )
        assert stale.is_error
        assert (
            stale.structured_content["type"]
            == "https://github.com/SterlingJF/knowledge-mcp/problems/digest-unknown"
        )
        assert snapshot(root) == before_attempt
    actual = release_host_apply(plan, evidence, accepted=outcome != "declined")
    assert actual == ("stale" if outcome.startswith("stale-") else outcome)
    assert snapshot(root) == before_attempt
    assert durable_history.read_bytes() == history_bytes
    for path in (instruction, source, history, document):
        assert b"\r\n" in path.read_bytes()
    # Record the computed host outcome outside the protected instruction/history tree.
    journal = tmp_path / "host-outcome.json"
    journal.write_text(
        json.dumps({"outcome": actual, "paths": [str(p) for p, _, _ in plan]})
    )
    assert json.loads(journal.read_text())["outcome"] == actual
