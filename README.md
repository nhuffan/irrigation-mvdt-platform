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

## Stage 2 output

- Thêm `asset_categories`, `assets` và migration Alembic; asset code duy nhất toàn hệ thống, category và parent–child trong cùng reservoir.
- Geometry nullable `GEOMETRY(4326)` hỗ trợ Point/LineString/Polygon; kiểm tra validity, phạm vi tọa độ và index GiST. Xóa parent giữ asset con và reservoir, chỉ bỏ liên kết parent.
- `GET /api/v1/reservoirs/{id}/assets` và `GET /api/v1/assets/{id}` trả category, parent ID và GeoJSON. Hồ rỗng trả `200 []`; resource không tồn tại trả 404; UUID sai trả 422.
- Reservoir Detail có Asset Registry và một GeoJSON source với các lớp point, line, polygon/outline; click geometry mở popup → `/assets/[id]`. Có nút Locate dùng bàn phím.
- Asset Detail hiển thị reservoir, category, parent link, UUID, trạng thái, thông tin kỹ thuật và bản đồ. Hồ chưa có asset và asset thiếu geometry có thông báo riêng; API failure không bị biến thành 404.
- Seed `DEV-*` gồm 4 asset minh họa: Polygon, LineString, Point và một bản ghi không có geometry. Chạy lại không duplicate; không đổi `mvdt_level` hoặc data status của reservoir.
- Kiểm tra đạt: 18 integration tests trên PostGIS (rollback), Ruff, ESLint, production build, Alembic schema check; browser xác nhận click cả ba geometry → popup → detail, parent link và hồ rỗng. HTTP 404 thật cho URL asset/reservoir không tồn tại.
- Seed và basemap chỉ phục vụ development; geometry không đồng nghĩa dữ liệu đã xác minh. Chưa có CRUD/tree editor, O&M, provenance, upload hoặc authentication. Import/reparenting phải gọi `validate_parent` để chặn cycle; database chặn self-parent và parent khác hồ.

## Stage 3 output

- Thêm 6 bảng và migration Alembic: `data_sources`, `asset_technical_attributes`, `asset_conditions`, `inspections`, `repairs`, `maintenance_records`; có FK, verification status, timestamps và index theo asset/ngày.
- Asset Detail có Technical Information, current condition, condition/inspection/repair/maintenance history và O&M timeline giảm dần theo ngày; mỗi record có badge verification và metadata nguồn mở rộng được.
- `GET /api/v1/assets/{id}/{technical|conditions|inspections|repairs|maintenance|timeline}` trả danh sách; `/current-condition` trả condition VERIFIED mới nhất hoặc `null`. Resource không tồn tại trả 404, UUID sai trả 422, danh sách rỗng trả `200 []`. `GET /api/v1/data-sources/{id}` trả metadata nguồn.
- Giữ các giá trị kỹ thuật conflict, giá trị 0 và dữ liệu thiếu; không suy diễn Good hoặc chọn giá trị ưu tiên. Current condition dựa trên verification của record, không dùng trạng thái legacy của asset thay thế.
- Mỗi phần có empty/error state riêng và nút thử lại; lỗi API không bị hiển thị thành không có dữ liệu. Timeline liên kết tới record lịch sử tương ứng.
- Seed development chạy lại không duplicate: 1 nguồn, 4 technical attributes (có conflict và null), 2 conditions, 2 inspections, 1 repair, 2 maintenance records. Tất cả mang UNVERIFIED và nhãn synthetic; không đổi maturity/data status của hồ.
- Kiểm tra đạt: 55 integration tests trên PostGIS (rollback), Ruff, ESLint, production build, Alembic schema check và seed chạy lại. HTTP production HTML xác nhận populated/empty states, provenance, timeline links/order, current VERIFIED bằng transaction rollback, lỗi 503 riêng từng phần, phục hồi và HTTP 404 thật.
- Chưa kiểm tra trực quan hoặc tương tác browser trong phiên này vì công cụ browser không khả dụng. Chưa có CRUD, upload/document storage, authentication, 3D hoặc SCADA.
- Xóa asset cascade các record O&M; nguồn đang được tham chiếu và reservoir có nguồn được bảo vệ bằng RESTRICT. Import sau này phải gọi `validate_source_link` để kiểm tra source cùng reservoir; ràng buộc cùng reservoir này hiện ở service, không ở database.

## Chạy local

Từ root, với Docker Desktop đang chạy và dependencies/env đã được cấu hình:

```sh
pnpm db:up
pnpm db:migrate
pnpm db:seed
pnpm db:seed:assets  # development assets + O&M; mặc định reservoir DT001
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

Seed cho reservoir khác: `cd apps/api && uv run python -m scripts.seed_dev --reservoir-code <CODE>`. Chỉ chạy trên database development.
