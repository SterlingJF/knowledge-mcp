from __future__ import annotations

from copy import deepcopy
from functools import cache
from pathlib import Path

import anyio
import pytest
import yaml

from knowledge_mcp import document_types as records
from knowledge_mcp.main import build_server
from tests.harness import BUNDLED, CODEBASE, knowledge_base, scope_arguments
from tests.test_convention_templates_end_to_end import catalog, variant
from tests.test_conventions_end_to_end import PERMISSION, PLACE
from tests.test_document_move_end_to_end import (
    apply,
    arguments,
    fail_write,
    invoke,
    vault,
)
from tests.test_filing_end_to_end import call

SPEC = "personal-notes"
PURPOSES = {
    "knowledge-note": "A reusable explanation or idea",
    "daily-note": "Notes for a recorded calendar date",
    "meeting-note": "Notes from a meeting",
    "project-note": "Notes supporting an active project",
    "area-note": "Notes supporting an ongoing responsibility",
    "resource-note": "Reference material",
    "archived-note": "Inactive material retained for reference",
    "decision-record": "A decision and its reasons",
    "field-note": "An unfamiliar note awaiting a folder decision",
}


@cache
def note_spec():
    data = yaml.safe_load(
        (BUNDLED / "product-development/universe.kbp.yaml").read_text()
    )
    data["universe"].update(id=SPEC, version="1", label="Personal notes")
    original = next(a for a in data["artifacts"] if a["id"] == "decision-record")
    data["artifacts"] = []
    for index, (kind, purpose) in enumerate(PURPOSES.items()):
        item = deepcopy(original)
        item.update(id=kind, code=f"a{index:04d}")
        item["enablement"].update(action=purpose, actor="note author")
        data["artifacts"].append(item)
    data["relations"] = []
    return yaml.safe_dump(data)


def folders():
    return [
        {
            "folder": "",
            "files": [
                {
                    "name": "personal-notes.kbp.yaml",
                    "id": SPEC,
                    "version": "1",
                    "text": note_spec(),
                }
            ],
        }
    ]


def proposal(
    template="ace",
    name="calendar-daily",
    kind="daily-note",
    folder=None,
    catalog_data=None,
):
    selected = (
        variant(template, name)
        if catalog_data is None
        else deepcopy(
            next(
                v
                for t in catalog_data["templates"]
                if t["id"] == template
                for v in t["variants"]
                if v["id"] == name
            )
        )
    )
    chosen = selected["folder"] if folder is None else folder
    assert chosen is not None, (
        "Ask for the numbered ID folder before proposing a convention."
    )
    return {
        "change": "upsert",
        "universe_spec": SPEC,
        "document_type": kind,
        "folder": chosen,
        "name": selected["name"],
        **({"content": selected["content"]} if "content" in selected else {}),
        "set_by": "agent",
    }


def save(changes, text="", permission=PERMISSION):
    return call(
        build_server(),
        "kb_prepare_conventions",
        {
            "location": "unreachable://vault",
            "conventions": text,
            "knowledge_bus_folders": folders(),
            "changes": changes,
            **({"allowed_by": permission} if permission else {}),
        },
    )


def stored(*changes):
    return save(list(changes))["record"]


def typed(kind):
    return records.entry(
        universe_spec=SPEC,
        version="1",
        document_type=kind,
        set_by="agent",
        allowed_by=PERMISSION,
        time="2026-10-18T00:00:00Z",
    )


def lookup(
    change,
    *,
    properties=None,
    content=None,
    listing=None,
    path="Inbox/Sunday.md",
    **extra,
):
    values = {
        "path": path,
        "universe_spec": SPEC,
        "document_type": change["document_type"],
        "properties": properties or {},
    }
    if content is not None:
        values["content"] = content
    return anyio.run(
        build_server().call_tool,
        "kb_get_document_type",
        {
            "location": "unreachable://vault",
            "name": Path(path).name,
            "folders": list(Path(path).parts[:-1]),
            "knowledge_bus_folders": folders(),
            "record": records.dump({path: typed(change["document_type"])}),
            "listing": [{"path": path}, *(listing or [])],
            "conventions": extra.get("config") or stored(change),
            "filing_values": [values],
        },
    ).structured_content


def test_t04_r07_daily_date_only_and_new_folder():
    change = proposal()
    item = lookup(change, properties={"date": "2026-10-18"})["filing"][0]
    assert item["proposal"]["path"] == "Calendar/2026-10-18.md"
    assert item["proposal"]["folder_new"] is True
    assert lookup(change)["filing"][0]["status"] == "values_needed"
    assert lookup(change, properties={"date": "2026-02-29"})["type"].endswith(
        "/filing-values-invalid"
    )


@pytest.mark.parametrize(
    ("name", "kind", "folder"),
    [
        ("atlas-title", "knowledge-note", "Atlas"),
        ("efforts-title", "project-note", "Efforts"),
        ("calendar-note", "meeting-note", "Calendar"),
    ],
)
def test_t04_ace_purposes(name, kind, folder):
    change = proposal(name=name, kind=kind)
    item = lookup(
        change, properties={"date": "2026-10-18"}, content="Launch discussion"
    )["filing"][0]
    assert item["proposal"]["folder"] == folder


@pytest.mark.parametrize(
    ("kind", "name", "folder"),
    [
        ("knowledge-note", "atlas-title", "Atlas (general notes)"),
        ("resource-note", "atlas-title", "Atlas (ai-owned)"),
        ("project-note", "efforts-title", "Efforts (time-bound notes)"),
    ],
)
def test_t05_customized_ace_exact_folders(kind, name, folder):
    change = proposal(name=name, kind=kind, folder=[folder])
    assert (
        lookup(change, content="Working memory")["filing"][0]["proposal"]["path"]
        == folder + "/Working memory.md"
    )


@pytest.mark.parametrize(
    ("kind", "role"),
    [
        ("project-note", "projects"),
        ("area-note", "areas"),
        ("resource-note", "resources"),
        ("archived-note", "archives"),
    ],
)
def test_t06_para(kind, role):
    change = proposal("para", role + "-title", kind)
    if role == "projects":
        change["folder"].append({"part": "property", "property": "project"})
    expected = role.title() + ("/Garden redesign" if role == "projects" else "")
    assert (
        lookup(
            change,
            properties={"project": "Garden redesign"},
            content="Supplier shortlist",
        )["filing"][0]["proposal"]["path"]
        == expected + "/Supplier shortlist.md"
    )


def test_t07_johnny_decimal_supplied_numbers():
    change = proposal(
        "johnny-decimal",
        "id-date-title",
        "meeting-note",
        ["10-19 Work", "12 Meetings", "12.03 Product reviews"],
    )
    change["name"]["parts"][0]["property"] = "meeting_date"
    assert (
        lookup(
            change,
            properties={"meeting_date": "2026-10-18"},
            content="Launch discussion",
        )["filing"][0]["proposal"]["path"]
        == "10-19 Work/12 Meetings/12.03 Product reviews/2026-10-18 Launch discussion.md"
    )


def test_t08_missing_numbers_stays_a_question():
    item = variant("johnny-decimal", "id-date-title")
    assert item["folder"] is None
    assert "Ask" in item["adaptation"]
    with pytest.raises(AssertionError, match="Ask for the numbered ID folder"):
        proposal("johnny-decimal", "id-date-title", "meeting-note")
    assert save([])["record"] is None


def test_t09_r08_mixed_patterns_and_recorded_number():
    daily = proposal()
    project = proposal("para", "projects-title", "project-note")
    decision = proposal(
        name="atlas-title", kind="decision-record", folder=["Atlas", "Decisions"]
    )
    decision["name"]["parts"].insert(
        0, {"part": "property", "property": "decision_number"}
    )
    text = stored(daily, project, decision)
    assert len(yaml.safe_load(text)["conventions"]) == 3
    assert "template" not in text
    assert (
        lookup(
            decision,
            properties={"decision_number": "0042"},
            content="Use a shared cache",
        )["filing"][0]["proposal"]["path"]
        == "Atlas/Decisions/0042 Use a shared cache.md"
    )
    assert lookup(decision, content="Use a shared cache")["filing"][0]["needed"] == [
        {"source": "property", "name": "decision_number"}
    ]


def test_r01_r02_r03_r04_r06_accept_change_drop_save(tmp_path):
    daily = proposal()
    meeting = proposal(name="calendar-note", kind="meeting-note")
    knowledge = proposal(name="atlas-title", kind="knowledge-note")
    project = proposal(
        name="efforts-title", kind="project-note", folder=["Old projects"]
    )
    old = stored(project)
    assert save([daily], old, permission=None)["status"] == "permission_needed"
    assert save([daily], old, permission=None)["record"] is None
    meeting["folder"] = ["Calendar", "Meetings"]
    source = tmp_path / "Inbox/Sunday.md"
    source.parent.mkdir()
    source.write_text("# Original note\n")
    tracking = records.dump({"Inbox/Sunday.md": typed("daily-note")})
    config = tmp_path / PLACE
    config.parent.mkdir(parents=True)
    (config.parent / "document-types.yaml").write_text(tracking)
    before = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    accepted = save([daily, meeting, knowledge], old)
    config.write_text(accepted["record"])
    entries = yaml.safe_load(config.read_text())["conventions"]
    assert {e["document_type"]: e["folder"] for e in entries} == {
        "daily-note": ["Calendar"],
        "meeting-note": ["Calendar", "Meetings"],
        "knowledge-note": ["Atlas"],
        "project-note": ["Old projects"],
    }
    assert all(
        e["time"].endswith("Z") and e["allowed_by"] == PERMISSION for e in entries
    )
    assert all((tmp_path / p).read_bytes() == data for p, data in before.items())
    assert not (tmp_path / "Calendar").exists()
    assert save([], config.read_text())["record"] is None
    assert save([], config.read_text())["status"] == "unchanged"


def test_r05_concurrent_retry_and_r12_catalog_leaves_custom_convention():
    first = proposal()
    other = proposal(name="atlas-title", kind="knowledge-note", folder=["My notes"])
    text = stored(other)
    catalog()
    assert save([], text)["record"] is None
    retry = save([first], text)
    assert len(yaml.safe_load(retry["record"])["conventions"]) == 2
    assert next(e for e in retry["current"] if e["document_type"] == "knowledge-note")[
        "folder"
    ] == ["My notes"]


def test_t12_duplicate_pair_rejected():
    result = anyio.run(
        build_server().call_tool,
        "kb_prepare_conventions",
        {
            "location": "vault",
            "conventions": "",
            "knowledge_bus_folders": folders(),
            "changes": [proposal(), proposal()],
            "allowed_by": PERMISSION,
        },
    )
    assert result.is_error
    assert result.structured_content["type"].endswith("/conventions-invalid")


def test_t13_recorded_folder_property():
    change = proposal(
        name="atlas-title",
        kind="knowledge-note",
        folder=[{"part": "property", "property": "note_folder"}],
    )
    assert (
        lookup(
            change,
            properties={"note_folder": "Atlas (general notes)"},
            content="Memory",
        )["filing"][0]["proposal"]["path"]
        == "Atlas (general notes)/Memory.md"
    )
    assert lookup(change, content="Memory")["filing"][0]["status"] == "values_needed"


@pytest.mark.parametrize(
    ("separator", "case", "expected"),
    [
        (" ", "as-written", "Shared Cache.md"),
        ("-", "lower", "shared-cache.md"),
        ("_", "as-written", "Shared_Cache.md"),
    ],
)
def test_r09_naming_choices(separator, case, expected):
    change = proposal(name="atlas-title", kind="knowledge-note")
    change["name"].update(separator=separator, case=case)
    assert (
        lookup(change, content="Shared Cache")["filing"][0]["proposal"]["name"]
        == expected
    )


@pytest.mark.parametrize("path", ["Calendar/old/deep/note.md", "calendar/old.md"])
def test_r10_folder_evidence(path):
    assert (
        lookup(proposal(), properties={"date": "2026-10-18"}, listing=[{"path": path}])[
            "filing"
        ][0]["proposal"]["folder_new"]
        is False
    )


def test_r11_occupied_destination():
    item = lookup(
        proposal(),
        properties={"date": "2026-10-18"},
        listing=[{"path": "Calendar/2026-10-18.md"}],
    )["filing"][0]
    assert item["status"] == "destination_occupied"
    assert item["proposal"] is None


def test_t10_t11_mixed_universe_type_inventory(tmp_path):
    root = knowledge_base(tmp_path, {"": [CODEBASE]})
    (root / ".knowledge-bus/personal-notes.kbp.yaml").write_text(note_spec())
    args = scope_arguments(root, "Inbox/Sunday.md", send_text=True)
    result = anyio.run(
        build_server().call_tool, "kbp_kinds", {"location": "vault", **args}
    )
    assert not result.is_error
    text = "\n".join(c.text for c in result.content)
    assert all(kind in text for kind in PURPOSES)
    review = [
        {
            "document_type": kind,
            "answer": "accept" if kind == "daily-note" else "drop",
            "question": "Choose a folder for field notes."
            if kind == "field-note"
            else None,
        }
        for kind in PURPOSES
    ]
    assert len(review) == len(PURPOSES)
    assert save([proposal()])["changes"][0]["universe_spec"] == SPEC


def test_templates_skill_keeps_mapping_and_permission_boundaries():
    root = Path(__file__).parents[1] / "skills"
    text = (
        (root / "kb-write-document/SKILL.md")
        .read_text()
        .split("## Templates", 1)[1]
        .split("## Conventions", 1)[0]
    )
    for phrase in [
        "kbp_kinds",
        "kbp_card",
        "kb_list_convention_templates",
        "accept, change or drop",
        "codebase",
        "empty folders",
        "category",
        "ID",
        "unresolved",
        "set_by",
        "in memory",
    ]:
        assert phrase in text
    for skill in ["kb-track-document-types", "kb-import-document"]:
        assert "Templates" in (root / skill / "SKILL.md").read_text()


def template_move(docs, change=None, *, destination_folders=None):
    change = change or proposal()
    path = lookup(change, properties={"date": "2026-10-18"}, path="Inbox/Note.md")[
        "filing"
    ][0]["proposal"]["path"]
    server = build_server()
    args = arguments(docs, path=path)
    args["record"] = records.dump({"Inbox/Note.md": typed(change["document_type"])})
    args["knowledge_bus_folders"] = folders() + (destination_folders or [])
    first = invoke(server, args)
    assert first["status"] == "texts_needed" and first["writes"] == []
    return invoke(
        server,
        {
            **args,
            "searched": True,
            "search": first["search"],
            "documents": [
                {"path": p, "text": t} for p, t in docs.items() if p.endswith(".md")
            ],
        },
    )


def test_m01_m02_template_move_preserves_independent_link_targets():
    docs = vault()
    plan = template_move(docs)
    after = apply(docs, plan)
    target = "Calendar/2026-10-18.md"
    assert "Inbox/Note.md" not in after
    assert "[plain](../Calendar/2026-10-18.md)" in after["References/Index.md"]
    assert [
        link["target_before"]
        for link in plan["links"]
        if link["source_path"] == "Inbox/Note.md"
    ] == ["References/assets/diagram.png", "Other/Reference.md", "Inbox/Note.md"]
    assert [
        link["target_before"]
        for link in plan["links"]
        if link["source_path"] == "References/Index.md"
    ] == ["Inbox/Note.md"] * 14 + ["Inbox/Space Name.md"]
    for link in plan["links"]:
        assert link["target_after"] == (
            target
            if link["target_before"] == "Inbox/Note.md"
            else link["target_before"]
        )
    for suffix in ["#Heading", "#^id", "|text"]:
        assert suffix in after["References/Index.md"]
    assert records.parse(plan["record"])[target] == typed("daily-note")


def test_m03_ambiguous_template_move_blocks():
    docs = vault()
    docs["Other/Reference.md"] = "[[Index]]"
    plan = template_move(docs)
    assert plan["status"] == "blocked" and plan["writes"] == []
    assert any(i["code"] == "link-ambiguous" for i in plan["issues"])


def test_m04_destination_lacks_note_type():
    text = note_spec().replace("daily-note", "other-note")
    destination = {
        "folder": "Calendar",
        "files": [
            {"name": "changed.kbp.yaml", "id": SPEC, "version": "1", "text": text}
        ],
    }
    plan = template_move(vault(), destination_folders=[destination])
    assert plan["status"] == "blocked" and plan["writes"] == []
    assert plan["record"] is None
    assert any(i["code"] == "destination-type-conflict" for i in plan["issues"])


def test_m05_template_move_reprepares_changed_source_and_convention():
    docs = vault()
    first = template_move(docs)
    docs["References/Index.md"] += "\nConcurrent text.\n"
    with pytest.raises(AssertionError):
        apply(docs, first)
    changed = proposal(folder=["Calendar", "Daily"])
    after = apply(docs, template_move(docs, changed))
    assert "Calendar/Daily/2026-10-18.md" in after
    assert "Concurrent text." in after["References/Index.md"]


def test_m06_template_move_partial_failure_restores_originals():
    docs = vault()
    original = dict(docs)
    plan = template_move(docs)
    written = []
    try:
        for write in plan["writes"]:
            if written:
                fail_write()
            docs = apply(docs, {**plan, "writes": [write]})
            written.append(write)
    except OSError:
        for write in reversed(written):
            assert records.digest(docs[write["path"]]) == write["after_digest"]
            docs.pop(write["path"])
            docs[write["old_path"]] = original[write["old_path"]]
    assert written
    assert docs == original


@pytest.mark.parametrize(
    ("supplied", "question"),
    [
        (
            ["10-19 Work", "22 Meetings", "22.03 Product reviews"],
            "Supply a category within area 10-19.",
        ),
        (
            ["10-19 Work", "12 Meetings", "13.03 Product reviews"],
            "Supply an ID within category 12.",
        ),
    ],
)
def test_t07_invalid_johnny_decimal_relationships_remain_pending(supplied, question):
    review = {
        "document_type": "meeting-note",
        "supplied": supplied,
        "question": question,
        "answer": "pending",
        "proposal": None,
    }
    assert review["question"] and review["proposal"] is None
    assert save([])["record"] is None
    skill = (
        Path(__file__).parents[1] / "skills/kb-write-document/SKILL.md"
    ).read_text()
    assert "category number belongs within the area range" in skill
    assert "ID begins with the category number" in skill
    assert "Request correction or clarification" in skill


def test_naming_guide_links_every_template_source():
    text = (Path(__file__).parents[2] / "docs/naming-and-filing.md").read_text()
    for template in catalog()["templates"]:
        assert all(source["url"] in text for source in template["sources"])


@pytest.mark.parametrize(
    ("relative_path", "format_name"),
    [
        ("runtime/skills/kb-write-document/SKILL.md", "knowledge-mcp/conventions/1"),
        ("contracts/README.md", "conventions.schema.yaml"),
    ],
)
def test_template_instructions_name_the_conventions_format(relative_path, format_name):
    text = (Path(__file__).parents[2] / relative_path).read_text()
    assert "B2" not in text
    assert format_name in text
