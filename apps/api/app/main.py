from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.asset_om import router as asset_om_router
from app.api.routes.assets import router as assets_router
from app.api.routes.data_sources import router as data_sources_router
from app.api.routes.health import router as health_router
from app.api.routes.media import router as media_router
from app.api.routes.rag_lite import router as rag_lite_router
from app.api.routes.research_workflow import router as research_workflow_router
from app.api.routes.reservoirs import router as reservoirs_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(research_workflow_router, prefix="/api/v1")
app.include_router(rag_lite_router, prefix="/api/v1")
app.include_router(media_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")
app.include_router(asset_om_router, prefix="/api/v1")
app.include_router(data_sources_router, prefix="/api/v1")

app.include_router(
    health_router,
    prefix="/api/v1",
)

app.include_router(
    reservoirs_router,
    prefix="/api/v1",
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "environment": settings.app_env,
    }
