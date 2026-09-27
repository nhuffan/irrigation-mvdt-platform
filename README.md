# Irrigation MVDT Platform

Monorepo Next.js + FastAPI + PostgreSQL/PostGIS theo [setup guide](docs/SETUP_GUIDE.md).

## Cài đặt

Yêu cầu Git, Docker Desktop đang chạy, Node >=20.9, pnpm 11.19.0, Python >=3.12 và uv.

```sh
pnpm install
cd apps/api
uv sync
cp .env.example .env
# Sửa DATABASE_URL thành postgresql+psycopg://mvdt:mvdt_dev_password@localhost:5432/mvdt cho DB development.
cd ../..
cp apps/web/.env.example apps/web/.env.local
pnpm db:up
pnpm db:migrate
pnpm db:seed
```

Seed chạy lại được, chỉ dùng để kiểm tra phần mềm; không phải dataset nghiên cứu đã xác minh.
Local .env đã được cấu hình khi setup lần đầu và bị loại khỏi Git.

## Chạy

Hai terminal từ root:

```sh
pnpm dev:api
```

```sh
pnpm dev:web
```

- Web: http://localhost:3000
- API: http://localhost:8000/api/v1/reservoirs
- Health: http://localhost:8000/api/v1/health
- Swagger: http://localhost:8000/docs

PostGIS dùng Docker named volume, port chỉ bind localhost. `pnpm db:down` dừng DB nhưng giữ dữ liệu.
MapLibre worker tự copy khi chạy dev/build, không đưa file sinh ra vào Git.

## Kiểm tra

```sh
pnpm lint:api
pnpm lint:web
pnpm build:web
```

Chưa triển khai map UI, authentication, asset, inspection, SCADA hoặc 3D.

Image PostGIS 17-3.5 dùng `platform: linux/amd64` để chạy trên Apple Silicon. Alembic bỏ qua các bảng reflected ngoài metadata nhằm bảo vệ bảng extension; khi xóa model, cần viết migration drop rõ ràng.
