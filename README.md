# Irrigation MVDT Platform

Next.js · FastAPI · PostgreSQL/PostGIS · MapLibre · CesiumJS.

Nghiên cứu: [dataset/import/freeze](research/dataset/README.md) · [evaluation protocol](research/evaluation/protocol.md).

Experimental future work: [historical evidence search preview](research/ai-poc/README.md).

## Chạy local

Từ **repository root**, với Docker Desktop đang chạy, dependencies/env và database/storage hiện có đã được cấu hình, mở đúng hai terminal:

```bash
# Terminal 1
RAG_LITE_ENABLED=true RAG_LITE_ALLOWLIST_PATH="$PWD/storage/rag-lite/allowlist.json" pnpm dev:api

# Terminal 2
pnpm dev:web
```

MVDT và **AI Research** dùng chung web [localhost:3000](http://localhost:3000) và API [localhost:8000](http://localhost:8000/docs). Mở [AI Research](http://localhost:3000/ai-research-preview) từ tab navigation. Dùng lại đúng instance của project nếu cổng3000/8000 đã được sử dụng; không mở stack thứ hai.

Kiểm tra trạng thái: `curl http://localhost:8000/api/v1/experimental/rag-lite/status`. `enabled=true` cho phép tìm bằng chứng; `generation_available=false` là chủ đích retrieval-only, không phải lỗi. Allowlist được cấp quyền, PDF gốc đúng checksum và index local phải có sẵn; các tài liệu riêng và file runtime này không được commit. Xem [cấu hình và giới hạn](research/ai-poc/README.md).

Mặc định cấu hình `RAG_LITE_ENABLED=false`. Để tắt sau khi opt-in, dừng API bằng Ctrl+C rồi chạy `RAG_LITE_ENABLED=false pnpm dev:api`; hoặc `pnpm dev:api` nếu `.env` không bật cờ. Chưa kết nối LLM bên ngoài, sinh câu trả lời, OCR, dự đoán hiện trạng, tư vấn vận hành hay xác nhận chuyên môn độc lập.

Nếu database local chưa chạy, khởi động một lần bằng `pnpm db:up` trước hai terminal trên.

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
