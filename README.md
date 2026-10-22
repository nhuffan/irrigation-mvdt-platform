# Irrigation MVDT Platform

Next.js · FastAPI · PostgreSQL/PostGIS · MapLibre · CesiumJS.

Nghiên cứu: [dataset/import/freeze](research/dataset/README.md) · [evaluation protocol](research/evaluation/protocol.md).

Experimental future work: [historical evidence search preview](research/ai-poc/README.md).

## Chạy local

Từ root, với Docker Desktop đang chạy, dependencies/env và database/storage hiện có đã được cấu hình:

```sh
pnpm db:up   # nếu database local chưa chạy
pnpm dev:api # terminal 1 — http://localhost:8000
pnpm dev:web # terminal 2 — http://localhost:3000
```

Web: http://localhost:3000 · Swagger: http://localhost:8000/docs. Kiểm tra instance đang dùng cổng 3000/8000 trước khi khởi chạy; dùng lại đúng instance của project, không mở stack thứ hai.

**AI Research Preview — Experimental / Future Work** dùng chung web/API trên. Mặc định `RAG_LITE_ENABLED=false`. Để bật, thay lệnh trong terminal API bằng:

```sh
RAG_LITE_ENABLED=true RAG_LITE_ALLOWLIST_PATH="$PWD/storage/rag-lite/allowlist.json" pnpm dev:api
```

Mở [AI Research Preview](http://localhost:3000/ai-research-preview) từ navigation. Cần allowlist đã được cấp quyền, checksum hợp lệ và index local hiện có; xem [cấu hình và demo](research/ai-poc/README.md). Đây là tìm kiếm bằng chứng lịch sử, chỉ đọc; chưa kết nối LLM bên ngoài, sinh câu trả lời, OCR, dự đoán hiện trạng, tư vấn vận hành hay xác nhận chuyên môn độc lập. Đặt `RAG_LITE_ENABLED=false` và khởi động lại API để tắt preview.

Không migrate, seed lại hoặc reset database nghiên cứu hiện có để chạy preview. Chỉ khi khởi tạo database development mới: `pnpm db:migrate`, `pnpm db:seed`, `pnpm db:seed:assets`, rồi `pnpm db:seed:media`; seed không phải dữ liệu nghiên cứu đã xác minh.

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
