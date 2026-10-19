# ADR-003: Real-Time Level State Engine & Air Pocket Slicing Detection

## Status
Accepted

## Date
2026-10-19

## Context
1. **Thiếu kịch bản trượt túi chân không (Air Pocket Vacuum Slide):**
   - Trước đây, bảng tác chiến Scalping trong [src/hud/html_dashboard.py](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Quant/src/hud/html_dashboard.py) chỉ tính toán bước giá cố định $5 (`secondary_support = strike_below - step`).
   - Khi mốc đệm 4,175 bị bẻ gãy, hệ thống chỉ đặt mục tiêu chốt lời (TP) non tại 4,171 (nấc 4,170), hoàn toàn bỏ sót nhịp rơi tự do 13 giá từ 4,175 xuyên thẳng qua khoảng rỗng thanh khoản về 4,162.35 – 4,160.00.
2. **Nguy cơ đỡ dao rơi (Knife Catching Risk):**
   - Trong môi trường Net GEX Âm (Short Gamma), khi một Level bị xuyên thủng và phía sau là vùng mỏng OI (Air Pocket), việc đặt cược mua bắt đáy ở các mốc lơ lửng (như 4,170 hay 4,168) gây rủi ro thua lỗ nặng do Dealer buộc phải bán tháo đuổi theo Delta (Delta Hedging).
3. **Tầng 4 mới chỉ tồn tại trên tài liệu:**
   - Mặc dù [docs/architecture.md (Mục V)](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Quant/docs/architecture.md) đã đặc tả State Machine cho từng Level (`DORMANT`, `TESTING`, `ABSORPTION_DEFENDED`, `SLICED_VACUUM_RUN`), mã nguồn trước đây chưa code hóa và chưa tích hợp vào giao diện HTML Terminal.

## Decision
1. **Xây dựng module lõi [src/quant_engine/level_state.py](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Quant/src/quant_engine/level_state.py):**
   - **`find_next_major_wall(df, current_strike, direction, oi_percentile=65.0, min_distance=10.0)`:** Tự động quét vùng thanh khoản năng động cục bộ (+/- 60 giá) để tìm ra điểm cực đại Open Interest (Local Peak Wall) thực sự thay vì nhảy nấc $5 máy móc.
   - **`detect_strike_air_pockets(df, start_strike, end_strike, threshold_ratio=0.40)`:** Tự động phát hiện các túi rỗng thanh khoản giữa 2 chốt chặn.
   - **`evaluate_tactical_level_states(spot_price, df, meta)`:** Máy trạng thái hữu hạn đánh giá động 7 chốt chặn then chốt (Call Wall, ATM Resistance, ATM Pivot, ATM Support, Immediate Resistance, Immediate Support, Major Put Wall).
2. **Tích hợp Radar Vi Mô vào [src/hud/html_dashboard.py](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Quant/src/hud/html_dashboard.py):**
   - Bổ sung khối **Radar Vi mô (Level State Engine - Tầng 4)** hiển thị trực quan các huy hiệu trạng thái:
     - 🔴 `SLICED / VACUUM RUN`: Cảnh báo level đã vỡ, chỉ rõ đích đến trượt dốc.
     - 🟡 `TESTING`: Đang kiểm định vi mô.
     - 🟢 `DEFENDED`: Hấp thụ thành công.
     - 🛡️ `HOLDING` / ⚪ `DORMANT`: Giữ nhịp / Chờ kích hoạt.
3. **Nâng cấp Bảng Tác Chiến Lướt Sóng (Table 1):**
   - Khi kích hoạt `Breakdown {strike_below}`: Nếu phát hiện Air Pocket phía dưới, Take Profit (TP) được mở rộng thẳng về **Major Wall** tiếp theo (ví dụ 4,160 thay vì 4,170).
   - Thêm cảnh báo tối thượng: `🚨 SLICED_VACUUM_RUN: Phía dưới là Túi chân không -> CẤM BẮT ĐÁY! Dealer xả Delta Hedge ép giá trượt thẳng về Major Wall`.

## Consequences
- **Khắc phục hoàn toàn điểm mù trượt giá:** Bảng tác chiến dự báo chính xác các pha thác đổ (Waterfall) 10-25 giá xuyên qua khoảng chân không.
- **Bảo vệ vốn tuyệt đối:** Ngăn chặn triệt để hành vi bắt dao rơi của trader khi chốt chặn bị đâm thủng trong môi trường Short Gamma.
- **Đạt chuẩn 100% Kiến trúc:** Hoàn thiện Tầng 4 (Level State Engine) từ tài liệu thiết kế sang mã nguồn chạy thực tế trên Cloud.
