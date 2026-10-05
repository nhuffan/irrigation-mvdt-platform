# Quy tắc làm việc của AI

## Dọn service khi hoàn thành task

- Trước khi khởi chạy service, ghi nhận các service/process/container đã chạy sẵn và các service do AI khởi chạy trong task hiện tại.
- Khi task hoàn thành, trước khi gửi câu trả lời cuối, phải dừng mọi service do AI khởi chạy cho task: frontend, backend, dev server, watcher, preview và container Docker. Task bị hủy cũng phải thực hiện bước dọn này khi có thể.
- Chỉ giữ service chạy khi người dùng yêu cầu rõ ràng. Không coi việc cần chạy service để kiểm thử là yêu cầu giữ nó chạy sau task.
- Không dừng service đã chạy trước task hoặc do người dùng/task khác khởi chạy. Không dùng kill/pkill rộng theo tên hoặc chỉ dựa vào port; xác minh PID, đường dẫn project và nguồn khởi chạy.
- Dừng process nhẹ nhàng bằng Ctrl+C/SIGINT hoặc SIGTERM, rồi kiểm tra process đã thoát và port đã được giải phóng.
- Với Docker Compose, chỉ dừng container do AI khởi chạy. Nếu toàn bộ stack được AI khởi chạy trong task, dùng `docker compose down` tại root project; nếu có container chạy sẵn, chỉ stop service do AI khởi chạy.
- Giữ nguyên dữ liệu database và volume. Không dùng `docker compose down -v`, `docker system prune` hoặc xóa volume để dọn service.
- Dừng container không đồng nghĩa thoát Docker Desktop. Chỉ thoát Docker Desktop nếu AI đã mở nó trong task và đã xác minh không còn workload khác cần dùng; nếu Docker đã chạy trước task, giữ nguyên trừ khi người dùng yêu cầu tắt.
- Cuối task, xác minh trạng thái thực tế và báo ngắn gọn service nào đã dừng, service nào còn chạy cùng lý do. Nếu không dừng được, nêu rõ blocker; không tuyên bố đã dừng khi chưa kiểm tra.

## Phạm vi và tài liệu

- Chỉ duy trì một file hướng dẫn AI: `AGENTS.md` tại root. Không tạo file AI riêng cho frontend/backend.
- Trước khi sửa Next.js, đọc tài liệu tương ứng tại `apps/web/node_modules/next/dist/docs/`. Next.js đã cấu hình `agentRules: false` để không tự sinh file hướng dẫn con.
- `README.md` chỉ giữ lệnh chạy ngắn gọn và kết quả theo `Stage 0 output`, `Stage 1 output`, ...; không sao chép guideline hay viết nhật ký setup chi tiết.
- Dữ liệu seed chỉ dùng development, không được mô tả là dữ liệu nghiên cứu đã xác minh. Không hard-code logic theo tên hồ.

- Sau khi hoàn thành **mỗi stage**, bắt buộc thêm/cập nhật mục `Stage N output` trong `README.md` theo mẫu Stage 0/1/2: chức năng đã chạy, route/API/schema mới, kết quả kiểm tra và giới hạn còn lại. Không đánh dấu hoàn tất hoặc gửi kết luận cuối trước khi cập nhật. Giữ output stage trước và chỉ ghi kết quả đã xác minh, không chép lại kế hoạch.

- Với O&M: giữ nguyên dữ liệu thiếu và các giá trị conflict; current condition chỉ lấy record VERIFIED mới nhất. Không dùng seed development làm bằng chứng nghiên cứu.
