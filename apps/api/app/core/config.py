from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    storage_root: Path = Path(__file__).resolve().parents[4] / "storage"

    asset_locations_path: Path | None = None

    reviewed_provenance_path: Path | None = None

    # Local-only experimental retrieval. No provider credentials or network adapter.
    rag_lite_enabled: bool = False
    rag_lite_allowlist_path: Path | None = None
    rag_lite_index_dir: Path = Path(__file__).resolve().parents[4] / "storage/rag-lite"
    rag_lite_max_context_chars: int = 12000

    mcp_enabled: bool = Field(default=False, validation_alias="MVDT_MCP_ENABLED")
    mcp_grant_path: Path | None = Field(
        default=None, validation_alias="MVDT_MCP_GRANT_PATH"
    )

    app_name: str = "MVDT API"
    app_env: str = "development"

    database_url: str
    frontend_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
