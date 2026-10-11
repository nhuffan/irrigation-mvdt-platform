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


## Stage 5B-B02-R output

- Review đủ 6 candidate ban đầu: **3 VERIFIED ở L2, 3 KEEP_AS_REFERENCE ở L1**; không có L3 hoặc domain-expert attestation. AI kiểm tra source/semantic được ghi riêng với user declaration B01B và automated validation.
- Ba technical được đối chiếu báo cáo với bản vẽ tường tâm giai đoạn II; label làm rõ component/phạm vi lịch sử, unit m và datum chưa xác định. Không nhầm với chiều dài toàn đập/cao trình đỉnh đập hoặc model input/output. Giữ stable attribute keys; dictionary được chấp nhận cho các trường đã review.
- Biên bản XL5 được phân loại lại thành REFERENCE vì phục vụ điều chỉnh thiết kế và phạm vi nhiều công trình; không nhập INSPECTION/REPAIR. Hai context references còn lại được giữ. Bản gốc, payload và lịch sử quyết định nằm trong private input archive, không xóa candidate.
- Tạo private verification log 6 dòng, crosscheck matrix (3 MATCH, 3 NOT_AVAILABLE), conflict log và review coverage kèm PDF SHA-256. Không xác lập tính độc lập giữa report và drawing nên không nâng L3. Không phát hiện conflict giá trị trong phạm vi đã xem; không kết luận toàn archive không có conflict.
- Xem bổ sung 12 trang bản vẽ tường tâm (có trang lặp), hoàn tất 5 trang bản vẽ quan trắc và xem 3 trang bản vẽ 1983; bản 1983 mờ chưa dùng xác minh số liệu. Tên file tường tâm ghi 2002 khác titleblock 2000/05-2000, được ghi nhận, không biến thành event date. Các hồ sơ XL1/XL5/seepage/monthly còn lại chưa review toàn bộ.
- MAIM technical giữ required=false cho cả 4 category, có rationale riêng; hash MAIM, source inventory và base-scope không đổi. Không mở rộng denominator/allowlist hoặc nâng source authority/maturity.
- Compiler hiện hữu tạo **B02A gồm 3 technical, READY_TO_IMPORT** tại private `batches/B02-R/B02A/`. Bốn nhóm O&M trả NO_VERIFIED_CANDIDATES, không sinh batch rỗng. **Chưa dry-run/apply database**: bàn giao bước B02-I, không tuyên bố DB/API đã có các giá trị mới.
- Kiểm tra offline đạt: review gates cho 6 candidate, 5 PDF hashes, input hashes, recompile batch/UUID giống hệt và protected-file hashes. **35 unit tests đạt, 5 DB tests không chạy**; một Starlette deprecation warning hiện hữu. Không đổi application code/schema/API/UI. Kiểm tra cấu trúc không thay thế xác minh kỹ thuật.
- Hướng dẫn bàn giao và header-only templates tại `research/dataset/field_review_handoff.md`; chi tiết thực tế tại private `reviewed/B02-review.md`. Stage 5B vẫn NOT_READY, không freeze hoặc browser acceptance mới.
- Không khởi chạy service cho lượt review; PostGIS và Docker Desktop do task trước khởi chạy đã được dừng khi hủy task đó, giữ nguyên volume. Không có API/web do task này khởi chạy.


## Stage 5B-B02-I output

- Đã import thật **3 technical L2 VERIFIED** từ đúng batch B02-R/B02A hiện hữu; không tái tạo UUID, sửa batch hoặc thêm extraction/O&M. Kiểm tra trước/sau xác nhận hash candidate, verification log, dictionary, evidence/source/target inventory, MAIM, review package và batch không đổi; 5 PDF nguồn khớp hash lưu trong B02-R.
- Dry-run trả **3 DRY_RUN**, rollback xác nhận DB và 33 phản hồi API giống baseline. Apply trả **3 IMPORTED**; retry cùng batch trả **3 UNCHANGED**, không duplicate. Các log khớp UUID/provenance, RS asset/source và batch hash.
- RS technical **0→3**; tổng technical gồm DEV **4→7**. RS conditions/inspections/repairs/maintenance vẫn **0**; current-condition của cả 4 RS assets vẫn null và timeline rỗng không đổi. Dữ liệu DEV, source rows, asset rows và reservoir rows giữ nguyên; không nâng source verification, asset data_status hoặc reservoir maturity.
- Kiểm chứng DB/API bằng FastAPI TestClient với database thật: 33 responses mỗi snapshot gồm detail, technical, O&M, current-condition, timeline và reservoir asset list. Ba giá trị/label/unit/verification/source linkage khớp batch. Không khởi động HTTP server và không tuyên bố browser acceptance.
- Cập nhật **chỉ `record_ids.technical`** trong private base-scope với đúng ba UUID đã import. Các allowlist khác giữ nguyên; MAIM CSV technical required=false cho cả 4 category. Scope fingerprint mới: `1541f2a9b5c29c683ed0f1bcdeecd5cdcaa10498ffe4d4e2e352798c00f8555b`; lưu cả fingerprint cũ và file hash mới trong audit.
- Readiness chạy lại tại private `reviewed/check-B02-I/`: **NOT_READY**, không sinh compiled scope. Các blockers còn lại gồm fingerprint review, source authority/type/ownership, browser acceptance và các checkpoint phương pháp chưa được phê duyệt. Không tự cập nhật case-study approval, sửa các trường scope khác, freeze DT-R1 hoặc công bố metrics.
- **197 tests đạt: 109 unit + 88 DB/integration; 0 skipped/failed.** Bao gồm importer, overwrite rejection, idempotency, source linkage, technical/detail API, timeline/current-condition. Fixtures DB rollback; audit sau tests xác nhận dữ liệu thật không thay đổi. Ruff đạt, format 78 files đạt; một Starlette TestClient deprecation warning hiện hữu. Không đổi schema/API/UI, không cần migration/seed.
- Báo cáo, snapshots baseline/rollback/apply/retry/post-tests, logs, scope change và kiểm tra hash lưu private tại `research/dataset/batches/B02-I/`; không đưa nguồn/batch riêng tư vào Git. B02 hoàn tất cho ba technical đã review; bước tiếp theo B03 documents + reviewed 3D, Stage 5B tổng thể vẫn NOT_READY.
- Đã dừng PostGIS, gỡ container/network do task khởi chạy và tắt Docker Desktop; giữ nguyên volume chứa dữ liệu đã import. Không khởi chạy API/web server.


## Stage 5B-B03 output

**Trạng thái: đã import tài liệu và mô hình tham khảo LOCAL; mapping 3D chờ người dùng xác nhận ở prompt sau. B03 chưa hoàn tất toàn bộ.**

- Import 5 PDF đã review bằng source/evidence linkage, SHA-256, original filename và page count thực tế. Dry-run rollback, apply 5 IMPORTED, retry 5 UNCHANGED; tổng documents 2→7. Các representation chưa đối chiếu giữ REFERENCE_ONLY, không tự khẳng định duplicate/revision.
- Thêm importer reviewed documents với stable UUID, kiểm tra bytes/MIME/page count, chống duplicate/overwrite và audit manifest. Dependency pypdf được khóa; không đổi schema hoặc migration. Hướng dẫn và header-only templates tại `research/dataset/reviewed_media_loading.md`.
- Chuyển SKP thật sang GLB bằng Blender 4.4.0 và SketchUp importer 0.24 theo authorization của người dùng; giữ nguyên file nguồn, hashes, tool provenance và render kiểm tra từ GLB re-import. Web converter đã render nhưng export timeout; không dùng output chưa hoàn chỉnh.
- GLB khoảng 137 MiB, 11.758 mesh nodes, lưu object inventory. Import 1 model REFERENCE/PARTIALLY_VERIFIED, LOCAL với geographic placement NULL; dry-run/apply/retry đạt, tổng models 1→2. Hierarchy đã flatten, không coi tên object là bằng chứng identity, chưa tối ưu cho thiết bị yếu.
- Viewer Cesium hỗ trợ LOCAL với camera và ánh sáng riêng. Browser đã render mô hình và picking object chưa liên kết trả thông báo phù hợp; không gán tọa độ địa lý hoặc mở asset giả. Cả 4 mapping vẫn AMBIGUOUS/UNVERIFIED theo yêu cầu hoãn trả lời của người dùng; RS model links vẫn 0, 3 DEV links giữ nguyên. Chưa nghiệm thu đầy đủ functional acceptance.
- Kiểm chứng 41 document/asset API checks và 5 model API checks, gồm metadata/source, content hash, preview/download và HTTP Range. Snapshot cuối giữ nguyên toàn bộ baseline rows, source/asset/technical/O&M; RS current-condition null. Source verification và reservoir maturity không nâng.
- Scope chỉ thêm 5 document UUID, 1 model UUID và danh sách 11 expected document sources từ inventory; không bỏ nguồn thiếu file khỏi denominator, không thêm model links hoặc đổi MAIM/target. Fingerprint mới `06fc48a9a3ce995e6a4ac8da3dc55ecd9cd1081f288bfbb087e161309d3aed63`. Readiness chạy lại tại private `reviewed/check-B03-updated/`: NOT_READY, không freeze DT-R1.
- **208 backend tests đạt (119 unit + 89 DB/integration), 8 web picking tests đạt; Ruff/format, ESLint, TypeScript và production build đạt.** Còn warning Starlette TestClient và Node module type hiện hữu. Private logs/snapshots/review manifests tại `research/dataset/batches/B03/`; evidence và dữ liệu nghiên cứu không đưa vào Git.
- Đã xác minh API/web không còn lắng nghe ở 8000/3000; PostGIS container/network do task khởi chạy đã được dừng/gỡ, giữ nguyên volume. Docker Desktop đã chạy trước task nên giữ nguyên; không còn container chạy tại thời điểm kiểm tra.

## Stage 5B-B03-M output

- Đã giải quyết mapping theo phương án **một điểm chọn đại diện** của mục 19.B: `G-No_Name_008` là mái chính liên tục của tòa nhà quản lý trong GLB đã lưu. Bounds, ảnh cô lập/highlight và bối cảnh tòa nhà khớp với quyết định identity trong guideline cập nhật. Không có stable parent trong GLB flattened; không tuyên bố mesh mái là toàn bộ công trình hoặc mọi mesh của nhà đều đã liên kết.
- Tạo đúng **1 VERIFIED model_asset_link** cho RS-DT-MGMT, UUID `136834ef-e8b7-582a-930f-b05e4c82ff91`. Dry-run rollback đạt; apply 1 IMPORTED; retry 1 UNCHANGED. Tổng model links 3 DEV→3 DEV + 1 RS; DB/API xác nhận đập, tràn và cống vẫn không có link. Không thêm asset, technical, O&M hoặc đổi model/source/reservoir rows.
- DAM giữ AMBIGUOUS: tag `Z3 - NET CHINH DAM` chỉ là bằng chứng reference/alignment. SPILLWAY và INTAKE giữ NOT_AVAILABLE đối với mapping trong nguồn hiện tại; không diễn giải thành asset không tồn tại. GLB và SKP giữ nguyên hash, không reconvert. Model vẫn PARTIALLY_VERIFIED, LOCAL, tọa độ địa lý NULL.
- Người dùng duyệt rõ **“Duyệt phạm vi 3D chỉ MGMT”**. Archive inventory cũ rồi cập nhật requires_3d từ DAM/SPILLWAY/INTAKE=true, MGMT=false sang chỉ MGMT=true. Review CSV ghi đủ old/new, reviewer, timezone, evidence, vai trò 3D và rationale nguồn legacy; phạm vi nghiên cứu tổng thể vẫn 4 asset. Quyết định này không tự duyệt source authority hoặc empirical scope.
- Thêm compiler `scripts.prepare_reviewed_model_link` kiểm tra GLB hash, active scene/unique node names, controlled target coverage và review gates; UUID ổn định, tối đa một link. Không sinh batch khi chưa có VERIFIED mapping. Thêm header-only eligibility template và cập nhật mapping template; hướng dẫn tại `research/dataset/reviewed_model_mapping.md`.
- Panel 3D hiển thị Asset ID và nêu giới hạn liên kết qua object đại diện. Browser Chrome trên production build: click mái chính mở đúng RS-DT-MGMT/UUID, nút Asset Detail mở đúng nhà quản lý; click nước `23`, cây và Background đều không mở asset. Ảnh và review log lưu riêng tư tại evidence/B03-M và batches/B03-M. Đây là nghiệm thu mục tiêu B03-M, chưa thay thế toàn bộ Stage 5B-FV.
- 14 DB/API checks đạt; snapshots sau retry/tests xác nhận mọi bảng khác và baseline DEV links giữ nguyên, RS current-condition vẫn null. **220 backend tests đạt, 0 skipped; 8 web picking tests đạt; Ruff/format 82 files, ESLint và production build/TypeScript đạt.** Warning Starlette TestClient và Node module type hiện hữu không phát sinh từ thay đổi này.
- Scope chỉ thêm đúng link UUID vào `record_ids.model_asset_links`. Base-scope fingerprint mới `b6a50803864d4e3d425edcc649aafb6b0a35cb1c6576a8076c95cabafbc57751`; full input fingerprint gồm targets mới `fe196fb9e80c6700bcaa5daa90c4611b7ce45c4900ed548329bce8a164c7f408`. Lưu fingerprint/input cũ; không tái sử dụng approval theo fingerprint trước. Source inventory, MAIM, case-study approval và functional matrix không sửa.
- B03 mapping/eligibility đã được giải quyết theo phạm vi đại diện trên. `prepare_empirical_scope` chạy lại tại private `reviewed/check-B03-M/` trả **NOT_READY**; không freeze DT-R1 hoặc công bố empirical metrics. Bước kế tiếp: Stage 5B-FV và review source authority/ownership/các checkpoint phương pháp còn thiếu.
- Đã dừng API/web đúng PID của task và xác minh không còn listener 8000/3000. PostGIS container/network do task khởi chạy đã gỡ, volume giữ nguyên; không còn container chạy. Docker Desktop có sẵn trước task nên giữ nguyên.

## Stage 5B-FV output

**Trạng thái: đã thực hiện và ghi đủ 21 mục nghiệm thu; FV chưa đạt hoàn tất, Stage 5B vẫn NOT_READY.**

- Nghiệm thu Chrome thật trên production build b74df9c, có screenshots/DOM, environment, input hashes, DB snapshots và reviewer ghi rõ AI-operated. Kết quả **14 PASS, 4 FAIL, 3 N/A**; blocking **12/14 PASS**. Không lấy automated tests thay browser acceptance. Giữ nguyên check IDs/function của controlled matrix.
- GIS navigation, bốn asset identity, trạng thái thiếu condition, ba technical có source, PDF thật, LOCAL GLB, camera, click mái `G-No_Name_008 → RS-DT-MGMT`, clear selection, deep link và các flow A/B/C đã kiểm tra. Flow B dùng nút object accessible; canvas picking được kiểm riêng F14. Nước/cây không resolve sang asset. Không suy ra surveyed geometry hoặc O&M history từ dữ liệu rỗng.
- **F02 FAIL**: 4 RS geometry NULL, thiếu nguồn/tolerance để đối chiếu accuracy. **F05 FAIL**: timeline rỗng nên chưa chứng minh thứ tự sự kiện. **F09 FAIL**: chưa có bằng chứng browser download hoàn tất (event timeout); PDF preview đạt và HTTP Range riêng trả 206. **F15 FAIL**: giới hạn highlight đã biết, nonblocking. F08/F10/F11 N/A theo phạm vi tài liệu thật; không tạo dữ liệu hay xóa file để ép đạt.
- **220 backend tests, 8 web picking tests đạt**; Ruff/format 82 files, ESLint, TypeScript và production build đạt. Còn Starlette/Node warnings hiện hữu; console warn/error capture của browser rỗng.
- Before/after toàn bộ DB rows và stored media hashes giống nhau; targets/source inventory/MAIM/base-scope/GLB/review/eligibility giữ nguyên. Chỉ cập nhật private functional result metadata. Base fingerprint vẫn `b6a50803864d4e3d425edcc649aafb6b0a35cb1c6576a8076c95cabafbc57751`. Full-input fingerprint mới lưu trong private FV/fingerprints.json. Không đổi denominator, approval, source authority hoặc maturity; không freeze DT-R1.
- Readiness tại private `reviewed/check-FV/` còn NOT_READY (F02/F05/F09 và review nguồn/phương pháp). Report, ma trận và evidence private tại `research/evaluation/evidence/FV/`. Thêm hướng dẫn `research/evaluation/functional_acceptance.md`; không thay schema/API/UI hoặc README.
- Đã dừng đúng API/web của task và xác minh không còn listener 8000/3000. PostGIS healthy và Docker Desktop được giữ vì đã chạy trước task; không xóa volume.

## Stage 5B-FV-R output

**Trạng thái: F09 đã xử lý; FV-R chưa đóng vì F02/F05 vẫn KEEP_FAIL. Stage 5B NOT_READY, chưa chuyển SA.**

- Đổi Download từ Blob URL sang attachment endpoint cùng origin đã có sẵn. Chrome thực tế phát download-complete và trả file; 769.124 bytes, SHA-256 khớp RS-DOC-017. Filename có hậu tố `(2)` do Chrome tránh trùng. Preview PDF vẫn hoạt động; Range qua frontend trả 206. F09 FAIL→PASS, ma trận **15 PASS / 3 FAIL / 3 N/A**.
- Đã đọc exact F05, rà index XL1/XL5 và đọc có giới hạn các trang scan ưu tiên. XL1 là điều chỉnh thiết kế; XL5 quantity minutes thiếu ngày/tháng thực tế. Không lấy ngày hợp đồng làm sự kiện O&M; không import. Review chưa bao phủ toàn archive, không kết luận không có bằng chứng.
- Phát hiện bản đồ hệ thống ghi WGS 1984 UTM Zone 48N, tỷ lệ 1:100.000; giữ nguồn reference để review vì chưa có geometry chi tiết/tolerance được chấp nhận. Không tuyên bố archive thiếu mọi nguồn CRS. Geometry bốn RS assets vẫn NULL.
- Tạo private `fv_applicability_review.csv`: F02/F05 KEEP_FAIL, chưa duyệt N/A. Compiler thêm `--applicability` có gate reviewer/time/decision/retest, bind dataset/base-scope/targets/sources/MAIM và fingerprint; chỉ F02/F05 có thể exempt khi đủ review. Pending/stale/duplicate/unrelated không bỏ qua gate; compiled scope revalidate cùng evidence. Thêm template và hướng dẫn remediation; giữ F15 nonblocking FAIL.
- **234 backend tests, 8 web tests đạt**; Ruff/format, ESLint, TypeScript, production build đạt. DB và media so với baseline FV giữ nguyên, protected input hashes không đổi; không nâng authority/maturity hay sửa denominator. Chỉ matrix F09 và private review mới thay đổi.
- Lưu bằng chứng download, source page coverage, report và old/new hashes private tại `research/evaluation/evidence/FV-R/`. Full-input fingerprint mới `a46faaba02325e771f29f8fd12b0a53b3080cfebd4f079bda2b92f1c92caa8e0`. `reviewed/check-FV-R/` vẫn NOT_READY vì F02/F05 và các gate nguồn/phương pháp; không freeze.
- Đã dừng API/web do task khởi chạy và xác minh không còn listener 8000/3000. PostGIS healthy và Docker Desktop có trước task được giữ nguyên; volume không thay đổi.


## Stage 5B-GV output

**GV đã thực hiện; Stage 5B vẫn NOT_READY. F02/F05 giữ FAIL / PENDING_EVIDENCE, không đổi N/A hoặc freeze DT-R1.**

- Tách registry/map thành Research (RS), Development (DEV), Other; mặc định RS khi có, không hard-code hồ/asset. Browser xác nhận RS 4 identities / 0 geometry và DEV 4 / 3 geometry riêng. Geometry NULL có thông báo rõ, không tạo marker hoặc hiển thị CRS asset khi chưa có geometry. Basemap/reservoir center chỉ là bối cảnh điều hướng.
- Chrome trên production kiểm tra đủ 5 PDF: metadata, source, preview và download-complete; mọi file tải về khớp size/SHA-256 lưu trong DB. F09 đã PASS từ FV-R và vẫn PASS. DOC001 lần đầu timeout, thử lại sau preview ổn định thành công; không lấy HTTP-only làm bằng chứng browser.
- GLB LOCAL render, zoom/reset/rotate đạt; canvas mái `G-No_Name_008` mở đúng RS-DT-MGMT, clear/unlinked/reselect không giữ sai asset. Water `23`, cây `Deciduous Tree 005: Ash.012`, Background không resolve asset. 3D → MGMT detail → deep link model và truy cập asset trực tiếp đạt. Mapping chỉ là điểm chọn đại diện, không toàn bộ semantic geometry; F15 highlight vẫn nonblocking FAIL.
- Bốn RS thiếu condition và rỗng O&M hiển thị đúng. Ba DAM technical giữ nguyên nhãn, 0.6 m / 28 m (datum chưa xác định) / 361.5 m và nguồn RS-SRC-007. Provenance phân biệt record, source, document, model và link; source authority/owner chưa được nâng.
- Baseline kỹ thuật: GLB 144.006.072 bytes, 11.758 nodes đều có mesh, 3.669 mesh definitions; Chrome/macOS Apple M5/16 GiB. Reload navigation 0,353 s; quan sát thấy model trong 9,120 s và xác nhận canvas selectable trong 40,106 s. Đây là **upper bounds gồm automation/decision/scroll overhead**, cache không xóa, không phải đo cold-load hay empirical metric. Không tối ưu/re-export GLB.
- **234 backend tests, 8 web picking tests đạt**; Ruff/format 83 files, ESLint, TypeScript, production build đạt. Warnings Starlette/Node đã có. API/web kiểm thử riêng 8001/3001 có CORS đúng origin; không mở rộng cấu hình API của người dùng.
- Snapshot toàn DB và stored media trước/sau giống hệt; RS assets 4, technical 3, condition/inspection/repair/maintenance 0, model links 1; current condition đều NULL. Protected inputs và GLB hash không đổi so với FV-R. Private evidence/checklist/logs tại `research/evaluation/evidence/GV/`; matrix FV giữ nguyên 15 PASS / 3 FAIL / 3 N/A.
- Readiness mới `reviewed/check-GV/` vẫn NOT_READY, giữ full-input fingerprint FV-R. **Awaiting user-supplied geometry/O&M evidence review.** Theo roadmap GV mới, có thể tiếp tục SA source authority/ownership trong lúc chờ F02/F05; xem `research/evaluation/gis_3d_continuation.md`. Không thực hiện SA hoặc tự duyệt methodology trong GV.
- Đã dừng API/web kiểm thử ở 8001/3001 và xác minh không còn listener; production build đã khôi phục về cấu hình API mặc định và build đạt. API 8000, web 3000, PostGIS healthy và Docker Desktop có trước task được giữ nguyên; không xóa volume.

## Stage 5B-SA output

**Đã hoàn tất review lớp nguồn trong phạm vi bằng chứng hiện có; Stage 5B vẫn NOT_READY. Không freeze DT-R1.**

- Tạo một private `reviewed/source_review.csv` với **16/16 nguồn RS**, đủ type, owner, issuer, authority, 10 vai trò eligibility, phạm vi asset, date semantics, digital-file status, representation/revision, locator và reviewer/time. Review AI có giới hạn nội dung/trang được ghi rõ; không thay cho xác nhận độc lập của chuyên gia hoặc đơn vị lưu giữ. Các nguồn chưa xác định được file vẫn có dòng UNKNOWN, không bị loại khỏi mẫu.
- Kết quả authority: **6 SUPPORTING, 4 REFERENCE, 6 UNKNOWN_AUTHORITY; 0 AUTHORITATIVE**. Owner/custodian **16 UNKNOWN**; issuer/producer **5 PARTIALLY_VERIFIED, 11 UNKNOWN**. Tên tổ chức trong title block, tác giả, affiliation và các bên tham gia biên bản được phân biệt với quyền sở hữu/đơn vị ban hành; không dùng Drive owner hoặc tên file để nâng authority. Đây là thống kê kiểm soát review, không phải empirical metrics.
- Digital status: **5 FILE_PRESENT, 6 MULTIPLE_REPRESENTATIONS, 4 UNRESOLVED, 1 FILE_MISSING**. Giữ nguyên **11 expected document sources**, gồm nguồn ảnh thiếu file. Folder, tập tài liệu và bản chuyển đổi không được tính là các nguồn độc lập. Date của báo cáo, giai đoạn quan trắc và event date tách riêng; không suy ngày đầy đủ từ filename.
- Phát hiện một representation trong nhóm submission nói về cảnh báo học vụ, không thuộc case study hồ: ghi **NOT_ELIGIBLE cho các vai trò nghiên cứu** ở review, giữ nguyên evidence index để MC xử lý ranh giới nguồn có kiểm soát. Bản author-response có chữ ký và đề nghị ban biên tập chấp thuận không được coi là quyết định acceptance hoặc phê duyệt kỹ thuật.
- Đối chiếu **5/5 PDF đã import**: DB source_id/source_code, evidence ID/Drive ID, original filename, bytes, SHA-256 và page count đều khớp. Chuỗi **SKP → GLB** khớp source/model ID, hai hash và conversion tool/version; model giữ **PARTIALLY_VERIFIED, LOCAL**, không có geographic placement. Chỉ MGMT có representative mapping như B03-M.
- Review riêng RS-SRC-007: nhóm gồm PDF báo cáo, DOCX có nội dung khác nhau và XLSX kịch bản; không khẳng định cùng revision. Ba technical đã import vẫn trỏ đúng source group và **EVID-IN-001 PDF p2 section 4** trong field review. Tên XLSX cũ của DB source không thay thế locator PDF; không reverify hoặc đổi giá trị technical.
- Tạo **5 candidate follow-ups** cho FV-R, chỉ là đầu mối cần kiểm tra tiếp. F02/F05 giữ **FAIL / PENDING_EVIDENCE**, không N/A; không import geometry, condition hoặc O&M. Coverage archive có giới hạn, không kết luận toàn archive thiếu bằng chứng.
- QA kiểm tra unique/exact 16-row coverage, source/evidence/asset references, enums, template, denominator, protected hashes và provenance đạt. Toàn bộ DB rows/stored-media hashes trước/sau giống nhau, fingerprint `c32988b9918e65471eecf6bdbd96360d76f06478898d865c59450bc6806b8dd8`. Không đổi schema/API/UI/compiler; không chạy lại backend/web regression hoặc tuyên bố browser acceptance mới cho stage chỉ thay review data/tài liệu này.
- Archive input trước review, retained evidence, summary, QA, provenance, candidate flags và hashes tại private `research/evaluation/evidence/SA/`. Chỉ thêm `source_review.csv` vào controlled inputs; các input cũ không đổi. **SA package fingerprint mới `50b33558320a0885ae56b452833f90210392f4fb73df167d7348f77eecabb3ee`**, tách khỏi legacy compiler fingerprint không đổi. Không tái sử dụng approval cũ cho review mới; bằng chứng riêng tư không đưa vào Git.
- Readiness mới `reviewed/check-SA/` trả **NOT_READY (exit 2)**, không sinh compiled scope. SA là auxiliary review, chưa trở thành formal compiler input; không điền UNKNOWN vào inventory để vượt gate nonempty hoặc tự duyệt case-study review. Hướng dẫn/mẫu tại `research/dataset/source_authority_review.md` và `source_review.template.csv`. Bước tiếp theo **MC** cần xử lý source boundaries, cách đưa review nguồn được duyệt vào protocol/compiler, MAIM, checkpoints và giới hạn reviewer; quay lại FV-R khi có bằng chứng F02/F05 đủ điều kiện.
- Không khởi động service trong task SA. Đã xác minh API 8000 (PID 35953/35955), web 3000 (PID 36053), PostGIS healthy có trước task vẫn chạy; giữ Docker Desktop và volume của người dùng.
