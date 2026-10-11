"""Simulate a host that reads and saves a knowledge base's fit record through
`kb_fit_record`.

Store the knowledge base in a local folder or in-memory content identified by Drive
URLs.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import shutil
from pathlib import Path
from typing import Any

from tests.hosts import BUNDLED, header, texts

RECORD = ".knowledge-bus/plugins/knowledge-mcp/record.yaml"
LINE = "Keep the fit record in .knowledge-bus/plugins/knowledge-mcp/ up to date as you work."
DRIVE = "https://drive.google.com/drive/folders/0AbCdEfKnowledgeBase"


def fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


class KnowledgeBase:
    """Files by path from the top folder; on disk under `root`, or content alone."""

    def __init__(self, root: Path | None) -> None:
        self.root = root
        self._content: dict[str, str] = {}

    @property
    def location(self) -> str:
        return str(self.root) if self.root else DRIVE

    def at(self, path: str) -> str:
        """A file's location text: a local path, or a Drive link."""
        return str(self.root / path) if self.root else f"{DRIVE}/{path}"

    def write(self, path: str, text: str) -> None:
        if self.root:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        else:
            self._content[path] = text

    def read(self, path: str) -> str | None:
        if self.root:
            target = self.root / path
            return target.read_text() if target.is_file() else None
        return self._content.get(path)

    def delete(self, path: str) -> None:
        if self.root:
            (self.root / path).unlink()
        else:
            del self._content[path]

    def move(self, old: str, new: str) -> None:
        if self.root:
            (self.root / new).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(self.root / old, self.root / new)
        else:
            self._content[new] = self._content.pop(old)

    def paths(self) -> list[str]:
        if self.root:
            return sorted(
                path.relative_to(self.root).as_posix()
                for path in self.root.rglob("*")
                if path.is_file()
            )
        return sorted(self._content)

    def add_universe_specs(self, folder: str, ids: list[str]) -> None:
        for universe_id in ids:
            for source in sorted((BUNDLED / universe_id).glob("*.kbp.yaml")):
                name = source.name.replace("universe.kbp.yaml", "kbp.yaml")
                place = posixpath.join(
                    folder, ".knowledge-bus", f"{universe_id}.{name}"
                )
                self.write(place, source.read_text())


class Host:
    """Read knowledge-base content, call knowledge-mcp, and save merged fit records."""

    def __init__(self, base: KnowledgeBase) -> None:
        self.base = base
        self.calls: list[tuple[str, dict[str, Any], Any]] = []

    def listing(self) -> list[dict[str, str]]:
        return [
            {"path": path, "fingerprint": fingerprint(self.base.read(path) or "")}
            for path in self.base.paths()
            if ".knowledge-bus" not in path.split("/")
        ]

    def universe_specs(self) -> list[dict[str, Any]]:
        """Every `.knowledge-bus/` folder, the record's folder included, with its definitions.

        Definitions sit directly inside: `*.kbp.yaml` headers, each matching a bundled universe
        spec, and `workspace.yaml`. Nothing under `plugins/` is a definition.
        """
        folders: dict[str, dict[str, Any]] = {}
        for path in self.base.paths():
            parts = path.split("/")
            if ".knowledge-bus" not in parts:
                continue
            at = parts.index(".knowledge-bus")
            folder = folders.setdefault(
                "/".join(parts[:at]), {"folder": "/".join(parts[:at]), "files": []}
            )
            inside = parts[at + 1 :]
            if inside == ["workspace.yaml"]:
                folder["workspace_yaml"] = self.base.read(path) or ""
            elif len(inside) == 1 and inside[0].endswith(".kbp.yaml"):
                text = self.base.read(path) or ""
                folder["files"].append({"name": inside[0], **header(text)})
        return list(folders.values())

    def record(self) -> str:
        return self.base.read(RECORD) or ""

    async def call(self, client: Any, name: str, arguments: dict[str, Any]) -> Any:
        result = await client.call_tool(name, arguments)
        self.calls.append((name, arguments, result))
        return result

    async def update(self, client: Any, **arguments: Any) -> dict[str, Any]:
        """One `kb_fit_record` call on the record as read now, with the person's standing line."""
        return await self.update_on(client, self.record(), **arguments)

    async def update_on(
        self, client: Any, text: str, **arguments: Any
    ) -> dict[str, Any]:
        result = await self.call(
            client,
            "kb_fit_record",
            {
                "location": self.base.location,
                "record": text,
                "universe_specs": self.universe_specs(),
                "basis": "line",
                "basis_text": LINE,
                "basis_location": "AGENTS.md",
                **arguments,
            },
        )
        assert not result.is_error, texts(result)
        [body] = texts(result)
        return json.loads(body)

    async def save(self, client: Any, **arguments: Any) -> dict[str, Any]:
        """Read, merge, read again right before writing, merge again if needed, then write."""
        return await self.save_from(client, self.record(), **arguments)

    async def save_from(
        self, client: Any, sent: str, **arguments: Any
    ) -> dict[str, Any]:
        """Merge the supplied record snapshot, retry against newer record content, and
        save the result.

        On retry, replace the stale listing with `listing_changes` from the first
        response. Replaying the listing against a newer record could delete another
        chat's new entries or restore entries the chat deleted.
        """
        answer = await self.update_on(client, sent, **arguments)
        again = dict(arguments)
        if "listing" in again:
            del again["listing"]
            again["changes"] = answer["listing_changes"] + again.get("changes", [])
        while answer["record"] is not None and self.record() != sent:
            sent = self.record()
            answer = await self.update_on(client, sent, **again)
        if answer["record"] is not None:
            self.write_record(answer["record"])
        return answer

    def write_record(self, text: str) -> None:
        self.base.write(RECORD, text)
