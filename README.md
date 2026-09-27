# Irrigation MVDT Platform

Next.js · FastAPI · PostgreSQL/PostGIS · MapLibre. Hướng dẫn AI duy nhất: [AGENTS.md](AGENTS.md).

## Stage 0 output

- Monorepo `apps/web` + `apps/api`; dependencies được khóa bằng pnpm/uv.
- PostGIS 17/3.5 qua Docker, bảng `reservoirs` với `POINT(4326)`, Alembic và seed chạy lại được.
- API danh sách hồ, health check, Swagger; frontend đọc dữ liệu thật.
- Dữ liệu seed chỉ dùng development, chưa được xác minh cho nghiên cứu.

## Stage 1 output

- `/`: registry, trạng thái hồ và liên kết đến chi tiết.
- `/map`: basemap MapLibre, marker theo tọa độ DB, màu theo trạng thái, legend, tự fit dataset và popup dẫn tới hồ.
- `/reservoirs/[id]`: thông tin hồ, UUID, tọa độ, trạng thái và maturity level; module tương lai được ghi rõ chưa triển khai.
- `GET /api/v1/reservoirs/{id}`: đọc PostGIS, trả 404 khi UUID không tồn tại và 422 khi UUID sai định dạng.
- Loading, empty và error states; lỗi API không bị chuyển nhầm thành 404. Popup dùng DOM text an toàn.
- Basemap dùng MapLibre demo tiles qua Internet, phù hợp demo; chưa phải bản đồ nền địa hình chi tiết cho nghiên cứu.
- Không thêm Asset, Authentication, 3D hoặc SCADA.

## Chạy local

Từ root, với Docker Desktop đang chạy và dependencies/env đã được cấu hình:

```sh
pnpm db:up
pnpm db:migrate
pnpm db:seed
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
cd apps/api && uv run python -m pytest -q
```

API tests cần local PostGIS đã migrate; dữ liệu test được rollback.
