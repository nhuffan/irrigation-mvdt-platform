from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.reservoir import Reservoir
from app.schemas.reservoir import ReservoirResponse

router = APIRouter(
    prefix="/reservoirs",
    tags=["reservoirs"],
)


def reservoir_query():
    return select(
        Reservoir.id,
        Reservoir.code,
        Reservoir.name,
        Reservoir.province,
        Reservoir.data_status,
        Reservoir.mvdt_level,
        Reservoir.description,
        ST_X(Reservoir.location).label("longitude"),
        ST_Y(Reservoir.location).label("latitude"),
    )


@router.get("", response_model=list[ReservoirResponse])
def get_reservoirs(db: Annotated[Session, Depends(get_db)]) -> list[ReservoirResponse]:
    rows = db.execute(reservoir_query().order_by(Reservoir.name)).mappings().all()
    return [ReservoirResponse(**row) for row in rows]


@router.get("/{reservoir_id}", response_model=ReservoirResponse)
def get_reservoir(
    reservoir_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> ReservoirResponse:
    row = (
        db.execute(reservoir_query().where(Reservoir.id == reservoir_id))
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Reservoir not found")
    return ReservoirResponse(**row)
