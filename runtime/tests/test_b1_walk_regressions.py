from __future__ import annotations

from pathlib import Path

import anyio
import pytest
from click.testing import CliRunner

from knowledge_mcp import document_types as records
from knowledge_mcp.cli import kb
from knowledge_mcp.main import build_server
from tests.harness import BUNDLED, PRODUCT, header, server_parameters, session, texts
from tests.test_document_move_end_to_end import apply, arguments, invoke

SKILLS = Path(__file__).parents[1] / "skills"


@pytest.mark.parametrize("destination", ["%4E%6F%74%65.md", "N%6Fte.md", "Note%2Emd"])
def test_m1_discovery_covers_encoded_links(destination):
    docs = {
        "Inbox/Note.md": "# Note\n",
        "References/Encoded.md": f"[x](../Inbox/{destination})",
    }
    server = build_server()
    args = arguments(docs)
    first = invoke(server, args)
    matches = {
        p: t
        for p, t in docs.items()
        if p == args["old_path"]
        or any(s.casefold() in t.casefold() for s in first["search"])
    }
    assert "References/Encoded.md" in matches
    assert "../Inbox/%4E%6F%74%65.md" in first["search"]
    plan = invoke(
        server,
        {
            **args,
            "documents": [{"path": p, "text": t} for p, t in matches.items()],
            "searched": True,
            "search": first["search"],
        },
    )
    assert apply(docs, plan)["References/Encoded.md"] == "[x](../decisions/Note.md)"


@pytest.mark.parametrize("mode", ["sensitive", "insensitive"])
def test_m2_case_variant_alias_requires_binding(mode):
    docs = {
        "Inbox/Note.md": "---\naliases: [Original note]\n---\n",
        "References/Alias.md": "[[original note]]",
    }
    server = build_server()
    args = arguments(docs)
    args["case_mode"] = mode
    first = invoke(server, args)
    args.update(
        documents=[{"path": p, "text": t} for p, t in docs.items()],
        searched=True,
        search=first["search"],
    )
    blocked = invoke(server, args)
    assert blocked["status"] == "blocked"
    assert blocked["issues"][0]["code"] == "link-ambiguous"
    args["bindings"] = [
        dict(
            source_path="References/Alias.md",
            start=0,
            end=17,
            target_path="Inbox/Note.md",
        )
    ]
    assert invoke(server, args)["status"] == "ready"


def test_m3_skill_names_required_lookup_and_move_arguments():
    skill = (SKILLS / "kb-write-document/SKILL.md").read_text()
    assert "\x60name\x60: the filename" in skill
    assert "\x60location\x60: the knowledge-base root" in skill
    assert "Keep the same root across both move calls." in skill


def test_m4_skill_filters_peer_definitions_for_card_and_reader(tmp_path):
    skill = (SKILLS / "kb-write-document/SKILL.md").read_text()
    assert "For card and reader calls, include only" in skill
    assert (
        "same \x60location\x60, \x60folders\x60 and \x60knowledge_bus_folders\x60"
        not in skill
    )
    files = [
        {"name": p.name, **header(p.read_text())}
        for p in (BUNDLED / PRODUCT).glob("*.kbp.yaml")
    ]
    inventory = [{"folder": f, "files": files} for f in ("", "inbox", "decisions")]

    async def steps(client):
        base = dict(location="unreachable://vault/inbox/Note.md", folders=["inbox"])
        lookup = await client.call_tool(
            "kb_get_document_type",
            {
                **base,
                "name": "Note.md",
                "knowledge_bus_folders": inventory,
                "listing": [{"path": "inbox/Note.md"}],
            },
        )
        assert not lookup.is_error, texts(lookup)
        ancestors = [f for f in inventory if not f["folder"] or f["folder"] == "inbox"]
        for name, extra in [
            ("kbp_card", {"kind": "decision-record", "universe": PRODUCT}),
            (
                "kb_list_audiences",
                {"document_type": "decision-record", "universe_spec": PRODUCT},
            ),
        ]:
            result = await client.call_tool(
                name, {**base, "knowledge_bus_folders": ancestors, **extra}
            )
            assert not result.is_error, texts(result)

    session(server_parameters(tmp_path), steps)


def test_s1_untyped_lookup_prints_a_result(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    saved = root / records.PLACE
    saved.parent.mkdir(parents=True)
    saved.write_text(
        records.dump(
            {
                "Untyped.md": records.entry(
                    no_document_type=True,
                    set_by="person",
                    allowed_by={"basis": "request", "text": "Keep untyped."},
                    time="2026-10-18T00:00:00Z",
                )
            }
        )
    )
    result = CliRunner().invoke(
        kb, ["type", str(root / "Untyped.md"), "--root", str(root)]
    )
    assert result.exit_code == 0, result.output
    assert result.output.strip().split("\t") == [
        "<none>",
        "<none>",
        "record",
        "<unset>",
        "<none>",
        "<none>",
        "No document type",
    ]


def test_s2_help_and_lookup_inventory_description():
    help_text = CliRunner().invoke(kb, ["type", "--help"]).output
    assert "peer" in help_text
    assert "<none>" in help_text

    async def listed():
        return await build_server().list_tools()

    tools = anyio.run(listed)
    tool = next(t for t in tools if t.name == "kb_get_document_type")
    assert (
        "peer"
        in tool.input_schema["properties"]["knowledge_bus_folders"]["description"]
    )


def test_s3_import_requests_name_and_folder_without_peers():
    skill = (SKILLS / "kb-import-document/SKILL.md").read_text()
    assert "Use the applicable convention before peer evidence." in skill
    assert "Without a convention, use the peer proposal." in skill
    assert "Without a usable proposal, ask the person for a name and folder." in skill


def test_s4_review_filing_before_writing():
    flow = (
        (SKILLS / "kb-write-document/SKILL.md")
        .read_text()
        .split("## Names, folders and moves")[0]
    )
    assert flow.index("**Review filing.**") < flow.index("**Write.**")
    assert "confirm the path" in flow
