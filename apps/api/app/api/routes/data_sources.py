from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.data_source import DataSource
from app.schemas.data_source import DataSourceResponse

router = APIRouter(prefix="/data-sources", tags=["provenance"])


@router.get("/{source_id}", response_model=DataSourceResponse)
def get_data_source(source_id: UUID, db: Annotated[Session, Depends(get_db)]):
    source = db.get(DataSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    return source
