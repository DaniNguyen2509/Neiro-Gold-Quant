"""src/quant_engine/scenario_engine.py

Real-time Market Maker Scenario Engine for Neiro-Quant.
Evaluates the 6 core Market Maker operational scenarios (KB-1 to KB-6)
purely based on CME Gold Futures real-time prices vs structural dealer levels.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional


class AlertLevel(str, Enum):
    GREEN = "GREEN"      # Co hoi mua / Support defended
    YELLOW = "YELLOW"    # Canh bao bien do / Cho doi / Nén giá
    RED = "RED"          # Bao dong do: Squeeze hoac Thung san Air pocket
    GRAY = "GRAY"        # Trung lap / Cho tin hieu


class ActionDirective(str, Enum):
    WAIT = "DUNG_NGOAI_CHO"
    BUY_REBOUND = "BUY_BAT_HOI"
    BUY_BREAKOUT = "BUY_MUA_DUOI"
    SELL_FADE = "SELL_BAN_CHAN"
    SELL_BREAKDOWN = "SELL_BAN_THAO"


@dataclass(frozen=True, slots=True)
class ScenarioItem:
    code: str                  # "KB-1" .. "KB-6"
    title: str                 # Ten kich ban
    mm_state: str              # Hanh vi / Trang thai cua MM
    condition_desc: str        # Dieu kien gia CME
    alert_level: AlertLevel    # RED, GREEN, YELLOW, GRAY
    action: ActionDirective    # Action enum
    action_label: str          # Label hanh dong to ro
    entry_trigger: float       # Gia kich hoat CME
    entry_desc: str            # Mo ta diem vao
    hard_sl: float             # Cat lo CME
    take_profit: float         # Chot loi CME
    lot_size: float            # Lot khuyen nghi ($10k risk 1%)
    forecast: str              # Du doan huong di 1 cau
    is_active: bool = False    # Kich ban dang xay ra
    active_reason: str = ""    # Ly do kich hoat hien tai


@dataclass(frozen=True, slots=True)
class ScenarioEvaluationResult:
    active_scenario: ScenarioItem
    all_scenarios: List[ScenarioItem]
    spot_price: float
    atm_strike: float
    strike_above: float
    strike_below: float
    call_wall: float
    put_wall: float


def evaluate_market_scenarios(
    spot_price: float,
    atm_strike: float,
    strike_above: float,
    strike_below: float,
    call_wall: float,
    call_wall_oi: int,
    put_wall: float,
    put_wall_oi: int,
    regime: str = "NEUTRAL",
    total_gex: float = 0.0,
    total_chex: float = 0.0,
    has_up_air_pocket: bool = False,
    has_down_air_pocket: bool = False,
    major_up_wall: float = 0.0,
    major_down_wall: float = 0.0,
    recommended_lots: float = 0.22,
) -> ScenarioEvaluationResult:
    """Evaluates the 6 real-time Market Maker scenarios based on pure CME Gold Futures price.

    Returns the active scenario (with highest priority) and all 6 scenarios formatted for UI display.
    """
    buffer = 1.50
    if major_up_wall <= 0:
        major_up_wall = call_wall if call_wall > strike_above else strike_above + 25.0
    if major_down_wall <= 0:
        major_down_wall = put_wall if put_wall < strike_below else strike_below - 25.0

    # Determine which scenario is active based on real-time price
    active_code = "KB-6"
    active_reason = ""

    # Priority 1: High-alert boundary breaches
    if spot_price >= strike_above + buffer:
        active_code = "KB-3"
        active_reason = f"Gia ${spot_price:,.2f} vuot qua tran ${strike_above:,.0f} -> MM vo tran Short"
    elif spot_price <= strike_below - buffer:
        active_code = "KB-5"
        active_reason = f"Gia ${spot_price:,.2f} dam thung san ${strike_below:,.0f} -> MM buong xuoi xa lu"
    elif strike_above - 2.0 <= spot_price < strike_above + buffer:
        active_code = "KB-2"
        active_reason = f"Gia ${spot_price:,.2f} cham vung tran ${strike_above:,.0f} -> MM ban chan phong thu"
    elif strike_below - buffer < spot_price <= strike_below + 2.0:
        active_code = "KB-4"
        active_reason = f"Gia ${spot_price:,.2f} cham vung san ${strike_below:,.0f} -> MM dem mua do gia"
    elif (strike_below + 2.0 < spot_price < strike_above - 2.0):
        active_code = "KB-1"
        active_reason = f"Gia ${spot_price:,.2f} kep trong bien do ${strike_below:,.0f} - ${strike_above:,.0f} -> MM ghim gia"
    else:
        active_code = "KB-6"
        active_reason = f"Gia ${spot_price:,.2f} o vung trung lap, chua cham moc kich hoat"

    # Define all 6 structured scenarios
    all_scenarios: List[ScenarioItem] = [
        ScenarioItem(
            code="KB-1",
            title="Giằng Co Nén Biên Độ (Pinning Box)",
            mm_state="MM đang ghìm giá giữa hai chốt chặn để bào mòn phí thời gian và ăn trọn tiền phế.",
            condition_desc=f"${strike_below + 2.0:,.1f} < Giá CME < ${strike_above - 2.0:,.1f} (Hiện tại: ${spot_price:,.2f})",
            alert_level=AlertLevel.YELLOW,
            action=ActionDirective.WAIT,
            action_label="ĐỨNG NGOÀI (CẤM ĐÁNH BREAKOUT)",
            entry_trigger=atm_strike,
            entry_desc=f"Vùng nén ${strike_below:,.0f} ◄► ${strike_above:,.0f}",
            hard_sl=0.0,
            take_profit=0.0,
            lot_size=0.0,
            forecast="Giá tiếp tục đi ngang lừ đừ trong biên độ hẹp, chờ phiên Mỹ phá vỡ.",
            is_active=(active_code == "KB-1"),
            active_reason=active_reason if active_code == "KB-1" else "",
        ),
        ScenarioItem(
            code="KB-2",
            title="MM Chặn Bán Phòng Thủ Trần (Call Defense)",
            mm_state="MM tung lệnh bán Futures lớn để bảo vệ trần quyền chọn Call đã bán khống.",
            condition_desc=f"Chạm vùng cản ${strike_above - 1.5:,.1f} - ${strike_above:,.1f} (Hiện tại: ${spot_price:,.2f})",
            alert_level=AlertLevel.YELLOW,
            action=ActionDirective.SELL_FADE,
            action_label="SELL BÁN ĐẢO CHIỀU (FADE)",
            entry_trigger=strike_above - 1.0,
            entry_desc=f"Bán khi giá chạm ${strike_above - 1.0:,.2f} có nến rút chân",
            hard_sl=strike_above + 2.50,
            take_profit=atm_strike,
            lot_size=recommended_lots,
            forecast="Giá bị cản dội ngược trở lại mốc cân bằng ATM.",
            is_active=(active_code == "KB-2"),
            active_reason=active_reason if active_code == "KB-2" else "",
        ),
        ScenarioItem(
            code="KB-3",
            title="MM Vỡ Trận Short (Gamma Squeeze)",
            mm_state="MM cháy trần Short Gamma, thuật toán buộc phải MUA Futures ồ ạt để phòng hộ.",
            condition_desc=f"Vượt bứt phá > ${strike_above + buffer:,.2f} (Hiện tại: ${spot_price:,.2f})",
            alert_level=AlertLevel.RED,
            action=ActionDirective.BUY_BREAKOUT,
            action_label="BUY MUA ĐUỔI THEO MM (SQUEEZE)",
            entry_trigger=strike_above + buffer + 0.50,
            entry_desc=f"Mua đuổi khi vượt nến đóng trên ${strike_above + buffer:,.2f}",
            hard_sl=strike_above - 2.0,
            take_profit=major_up_wall - 1.0,
            lot_size=recommended_lots,
            forecast=f"Giá tăng tốc cực mạnh quét qua vùng cản, hướng thẳng lên ${major_up_wall:,.0f}.",
            is_active=(active_code == "KB-3"),
            active_reason=active_reason if active_code == "KB-3" else "",
        ),
        ScenarioItem(
            code="KB-4",
            title="MM Đệm Mua Bảo Vệ Sàn Đáy (Put Defense)",
            mm_state="MM gom mua Futures thụ động để bảo vệ sàn Put Wall, ngăn giá giảm thêm.",
            condition_desc=f"Chạm vùng sàn ${strike_below:,.1f} - ${strike_below + 1.5:,.1f} (Hiện tại: ${spot_price:,.2f})",
            alert_level=AlertLevel.GREEN,
            action=ActionDirective.BUY_REBOUND,
            action_label="BUY BẮT HỒI (REBOUND)",
            entry_trigger=strike_below + 1.0,
            entry_desc=f"Mua khi giá chạm ${strike_below + 1.0:,.2f} có nến rút chân",
            hard_sl=strike_below - 3.50,
            take_profit=atm_strike,
            lot_size=recommended_lots,
            forecast="Giá phản ứng rút chân tại đệm đỡ, bật hồi phục về trục ATM.",
            is_active=(active_code == "KB-4"),
            active_reason=active_reason if active_code == "KB-4" else "",
        ),
        ScenarioItem(
            code="KB-5",
            title="Thủng Sàn & Xả Lũ (Air Pocket Slide)",
            mm_state="Thủng đệm đỡ, phía dưới là túi rỗng Air Pocket. MM buông xuôi và xả hàng bán tháo.",
            condition_desc=f"Thủng dứt khoát < ${strike_below - buffer:,.2f} (Hiện tại: ${spot_price:,.2f})",
            alert_level=AlertLevel.RED,
            action=ActionDirective.SELL_BREAKDOWN,
            action_label="CẤM BẮT ĐÁY / SELL BÁN THÁO",
            entry_trigger=strike_below - buffer - 0.50,
            entry_desc=f"Đánh theo đà rơi khi nến đóng dưới ${strike_below - buffer:,.2f}",
            hard_sl=strike_below + 2.0,
            take_profit=major_down_wall + 1.0,
            lot_size=recommended_lots,
            forecast=f"Giá rơi tự do không phanh qua vùng rỗng lệnh về đáy ${major_down_wall:,.0f}.",
            is_active=(active_code == "KB-5"),
            active_reason=active_reason if active_code == "KB-5" else "",
        ),
        ScenarioItem(
            code="KB-6",
            title="Vùng Trung Lập (Neutral Floating)",
            mm_state="Giá đang trôi ở khoảng trống giữa các mốc, MM chưa kích hoạt phòng hộ lớn.",
            condition_desc=f"Nằm cách xa các mốc kích hoạt trên và dưới (Hiện tại: ${spot_price:,.2f})",
            alert_level=AlertLevel.GRAY,
            action=ActionDirective.WAIT,
            action_label="KIÊN NHẪN CHỜ ĐỢI",
            entry_trigger=0.0,
            entry_desc="Không vào lệnh lưng chừng để tránh rủi ro nhiễu",
            hard_sl=0.0,
            take_profit=0.0,
            lot_size=0.0,
            forecast="Giá tiếp tục trôi tự do tìm kiếm mốc kích hoạt gần nhất.",
            is_active=(active_code == "KB-6"),
            active_reason=active_reason if active_code == "KB-6" else "",
        ),
    ]

    active_item = next((s for s in all_scenarios if s.code == active_code), all_scenarios[0])

    return ScenarioEvaluationResult(
        active_scenario=active_item,
        all_scenarios=all_scenarios,
        spot_price=spot_price,
        atm_strike=atm_strike,
        strike_above=strike_above,
        strike_below=strike_below,
        call_wall=call_wall,
        put_wall=put_wall,
    )
