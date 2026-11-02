# GEMINI.md - Quy tắc cốt lõi cho Google Gemini & Antigravity IDE
> File này được nạp tự động vào ngữ cảnh của Google Gemini mỗi phiên làm việc tại Neiro-Quant.

---

## 1. QUY TRÌNH BẮT BUỘC TRƯỚC MỌI HÀNH ĐỘNG (PRE-ACTION SKILL DISCOVERY)

> **BƯỚC 0: TRƯỚC KHI TRẢ LỜI, PHÂN TÍCH HAY CHỈNH SỬA CODE:**
> Gemini **BẮT BUỘC** phải gọi tool iew_file để đọc nội dung file SKILL.md tương ứng trong thư mục .agents/skills/.
> Tuyệt đối không được bỏ qua bước này.

### 1.1. Bằng chứng bắt buộc trong mỗi câu trả lời (Mandatory Status Header)
Bắt đầu mỗi câu trả lời gửi đến người dùng, Gemini **PHẢI** xuất ra dòng trạng thái:
- Nếu áp dụng skill:
  [Active Skill: <tên-skill> | Path: .agents/skills/<tên-skill>/SKILL.md]
- Nếu là câu chào hỏi / xã giao thuần túy:
  [Active Skill: None | Reason: <lý do ngắn gọn>]

### 1.2. Chống lách luật (Anti-Rationalization Gate)
Nghiêm cấm Gemini tự đưa ra các lý do sau để bỏ qua việc mở skill:
- Yêu cầu này đơn giản tôi có thể giải quyết ngay -> **CẤM**
- Tôi đã có đủ kiến thức trong prompt -> **CẤM**
- Tôi sẽ trả lời trước rồi mới gọi skill sau -> **CẤM**

---

## 2. BẢNG ÁNH XẠ NHANH
*(Xem bảng đầy đủ tại [AGENTS.md](AGENTS.md))*

---

## 3. LUẬT BẤT DI BẤT DỊCH TẠI NEIRO-QUANT

1. **Nguồn sự thật:** [docs/spec.md](docs/spec.md) & [docs/architecture.md](docs/architecture.md). Mã nguồn thực tế có quyền lực tối cao nếu có mâu thuẫn.
2. **Không đổi cấu hình mặc định** của indicator đã có (2TC-v10, Neiro-Liquidity-Map-v2).
3. **ASCII và KHÔNG EMOJI** trong code MQL5. Pine và Markdown dùng tiếng Việt có dấu.
4. **Không tự chế luật hoặc backtest ngoài lề.** Mọi thay đổi logic do owner trực tiếp chỉ đạo.
5. **Performance constraints:** Python code phải đảm bảo CPU < 5%, RAM cố định, zero memory leak.
6. **BẮT BUỘC ĐỒNG BỘ TÀI LIỆU (DOCUMENTATION-FIRST MANDATE):** Sau khi hoàn thành bất kỳ thay đổi, tối ưu tính năng, kiến trúc hoặc sửa lỗi (fix bug) nào trong repository, AI model **BẮT BUỘC PHẢI CẬP NHẬT LẠI TÀI LIỆU** tương ứng (`docs/spec.md`, `docs/architecture.md`, `README.md`, hoặc tạo ADR trong `docs/decisions/` nếu có quyết định kiến trúc mới) trước khi kết thúc phiên làm việc. Tuyệt đối không để mã nguồn đi trước mà tài liệu bị lạc hậu.
7. **CME OPTIONS MICROSTRUCTURE & ZERO GAMMA INVARIANT:** Dữ liệu Open Interest (OI) của CME Options là tĩnh trong phiên (chỉ cập nhật qua đêm bởi Clearing House). Mọi đánh giá áp lực thành trì trong ngày (Intraday Pressure/Flow Rate) phải đo lường bằng tỷ lệ Volume so với OI nền (`Wall Siege Ratio = Volume / OI`). Mốc Zero Gamma Flip ($S^*$) bắt buộc phải giải liên tục bằng phương trình hàm giải nghiệm số (Dekker-Brent `_brentq` thuần Python), không được dùng xấp xỉ strike thô để tránh sai lệch toán học do bất đẳng thức Jensen và Black-76 convexity.


8. **100% PURE CME GOLD FUTURES QUOTE INVARIANT:** Trong mọi phân tích, nhận định chiến lược, báo cáo và giao tiếp với người dùng, hệ thống **bắt buộc đồng bộ 100% chỉ sử dụng duy nhất giá Hợp đồng Tương lai Vàng (CME Gold Futures - GC / GCZ26)**. Tuyệt đối không tự ý quy đổi hoặc đề cập kèm giá Spot CFD / MT5 (XAUUSD) nếu người dùng không yêu cầu rõ ràng, nhằm tránh gây nhiễu và bảo toàn tính chuẩn xác tuyệt đối theo các mức Strike Options của sàn COMEX.

---

## 🧹 3. QUY ĐỊNH BẮT BUỘC: DỌN RÁC & BẢO TỒN DUNG LƯỢNG MÁY TÍNH (ZERO-WASTE MANDATE)

> [!CRITICAL]
> **TIÊU CHUẨN DUNG LƯỢNG TỐI THIỂU CHO MÁY TÍNH CỦA NGƯỜI DÙNG:**
> Toàn bộ dự án phải luôn được giữ ở mức siêu nhẹ (< 15MB). Mọi AI model khi thực thi đều phải tuân thủ nghiêm ngặt:
> 1. **Tự động dọn rác ngay lập tức:** Mọi file cào thử nghiệm (HTML/JSON tạm), script test scratch, file log tạm thời sinh ra trong quá trình nghiên cứu bắt buộc phải bị XÓA SẠCH SẼ ngay sau khi tác vụ hoàn thành.
> 2. **Không xả rác vào thư mục gốc:** Không tạo các file rác, file backup đuôi .bak, .tmp bừa bãi.
> 3. **Tận dụng đám mây (Cloud-First):** Ưu tiên chạy tính toán trên Google Colab / Codespaces, không cài đặt các gói dữ liệu nặng vào ổ cứng laptop của người dùng nếu không có yêu cầu rõ ràng.
