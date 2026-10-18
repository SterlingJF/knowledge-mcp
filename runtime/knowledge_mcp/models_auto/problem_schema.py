# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class ArgumentError(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    detail: str
    pointer: Annotated[
        str,
        Field(
            description='JSON Pointer into the arguments as sent, such as "#/entries/0/document_type".',
            pattern="^#(/([^~/]|~[01])*)*$",
        ),
    ]


class ProblemDetails(BaseModel):
    """
    An error from a knowledge-mcp tool, as RFC 9457 problem details. On failure, `kb type --json` and `kb doctor --json` print a problem object as the last stderr line. Branch on `type`.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    type: Literal[
        "https://github.com/SterlingJF/knowledge-mcp/problems/argument-invalid",
        "https://github.com/SterlingJF/knowledge-mcp/problems/scope-invalid",
        "https://github.com/SterlingJF/knowledge-mcp/problems/digest-unknown",
        "https://github.com/SterlingJF/knowledge-mcp/problems/record-invalid",
        "https://github.com/SterlingJF/knowledge-mcp/problems/document-type-unknown",
        "https://github.com/SterlingJF/knowledge-mcp/problems/kbp-failed",
        "https://github.com/SterlingJF/knowledge-mcp/problems/kbp-version-skew",
        "https://github.com/SterlingJF/knowledge-mcp/problems/internal-error",
        "https://github.com/SterlingJF/knowledge-mcp/problems/move-invalid",
        "https://github.com/SterlingJF/knowledge-mcp/problems/move-input-incomplete",
    ]
    title: str
    detail: Annotated[
        str,
        Field(
            description="For MCP errors, the last text block contains the same detail.",
            min_length=1,
        ),
    ]
    errors: Annotated[list[ArgumentError] | None, Field(min_length=1)] = None
