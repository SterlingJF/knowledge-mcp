from __future__ import annotations

import json
import posixpath
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, unquote

import yaml

from knowledge_mcp import document_types as records
from knowledge_mcp import problems
from knowledge_mcp.models import AllowedBy, KnowledgeBusFolder, ListedFile
from knowledge_mcp.models_auto.common_schema import LinkBinding, MoveDocument
from knowledge_mcp.scope import Workspace
from knowledge_mcp.type_scope import Scopes


class MoveError(problems.Error):
    code = "move-invalid"


def _path(path: str) -> str:
    return records.normal_path(path, code="move-invalid")


def _aliases(text: str) -> list[str]:
    if not text.startswith("---\n"):
        return []
    head, mark, _ = text[4:].partition("\n---")
    if not mark:
        return []
    try:
        data = yaml.safe_load(head)
    except yaml.YAMLError:
        return []
    aliases = data.get("aliases", []) if isinstance(data, dict) else []
    if isinstance(aliases, str):
        return [aliases]
    return (
        [a for a in aliases if isinstance(a, str)] if isinstance(aliases, list) else []
    )


def search_strings(old: str, new: str, listing: list[str], text: str) -> list[str]:
    # Percent escapes can encode any byte, including mixed spellings of ASCII names.
    # The broad marker catches variants without enumerating exponentially many paths.
    found = {"%", *_aliases(text)}
    for path in (old, new):
        forms = {path, posixpath.basename(path)}
        for source in listing:
            if source.lower().endswith(".md"):
                relative = posixpath.relpath(path, posixpath.dirname(source) or ".")
                forms.update((relative, "./" + relative))
        for form in list(forms):
            if form.lower().endswith(".md"):
                forms.add(form[:-3])
        found.update(forms)
        found.update(quote(form, safe="/.-_") for form in forms)
        for form in forms:
            directory, name = posixpath.split(form)
            stem_name, ext = posixpath.splitext(name)
            found.add(
                posixpath.join(
                    directory, "".join(f"%{b:02X}" for b in stem_name.encode()) + ext
                )
            )
            stem, extension = posixpath.splitext(form)
            found.add(
                "/".join(
                    "".join(f"%{b:02X}" for b in part.encode())
                    for part in stem.split("/")
                )
                + extension
            )
            found.add("".join(f"%{b:02X}" for b in form.encode()))
    return sorted(f for f in found if f)


@dataclass(frozen=True)
class Token:
    start: int
    end: int
    path_start: int
    path_end: int
    path: str
    wiki: bool


def _mask(text: str) -> str:
    chars = list(text)
    fence = ""
    count = 0
    offset = 0
    for line in text.splitlines(keepends=True):
        found = re.match(r" {0,3}(`{3,}|~{3,})", line)
        if fence:
            chars[offset : offset + len(line)] = " " * len(line)
            if (
                found
                and found[1][0] == fence
                and len(found[1]) >= count
                and not line[found.end() :].strip()
            ):
                fence = ""
        elif found:
            fence, count = found[1][0], len(found[1])
            chars[offset : offset + len(line)] = " " * len(line)
        offset += len(line)
    masked = "".join(chars)
    for match in re.finditer(r"(`+)(?!`)([\s\S]*?)(?<!`)\1(?!`)", masked):
        chars[match.start() : match.end()] = " " * len(match[0])
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end >= 0:
            chars[: end + 4] = " " * (end + 4)
    for match in re.finditer(r"\\!?\[\[[^\n]*?\]\]", "".join(chars)):
        chars[match.start() : match.end()] = " " * len(match[0])
    return "".join(chars)


def _external(path: str) -> bool:
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", path)) or path.startswith("//")


def tokens(text: str) -> tuple[list[Token], list[tuple[int, int]]]:
    masked = _mask(text)
    found: list[Token] = []
    covered = list(masked)
    for match in re.finditer(r"!?\[\[([^\]\n]+)\]\]", masked):
        if match.start() and masked[match.start() - 1] == "\\":
            continue
        inside = match[1]
        path = inside.split("|", 1)[0].split("#", 1)[0]
        start = match.start(1)
        found.append(
            Token(match.start(), match.end(), start, start + len(path), path, True)
        )
        covered[match.start() : match.end()] = " " * len(match[0])
    remaining = "".join(covered)
    # Destinations are replaced in place so labels, reference names and titles stay byte-identical.
    patterns = [
        r'!?\[(?:[^\[\]\\]|\\.)*\]\(\s*(?P<dest><[^>\n]*>|(?:\\.|[^\s()])+)(?:\s+(?:"[^"\n]*"|\x27[^\x27\n]*\x27|\([^\)\n]*\)))?\s*\)',
        r'^ {0,3}\[[^\]\n]+\]:[ \t]*(?P<dest><[^>\n]*>|[^\s]+)(?:[ \t]+(?:"[^"\n]*"|\x27[^\x27\n]*\x27|\([^\)\n]*\)))?[ \t]*$',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, remaining, re.MULTILINE):
            dest = match["dest"]
            start = match.start("dest")
            if dest.startswith("<"):
                dest = dest[1:-1]
                start += 1
            raw = dest.split("#", 1)[0]
            if not _external(raw):
                found.append(
                    Token(
                        match.start(),
                        match.end(),
                        start,
                        start + len(raw),
                        unquote(raw),
                        False,
                    )
                )
            covered[match.start() : match.end()] = " " * len(match[0])
    rest = "".join(covered)
    unsupported = [
        (m.start(), m.end()) for m in re.finditer(r"\[\[|\]\]|!?\[[^\n]*\]\(", rest)
    ]
    unsupported.extend(_unsupported_html(rest))
    unsupported.extend((t.start, t.end) for t in found if _unsupported_path(t))
    return sorted(found, key=lambda t: t.start), unsupported


def _unsupported_html(text: str) -> list[tuple[int, int]]:
    pattern = r"""<[^>]*\b(?:href|src)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))[^>]*>"""
    found = []
    for match in re.finditer(pattern, text):
        destination = next(g for g in match.groups() if g is not None)
        if not _external(destination):
            found.append((match.start(), match.end()))
    return found


def _unsupported_path(token: Token) -> bool:
    return "\\" in token.path or (
        token.wiki and any(part in token.path for part in ("^", ":", "%%", "[[", "]]"))
    )


def _candidates(token: Token, source: str, paths: list[str]) -> tuple[list[str], bool]:
    path = token.path
    if token.wiki and path.startswith("/"):
        path = path[1:]
    if not path:
        return [source], False
    if token.wiki:
        names = [path]
        if not path.lower().endswith(".md"):
            names.append(path + ".md")
        if path.startswith(("./", "../")):
            names = [
                posixpath.normpath(posixpath.join(posixpath.dirname(source), n))
                for n in names
            ]
            exact = [p for p in paths if p in names]
            folded = [p for p in paths if p.casefold() in {n.casefold() for n in names}]
        elif "/" in path:
            exact = [p for p in paths if p in names]
            if not exact:
                exact = [p for p in paths if any(p.endswith("/" + n) for n in names)]
            folded = [
                p
                for p in paths
                if any(
                    p.casefold() == n.casefold()
                    or p.casefold().endswith("/" + n.casefold())
                    for n in names
                )
            ]
        else:
            exact = [p for p in paths if posixpath.basename(p) in names]
            folded = [
                p
                for p in paths
                if posixpath.basename(p).casefold() in {n.casefold() for n in names}
            ]
    else:
        absolute = (
            posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
            if not path.startswith("/")
            else path.lstrip("/")
        )
        exact = [p for p in paths if p == absolute]
        folded = [p for p in paths if p.casefold() == absolute.casefold()]
    return (exact if exact else folded), len(exact) != len(folded)


def _resolve(
    token: Token, source: str, paths: list[str]
) -> tuple[str | None, str | None]:
    candidates, case_dependent = _candidates(token, source, paths)
    if case_dependent or len(candidates) > 1:
        return None, "link-ambiguous"
    return (candidates[0], None) if candidates else (None, "link-broken")


def _reference(token: Token, target: str, source: str, paths: list[str]) -> str:
    explicit_extension = token.path.lower().endswith(
        ".md"
    ) or not target.lower().endswith(".md")
    if not token.wiki:
        path = (
            "/" + target
            if token.path.startswith("/")
            else posixpath.relpath(target, posixpath.dirname(source) or ".")
        )
        return quote(path, safe="/.-_")
    stem = (
        target[:-3]
        if target.lower().endswith(".md") and not explicit_extension
        else target
    )
    if token.path.startswith("/"):
        return "/" + stem
    if token.path.startswith(("./", "../")):
        relative = posixpath.relpath(stem, posixpath.dirname(source) or ".")
        return relative if relative.startswith("../") else "./" + relative
    if (
        "/" in token.path
        and token.path == (token.path.lstrip("/"))
        and any(token.path == p or token.path + ".md" == p for p in paths)
    ):
        return stem
    parts = stem.split("/")
    for length in range(1, len(parts) + 1):
        candidate = "/".join(parts[-length:])
        check = Token(0, 0, 0, 0, candidate, True)
        resolved, issue = _resolve(check, source, paths)
        if resolved == target and issue is None:
            return candidate
    return stem


def _issue(
    code: str, source: str | None, token: Token | None, detail: str
) -> dict[str, Any]:
    return dict(
        code=code,
        source_path=source,
        start=token.start if token else None,
        end=token.end if token else None,
        detail=detail,
    )


@dataclass(frozen=True)
class Request:
    location: str
    old_path: str
    path: str
    listing: list[ListedFile]
    documents: list[MoveDocument]
    case_mode: str
    bindings: list[LinkBinding]
    searched: bool
    search: list[str]
    allowed_by: AllowedBy
    knowledge_bus_folders: list[KnowledgeBusFolder]


def _invalid(detail: str, *, code: str = "move-invalid") -> None:
    raise MoveError(detail, code=code)


def _inputs(sent: Request) -> tuple[list[str], dict[str, str]]:
    old, new = _path(sent.old_path), _path(sent.path)
    paths = sorted(_path(item.path) for item in sent.listing)
    if len(set(paths)) != len(paths):
        _invalid("Send each inventory path once.")
    if (
        old not in paths
        or records.is_configuration(old)
        or records.is_configuration(new)
    ):
        _invalid(
            "Use a listed source and keep both paths outside configuration folders."
        )
    docs = {_path(item.path): item.text for item in sent.documents}
    if len(docs) != len(sent.documents) or any(p not in paths for p in docs):
        _invalid("Send each document once, using a path from the listing.")
    if old not in docs:
        _invalid("Send the moved document text.", code="move-input-incomplete")
    return paths, docs


def _answer(
    workspace: Workspace,
    sent: Request,
    record: str,
    paths: list[str],
    docs: dict[str, str],
) -> dict[str, Any]:
    return dict(
        schema="knowledge-mcp/document-move/1",
        location=sent.location,
        old_path=sent.old_path,
        path=sent.path,
        allowed_by=sent.allowed_by.model_dump(mode="json", exclude_unset=True),
        status="texts_needed",
        search=search_strings(sent.old_path, sent.path, paths, docs[sent.old_path]),
        based_on=dict(
            listing_digest=records.digest(
                json.dumps(
                    [
                        i.model_dump(mode="json")
                        for i in sorted(sent.listing, key=lambda i: i.path)
                    ],
                    sort_keys=True,
                )
            ),
            record_digest=workspace.remember(record),
            documents=[
                dict(path=p, digest=workspace.remember(t))
                for p, t in sorted(docs.items())
            ],
        ),
        writes=[],
        record=None,
        digest=None,
        links=[],
        issues=[],
        received=[],
    )


@dataclass
class Plan:
    sent: Request
    paths: list[str]
    docs: dict[str, str]
    result: dict[str, Any]
    after_paths: list[str] = field(init=False)
    bindings: dict[tuple[str, int, int], str] = field(init=False)
    used: set[tuple[str, int, int]] = field(default_factory=set)
    revised: dict[str, str] = field(default_factory=dict)
    aliases: set[str] = field(init=False)

    def __post_init__(self) -> None:
        self.after_paths = sorted(self.after(p) for p in self.paths)
        self.bindings = {
            (b.source_path, b.start, b.end): b.target_path for b in self.sent.bindings
        }
        self.aliases = {
            alias for text in self.docs.values() for alias in _aliases(text)
        }
        if len(self.bindings) != len(self.sent.bindings):
            _invalid("Send each link binding once.")

    def after(self, path: str) -> str:
        return self.sent.path if path == self.sent.old_path else path

    def issue(
        self, code: str, source: str | None, token: Token | None, detail: str
    ) -> None:
        self.result["issues"].append(_issue(code, source, token, detail))

    def target(self, token: Token, source: str) -> str | None:
        target, problem = _resolve(token, source, self.paths)
        if (
            token.wiki
            and token.path.casefold() in {alias.casefold() for alias in self.aliases}
            and target is None
        ):
            problem = "link-ambiguous"
        key = (source, token.start, token.end)
        if key in self.bindings:
            bound = self.bindings[key]
            plausible, _ = _candidates(token, source, self.paths)
            if (
                bound not in self.paths
                or (plausible and bound not in plausible)
                or (target is not None and target != bound)
            ):
                _invalid("A binding conflicts with the supplied link or inventory.")
            self.used.add(key)
            return bound
        if problem:
            detail = (
                "Establish the original target with a verified binding."
                if problem == "link-ambiguous"
                else "The existing link has no listed target."
            )
            self.issue(problem, source, token, detail)
        return target

    def replacement(self, token: Token, source: str, target: str) -> str | None:
        after_source, after_target = self.after(source), self.after(target)
        resolved, problem = _resolve(token, after_source, self.after_paths)
        if resolved == after_target and problem is None:
            return None
        if (
            token.wiki
            and "/" in token.path
            and token.path in (target, target.removesuffix(".md"))
        ):
            return (
                after_target.removesuffix(".md")
                if not token.path.endswith(".md")
                else after_target
            )
        return _reference(token, after_target, after_source, self.after_paths)

    def document(self, source: str, text: str) -> None:
        parsed, unsupported = tokens(text)
        for start, end in unsupported:
            self.result["issues"].append(
                dict(
                    code="link-unsupported",
                    source_path=source,
                    start=start,
                    end=end,
                    detail="Replace the unsupported internal link syntax before moving the document.",
                )
            )
        edits = []
        expected = []
        for token in parsed:
            target = self.target(token, source)
            expected.append(self.after(target) if target is not None else None)
            if target is None:
                continue
            reference = self.replacement(token, source, target)
            replacement = None
            if reference is not None:
                edits.append((token.path_start, token.path_end, reference))
                replacement = (
                    text[token.start : token.path_start]
                    + reference
                    + text[token.path_end : token.end]
                )
            self.result["links"].append(
                dict(
                    source_path=source,
                    start=token.start,
                    end=token.end,
                    target_before=target,
                    target_after=self.after(target),
                    replacement=replacement,
                )
            )
        for start, end, reference in sorted(edits, reverse=True):
            text = text[:start] + reference + text[end:]
        self.verify(source, text, expected)
        self.revised[source] = text

    def verify(self, source: str, text: str, expected: list[str | None]) -> None:
        parsed, unsupported = tokens(text)
        if unsupported or len(parsed) != len(expected):
            self.issue(
                "link-unpreserved",
                source,
                None,
                "The replacement changes internal link syntax. Choose another destination.",
            )
            return
        for token, target in zip(parsed, expected, strict=True):
            resolved, problem = _resolve(token, self.after(source), self.after_paths)
            if (
                resolved != target
                or (target is not None and problem)
                or (target is None and problem != "link-broken")
            ):
                self.issue(
                    "link-unpreserved",
                    source,
                    token,
                    "Choose a destination that preserves the original link target.",
                )

    def validate_destination(self, files: records.Files, scopes: Scopes) -> None:
        equal: Callable[[str], str] = (
            str.casefold if self.sent.case_mode == "insensitive" else str
        )
        if any(
            p != self.sent.old_path and equal(p) == equal(self.sent.path)
            for p in self.paths
        ):
            self.issue(
                "destination-occupied", None, None, "Choose an unoccupied destination."
            )
        entry = files.get(self.sent.old_path)
        universe, _, _ = (
            records.named(entry) if entry is not None else (None, None, False)
        )
        if entry is not None and (
            not records.valid_at(entry, scopes.kinds_at(self.sent.path))
            or (
                universe is not None
                and not scopes.same_definition(
                    self.sent.old_path, self.sent.path, universe
                )
            )
        ):
            self.issue(
                "destination-type-conflict",
                self.sent.old_path,
                None,
                "Choose a folder with the saved universe spec and document type, or change the universe specs separately.",
            )

    def writes(self, files: records.Files) -> None:
        for source in sorted(self.docs, key=lambda p: (p != self.sent.old_path, p)):
            text = self.revised.get(source, self.docs[source])
            if source != self.sent.old_path and text == self.docs[source]:
                continue
            path = self.after(source)
            self.result["writes"].append(
                dict(
                    old_path=source,
                    path=path,
                    before_digest=records.digest(self.docs[source]),
                    after_digest=records.digest(text),
                    text=text,
                )
            )
            if source in files:
                entry = files.pop(source)
                if text != self.docs[source]:
                    entry = entry.model_copy(
                        update={"fingerprint": records.digest(text)}
                    )
                files[path] = entry


def prepare(workspace: Workspace, sent: Request, record: str) -> dict[str, Any]:
    paths, docs = _inputs(sent)
    result = _answer(workspace, sent, record, paths, docs)
    if not sent.searched or sent.search != result["search"]:
        return result
    files = records.parse(record)
    scopes = Scopes(workspace, sent.knowledge_bus_folders)
    plan = Plan(sent, paths, docs, result)
    plan.validate_destination(files, scopes)
    for source, text in sorted(docs.items()):
        if source.lower().endswith(".md"):
            plan.document(source, text)
    if plan.used != plan.bindings.keys():
        _invalid(
            "Each binding must identify a complete internal link token in the supplied text."
        )
    result["received"] = list(scopes.received.values())
    if any(i["code"] != "link-broken" for i in result["issues"]):
        result["status"] = "blocked"
        return result
    result["status"] = "unchanged" if sent.old_path == sent.path else "ready"
    plan.writes(files)
    result["record"] = records.dump(files)
    result["digest"] = workspace.remember(result["record"])
    return result
