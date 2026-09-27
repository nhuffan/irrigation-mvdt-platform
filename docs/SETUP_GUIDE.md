# SETUP GUIDE — GIS-BASED MVDT WEB PLATFORM

> **Project scope của tài liệu này:** tạo project từ số 0 đến khi:
>
> 1. Repository chạy theo mô hình monorepo.
> 2. PostgreSQL + PostGIS chạy bằng Docker.
> 3. FastAPI kết nối được database.
> 4. Có bảng `reservoirs` chứa dữ liệu hồ.
> 5. API `GET /api/v1/reservoirs` trả dữ liệu từ PostgreSQL/PostGIS.
> 6. Next.js gọi được API và hiển thị danh sách hồ.
> 7. Cài MapLibre sẵn để bắt đầu Stage tiếp theo.
>
> **Chưa làm trong tài liệu này:** Asset, Inspection, Repair, Maintenance, Document Storage, Authentication, 3D/Cesium, SCADA.

---

## 0. Kiến trúc sau khi hoàn tất guide

```text
Browser
   │
   ▼
Next.js
localhost:3000
   │
   │ HTTP GET /api/v1/reservoirs
   ▼
FastAPI
localhost:8000
   │
   ▼
SQLAlchemy / GeoAlchemy2
   │
   ▼
PostgreSQL + PostGIS
localhost:5432
```

Repository:

```text
irrigation-mvdt-platform/
│
├── apps/
│   ├── web/                 # Next.js
│   └── api/                 # FastAPI
│
├── database/
│   └── init/
│
├── gis/
│   ├── raw/
│   ├── processed/
│   └── qgis/
│
├── docs/
│
├── docker-compose.yml
├── package.json
├── pnpm-workspace.yaml
├── .gitignore
├── .env.example
└── README.md
```

---

# 1. Prerequisites

## 1.1. Required tools

Cài trước:

- Git
- Docker Desktop
- Node.js >= 20.9
- pnpm
- Python 3.12+
- uv
- VS Code hoặc IDE tương đương

Kiểm tra:

```bash
git --version
docker --version
node --version
pnpm --version
python3 --version
uv --version
```

Nếu chưa có `pnpm`:

```bash
npm install -g pnpm
```

Nếu chưa có `uv` trên macOS/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Sau đó mở terminal mới và kiểm tra:

```bash
uv --version
```

---

# 2. Create Git repository

## 2.1. Tạo project

```bash
mkdir irrigation-mvdt-platform
cd irrigation-mvdt-platform

git init
git branch -M main
```

## 2.2. Tạo folder cơ bản

```bash
mkdir -p apps
mkdir -p database/init
mkdir -p gis/raw
mkdir -p gis/processed
mkdir -p gis/qgis
mkdir -p docs
```

---

# 3. Root workspace setup

Tạo file:

```text
package.json
```

Nội dung:

```json
{
  "name": "irrigation-mvdt-platform",
  "private": true,
  "scripts": {
    "dev:web": "pnpm --dir apps/web dev",
    "dev:api": "cd apps/api && uv run fastapi dev app/main.py",
    "db:up": "docker compose up -d db",
    "db:down": "docker compose down",
    "db:logs": "docker compose logs -f db"
  }
}
```

Tạo:

```text
pnpm-workspace.yaml
```

```yaml
packages:
  - "apps/web"
```

---

# 4. Root `.gitignore`

Tạo file:

```text
.gitignore
```

```gitignore
# macOS
.DS_Store

# Environment variables
.env
.env.local
.env.*.local

# Node
node_modules/
.next/
out/

# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/

# IDE
.vscode/
.idea/

# Local DB / Docker
postgres_data/

# GIS temporary/export files
gis/raw/*
!gis/raw/.gitkeep

# User uploads
storage/
```

Tạo placeholder:

```bash
touch gis/raw/.gitkeep
```

---

# 5. PostgreSQL + PostGIS with Docker

Đối với project này không dùng PostgreSQL thường. Dùng PostGIS vì về sau cần:

- Point cho vị trí hồ/cống.
- LineString cho kênh.
- Polygon cho đập/khu vực.
- Spatial query.
- GIS indexing.

## 5.1. Tạo `docker-compose.yml`

Ở root:

```yaml
services:
  db:
    image: postgis/postgis:17-3.5
    container_name: mvdt-postgis
    restart: unless-stopped

    environment:
      POSTGRES_DB: mvdt
      POSTGRES_USER: mvdt
      POSTGRES_PASSWORD: mvdt_dev_password

    ports:
      - "5432:5432"

    volumes:
      - postgres_data:/var/lib/postgresql/data

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mvdt -d mvdt"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  postgres_data:
```

> Trong development dùng password đơn giản được. Production tuyệt đối không commit password thật.

## 5.2. Start database

```bash
docker compose up -d db
```

Kiểm tra:

```bash
docker compose ps
```

Kỳ vọng:

```text
mvdt-postgis   ...   Up (healthy)
```

Xem logs:

```bash
docker compose logs -f db
```

Thoát log:

```text
Ctrl + C
```

---

# 6. Verify PostGIS

Mở `psql` bên trong container:

```bash
docker exec -it mvdt-postgis psql -U mvdt -d mvdt
```

Trong PostgreSQL:

```sql
SELECT version();
```

Kiểm tra PostGIS:

```sql
SELECT PostGIS_Version();
```

Có version trả về là OK.

Thoát:

```sql
\q
```

---

# 7. Create FastAPI backend

Đi vào:

```bash
cd apps
mkdir api
cd api
```

Khởi tạo Python project bằng `uv`:

```bash
uv init --bare
```

## 7.1. Add dependencies

```bash
uv add "fastapi[standard]"
uv add sqlalchemy
uv add "psycopg[binary]"
uv add geoalchemy2
uv add alembic
uv add pydantic-settings
```

Dev dependencies:

```bash
uv add --dev pytest
uv add --dev ruff
```

Sau bước này sẽ có:

```text
apps/api/
├── pyproject.toml
└── uv.lock
```

---

# 8. Backend folder structure

Tạo:

```bash
mkdir -p app/api/routes
mkdir -p app/core
mkdir -p app/db
mkdir -p app/models
mkdir -p app/schemas
mkdir -p app/services

touch app/__init__.py
touch app/api/__init__.py
touch app/api/routes/__init__.py
touch app/core/__init__.py
touch app/db/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/services/__init__.py
```

Structure:

```text
apps/api/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   └── routes/
│   │       ├── health.py
│   │       └── reservoirs.py
│   │
│   ├── core/
│   │   └── config.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   │
│   ├── models/
│   │   └── reservoir.py
│   │
│   └── schemas/
│       └── reservoir.py
│
├── alembic/
├── alembic.ini
├── .env
├── .env.example
├── pyproject.toml
└── uv.lock
```

---

# 9. Backend environment variables

Tạo:

```text
apps/api/.env
```

```env
APP_NAME=MVDT API
APP_ENV=development

DATABASE_URL=postgresql+psycopg://mvdt:mvdt_dev_password@localhost:5432/mvdt

FRONTEND_ORIGIN=http://localhost:3000
```

Tạo:

```text
apps/api/.env.example
```

```env
APP_NAME=MVDT API
APP_ENV=development

DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/DATABASE

FRONTEND_ORIGIN=http://localhost:3000
```

Không commit `.env`.

---

# 10. FastAPI settings

Tạo:

```text
apps/api/app/core/config.py
```

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MVDT API"
    app_env: str = "development"

    database_url: str
    frontend_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
```

---

# 11. SQLAlchemy Base

Tạo:

```text
apps/api/app/db/base.py
```

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

---

# 12. Database session

Tạo:

```text
apps/api/app/db/session.py
```

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
```

---

# 13. Reservoir model

Tạo:

```text
apps/api/app/models/reservoir.py
```

```python
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Reservoir(Base):
    __tablename__ = "reservoirs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    province: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    data_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REGISTERED",
    )

    mvdt_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    location = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
            spatial_index=True,
        ),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

---

# 14. Import models into Base metadata

Sửa:

```text
apps/api/app/db/base.py
```

thành:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so Alembic can discover them.
from app.models.reservoir import Reservoir  # noqa: E402, F401
```

---

# 15. Setup Alembic

Đứng trong:

```text
apps/api
```

chạy:

```bash
uv run alembic init alembic
```

Sau đó có:

```text
apps/api/
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
└── alembic.ini
```

---

# 16. Configure Alembic

Mở:

```text
apps/api/alembic/env.py
```

Tìm:

```python
target_metadata = None
```

thay bằng:

```python
from app.core.config import settings
from app.db.base import Base

target_metadata = Base.metadata
```

Sau đó set URL:

```python
config.set_main_option("sqlalchemy.url", settings.database_url)
```

Phần đầu file nên có logic tương tự:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base


config = context.config

config.set_main_option(
    "sqlalchemy.url",
    settings.database_url,
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
```

---

# 17. Create first migration

Đảm bảo DB đang chạy:

```bash
docker compose ps
```

Từ `apps/api`:

```bash
uv run alembic revision --autogenerate -m "create reservoirs table"
```

Kiểm tra file vừa sinh trong:

```text
alembic/versions/
```

Sau đó migrate:

```bash
uv run alembic upgrade head
```

---

# 18. Verify table

```bash
docker exec -it mvdt-postgis psql -U mvdt -d mvdt
```

Trong `psql`:

```sql
\dt
```

Kỳ vọng có:

```text
alembic_version
reservoirs
```

Kiểm tra table:

```sql
\d reservoirs
```

Kiểm tra geometry:

```sql
SELECT
    f_table_name,
    f_geometry_column,
    type,
    srid
FROM geometry_columns;
```

Kỳ vọng:

```text
reservoirs | location | POINT | 4326
```

Thoát:

```sql
\q
```

---

# 19. Insert development data

> Đây chỉ là seed dữ liệu development để xác nhận architecture hoạt động. Tọa độ/dữ liệu nghiên cứu chính thức phải thay bằng dataset đã được xác minh trong Phase 1.

Mở:

```bash
docker exec -it mvdt-postgis psql -U mvdt -d mvdt
```

Insert:

```sql
INSERT INTO reservoirs (
    id,
    code,
    name,
    province,
    data_status,
    mvdt_level,
    description,
    location
)
VALUES (
    gen_random_uuid(),
    'DT001',
    'Dau Tieng Reservoir',
    'Tay Ninh',
    'MVDT_AVAILABLE',
    3,
    'Development seed record for API integration testing.',
    ST_SetSRID(
        ST_MakePoint(106.30, 11.35),
        4326
    )
);
```

Thêm một hồ placeholder:

```sql
INSERT INTO reservoirs (
    id,
    code,
    name,
    province,
    data_status,
    mvdt_level,
    description,
    location
)
VALUES (
    gen_random_uuid(),
    'DEMO002',
    'Example Reservoir',
    'Example Province',
    'DATA_COLLECTION',
    1,
    'Placeholder record for platform testing.',
    ST_SetSRID(
        ST_MakePoint(106.00, 11.00),
        4326
    )
);
```

Kiểm tra:

```sql
SELECT
    code,
    name,
    data_status,
    mvdt_level,
    ST_X(location) AS longitude,
    ST_Y(location) AS latitude
FROM reservoirs;
```

Thoát:

```sql
\q
```

---

# 20. Pydantic reservoir schema

Tạo:

```text
apps/api/app/schemas/reservoir.py
```

```python
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
```

---

# 21. Health API

Tạo:

```text
apps/api/app/api/routes/health.py
```

```python
from fastapi import APIRouter


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
    }
```

---

# 22. Reservoir API

Tạo:

```text
apps/api/app/api/routes/reservoirs.py
```

```python
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
    db: Session = Depends(get_db),
) -> list[ReservoirResponse]:
    stmt = (
        select(
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
        .order_by(Reservoir.name)
    )

    rows = db.execute(stmt).mappings().all()

    return [
        ReservoirResponse(**row)
        for row in rows
    ]
```

---

# 23. FastAPI application

Tạo:

```text
apps/api/app/main.py
```

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
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
```

---

# 24. Run FastAPI

Từ:

```text
apps/api
```

chạy:

```bash
uv run fastapi dev app/main.py
```

Kỳ vọng:

```text
Uvicorn running on http://127.0.0.1:8000
```

---

# 25. Test API

Terminal khác:

```bash
curl http://localhost:8000/
```

Expected:

```json
{
  "name": "MVDT API",
  "environment": "development"
}
```

Health:

```bash
curl http://localhost:8000/api/v1/health
```

Expected:

```json
{
  "status": "ok"
}
```

Reservoir API:

```bash
curl http://localhost:8000/api/v1/reservoirs
```

Expected structure:

```json
[
  {
    "id": "...",
    "code": "DT001",
    "name": "Dau Tieng Reservoir",
    "province": "Tay Ninh",
    "data_status": "MVDT_AVAILABLE",
    "mvdt_level": 3,
    "description": "Development seed record for API integration testing.",
    "longitude": 106.3,
    "latitude": 11.35
  }
]
```

---

# 26. Swagger / OpenAPI

FastAPI tự sinh API docs.

Mở browser:

```text
http://localhost:8000/docs
```

Bạn phải thấy:

```text
GET /api/v1/health
GET /api/v1/reservoirs
```

Test trực tiếp bằng:

```text
Try it out
→ Execute
```

---

# 27. Setup Next.js frontend

Mở terminal mới.

Từ root repository:

```bash
pnpm create next-app@latest apps/web
```

Khi CLI hỏi, chọn:

```text
Would you like to use TypeScript?         Yes
Which linter?                             ESLint
Would you like to use React Compiler?     Yes
Would you like to use Tailwind CSS?       Yes
Would you like your code inside src/?     Yes
Would you like to use App Router?         Yes
Would you like to customize import alias? No
```

Sau đó:

```bash
cd apps/web
pnpm dev
```

Mở:

```text
http://localhost:3000
```

Next.js chạy được là OK.

---

# 28. Frontend environment

Tạo:

```text
apps/web/.env.local
```

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Tạo:

```text
apps/web/.env.example
```

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Restart Next.js sau khi thêm `.env.local`.

---

# 29. Define frontend type

Tạo:

```text
apps/web/src/types/reservoir.ts
```

Nếu chưa có folder:

```bash
mkdir -p src/types
```

Nội dung:

```typescript
export type Reservoir = {
  id: string;
  code: string;
  name: string;
  province: string | null;

  data_status: string;
  mvdt_level: number;

  description: string | null;

  longitude: number;
  latitude: number;
};
```

---

# 30. API client

Tạo:

```text
apps/web/src/lib/api.ts
```

```typescript
import type { Reservoir } from "@/types/reservoir";


const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000/api/v1";


export async function getReservoirs(): Promise<Reservoir[]> {
  const response = await fetch(
    `${API_BASE_URL}/reservoirs`,
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      `Failed to fetch reservoirs: ${response.status}`,
    );
  }

  return response.json();
}
```

---

# 31. Frontend page calling FastAPI

Thay nội dung:

```text
apps/web/src/app/page.tsx
```

bằng:

```tsx
import { getReservoirs } from "@/lib/api";


export default async function HomePage() {
  const reservoirs = await getReservoirs();

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-3xl font-semibold">
          Irrigation MVDT Platform
        </h1>

        <p className="mt-2 text-slate-600">
          Reservoir registry loaded from FastAPI + PostGIS.
        </p>

        <div className="mt-8 grid gap-4">
          {reservoirs.map((reservoir) => (
            <article
              key={reservoir.id}
              className="rounded-xl border bg-white p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-medium">
                    {reservoir.name}
                  </h2>

                  <p className="text-sm text-slate-500">
                    {reservoir.code}
                  </p>
                </div>

                <span className="rounded-full bg-slate-100 px-3 py-1 text-sm">
                  Level {reservoir.mvdt_level}
                </span>
              </div>

              <dl className="mt-4 grid gap-2 text-sm">
                <div>
                  <dt className="font-medium">
                    Province
                  </dt>
                  <dd>
                    {reservoir.province ?? "Unknown"}
                  </dd>
                </div>

                <div>
                  <dt className="font-medium">
                    Data Status
                  </dt>
                  <dd>
                    {reservoir.data_status}
                  </dd>
                </div>

                <div>
                  <dt className="font-medium">
                    Coordinates
                  </dt>
                  <dd>
                    {reservoir.latitude}, {reservoir.longitude}
                  </dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}
```

---

# 32. Run frontend + backend + database

Bạn cần 3 services.

## Terminal 1 — Database

Từ root:

```bash
docker compose up -d db
```

## Terminal 2 — Backend

```bash
cd apps/api
uv run fastapi dev app/main.py
```

## Terminal 3 — Frontend

```bash
cd apps/web
pnpm dev
```

Sau đó:

```text
Database: localhost:5432
API:      http://localhost:8000
Web:      http://localhost:3000
Swagger:  http://localhost:8000/docs
```

Mở:

```text
http://localhost:3000
```

Nếu thấy:

```text
Dau Tieng Reservoir
DT001
MVDT_AVAILABLE
Level 3
...
```

thì flow đã chạy:

```text
PostGIS
  ↓
FastAPI
  ↓
HTTP API
  ↓
Next.js
```

---

# 33. Install MapLibre

Bây giờ mới cài GIS client.

Từ:

```text
apps/web
```

```bash
pnpm add maplibre-gl
```

MapLibre 6 dùng ESM; với Next.js nên copy worker files sang `public` để worker và shared module nằm cùng origin.

Tạo:

```text
apps/web/scripts/copy-maplibre-worker.mjs
```

```javascript
import {
  copyFileSync,
  mkdirSync,
} from "node:fs";

import {
  createRequire,
} from "node:module";

import path from "node:path";


const require = createRequire(import.meta.url);

const dist = path.join(
  path.dirname(
    require.resolve("maplibre-gl/package.json"),
  ),
  "dist",
);

const dest = path.join(
  process.cwd(),
  "public",
  "maplibre",
);

mkdirSync(dest, {
  recursive: true,
});

for (
  const file of [
    "maplibre-gl-worker.mjs",
    "maplibre-gl-shared.mjs",
  ]
) {
  copyFileSync(
    path.join(dist, file),
    path.join(dest, file),
  );
}
```

Mở:

```text
apps/web/package.json
```

thêm các script `predev` và `prebuild`. Không xóa script hiện có:

```json
{
  "scripts": {
    "predev": "node ./scripts/copy-maplibre-worker.mjs",
    "dev": "next dev",
    "prebuild": "node ./scripts/copy-maplibre-worker.mjs",
    "build": "next build",
    "start": "next start",
    "lint": "eslint"
  }
}
```

> MapLibre chỉ được cài ở bước này. Stage tiếp theo mới tạo map component và đưa reservoir API thành GeoJSON/layer.

---

# 34. Root development commands

Quay về root.

DB:

```bash
pnpm db:up
```

API:

```bash
pnpm dev:api
```

Web:

```bash
pnpm dev:web
```

---

# 35. First Git commit

Kiểm tra:

```bash
git status
```

Đảm bảo không có:

```text
.env
.env.local
```

Add:

```bash
git add .
```

Commit:

```bash
git commit -m "chore: initialize MVDT platform"
```

---

# 36. Connect GitHub remote

Sau khi tạo empty repository trên GitHub:

```bash
git remote add origin git@github.com:<YOUR_USERNAME>/irrigation-mvdt-platform.git
```

Kiểm tra:

```bash
git remote -v
```

Push:

```bash
git push -u origin main
```

---

# 37. Recommended branch workflow

Không code trực tiếp mọi thứ trên `main`.

Ví dụ:

```bash
git checkout -b feature/reservoir-api
```

Sau khi hoàn thành:

```bash
git add .
git commit -m "feat: add reservoir API"
git push -u origin feature/reservoir-api
```

Các branch tiếp theo:

```text
feature/reservoir-map
feature/reservoir-detail
feature/asset-model
feature/asset-api
feature/asset-map
feature/inspection-module
feature/maintenance-module
feature/document-storage
```

---

# 38. Final folder structure

Sau guide này:

```text
irrigation-mvdt-platform/
│
├── apps/
│   │
│   ├── api/
│   │   ├── alembic/
│   │   │   └── versions/
│   │   │
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── routes/
│   │   │   │       ├── health.py
│   │   │   │       └── reservoirs.py
│   │   │   │
│   │   │   ├── core/
│   │   │   │   └── config.py
│   │   │   │
│   │   │   ├── db/
│   │   │   │   ├── base.py
│   │   │   │   └── session.py
│   │   │   │
│   │   │   ├── models/
│   │   │   │   └── reservoir.py
│   │   │   │
│   │   │   ├── schemas/
│   │   │   │   └── reservoir.py
│   │   │   │
│   │   │   └── main.py
│   │   │
│   │   ├── .env
│   │   ├── .env.example
│   │   ├── alembic.ini
│   │   ├── pyproject.toml
│   │   └── uv.lock
│   │
│   └── web/
│       ├── public/
│       │   └── maplibre/
│       │
│       ├── scripts/
│       │   └── copy-maplibre-worker.mjs
│       │
│       ├── src/
│       │   ├── app/
│       │   │   └── page.tsx
│       │   ├── lib/
│       │   │   └── api.ts
│       │   └── types/
│       │       └── reservoir.ts
│       │
│       ├── .env.local
│       ├── .env.example
│       └── package.json
│
├── database/
│   └── init/
│
├── docs/
│
├── gis/
│   ├── raw/
│   ├── processed/
│   └── qgis/
│
├── .gitignore
├── docker-compose.yml
├── package.json
├── pnpm-workspace.yaml
└── README.md
```

---

# 39. End-to-end verification checklist

## Repository

- [ ] Git repository initialized
- [ ] `main` branch exists
- [ ] `.gitignore` excludes secrets
- [ ] Monorepo folders exist

## Database

- [ ] Docker Desktop running
- [ ] PostGIS container healthy
- [ ] `SELECT PostGIS_Version()` works
- [ ] Alembic migration successful
- [ ] `reservoirs` table exists
- [ ] `location` is `POINT SRID 4326`
- [ ] Seed rows exist

## Backend

- [ ] FastAPI starts
- [ ] `/api/v1/health` returns 200
- [ ] `/api/v1/reservoirs` returns rows from PostGIS
- [ ] `/docs` works

## Frontend

- [ ] Next.js starts
- [ ] `NEXT_PUBLIC_API_BASE_URL` configured
- [ ] Next.js fetches `/reservoirs`
- [ ] Reservoir records render in browser
- [ ] No CORS error

## GIS dependency

- [ ] `maplibre-gl` installed
- [ ] Worker files copied to `public/maplibre`

---

# 40. Common errors

## Error: port 5432 already in use

Kiểm tra:

```bash
lsof -i :5432
```

Nếu máy đã có PostgreSQL local, đổi Docker port:

```yaml
ports:
  - "5433:5432"
```

Backend `.env`:

```env
DATABASE_URL=postgresql+psycopg://mvdt:mvdt_dev_password@localhost:5433/mvdt
```

---

## Error: `uv: command not found`

Restart terminal.

Hoặc cài lại:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Error: FastAPI cannot connect to database

Kiểm tra:

```bash
docker compose ps
```

Test database:

```bash
docker exec -it mvdt-postgis psql -U mvdt -d mvdt
```

Kiểm tra `.env`:

```env
DATABASE_URL=postgresql+psycopg://mvdt:mvdt_dev_password@localhost:5432/mvdt
```

---

## Error: `relation "reservoirs" does not exist`

Migration chưa chạy:

```bash
cd apps/api
uv run alembic upgrade head
```

---

## Error: CORS

Backend `.env`:

```env
FRONTEND_ORIGIN=http://localhost:3000
```

Restart FastAPI.

---

## Error: Next.js `fetch failed`

Kiểm tra API trước:

```bash
curl http://localhost:8000/api/v1/reservoirs
```

Nếu curl fail thì sửa backend trước.

Nếu curl OK, kiểm tra:

```text
apps/web/.env.local
```

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Restart:

```bash
pnpm dev
```

---

## Error: Alembic cannot find `app`

Phải chạy Alembic từ:

```text
apps/api
```

Đúng:

```bash
cd apps/api
uv run alembic upgrade head
```

---

# 41. Definition of Done cho Setup Stage

Setup stage hoàn thành khi:

```text
docker compose up -d db
        ↓
PostGIS healthy
        ↓
uv run fastapi dev app/main.py
        ↓
GET /api/v1/reservoirs
        ↓
data from PostgreSQL
        ↓
pnpm dev
        ↓
Next.js calls FastAPI
        ↓
reservoirs displayed in browser
```

**Quan trọng:** API phải lấy dữ liệu từ database thật. Không dùng hard-coded array ở FastAPI hoặc mock JSON ở frontend để đánh dấu stage này hoàn thành.

---

# 42. Stage tiếp theo sau tài liệu này

Sau khi guide này chạy ổn:

```text
Stage 1
Reservoir GIS Map
        ↓
Stage 2
Reservoir Detail
        ↓
Stage 3
Asset Model + Asset API
        ↓
Stage 4
Asset GIS Layer
        ↓
Stage 5
Asset Detail
        ↓
Stage 6
Inspection / Repair / Maintenance
        ↓
Stage 7
Legacy Data Source + Provenance
        ↓
Stage 8
Documents
        ↓
Stage 9
Admin / Reservoir Onboarding
        ↓
Stage 10
Optional 3D / Cesium
        ↓
Future
SCADA / realtime
```

---

# 43. Technology decisions used in this setup

| Component | Technology | Reason |
|---|---|---|
| Monorepo | Git + pnpm workspace | Frontend/backend cùng project nhưng tách app |
| Frontend | Next.js App Router + TypeScript | Web platform/dashboard |
| Backend | FastAPI | API layer rõ ràng, Python thuận tiện cho data/GIS |
| Python manager | uv | Fast dependency/project workflow |
| Database | PostgreSQL | Relational asset/O&M data |
| Spatial database | PostGIS | Geometry + spatial indexing/query |
| ORM | SQLAlchemy | Backend data layer |
| Spatial ORM | GeoAlchemy2 | PostGIS geometry support |
| Migration | Alembic | Version database schema |
| GIS frontend | MapLibre GL JS | Interactive web GIS |
| Dev database | Docker Compose | Reproducible local setup |

---

# 44. Notes for research data

Các dữ liệu dùng trong development như:

```text
Dau Tieng Reservoir
106.30
11.35
MVDT Level 3
```

trong guide này chỉ nhằm xác nhận software architecture.

Khi chuyển sang dữ liệu nghiên cứu:

1. Không tự suy đoán tọa độ.
2. Không tự tạo asset chính thức.
3. Chỉ import asset/dataset đã đi qua Phase 1 — Asset Inventory & Legacy Data Audit.
4. Mỗi dữ liệu quan trọng nên giữ `source_id`/provenance ở stage sau.
5. Hồ chưa đủ dữ liệu vẫn có thể nằm trên GIS ở `REGISTERED` hoặc `DATA_COLLECTION`.
6. Chỉ công trình đáp ứng MVDT criteria mới chuyển sang `MVDT_AVAILABLE`.

---

# 45. Official references checked for this setup

- Next.js documentation: https://nextjs.org/docs
- Next.js support policy: https://nextjs.org/support-policy
- FastAPI tutorial: https://fastapi.tiangolo.com/tutorial/
- PostGIS Docker image: https://hub.docker.com/r/postgis/postgis
- MapLibre GL JS documentation: https://maplibre.org/maplibre-gl-js/docs/
