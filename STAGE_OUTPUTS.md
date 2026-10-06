# Stage outputs

Kết quả triển khai và kiểm tra theo từng stage.

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

## Stage 4 output

- Thêm `documents`, `models`, `model_asset_links` và migration Alembic. Composite FK chặn model–asset khác reservoir, object key duy nhất trong model; kiểm tra tọa độ, scale và verification. Xóa model/asset chỉ cascade mapping; nguồn còn document/model được bảo vệ bằng RESTRICT.
- Storage adapter local dùng `STORAGE_ROOT` (mặc định `storage/` tại root, không commit file). Import document theo source code, tính SHA-256, idempotent theo source + checksum và phục hồi blob bị mất khi import lại. Không expose storage key/path trong API; chặn traversal/symlink thoát storage.
- API `GET /api/v1/data-sources/{id}/documents`, `/documents/{id}`, `/documents/{id}/content`, `/assets/{id}/documents`; metadata file mất trả 410, unknown 404, UUID sai 422. Content hỗ trợ Range; loại ngoài PDF/raster image buộc download với `nosniff`.
- Asset Detail có Documents; O&M source → Open documents → `/documents/[id]` với preview PDF/PNG/JPEG/WebP/GIF, metadata/checksum và download. Next content proxy cùng origin hỗ trợ streaming/Range, giữ trạng thái lỗi; lỗi tải file khác trạng thái rỗng.
- API `/reservoirs/{id}/models`, `/models/{id}`, `/models/{id}/content`, `/models/{id}/asset-links`, `/assets/{id}/model-links`. Route `/reservoirs/[id]/3d` dùng CesiumJS 1.146.0 self-host, chỉ tải tại route 3D, không cần Cesium ion/token. Có chọn model, placement/provenance, reset camera, chọn/clear object và panel asset + current VERIFIED condition + latest inspection/maintenance.
- GIS popup và Asset Detail có View in 3D khi có mapping; deep link theo model/object key. Picking lấy glTF node name qua adapter đã pin version; mọi thông tin asset được resolve từ Asset ID/API. Model LOCAL chưa có placement và format chưa hỗ trợ hiển thị lỗi rõ ràng; prototype hiện render GLB self-contained, chưa có pipeline 3D Tiles hoặc BIM/CAD conversion.
- Seed `pnpm db:seed:media`: 2 synthetic files (PDF/PNG), 1 GLB nhỏ với 3 object–asset mappings và 1 object không liên kết. Tất cả UNVERIFIED, MANUAL_PLACEMENT tại tọa độ tham chiếu hồ; không phải công trình khảo sát hay kết quả nghiên cứu. Seed chạy lại giữ số lượng record; không đổi maturity của reservoir.
- Kiểm tra đạt: 84 integration tests PostGIS, 8 tests picking adapter, Ruff, ESLint, TypeScript, production build, Alembic schema check. Live HTTP xác nhận PDF/image checksum, Range proxy, GLB node mapping, metadata/navigation, empty states và HTTP 404. **Chưa xác nhận trực quan** PDF/image preview, WebGL render, xoay/zoom/click và clear selection vì công cụ browser không kết nối trong phiên này; Stage 4 còn bước nghiệm thu browser/manual theo guideline.
- Chưa có public upload/CRUD, authentication, SCADA/IoT, AI extraction hoặc BIM authoring. Files được giữ lại khi xóa metadata; chưa có garbage collection. Core Asset/O&M/verification tiếp tục ở PostgreSQL.

