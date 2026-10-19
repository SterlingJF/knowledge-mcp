"""Short-lived import worker. Only upstream kbp and the standard library load here."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from kbp_conform import card, cli, explorer  # type: ignore[import-untyped]

type Printed = tuple[str, str, int]


def printed(argv: list[str]) -> Printed:
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = cli.main(argv)
    return stdout.getvalue(), stderr.getvalue(), code


def upstream_card(spec: str, kind: str) -> Printed:
    return printed(["--card", kind, "--universe", spec, "--format", "json"])


def build_cards(groups: list[dict[str, Any]]) -> list[Printed]:
    wanted = [
        (group["universe_spec"]["id"], kind["kind"])
        for group in groups
        for kind in group["kinds"]
    ]
    try:
        paths, _, named = explorer.resolve_selection([], marks=False)
        protocol = cli.default_protocol()
        parents = named.ids if named else ()
        loaded = {
            group["universe_spec"]["id"]: explorer.load_selection(
                protocol,
                paths,
                universe_id=group["universe_spec"]["id"],
                marks=False,
                named=named,
            )[1:3]
            for group in groups
        }
    except explorer.InspectionError, OSError:
        # Each card loads every selected universe. Replay for authoritative diagnostics.
        return [upstream_card(spec, kind) for spec, kind in wanted]
    outputs = []
    for spec, kind in wanted:
        universe, guidance = loaded[spec]
        others = [
            (*selection, identity in parents)
            for identity, selection in loaded.items()
            if identity != spec
        ]
        try:
            result = card.build_card(
                universe, guidance, kind, others, from_parent=spec in parents
            )
        except explorer.InspectionError, OSError:
            outputs.append(upstream_card(spec, kind))
        else:
            outputs.append(
                (json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n", "", 0)
            )
    return outputs


def query() -> tuple[Printed, list[Printed]]:
    listing = printed(["--kinds"])
    if listing[2] != 0:
        return listing, []
    try:
        data = json.loads(listing[0])
    except ValueError:
        return listing, []
    if not isinstance(data, dict) or data.get("schema") not in (
        "knowledge-bus/kinds/1",
        "knowledge-bus/kinds-set/1",
    ):
        return listing, []
    return listing, build_cards(data.get("universe_specs", [data]))


if __name__ == "__main__":
    print(json.dumps(query(), ensure_ascii=False))  # noqa: T201
