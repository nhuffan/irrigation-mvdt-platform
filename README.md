# Irrigation MVDT Platform

Next.js · FastAPI · PostgreSQL/PostGIS · MapLibre · CesiumJS.

Nghiên cứu: [dataset/import/freeze](research/dataset/README.md) · [evaluation protocol](research/evaluation/protocol.md).

Experimental future work: [historical evidence search preview](research/ai-poc/README.md).

Live demo (synthetic data only): [irrigation-mvdt-platform.vercel.app](https://irrigation-mvdt-platform.vercel.app/ai-research-preview).

AI Research: [architecture](research/ai-poc/ARCHITECTURE.md) · [public demo on synthetic data: run, deploy, video script](research/ai-poc/DEMO_DEPLOY.md).

Demo toàn bộ project: [DEMO.md](DEMO.md).

## Chạy local

Từ **repository root**, với Docker Desktop đang chạy, dependencies/env và database/storage hiện có đã được cấu hình, mở đúng hai terminal:

```bash
# Terminal 1
RAG_LITE_ENABLED=true RAG_LITE_ALLOWLIST_PATH="$PWD/storage/rag-lite/allowlist.json" pnpm dev:api

# Terminal 2
pnpm dev:web
```

MVDT và **AI Research** dùng chung web [localhost:3000](http://localhost:3000) và API [localhost:8000](http://localhost:8000/docs). Mở [AI Research](http://localhost:3000/ai-research-preview) từ tab navigation. Dùng lại đúng instance của project nếu cổng3000/8000 đã được sử dụng; không mở stack thứ hai.

Kiểm tra trạng thái bằng `curl http://localhost:8000/api/v1/experimental/rag-lite/status`. `enabled=true` cho phép tìm bằng chứng. `generation_available=true` báo model local đã sẵn sàng trong phạm vi được cấp quyền. Tra cứu PDF dùng allowlist, PDF gốc đúng checksum và index local. [Hướng dẫn AI Research, MCP và quyền dữ liệu](research/ai-poc/README.md)

Tra cứu thử nghiệm, sinh câu trả lời qua Ollama và các transport MCP đều tắt mặc định. Để tắt preview sau khi dùng, dừng API bằng Ctrl+C rồi chạy `RAG_LITE_ENABLED=false pnpm dev:api`.

Nếu database local chưa chạy, khởi động một lần bằng `pnpm db:up` trước hai terminal trên.

Không migrate, seed lại hoặc reset database nghiên cứu hiện có để chạy preview. Chỉ khi khởi tạo database development mới: `pnpm db:migrate`, `pnpm db:seed`, `pnpm db:seed:assets`, rồi `pnpm db:seed:media`; seed không phải dữ liệu nghiên cứu đã xác minh.

Dừng frontend/API bằng Ctrl+C; `pnpm db:down` dừng database và giữ volume.

## Methodology workflow

Trang [Methodology](http://localhost:3000/methodology) mặc định hiển thị framework Level 1, bằng chứng đang có và giới hạn nghiên cứu. Luồng 5 bước và các gate giữ trong **Research Workflow & Acceptance (advanced)**; software workflow sẵn sàng không đồng nghĩa nghiên cứu đã hoàn tất. Preflight và bộ input trống không thay đổi database hay phê duyệt:

```sh
cd apps/api
uv run python -m scripts.research_workflow --output /tmp/methodology-preflight.json
uv run python -m scripts.research_workflow --templates /tmp/methodology-inputs
uv run python -m scripts.research_workflow --help
```

Chỉ dùng `--apply` cho import/freeze/evaluate/export khi đã có input được review hợp lệ. Mỗi lần freeze dùng thư mục riêng trong `research/`; thiếu approval, acceptance hoặc quan sát thực tế sẽ chặn bước tương ứng. Giao diện đọc trạng thái mới qua API hiện có, không cần chạy service bổ sung.

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
