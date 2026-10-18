from __future__ import annotations

import json

import anyio
import pytest
import yaml
from jsonschema import Draft202012Validator

from knowledge_mcp.main import build_server
from tests.harness import BUNDLED, PRODUCT, header, server_parameters, session, texts
from tests.test_conventions_end_to_end import PERMISSION, stored, upsert
from tests.test_template_workflow_end_to_end import (
    SPEC,
    proposal,
)
from tests.test_template_workflow_end_to_end import (
    folders as note_folders,
)


def spec(folder, identity, replacements=(), parent=False):
    text = (BUNDLED / PRODUCT / "universe.kbp.yaml").read_text()
    text = text.replace(PRODUCT, identity).replace("experiment-plan", "meeting-note")
    if identity in ("finance", "engineering"):
        meaning = (
            "Revenue minus direct costs."
            if identity == "finance"
            else "Spare capacity before a service limit."
        )
        text = text.replace(
            "  terms:\n", f"  terms:\n    - {{ term: margin, means: {meaning} }}\n", 1
        )
    for old, new in replacements:
        text = text.replace(old, new)
    result = dict(
        folder=folder, files=[dict(name="team.kbp.yaml", **header(text), text=text)]
    )
    if parent:
        result["workspace_yaml"] = "from_parent: [company-records]\n"
    return result


def entry(identity, kind, folder):
    value = upsert()
    value["name"]["case"] = "as-written"
    value.update(universe_spec=identity, document_type=kind, folder=[folder])
    return value


def config(*entries, selected=()):
    data = yaml.safe_load(stored(*(entries or [upsert()])))
    data["conventions"] = data["conventions"] if entries else []
    data["from_parent"] = [dict(universe_spec=u, document_type=k) for u, k in selected]
    return yaml.safe_dump(data)


CONTRACT = ("company-records", "contract")
DECISION = ("company-records", "decision-record")
INVOICE = ("finance", "invoice")
ROOT = config(
    entry(*CONTRACT, "Contracts"),
    entry(*DECISION, "Decisions"),
    entry("company-records", "meeting-note", "Meetings"),
)
FINANCE = config(entry(*INVOICE, "Invoices"), selected=[CONTRACT, DECISION])


def folders():
    return [
        spec("", "company-records", [("design-doc", "contract")]),
        spec("Finance", "finance", [("design-doc", "invoice")], parent=True),
        spec("Engineering", "engineering"),
    ]


def files(finance=FINANCE, root=ROOT):
    return [
        dict(folder="", text=root),
        dict(folder="Finance", text=finance),
        dict(
            folder="Engineering",
            text=config(entry("engineering", "meeting-note", "Reviews")),
        ),
    ]


def call(tool="kb_list_conventions", server=None, **extra):
    result = anyio.run(
        (server or build_server()).call_tool,
        tool,
        (
            dict(location="unreachable://company", knowledge_bus_folders=folders())
            | extra
        ),
    )
    if not result.is_error:
        assert json.loads(texts(result)[0]) == result.structured_content
    return result.structured_content


def inspect(folder="Finance", **extra):
    return call(folder=folder, **(dict(conventions_files=files()) | extra))


def pairs(answer):
    return {(e["universe_spec"], e["document_type"]) for e in answer["conventions"]}


def test_r01_no_team_file():
    assert pairs(inspect(conventions_files=files(""))) == {
        CONTRACT,
        DECISION,
        ("company-records", "meeting-note"),
    }


def test_r02_empty_boundary():
    assert inspect(conventions_files=files(config()))["conventions"] == []


def test_r03_local_boundary():
    assert pairs(
        inspect(conventions_files=files(config(entry(*INVOICE, "Invoices"))))
    ) == {INVOICE}


@pytest.mark.parametrize(
    "folder,inherited", [("Finance", False), ("Finance/Planning", True)]
)
def test_r04_r05_sources(folder, inherited):
    a = inspect(folder)
    assert pairs(a) == {CONTRACT, DECISION, INVOICE}
    for e in a["conventions"]:
        source = e["source"]
        assert source["folder"] == (
            "Finance" if e["universe_spec"] == "finance" else ""
        )
        assert e["base_folder"] == source["folder"]
        assert source["from_parent"] == (inherited or source["folder"] == "")
        assert source["definition"]["allowed_by"] == PERMISSION
    assert "Finance/.knowledge-bus/plugins/knowledge-mcp/conventions.yaml" in [
        r["name"] for r in a["received"]
    ]


@pytest.mark.parametrize("selection,valid", [(INVOICE, True), (CONTRACT, False)])
def test_r06_r07_direct_parent(selection, valid):
    a = inspect(
        "Finance/Audit",
        conventions_files=[
            *files(),
            dict(folder="Finance/Audit", text=config(selected=[selection])),
        ],
    )
    if valid:
        assert pairs(a) == {INVOICE}
        assert a["conventions"][0]["base_folder"] == "Finance"
    else:
        assert a["type"].endswith("/conventions-invalid")
        assert "from_parent" in a["errors"][0]["pointer"]


def test_explicit_local_copy():
    finance = config(entry(*CONTRACT, "Contracts"))
    a = inspect(
        "Finance/Audit",
        conventions_files=[
            *files(finance),
            dict(folder="Finance/Audit", text=config(selected=[CONTRACT])),
        ],
    )
    assert a["conventions"][0]["base_folder"] == "Finance"


@pytest.mark.parametrize(
    "root,finance",
    [
        (config(selected=[CONTRACT]), ""),
        (config(), FINANCE),
        (ROOT, config(selected=[CONTRACT, CONTRACT])),
        (ROOT, config(entry(*CONTRACT, "Contracts"), selected=[CONTRACT])),
    ],
)
def test_r08_r09_r10_invalid_selection(root, finance):
    assert inspect(conventions_files=files(finance, root))["type"].endswith(
        "/conventions-invalid"
    )


def test_r11_intervening_empty_configuration():
    a = inspect(
        "Finance/Planning",
        knowledge_bus_folders=[
            *folders(),
            dict(
                folder="Finance/Planning",
                files=[],
                workspace_yaml="from_parent: [finance]\n",
            ),
        ],
        conventions_files=[*files(), dict(folder="Finance/Planning", text="")],
    )
    assert pairs(a) == {INVOICE}
    assert {e["document_type"] for e in a["inactive"]} == {
        "contract",
        "decision-record",
    }


@pytest.mark.parametrize("explicit", [False, True])
def test_r12_r13_unavailable(explicit):
    fs = [f for f in folders() if f["folder"] != "Finance"] + [
        spec("Finance", "finance")
    ]
    a = inspect(
        knowledge_bus_folders=fs, conventions_files=files(FINANCE if explicit else "")
    )
    if explicit:
        assert a["type"].endswith("/conventions-invalid")
    else:
        assert a["conventions"] == []
        assert {e["reason"] for e in a["inactive"]} == {"document_type_unavailable"}


def test_r14_reused_identifier():
    fs = [
        folders()[0],
        spec(
            "Finance",
            "company-records",
            [("design-doc", "contract"), ("Product development", "Different meaning")],
        ),
    ]
    a = inspect(knowledge_bus_folders=fs, conventions_files=files(""))
    assert a["conventions"] == []
    assert {e["reason"] for e in a["inactive"]} == {"definition_differs"}


def test_r15_incomplete_context():
    assert inspect(conventions_files=files()[1:])["type"].endswith(
        "/conventions-context-incomplete"
    )


def test_r16_digest_reuse_and_refresh():
    server = build_server()
    a = inspect(server=server)
    digests = {r["name"]: r["digest"] for r in a["received"]}
    inputs = [
        dict(
            folder=e["folder"],
            digest=digests[
                (e["folder"] + "/" if e["folder"] else "")
                + ".knowledge-bus/plugins/knowledge-mcp/conventions.yaml"
            ],
        )
        for e in files()
        if e["folder"] != "Engineering"
    ]
    assert (
        inspect(server=server, conventions_files=inputs)["conventions"]
        == a["conventions"]
    )
    changed = ROOT.replace("Contracts", "Signed")
    assert (
        inspect(server=server, conventions_files=files(root=changed))["conventions"]
        != a["conventions"]
    )


def test_r17_digest_isolation():
    text = config(entry(*DECISION, "Decisions"))
    a = inspect("Finance", conventions_files=files(text, text))
    assert a["conventions"][0]["base_folder"] == "Finance"


def test_r18_irrelevant_sibling():
    assert pairs(
        inspect(conventions_files=[*files()[:2], dict(folder="Engineering", text="[")])
    ) == {CONTRACT, DECISION, INVOICE}


def test_r19_content_only_stale_local():
    a = inspect(conventions_files=files(config(entry("finance", "gone", "Old"))))
    assert a["conventions"] == []
    assert a["inactive"][0]["document_type"] == "gone"


def test_r20_stdio(tmp_path):
    async def steps(client):
        result = await client.call_tool(
            "kb_list_conventions",
            dict(
                location="unreachable://company",
                folder="Finance",
                knowledge_bus_folders=folders(),
                conventions_files=files(),
            ),
        )
        assert not result.is_error
        tool = next(
            t
            for t in (await client.list_tools()).tools
            if t.name == "kb_list_conventions"
        )
        assert tool.output_schema
        Draft202012Validator(tool.output_schema).validate(result.structured_content)
        assert json.loads(texts(result)[0]) == result.structured_content

    session(server_parameters(tmp_path / "state"), steps)


def prepare(**extra):
    return call(
        "kb_prepare_conventions",
        **(
            dict(
                folder="Finance",
                conventions=config(entry(*INVOICE, "Invoices")),
                conventions_files=[dict(folder="", text=ROOT)],
            )
            | extra
        ),
    )


def test_p01_p02_p06_permission_and_audit():
    assert (
        prepare(
            from_parent=[
                dict(zip(("universe_spec", "document_type"), CONTRACT, strict=True))
            ]
        )["status"]
        == "permission_needed"
    )
    a = prepare(
        from_parent=[dict(universe_spec=CONTRACT[0], document_type=CONTRACT[1])],
        allowed_by=PERMISSION,
    )
    assert a["status"] == "ready"
    saved = yaml.safe_load(a["record"])
    assert saved["schema"] == "knowledge-mcp/conventions/1"
    assert (
        saved["conventions"]
        == yaml.safe_load(config(entry(*INVOICE, "Invoices")))["conventions"]
    )
    assert a["allowed_by"] == PERMISSION


def test_p03_p04_p05_selection_preservation():
    selected = [dict(universe_spec=u, document_type=k) for u, k in [CONTRACT, DECISION]]
    assert (
        prepare(conventions=FINANCE, from_parent=selected[::-1])["status"]
        == "unchanged"
    )
    a = prepare(
        conventions=FINANCE, changes=[entry(*INVOICE, "Bills")], allowed_by=PERMISSION
    )
    assert yaml.safe_load(a["record"])["from_parent"] == selected
    a = prepare(conventions=FINANCE, from_parent=[], allowed_by=PERMISSION)
    assert yaml.safe_load(a["record"])["from_parent"] == []


def test_p07_p08_team_upsert_preserves_stale():
    a = prepare(
        conventions=config(entry("finance", "gone", "Old")),
        changes=[entry(*INVOICE, "Invoices")],
        allowed_by=PERMISSION,
    )
    assert {e["document_type"] for e in yaml.safe_load(a["record"])["conventions"]} == {
        "invoice",
        "gone",
    }


@pytest.mark.parametrize(
    "folder", ["/Finance", "../Finance", "Finance/../Audit", "Finance//Audit"]
)
def test_invalid_folder(folder):
    assert "type" in inspect(folder)


def test_p15_mixed_inputs():
    a = call(
        "kb_get_document_type",
        name="contract.md",
        folders=["Finance"],
        conventions=ROOT,
        conventions_files=files(),
    )
    assert a["type"].endswith("/argument-invalid")


def lookup(**extra):
    return call(
        "kb_get_document_type",
        **(
            dict(
                name="contract.md",
                folders=["Finance"],
                conventions_files=files(),
                listing=[dict(path="Finance/contract.md")],
                filing_values=[
                    dict(
                        path="Finance/contract.md",
                        universe_spec=CONTRACT[0],
                        document_type=CONTRACT[1],
                        properties={},
                        content="Signed",
                    )
                ],
            )
            | extra
        ),
    )


def test_p10_source_relative_rendering():
    a = lookup()
    assessment = next(e for e in a["filing"] if e["document_type"] == "contract")
    assert assessment["proposal"]["path"] == "Contracts/Signed.md"
    assert assessment["convention"]["folder"] == ""


def test_destination_without_type_blocks_proposal():
    a = lookup(knowledge_bus_folders=[*folders(), spec("Contracts", "engineering")])
    assessment = next(e for e in a["filing"] if e["document_type"] == "contract")
    assert assessment["status"] == "destination_type_conflict"
    assert assessment["proposal"] is None


def test_p11_per_path_tracking():
    entries = [
        dict(
            path="Finance/invoice.md",
            universe_spec="finance",
            document_type="invoice",
            set_by="person",
        ),
        dict(
            path="Engineering/meeting-note.md",
            universe_spec="engineering",
            document_type="meeting-note",
            set_by="person",
        ),
    ]
    configs = [
        *files()[:2],
        dict(
            folder="Engineering",
            text=config(entry("engineering", "meeting-note", "Reviews")),
        ),
    ]
    a = call(
        "kb_prepare_document_types",
        record="",
        conventions_files=configs,
        entries=entries,
        listing=[dict(path=e["path"]) for e in entries],
        allowed_by=PERMISSION,
        filing_values=[
            dict(
                path=e["path"],
                universe_spec=e["universe_spec"],
                document_type=e["document_type"],
                properties={},
                content="Review",
            )
            for e in entries
        ],
    )
    assert {e["proposal"]["path"] for e in a["filing"]} == {
        "Finance/Invoices/Review.md",
        "Engineering/Reviews/Review.md",
    }


def test_p12_values_needed_provenance():
    a = lookup(filing_values=[])
    assessment = next(e for e in a["filing"] if e["document_type"] == "contract")
    assert assessment["status"] == "values_needed"
    assert assessment["proposal"] is None
    assert assessment["convention"]["from_parent"] is True


def test_p09_concurrent_reprepare():
    first = prepare(
        from_parent=[dict(universe_spec=CONTRACT[0], document_type=CONTRACT[1])],
        allowed_by=PERMISSION,
    )
    assert first["status"] == "ready"
    retry = prepare(
        conventions_files=[dict(folder="", text=config())],
        from_parent=[dict(universe_spec=CONTRACT[0], document_type=CONTRACT[1])],
        allowed_by=PERMISSION,
    )
    assert retry["type"].endswith("/conventions-invalid")


@pytest.mark.parametrize("text", [" ", "\n", "[", "{}"])
def test_invalid_existing_file(text):
    assert inspect(conventions_files=files(text))["type"].endswith(
        "/conventions-invalid"
    )


def test_unknown_file_fields():
    assert "type" in inspect(
        conventions_files=[dict(folder="", text=ROOT, unknown=True)]
    )


def test_b3_template_saved_in_team_folder():
    definitions = note_folders()
    definitions[0]["folder"] = "Finance"
    saved = call(
        "kb_prepare_conventions",
        folder="Finance",
        conventions="",
        knowledge_bus_folders=definitions,
        conventions_files=[],
        changes=[proposal()],
        allowed_by=PERMISSION,
    )
    assert saved["status"] == "ready"
    a = call(
        "kb_get_document_type",
        name="daily-note.md",
        folders=["Finance"],
        knowledge_bus_folders=definitions,
        conventions_files=[dict(folder="Finance", text=saved["record"])],
        listing=[dict(path="Finance/daily-note.md")],
        filing_values=[
            dict(
                path="Finance/daily-note.md",
                universe_spec=SPEC,
                document_type="daily-note",
                properties={"date": "2026-10-18"},
            )
        ],
    )
    assessment = next(e for e in a["filing"] if e["document_type"] == "daily-note")
    assert assessment["proposal"]["path"] == "Finance/Calendar/2026-10-18.md"


def test_duplicate_file_folder():
    a = inspect(conventions_files=[*files(), files()[0]])
    assert a["type"].endswith("/argument-invalid")


def test_m07_changed_parent_refreshes_proposal():
    before = lookup()
    after = lookup(conventions_files=files(root=ROOT.replace("Contracts", "Signed")))
    first = next(e for e in before["filing"] if e["document_type"] == "contract")
    second = next(e for e in after["filing"] if e["document_type"] == "contract")
    assert first["proposal"]["path"] == "Contracts/Signed.md"
    assert second["proposal"]["path"] == "Signed/Signed.md"
    assert first["convention"]["digest"] != second["convention"]["digest"]
