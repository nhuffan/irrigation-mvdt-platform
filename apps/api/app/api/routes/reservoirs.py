from typing import Annotated

from fastapi import APIRouter, Depends
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


@router.get(
    "",
    response_model=list[ReservoirResponse],
)
def get_reservoirs(
    db: Annotated[Session, Depends(get_db)],
) -> list[ReservoirResponse]:
    stmt = select(
        Reservoir.id,
        Reservoir.code,
        Reservoir.name,
        Reservoir.province,
        Reservoir.data_status,
        Reservoir.mvdt_level,
        Reservoir.description,
        ST_X(Reservoir.location).label("longitude"),
        ST_Y(Reservoir.location).label("latitude"),
    ).order_by(Reservoir.name)

    rows = db.execute(stmt).mappings().all()

    return [ReservoirResponse(**row) for row in rows]
