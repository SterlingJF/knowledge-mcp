from __future__ import annotations

from importlib import resources
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from knowledge_mcp import conventions, schemas
from knowledge_mcp.models_auto.convention_templates_schema import (
    ConventionTemplatesAnswer,
)


def catalog(location: str) -> dict[str, Any]:
    resource = resources.files("knowledge_mcp") / "convention_templates.yaml"
    data = {
        "schema": "knowledge-mcp/convention-templates/1",
        "location": location,
        **yaml.safe_load(resource.read_text(encoding="utf-8")),
    }
    Draft202012Validator(schemas.listed("convention-templates")).validate(data)
    answer = ConventionTemplatesAnswer.model_validate(data)
    seen = set()
    for template in answer.templates:
        if template.id in seen:
            message = "Use unique template identifiers."
            raise ValueError(message)
        seen.add(template.id)
        sources = {source.url for source in template.sources}
        variants = set()
        for variant in template.variants:
            if variant.id in variants:
                message = "Use unique variant identifiers within each template."
                raise ValueError(message)
            variants.add(variant.id)
            if not set(variant.folder_sources + variant.name_sources) <= sources:
                message = "Declare every variant source in the template sources."
                raise ValueError(message)
            pattern = variant.model_dump(mode="json", exclude_none=True)
            pattern.setdefault("folder", [])
            conventions.validate_pattern(pattern, "#/templates")
    return answer.model_dump(mode="json", by_alias=True, exclude_unset=True)
