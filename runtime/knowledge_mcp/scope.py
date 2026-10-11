"""The folders a host describes, rebuilt in a private temporary folder for `kbp` to run in.

`kbp` runs from the document's rebuilt folder with no target, so it picks the nearest
`.knowledge-bus/` and applies `workspace.yaml` itself. When no folder on the chain holds a
definition, the bundled universe specs apply. Nothing here reads the knowledge base.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import shutil
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from knowledge_mcp import bundled, log
from knowledge_mcp.contract import ScopeRequest, SpecFile

SENT = "sent by the host"
SUFFIX = ".kbp.yaml"


class ScopeError(ValueError):
    """The request can't be rebuilt; the message says what to send instead."""


@dataclass
class Rebuilt:
    """A rebuilt folder chain, alive inside `Workspace.rebuilt`."""

    cwd: Path
    bundled: list[str] = field(default_factory=list)
    received: list[dict[str, object]] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)
    nearest: set[str] | None = None
    key: str = ""


class Workspace:
    """One server process: its private temporary folder and the texts sent this session."""

    def __init__(self, base: Path | None = None) -> None:
        self._base = base
        self._texts: dict[str, str] = {}
        self._lock = threading.Lock()
        # Per knowledge base location: the fingerprint last seen for each path this session.
        self.fingerprints: dict[str, dict[str, str]] = {}

    def remember(self, text: str) -> str:
        """Keep a text sent this session; return its digest."""
        digest = _digest(text)
        with self._lock:
            self._texts[digest] = text
        return digest

    def recall(self, digest: str) -> str | None:
        """A text this session holds for the digest."""
        with self._lock:
            return self._texts.get(digest)

    @property
    def base(self) -> Path:
        if self._base is None:
            self._base = Path(tempfile.mkdtemp(prefix="knowledge-mcp-"))
            atexit.register(shutil.rmtree, self._base, ignore_errors=True)
        self._base.mkdir(parents=True, exist_ok=True, mode=0o700)
        return self._base

    @contextmanager
    def rebuilt(
        self, request: ScopeRequest, *, sent_only: bool = False
    ) -> Iterator[Rebuilt]:
        """Rebuild the chain; `sent_only` refuses bundled copies, for checking."""
        with self._lock:
            plan, rebuilt = self._plan(request, sent_only=sent_only)
            rebuilt.key = hashlib.sha256(
                json.dumps(
                    [request.folders, [(d, n, _digest(t)) for d, n, t in plan]],
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            place = self.base / rebuilt.key[:16]
            shutil.rmtree(place, ignore_errors=True)
            top = place / "knowledge-base"
            try:
                for depth, inside, text in plan:
                    target = top.joinpath(*request.folders[:depth]) / inside
                    if inside.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(text, encoding="utf-8")
                rebuilt.cwd = top.joinpath(*request.folders)
                rebuilt.cwd.mkdir(parents=True, exist_ok=True)
                yield rebuilt
            finally:
                shutil.rmtree(place, ignore_errors=True)

    def _plan(
        self, request: ScopeRequest, *, sent_only: bool
    ) -> tuple[list[tuple[int, str, str]], Rebuilt]:
        """(depth, path inside the depth's folder, text) for every file to write."""
        for name in request.folders:
            _safe_folder(name)
        depths = [scope.depth for scope in request.universe_specs]
        if len(set(depths)) != len(depths):
            msg = "Send each folder of the chain once in `universe_specs`."
            raise ScopeError(msg)
        for scope in request.universe_specs:
            if scope.depth > len(request.folders):
                msg = (
                    f"`depth` {scope.depth} lies below the document's folder: it counts entries "
                    f"of `folders`, which has {len(request.folders)} entries."
                )
                raise ScopeError(msg)
        rebuilt = Rebuilt(cwd=Path())
        plan: list[tuple[int, str, str]] = []
        # A `.knowledge-bus/` holding no definition, such as one holding only the fit record's
        # plugin folder, adds nothing; with no definition on the chain, the bundled set applies.
        if not any(
            scope.files or scope.workspace_yaml is not None
            for scope in request.universe_specs
        ):
            if sent_only:
                msg = (
                    "kbp_check checks only universe spec text you send, never a bundled copy: "
                    "send the text of each `*.kbp.yaml` file in scope."
                )
                raise ScopeError(msg)
            for copy in bundled.copies():
                plan.append((0, f".knowledge-bus/{copy.name}", _read(copy.path)))
                rebuilt.bundled.append(copy.name)
                rebuilt.sources[copy.id] = bundled.label()
            return plan, rebuilt

        missing = []
        for scope in sorted(request.universe_specs, key=lambda scope: scope.depth):
            plan.append((scope.depth, ".knowledge-bus/", ""))
            for spec in scope.files:
                _safe_file(spec.name)
                text = self._text(spec, rebuilt, sent_only=sent_only)
                if text is None:
                    missing.append(spec.name)
                    continue
                plan.append((scope.depth, f".knowledge-bus/{spec.name}", text))
            if scope.workspace_yaml is not None:
                plan.append(
                    (scope.depth, ".knowledge-bus/workspace.yaml", scope.workspace_yaml)
                )
        if missing:
            names = ", ".join(missing)
            if sent_only:
                msg = (
                    "kbp_check checks only universe spec text you send, never a bundled copy: "
                    f"send the text of {names}."
                )
            else:
                msg = (
                    f"Send the text of {names}: no bundled universe spec has that id and version, "
                    "and this session holds no copy for the digest sent."
                )
            raise ScopeError(msg)
        nearest = max(request.universe_specs, key=lambda scope: scope.depth)
        rebuilt.nearest = {spec.id for spec in nearest.files}
        return plan, rebuilt

    def _text(self, spec: SpecFile, rebuilt: Rebuilt, *, sent_only: bool) -> str | None:
        if spec.text is not None:
            digest = _digest(spec.text)
            self._texts[digest] = spec.text
            rebuilt.received.append({"name": spec.name, "digest": digest})
            rebuilt.sources[spec.id] = SENT
            return spec.text
        if spec.digest is not None:
            text = self._texts.get(spec.digest)
            if text is not None:
                rebuilt.sources[spec.id] = SENT
            return text
        copy = None if sent_only else bundled.index().get((spec.id, spec.version))
        if copy is None:
            return None
        rebuilt.bundled.append(spec.name)
        rebuilt.sources[spec.id] = bundled.label()
        return _read(copy.path)


def _digest(text: str) -> str:
    return log.text_digest(text)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _safe_folder(name: str) -> None:
    if name in ("", ".", "..") or any(char in name for char in "/\\\0"):
        msg = f"Unsupported folder name {name!r}. Use each folder's own name."
        raise ScopeError(msg)


def _safe_file(name: str) -> None:
    stem = name.removesuffix(SUFFIX)
    if (
        not name.endswith(SUFFIX)
        or not stem
        or stem.startswith(".")
        or any(char in name for char in "/\\\0")
    ):
        msg = (
            f"Unsupported definition filename {name!r}. Use a `.kbp.yaml` filename "
            "without a leading dot or path separators."
        )
        raise ScopeError(msg)
