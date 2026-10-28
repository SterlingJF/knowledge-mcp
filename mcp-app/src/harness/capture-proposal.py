"""Calls kb_prepare_proposal over stdio and saves two real results for the harness.

Run from the repo root: uv run --project runtime python mcp-app/src/harness/capture-proposal.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parents[2] / "runtime"
sys.path.insert(0, str(RUNTIME))

from tests.harness import server_parameters, session  # noqa: E402
from tests.test_proposal_end_to_end import DEMO  # noqa: E402

# E02: the evening-build proposal, sent with the digest of the document it was read from.
DOCUMENT = "# Build schedule and cache rollout\n\nThe evening build never finishes.\n"
DIGEST = "sha256:" + hashlib.sha256(DOCUMENT.encode()).hexdigest()
FIRST = {**DEMO, "document_digest": DIGEST}
# A younger proposal for the same document: the first card should stand down.
YOUNGER = {
    **FIRST,
    "summary": "Retire the evening build",
    "rows": FIRST["rows"][:2],
}


def main() -> None:
    async def steps(client):
        first = await client.call_tool("kb_prepare_proposal", FIRST)
        younger = await client.call_tool("kb_prepare_proposal", YOUNGER)
        return first, younger

    with tempfile.TemporaryDirectory() as state:
        results = session(server_parameters(Path(state)), steps)
    for result, name in zip(results, ("proposal", "proposal.younger"), strict=True):
        assert not result.is_error, result.content
        out = HERE / f"{name}.result.json"
        out.write_text(json.dumps(result.structured_content, indent=2) + "\n")
        sys.stdout.write(f"wrote {out}\n")


if __name__ == "__main__":
    main()
