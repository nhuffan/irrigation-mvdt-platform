# Irrigation MVDT Platform

Next.js · FastAPI · PostgreSQL/PostGIS · MapLibre · CesiumJS.

Nghiên cứu: [dataset/import/freeze](research/dataset/README.md) · [evaluation protocol](research/evaluation/protocol.md).

Experimental future work: [historical evidence search preview](research/ai-poc/README.md).

## Chạy local

Từ root, với Docker Desktop đang chạy và dependencies/env đã được cấu hình:

```sh
pnpm db:up
pnpm db:migrate
pnpm db:seed
pnpm db:seed:assets  # development assets + O&M; mặc định reservoir DT001
pnpm db:seed:media   # development PDF/PNG/GLB; chạy sau assets seed
pnpm dev:api  # terminal 1
pnpm dev:web  # terminal 2
```

Web: http://localhost:3000 · Swagger: http://localhost:8000/docs.
Dừng frontend/API bằng Ctrl+C; `pnpm db:down` dừng database và giữ volume.

## Kiểm tra

```sh
pnpm lint:api
pnpm lint:web
pnpm build:web
pnpm --dir apps/web test:media
cd apps/api && uv run python -m pytest -q
```

API tests cần local PostGIS đã migrate; dữ liệu test được rollback.

Seed cho reservoir khác: `cd apps/api && uv run python -m scripts.seed_dev --reservoir-code <CODE>`. Chỉ chạy trên database development.

Import document: `cd apps/api && uv run python -m scripts.import_documents --source-code <SOURCE_CODE> --file <PATH> --document-code <CODE>`. File không được commit; khi triển khai cần backup cả database và storage.
