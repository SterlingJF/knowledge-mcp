from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--write-snapshots",
        action="store_true",
        help=(
            "Rewrite contracts/extensions/mcp/v1/tools.json and the pass samples from the "
            "server's answers."
        ),
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
