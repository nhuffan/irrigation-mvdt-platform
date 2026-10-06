from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select, union
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.data_source import DataSource
from app.models.media import Document, Model, ModelAssetLink
from app.models.reservoir import Reservoir
from app.schemas.media import DocumentResponse, ModelAssetLinkResponse, ModelResponse
from app.services.om_service import RECORD_TYPES, require_asset
from app.services.storage_service import get_storage
from app.storage.base import Storage

router = APIRouter(tags=["Documents and 3D"])


def required(db, model, id):
    record = db.get(model, id)
    if record is None:
        raise HTTPException(404, "Resource not found")
    return record


def content(record, storage, download=False):
    try:
        path = storage.path(record.storage_key)
        if not path.is_file():
            raise HTTPException(410, "Metadata exists, but the file is unavailable")
    except ValueError:
        raise HTTPException(410, "Stored file is unavailable") from None
    mime = record.mime_type if isinstance(record, Document) else "model/gltf-binary"
    safe = mime in {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
    }
    filename = (
        record.original_file_name if isinstance(record, Document) else "model.glb"
    )
    return FileResponse(
        path,
        media_type=mime
        if safe or isinstance(record, Model)
        else "application/octet-stream",
        filename=filename,
        content_disposition_type="inline" if safe and not download else "attachment",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
            "Cache-Control": "no-store",
        },
    )


@router.get(
    "/data-sources/{source_id}/documents", response_model=list[DocumentResponse]
)
def source_documents(source_id: UUID, db: Annotated[Session, Depends(get_db)]):
    required(db, DataSource, source_id)
    return list(
        db.scalars(
            select(Document)
            .where(Document.source_id == source_id)
            .options(selectinload(Document.source))
            .order_by(Document.document_code)
        )
    )


@router.get("/assets/{asset_id}/documents", response_model=list[DocumentResponse])
def asset_documents(asset_id: UUID, db: Annotated[Session, Depends(get_db)]):
    require_asset(db, asset_id)
    sources = union(
        *(
            select(model.source_id).where(
                model.asset_id == asset_id, model.source_id.is_not(None)
            )
            for model, _, _ in RECORD_TYPES.values()
        )
    )
    return list(
        db.scalars(
            select(Document)
            .where(Document.source_id.in_(sources))
            .options(selectinload(Document.source))
            .order_by(Document.document_code)
        )
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def document_detail(document_id: UUID, db: Annotated[Session, Depends(get_db)]):
    return required(db, Document, document_id)


@router.get("/documents/{document_id}/content")
def document_content(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[Storage, Depends(get_storage)],
    download: bool = False,
):
    return content(required(db, Document, document_id), storage, download)


@router.get("/reservoirs/{reservoir_id}/models", response_model=list[ModelResponse])
def reservoir_models(reservoir_id: UUID, db: Annotated[Session, Depends(get_db)]):
    required(db, Reservoir, reservoir_id)
    return list(
        db.scalars(
            select(Model)
            .where(Model.reservoir_id == reservoir_id)
            .options(selectinload(Model.source))
            .order_by(Model.model_code)
        )
    )


@router.get("/models/{model_id}", response_model=ModelResponse)
def model_detail(model_id: UUID, db: Annotated[Session, Depends(get_db)]):
    return required(db, Model, model_id)


@router.get("/models/{model_id}/content")
def model_content(
    model_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[Storage, Depends(get_storage)],
):
    model = required(db, Model, model_id)
    if model.format != "GLB":
        raise HTTPException(
            415, "This viewer currently supports self-contained GLB files"
        )
    return content(model, storage)


@router.get(
    "/models/{model_id}/asset-links", response_model=list[ModelAssetLinkResponse]
)
def model_links(model_id: UUID, db: Annotated[Session, Depends(get_db)]):
    required(db, Model, model_id)
    return list(
        db.scalars(
            select(ModelAssetLink)
            .where(ModelAssetLink.model_id == model_id)
            .order_by(ModelAssetLink.object_key)
        )
    )


@router.get(
    "/assets/{asset_id}/model-links", response_model=list[ModelAssetLinkResponse]
)
def asset_links(asset_id: UUID, db: Annotated[Session, Depends(get_db)]):
    require_asset(db, asset_id)
    return list(
        db.scalars(
            select(ModelAssetLink)
            .where(ModelAssetLink.asset_id == asset_id)
            .order_by(ModelAssetLink.object_key)
        )
    )
