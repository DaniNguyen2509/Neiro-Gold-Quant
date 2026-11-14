# CLAUDE.md

Luật làm việc trong kho Neiro-Quant. Đọc hết file này **trước khi sửa dòng code đầu tiên**.

Nguồn sự thật: [docs/spec.md](docs/spec.md) (đặc tả hệ thống) và
[docs/architecture.md](docs/architecture.md) (kiến trúc).
Chỗ nào tài liệu nói khác **mã nguồn** thì **mã nguồn đúng**.

---

## 0. Quy trình gọi Skill bắt buộc (Skill Protocol)

> **BẮT BUỘC TRƯỚC MỖI PHẢN HỒI HOẶC SỬA CODE:**
> Claude/Agent phải tra cứu và kích hoạt skill phù hợp từ thư mục .agents/skills/
> (xem chi tiết ánh xạ intent tại [AGENTS.md](AGENTS.md)).
> Mọi phản hồi phải kèm header xác nhận:
> [Active Skill: <tên-skill> | Path: .agents/skills/<tên-skill>/SKILL.md].

---

## 1. Kho này có gì

| Thành phần | Vai trò | Đường dẫn |
|---|---|---|
| **2TC-v10** | Indicator tín hiệu (Pine) | tradingview/2TC-v10.pine |
| **2TC-v10** | Indicator tín hiệu (MT5) | mt5/Indicators/2TC-v10.mq5 |
| **Neiro-Liquidity-Map-v2** | Bản đồ thanh khoản (Pine) | tradingview/Neiro-Liquidity-Map-v2.pine |
| **Neiro-Liquidity-Map-v2** | Bản đồ thanh khoản (MT5) | mt5/Indicators/Neiro-Liquidity-Map-v2.mq5 |
| **Quant Engine** | Lõi tính toán Python | src/quant_engine/ |
| **Collector** | Thu thập Options Chain | src/collector/ |
| **MT5 Bridge** | Cầu nối Python-MT5 | src/mt5_bridge/ |
| **HUD** | All-in-One Terminal & Live Bridge HUD | src/hud/ |

---

## 2. Luật không được phá

1. **Không tự ý đổi tham số mặc định** của 2 indicator sẵn có.
2. **ASCII và không emoji** trong code MQL5. Pine và Markdown dùng tiếng Việt có dấu.
3. **Performance constraints:** CPU < 5%, RAM cố định, zero memory leak.
4. **Không tự chế luật hoặc backtest** ngoài lề. Mọi thay đổi do owner chỉ đạo.
5. **Tuyệt đối LOẠI BỎ cột Latest** trên Barchart (stale prints).
6. **Tuyệt đối LOẠI BỎ bảng Greeks mặc định** của Barchart trong ngày 0DTE.
7. **CME Microstructure & Zero Gamma Invariant:** `Wall Siege Ratio = Volume / OI`; Zero Gamma Flip ($S^*$) giải liên tục bằng `_brentq` thuần Python.
8. **100% Pure CME Gold Futures (`GC` / `GC=F`):** Mọi phân tích, HUD, chiến lược và tài liệu đồng bộ duy nhất giá CME Gold Futures; không tự ý quy đổi Spot CFD `XAUUSD`.
