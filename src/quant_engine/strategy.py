"""Tier 5: Quantitative Strategy & Rule-Based Execution Matrix.

Pure deterministic mathematical logic - 0 external AI dependencies.
Generates institutional-grade trade setups (Fade Reversal, Breakout Runner),
risk regimes, and hard prohibitions directly from Options GEX/OI microstructure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True, slots=True)
class TradeSetup:
    name: str
    direction: Literal["BUY", "SELL"]
    setup_type: Literal["FADE_REVERSAL", "BREAKOUT_RUNNER", "ATM_PIVOT_MEAN_REVERSION"]
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward: float
    trigger_condition: str
    rationale: str


@dataclass(frozen=True, slots=True)
class QuantExecutionReport:
    session_name: str
    spot_price: float
    futures_price: float
    basis: float
    total_net_gex: float
    gex_regime: str
    call_wall_spot: float
    call_wall_futures: float
    call_wall_oi: int
    put_wall_spot: float
    put_wall_futures: float
    put_wall_oi: int
    synthetic_pivot_spot: float
    synthetic_pivot_futures: float
    upper_1s_spot: float
    lower_1s_spot: float
    upper_085s_spot: float
    lower_085s_spot: float
    air_pocket_strikes_cme: list[float]
    air_pocket_strikes_spot: list[float]
    setups: list[TradeSetup] = field(default_factory=list)
    prohibitions: list[str] = field(default_factory=list)

    def render_terminal(self) -> str:
        regime_desc = (
            "Dealer MUA khi giá giảm, BÁN GHÌM khi giá tăng => HẤP THỤ BIẾN ĐỘNG (Mean-Reverting)"
            if self.total_net_gex > 0
            else "Dealer BÁN THÁO khi giá giảm, MUA ĐUỔI khi giá tăng => KHUẾCH ĐẠI ĐÀ TRƯỢT GIÁ (Trend Acceleration)"
        )

        setups_text = []
        for s in self.setups:
            setups_text.append(
                f"   ▶️ {s.name} ({s.direction})\n"\
                f"      • Điều kiện kích hoạt: {s.trigger_condition}\n"\
                f"      • Entry: {s.entry:.2f} | Stop Loss: {s.stop_loss:.2f}\n"\
                f"      • Take Profit 1: {s.take_profit_1:.2f} | TP2: {s.take_profit_2:.2f}\n"\
                f"      • Risk/Reward Ratio: 1 : {s.risk_reward:.1f}\n"\
                f"      • Cơ sở vi mô: {s.rationale}"
            )
        setups_block = "\n\n".join(setups_text)

        prohibitions_block = "\n".join([f"   • [!] {p}" for p in self.prohibitions])

        banner = "=" * 88
        report = f"""
{banner}
🏛️ BẢN KẾ HOẠCH TÁC CHIẾN ĐỊNH LƯỢNG THUẦN TOÁN HỌC (NEIRO-QUANT ENGINE v2.0)
   PHIÊN: {self.session_name} | SPOT: {self.spot_price:.2f} | FUTURES CME: {self.futures_price:.2f} | BASIS: {self.basis:+.2f}
{banner}

1. TRẠNG THÁI CẤU TRÚC VI MÔ & ĐỊNH VỊ DEALER (MICROSTRUCTURE & REGIME)
   • Chế độ Gamma: {self.gex_regime}
   • Tổng Net GEX: {self.total_net_gex:+.2f} Triệu USD
   • Cơ chế tạo lập: {regime_desc}

2. MA TRẬN CHỐT CHẶN TRỌNG YẾU (KEY CHOKEPOINTS - CHIẾU SPOT XAUUSD)
   • 🛡️ Major Put Wall  : Spot {self.put_wall_spot:.2f} (CME {self.put_wall_futures:.1f} | OI: {self.put_wall_oi:,})
   • 🎯 Synthetic Pivot  : Spot {self.synthetic_pivot_spot:.2f} (CME {self.synthetic_pivot_futures:.2f} | Mốc cân bằng Put-Call)
   • 🏰 Major Call Wall : Spot {self.call_wall_spot:.2f} (CME {self.call_wall_futures:.1f} | OI: {self.call_wall_oi:,})
   • 📏 Expected Move 1σ : [{self.lower_1s_spot:.2f} <=====> {self.upper_1s_spot:.2f}] (Biên dao động thống kê 68.2%)
   • 📐 Dải bảo thủ 0.85σ: [{self.lower_085s_spot:.2f} <=====> {self.upper_085s_spot:.2f}] (Vùng phòng thủ thực chiến)

3. NHẬN DIỆN VÙNG CHÂN KHÔNG THANH KHOẢN (AIR POCKETS & SLIPPAGE RISK)
   • CME Strikes mỏng OI (<35% trung bình): {self.air_pocket_strikes_cme}
   • Vùng nguy hiểm trên Spot XAUUSD:       {self.air_pocket_strikes_spot}
   • Cảnh báo: Giá rơi vào các vùng này sẽ trượt dốc không phanh do thiếu lực đỡ Passive Limit!

4. MA TRẬN TÁC CHIẾN TỰ ĐỘNG (RULE-BASED EXECUTION MATRIX)
{setups_block}

5. ⛔ LỆNH CẤM TỐI CAO (HARD CONSTRAINTS)
{prohibitions_block}
{banner}
"""
        return report


def build_quant_execution_plan(
    session_name: str,
    spot_price: float,
    futures_price: float,
    basis: float,
    total_net_gex: float,
    gex_regime: str,
    call_wall_futures: float,
    call_wall_spot: float,
    call_wall_oi: int,
    put_wall_futures: float,
    put_wall_spot: float,
    put_wall_oi: int,
    synthetic_pivot_futures: float,
    synthetic_pivot_spot: float,
    upper_1s_spot: float,
    lower_1s_spot: float,
    upper_085s_spot: float,
    lower_085s_spot: float,
    air_pocket_strikes_cme: list[float],
) -> QuantExecutionReport:
    air_pockets_spot = [round(k - basis, 2) for k in air_pocket_strikes_cme]

    setups: list[TradeSetup] = []

    # 1. Fade Put Wall
    fade_buy_entry = round(put_wall_spot, 2)
    fade_buy_sl = round(put_wall_spot - 2.0, 2)
    fade_buy_tp1 = round(max(synthetic_pivot_spot, put_wall_spot + 5.0), 2) if put_wall_spot >= synthetic_pivot_spot else round(synthetic_pivot_spot, 2)
    fade_buy_tp2 = round(max(call_wall_spot, fade_buy_tp1 + 5.0), 2)
    rr_buy = round(abs(fade_buy_tp1 - fade_buy_entry) / max(0.5, abs(fade_buy_entry - fade_buy_sl)), 2)
    setups.append(
        TradeSetup(
            name="KÈO 1: FADE BUY TẠI PUT WALL (Bắt Đảo Chiều)",
            direction="BUY",
            setup_type="FADE_REVERSAL",
            entry=fade_buy_entry,
            stop_loss=fade_buy_sl,
            take_profit_1=fade_buy_tp1,
            take_profit_2=fade_buy_tp2,
            risk_reward=rr_buy,
            trigger_condition=f"Giá test vùng {fade_buy_entry:.2f} và nến M5 rút chân xác nhận lực hấp thụ (Absorption)",
            rationale="Khai thác lực mua phòng hộ của Dealer tại chốt chặn Put Wall tập trung OI lớn nhất.",
        )
    )

    # 2. Fade Call Wall
    fade_sell_entry = round(call_wall_spot, 2)
    fade_sell_sl = round(call_wall_spot + 2.0, 2)
    fade_sell_tp1 = round(min(synthetic_pivot_spot, call_wall_spot - 5.0), 2) if call_wall_spot <= synthetic_pivot_spot else round(synthetic_pivot_spot, 2)
    fade_sell_tp2 = round(min(put_wall_spot, fade_sell_tp1 - 5.0), 2)
    rr_sell = round(abs(fade_sell_entry - fade_sell_tp1) / max(0.5, abs(fade_sell_sl - fade_sell_entry)), 2)
    setups.append(
        TradeSetup(
            name="KÈO 2: FADE SELL TẠI CALL WALL (Đánh Chặn Đỉnh)",
            direction="SELL",
            setup_type="FADE_REVERSAL",
            entry=fade_sell_entry,
            stop_loss=fade_sell_sl,
            take_profit_1=fade_sell_tp1,
            take_profit_2=fade_sell_tp2,
            risk_reward=rr_sell,
            trigger_condition=f"Giá chạm vùng {fade_sell_entry:.2f} và xuất hiện nến M5 từ chối giá (Pinbar/Bearish Engulfing)",
            rationale="Khai thác lực bán ghìm chỉ số của Dealer tại Call Wall để bảo vệ lượng quyền chọn đã bán.",
        )
    )

    # 3. Breakdown Runner
    breakdown_trigger = round(put_wall_spot - 1.5, 2)
    breakdown_sl = round(put_wall_spot + 1.2, 2)
    breakdown_tp = round(lower_1s_spot, 2)
    rr_bd = round(abs(breakdown_trigger - breakdown_tp) / max(0.5, abs(breakdown_sl - breakdown_trigger)), 2)
    setups.append(
        TradeSetup(
            name="KÈO 3: BREAKDOWN RUNNER (Đánh Phá Vỡ Đón Tháo Chạy)",
            direction="SELL",
            setup_type="BREAKOUT_RUNNER",
            entry=breakdown_trigger,
            stop_loss=breakdown_sl,
            take_profit_1=breakdown_tp,
            take_profit_2=round(lower_1s_spot - 5.0, 2),
            risk_reward=rr_bd,
            trigger_condition=f"Nến M5 đóng cửa dứt khoát dưới {breakdown_trigger:.2f} (Xuyên thủng Put Wall vào khoảng trống thanh khoản)",
            rationale="Dealer bị kẹp vị thế và buộc phải quét lệnh khẩn cấp bán đuổi, kích hoạt đà trượt giá.",
        )
    )

    # 4. Breakout Runner
    breakout_trigger = round(call_wall_spot + 1.5, 2)
    breakout_sl = round(call_wall_spot - 1.2, 2)
    breakout_tp = round(upper_1s_spot, 2)
    rr_bo = round(abs(breakout_tp - breakout_trigger) / max(0.5, abs(breakout_trigger - breakout_sl)), 2)
    setups.append(
        TradeSetup(
            name="KÈO 4: BREAKOUT RUNNER (Gamma Squeeze Đón Sóng Tăng)",
            direction="BUY",
            setup_type="BREAKOUT_RUNNER",
            entry=breakout_trigger,
            stop_loss=breakout_sl,
            take_profit_1=breakout_tp,
            take_profit_2=round(upper_1s_spot + 5.0, 2),
            risk_reward=rr_bo,
            trigger_condition=f"Nến M5 đóng cửa dứt khoát trên {breakout_trigger:.2f} (Bứt phá qua Call Wall)",
            rationale="Kích hoạt Gamma Squeeze: Dealer buộc phải mua Futures bù đắp Delta khi Call Wall bị xuyên thủng.",
        )
    )

    prohibitions = [
        f"TUYỆT ĐỐI CẤM BẮT ĐÁY khi giá phá thủng {put_wall_spot:.2f} mà nến M5 chưa tạo cấu trúc rút chân!",
        f"TUYỆT ĐỐI CẤM ĐỠ DAO trong vùng Air Pockets: {air_pockets_spot} (Tốc độ trượt giá cực cao do thiếu thanh khoản)!",
        f"CẤM ĐẶT TAKE PROFIT vượt ra ngoài dải biên 1-Sigma [{lower_1s_spot:.2f} - {upper_1s_spot:.2f}] trong phiên thường!",
    ]
    if total_net_gex < 0:
        prohibitions.insert(0, "CẢNH BÁO REGIME SHORT GAMMA: Thị trường có xu hướng khuếch đại trend. CẤM đánh chặn đầu sóng ngược xu hướng!")

    return QuantExecutionReport(
        session_name=session_name,
        spot_price=spot_price,
        futures_price=futures_price,
        basis=basis,
        total_net_gex=total_net_gex,
        gex_regime=gex_regime,
        call_wall_spot=call_wall_spot,
        call_wall_futures=call_wall_futures,
        call_wall_oi=call_wall_oi,
        put_wall_spot=put_wall_spot,
        put_wall_futures=put_wall_futures,
        put_wall_oi=put_wall_oi,
        synthetic_pivot_spot=synthetic_pivot_spot,
        synthetic_pivot_futures=synthetic_pivot_futures,
        upper_1s_spot=upper_1s_spot,
        lower_1s_spot=lower_1s_spot,
        upper_085s_spot=upper_085s_spot,
        lower_085s_spot=lower_085s_spot,
        air_pocket_strikes_cme=air_pocket_strikes_cme,
        air_pocket_strikes_spot=air_pockets_spot,
        setups=setups,
        prohibitions=prohibitions,
    )
