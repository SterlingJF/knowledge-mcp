# File: server/app/knowledge_model/__init__.py
from __future__ import annotations

import sys
from pathlib import Path

from app.knowledge_model.loader import (
    ArtifactTypeIndex,
    CompositionEntry,
    ElementIndex,
    GuidanceIndex,
    KnowledgeModel,
    UniverseIndex,
)

__all__ = [
    'ArtifactTypeIndex',
    'CompositionEntry',
    'ElementIndex',
    'GuidanceIndex',
    'KnowledgeModel',
    'UniverseIndex',
    'resolve_knowledge_model_dir',
]

BUNDLE_DIR_NAME = 'knowledge-model'


def resolve_knowledge_model_dir(override: Path | None = None) -> Path:
    if override is not None:
        return Path(override).expanduser()

    frozen_base = getattr(sys, '_MEIPASS', None)
    if frozen_base is not None:
        return Path(frozen_base) / BUNDLE_DIR_NAME

    # server/app/knowledge_model → server/app → server → repo root
    return Path(__file__).resolve().parents[2].parent / BUNDLE_DIR_NAME
