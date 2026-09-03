# File: server/app/dependencies.py
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.config import read_config
from app.knowledge_model import KnowledgeModel
from app.store.file_store import FileStore
from app.store.service import ArtifactService
from app.store.vaults import VAULT_HEADER, VaultStores


def get_store(request: Request) -> FileStore:
    """Request vault from `X-Km-Vault`, falling back to process default (`VaultStores.resolve`)."""
    vaults: VaultStores = request.app.state.vaults
    known = {
        identifier: entry.path for identifier, entry in read_config().stores.items()
    }
    return vaults.resolve(request.headers.get(VAULT_HEADER), known)


def get_knowledge_model(request: Request) -> KnowledgeModel:
    return request.app.state.knowledge_model


def get_artifact_service(request: Request) -> ArtifactService:
    return ArtifactService(get_store(request), request.app.state.knowledge_model)


FileStoreDep = Annotated[FileStore, Depends(get_store)]
KnowledgeModelDep = Annotated[KnowledgeModel, Depends(get_knowledge_model)]
ArtifactServiceDep = Annotated[ArtifactService, Depends(get_artifact_service)]
