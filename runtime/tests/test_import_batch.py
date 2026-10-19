"""Upstream listing/card parity and production import-cache validation."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import anyio
import pytest
from mcp.client import Client

from knowledge_mcp import importing, kbp, problems
from knowledge_mcp.main import build_server
from knowledge_mcp.models import ScopeRequest
from knowledge_mcp.scope import Rebuilt, Workspace
from tests.harness import (
    CODEBASE,
    PRODUCT,
    checked,
    knowledge_base,
    scope_arguments,
    validator,
)


@pytest.mark.parametrize("inherited", [False, True])
def test_every_card_matches_upstream(tmp_path: Path, inherited: bool) -> None:
    scopes = (
        {"": [CODEBASE, PRODUCT]}
        if not inherited
        else {"": [CODEBASE], "inner": [PRODUCT]}
    )
    root = knowledge_base(tmp_path / "kb", scopes)
    document = "inner/note.md" if inherited else "note.md"
    if inherited:
        (root / "inner/.knowledge-bus/workspace.yaml").write_text(
            f"from_parent:\n  - {CODEBASE}\n"
        )
    request = ScopeRequest.model_validate(scope_arguments(root, document))
    with Workspace(tmp_path / "work").rebuilt(request) as rebuilt:
        # marks=False must ignore malformed marks in both listing and card paths.
        (rebuilt.cwd / ".knowledge-bus/broken.explorer.yaml").write_text(
            "[invalid yaml"
        )
        listing, outputs = kbp.query_scope(rebuilt.cwd, cards=True)
        assert listing == kbp.run(["--kinds"], rebuilt.cwd)
        assert listing.code == 0
        data = kbp.parsed(listing, "kinds", kbp.KINDS)
        groups = data["universe_specs"]
        assert [group["universe_spec"]["id"] for group in groups] == (
            [PRODUCT, CODEBASE] if inherited else [CODEBASE, PRODUCT]
        )
        wanted = importing.pairs(data)
        assert len(wanted) == len(outputs) == 39
        for (spec, kind), output in zip(wanted, outputs, strict=True):
            assert output == kbp.run(
                ["--card", kind, "--universe", spec, "--format", "json"], rebuilt.cwd
            )


def test_single_universe_without_guidance_matches_upstream(tmp_path: Path) -> None:
    root = knowledge_base(tmp_path / "kb", {"": [CODEBASE]})
    guidance = list((root / ".knowledge-bus").glob("*guidance.kbp.yaml"))
    assert guidance
    for path in guidance:
        path.unlink()
    request = ScopeRequest.model_validate(
        scope_arguments(root, "note.md", send_text=True)
    )
    with Workspace(tmp_path / "work").rebuilt(request) as rebuilt:
        assert not list((rebuilt.cwd / ".knowledge-bus").glob("*guidance.kbp.yaml"))
        listing, outputs = kbp.query_scope(rebuilt.cwd, cards=True)
        assert listing == kbp.run(["--kinds"], rebuilt.cwd)
        assert listing.code == 0
        data = kbp.parsed(listing, "kinds", kbp.KINDS)
        assert data["universe_spec"]["id"] == CODEBASE
        assert "universe_specs" not in data
        wanted = importing.pairs(data)
        assert wanted
        assert len(wanted) == len(outputs)
        for (spec, kind), output in zip(wanted, outputs, strict=True):
            assert output == kbp.run(
                ["--card", kind, "--universe", spec, "--format", "json"], rebuilt.cwd
            )


@pytest.mark.parametrize("broken", ["definition", "guidance", "workspace"])
def test_kinds_errors_match_before_cards(tmp_path: Path, broken: str) -> None:
    root = knowledge_base(tmp_path / "kb", {"": [CODEBASE, PRODUCT]})
    request = ScopeRequest.model_validate(scope_arguments(root, "note.md"))
    with Workspace(tmp_path / "work").rebuilt(request) as rebuilt:
        scope = rebuilt.cwd / ".knowledge-bus"
        if broken == "workspace":
            (scope / "workspace.yaml").write_text("from_parent: [unknown-universe]\n")
        else:
            path = (
                scope
                / f"{PRODUCT}.{'type-guidance.kbp.yaml' if broken == 'guidance' else 'kbp.yaml'}"
            )
            path.write_text("[invalid yaml")
        listing, outputs = kbp.query_scope(rebuilt.cwd, cards=True)
        assert listing == kbp.run(["--kinds"], rebuilt.cwd)
        assert listing.code != 0
        assert outputs == []


def test_import_cache_refreshes_changed_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KNOWLEDGE_MCP_STATE_DIR", str(tmp_path / "state"))
    root = knowledge_base(tmp_path / "kb", {"": [CODEBASE, PRODUCT]})
    workspace = Workspace(tmp_path / "work")
    server = build_server(workspace)

    def arguments() -> dict:
        return {
            "location": "pasted in chat",
            "text": "A passage to label.",
            **scope_arguments(root, "note.md", send_text=True),
        }

    async def calls() -> None:
        async with Client(server, mode="legacy") as client:
            first = checked(
                await client.call_tool("kb_prepare_import", arguments()), "import"
            )
            warm = checked(
                await client.call_tool("kb_prepare_import", arguments()), "import"
            )
            assert warm == first
            guidance = next(
                (root / ".knowledge-bus").glob(f"{PRODUCT}.*guidance.kbp.yaml")
            )
            universe = root / f".knowledge-bus/{PRODUCT}.kbp.yaml"
            text = universe.read_text()
            assert "What did we decide?" in text
            universe.write_text(
                text.replace("What did we decide?", "What choice did we make?")
            )
            changed = checked(
                await client.call_tool("kb_prepare_import", arguments()), "import"
            )
            expected = json.loads(
                json.dumps(first["document_types"]).replace(
                    "What did we decide?", "What choice did we make?"
                )
            )
            assert changed["document_types"] == expected
            assert changed["document_types"] != first["document_types"]
            universe.write_text(text)
            assert (
                checked(
                    await client.call_tool("kb_prepare_import", arguments()), "import"
                )
                == first
            )
            # Changed guidance must invalidate a previously successful scope.
            # Keep the header so the request reaches kbp's YAML validation.
            guidance.write_text(guidance.read_text() + "\n[invalid yaml")
            failed = await client.call_tool("kb_prepare_import", arguments())
            assert failed.is_error
            assert failed.meta["exit_code"] == 1
            validator("problem").validate(failed.structured_content)
            assert failed.structured_content["type"] == problems.BASE + "kbp-failed"
            assert (
                failed.structured_content["detail"] == "kbp --kinds exited with code 1."
            )

    anyio.run(calls)


def test_warm_import_cache_validates_rebuilt_guidance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KNOWLEDGE_MCP_STATE_DIR", str(tmp_path / "state"))
    root = knowledge_base(tmp_path / "kb", {"": [CODEBASE, PRODUCT]})

    class CorruptibleWorkspace(Workspace):
        corrupt = False

        @contextmanager
        def rebuilt(
            self, request: ScopeRequest, *, sent_only: bool = False
        ) -> Iterator[Rebuilt]:
            with super().rebuilt(request, sent_only=sent_only) as rebuilt:
                keys.append(rebuilt.key)
                if self.corrupt:
                    guidance = next(
                        (rebuilt.cwd / ".knowledge-bus").glob(
                            f"{PRODUCT}.*guidance.kbp.yaml"
                        )
                    )
                    guidance.write_text("[invalid yaml")
                yield rebuilt

    keys: list[str] = []
    workspace = CorruptibleWorkspace(tmp_path / "work")
    server = build_server(workspace)
    arguments = {
        "location": "pasted in chat",
        "text": "A passage to label.",
        **scope_arguments(root, "note.md", send_text=True),
    }

    async def calls() -> None:
        async with Client(server, mode="legacy") as client:
            first = checked(
                await client.call_tool("kb_prepare_import", arguments), "import"
            )
            assert (
                checked(
                    await client.call_tool("kb_prepare_import", arguments), "import"
                )
                == first
            )
            workspace.corrupt = True
            failed = await client.call_tool("kb_prepare_import", arguments)
            assert failed.is_error
            assert failed.meta["exit_code"] == 1
            validator("problem").validate(failed.structured_content)
            assert failed.structured_content["type"] == problems.BASE + "kbp-failed"
            assert (
                failed.structured_content["detail"] == "kbp --kinds exited with code 1."
            )
            assert any(
                (block.meta or {}).get("stream") == "stderr" and block.text
                for block in failed.content
            )
            assert len(keys) == 3
            assert keys[0] and keys == [keys[0]] * 3

    anyio.run(calls)
