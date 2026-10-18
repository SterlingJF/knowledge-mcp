"""Rebuild `.knowledge-bus/` folders in temporary storage for kbp."""

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

from knowledge_mcp import bundled, log, problems
from knowledge_mcp.models import KnowledgeBusFolder, ScopeRequest, SpecFile

SENT = "sent by the harness"
SUFFIX = ".kbp.yaml"


class ScopeError(problems.Error):
    code = "scope-invalid"


@dataclass
class Rebuilt:
    """`Workspace.rebuilt` deletes `cwd` on exit."""

    cwd: Path
    bundled: list[str] = field(default_factory=list)
    received: list[dict[str, object]] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)
    nearest: set[str] | None = None
    key: str = ""


class Workspace:
    """Hold the private temporary folder, spec texts keyed by digest, and file fingerprints for
    one process.
    """

    def __init__(self, base: Path | None = None) -> None:
        self._base = base
        self._texts: dict[str, str] = {}
        self._lock = threading.Lock()
        self.fingerprints: dict[str, dict[str, str]] = {}

    def remember(self, text: str) -> str:
        """Store `text` for this session and return its digest."""
        digest = _digest(text)
        with self._lock:
            self._texts[digest] = text
        return digest

    def recall(self, digest: str) -> str | None:
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
        """Write the `.knowledge-bus/` folders to a temporary folder.

        Hold the workspace lock until exit, then delete the temporary folder. With `sent_only`,
        use supplied text or cached digests and skip bundled files.
        """
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
        """Return the files to write as (depth, path relative to the folder at that depth, text),
        plus the Rebuilt record.

        A path ending in `/` is a folder to create. Raise ScopeError for unsafe names, duplicate folders,
        folders outside the document path, or unavailable universe spec text.
        """
        for index, name in enumerate(request.folders):
            _safe_folder(name, problems.pointer("folders", index))
        chain = _chain(request)
        rebuilt = Rebuilt(cwd=Path())
        plan: list[tuple[int, str, str]] = []
        # A `.knowledge-bus/` with no spec file or workspace.yaml, such as one holding only the
        # plugins folder, counts as empty. When every `.knowledge-bus/` sent is empty, kb uses
        # the bundled universe specs.
        if not any(
            item.files or item.workspace_yaml is not None for _, _, item in chain
        ):
            if sent_only:
                msg = (
                    "kbp_validate never validates a bundled copy, so send the text of each "
                    "`*.kbp.yaml` file from the root folder down to the document's folder."
                )
                raise ScopeError(msg, pointer=problems.pointer("knowledge_bus_folders"))
            for copy in bundled.copies():
                plan.append((0, f".knowledge-bus/{copy.name}", _read(copy.path)))
                rebuilt.bundled.append(copy.name)
                rebuilt.sources[copy.id] = bundled.label()
            return plan, rebuilt

        missing: list[tuple[str, str, bool]] = []
        for depth, position, item in chain:
            plan.append((depth, ".knowledge-bus/", ""))
            for number, spec in enumerate(item.files):
                place = ("knowledge_bus_folders", position, "files", number)
                _safe_file(spec.name, problems.pointer(*place, "name"))
                text = self._text(spec, rebuilt, sent_only=sent_only)
                if text is None:
                    sent_digest = spec.digest is not None and spec.text is None
                    field = ("digest",) if sent_digest else ()
                    missing.append(
                        (spec.name, problems.pointer(*place, *field), sent_digest)
                    )
                    continue
                plan.append((depth, f".knowledge-bus/{spec.name}", text))
            if item.workspace_yaml is not None:
                plan.append(
                    (depth, ".knowledge-bus/workspace.yaml", item.workspace_yaml)
                )
        if missing:
            raise _missing(missing, sent_only=sent_only)
        nearest = chain[-1][2]
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


def _parts(folder: str, pointer: str) -> tuple[str, ...]:
    """Split a root-relative folder path into folder names. `""` and `.` mean the root and give `()`."""
    if folder in ("", "."):
        return ()
    parts = tuple(folder.removeprefix("./").split("/"))
    for name in parts:
        _safe_folder(name, pointer)
    return parts


def _chain(request: ScopeRequest) -> list[tuple[int, int, KnowledgeBusFolder]]:
    """List (depth, index as sent, folder) for each `.knowledge-bus/` folder, root first.

    Raise ScopeError for a folder sent twice or a folder outside the path to the document.
    """
    positions = request.positions or list(range(len(request.knowledge_bus_folders)))
    chain = []
    seen = set()
    for position, item in zip(positions, request.knowledge_bus_folders, strict=True):
        pointer = problems.pointer("knowledge_bus_folders", position, "folder")
        parts = _parts(item.folder, pointer)
        if parts in seen:
            msg = (
                f"{item.folder!r} appears twice in `knowledge_bus_folders`. "
                "Send each folder once."
            )
            raise ScopeError(msg, pointer=pointer)
        if list(parts) != request.folders[: len(parts)]:
            msg = (
                f"{item.folder!r} is not on the path to the document. Send only the folders "
                "from the root folder down to the document's folder."
            )
            raise ScopeError(msg, pointer=pointer)
        seen.add(parts)
        chain.append((len(parts), position, item))
    chain.sort(key=lambda found: found[0])
    return chain


def _missing(missing: list[tuple[str, str, bool]], *, sent_only: bool) -> ScopeError:
    """Without `sent_only`, when any file was sent by digest, the code is `digest-unknown` and the
    errors name only the files sent by digest.
    """
    names = ", ".join(name for name, _, _ in missing)
    errors = [(f"No text for {name}.", pointer) for name, pointer, _ in missing]
    if sent_only:
        msg = (
            f"Send the text of {names}, or a digest from an earlier response in this session. "
            "kbp_validate never validates a bundled copy."
        )
        return ScopeError(msg, errors=errors)
    msg = (
        f"Send the text of {names}. Either no bundled universe spec has the id and version "
        "you sent, or this session has no text for the digest you sent."
    )
    if any(sent_digest for _, _, sent_digest in missing):
        digests = [
            error for error, (_, _, sent) in zip(errors, missing, strict=True) if sent
        ]
        return ScopeError(msg, code="digest-unknown", errors=digests)
    return ScopeError(msg, errors=errors)


def _safe_folder(name: str, pointer: str) -> None:
    if name in ("", ".", "..") or any(char in name for char in "/\\\0"):
        msg = f"Unsupported folder name {name!r}. Send each folder as a plain name without slashes, not `.` or `..`."
        raise ScopeError(msg, pointer=pointer)


def _safe_file(name: str, pointer: str) -> None:
    stem = name.removesuffix(SUFFIX)
    if (
        not name.endswith(SUFFIX)
        or not stem
        or stem.startswith(".")
        or any(char in name for char in "/\\\0")
    ):
        msg = (
            f"Unsupported universe spec file name {name!r}. Use a `.kbp.yaml` name "
            "without a leading dot or path separators."
        )
        raise ScopeError(msg, pointer=pointer)
