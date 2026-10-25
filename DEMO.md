# Five-minute project demo

Đây là hướng dẫn live demo duy nhất của project. UI dùng tiếng Anh; lời dẫn dưới đây có thể nói bằng tiếng Việt. Phần phương pháp nghiên cứu học thuật trình bày trên **một slide**, không chạy wizard acceptance trong demo.

## Chuẩn bị trước khi bấm giờ

Từ repository root, dùng database/storage/env/dependencies hiện có và Docker Desktop đang chạy. Nếu DB chưa chạy: `pnpm db:up`. Giữ instance project đã chạy; không mở thêm stack, migrate, seed hay reset dữ liệu nghiên cứu.

```sh
# Terminal 1 — API http://localhost:8000
RAG_LITE_ENABLED=true RAG_LITE_ALLOWLIST_PATH="$PWD/storage/rag-lite/allowlist.json" pnpm dev:api

# Terminal 2 — web http://localhost:3000
pnpm dev:web
```

- Dùng **Chrome** với origin `localhost:3000` thống nhất. Kiểm tra `http://localhost:8000/api/v1/health` và `http://localhost:8000/api/v1/experimental/rag-lite/status`: `enabled=true`, `generation_available=false`. RAG cần allowlist được cấp quyền thực sự, đúng checksum original và index local hiện có; không tự cấp quyền/rebuild chỉ để demo. Xem [setup và giới hạn](research/ai-poc/README.md).
- Mở [Overview](http://localhost:3000/reservoirs/63adca21-9195-44e2-81a2-0475bd6829f3); bỏ filter cũ. Preload GIS, 3D và hai original bên dưới trước buổi trình bày rồi quay về Overview. Không chờ tải PDF/GLB lần đầu trong thời gian nói.
- Thử đúng hai query ở đúng asset, chế độ mặc định **Technical fields, then PDF passages**. Nếu dữ liệu/index thay đổi, xác minh lại kết quả; các số dưới đây là mốc rehearsal ngày 25/10/2026, không hard-code vào UI.
- Giữ attribution của basemap. Native PDF có thể mở cùng tab hoặc tab riêng: dùng browser Back hoặc đóng riêng tab PDF tương ứng. Không đóng tab ứng dụng.

| Mốc đã đối chiếu | Liên kết chuẩn / bằng chứng |
|---|---|
| Main Dam · `RS-DT-DAM` | [Asset](http://localhost:3000/assets/bd4aff6e-8117-426d-906e-953a2b5a4ae9#technical): crest length **1100 m**, nguồn `RS-SRC-019`, locator `PDF:p20:printed9:Table2:MainDam:reported_main_dam_crest_length`. [W2 original physical20/140](http://localhost:3000/api/media/documents/62e83ed1-2162-510a-a8ce-344a7320c8d1#page=20): Table2, Main Dam (Earthfill),1,100m. |
| Spillway · `RS-DT-SPILLWAY` | Asset UUID `9cc2f301-f40f-4f2b-aeef-dc45251d279c`; nguồn `RS-SRC-018`. [Manual original physical10/51](http://localhost:3000/api/media/documents/6c2975db-da89-546c-b1c7-f421827c1fc2#page=10): xylanh chốt cửa, **Áp suất thử nghiệm:270bar**. Physical9 là xylanh cửa van khác; không trộn hai ngữ cảnh. |
| Representative 3D | Model `13654bda-e636-565b-a990-18813aca8d3c`, object `G-No_Name_008`, liên kết với **Management / Operations Complex**. Không gán model này cho Main Dam hay một nhà con. |

Hai original tồn tại, khớp SHA-256 metadata và trả Range206 trong preflight. W2:`e4c727a343fee05a17090592344cd0d6bf7dc3ac09d38cdefd596b643cc9ede9`; manual:`3bef4ea0da58046cfa95bb20f3162f9a0cdfd10bf7c5eb9459ee81e38c2be348`. Cả hai source vẫn **UNVERIFIED**, authority **UNKNOWN**, ngày nguồn chính xác chưa có. Reviewed L2 không nâng source authority.

## Tuyến trình bày — dừng ở 5:00

Các cửa sổ dưới đây là **ngân sách presenter**, gồm click, tải và lời dẫn; không phải số đo hiệu năng. Rehearsal Chrome thực tế ngày25/10/2026 đo **187.79s (3:07.79)** cho thao tác, tải và kiểm tra hình ảnh trên dịch vụ đã preflight; không ghi âm/tính thời gian nói. Các đoạn đo được: Registry8.18s; GIS/3D29.59s; Asset24.74s; AI MainDam14.26s; original20/chuyểnSpillway23.63s; Source/Document/original10/Back62.86s; Methodology24.53s. Phần còn lại dành cho lời dẫn và dự phòng. Nếu chậm, dùng fallback ngay, không kéo dài hay tuyên bố bước bị bỏ qua đã chạy.

### 0:00–0:25 · Overview / Asset Registry

**Click/proof:** Chỉ các số đang hiện:10 research assets,44 technical records,0 verified O&M,1 3D link; phân cấp4 primary và6 components thể hiện ở Methodology cuối tuyến. Gõ `Main Dam` vào **Search assets** để thấy7 technical records và reference location.

**Nói:** “Prototype liên kết định danh tài sản với hồ sơ và nguồn gốc dữ liệu. Thiếu dữ liệu vẫn được hiển thị, không biến thành đánh giá hiện trạng tốt.”

**Đi tiếp/fallback:** Chọn **GIS Map** trên navigation. Nếu API chưa đọc được, dùng Retry; quá thời gian thì nói inventory unavailable và chuyển phần giới hạn, không đọc số lịch sử thay số live.

### 0:25–1:05 · GIS và representative 3D

**Click/proof:** GIS Map có hai marker **REFERENCE** Main Dam/Spillway và provider attribution. Chọn **3D**; đợi **LOCAL · Ready**, thấy management object được chọn và linked asset đúng parent. Có thể kéo orbit nhẹ, không chọn thêm object.

**Nói:** “GIS cung cấp ngữ cảnh và vị trí tham chiếu; đây chưa phải geometry khảo sát. 3D là biểu diễn liên kết với khu quản lý, không xác nhận vị trí hay định danh từng nhà.”

**Đi tiếp/fallback:** **Overview** → dòng Main Dam → **View Detail**. Nếu basemap/GLB lỗi, chỉ label/reference hoặc linked-asset panel còn đọc được; bỏ orbit, nói rõ renderer chưa kiểm tra được thay vì đợi vô hạn.

### 1:05–1:40 · Main Dam record

**Click/proof:** Tại Asset Detail, chọn **Technical**. Chỉ **Main dam crest length per2003 report:1100m**, L2, exact locator physical20/printed9 và source`RS-SRC-019`. Nêu current condition/O&M thiếu; không đọc hết bảng.

**Nói:** “Giá trị1100m truy vết đến một ô của báo cáo lịch sử. Trạng thái review của trường dữ liệu không có nghĩa nguồn đã được chứng nhận hay công trình đang có hiện trạng tương ứng.”

**Đi tiếp/fallback:** Chọn **AI Research**. Nếu record không đọc được, mở W2 original20 từ link chuẩn ở trên và nói rõ record UI chưa xác minh được trong lượt đó.

### 1:40–2:20 · AI Research — Main Dam

**Click/proof:** Chọn **Selected asset → Main Dam**, nhập `vật liệu đập`, **Search evidence**. Hiện1 reference, source019, **Physical PDF page20**, Table2 “Main Dam (Earthfill)” cùng crest length1,100m. Mở **Open original PDF (page20)**, chỉ dòng tương ứng rồi browser Back về search.

**Nói:** “Đây là tìm bằng chứng đúng asset, trả đoạn gốc và physical page. Hệ thống retrieval-only, không sinh kết luận kỹ thuật.”

**Đi tiếp/fallback:** Đổi dropdown sang **Spillway**. Nếu search unavailable, dùng original20 đã kiểm tra và nói rõ live retrieval bị bỏ qua; không thay query/scope ngẫu nhiên để kiếm một hit.

### 2:20–3:50 · Spillway, source/document traceability và Back

**Click/proof:** Nhập `áp suất thử nghiệm`, **Search evidence**:2 references, physical10 và9 của manual. Dùng passage physical10, chỉ **270bar** trong ngữ cảnh xylanh chốt cửa. **Evidence details → Source details**: source018, date chưa có, authority UNKNOWN, UNVERIFIED; **Back to AI Research**. Mở lại **Evidence details → Document details**:51 pages, page10. **Open original PDF (page10)**, đối chiếu270bar; đóng riêng tab PDF rồi **Back to AI Research**. Query, Spillway scope và citation được giữ lại.

**Nói:** “Cùng một từ khóa có hai đoạn cho hai loại xylanh; cần đọc đúng ngữ cảnh. Original, checksum và locator giúp kiểm tra lại, nhưng đây không phải áp suất vận hành được khuyến nghị.”

**Đi tiếp/fallback:** Chọn **Methodology & Evidence**. Nếu iframe trắng, dùng original/download luôn có trên toolbar; original lỗi thì giữ passage/metadata và nói chưa mở lại được bytes. Nếu thiếu thời gian, bỏ vòng Source details đã preflight, vẫn giữ Document→original→Back.

### 3:50–4:35 · Methodology overview

**Click/proof:** Chỉ **Level-1 information framework** và **Live evidence snapshot**: registry↔GIS/3D↔records↔sources,10 assets/44 L2/6 distinct linked PDF hashes,2 reference locations,0 verified O&M,1 representative link tại rehearsal. Các số là live readback; hash metadata không thay kiểm tra original. Giữ **Research Workflow & Acceptance (advanced)** đóng.

**Nói:** “Đóng góp Phase1 là mô hình thông tin Level1 có truy vết và công cụ phần mềm đã hoàn thành. Research acceptance vẫn pending, dataset NOT_FROZEN; workflow và các approval gate được giữ ở Advanced.”

**Đi tiếp/fallback:** Ở lại đây để kết luận. Nếu snapshot unavailable, chỉ khung thông tin và trạng thái unavailable; không mở báo cáo cũ để trình bày như số hiện tại.

### 4:35–5:00 · Kết luận

**Nói:** “Prototype hỗ trợ tra cứu hồ sơ và kiểm chứng nguồn theo từng tài sản. Domain review, geometry accuracy và đánh giá người dùng thực tế còn pending; chưa có suy luận hiện trạng, SCADA, OCR hay tư vấn vận hành.”

**Dừng:** Không mở wizard, chạy freeze, questionnaire, Intake/corpus pagination hay thêm live query trong tuyến5 phút. Phương pháp nghiên cứu chi tiết nằm trên slide học thuật và trong [protocol](research/evaluation/protocol.md), không phải thao tác chứng minh đã hoàn tất nghiên cứu.

Sau buổi demo, chỉ Ctrl+C các web/API do bạn khởi chạy; giữ service có sẵn và database volume. Kết quả stage và giới hạn được lưu tại [STAGE_OUTPUTS.md](STAGE_OUTPUTS.md).
