from uuid import UUID

from pydantic import BaseModel


class ReservoirResponse(BaseModel):
    id: UUID
    code: str
    name: str
    province: str | None
    data_status: str
    mvdt_level: int
    description: str | None

    longitude: float
    latitude: float
