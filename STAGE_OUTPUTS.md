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


## Stage 5 output

**Trạng thái: đã triển khai công cụ đánh giá; nghiên cứu thực nghiệm chưa hoàn tất.** Chưa được xem là research validation hoàn thành khi thiếu inventory thật, dataset freeze và quan sát người dùng.

- Thêm research workflow tại `research/dataset/` và `research/evaluation/`: scope/version/import templates, protocol, định nghĩa metric/mẫu số, functional acceptance matrix, 6 retrieval tasks, answer key, custom questionnaire 8 câu (không phải SUS) và conflict-review template.
- `scripts.import_research_data`: reviewed JSON batch, dry-run mặc định/rollback, apply có chủ đích, UUID và verification khai báo rõ, RS- convention tách DEV, GeoJSON/hierarchy/source/model link validation, idempotent và không overwrite record khác nội dung; xuất CSV import log kèm batch SHA-256. Document file import dùng workflow Stage 4.
- `scripts.freeze_research_dataset`: scope explicit từ Phase 1, target assets và allowlist record IDs, transaction REPEATABLE READ chỉ đọc, giữ target chưa đăng ký trong mẫu số, kiểm tra nguồn/cùng hồ; snapshot JSON + SHA-256 và bản sao file content-addressed. Không ghi đè version/output đã có. Hash kiểm tra thay đổi, không tự xác thực người duyệt hay độ đúng dữ liệu thực tế.
- `scripts.evaluate_research_dataset`: đọc frozen snapshot độc lập với DB, kiểm tra checksum và xuất CSV/JSON cho identification/GIS/technical/condition/O&M coverage, traceability, document/integrity, 3D mapping, verification, MAIM completeness, missing fields và candidate conflicts. Giữ zero hợp lệ; mẫu số trống trả null; known source date không bị diễn giải thành dữ liệu còn mới.
- `scripts.export_research_results`: bảng retrieval theo workflow và so sánh paired participant/task/version; time reduction chỉ cho cặp thành công với baseline > 0, success rate tính trên mọi attempt. Questionnaire xuất n/mean/median/range/sample SD, giữ NA/missing. Reject duplicate/invalid observations; file trống trả NOT_COLLECTED, không tạo người tham gia/kết quả giả.
- Audit thực tế trong `research/evaluation/readiness_audit.json`: 4 asset hiện có đều thuộc development convention, 0 asset RS-; dataset `version.json` giữ NOT_FROZEN. Đây là audit triển khai, không phải số liệu case study. Không tạo DT-R1 giả hoặc tăng maturity tự động.
- Chuẩn bị 3 SVG có source tái tạo: architecture, research workflow, asset-centric information model; đã render và kiểm tra bố cục. Screenshots case study chưa có. Folder frozen files, batch, observations, screenshots và results được gitignore để không tự push tài liệu nguồn hoặc dữ liệu người tham gia.
- Kiểm tra đạt: 103 backend/integration tests (gồm 19 research tests), Ruff; CLI chặn scope chưa duyệt, export trống NOT_COLLECTED; export cùng snapshot cho JSON giống nhau. Các test dùng fixture synthetic/rollback, không phải evidence nghiên cứu. Không đổi schema/API/UI sản phẩm.
- Còn thiếu để nghiệm thu Stage 5: inventory/MAIM và nguồn thật đã duyệt, import/freeze dataset nghiên cứu, browser/manual acceptance và screenshots, actual baseline/MVDT sessions, questionnaire/feedback và phân tích kết quả thực nghiệm. Browser vẫn không kết nối được; matrix giữ NOT_TESTED. Viewer Stage 4 có panel selection nhưng per-object visual highlight chưa được triển khai/accept, đã ghi rõ trong protocol. Chưa có cơ sở kết luận cải thiện retrieval hoặc usability.


## Stage 5B output

**Trạng thái: đã triển khai công cụ chuẩn bị và phân tích thực nghiệm; case study chưa hoàn tất.** Không có inventory/hồ sơ thật đã duyệt hoặc observations được cung cấp trong phiên này; không import dữ liệu giả, không freeze DT-R1 và không tạo kết quả nghiên cứu.

- Thêm inventory templates cho target assets, nguồn, MAIM theo category và review checkpoints A–D; có geometry review, participant profiles và qualitative coding. Hướng dẫn vận hành tại `research/evaluation/stage5b_protocol.md`.
- `scripts.prepare_empirical_scope` biên dịch scope theo `STAGE-5B-v1`: RS codes, inventory/hierarchy, nguồn/ownership/authority, MAIM thuộc tính + đơn vị, reviewer/evidence và functional acceptance. Gate giữ target chưa đăng ký và nguồn thiếu file trong mẫu số; không suy diễn approval. Các chức năng cốt lõi phải PASS; có target 3D thì picking/navigation cũng phải PASS. F15 visual highlight được giữ là limitation, không tự coi là đã triển khai.
- Review gắn fingerprint của scope/record allowlists; scope nhúng inventory, MAIM, acceptance và hash đầu vào. Freeze/evaluation kiểm tra lại bundle; thay đổi scope cần review lại. Hash không xác thực người duyệt hoặc thay cho kiểm tra hồ sơ thực tế.
- Metric version riêng giữ khả năng đọc Stage 5A: GIS/condition theo toàn bộ target inventory; technical yêu cầu đủ thuộc tính VERIFIED và đúng đơn vị; inspection/maintenance theo target đủ điều kiện; repair count chỉ là mô tả. Thêm current-condition/geometry/technical-requirement/conflict-review exports, MAIM theo asset và N/A có rationale. 3D yêu cầu mapping VERIFIED, nguồn rõ, placement và object hợp lệ. Geometry hợp lệ không được diễn giải thành độ chính xác khảo sát.
- Retrieval bắt buộc task_version, cohort và timestamps; tách DOMAIN_STAFF khỏi RESEARCH_TEAM, chỉ pair cùng dataset/version/cohort/participant/task. Kiểm tra elapsed time, giữ failures trong success denominator. Questionnaire giữ thiếu/N/A, xuất n=0 khi một câu không có câu trả lời; không gộp benchmark nội bộ thành evidence người dùng chuyên môn.
- Kiểm tra đạt: **126 backend/integration tests**, gồm 42 research tests, Ruff và format check. Có một deprecation warning hiện hữu của Starlette TestClient. Fixture kiểm thử là synthetic và transaction rollback, không phải case-study evidence. Không đổi schema/API/UI; không cần migration hoặc seed mới cho thay đổi này.
- CLI chạy với template thực tế trả NOT_READY (45 blockers), không sinh compiled scope; lưu `research/evaluation/stage5b_readiness.json`. `version.json` vẫn NOT_FROZEN. Browser tool không kết nối được; functional matrix vẫn NOT_TESTED, không có screenshot/visual acceptance mới.
- Còn cần: approved Phase 1 inventory, nguồn/GIS/O&M thật, review MAIM/geometry/3D, nghiệm thu browser, import/freeze và lưu archive, paired baseline–MVDT sessions, questionnaire/feedback, bảng/hình và kết luận từ observations thực tế. Chưa có cơ sở khẳng định hiệu quả retrieval hoặc usability.
- Không khởi chạy service/container mới trong task. API, web và PostGIS do người dùng chạy sẵn được giữ nguyên.


## Stage 5B-DB output

- Hoàn thành **B01A** theo khuyến nghị cuối guideline: nạp 4 RS category và 16 candidate sources vào reservoir DT001 hiện hữu. Không nạp 4 target assets; B01B chờ review danh tính, inclusion và geometry. Không thêm technical/O&M/geometry/document/model giả.
- Tất cả 16 nguồn giữ UNVERIFIED; owner/authority chưa biết giữ NULL. Source date thiếu ngày hoặc là khoảng thời gian giữ NULL, nguyên văn nằm trong notes. Không suy diễn file_name từ title; file_available trong CSV chỉ là thông tin draft, không phải kiểm tra file thực tế.
- Thêm `scripts.prepare_initial_research_batch`: đọc ba CSV, kiểm tra code/liên kết/boolean, tạo batch chỉ category/source, lưu hash đầu vào và UUID map ổn định (gồm asset UUID dự trữ). Không ghi đè output; retry dùng lại batch cũ. `reviewed_by` ghi rõ Codex chỉ review chuyển đổi cấu trúc, không phải domain approval.
- Ba draft giữ nguyên byte trong `research/dataset/reviewed/`; batch/logs/UUIDs và báo cáo verification tại `research/dataset/batches/B01A/`, đều private/gitignored. Bổ sung ignore evidence directory. Hướng dẫn tại `research/dataset/initial_loading.md`.
- Dry-run 20 dòng DRY_RUN, hash khớp và DB rollback; apply 20 dòng IMPORTED; chạy lại trong transaction cho 20 dòng UNCHANGED. Category tổng 5→9, source tổng 1→17; asset vẫn 4 DEV, các bảng O&M/media không đổi. Reservoir giữ data_status MVDT_AVAILABLE, mvdt_level 3 như trước task, không nâng maturity.
- API TestClient kiểm tra thành công cả 16 nguồn và reservoir asset endpoint; chưa có RS asset hiển thị vì B01A không insert asset. Không mở web/API server hoặc tuyên bố nghiệm thu browser.
- Sửa reader của empirical scope để chấp nhận UTF-8 BOM trong CSV cung cấp. Kiểm tra bằng các draft thực tế trả NOT_READY, không sinh compiled scope hoặc freeze DT-R1. Domain review, source authority và functional acceptance vẫn pending.
- **134 backend/integration tests đạt**, Ruff/format đạt; một deprecation warning Starlette hiện hữu. Không đổi schema, không cần migration. Stage 5B thực nghiệm chưa hoàn tất.
- Đã dừng PostGIS do task khởi động; giữ nguyên volume chứa B01A. Không có API/web service được task khởi chạy.


## Stage 5B-B01B output

- Đã nạp **4 RS asset** bằng UUID dự trữ B01A, với data_status REGISTERED, parent NULL và geometry NULL. Identity/inclusion trong controlled inventory dựa trên xác nhận review/duyệt tài liệu Drive/local của người dùng trong task; lưu nguyên văn declaration và context riêng tư. Không diễn giải thành asset data VERIFIED hoặc approval mọi empirical checkpoint.
- Thêm `scripts.prepare_reviewed_asset_batch`: offline compiler kiểm tra RS/UUID, inclusion true/false, identity VERIFIED, canonical name/category/parent, evidence liên quan đúng asset/purpose, physical-file evidence, reviewer/timezone, hierarchy cycle và parent order. Không ghi DB/đè output/tự nâng trạng thái. Xuất batch, input hashes, review manifest và verification report.
- Geometry NULL cần NOT_AVAILABLE/rationale/survey_grade=false. Optional geometry_geojson cần CRS/provenance/review; dùng Shapely kiểm tra topology, finite 2D lon/lat, kiểu geometry và closed polygon. Thêm dependency Shapely đã khóa trong uv.lock; không đổi schema/API/UI.
- Bảo toàn bản cũ trước cập nhật source/evidence inventory trong private reviewed/. Tách logical source khỏi evidence file, bổ sung 21 leaf PDF XL5, tổng manifest 40 mục. Drive xác nhận locator ba PDF đập và SKP; AI xem trang đầu EVID-DAM-001 và đọc text báo cáo đầu vào, không tuyên bố đã xem mọi PDF/đã render SKP. Review user-declared và AI inspection coverage lưu tách biệt.
- Giữ initial MAIM, không tự tạo technical key/unit. Tạo B02 candidate queue với một REFERENCE transcription chưa xác minh; chưa import technical/O&M. Source inventory mới không âm thầm overwrite 16 source B01A trong DB; owner/authority và quan hệ revision còn cần hoàn thiện.
- Dry-run 4 dòng rollback và hash khớp; apply 4 dòng. DB asset tổng 4→8 (4 DEV + 4 RS); bốn asset detail và reservoir-list API đạt, retry cho 4 UNCHANGED. Các bảng source/O&M/media và reservoir data_status/mvdt_level giữ nguyên. Audit/logs tại private batches/B01B/.
- **157 backend/integration tests đạt**, gồm 23 tests mới cho B01B; Ruff đạt. Một deprecation warning Starlette hiện hữu. Không có browser acceptance mới.
- Compiler B01B đạt READY_TO_IMPORT; empirical scope vẫn NOT_READY vì source authority, acceptance và các checkpoint sau chưa hoàn thành. Không tạo DT-R1. Hướng dẫn ở `research/dataset/reviewed_asset_loading.md`.
- Đã dừng PostGIS và Docker Desktop do task khởi chạy, giữ nguyên database volume. Không khởi chạy API/web server.


## Stage 5B-B02 output

**Trạng thái: công cụ và lượt trích xuất đầu tiên đã triển khai; field review/import dữ liệu thật còn pending.** Không coi approval bộ tài liệu B01B là approval tự động cho các giá trị B02 mới.

- Thêm `scripts.prepare_reviewed_om_batch`: compiler offline cho technical/conditions/inspections/repairs/maintenance; chỉ chọn VERIFIED candidates có reviewer/timestamp, approved RS target, source/evidence linkage và locator cụ thể. Không inference current condition, không ghi DB, không đổi verification source/maturity.
- Technical dùng dictionary key/label/unit chính xác, explicit number/text, giữ zero và chặn NaN/Infinity/missing placeholder. O&M yêu cầu full event date, payload fields theo schema và event basis; chặn date range/thiếu description hoặc inspection thiếu nội dung. MONITORING/MODEL_OUTPUT/REFERENCE không tự trở thành O&M.
- UUIDv5 theo asset UUID + type + candidate ID, persist map; sửa giá trị giữ ID để importer chặn overwrite. Conflict candidates giữ riêng và báo nhóm cần review. Xuất input hashes, review manifest, provenance record→candidate→evidence→source→Drive/page, id_map và verification report. Batch rỗng hoặc chưa duyệt chỉ xuất report, không tạo import JSON.
- Trích xuất ban đầu có 6 candidates: 3 technical từ EVID-IN-001 trang 2–3, 1 inspection từ biên bản XL5 trang 1–3 và 2 references. Tất cả REVIEW_PENDING, không phải kết quả đo hiện trạng. Có dictionary đề xuất cho 3 giá trị; MAIM technical vẫn false, chưa áp đặt yêu cầu mới. Chưa review toàn bộ archive; không kết luận O&M không tồn tại chỉ vì chưa nhập.
- Đã xem trực quan các trang báo cáo nguồn, bản vẽ và biên bản XL5; biên bản ghi kiểm tra/điều chỉnh thiết kế, không được chuyển thành completed repair. Candidate inspection cần review liên kết asset vì phạm vi đầu mối/XL5 rộng. Bản review cụ thể lưu private `reviewed/B02-review.md`; bản gốc trước migration candidate schema được archive.
- **197 backend/integration tests đạt**, gồm 40 B02 tests. Tests dùng synthetic fixture/rollback kiểm tra cả 5 loại qua DB/API, idempotency, overwrite rejection, source linkage, timeline và current-condition. Ruff/format đạt; deprecation warning Starlette hiện hữu.
- Chạy compiler trên dữ liệu thật cho cả 5 loại: NO_VERIFIED_CANDIDATES, không sinh batch giả. Audit 28 API responses cho 4 RS assets đạt; research technical/O&M vẫn 0 và current-condition null. Không có import/apply B02 thật, không mở rộng record allowlist. Reservoir vẫn MVDT_AVAILABLE/level 3. Báo cáo riêng tư tại batches/B02/verification_report.json.
- Còn cần duyệt từng giá trị/event đã trích xuất, tiếp tục kiểm tra hồ sơ chưa đọc, quyết định dictionary/MAIM rồi dry-run/apply các batch có dữ liệu đã duyệt. Stage 5B vẫn NOT_READY; chưa có browser acceptance hoặc DT-R1 freeze. Hướng dẫn tại `research/dataset/reviewed_om_loading.md`.
- Đã dừng PostGIS và Docker Desktop do task khởi chạy, giữ nguyên volume; không khởi chạy API/web server.
