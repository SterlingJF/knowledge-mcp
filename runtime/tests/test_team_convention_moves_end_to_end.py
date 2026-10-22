from __future__ import annotations

from copy import deepcopy
from functools import partial
from pathlib import Path

import pytest
from mcp.client import Client

from knowledge_mcp import document_types as records
from knowledge_mcp.main import build_server
from tests.harness import scope_arguments, server_parameters, session
from tests.test_conventions_end_to_end import PLACE
from tests.test_document_move_end_to_end import apply, arguments, invoke, prepare, vault
from tests.test_filing_end_to_end import typed
from tests.test_team_conventions_end_to_end import (
    CONTRACT,
    DECISION,
    config,
    entry,
    spec,
)
from tests.test_template_workflow_end_to_end import disk_snapshot, place_convention_move


def test_m01_m04_cross_team_links():
    docs = vault()
    plan = prepare(docs, path="Finance/Note.md")
    after = apply(docs, plan)
    assert "Finance/Note.md" in records.parse(plan["record"])
    expected = {
        "Inbox/Note.md",
        "References/assets/diagram.png",
        "Other/Reference.md",
        "Inbox/Space Name.md",
        "Same/Index.md",
        "References/Index.md",
    }
    assert {e["target_before"] for e in plan["links"] if e["target_before"]} <= expected
    for link in plan["links"]:
        assert link["target_after"] == (
            "Finance/Note.md"
            if link["target_before"] == "Inbox/Note.md"
            else link["target_before"]
        )
    assert "[plain](../Finance/Note.md)" in after["References/Index.md"]


def test_m02_destination_type_absent():
    docs = vault()
    a = prepare(
        docs,
        path="Engineering/Note.md",
        knowledge_bus_folders=[spec("Engineering", "engineering")],
    )
    assert a["status"] == "blocked"
    assert a["writes"] == []
    assert any(i["code"] == "destination-type-conflict" for i in a["issues"])


def test_m03_reused_definition_blocks():
    docs = vault()
    a = prepare(
        docs,
        path="Finance/Note.md",
        knowledge_bus_folders=[
            spec(
                "Finance",
                "product-development",
                [("Product development", "Different meaning")],
            )
        ],
    )
    assert a["status"] == "blocked"
    assert not a["writes"]


def test_m05_ambiguous_cross_team_links_block():
    docs = vault()
    docs["Other/Reference.md"] = "[[Index]]"
    a = prepare(docs, path="Finance/Note.md")
    assert a["status"] == "blocked"
    assert not a["writes"]
    assert any(i["code"] == "link-ambiguous" for i in a["issues"])


def test_m06_cross_team_search_echo():
    docs = vault()
    args = arguments(docs, path="Finance/Note.md")
    server = build_server()
    first = invoke(server, args)
    assert first["status"] == "texts_needed"
    args.update(searched=True, search=[*first["search"], "altered"])
    second = invoke(server, args)
    assert second["status"] == "texts_needed"
    assert second["writes"] == []


def test_m08_cross_team_recovery():
    docs = vault()
    original = dict(docs)
    plan = prepare(docs, path="Finance/Note.md")
    first = plan["writes"][0]
    after = apply(docs, {**plan, "writes": [first]})
    assert records.digest(after[first["path"]]) == first["after_digest"]
    after.pop(first["path"])
    after[first["old_path"]] = original[first["old_path"]]
    assert after == original


@pytest.fixture
def selected_team_folder(tmp_path):
    root = tmp_path / "remote-folder-mirror"
    root.mkdir()
    scopes = [
        spec("", "company-records", [("design-doc", "contract")]),
        spec("Finance", "finance", parent=True),
    ]
    for scope in scopes:
        home = root / scope["folder"] / ".knowledge-bus"
        home.mkdir(parents=True, exist_ok=True)
        (home / "team.kbp.yaml").write_text(scope["files"][0]["text"])
        if "workspace_yaml" in scope:
            (home / "workspace.yaml").write_text(scope["workspace_yaml"])
    configs = [
        dict(
            folder="",
            text=config(
                entry(*CONTRACT, "Contracts"),
                entry(*DECISION, "Decisions"),
                entry("company-records", "meeting-note", "Meetings"),
            ),
        ),
        dict(
            folder="Finance",
            text=config(
                entry(*DECISION, "TeamDecisions"),
                entry("finance", "decision-record", "LocalDecisions"),
                selected=[CONTRACT],
            ),
        ),
    ]
    source, target = "Finance/contract.md", "Contracts/Signed.md"
    for relative, text in {
        source: "# Signed\n\nA signed contract.\n",
        ".hidden/Index.md": "[Contract](../Finance/contract.md)\n[[Finance/contract|contract]]\n",
        **{str(Path(c["folder"]) / PLACE): c["text"] for c in configs},
    }.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    original_entry = records.entry(
        **(
            records.plain(
                typed(
                    audience={"value": "team reader", "status": "confirmed"},
                    fingerprint=records.digest((root / source).read_text()),
                )
            )
            | {
                "universe_spec": "company-records",
                "document_type": "contract",
                "set_by": "person",
            }
        )
    )
    (root / records.PLACE).write_text(records.dump({source: original_entry}))
    saved = disk_snapshot(root)
    parameters = server_parameters(tmp_path / "state")
    # A harness can supply a readable remote folder's bytes without a server connector.
    location = "sftp://fixture.example/team"
    return root, configs, source, target, saved, parameters, location


@pytest.mark.parametrize("basis", ["request", "instruction", "accepted_change"])
def test_selected_team_rules_physical_placement_and_fresh_session(
    selected_team_folder, basis
):
    root, configs, source, target, saved, parameters, location = selected_team_folder
    permission = {
        "basis": basis,
        "text": "Move Finance/contract.md to Contracts/Signed.md and repair its references and classification.",
    }

    plan = session(
        parameters,
        partial(
            preview_selected_team_move,
            selected_team_folder=selected_team_folder,
            permission=permission,
        ),
    )
    assert [
        (link["source_path"], link["target_before"], link["target_after"])
        for link in plan["links"]
    ] == [(".hidden/Index.md", source, target), (".hidden/Index.md", source, target)]
    writes = [
        *plan["writes"],
        dict(
            old_path=records.PLACE,
            path=records.PLACE,
            text=plan["record"],
            before_digest=records.digest(saved[records.PLACE].decode()),
            after_digest=records.digest(plan["record"]),
        ),
    ]
    assert len(writes) == 3

    async def place(client: Client):
        assert disk_snapshot(root) == saved
        for w in writes:
            path = root / w["old_path"]
            before = path.read_bytes()
            changed = before.replace(b"\n", b"\r\n")
            assert changed != before
            path.write_bytes(changed)
            stale = disk_snapshot(root)
            state = Path(parameters.env["XDG_STATE_HOME"])
            state_before = disk_snapshot(state)
            with pytest.raises(AssertionError, match=w["old_path"]):
                await place_convention_move(client, root, writes, permission)
            assert disk_snapshot(root) == stale
            assert disk_snapshot(state) == state_before
            history = await client.call_tool("kb_list_edits", {"location": str(root)})
            assert not history.is_error
            assert history.structured_content["edits"] == []
            path.write_bytes(before)
        assert disk_snapshot(root) == saved
        await place_convention_move(client, root, writes, permission)

    session(parameters, place)
    assert not (root / source).exists()
    assert (root / target).read_bytes() == saved[source]
    assert (
        (root / ".hidden/Index.md").read_bytes()
        == b"[Contract](../Contracts/Signed.md)\n[[Contracts/Signed|contract]]\n"
    )
    for c in configs:
        assert (root / c["folder"] / PLACE).read_text() == c["text"]
    expected_entries = {
        target if p == source else p: records.plain(e)
        for p, e in records.parse(saved[records.PLACE].decode("utf-8")).items()
    }
    assert {
        p: records.plain(e)
        for p, e in records.parse(
            (root / records.PLACE).read_bytes().decode("utf-8")
        ).items()
    } == expected_entries

    async def reopen(client: Client):
        typed_result = await client.call_tool(
            "kb_get_document_type",
            dict(
                location=location,
                name="Signed.md",
                **scope_arguments(root, target, send_text=True),
                record=(root / records.PLACE).read_text(),
                listing=[{"path": p} for p in disk_snapshot(root)],
            ),
        )
        assert not typed_result.is_error
        assert typed_result.structured_content["recorded"]["entry"] == records.plain(
            records.parse(saved[records.PLACE].decode())[source]
        )
        rules = await client.call_tool(
            "kb_list_conventions",
            dict(
                location=location,
                folder="Finance",
                **{
                    k: v
                    for k, v in scope_arguments(root, source, send_text=True).items()
                    if k == "knowledge_bus_folders"
                },
                conventions_files=[
                    dict(
                        folder=c["folder"],
                        text=(root / c["folder"] / PLACE).read_text(),
                    )
                    for c in configs
                ],
            ),
        )
        assert not rules.is_error and len(rules.structured_content["conventions"]) == 3
        result = await client.call_tool("kb_list_edits", {"location": str(root)})
        assert not result.is_error
        history = result.structured_content["edits"]
        assert len(history) == 3
        for index, (e, w) in enumerate(zip(history, writes, strict=True), 1):
            assert e["operation"] == dict(
                id="convention-placement",
                index=index,
                count=3,
                old_path=w["old_path"],
                path=w["path"],
            )
            assert e["allowed_by"] == permission
            assert e["before"].encode() == saved[w["old_path"]]
            assert e["after_digest"] == records.digest(
                (root / w["path"]).read_bytes().decode()
            )

    session(parameters, reopen)


async def preview_selected_team_move(client: Client, selected_team_folder, permission):
    root, configs, source, target, saved, _parameters, location = selected_team_folder
    common = dict(
        location=location,
        knowledge_bus_folders=scope_arguments(root, source, send_text=True)[
            "knowledge_bus_folders"
        ],
    )
    listed = await client.call_tool(
        "kb_list_conventions",
        dict(**common, folder="Finance", conventions_files=configs),
    )
    assert not listed.is_error
    rules = listed.structured_content["conventions"]
    assert {
        (r["universe_spec"], r["document_type"], r["base_folder"]) for r in rules
    } == {
        (*CONTRACT, ""),
        (*DECISION, "Finance"),
        ("finance", "decision-record", "Finance"),
    }
    assert all(r["source"]["folder"] == r["base_folder"] for r in rules)
    broken = deepcopy(configs)
    broken[1]["text"] = config(selected=[("company-records", "missing")])
    refused = await client.call_tool(
        "kb_list_conventions",
        dict(**common, folder="Finance", conventions_files=broken),
    )
    assert refused.is_error and refused.structured_content["type"].endswith(
        "/conventions-invalid"
    )
    type_args = dict(
        **common,
        name="contract.md",
        folders=["Finance"],
        record=saved[records.PLACE].decode(),
        listing=[{"path": p} for p in saved],
        conventions_files=configs,
    )
    missing = await client.call_tool("kb_get_document_type", type_args)
    assert not missing.is_error
    assert missing.structured_content["filing"][0]["status"] == "values_needed"
    assert missing.structured_content["filing"][0]["proposal"] is None
    result = await client.call_tool(
        "kb_get_document_type",
        dict(
            **type_args,
            filing_values=[
                dict(
                    path=source,
                    universe_spec="company-records",
                    document_type="contract",
                    properties={},
                    content="Signed",
                )
            ],
        ),
    )
    assert not result.is_error
    assert result.structured_content["filing"][0]["proposal"]["path"] == target
    args = dict(
        **common,
        old_path=source,
        path=target,
        record=saved[records.PLACE].decode(),
        listing=[{"path": p} for p in saved],
        documents=[{"path": source, "text": saved[source].decode()}],
        case_mode="sensitive",
    )
    denied = await client.call_tool("kb_prepare_document_move", args)
    assert denied.is_error
    first = await client.call_tool(
        "kb_prepare_document_move", dict(**args, allowed_by=permission)
    )
    assert not first.is_error and first.structured_content["status"] == "texts_needed"
    args.update(
        documents=[
            {"path": p, "text": t.decode()}
            for p, t in saved.items()
            if p.endswith(".md")
        ]
    )
    result = await client.call_tool(
        "kb_prepare_document_move",
        dict(
            **args,
            allowed_by=permission,
            searched=True,
            search=first.structured_content["search"],
        ),
    )
    assert not result.is_error
    assert result.structured_content["status"] == "ready"
    assert disk_snapshot(root) == saved
    return result.structured_content
