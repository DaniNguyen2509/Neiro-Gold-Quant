//+------------------------------------------------------------------+
//|                                         Neiro-Liquidity-Map-v2.mq5 |
//|  NEIRO LIQUIDITY MAP  v2  -  GTRADER EDITION                       |
//|                                                                    |
//|  Every level = one horizontal line drawn from the candle that made  |
//|  it, extended to the right, with a price label. Sessions, daily and  |
//|  weekly extremes, equal highs & lows, intraday pivots, and a memory  |
//|  of what has already been swept.                                    |
//|                                                                     |
//|  BAN MT5 CUA tradingview/Neiro-Liquidity-Map-v2.pine. So voi ban 1.0 |
//|  (mt5/Neiro-Liquidity-Map.mq5, da XOA 23-08) co them:               |
//|    1. Phien thu NAM - NY Lunch 11:00-13:00 NY, mac dinh TAT.        |
//|    2. Lop ICT MACROS port tu "GTrader-ICT All In One - Community    |
//|       Version" - 5 cua so 20 phut, vach tren + vach duoi + nhan.    |
//|    3. Lop PROJECTION CANDLES - cum nen W / D / H4 / H1 ve o le phai, |
//|       cau tao than / vien / rau tach mau theo nhom "5.HTF Candles"  |
//|       cua ban goc GTrader, kem dem nguoc, moc ngay, nhan gia, trace. |
//|    4. Box vung phien: moi phien mot cong tac + mau VIEN + mau NEN    |
//|       rieng, cong day / net vien dung chung.                        |
//|                                                                     |
//|  23-08: lop PREMIUM & DISCOUNT (port 1:1 LuxAlgo SMC) da GO HAN o    |
//|  day nua - ban Pine go tu 22-08. Nay chi con MOT ban duy nhat, chinh |
//|  la ban dem ban, hai nen tang khop nhau tung lop. Lay lai lop do:    |
//|  git show b6dfc82:mt5/Neiro-Liquidity-Map-v2.mq5                     |
//|                                                                     |
//|  Chart objects use the NL_ prefix. All time anchors use New York     |
//|  time (auto DST). No orders placed.                                 |
//+------------------------------------------------------------------+
#property copyright "Neiro-Gold"
#property link      "https://www.mql5.com/en/users/daniel.nguyen2509"
#property version   "2.00"
#define NL_VER "2.0"
#property description "ICT liquidity map. Every level drawn from the candle that made it:"
#property description "sessions, prev day/week, today, midnight open, ATH, equal highs/lows, H1-M15 pivots."
#property description "Swept levels turn grey - one per timeframe per side, so the chart stays readable."
#property description "Plus ICT macro windows and W/D/H4/H1 projection candles in the right margin."
#property description "New York time, auto DST. Display only - places no orders."
#property indicator_chart_window
#property indicator_plots 0

//==================================================================
//   ENUMS
//==================================================================
enum ENUM_NL_PRESET
  {
   NL_CUSTOM   = 0,   // Custom - use the checkboxes below
   NL_MINIMAL  = 1,   // Minimal - ATH, prev day, today, live session
   NL_DAYTRADE = 2,   // Day Trading - adds week, midnight open, EQH/EQL
   NL_FULL     = 3    // Full ICT - everything incl. H1/M15 pivots
  };

enum ENUM_NL_CORNER
  {
   NL_TR = 0,         // Top right
   NL_TL = 1,         // Top left
   NL_BR = 2,         // Bottom right
   NL_BL = 3,         // Bottom left
   NL_MR = 4,         // Middle right
   NL_ML = 5          // Middle left
  };

enum ENUM_NL_SCALE
  {
   NL_SCALE_PRICE = 0,   // Price - by price level only; tuned on gold
   NL_SCALE_ATR   = 1,   // Volatility - ATR 200 on D1; right unit on any symbol
   NL_SCALE_OFF   = 2    // Off - take the gold dollar values literally
  };

enum ENUM_NL_DAYZONE
  {
   NL_DAY_NY     = 0,   // New York (ICT)
   NL_DAY_BROKER = 1,   // Broker server time
   NL_DAY_UTC    = 2,   // UTC
   NL_DAY_CUSTOM = 3    // Custom UTC offset
  };

enum ENUM_NL_CROWD
  {
   NL_CROWD_STAGGER   = 0,   // Stagger into columns
   NL_CROWD_STRONGEST = 1,   // Keep the strongest only
   NL_CROWD_OVERLAP   = 2    // Show all, overlapping
  };

enum ENUM_NL_THEME
  {
   NL_DARK  = 0,      // Dark
   NL_LIGHT = 1       // Light
  };

enum ENUM_NL_DCLBL
  {
   NL_DCL_TOP  = 0,   // Top
   NL_DCL_BOT  = 1,   // Bottom
   NL_DCL_BOTH = 2,   // Both
   NL_DCL_OFF  = 3    // Off
  };

enum ENUM_NL_DCALIGN
  {
   NL_DCA_FOLLOW = 0, // Follow candles
   NL_DCA_ALIGN  = 1  // Align
  };

//==================================================================
//   INPUTS
//   Layout mirrors tradingview/Neiro-Liquid.pine group for group.
//   One row per layer: the switch first, then its colour, then its line.
//==================================================================
input group "GENERAL"
input ENUM_NL_PRESET InpPreset = NL_CUSTOM; // Preset (overrides the checkboxes)
input int    InpDaysBack      = 10;     // History depth (days)
input ENUM_NL_DAYZONE InpDayZone = NL_DAY_NY; // Day boundary
input int    InpDayUtcOff     = 2;      //    ... UTC offset in hours, for Custom only
input int    InpDayHour       = 0;      // Day starts at (hour); 17 + New York = forex day
input ENUM_NL_SCALE InpScaleMode = NL_SCALE_ATR;   // Scale thresholds to symbol
input int    InpTextSize      = 8;      // Label text size (pt)
input int    InpKeyTextSize   = 10;     // Key level text size (pt)

input group "DAILY & WEEKLY LEVELS"
input bool   InpShowAth  = true;                // All-Time High
input color  InpColAth   = C'255,215,0';        //    colour
input ENUM_LINE_STYLE InpStyAth = STYLE_SOLID;  //    line
input bool   InpShowPw   = true;                // Previous Week H/L
input color  InpColPw    = C'149,117,205';      //    colour
input ENUM_LINE_STYLE InpStyPw  = STYLE_DASH;   //    line
input bool   InpShowWk   = true;                // Current Week H/L
input color  InpColWk    = C'92,107,192';       //    colour
input ENUM_LINE_STYLE InpStyWk  = STYLE_SOLID;  //    line
input bool   InpShowPD   = true;                // Previous Day H/L
input color  InpColPd    = C'255,193,7';        //    colour
input ENUM_LINE_STYLE InpStyPd  = STYLE_DASH;   //    line
input bool   InpShowBpd  = false;               // Two Days Ago H/L
input color  InpColBpd   = C'255,224,130';      //    colour
input ENUM_LINE_STYLE InpStyBpd = STYLE_DASH;   //    line
input bool   InpShowDay  = true;                // Today H/L
input color  InpColDay   = C'38,198,218';       //    colour
input ENUM_LINE_STYLE InpStyDay = STYLE_SOLID;  //    line
input bool   InpShowMno  = true;                // Midnight Open (00:00 NY)
input color  InpColMno   = clrGray;             //    colour
input ENUM_LINE_STYLE InpStyMno = STYLE_DASH;   //    line

input group "SESSION LEVELS"
input bool   InpShowTokyo  = true;              // Tokyo
input int    InpTokyoOpen  = 0;                 //    open  (NY, HHMM)
input int    InpTokyoClose = 200;               //    close (NY, HHMM)
input color  InpColTk      = C'255,152,0';      //    colour - live
input color  InpColBTk     = C'255,204,128';    //    colour - earlier
input bool   InpShowLondon = true;              // London
input int    InpLondonOpen = 200;               //    open  (NY, HHMM)
input int    InpLondonClose= 930;               //    close (NY, HHMM)
input color  InpColLo      = C'41,98,255';      //    colour - live
input color  InpColBLo     = C'144,202,249';    //    colour - earlier
input bool   InpShowNyAm   = true;              // NY AM
input int    InpNyAmOpen   = 930;               //    open  (NY, HHMM)
input int    InpNyAmClose  = 1100;              //    close (NY, HHMM)
input color  InpColAm      = C'229,57,53';      //    colour - live
input color  InpColBAm     = C'239,154,154';    //    colour - earlier
input bool   InpShowLunch  = false;             // NY Lunch
input int    InpLunchOpen  = 1100;              //    open  (NY, HHMM)
input int    InpLunchClose = 1300;              //    close (NY, HHMM)
input color  InpColLu      = C'141,110,99';     //    colour - live
input color  InpColBLu     = C'188,170,164';    //    colour - earlier
input bool   InpShowNyPm   = true;              // NY PM
input int    InpNyPmOpen   = 1330;              //    open  (NY, HHMM)
input int    InpNyPmClose  = 1600;              //    close (NY, HHMM)
input color  InpColPm      = C'142,36,170';     //    colour - live
input color  InpColBPm     = C'206,147,216';    //    colour - earlier
input bool   InpShowPrevSess = true;                 // Show earlier sessions (p-prefixed)
input ENUM_LINE_STYLE InpStySess     = STYLE_SOLID;  //    line - live
input ENUM_LINE_STYLE InpStyPrevSess = STYLE_DASH;   //    line - earlier

input group "SESSION RANGES"
input bool   InpShowSessZone  = true;   // Draw session range box
// Hai o hinh dang CHUNG cho ca lop, dat ngay duoi cong tac tong - giong ban Pine
// 23-08. Truoc do chung nam duoi cung nhom nen owner doi mau nen roi tuong la hong.
input bool   InpSessZoneBrd   = true;               // Border
input int    InpSessZoneBrdW  = 1;                  //    ... width
input ENUM_LINE_STYLE InpSessZoneBrdS = STYLE_DASH; //    ... style
input bool   InpSessZoneFill  = true;               // Fill the boxes
// MT5 KHONG co kenh alpha cho OBJ_RECTANGLE. Ben Pine moi o mau tu mang do trong
// suot rieng (mac dinh 90%); o day mot o duy nhat, ap cho ca nam. Mau nen duoc TU
// TRON voi mau nen chart - box ve o che do BACK nen mat thuong thay y het Pine.
input int    InpSessZoneTrans = 90;                 //    ... fill transparency (0 = solid, 100 = invisible)
// Moi phien mot hang: [x] ten | mau VIEN | mau NEN. NY Lunch va NY PM mac dinh TAT -
// nam box chong nhau tren mot buoi chieu New York la qua nhieu hinh chu nhat.
// Fill = clrNONE on all five zones: owner's liquid.set 24-08 - only the border
// is drawn, the box body stays clear so candles read cleanly underneath.
input bool   InpZTok  = true;                       // Tokyo
input color  InpZTokB = C'255,152,0';               //    ... border
input color  InpZTokF = clrNONE;                    //    ... fill
input bool   InpZLon  = true;                       // London
input color  InpZLonB = C'41,98,255';               //    ... border
input color  InpZLonF = clrNONE;                    //    ... fill
input bool   InpZAm   = true;                       // NY AM
input color  InpZAmB  = C'229,57,53';               //    ... border
input color  InpZAmF  = clrNONE;                    //    ... fill
input bool   InpZLu   = false;                      // NY Lunch
input color  InpZLuB  = C'141,110,99';              //    ... border
input color  InpZLuF  = clrNONE;                    //    ... fill
input bool   InpZPm   = false;                      // NY PM
input color  InpZPmB  = C'142,36,170';              //    ... border
input color  InpZPmF  = clrNONE;                    //    ... fill
input int    InpSessZoneDays  = 3;      // Boxes kept per session
input bool   InpSessZoneLbl   = true;   // Session name on the box
input bool   InpSessZoneOpen  = false;  // Session opening price line
input ENUM_TIMEFRAMES InpSessTfMin = PERIOD_M1;  // Draw between (lowest TF)
input ENUM_TIMEFRAMES InpSessTfMax = PERIOD_MN1; // ... and (highest TF)

input group "EQUAL HIGHS & LOWS"
input bool   InpShowEq   = true;                // EQH / EQL
input color  InpColEq    = C'0,176,255';        //    colour
input ENUM_LINE_STYLE InpStyEq = STYLE_DOT;     //    line
input double InpEqRelIn  = 0.25;                //    relative tolerance ($ gold); 0 = exact match only

input group "INTRADAY PIVOTS"
input bool   InpShowPivH1  = true;                 // H1 pivots (unswept)
input color  InpColPvH1    = C'120,144,156';       //    colour
input ENUM_LINE_STYLE InpStyPvH1 = STYLE_SOLID;    //    line
input bool   InpShowPivM15 = false;                // M15 pivots (unswept)
input color  InpColPvM15   = C'176,190,197';       //    colour
input ENUM_LINE_STYLE InpStyPvM15 = STYLE_DOT;     //    line

input group "SWEPT LEVELS"
input color  InpSweptCol   = clrGray;   // Swept colour (line also turns dashed)
input bool   InpShowSwHist = false;     // Keep every swept level on the chart
input int    InpSwHistDays = 3;         //    ... but only this many days back

input group "DASHBOARD"
input bool   InpHud        = false;     // Show dashboard
input ENUM_NL_CORNER InpHudCorner = NL_TR;   // Position
input ENUM_NL_THEME  InpHudTheme  = NL_DARK; // Theme
input int    InpHudX       = 14;        // Offset X (px)
input int    InpHudY       = 18;        // Offset Y (px)
input int    InpHudFont    = 9;         // Font size (pt)
input int    InpHudWidth   = 306;       // Panel width (px); widened automatically if the font needs it
input bool   InpHudSess    = true;      // Session row
input bool   InpHudSwept   = true;      // Last-swept row

input group "LINES & LABELS"
input int    InpLineWidth     = 1;      // Line width
input int    InpLabelBars     = 5;      // Label offset from the live candle (bars)
input double InpMergeGapIn    = 1.0;    // Merge levels closer than ($ gold); 0 = keep all separate
input ENUM_NL_CROWD InpLabelCrowd = NL_CROWD_STAGGER; // When labels crowd
input double InpLabelGapIn    = 1.0;    // Separate labels closer than (gold $)
input int    InpLabelColBars  = 20;     // Label column step (bars); ceiling - columns squeeze if the chart is tight

input group "ALERTS"
input bool   InpAlertSweep  = true;     // Alert when liquidity is swept
input bool   InpAlertNear   = false;    // Alert when price approaches a level
input double InpNearDistIn  = 5.0;      //    within ($ gold)
input bool   InpAlertM15    = false;    // Alert for M15 levels
input bool   InpAlertPush   = false;    // Also send push notification (mobile)

input group "PROJECTION CANDLES"
// Cum nen gop W -> D -> H4 -> H1 ve o LE PHAI chart. Cau tao mot cay bam theo nhom
// "5.HTF Candles" cua GTrader-ICT: THAN / VIEN / RAU ba cap mau rieng, khoang trong
// giua cac cum, cho dat + can nhan, dem nguoc, moc ngay, nhan gia, vach trace.
// LUU Y RIENG CUA MT5: object chi ve duoc trong vung SHIFT ben phai nen cuoi. Zoom
// gan thi vung do it nen - ca cum se bi BOP LAI cho vua, giong cach cot nhan da lam.
input bool   InpDcWk     = false;   // Weekly
input int    InpDcWkNum  = 1;       //    ... bars (1-4)
input bool   InpDcDay    = false;   // Daily
input int    InpDcDayNum = 1;       //    ... bars (1-6)
input bool   InpDcH4     = false;   // H4
input int    InpDcH4Num  = 1;       //    ... bars (1-6)
input bool   InpDcH1     = false;   // H1
input int    InpDcH1Num  = 2;       //    ... bars (1-6)
input int    InpDcOffset = 40;      // Distance from the live candle (bars)
input int    InpDcGap    = 5;       // Gap between bars
input int    InpDcBody   = 1;       // Body width (bars)
input int    InpDcGrpGap = 10;      // Gap between timeframe groups (bars)
input color  InpDcBull   = C'8,153,129';    // Body - up
input color  InpDcBear   = C'242,54,69';    // Body - down
input color  InpDcBullBd = C'8,153,129';    // Border - up
input color  InpDcBearBd = C'242,54,69';    // Border - down
input color  InpDcBullWk = C'8,153,129';    // Wick - up
input color  InpDcBearWk = C'242,54,69';    // Wick - down
input color  InpDcText   = C'120,123,134';  // Label
input ENUM_NL_DCLBL   InpDcLblPos   = NL_DCL_TOP;    // Name label
input ENUM_NL_DCALIGN InpDcLblAlign = NL_DCA_FOLLOW; //    ... alignment
input bool   InpDcTimer  = false;   // Countdown (under the name)
input bool   InpDcStamp  = false;   // Date (under the candle)
input bool   InpDcPxLbl  = false;   // Price (right of the body)
input bool   InpDcTrace  = false;   // Trace lines back to the live candle
input bool   InpDcTrO    = true;    //    ... Open
input color  InpDcTrOC   = C'120,123,134';
input ENUM_LINE_STYLE InpDcTrOS = STYLE_DOT;
input bool   InpDcTrC    = true;    //    ... Close
input color  InpDcTrCC   = C'120,123,134';
input ENUM_LINE_STYLE InpDcTrCS = STYLE_DOT;
input bool   InpDcTrH    = true;    //    ... High
input color  InpDcTrHC   = C'120,123,134';
input ENUM_LINE_STYLE InpDcTrHS = STYLE_DOT;
input bool   InpDcTrL    = true;    //    ... Low
input color  InpDcTrLC   = C'120,123,134';
input ENUM_LINE_STYLE InpDcTrLS = STYLE_DOT;

input group "ICT MACROS"
// Moi macro = mot cua so 20 phut. Ve vach TREN (cuc dai) + vach DUOI (cuc tieu) chay
// theo gia trong suot cua so, cong mot nhan "MACRO hh:mm-hh:mm".
// LUU Y: day thuan tuy la lop HIEN THI - no khong sinh tin hieu nao.
input bool   InpMcOn     = true;    // Macro windows
input int    InpMcTfLim  = 3;       // Only draw at or below (minutes)
input double InpMcDistIn = 2.0;     // Line offset from the extreme (gold $)
input color  InpMcCol    = C'120,123,134';  // Lines & label
input int    InpMcKeep   = 1;       // Macros kept per window
// 999 = New York, tu doi theo DST (giong o Broker offset). So khac = mui gio CO DINH
// tinh bang gio so voi UTC, khong doi theo mua - dung nhu danh sach GMT cua ban goc.
input int    InpMcUtcOff = 999;     // Timezone (UTC hours; 999 = New York, auto DST)
input bool   InpMc1On    = true;    // Macro 1
input int    InpMc1S     = 950;     //    ... start (HHMM)
input int    InpMc1E     = 1010;    //    ... end   (HHMM)
input bool   InpMc1T     = true;    //    ... top line
input bool   InpMc1B     = false;   //    ... bottom line
input bool   InpMc2On    = true;    // Macro 2
input int    InpMc2S     = 1050;    //    ... start (HHMM)
input int    InpMc2E     = 1110;    //    ... end   (HHMM)
input bool   InpMc2T     = true;    //    ... top line
input bool   InpMc2B     = false;   //    ... bottom line
input bool   InpMc3On    = true;    // Macro 3
input int    InpMc3S     = 250;     //    ... start (HHMM)
input int    InpMc3E     = 310;     //    ... end   (HHMM)
input bool   InpMc3T     = true;    //    ... top line
input bool   InpMc3B     = false;   //    ... bottom line
input bool   InpMc4On    = true;    // Macro 4
input int    InpMc4S     = 350;     //    ... start (HHMM)
input int    InpMc4E     = 410;     //    ... end   (HHMM)
input bool   InpMc4T     = true;    //    ... top line
input bool   InpMc4B     = false;   //    ... bottom line
input bool   InpMc5On    = true;    // Macro 5
input int    InpMc5S     = 650;     //    ... start (HHMM)
input int    InpMc5E     = 710;     //    ... end   (HHMM)
input bool   InpMc5T     = true;    //    ... top line
input bool   InpMc5B     = false;   //    ... bottom line

input group "PERFORMANCE & DATA"
input int    InpOffsetHours = 999;      // Broker offset (hours); 999 = auto-detect
input int    InpRefreshMs   = 400;      // Minimum redraw interval (ms); 0 = every tick

//==================================================================
//   PRESET RESOLUTION
//   tier 1 = core, 2 = day-trading, 3 = full. A preset overrides the
//   checkboxes; NL_CUSTOM hands control back to them.
//==================================================================
bool NlOn(const bool userToggle,const int tier)
  {
   if(InpPreset==NL_CUSTOM)   return userToggle;
   if(InpPreset==NL_MINIMAL)  return tier<=1;
   if(InpPreset==NL_DAYTRADE) return tier<=2;
   return true;
  }

// Thresholds actually used by the engine. Filled by ApplyScale() at the top of
// every Draw(): the inputs above are GOLD dollars, these are the same distance
// expressed in whatever the chart symbol quotes in.
#define NL_REF_PRICE 4500.0
#define NL_REF_ATR   88.0
double InpEqRelUSD=0.25, InpMergeGapUSD=1.5, InpLabelGapUSD=2.0, InpNearDist=3.0, InpMcDist=2.0;
double g_scaleF=1.0;
long   g_brokerOff=0;   // set o dau Draw(); DayZoneOffset() can no
int    g_atrH=INVALID_HANDLE;

// How many H1 / M15 bars to pull. Derived from History depth instead of being an
// input: the engine discards anything older than that window anyway, so loading
// more is pure cost. 1.2x covers weekends; EqLoad() keeps its own 260-bar floor.
int    InpEqH1Bars=2000, InpEqM15Bars=5000;

// Redraw throttle. OnCalculate fires on every tick and OnTimer every second;
// without this, Draw() reloads thousands of bars dozens of times a second.
uint   g_lastDraw=0;

// The labels and the right margin need chart shift on, so OnInit turns it on -
// but that is the user's chart setting, not ours. Remember what it was and put
// it back on removal. Saved on every OnInit and restored on every OnDeinit, so
// a parameter change (deinit then init) round-trips correctly.
bool   g_prevShift=false;

// Y goc cua bang. Bang thuong = InpHudY; hai vi tri GIUA thi tinh theo chieu cao chart
// nen phai co bien rieng - HudCell doc bien nay chu khong doc thang o nhap.
int    g_hudY=18;

bool g_onSess=true, g_onPrevSess=true;
bool g_onSessArr[5];
bool g_onZoneArr[5];
bool g_onMacro=false;
bool g_onPd=true, g_onBpd=true, g_onDay=true, g_onPw=true, g_onWk=true;
bool g_onMno=true, g_onAth=true, g_onEq=true, g_onPvH1=true, g_onPvM15=true;

// Dashboard payload, filled at the end of Draw().
double g_hudPx=0, g_hudBslP=0, g_hudSslP=0;
string g_hudBslN="", g_hudSslN="", g_hudSwN="";
long   g_hudSwT=0;
string g_nearHiSig="", g_nearLoSig="";

// Set in OnInit: session range boxes only draw inside the chosen TF band.
bool g_sessZoneOn = false;

void HudDraw();
void NearAlert();
void ApplyScale();
void ResolvePreset();

const string PFX = "NL_";
#define LVL_MAX 500

//--- format theo loai (0..19) ---
// 0..9  = nam phien, moi phien hai suat: live va p-truoc do
//         (Tokyo 0/1, London 2/3, NY AM 4/5, NY Lunch 6/7, NY PM 8/9)
// 10..17 = PD / Day / EQ / H1 / M15 / BPD / PW / Week
// 18, 19 = MNO va ATH (ve ngoai pipeline gop nhung VAN chia cot chung, giong Pine).
// v2 chen NY Lunch vao 6/7 nen moi so tu 8 tro len da +2 so voi ban 1.0. Preset .set
// cua ban 1.0 KHONG dung lai duoc - phai dat lai tu dau.
color           g_fcol[20];
ENUM_LINE_STYLE g_fsty[20];
int             g_fsz[20];

//--- danh sach muc ---
struct Lvl { double price; string name; long formT; long sweptT; int fmt; };
Lvl g_lv[]; int g_nlv = 0;
int g_zoneN = 0;   // so box vung phien da ve trong luot Draw hien tai
int g_zoneDrawn = 0;  // so box cua luot TRUOC - de don dung phan du thua
double g_mnoPrice=0; long g_mnoT=0;   // MNO (Midnight Open NY) - ve doc lap
double g_athPrice=0; long g_athT=0;   // ATH (gia cao nhat lich su) - ve doc lap

//--- ALERT sweep (chong spam: nho cac muc DA bao, seed luc attach) ---
bool   g_alertInit=false;
string g_alertSeen=";";

string TfStr(){ return StringSubstr(EnumToString((ENUM_TIMEFRAMES)_Period),7); }
void FireAlert(const string msg){ Alert(msg); if(InpAlertPush) SendNotification(msg); }

//--- MQL5 iBarShift false = tra ve bar <= thoi gian truyen vao, bi sai khi can tim bar dau phien
int BarShiftOpen(long t)
  {
   int b = iBarShift(_Symbol, PERIOD_CURRENT, (datetime)t, false);
   if(b >= 0 && (long)iTime(_Symbol, PERIOD_CURRENT, b) < t) b = b - 1;
   return b;
  }

//--- MT5 KHONG co kenh alpha cho OBJ_RECTANGLE. Nhung box ve o che do BACK thi nen
//--- chart va NEN cua chinh box deu nam duoi cay nen, nen chi can TU TRON mau voi mau
//--- nen chart la ra dung cai Pine thay duoc bang color.new(col, trans). Doc mau nen
//--- THAT tu chart nen chart sang hay toi deu dung, khong phai hardcode ban toi.
//--- trans = DO TRONG SUOT, khong phai do dam: 0 = dac kin, 100 = tang hinh.
//--- (Ham nay sinh ra cho lop Premium & Discount, lop do da go 23-08; nay box vung
//--- phien va than nen projection dung no.)
color BlendBg(const color col,const int trans)
  {
   int t=trans; if(t<0) t=0; if(t>100) t=100;
   color bg = (color)ChartGetInteger(0,CHART_COLOR_BACKGROUND);
   double k = (100.0-(double)t)/100.0;
   int cr=(int)(col&0xFF),       cg =(int)((col>>8)&0xFF), cb=(int)((col>>16)&0xFF);
   int br=(int)(bg &0xFF),       bg2=(int)((bg >>8)&0xFF), bb=(int)((bg >>16)&0xFF);
   int r=(int)(br +(cr -br )*k), g  =(int)(bg2+(cg-bg2)*k), b=(int)(bb +(cb -bb )*k);
   return (color)((b<<16)|(g<<8)|r);
  }

//--- box vung phien (OBJ_RECTANGLE) ---
// MT5 chi cho MOT mau tren mot OBJ_RECTANGLE: bat OBJPROP_FILL la ca vien lan nen deu
// an mau do. Ban Pine 23-08 cho moi phien mot mau VIEN va mot mau NEN rieng, nen o day
// phai ve HAI hinh chu nhat chong khit: NL_ZF (to nen, tao TRUOC nen nam duoi) va
// NL_Z (chi vien, nam tren).
void DrawZone(const long tL,const long tR,const double hi,const double lo,
              const color brdCol,const color fillCol,const string sname,const double opx)
  {
   string fn="NL_ZF"+IntegerToString(g_zoneN);
   if(InpSessZoneFill)
     {
      if(ObjectFind(0,fn)<0)
        { ObjectCreate(0,fn,OBJ_RECTANGLE,0,(datetime)tL,hi,(datetime)tR,lo);
          ObjectSetInteger(0,fn,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,fn,OBJPROP_HIDDEN,true); }
      ObjectMove(0,fn,0,(datetime)tL,hi); ObjectMove(0,fn,1,(datetime)tR,lo);
      ObjectSetInteger(0,fn,OBJPROP_COLOR,BlendBg(fillCol,InpSessZoneTrans));
      ObjectSetInteger(0,fn,OBJPROP_STYLE,STYLE_SOLID);
      ObjectSetInteger(0,fn,OBJPROP_WIDTH,1);
      ObjectSetInteger(0,fn,OBJPROP_FILL,true);
      ObjectSetInteger(0,fn,OBJPROP_BACK,true);
     }
   else ObjectDelete(0,fn);

   string bn="NL_Z"+IntegerToString(g_zoneN);
   const color col=brdCol;                     // nhan ten + duong Open an theo mau vien
   if(InpSessZoneBrd)
     {
      if(ObjectFind(0,bn)<0)
        { ObjectCreate(0,bn,OBJ_RECTANGLE,0,(datetime)tL,hi,(datetime)tR,lo);
          ObjectSetInteger(0,bn,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,bn,OBJPROP_HIDDEN,true); }
      ObjectMove(0,bn,0,(datetime)tL,hi); ObjectMove(0,bn,1,(datetime)tR,lo);
      ObjectSetInteger(0,bn,OBJPROP_COLOR,brdCol);
      ObjectSetInteger(0,bn,OBJPROP_STYLE,InpSessZoneBrdS);
      ObjectSetInteger(0,bn,OBJPROP_WIDTH,MathMax(1,InpSessZoneBrdW));
      ObjectSetInteger(0,bn,OBJPROP_FILL,false);
      ObjectSetInteger(0,bn,OBJPROP_BACK,true);
     }
   else ObjectDelete(0,bn);
   // nhan TEN phien tren goc trai-tren box (giong Pine sessZoneLbl)
   string ln="NL_ZL"+IntegerToString(g_zoneN);
   if(InpSessZoneLbl)
     {
      if(ObjectFind(0,ln)<0)
        { ObjectCreate(0,ln,OBJ_TEXT,0,(datetime)tL,hi); ObjectSetString(0,ln,OBJPROP_FONT,"Arial");
          ObjectSetInteger(0,ln,OBJPROP_ANCHOR,ANCHOR_LEFT_LOWER);
          ObjectSetInteger(0,ln,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,ln,OBJPROP_HIDDEN,true); }
      ObjectMove(0,ln,0,(datetime)tL,hi);
      ObjectSetString (0,ln,OBJPROP_TEXT,sname);
      ObjectSetInteger(0,ln,OBJPROP_FONTSIZE,8);
      ObjectSetInteger(0,ln,OBJPROP_COLOR,col);
     }
   else ObjectDelete(0,ln);
   // duong Open phien + nhan "O <ten>" (giong Pine sessZoneOpen)
   string on="NL_ZO"+IntegerToString(g_zoneN), ot="NL_ZOT"+IntegerToString(g_zoneN);
   if(InpSessZoneOpen && opx>0)
     {
      if(ObjectFind(0,on)<0)
        { ObjectCreate(0,on,OBJ_TREND,0,(datetime)tL,opx,(datetime)tR,opx);
          ObjectSetInteger(0,on,OBJPROP_RAY_RIGHT,false);
          ObjectSetInteger(0,on,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,on,OBJPROP_HIDDEN,true); }
      ObjectMove(0,on,0,(datetime)tL,opx); ObjectMove(0,on,1,(datetime)tR,opx);
      ObjectSetInteger(0,on,OBJPROP_COLOR,col);
      ObjectSetInteger(0,on,OBJPROP_STYLE,STYLE_SOLID);
      ObjectSetInteger(0,on,OBJPROP_WIDTH,2);
      ObjectSetInteger(0,on,OBJPROP_BACK,true);
      if(ObjectFind(0,ot)<0)
        { ObjectCreate(0,ot,OBJ_TEXT,0,(datetime)tL,opx); ObjectSetString(0,ot,OBJPROP_FONT,"Arial");
          ObjectSetInteger(0,ot,OBJPROP_ANCHOR,ANCHOR_LEFT);
          ObjectSetInteger(0,ot,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,ot,OBJPROP_HIDDEN,true); }
      ObjectMove(0,ot,0,(datetime)tL,opx);
      ObjectSetString (0,ot,OBJPROP_TEXT,"O "+sname);
      ObjectSetInteger(0,ot,OBJPROP_FONTSIZE,8);
      ObjectSetInteger(0,ot,OBJPROP_COLOR,col);
     }
   else { ObjectDelete(0,on); ObjectDelete(0,ot); }
   g_zoneN++;
  }

void AddLvl(const double price,const string name,const long formT,const long sweptT,const int fmt)
  {
   if(price<=0) return;
   int n=g_nlv; if(n>=ArraySize(g_lv)) ArrayResize(g_lv,n+64);
   g_lv[n].price=price; g_lv[n].name=name; g_lv[n].formT=formT; g_lv[n].sweptT=sweptT; g_lv[n].fmt=fmt; g_nlv++;
  }

//==========================================================================
//   NY-time (port tu NeiroDayCandle - da verify)
//==========================================================================
datetime NthSunday(const int year,const int month,const int n)
  {
   MqlDateTime d; d.year=year; d.mon=month; d.day=1; d.hour=0; d.min=0; d.sec=0;
   datetime first=StructToTime(d); MqlDateTime f; TimeToStruct(first,f);
   int firstSun=1+((7-f.day_of_week)%7);
   d.day=firstSun+(n-1)*7; return StructToTime(d);
  }
int NyOffset(const long utc)
  {
   MqlDateTime d; TimeToStruct((datetime)utc,d);
   long dstStart=(long)NthSunday(d.year,3,2)+7*3600;
   long dstEnd  =(long)NthSunday(d.year,11,1)+6*3600;
   if(utc>=dstStart && utc<dstEnd) return -4*3600;
   return -5*3600;
  }
long FloorDay(const long e)
  { MqlDateTime d; TimeToStruct((datetime)e,d); d.hour=0; d.min=0; d.sec=0; return (long)StructToTime(d); }
// Moc 00:00 NEW YORK. Dung cho PHIEN va cho dong ho tren dashboard - gio mo
// cua London khong phu thuoc vao viec nguoi dung cat ngay o dau.
long DayStartNY(const long utc)
  {
   int off=NyOffset(utc); long mid=FloorDay(utc+off); long ds=mid-off;
   int off2=NyOffset(ds); if(off2!=off) ds=mid-off2; return ds;
  }

// Offset cua vung gio dung de CAT NGAY (khac vung gio cua phien).
int DayZoneOffset(const long utc)
  {
   if(InpDayZone==NL_DAY_BROKER) return (int)g_brokerOff;
   if(InpDayZone==NL_DAY_UTC)    return 0;
   if(InpDayZone==NL_DAY_CUSTOM) return InpDayUtcOff*3600;
   return NyOffset(utc);
  }

// Moc ngay NGUOI DUNG chon: 00:00 + InpDayHour trong vung gio da chon.
// Dat mot lan roi kiem "da toi moc hom nay chua"; chua toi thi lui mot ngay.
long DayStart(const long utc)
  {
   int  off = DayZoneOffset(utc);
   long mid = FloorDay(utc+off) + (long)InpDayHour*3600;
   long ds  = mid-off;
   if(ds>utc) ds-=86400;
   int off2 = DayZoneOffset(ds);
   if(off2!=off){ ds=mid-off2; if(ds>utc) ds-=86400; }
   return ds;
  }
long OffsetDetect()
  {
   if(InpOffsetHours!=999) return (long)InpOffsetHours*3600;
   long diff=(long)TimeTradeServer()-(long)TimeGMT();
   return (long)MathRound((double)diff/900.0)*900;
  }
// Kiem tra mot moc UTC co roi vao weekend (Thu Bay / Chu Nhat) khong.
// Dung chung cho ComputeSessions, McRun, ComputePD de skip ngay khong giao dich.
bool IsWeekendNY(const long utc)
  {
   int off=NyOffset(utc); long ny=utc+off;
   MqlDateTime d; TimeToStruct((datetime)ny,d);
   return (d.day_of_week==0 || d.day_of_week==6);
  }


//==========================================================================
//   EQ engine (port tu NeiroLiq/NeiroDayCandle: fractal + cum theo eqRel)
//==========================================================================
#define EQ_DAYSEC     86400
#define EQ_BSL        1
#define EQ_SSL        (-1)

struct EqBar { long t, tend; double o, h, l, c; };
struct EqSw  { long t; int bi; double price; int side; };
struct EqLvl { int side; double price; long atime; int tfid; };

EqBar  g_eb[];  int g_ebn=0;
EqSw   g_esw[]; int g_eswn=0;
EqLvl  g_eq[];  int g_neq=0;
double g_curUp=0, g_curDn=0;
double g_sufHi[]; double g_sufLo[];   // suffix max-high / min-low: g_suf*[i] = tren cac nen [i..end]

bool EqLoad(const ENUM_TIMEFRAMES tf,const int count,const long offset)
  {
   MqlRates rt[]; ArraySetAsSeries(rt,false);
   // start=0: LAY CA nen dang chay (giong Pine request.security lookahead_off) -> pivot
   // xac nhan NGAY khi nen ke tiep vua mo, khong phai cho no dong. Nen dang chay khong
   // bao gio TU no thanh pivot (EqSwings can i+1), no chi lam "nen ben phai" xac nhan.
   int got=CopyRates(_Symbol,tf,0,MathMax(count,260),rt);
   if(got<=3) return false;
   long per=(long)PeriodSeconds(tf);
   g_ebn=got; ArrayResize(g_eb,got);
   for(int k=0;k<got;k++)
     { long t=(long)rt[k].time-offset; g_eb[k].t=t; g_eb[k].tend=t+per;
       g_eb[k].o=rt[k].open;  g_eb[k].h=rt[k].high; g_eb[k].l=rt[k].low; g_eb[k].c=rt[k].close; }
   return true;
  }
void EqSwings()
  {
   g_eswn=0; ArrayResize(g_esw,g_ebn*2);
   for(int i=1;i<g_ebn-1;i++)
     {
      // KHOA pivot: chot dung luc XAC NHAN (nen i+1 vua mo) -> so voi GIA MO cua nen
      // i+1, KHONG so voi high/low cuoi cung cua no. Nen i+1 an lai dinh/day thi pivot
      // van con trong danh sach va chuyen XAM (da quet) thay vi bien mat khong dau vet.
      // (h[i]>h[i+1] => h[i]>o[i+1], nen tap pivot cu VAN nam tron trong tap moi.)
      if(g_eb[i].h>g_eb[i-1].h && g_eb[i].h>g_eb[i+1].o)
        { int n=g_eswn; g_esw[n].t=g_eb[i].t; g_esw[n].bi=i; g_esw[n].price=g_eb[i].h; g_esw[n].side=1;  g_eswn++; }
      if(g_eb[i].l<g_eb[i-1].l && g_eb[i].l<g_eb[i+1].o)
        { int n=g_eswn; g_esw[n].t=g_eb[i].t; g_esw[n].bi=i; g_esw[n].price=g_eb[i].l; g_esw[n].side=-1; g_eswn++; }
     }
   ArrayResize(g_esw,g_eswn);
  }
// EQ: gom cum theo GIA (giong Pine buildEq) - CHI pivot CHUA quet + trong cua so,
//   sort theo gia -> single-linkage (khoang cach gia <= thr) -> moi cum >=2 = 1 muc EQ.
//   EQH/EQL = gia TRUNG KHIT (cung 1 gia niem yet); lech <= InpEqRelUSD = rEQH/rEQL.
//   Da bi quet = KHONG con la EQ nua (pool "da quet" da bo han). EQ luon swT=0
//   (KHONG bao gio xam; bien mat khi pivot bi quet lam cum con < 2). Nhan them tfName.
void EqCollect(const long now_utc,const long dispDays,const long offset,const long nowSrv,const string tfName)
  {
   double exact = _Point*0.5;                          // trung khit = cung 1 gia niem yet
   double thr   = MathMax(InpEqRelUSD, exact);         // cum "gan bang" (rEQ)
   if(thr<=0) return;
   long cutoff = now_utc - (long)dispDays*EQ_DAYSEC;
   for(int pass=0;pass<2;pass++)
     {
      int side=(pass==0)?EQ_BSL:EQ_SSL;
      int idx[]; int c=0; ArrayResize(idx,MathMax(g_eswn,1));
      for(int i=0;i<g_eswn;i++)
        {
         if(!((side==EQ_BSL && g_esw[i].side>0)||(side==EQ_SSL && g_esw[i].side<0))) continue;
         if(g_esw[i].t < cutoff) continue;                                          // ngoai cua so
         if(EqSweptTime(g_esw[i].price,side,g_esw[i].bi,offset,nowSrv)!=0) continue; // chi CHUA quet
         idx[c++]=i;
        }
      if(c<2) continue;
      for(int a=0;a<c-1;a++)                                                        // sort theo GIA tang dan
         for(int b=0;b<c-1-a;b++)
            if(g_esw[idx[b]].price > g_esw[idx[b+1]].price){ int t=idx[b]; idx[b]=idx[b+1]; idx[b+1]=t; }
      int p=0;
      while(p<c)                                                                    // single-linkage cluster
        {
         int j=p+1;
         while(j<c){ if((g_esw[idx[j]].price - g_esw[idx[j-1]].price) > thr) break; j++; }
         if(j-p>=2)
           {
            double lp=(side==EQ_BSL)? g_esw[idx[j-1]].price : g_esw[idx[p]].price;   // EQH=cao nhat / EQL=thap nhat cum
            long org=g_esw[idx[p]].t;
            for(int k=p;k<j;k++) if(g_esw[idx[k]].t<org) org=g_esw[idx[k]].t;        // loc = pivot som nhat
            bool khit=((g_esw[idx[j-1]].price-g_esw[idx[p]].price)<=exact);          // moi gia trong cum BANG NHAU
            string enm=(khit?"":"r")+(side==EQ_BSL?"EQH ":"EQL ")+tfName;            // khong khit -> rEQH/rEQL
            AddLvl(lp, enm, org+offset, 0, 12);                                      // swT=0: EQ KHONG xam
           }
         p=j;
        }
     }
  }
// suffix max-high / min-low de check "da bi quet" O(1)
void EqSuffix()
  {
   ArrayResize(g_sufHi,g_ebn+1); ArrayResize(g_sufLo,g_ebn+1);
   g_sufHi[g_ebn]=-DBL_MAX; g_sufLo[g_ebn]=DBL_MAX;
   for(int i=g_ebn-1;i>=0;i--)
     { g_sufHi[i]=MathMax(g_eb[i].h,g_sufHi[i+1]);
       g_sufLo[i]=MathMin(g_eb[i].l,g_sufLo[i+1]); }
  }
// gio (server-time) muc EQ/pivot bi quet: nen g_eb dau tien SAU bi vuot qua; 0 = chua quet
long EqSweptTime(const double price,const int side,const int bi,const long offset,const long nowSrv)
  {
   for(int i=bi+1;i<g_ebn;i++)
     { if(side==EQ_BSL){ if(g_eb[i].h>=price) return g_eb[i].t+offset; }
       else            { if(g_eb[i].l<=price) return g_eb[i].t+offset; } }
   if(side==EQ_BSL && g_curUp>=price) return nowSrv;   // quet boi gia realtime
   if(side==EQ_SSL && g_curDn<=price) return nowSrv;
   return 0;
  }
// MOI dinh/day (pivot): them HET voi sweptT (chua quet -> hien; da quet -> feed maxSw); tra ve so pivot
int EqAllPivots(const long now_utc,const long dispDays,const long offset,const int fmt,const string tfName,const long nowSrv)
  {
   long minKeep=now_utc-(long)dispDays*EQ_DAYSEC; int cnt=0;
   for(int i=0;i<g_eswn;i++)
     {
      int    bi   =g_esw[i].bi;
      double price=g_esw[i].price;
      long   formedGmt=g_eb[bi].tend;
      if(formedGmt<minKeep) continue;                       // ngoai cua so 10 ngay
      if(g_esw[i].side>0)                                   // dinh (BSL)
        { long swT=EqSweptTime(price,EQ_BSL,bi,offset,nowSrv);
          AddLvl(price, tfName+"-H", g_esw[i].t+offset, swT, fmt); cnt++; }
      else                                                  // day (SSL)
        { long swT=EqSweptTime(price,EQ_SSL,bi,offset,nowSrv);
          AddLvl(price, tfName+"-L", g_esw[i].t+offset, swT, fmt); cnt++; }
     }
   return cnt;
  }
void ComputeEQ(const long offset,const long nowSrv)
  {
   long now_utc=(long)TimeGMT();
   long days=(long)MathMax(InpDaysBack,1);
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID); if(bid<=0) bid=iClose(_Symbol,PERIOD_CURRENT,0);
   double h0=iHigh(_Symbol,PERIOD_CURRENT,0), l0=iLow(_Symbol,PERIOD_CURRENT,0);
   g_curUp=(h0>0)?MathMax(bid,h0):bid; g_curDn=(l0>0)?MathMin(bid,l0):bid;
   bool needH1 =(g_onEq||g_onPvH1);
   bool needM15=(g_onEq||g_onPvM15);
   if(needH1 && EqLoad(PERIOD_H1, InpEqH1Bars, offset))
     { EqSwings(); EqSuffix();
       if(g_onEq) EqCollect(now_utc,days,offset,nowSrv,"H1");
       if(g_onPvH1) EqAllPivots(now_utc,days,offset,13,"H1",nowSrv); }
   if(needM15 && EqLoad(PERIOD_M15,InpEqM15Bars,offset))
     { EqSwings(); EqSuffix();
       if(g_onEq) EqCollect(now_utc,days,offset,nowSrv,"M15");
       if(g_onPvM15) EqAllPivots(now_utc,days,offset,14,"M15",nowSrv); }
  }

//==========================================================================
//   Scan chart-TF: sweep-time (nen dau tien SAU fromBar vuot qua muc)
//==========================================================================
long SweptTime(const double price,const bool isHigh,const int fromBar)
  {
   for(int b=fromBar-1;b>=0;b--)   // b=fromBar-1 = som nhat sau close ; b=0 = now
     {
      double h=iHigh(_Symbol,PERIOD_CURRENT,b), l=iLow(_Symbol,PERIOD_CURRENT,b);
      if(isHigh ? (h>price) : (l<price)) return (long)iTime(_Symbol,PERIOD_CURRENT,b);
     }
   return 0;
  }

//==========================================================================
//   Sessions: live occurrence (occ0) + earlier ones (p-prefixed) H/L + formT + sweptT
//==========================================================================
void ComputeSessions(const long offset,const long nowSrv)
  {
   int    oHH[5]; int cHH[5]; string nm[5]; int fmtC[5]; int fmtP[5];
   color  zB[5]; color zF[5];
   oHH[0]=InpTokyoOpen;  cHH[0]=InpTokyoClose;  nm[0]="Tokyo";    fmtC[0]=0; fmtP[0]=1;
   oHH[1]=InpLondonOpen; cHH[1]=InpLondonClose; nm[1]="London";   fmtC[1]=2; fmtP[1]=3;
   oHH[2]=InpNyAmOpen;   cHH[2]=InpNyAmClose;   nm[2]="NY AM";    fmtC[2]=4; fmtP[2]=5;
   oHH[3]=InpLunchOpen;  cHH[3]=InpLunchClose;  nm[3]="NY Lunch"; fmtC[3]=6; fmtP[3]=7;
   oHH[4]=InpNyPmOpen;   cHH[4]=InpNyPmClose;   nm[4]="NY PM";    fmtC[4]=8; fmtP[4]=9;
   zB[0]=InpZTokB; zF[0]=InpZTokF;
   zB[1]=InpZLonB; zF[1]=InpZLonF;
   zB[2]=InpZAmB;  zF[2]=InpZAmF;
   zB[3]=InpZLuB;  zF[3]=InpZLuF;
   zB[4]=InpZPmB;  zF[4]=InpZPmF;

   long todayMid=DayStartNY(nowSrv-offset);
   long minMid  =todayMid-(long)MathMax(InpDaysBack,1)*86400;   // cua so 10 ngay
   for(int s=0;s<5;s++)
     {
      long prevMid=todayMid; int found=0;
      for(int d=0; d<InpDaysBack+6; d++)
        {
         long dMid=(d==0)?prevMid:DayStartNY(prevMid-3600); prevMid=dMid;
         if(dMid<minMid) break;                          // ngoai cua so 10 ngay -> dung
         // ICT: skip weekend - phien Chu Nhat / Thu Bay khong phai phien giao dich hop le
         if(IsWeekendNY(dMid)) continue;
         long oUtc=dMid+(long)(oHH[s]/100)*3600+(long)(oHH[s]%100)*60;
         long cUtc=dMid+(long)(cHH[s]/100)*3600+(long)(cHH[s]%100)*60; if(cUtc<=oUtc) cUtc+=86400;
         long oSrv=oUtc+offset, cSrv=cUtc+offset;
         if(oSrv>nowSrv) continue;                       // chua bat dau
         long cClamp=(cSrv<nowSrv)?cSrv:nowSrv;
         int bO=BarShiftOpen(oSrv);
         int bC=iBarShift(_Symbol,PERIOD_CURRENT,(datetime)cClamp,false);
         if(bO<0||bC<0){ found++; continue; }
         double hi=-DBL_MAX,lo=DBL_MAX; long tHi=0,tLo=0;
         for(int b=bC;b<=bO;b++)
           { double h=iHigh(_Symbol,PERIOD_CURRENT,b),l=iLow(_Symbol,PERIOD_CURRENT,b);
             if(h>hi){hi=h;tHi=(long)iTime(_Symbol,PERIOD_CURRENT,b);}
             if(l<lo){lo=l;tLo=(long)iTime(_Symbol,PERIOD_CURRENT,b);} }
         if(hi<=-DBL_MAX){ found++; continue; }
         if(g_onSessArr[s] && (found==0 || g_onPrevSess))
           { int fmt=(found==0)?fmtC[s]:fmtP[s];
             string base=(found==0)?nm[s]:("p"+nm[s]);
             AddLvl(hi, base+"-H", tHi, SweptTime(hi,true,bC),  fmt);
             AddLvl(lo, base+"-L", tLo, SweptTime(lo,false,bC), fmt); }
         if(g_sessZoneOn && g_onZoneArr[s] && found<InpSessZoneDays)
             DrawZone((long)iTime(_Symbol,PERIOD_CURRENT,bO),(long)iTime(_Symbol,PERIOD_CURRENT,bC),hi,lo,
                      zB[s],zF[s],(found==0)?nm[s]:("p"+nm[s]),iOpen(_Symbol,PERIOD_CURRENT,bO));
         found++;
        }
     }
  }

//==========================================================================
//   PDH/PDL (ngay NY hom qua) + Day-High/Low (hom nay)
//==========================================================================
void ComputePD(const long offset,const long nowSrv)
  {
   long todayMid=DayStart(nowSrv-offset);
   // ICT: "today" KHONG duoc la Chu Nhat hay Thu Bay. Neu todayMid roi vao weekend
   // (vd chi chay luc thi truong vua mo toi Chu Nhat), lui ve ngay giao dich gan nhat
   // (Thu Sau) de lam "today", va "yesterday" = Thu Nam. Nhu vay PDH/PDL luon la ngay
   // giao dich truoc do, khong bao gio chua data Chu Nhat.
   while(true)
     {
      MqlDateTime dt; TimeToStruct((datetime)(todayMid + 12*3600 + DayZoneOffset(todayMid + 12*3600)), dt);
      if(dt.day_of_week == 0 || dt.day_of_week == 6) todayMid = DayStart(todayMid - 3600);
      else break;
     }
   long yestMid =DayStart(todayMid-3600);
   while(true)
     {
      MqlDateTime dt; TimeToStruct((datetime)(yestMid + 12*3600 + DayZoneOffset(yestMid + 12*3600)), dt);
      if(dt.day_of_week == 0 || dt.day_of_week == 6) yestMid = DayStart(yestMid - 3600);
      else break;
     }
   long bbMid   =DayStart(yestMid-3600);      // ngay lui 2 (truoc hom qua)
   while(true)
     {
      MqlDateTime dt; TimeToStruct((datetime)(bbMid + 12*3600 + DayZoneOffset(bbMid + 12*3600)), dt);
      if(dt.day_of_week == 0 || dt.day_of_week == 6) bbMid = DayStart(bbMid - 3600);
      else break;
     }
   // Can tren cua khoang PDH/PDL: ngay TIEP THEO sau yestMid (tuc todayMid), nhung
   // khong vuot qua nowSrv. Tuong tu cho BPDH/BPDL (can tren = yestMid).
   long pdEnd = todayMid;       // [yestMid, todayMid)  - chi 1 ngay giao dich
   long bpdEnd= yestMid;        // [bbMid,   yestMid)   - chi 1 ngay giao dich
   long tSrv=todayMid+offset;
   // hom qua [yestMid, pdEnd) -> PDH/PDL
   int bYO=BarShiftOpen(yestMid+offset);
   int bYC=iBarShift(_Symbol,PERIOD_CURRENT,(datetime)(pdEnd+offset-1),false);
   if(g_onPd && bYO>=0 && bYC>=0 && bYC<=bYO)
     {
      double hi=-DBL_MAX,lo=DBL_MAX; long tHi=0,tLo=0;
      for(int b=bYC;b<=bYO;b++)
        { double h=iHigh(_Symbol,PERIOD_CURRENT,b),l=iLow(_Symbol,PERIOD_CURRENT,b);
          if(h>hi){hi=h;tHi=(long)iTime(_Symbol,PERIOD_CURRENT,b);}
          if(l<lo){lo=l;tLo=(long)iTime(_Symbol,PERIOD_CURRENT,b);} }
      if(hi>-DBL_MAX)
        {
         AddLvl(hi,"PDH",tHi,SweptTime(hi,true,bYC),10);
         AddLvl(lo,"PDL",tLo,SweptTime(lo,false,bYC),10);
        }
     }
   // lui 2 ngay [bbMid, bpdEnd) -> BPDH/BPDL
   int bBO=BarShiftOpen(bbMid+offset);
   int bBC=iBarShift(_Symbol,PERIOD_CURRENT,(datetime)(bpdEnd+offset-1),false);
   if(g_onBpd && bBO>=0 && bBC>=0 && bBC<=bBO)
     {
      double hi=-DBL_MAX,lo=DBL_MAX; long tHi=0,tLo=0;
      for(int b=bBC;b<=bBO;b++)
        { double h=iHigh(_Symbol,PERIOD_CURRENT,b),l=iLow(_Symbol,PERIOD_CURRENT,b);
          if(h>hi){hi=h;tHi=(long)iTime(_Symbol,PERIOD_CURRENT,b);}
          if(l<lo){lo=l;tLo=(long)iTime(_Symbol,PERIOD_CURRENT,b);} }
      if(hi>-DBL_MAX)
        {
         AddLvl(hi,"BPDH",tHi,SweptTime(hi,true,bBC),15);
         AddLvl(lo,"BPDL",tLo,SweptTime(lo,false,bBC),15);
        }
     }
   // hom nay: dung todayMid da skip weekend lam moc. Nhung ban THAN khoang HOD/LOD
   // phai chay tu moc THUC cua server (ke ca nen Chu Nhat) den now, nen dung moc
   // server goc (DayStart tu nowSrv goc) thay vi todayMid da skip.
   long todayReal=DayStart(nowSrv-offset);
   long tSrvReal =todayReal+offset;
   int bTO=BarShiftOpen(tSrvReal);
   if(bTO>=0){ g_mnoPrice=iOpen(_Symbol,PERIOD_CURRENT,bTO); g_mnoT=(long)iTime(_Symbol,PERIOD_CURRENT,bTO); }
   else       g_mnoPrice=0;
   if(g_onDay && bTO>=0)
     {
      double hi=-DBL_MAX,lo=DBL_MAX; long tHi=0,tLo=0;
      for(int b=0;b<=bTO;b++)
        { double h=iHigh(_Symbol,PERIOD_CURRENT,b),l=iLow(_Symbol,PERIOD_CURRENT,b);
          if(h>hi){hi=h;tHi=(long)iTime(_Symbol,PERIOD_CURRENT,b);}
          if(l<lo){lo=l;tLo=(long)iTime(_Symbol,PERIOD_CURRENT,b);} }
      if(hi>-DBL_MAX)
        {
         AddLvl(hi,"HOD",tHi,0,11);   // HOD/LOD (cuc tri ngay) khong bao gio bi quet
         AddLvl(lo,"LOD",tLo,0,11);
        }
     }
  }

//==========================================================================
//   Tuan: PWH/PWL (tuan truoc) + HOW/LOW (tuan nay) - theo nen W1 broker
//==========================================================================
void ComputeWeek(const long offset,const long nowSrv)
  {
   long curWT =(long)iTime(_Symbol,PERIOD_W1,0);
   long prevWT=(long)iTime(_Symbol,PERIOD_W1,1);
   double howh=iHigh(_Symbol,PERIOD_W1,0), lowl=iLow(_Symbol,PERIOD_W1,0);
   double pwh =iHigh(_Symbol,PERIOD_W1,1), pwl =iLow(_Symbol,PERIOD_W1,1);
   int bWk=BarShiftOpen(curWT);
   if(bWk<0) bWk=Bars(_Symbol,PERIOD_CURRENT)-1;
   if(g_onPw && pwh>0 && prevWT>0)
     {
      long swH=SweptTime(pwh,true, bWk);
      long swL=SweptTime(pwl,false,bWk);
      // Da quet TRUOC 00:00 NY hom nay -> AN HAN (khong AddLvl) => mat ca duong, nhan,
      // suat vach xam nhom Tuan va ca khi bat InpShowSwHist. Quet trong NGAY thi van hien.
      long tSrvToday=DayStart(nowSrv-offset)+offset;
      if(swH==0 || swH>=tSrvToday) AddLvl(pwh,"PWH",prevWT,swH,16);
      if(swL==0 || swL>=tSrvToday) AddLvl(pwl,"PWL",prevWT,swL,16);
     }
   if(g_onWk && howh>0 && curWT>0)
     {
      AddLvl(howh,"HOW",curWT,0,17);   // HOW/LOW (cuc tri tuan nay) khong bi quet
      AddLvl(lowl,"LOW",curWT,0,17);
     }
  }

//==========================================================================
//   ATH = gia cao nhat lich su (khung Thang MN1) - luon nam tren cung
//==========================================================================
void ComputeATH()
  {
   g_athPrice=0; g_athT=0;
   if(!g_onAth) return;
   int mnBars=Bars(_Symbol,PERIOD_MN1);
   if(mnBars<=0) return;
   int hidx=iHighest(_Symbol,PERIOD_MN1,MODE_HIGH,mnBars,0);
   if(hidx<0) return;
   g_athPrice=iHigh(_Symbol,PERIOD_MN1,hidx);
   g_athT    =(long)iTime(_Symbol,PERIOD_MN1,hidx);
  }

//==========================================================================
//   GOP cum: uu tien type (nho=cao) + phia (dinh/day)
//==========================================================================
// Thang bac khop 1:1 voi f_prio() ben Pine. So tuyet doi doi (them ATH o dau)
// nhung THU TU TUONG DOI khong doi -> ket qua gop cum y het truoc.
int Prio(const int fmt)
  { if(fmt==19) return 0;                // ATH
    if(fmt==16) return 1;                // PW (PWH/PWL tuan truoc)
    if(fmt==10) return 2;                // PD (PDH/PDL hom qua)
    if(fmt==15) return 3;                // BPD (BPDH/BPDL lui 2)
    if(fmt==17) return 4;                // Week (HOW/LOW tuan nay)
    if(fmt==11) return 5;                // Day (HOD/LOD hom nay)
    if(fmt>=0 && fmt<=9) return 6;       // Session (Tokyo/London/NY x5, cur+prev)
    if(fmt==18) return 6;                // MNO - cung tier session, giong Pine
    if(fmt==12) return 7;                // EQ (EQH/EQL)
    if(fmt==13) return 8;                // H1
    return 9; }                          // M15
bool IsHigh(const string nm)
  { return (StringFind(nm,"-H")>=0 || StringFind(nm,"High")>=0 || StringFind(nm,"EQH")>=0
            || nm=="PDH" || nm=="BPDH" || nm=="PWH" || nm=="HOD" || nm=="HOW" || nm=="ATH"); }
// timeframe/nhom cua tung muc (theo fmt): moi TF giu 1 muc xam RIENG
//   0=Phien(0..7) 1=Ngay(PD8/BPD13/HOD-LOD9) 2=Tuan(PW14/HOW-LOW15) 3=H1(pivot11) 4=M15(12) 5=EQ(10)
int TfGroup(const int fmt)
  { if(fmt==18)                   return 1;   // MNO - khong bao gio swept, nhom cho co
    if(fmt==19)                   return 2;   // ATH - nt
    if(fmt>=0 && fmt<=9)          return 0;
    if(fmt==10||fmt==15||fmt==11) return 1;
    if(fmt==16||fmt==17)          return 2;
    if(fmt==13)                   return 3;
    if(fmt==12)                   return 5;   // EQ = loai rieng
    return 4; }                                // 14 = M15

// suat vach xam: moi TF 2 suat rieng (0=phia DINH, 1=phia DAY)
#define SW_SLOT 12
int SwSlot(const Lvl &v)
  { return TfGroup(v.fmt)*2 + (IsHigh(v.name)?0:1); }


//==========================================================================
//   ICT MACROS
//   Port tu "GTrader-ICT All In One - Comumnity Version"
//   (tradingview/vendor/Gtrader-ICT.txt, CHI DOC).
//
//   Moi macro = mot cua so 20 phut. Vach TREN chay theo cuc dai cua cua so,
//   vach DUOI theo cuc tieu, cong mot nhan o giua.
//
//   Cho LECH ban goc, va ly do:
//   1. Ban Pine phai chong nhan doi tren nen realtime (Pine khong rollback
//      array/object). MT5 KHONG dinh benh do: moi luot Draw() quet lai lich su
//      va ve de len chinh object cu, nen o day khong co doan khoa nao ca.
//   2. Nhan cua ban goc la hai dong "MACRO\\n09:50-10:10". OBJ_TEXT cua MT5
//      khong xuong dong duoc nen gop thanh mot dong.
//   3. Mui gio: ban goc cho chon America/New_York hoac mot trong 27 muc GMT.
//      O day mot o so nguyen theo dung le da dung cho Broker offset:
//      999 = New York tu doi DST, so khac = UTC co dinh.
//
//   LUU Y: day thuan tuy la lop HIEN THI - no khong sinh tin hieu nao.
//==========================================================================
int g_mcN=0, g_mcDrawn=0;
int g_fut=1;      // so nen ve duoc ben PHAI nen cuoi (vung SHIFT); set trong Draw()

int McZoneOffset(const long utc)
  { if(InpMcUtcOff==999) return NyOffset(utc); return InpMcUtcOff*3600; }

// 00:00 cua ngay trong mui gio doc macro
long McDayStart(const long utc)
  {
   int off=McZoneOffset(utc); long mid=FloorDay(utc+off); long ds=mid-off;
   int off2=McZoneOffset(ds); if(off2!=off) ds=mid-off2;
   return ds;
  }

void McLine(const string nm,const long t1,const long t2,const double px)
  {
   if(ObjectFind(0,nm)<0)
     { ObjectCreate(0,nm,OBJ_TREND,0,(datetime)t1,px,(datetime)t2,px);
       ObjectSetInteger(0,nm,OBJPROP_RAY_RIGHT,false); ObjectSetInteger(0,nm,OBJPROP_RAY_LEFT,false);
       ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true); }
   ObjectMove(0,nm,0,(datetime)t1,px); ObjectMove(0,nm,1,(datetime)t2,px);
   ObjectSetInteger(0,nm,OBJPROP_RAY_RIGHT,false);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,InpMcCol);
   ObjectSetInteger(0,nm,OBJPROP_STYLE,STYLE_SOLID);
   ObjectSetInteger(0,nm,OBJPROP_WIDTH,2);
  }

void McRun(const bool use,const int hhS,const int hhE,const bool useTop,const bool useBot,
           const long offset,const long nowSrv,const long P)
  {
   if(!use) return;
   long todayMid=McDayStart(nowSrv-offset);
   long prevMid=todayMid; int found=0;
   long rightMax=nowSrv+(long)g_fut*P;      // xa hon the la MT5 khong ve ra duoc
   for(int d=0; d<InpMcKeep+10 && found<InpMcKeep; d++)
     {
      long dMid=(d==0)?prevMid:McDayStart(prevMid-3600); prevMid=dMid;
      // ICT: skip weekend - macro Chu Nhat / Thu Bay khong hop le
      if(IsWeekendNY(dMid)) continue;
      long oUtc=dMid+(long)(hhS/100)*3600+(long)(hhS%100)*60;
      long cUtc=dMid+(long)(hhE/100)*3600+(long)(hhE%100)*60; if(cUtc<=oUtc) cUtc+=86400;
      long oSrv=oUtc+offset, cSrv=cUtc+offset;
      if(oSrv>nowSrv) continue;                       // cua so chua toi
      long cClamp=(cSrv<nowSrv)?cSrv:nowSrv;
      int bO=BarShiftOpen(oSrv);
      int bC=iBarShift(_Symbol,PERIOD_CURRENT,(datetime)cClamp,false);
      if(bO<0||bC<0||bC>bO) continue;
      double hi=-DBL_MAX,lo=DBL_MAX;
      for(int b=bC;b<=bO;b++)
        { double h=iHigh(_Symbol,PERIOD_CURRENT,b),l=iLow(_Symbol,PERIOD_CURRENT,b);
          if(h>hi) hi=h; if(l<lo) lo=l; }
      if(hi<=-DBL_MAX) continue;

      long xL=(long)iTime(_Symbol,PERIOD_CURRENT,bO);
      long xR=cSrv; if(xR>rightMax) xR=rightMax; if(xR<xL) xR=xL;
      string is=IntegerToString(g_mcN);
      string hn="NL_MC"+is+"H", ln="NL_MC"+is+"L", tn="NL_MC"+is+"T";
      if(useTop) McLine(hn,xL,xR,hi+InpMcDist); else ObjectDelete(0,hn);
      if(useBot) McLine(ln,xL,xR,lo-InpMcDist); else ObjectDelete(0,ln);
      if(ObjectFind(0,tn)<0)
        { ObjectCreate(0,tn,OBJ_TEXT,0,(datetime)((xL+xR)/2),hi+InpMcDist);
          ObjectSetString (0,tn,OBJPROP_FONT,"Arial");
          ObjectSetInteger(0,tn,OBJPROP_ANCHOR,ANCHOR_LOWER);
          ObjectSetInteger(0,tn,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,tn,OBJPROP_HIDDEN,true); }
      ObjectMove(0,tn,0,(datetime)((xL+xR)/2),hi+InpMcDist);
      ObjectSetString (0,tn,OBJPROP_TEXT,StringFormat("MACRO %02d:%02d-%02d:%02d",
                       hhS/100,hhS%100,hhE/100,hhE%100));
      ObjectSetInteger(0,tn,OBJPROP_FONTSIZE,MathMax(5,InpTextSize));
      ObjectSetInteger(0,tn,OBJPROP_COLOR,InpMcCol);
      g_mcN++; found++;
     }
  }

void McDraw(const long offset,const long nowSrv,const long P)
  {
   g_mcN=0;
   // Macro dai 20 phut nen chi co nghia o khung nho - ban goc chan tu M3 tro xuong.
   if(g_onMacro && PeriodSeconds(PERIOD_CURRENT)<=InpMcTfLim*60)
     {
      McRun(InpMc1On,InpMc1S,InpMc1E,InpMc1T,InpMc1B,offset,nowSrv,P);
      McRun(InpMc2On,InpMc2S,InpMc2E,InpMc2T,InpMc2B,offset,nowSrv,P);
      McRun(InpMc3On,InpMc3S,InpMc3E,InpMc3T,InpMc3B,offset,nowSrv,P);
      McRun(InpMc4On,InpMc4S,InpMc4E,InpMc4T,InpMc4B,offset,nowSrv,P);
      McRun(InpMc5On,InpMc5S,InpMc5E,InpMc5T,InpMc5B,offset,nowSrv,P);
     }
   for(int i=g_mcN;i<g_mcDrawn;i++)
     { string is=IntegerToString(i);
       ObjectDelete(0,"NL_MC"+is+"H"); ObjectDelete(0,"NL_MC"+is+"L"); ObjectDelete(0,"NL_MC"+is+"T"); }
   g_mcDrawn=g_mcN;
  }

//==========================================================================
//   PROJECTION CANDLES  (W -> D -> H4 -> H1, ve o le phai)
//   Cau tao mot cay bam theo nhom "5.HTF Candles" cua GTrader-ICT: THAN
//   (hinh chu nhat) / VIEN (mau rieng) / RAU (mau rieng), cong nhan ten dat
//   tren hoac duoi, dem nguoc, moc ngay, nhan gia, va vach trace keo tu nen
//   song ve tung muc O/H/L/C.
//
//   RANG BUOC RIENG CUA MT5: object chi ve duoc trong vung SHIFT ben phai nen
//   cuoi. Zoom cang gan thi vung do cang it nen. Ca cum se bi BOP LAI cho vua
//   thay vi bien mat khong dau vet - dung cach cot nhan da lam tu ban 1.0.
//==========================================================================
int g_dcBN=0, g_dcBDrawn=0;     // than nen (moi cay 2 object: nen + vien)
int g_dcLN=0, g_dcLDrawn=0;     // rau + vach trace
int g_dcTN=0, g_dcTDrawn=0;     // nhan

#define DC_STAMP_OFF 0
#define DC_STAMP_DATE 1          // dd/MM   - cum tuan
#define DC_STAMP_DOW  2          // Mon/Tue - cum ngay
#define DC_STAMP_TIME 3          // HH:mm   - cum H4 / H1

// Dem nguoc cua cay dang chay -> "1d 4h" / "3h 12m" / "07m 40s". Het gio = rong.
string DcCountdown(const long secLeft)
  {
   if(secLeft<=0) return "";
   long dd=secLeft/86400, hh=(secLeft%86400)/3600, mm=(secLeft%3600)/60, s2=secLeft%60;
   if(dd>0) return StringFormat("%dd %dh",(int)dd,(int)hh);
   if(hh>0) return StringFormat("%dh %dm",(int)hh,(int)mm);
   return StringFormat("%dm %ds",(int)mm,(int)s2);
  }

// Nhan ngay/gio duoi cay. CA BA kieu deu doc theo gio NEW YORK - owner chot 22-08.
string DcStamp(const long tSrv,const int kind,const long offset)
  {
   if(kind==DC_STAMP_OFF || tSrv<=0) return "";
   long utc=tSrv-offset; long ny=utc+NyOffset(utc);
   MqlDateTime d; TimeToStruct((datetime)ny,d);
   if(kind==DC_STAMP_DATE) return StringFormat("%02d/%02d",d.day,d.mon);
   if(kind==DC_STAMP_TIME) return StringFormat("%02d:%02d",d.hour,d.min);
   string dow[7]={"Sun","Mon","Tue","Wed","Thu","Fri","Sat"};
   return dow[d.day_of_week%7];
  }

void DcText(const long t,const double px,const string txt,const ENUM_ANCHOR_POINT anc)
  {
   if(txt=="") return;
   string nm="NL_DCT"+IntegerToString(g_dcTN);
   if(ObjectFind(0,nm)<0)
     { ObjectCreate(0,nm,OBJ_TEXT,0,(datetime)t,px); ObjectSetString(0,nm,OBJPROP_FONT,"Arial");
       ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true); }
   ObjectMove(0,nm,0,(datetime)t,px);
   ObjectSetInteger(0,nm,OBJPROP_ANCHOR,anc);
   ObjectSetString (0,nm,OBJPROP_TEXT,txt);
   ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,MathMax(5,InpTextSize));
   ObjectSetInteger(0,nm,OBJPROP_COLOR,InpDcText);
   g_dcTN++;
  }

void DcLine(const long t1,const double p1,const long t2,const double p2,
            const color col,const ENUM_LINE_STYLE sty,const int wid)
  {
   string nm="NL_DCL"+IntegerToString(g_dcLN);
   if(ObjectFind(0,nm)<0)
     { ObjectCreate(0,nm,OBJ_TREND,0,(datetime)t1,p1,(datetime)t2,p2);
       ObjectSetInteger(0,nm,OBJPROP_RAY_RIGHT,false); ObjectSetInteger(0,nm,OBJPROP_RAY_LEFT,false);
       ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true); }
   ObjectMove(0,nm,0,(datetime)t1,p1); ObjectMove(0,nm,1,(datetime)t2,p2);
   ObjectSetInteger(0,nm,OBJPROP_RAY_RIGHT,false);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,col);
   ObjectSetInteger(0,nm,OBJPROP_STYLE,sty);
   ObjectSetInteger(0,nm,OBJPROP_WIDTH,wid);
   g_dcLN++;
  }

// Than nen: HAI hinh chu nhat chong khit, cung ly do nhu box vung phien -
// mot OBJ_RECTANGLE cua MT5 chi mang duoc mot mau.
void DcBody(const long tL,const long tR,const double hi,const double lo,
            const color fillCol,const color brdCol)
  {
   string is=IntegerToString(g_dcBN);
   string fn="NL_DCB"+is, bn="NL_DCBR"+is;
   if(ObjectFind(0,fn)<0)
     { ObjectCreate(0,fn,OBJ_RECTANGLE,0,(datetime)tL,hi,(datetime)tR,lo);
       ObjectSetInteger(0,fn,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,fn,OBJPROP_HIDDEN,true); }
   ObjectMove(0,fn,0,(datetime)tL,hi); ObjectMove(0,fn,1,(datetime)tR,lo);
   ObjectSetInteger(0,fn,OBJPROP_COLOR,fillCol);
   ObjectSetInteger(0,fn,OBJPROP_STYLE,STYLE_SOLID);
   ObjectSetInteger(0,fn,OBJPROP_WIDTH,1);
   ObjectSetInteger(0,fn,OBJPROP_FILL,true);
   ObjectSetInteger(0,fn,OBJPROP_BACK,true);
   if(ObjectFind(0,bn)<0)
     { ObjectCreate(0,bn,OBJ_RECTANGLE,0,(datetime)tL,hi,(datetime)tR,lo);
       ObjectSetInteger(0,bn,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,bn,OBJPROP_HIDDEN,true); }
   ObjectMove(0,bn,0,(datetime)tL,hi); ObjectMove(0,bn,1,(datetime)tR,lo);
   ObjectSetInteger(0,bn,OBJPROP_COLOR,brdCol);
   ObjectSetInteger(0,bn,OBJPROP_STYLE,STYLE_SOLID);
   ObjectSetInteger(0,bn,OBJPROP_WIDTH,1);
   ObjectSetInteger(0,bn,OBJPROP_FILL,false);
   ObjectSetInteger(0,bn,OBJPROP_BACK,true);
   g_dcBN++;
  }

// Ve MOT cum; tra ve cot X ngay sau cum de cum ke tiep noi vao.
// Mang vao theo thu tu CU -> MOI, cay cuoi = cay dang chay.
int DcCluster(const double &co[],const double &ch[],const double &cl[],const double &cc[],const long &ct[],
              const int m,const int x0,const int halfW,const string tag,const long secLeft,const int stampKind,
              const long nowSrv,const long P,const long offset,
              const int gapB,const int grpB)
  {
   if(m<=0) return x0;
   double clHi=-DBL_MAX, clLo=DBL_MAX;
   for(int j=0;j<m;j++){ if(ch[j]>clHi) clHi=ch[j]; if(cl[j]<clLo) clLo=cl[j]; }
   for(int i=0;i<m;i++)
     {
      int  xc =x0+i*gapB;
      bool up =(cc[i]>=co[i]);
      bool run=(i==m-1);                                  // cay cuoi cum = cay dang chay
      long tC =nowSrv+(long)xc*P;
      long tL =nowSrv+(long)(xc-halfW)*P;
      long tR =nowSrv+(long)(xc+halfW)*P;
      DcBody(tL,tR,MathMax(co[i],cc[i]),MathMin(co[i],cc[i]),
             up?InpDcBull:InpDcBear, up?InpDcBullBd:InpDcBearBd);
      DcLine(tC,ch[i],tC,cl[i], up?InpDcBullWk:InpDcBearWk, STYLE_SOLID, MathMax(1,InpLineWidth));

      // Chi ghi TEN cum. Cay cuoi = cay dang chay -> de tran; cay cu lui dan: H1-1, H1-2...
      string txt = run ? tag : tag+"-"+IntegerToString(m-1-i);
      double yTop=(InpDcLblAlign==NL_DCA_ALIGN)?clHi:ch[i];
      double yBot=(InpDcLblAlign==NL_DCA_ALIGN)?clLo:cl[i];
      if(InpDcLblPos==NL_DCL_TOP || InpDcLblPos==NL_DCL_BOTH)
        {
         // OBJ_TEXT khong xuong dong duoc: dem nguoc thanh mot nhan RIENG dat cao hon.
         DcText(tC,yTop,txt,ANCHOR_LOWER);
         if(run && InpDcTimer)
           { string cd=DcCountdown(secLeft);
             if(cd!="") DcText(tC+(long)halfW*P,yTop,cd,ANCHOR_LEFT_LOWER); }
        }
      string bTxt="";
      if(InpDcLblPos==NL_DCL_BOT || InpDcLblPos==NL_DCL_BOTH) bTxt=txt;
      if(InpDcStamp)
        { string st=DcStamp(ct[i],stampKind,offset);
          if(st!="") bTxt=(bTxt=="")?st:(bTxt+" "+st); }
      if(bTxt!="") DcText(tC,yBot,bTxt,ANCHOR_UPPER);
      if(InpDcPxLbl) DcText(tR,cc[i],DoubleToString(cc[i],_Digits),ANCHOR_LEFT);

      // Trace: keo tu nen SONG sang tan cay, chi cho cay dang chay.
      if(InpDcTrace && run)
        {
         int lw=MathMax(1,InpLineWidth);
         if(InpDcTrO) DcLine(nowSrv,co[i],tC,co[i],InpDcTrOC,InpDcTrOS,lw);
         if(InpDcTrC) DcLine(nowSrv,cc[i],tC,cc[i],InpDcTrCC,InpDcTrCS,lw);
         if(InpDcTrH) DcLine(nowSrv,ch[i],tC,ch[i],InpDcTrHC,InpDcTrHS,lw);
         if(InpDcTrL) DcLine(nowSrv,cl[i],tC,cl[i],InpDcTrLC,InpDcTrLS,lw);
        }
     }
   return x0+m*gapB+grpB;
  }

// Nap cum tu MOT khung co san cua terminal (W1 / H4 / H1). Cay na thi bo qua.
int DcLoadTf(const ENUM_TIMEFRAMES tf,const int num,
             double &co[],double &ch[],double &cl[],double &cc[],long &ct[])
  {
   int m=0;
   for(int k=num-1;k>=0;k--)
     {
      double o=iOpen(_Symbol,tf,k);
      if(o<=0) continue;
      co[m]=o; ch[m]=iHigh(_Symbol,tf,k); cl[m]=iLow(_Symbol,tf,k); cc[m]=iClose(_Symbol,tf,k);
      ct[m]=(long)iTime(_Symbol,tf,k); m++;
     }
   return m;
  }

// Cum nen-NGAY gop TAY tu nen chart, theo dung moc "Day boundary" o nhom General -
// nen no luon khop voi PDH/PDL va duong Midnight Open. Chi co nghia tu H1 tro xuong.
int DcLoadDay(const int num,const long offset,const long nowSrv,
              double &co[],double &ch[],double &cl[],double &cc[],long &ct[])
  {
   int m=0;
   long mids[]; ArrayResize(mids,num+1);
   long cur=DayStart(nowSrv-offset);
   for(int k=0;k<=num;k++){ mids[k]=cur; cur=DayStart(cur-3600); }   // mids[0] = hom nay
   for(int k=num-1;k>=0;k--)
     {
      long oSrv=mids[k]+offset;
      long eSrv=(k==0)? nowSrv : (mids[k-1]+offset-1);
      int bO=BarShiftOpen(oSrv);
      int bC=iBarShift(_Symbol,PERIOD_CURRENT,(datetime)eSrv,false);
      if(bO<0||bC<0||bC>bO) continue;
      double hi=-DBL_MAX,lo=DBL_MAX;
      for(int b=bC;b<=bO;b++)
        { double h=iHigh(_Symbol,PERIOD_CURRENT,b),l=iLow(_Symbol,PERIOD_CURRENT,b);
          if(h>hi) hi=h; if(l<lo) lo=l; }
      if(hi<=-DBL_MAX) continue;
      co[m]=iOpen(_Symbol,PERIOD_CURRENT,bO); ch[m]=hi; cl[m]=lo;
      cc[m]=iClose(_Symbol,PERIOD_CURRENT,bC);
      ct[m]=(long)iTime(_Symbol,PERIOD_CURRENT,bO); m++;
     }
   return m;
  }

void DcDraw(const long offset,const long nowSrv,const long P)
  {
   g_dcBN=0; g_dcLN=0; g_dcTN=0;
   bool any=(InpDcWk||InpDcDay||InpDcH4||InpDcH1);
   if(any && g_fut>2)
     {
      double wo[8],wh[8],wl[8],wc[8]; long wt[8]; int wn=0;
      double do_[8],dh[8],dl[8],dc[8]; long dt[8]; int dn=0;
      double ao[8],ah[8],al[8],ac[8];  long at[8]; int an=0;
      double bo[8],bh[8],bl[8],bc[8];  long bt[8]; int bn=0;
      if(InpDcWk)  wn=DcLoadTf(PERIOD_W1,MathMin(MathMax(InpDcWkNum,1),4),wo,wh,wl,wc,wt);
      if(InpDcDay) dn=DcLoadDay(MathMin(MathMax(InpDcDayNum,1),6),offset,nowSrv,do_,dh,dl,dc,dt);
      if(InpDcH4)  an=DcLoadTf(PERIOD_H4,MathMin(MathMax(InpDcH4Num,1),6),ao,ah,al,ac,at);
      if(InpDcH1)  bn=DcLoadTf(PERIOD_H1,MathMin(MathMax(InpDcH1Num,1),6),bo,bh,bl,bc,bt);

      int gapB=MathMax(2,InpDcGap), grpB=MathMax(0,InpDcGrpGap), offB=MathMax(1,InpDcOffset);
      int halfW=MathMax(1,InpDcBody/2);
      // Bop ca cum cho vua vung SHIFT. Cot xa nhat = offB + span + halfW.
      int span=0;
      if(wn>0) span+=wn*gapB+grpB;
      if(dn>0) span+=dn*gapB+grpB;
      if(an>0) span+=an*gapB+grpB;
      if(bn>0) span+=bn*gapB+grpB;
      int maxCol=offB+span+halfW, room=g_fut-1;
      if(maxCol>room && maxCol>0)
        {
         double k=(double)room/(double)maxCol;
         offB =MathMax(1,(int)(offB*k));
         gapB =MathMax(2,(int)(gapB*k));
         grpB =MathMax(0,(int)(grpB*k));
         halfW=MathMax(1,(int)(halfW*k));
        }

      long wSec=(long)(iTime(_Symbol,PERIOD_W1,0)+PeriodSeconds(PERIOD_W1))-(long)TimeCurrent();
      long aSec=(long)(iTime(_Symbol,PERIOD_H4,0)+PeriodSeconds(PERIOD_H4))-(long)TimeCurrent();
      long bSec=(long)(iTime(_Symbol,PERIOD_H1,0)+PeriodSeconds(PERIOD_H1))-(long)TimeCurrent();
      int x=offB;
      if(wn>0) x=DcCluster(wo,wh,wl,wc,wt,wn,x,halfW,"1W",wSec,DC_STAMP_DATE,nowSrv,P,offset,gapB,grpB);
      // Cum nen-ngay gop tay tu nen chart nen KHONG co gio dong chinh xac - khong dem nguoc.
      if(dn>0) x=DcCluster(do_,dh,dl,dc,dt,dn,x,halfW,"1D",0,DC_STAMP_DOW,nowSrv,P,offset,gapB,grpB);
      if(an>0) x=DcCluster(ao,ah,al,ac,at,an,x,halfW,"H4",aSec,DC_STAMP_TIME,nowSrv,P,offset,gapB,grpB);
      if(bn>0) x=DcCluster(bo,bh,bl,bc,bt,bn,x,halfW,"H1",bSec,DC_STAMP_TIME,nowSrv,P,offset,gapB,grpB);
     }
   for(int i=g_dcBN;i<g_dcBDrawn;i++)
     { string is=IntegerToString(i); ObjectDelete(0,"NL_DCB"+is); ObjectDelete(0,"NL_DCBR"+is); }
   for(int i=g_dcLN;i<g_dcLDrawn;i++) ObjectDelete(0,"NL_DCL"+IntegerToString(i));
   for(int i=g_dcTN;i<g_dcTDrawn;i++) ObjectDelete(0,"NL_DCT"+IntegerToString(i));
   g_dcBDrawn=g_dcBN; g_dcLDrawn=g_dcLN; g_dcTDrawn=g_dcTN;
  }

//==========================================================================
//   VE
//==========================================================================
void DrawOne(const int slot,const Lvl &v,const bool swept,const long P,const long bcur,const int coln,
             const int baseBars,const int colStep,const bool withLabel)
  {
   // vua bi quet -> xam + gach dut; con lai theo format loai
   color           col = swept ? InpSweptCol : g_fcol[v.fmt];
   ENUM_LINE_STYLE sty = swept ? STYLE_DASH  : g_fsty[v.fmt];
   int             fsz = g_fsz[v.fmt];
   // duong tu nen goc -> diem cuoi = nen realtime + baseBars nen.
   // Nhan nam o xE nhung lui ve ben TRAI tuy theo so thu tu cot (coln)
   long startX = bcur + (long)baseBars * P;
   long lblX   = startX - (long)coln * (long)colStep * P;
   long xE     = lblX; // Duong ke dung dung cho cai nhan chu
   long x1     = v.formT;

   string ln=PFX+"L"+IntegerToString(slot);
   if(ObjectFind(0,ln)<0)
     { ObjectCreate(0,ln,OBJ_TREND,0,(datetime)x1,v.price,(datetime)xE,v.price);
       ObjectSetInteger(0,ln,OBJPROP_RAY_RIGHT,false); ObjectSetInteger(0,ln,OBJPROP_RAY_LEFT,false);
       ObjectSetInteger(0,ln,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,ln,OBJPROP_HIDDEN,true);
       ObjectSetInteger(0,ln,OBJPROP_BACK,false); }
   ObjectMove(0,ln,0,(datetime)x1,v.price); ObjectMove(0,ln,1,(datetime)xE,v.price);
   ObjectSetInteger(0,ln,OBJPROP_RAY_RIGHT,false);
   ObjectSetInteger(0,ln,OBJPROP_COLOR,col); ObjectSetInteger(0,ln,OBJPROP_STYLE,sty);
   ObjectSetInteger(0,ln,OBJPROP_WIDTH,InpLineWidth);

   string tx=PFX+"T"+IntegerToString(slot);
   // coln < 0 = che do "chi giu manh nhat": duong VAN ve, chi bo nhan.
   if(!withLabel){ ObjectDelete(0,tx); return; }
   if(ObjectFind(0,tx)<0)
     { ObjectCreate(0,tx,OBJ_TEXT,0,(datetime)lblX,v.price); ObjectSetString(0,tx,OBJPROP_FONT,"Arial");
       ObjectSetInteger(0,tx,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,tx,OBJPROP_HIDDEN,true);
       ObjectSetInteger(0,tx,OBJPROP_ANCHOR,ANCHOR_RIGHT_LOWER); } // Nhan nam tren duong ke, phat trien sang trai
   ObjectMove(0,tx,0,(datetime)lblX,v.price);
   ObjectSetString (0,tx,OBJPROP_TEXT,v.name+" : "+DoubleToString(v.price,_Digits));
   ObjectSetInteger(0,tx,OBJPROP_FONTSIZE,fsz);
   ObjectSetInteger(0,tx,OBJPROP_COLOR,col);
  }

void Draw()
  {
   ApplyScale();
   long offset=OffsetDetect();
   g_brokerOff=offset;
   long nowSrv=(long)iTime(_Symbol,PERIOD_CURRENT,0); if(nowSrv<=0) nowSrv=(long)TimeCurrent();

   g_nlv=0; ArrayResize(g_lv,64); g_zoneN=0;
   if(g_onSess || g_sessZoneOn) ComputeSessions(offset,nowSrv);
   ComputePD(offset,nowSrv);          // PDH/PDL, BPDH/BPDL, HOD/LOD, MNO
   ComputeWeek(offset,nowSrv);        // PWH/PWL, HOW/LOW
   if(g_onEq || g_onPvH1 || g_onPvM15) ComputeEQ(offset,nowSrv);
   ComputeATH();                      // g_athPrice (khung Thang)

   // muc VUA QUET moi nhat RIENG cho TUNG timeframe VA RIENG TUNG PHIA:
   //   suat = TfGroup*2 + (dinh?0:day 1) -> moi TF giu 1 vach xam DINH + 1 vach xam DAY.
   //   Vach xam dinh chi bi thay khi co DINH KHAC cung TF bi quet (day khong dinh toi).
   //   Tie-break theo Prio.
   long gMaxSw[SW_SLOT]; int gWin[SW_SLOT];
   for(int g=0;g<SW_SLOT;g++){ gMaxSw[g]=0; gWin[g]=-1; }
   for(int i=0;i<g_nlv;i++)
      if(g_lv[i].sweptT>0){ int gg=SwSlot(g_lv[i]); if(g_lv[i].sweptT>gMaxSw[gg]) gMaxSw[gg]=g_lv[i].sweptT; }
   for(int i=0;i<g_nlv;i++)
     { if(g_lv[i].sweptT<=0) continue;
       int gg=SwSlot(g_lv[i]);
       if(g_lv[i].sweptT==gMaxSw[gg])
          if(gWin[gg]<0 || Prio(g_lv[i].fmt)<Prio(g_lv[gWin[gg]].fmt)) gWin[gg]=i; }

   // ===== ALERT: thanh khoan vua bi QUET (bao 1 lan/muc; seed luc attach de khong don cu) =====
   if(!g_alertInit)
     {
      g_alertInit=true; g_alertSeen=";";
      for(int i=0;i<g_nlv;i++)
         if(g_lv[i].sweptT>0)
           { string s=g_lv[i].name+"@"+DoubleToString(g_lv[i].price,_Digits);
             if(StringFind(g_alertSeen,";"+s+";")<0) g_alertSeen+=s+";"; }
     }
   else if(InpAlertSweep)
     {
      for(int g=0;g<SW_SLOT;g++)
        {
         if(gWin[g]<0) continue;
         if(!InpAlertM15 && TfGroup(g_lv[gWin[g]].fmt)==4) continue;
         string sig=g_lv[gWin[g]].name+"@"+DoubleToString(g_lv[gWin[g]].price,_Digits);
         if(StringFind(g_alertSeen,";"+sig+";")<0)
           { g_alertSeen+=sig+";";
             FireAlert(StringFormat("Neiro Liquidity Map [%s %s]: liquidity SWEPT - %s @ %s",
                       _Symbol,TfStr(),g_lv[gWin[g]].name,DoubleToString(g_lv[gWin[g]].price,_Digits))); }
        }
     }

   long P=(long)PeriodSeconds(PERIOD_CURRENT); if(P<=0) P=60;

   // ===== GOP cum: uu tien PW>PD>BPD>Week>Day>Session>EQ>H1>M15, gia = cuc tri cum =====
   Lvl fin[]; ArrayResize(fin,MathMax(g_nlv*2+8,8)); int nf=0;
   // (1) muc DA QUET (xam, dut gach):
   //   - InpShowSwHist OFF: MOI timeframe giu 1 muc vua quet moi nhat (gWin[])
   //   - InpShowSwHist ON : hien HET cac muc da quet trong cua so
   if(InpShowSwHist)
     { // Cat theo InpSwHistDays: ca cua so co the sinh hang nghin duong, vuot
       // LVL_MAX va cac muc cu bi bo am tham.
       long swCut=nowSrv-(long)MathMax(InpSwHistDays,1)*86400;
       for(int i=0;i<g_nlv;i++)
          if(g_lv[i].sweptT>=swCut){ if(nf>=ArraySize(fin)) ArrayResize(fin,nf+16); fin[nf]=g_lv[i]; nf++; } }
   else
     {
      double eqWinPrH = (gWin[10]>=0)? g_lv[gWin[10]].price : -1.0;  // uu tien EQ (nhom 5) phia DINH
      double eqWinPrL = (gWin[11]>=0)? g_lv[gWin[11]].price : -1.0;  //                    phia DAY
      double dgap = InpMergeGapUSD; if(dgap<0) dgap=0;
      for(int sl=0;sl<SW_SLOT;sl++)
        {
         if(gWin[sl]<0) continue;
         int    gtf =sl/2;
         double eqPr=((sl%2)==0)? eqWinPrH : eqWinPrL;                                          // so CUNG phia
         if((gtf==3||gtf==4) && eqPr>0 && MathAbs(g_lv[gWin[sl]].price-eqPr)<=dgap) continue;   // pivot H1/M15 trung EQ -> bo
         if(nf>=ArraySize(fin)) ArrayResize(fin,nf+16);
         fin[nf]=g_lv[gWin[sl]]; nf++;
        }
     }
   // (2) unswept: tach 2 phia -> sort gia -> cluster single-linkage -> 1 muc/cum
   double mg=InpMergeGapUSD; if(mg<0) mg=0;
   for(int side=0;side<2;side++)
     {
      int ix[]; ArrayResize(ix,MathMax(g_nlv,1)); int c=0;
      for(int i=0;i<g_nlv;i++)
        { if(g_lv[i].sweptT!=0) continue;                    // chi unswept
          bool hi=IsHigh(g_lv[i].name);
          if((side==0)==hi) ix[c++]=i; }                     // side0=dinh, side1=day
      for(int a=0;a<c-1;a++) for(int b=a+1;b<c;b++)
         if(g_lv[ix[b]].price<g_lv[ix[a]].price){ int t=ix[a]; ix[a]=ix[b]; ix[b]=t; }
      int k=0;
      while(k<c)
        {
         int j=k+1;
         while(j<c && mg>0 && (g_lv[ix[j]].price-g_lv[ix[j-1]].price)<=mg) j++;   // cum [k,j-1]
         int best=ix[k]; double ex=g_lv[ix[k]].price;
         for(int m=k;m<j;m++)
           { if(Prio(g_lv[ix[m]].fmt)<Prio(g_lv[best].fmt)) best=ix[m];   // giu uu tien cao nhat
             if(side==0){ if(g_lv[ix[m]].price>ex) ex=g_lv[ix[m]].price; }// dinh -> MAX
             else       { if(g_lv[ix[m]].price<ex) ex=g_lv[ix[m]].price; }}// day -> MIN
         if(nf>=ArraySize(fin)) ArrayResize(fin,nf+16);
         fin[nf]=g_lv[best]; fin[nf].price=ex; nf++;          // ten/mau theo best, gia = cuc tri
         k=j;
        }
     }
   // MNO va ATH: KHONG qua buoc gop cum (nen khong bi mot muc khac nuot),
   // nhung van vao fin[] de duoc chia cot nhu moi nguoi. Truoc day chung ve
   // rieng bang DrawSolo() nen luon dinh cot 0 va de len nhan trung gia.
   if(g_onMno && g_mnoPrice>0)
     { if(nf>=ArraySize(fin)) ArrayResize(fin,nf+4);
       fin[nf].price=g_mnoPrice; fin[nf].name="MNO"; fin[nf].formT=g_mnoT; fin[nf].sweptT=0; fin[nf].fmt=18; nf++; }
   if(g_onAth && g_athPrice>0)
     { if(nf>=ArraySize(fin)) ArrayResize(fin,nf+4);
       fin[nf].price=g_athPrice; fin[nf].name="ATH"; fin[nf].formT=g_athT; fin[nf].sweptT=0; fin[nf].fmt=19; nf++; }

   // (3) so le nhan con TRUNG gia (theo InpLabelGapUSD)
   for(int a=0;a<nf-1;a++)
      for(int b=a+1;b<nf;b++)
         if(fin[b].price<fin[a].price){ Lvl tt=fin[a]; fin[a]=fin[b]; fin[b]=tt; }
   double colLast[]; ArrayResize(colLast,MathMax(nf,1)); int ncol=0;
   int    colOf[];   ArrayResize(colOf,  MathMax(nf,1));
   double gap=InpLabelGapUSD; if(gap<=0) gap=0.01;
   if(InpLabelCrowd==NL_CROWD_OVERLAP)
     { for(int k=0;k<nf;k++) colOf[k]=0; ncol=1; }
   else if(InpLabelCrowd==NL_CROWD_STRONGEST)
     {
      // fin[] da sort tang dan theo gia -> gom cum lien tiep nam trong gap,
      // moi cum chi giu nhan cua muc uu tien cao nhat. colOf = -1 => bo NHAN,
      // duong van ve.
      int i=0;
      while(i<nf)
        {
         int j=i+1;
         while(j<nf && (fin[j].price-fin[j-1].price)<gap) j++;
         int best=i;
         for(int k=i;k<j;k++) if(Prio(fin[k].fmt)<Prio(fin[best].fmt)) best=k;
         for(int k=i;k<j;k++) colOf[k]=(k==best)?0:-1;
         i=j;
        }
      ncol=1;
     }
   else
     {
      for(int k=0;k<nf;k++)
        { double pr=fin[k].price; int placed=-1;
          for(int cc=0;cc<ncol;cc++) if(pr-colLast[cc]>=gap){ placed=cc; break; }
          if(placed<0){ placed=ncol; ncol++; }
          colOf[k]=placed; colLast[placed]=pr; }
     }
   // --- Nhan bi "mat tieu" khi zoom: nhan nam o nen TUONG LAI (bcur + baseBars +
   // coln*step). MT5 chi ve duoc trong vung SHIFT ben phai; zoom cang gan thi vung
   // do cang it nen -> cot 1,2,3... roi ra ngoai va bien mat. Nen phai CO LAI buoc
   // cot theo cho trong thuc te thay vi dung cung 40 nen.
   int  visB  = (int)ChartGetInteger(0,CHART_VISIBLE_BARS);
   bool shOn  = (bool)ChartGetInteger(0,CHART_SHIFT);
   int widthBars = (int)ChartGetInteger(0, CHART_WIDTH_IN_BARS);
   int firstVis  = (int)ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
   int  fut   = widthBars - firstVis - 1;
   if(!shOn && fut > 10) fut = 1; // neu khong bat shift ma bi keo am thi thoi
   if(fut<1) fut=1;
   g_fut = fut;                                     // macro + cum nen dung chung so nay
   
   // Tinh baseB cho viec hien thi (Dung vung Shift)
   int baseB = fut - 1;
   if(baseB < InpLabelBars) baseB = InpLabelBars;
   
   int cstep = InpLabelColBars;
   int room = baseB - InpLabelBars;
   if(ncol > 1 && cstep * (ncol - 1) > room) {
      int safeDiv = room / (ncol - 1);
      cstep = (safeDiv > 1) ? safeDiv : 1;
   }

   // ve
   int slot=0;
   for(int k=0;k<nf && slot<LVL_MAX;k++)
     { bool sw=(fin[k].sweptT>0);
       DrawOne(slot, fin[k], sw, P, nowSrv, MathMax(colOf[k],0), baseB, cstep, colOf[k]>=0); slot++; }
   for(int s=slot;s<LVL_MAX;s++)
     { ObjectDelete(0,PFX+"L"+IntegerToString(s)); ObjectDelete(0,PFX+"T"+IntegerToString(s)); }
   // Xoa box + nhan + duong Open du thua. Khong the do "con object khong" de dung vong
   // lap: tat o Border la NL_Z khong duoc tao, vong lap se dung ngay o suat dau tien va
   // bo lai ca dam nen/nhan phia sau. Nho SO box cua luot truoc roi don den do.
   for(int z=g_zoneN;z<g_zoneDrawn;z++)
     { string zs=IntegerToString(z);
       ObjectDelete(0,"NL_Z" +zs); ObjectDelete(0,"NL_ZF"+zs); ObjectDelete(0,"NL_ZL"+zs);
       ObjectDelete(0,"NL_ZO"+zs); ObjectDelete(0,"NL_ZOT"+zs); }
   g_zoneDrawn=g_zoneN;

   // MNO va ATH nay di chung duong voi cac muc khac (fin[]), khong con
   // DrawSolo. Xoa object cu de ban nang cap khong con vet.
   ObjectDelete(0,PFX+"MNOL"); ObjectDelete(0,PFX+"MNOT");
   ObjectDelete(0,PFX+"ATHL"); ObjectDelete(0,PFX+"ATHT");

   // ===== So lieu cho dashboard: muc CHUA quet gan nhat hai phia + muc vua quet =====
   // Doc tu fin[] (da gop cum, da co ca MNO/ATH) nen khop chinh xac nhung gi ve tren
   // chart - giong ban Pine doc tu mang `merged`.
   double hudPx=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   if(hudPx<=0) hudPx=iClose(_Symbol,PERIOD_CURRENT,0);
   g_hudPx=hudPx;
   g_hudBslP=0; g_hudSslP=0; g_hudBslN=""; g_hudSslN=""; g_hudSwN=""; g_hudSwT=0;
   for(int k=0;k<nf;k++)
     {
      if(fin[k].sweptT<=0)
        {
         if(fin[k].price>hudPx && (g_hudBslP<=0 || fin[k].price<g_hudBslP))
           { g_hudBslP=fin[k].price; g_hudBslN=fin[k].name; }
         if(fin[k].price<hudPx && (g_hudSslP<=0 || fin[k].price>g_hudSslP))
           { g_hudSslP=fin[k].price; g_hudSslN=fin[k].name; }
        }
      else if(fin[k].sweptT>g_hudSwT)
        { g_hudSwT=fin[k].sweptT; g_hudSwN=fin[k].name; }
     }

   McDraw(offset,nowSrv,P);           // ICT macros
   DcDraw(offset,nowSrv,P);           // cum nen W / D / H4 / H1 o le phai
   HudDraw();
   NearAlert();

   ChartRedraw();
  }

//+------------------------------------------------------------------+
//==================================================================
//   FORMAT TABLE
//   fmt 0..19 -> colour / line style / font size used by DrawOne().
//   Sessions share one style for the live leg and one for the earlier legs.
//==================================================================
void LoadFmt()
  {
   int ts = MathMax(5,InpTextSize);
   g_fcol[0]=InpColTk;   g_fsty[0]=InpStySess;     g_fsz[0]=ts;
   g_fcol[1]=InpColBTk;  g_fsty[1]=InpStyPrevSess; g_fsz[1]=ts;
   g_fcol[2]=InpColLo;   g_fsty[2]=InpStySess;     g_fsz[2]=ts;
   g_fcol[3]=InpColBLo;  g_fsty[3]=InpStyPrevSess; g_fsz[3]=ts;
   g_fcol[4]=InpColAm;   g_fsty[4]=InpStySess;     g_fsz[4]=ts;
   g_fcol[5]=InpColBAm;  g_fsty[5]=InpStyPrevSess; g_fsz[5]=ts;
   g_fcol[6]=InpColLu;   g_fsty[6]=InpStySess;     g_fsz[6]=ts;
   g_fcol[7]=InpColBLu;  g_fsty[7]=InpStyPrevSess; g_fsz[7]=ts;
   g_fcol[8]=InpColPm;   g_fsty[8]=InpStySess;     g_fsz[8]=ts;
   g_fcol[9]=InpColBPm;  g_fsty[9]=InpStyPrevSess; g_fsz[9]=ts;
   g_fcol[10]=InpColPd;    g_fsty[10]=InpStyPd;     g_fsz[10]=ts;
   g_fcol[11]=InpColDay;   g_fsty[11]=InpStyDay;    g_fsz[11]=ts;
   g_fcol[12]=InpColEq;    g_fsty[12]=InpStyEq;     g_fsz[12]=ts;
   g_fcol[13]=InpColPvH1;  g_fsty[13]=InpStyPvH1;   g_fsz[13]=ts;
   g_fcol[14]=InpColPvM15; g_fsty[14]=InpStyPvM15;  g_fsz[14]=ts;
   g_fcol[15]=InpColBpd;   g_fsty[15]=InpStyBpd;    g_fsz[15]=ts;
   g_fcol[16]=InpColPw;    g_fsty[16]=InpStyPw;     g_fsz[16]=ts;
   g_fcol[17]=InpColWk;    g_fsty[17]=InpStyWk;     g_fsz[17]=ts;
   g_fcol[18]=InpColMno;   g_fsty[18]=InpStyMno;    g_fsz[18]=ts;
   g_fcol[19]=InpColAth;   g_fsty[19]=InpStyAth;    g_fsz[19]=MathMax(5,InpKeyTextSize);
  }

//==================================================================
//   THRESHOLD SCALING
//   Every dollar threshold in this indicator was tuned on gold. NL_REF_* are
//   the gold readings they were tuned against (20-08-2026: price 4483, D1 ATR
//   88.5), so on gold the factor lands on 1.00 and the defaults behave exactly
//   as before. Any other symbol gets the same distance in ITS own units.
//
//   ATR period is 200, not 14. Measured over 460 days of gold, the effective
//   threshold under ATR(14) swung across a 7.4x band and moved 2.85% a day -
//   the chart changed character week to week. ATR(200) holds a 1.8x band and
//   0.31% a day, which is STEADIER than the price factor's 1.9x / 0.98%, while
//   still being the dimensionally correct unit. ATR(200) on gold reads 89.3,
//   so NL_REF_ATR = 88 stays valid to within 1.5%.
//==================================================================
#define NL_ATR_PERIOD 200
double AtrD1()
  {
   if(g_atrH==INVALID_HANDLE) g_atrH=iATR(_Symbol,PERIOD_D1,NL_ATR_PERIOD);
   if(g_atrH==INVALID_HANDLE) return 0;
   double b[];
   if(CopyBuffer(g_atrH,0,0,1,b)<1) return 0;
   return b[0];
  }

void ApplyScale()
  {
   double px=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   if(px<=0) px=iClose(_Symbol,PERIOD_CURRENT,0);
   double byPrice=(px>0)? px/NL_REF_PRICE : 1.0;

   if(InpScaleMode==NL_SCALE_OFF)      g_scaleF=1.0;
   else if(InpScaleMode==NL_SCALE_ATR)
     {
      // ATR(200) needs 200 D1 bars. On a fresh terminal or a thin symbol they
      // may not have downloaded yet, so fall back to the price factor rather
      // than to 1.0, which would be the gold-only number elsewhere.
      double a=AtrD1();
      g_scaleF=(a>0)? a/NL_REF_ATR : byPrice;
     }
   else g_scaleF=byPrice;
   if(g_scaleF<=0) g_scaleF=1.0;

   InpEqRelUSD    = InpEqRelIn    * g_scaleF;
   InpMergeGapUSD = InpMergeGapIn * g_scaleF;
   InpLabelGapUSD = InpLabelGapIn * g_scaleF;
   InpNearDist    = InpNearDistIn * g_scaleF;
   InpMcDist      = InpMcDistIn   * g_scaleF;
  }

//==================================================================
//   PRESET
//==================================================================
void ResolvePreset()
  {
   g_onSessArr[0]=NlOn(InpShowTokyo, 1);
   g_onSessArr[1]=NlOn(InpShowLondon,1);
   g_onSessArr[2]=NlOn(InpShowNyAm,  1);
   g_onSessArr[3]=NlOn(InpShowLunch, 1);
   g_onSessArr[4]=NlOn(InpShowNyPm,  1);
   g_onSess     = (g_onSessArr[0]||g_onSessArr[1]||g_onSessArr[2]||g_onSessArr[3]||g_onSessArr[4]);
   // Box vung phien: cong tac tong o g_sessZoneOn (OnInit), day la cong tac tung phien.
   g_onZoneArr[0]=InpZTok; g_onZoneArr[1]=InpZLon; g_onZoneArr[2]=InpZAm;
   g_onZoneArr[3]=InpZLu;  g_onZoneArr[4]=InpZPm;
   g_onPrevSess = NlOn(InpShowPrevSess,2);
   g_onAth      = NlOn(InpShowAth,  1);
   g_onPd       = NlOn(InpShowPD,   1);
   g_onDay      = NlOn(InpShowDay,  1);
   g_onPw       = NlOn(InpShowPw,   2);
   g_onWk       = NlOn(InpShowWk,   2);
   g_onMno      = NlOn(InpShowMno,  2);
   g_onEq       = NlOn(InpShowEq,   2);
   g_onBpd      = NlOn(InpShowBpd,  3);
   g_onPvH1     = NlOn(InpShowPivH1, 3);
   g_onPvM15    = NlOn(InpShowPivM15,3);
   g_onMacro    = NlOn(InpMcOn,      3);

   int days=MathMax(InpDaysBack,1);
   InpEqH1Bars  = (int)(days*24*1.2);
   InpEqM15Bars = (int)(days*96*1.2);
  }

//==================================================================
//   DASHBOARD
//   Three columns, six rows: title / BSL / SSL / DRAW / SWEPT / SESSION.
//   Column 0 and 1 hang off the LEFT edge of the panel, column 2 off the
//   RIGHT edge, so the numbers stay aligned whichever corner is chosen.
//==================================================================
bool NlInSess(const int cur,const int o,const int c)
  { if(c>o) return (cur>=o && cur<c); return (cur>=o || cur<c); }

string NlSessionNow(const long utc)
  {
   long dMid = DayStartNY(utc);
   int  mins = (int)((utc-dMid)/60);
   int  cur  = (mins/60)*100 + (mins%60);
   if(NlInSess(cur,InpTokyoOpen, InpTokyoClose))  return "Tokyo";
   if(NlInSess(cur,InpLondonOpen,InpLondonClose)) return "London";
   if(NlInSess(cur,InpNyAmOpen,  InpNyAmClose))   return "NY AM";
   if(NlInSess(cur,InpLunchOpen, InpLunchClose))  return "NY Lunch";
   if(NlInSess(cur,InpNyPmOpen,  InpNyPmClose))   return "NY PM";
   return "Closed";
  }

void HudCell(const int row,const int col,const string txt,const color c,
             const ENUM_BASE_CORNER cn,const bool left,const bool top,
             const int W,const int H,const int pad,const int rowH,const int c1,const int fs)
  {
   string nm = PFX+"HUD"+IntegerToString(row)+IntegerToString(col);
   // A fresh OBJ_LABEL carries the literal text "Label" until something sets it,
   // and MT5 will not accept "" as a replacement - so an empty cell has to be
   // deleted outright, not blanked.
   if(txt=="")
     { ObjectDelete(0,nm); return; }
   if(ObjectFind(0,nm)<0)
     { ObjectCreate(0,nm,OBJ_LABEL,0,0,0);
       ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
       ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
       ObjectSetString (0,nm,OBJPROP_FONT,"Segoe UI"); }
   ObjectSetInteger(0,nm,OBJPROP_CORNER,cn);
   int x;
   if(col==2) x = left ? (InpHudX+W-pad) : (InpHudX+pad);
   else
     {
      int inset = pad + (col==1 ? c1 : 0);
      x = left ? (InpHudX+inset) : (InpHudX+W-inset);
     }
   // Bottom corners measure Y upward from the chart edge, so row 0 has to sit at
   // the FAR end of the panel and later rows step back toward the anchor. Using
   // (row+1) here pushed the last row clean out through the bottom of the panel.
   int y = top ? (g_hudY+pad+row*rowH) : (g_hudY+H-pad-row*rowH);
   ObjectSetInteger(0,nm,OBJPROP_ANCHOR,(col==2)?ANCHOR_RIGHT_UPPER:ANCHOR_LEFT_UPPER);
   ObjectSetInteger(0,nm,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,nm,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,fs);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,c);
   ObjectSetString (0,nm,OBJPROP_TEXT,txt);
  }

void HudDraw()
  {
   if(!InpHud){ ObjectsDeleteAll(0,PFX+"HUD"); return; }

   ENUM_BASE_CORNER cn = CORNER_RIGHT_UPPER;
   bool left=false, top=true;
   if(InpHudCorner==NL_TL){ cn=CORNER_LEFT_UPPER;  left=true;  top=true;  }
   if(InpHudCorner==NL_BR){ cn=CORNER_RIGHT_LOWER; left=false; top=false; }
   if(InpHudCorner==NL_BL){ cn=CORNER_LEFT_LOWER;  left=true;  top=false; }
   if(InpHudCorner==NL_MR){ cn=CORNER_RIGHT_UPPER; left=false; top=true;  }
   if(InpHudCorner==NL_ML){ cn=CORNER_LEFT_UPPER;  left=true;  top=true;  }

   int fs   = MathMax(6,InpHudFont);
   int rowH = fs+9;
   int pad  = 9;
   // Floor scales with the font: title, label column, value column, paddings.
   // At 9pt that is 306px - the full product name needs the extra room.
   int W    = MathMax(InpHudWidth, fs*34);
   int H    = rowH*6 + pad*2;
   int c1   = fs*7;
   // MT5 khong co goc "giua": neo vao goc TREN roi tu day bang xuong nua man hinh.
   // Offset Y cua nguoi dung khong con nghia o hai vi tri nay.
   g_hudY = InpHudY;
   if(InpHudCorner==NL_MR || InpHudCorner==NL_ML)
     { int chH=(int)ChartGetInteger(0,CHART_HEIGHT_IN_PIXELS);
       g_hudY = MathMax(0,(chH-H)/2); }

   color cBg  = (InpHudTheme==NL_DARK) ? C'19,23,34'    : C'255,255,255';
   color cBrd = (InpHudTheme==NL_DARK) ? C'42,46,57'    : C'224,227,235';
   color cTxt = (InpHudTheme==NL_DARK) ? C'209,212,220' : C'19,23,34';
   color cMut = C'120,123,134';
   color cBsl = C'242,54,69';
   color cSsl = C'8,153,129';

   string bg = PFX+"HUDBG";
   if(ObjectFind(0,bg)<0)
     { ObjectCreate(0,bg,OBJ_RECTANGLE_LABEL,0,0,0);
       ObjectSetInteger(0,bg,OBJPROP_SELECTABLE,false);
       ObjectSetInteger(0,bg,OBJPROP_HIDDEN,true);
       ObjectSetInteger(0,bg,OBJPROP_BACK,false); }
   ObjectSetInteger(0,bg,OBJPROP_CORNER,cn);
   // A rectangle label always grows right-and-down from its anchor, whichever
   // corner it is bound to. On a right/bottom corner the distance is measured
   // back toward that edge, so the anchor has to be pushed out by the panel size
   // or the box hangs off the screen and only its near edge stays visible.
   ObjectSetInteger(0,bg,OBJPROP_XDISTANCE, left ? InpHudX : (InpHudX+W));
   ObjectSetInteger(0,bg,OBJPROP_YDISTANCE, top  ? g_hudY : (g_hudY+H));
   ObjectSetInteger(0,bg,OBJPROP_XSIZE,W);
   ObjectSetInteger(0,bg,OBJPROP_YSIZE,H);
   ObjectSetInteger(0,bg,OBJPROP_BGCOLOR,cBg);
   ObjectSetInteger(0,bg,OBJPROP_COLOR,cBrd);
   ObjectSetInteger(0,bg,OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetInteger(0,bg,OBJPROP_WIDTH,1);

   long offset = OffsetDetect();
   long utc    = (long)TimeCurrent()-offset;
   long nyT    = utc + NyOffset(utc);
   MqlDateTime ny; TimeToStruct((datetime)nyT,ny);

   double dUp = (g_hudBslP>0) ? (g_hudBslP-g_hudPx) : -1.0;
   double dDn = (g_hudSslP>0) ? (g_hudPx-g_hudSslP) : -1.0;

   HudCell(0,0,"NEIRO LIQUIDITY MAP",cTxt,cn,left,top,W,H,pad,rowH,c1,fs);
   HudCell(0,1,"",            cMut,cn,left,top,W,H,pad,rowH,c1,fs);
   HudCell(0,2,_Symbol+" "+TfStr()+"  v" NL_VER,cMut,cn,left,top,W,H,pad,rowH,c1,fs);

   HudCell(1,0,"BSL",cBsl,cn,left,top,W,H,pad,rowH,c1,fs);
   HudCell(1,1,(dUp<0)?"-":g_hudBslN,cTxt,cn,left,top,W,H,pad,rowH,c1,fs);
   HudCell(1,2,(dUp<0)?"-":DoubleToString(g_hudBslP,_Digits)+"   +"+DoubleToString(dUp,_Digits),
           cBsl,cn,left,top,W,H,pad,rowH,c1,fs);

   HudCell(2,0,"SSL",cSsl,cn,left,top,W,H,pad,rowH,c1,fs);
   HudCell(2,1,(dDn<0)?"-":g_hudSslN,cTxt,cn,left,top,W,H,pad,rowH,c1,fs);
   HudCell(2,2,(dDn<0)?"-":DoubleToString(g_hudSslP,_Digits)+"   -"+DoubleToString(dDn,_Digits),
           cSsl,cn,left,top,W,H,pad,rowH,c1,fs);

   string drawTxt="-"; color drawCol=cMut; string drawVal="";
   if(dUp>=0 || dDn>=0)
     {
      bool up = (dDn<0) || (dUp>=0 && dUp<=dDn);
      drawTxt = up ? "BSL" : "SSL";
      drawCol = up ? cBsl : cSsl;
      if(dUp>=0 && dDn>=0) drawVal = DoubleToString(MathMin(dUp,dDn),_Digits)+" away";
     }
   HudCell(3,0,"DRAW",  cMut,  cn,left,top,W,H,pad,rowH,c1,fs);
   HudCell(3,1,drawTxt, drawCol,cn,left,top,W,H,pad,rowH,c1,fs);
   HudCell(3,2,drawVal, cMut,  cn,left,top,W,H,pad,rowH,c1,fs);

   if(InpHudSwept)
     {
      string swClock="";
      if(g_hudSwT>0)
        { long swUtc=g_hudSwT-offset;
          MqlDateTime sw; TimeToStruct((datetime)(swUtc+NyOffset(swUtc)),sw);
          swClock=StringFormat("%02d:%02d",sw.hour,sw.min); }
      HudCell(4,0,"SWEPT",cMut,cn,left,top,W,H,pad,rowH,c1,fs);
      HudCell(4,1,(g_hudSwN=="")?"-":g_hudSwN,cTxt,cn,left,top,W,H,pad,rowH,c1,fs);
      HudCell(4,2,swClock,cMut,cn,left,top,W,H,pad,rowH,c1,fs);
     }
   else
     { HudCell(4,0,"",cMut,cn,left,top,W,H,pad,rowH,c1,fs);
       HudCell(4,1,"",cMut,cn,left,top,W,H,pad,rowH,c1,fs);
       HudCell(4,2,"",cMut,cn,left,top,W,H,pad,rowH,c1,fs); }

   if(InpHudSess)
     {
      string sNow = NlSessionNow(utc);
      HudCell(5,0,"SESSION",cMut,cn,left,top,W,H,pad,rowH,c1,fs);
      HudCell(5,1,sNow,(sNow=="Closed")?cMut:cTxt,cn,left,top,W,H,pad,rowH,c1,fs);
      HudCell(5,2,StringFormat("%02d:%02d NY",ny.hour,ny.min),cMut,cn,left,top,W,H,pad,rowH,c1,fs);
     }
   else
     { HudCell(5,0,"",cMut,cn,left,top,W,H,pad,rowH,c1,fs);
       HudCell(5,1,"",cMut,cn,left,top,W,H,pad,rowH,c1,fs);
       HudCell(5,2,"",cMut,cn,left,top,W,H,pad,rowH,c1,fs); }

  }

//==================================================================
//   APPROACH ALERT
//   Fires once when price walks into the buffer around a live level and
//   re-arms only after price leaves it again.
//==================================================================
void NearAlert()
  {
   if(!InpAlertNear || !g_alertInit) return;
   double d = InpNearDist; if(d<=0) return;

   if(g_hudBslP>0 && (g_hudBslP-g_hudPx)<=d)
     {
      // Kiem tra M15 filter (BSL)
      bool skip = false;
      for(int i=0; i<g_nlv; i++) if(g_lv[i].name==g_hudBslN && !InpAlertM15 && TfGroup(g_lv[i].fmt)==4) skip = true;
      if(!skip)
        {
         string s=g_hudBslN+"@"+DoubleToString(g_hudBslP,_Digits);
         if(s!=g_nearHiSig)
           { g_nearHiSig=s;
             FireAlert(StringFormat("Neiro Liquidity Map [%s %s]: price approaching %s @ %s",
                       _Symbol,TfStr(),g_hudBslN,DoubleToString(g_hudBslP,_Digits))); }
        }
     }
   else g_nearHiSig="";

   if(g_hudSslP>0 && (g_hudPx-g_hudSslP)<=d)
     {
      // Kiem tra M15 filter (SSL)
      bool skip = false;
      for(int i=0; i<g_nlv; i++) if(g_lv[i].name==g_hudSslN && !InpAlertM15 && TfGroup(g_lv[i].fmt)==4) skip = true;
      if(!skip)
        {
         string s=g_hudSslN+"@"+DoubleToString(g_hudSslP,_Digits);
         if(s!=g_nearLoSig)
           { g_nearLoSig=s;
             FireAlert(StringFormat("Neiro Liquidity Map [%s %s]: price approaching %s @ %s",
                       _Symbol,TfStr(),g_hudSslN,DoubleToString(g_hudSslP,_Digits))); }
        }
     }
   else g_nearLoSig="";
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   int tfCur = PeriodSeconds(PERIOD_CURRENT);
   g_sessZoneOn = NlOn(InpShowSessZone,2)
                  && tfCur >= PeriodSeconds(InpSessTfMin)
                  && tfCur <= PeriodSeconds(InpSessTfMax);
   IndicatorSetString(INDICATOR_SHORTNAME,"Neiro Liquidity Map");
   ResolvePreset();
   LoadFmt();
   g_prevShift=(bool)ChartGetInteger(0,CHART_SHIFT);
   ChartSetInteger(0,CHART_SHIFT,true);
   ObjectsDeleteAll(0,PFX);
   // Bo dem object phai ve 0 cung luc chart bi don sach, khong thi vong don du thua
   // se di xoa nhung object vua duoc ve lai.
   g_zoneDrawn=0; g_mcDrawn=0; g_dcBDrawn=0; g_dcLDrawn=0; g_dcTDrawn=0;
   EventSetTimer(1);
   Draw();
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason)
  {
   EventKillTimer();
   if(g_atrH!=INVALID_HANDLE){ IndicatorRelease(g_atrH); g_atrH=INVALID_HANDLE; }
   ObjectsDeleteAll(0,PFX);
   if(!g_prevShift) ChartSetInteger(0,CHART_SHIFT,false);
   ChartRedraw();
  }
// Draw() reloads the H1 / M15 history every call, so it must not run on every
// tick. A new bar always redraws immediately; between bars the throttle caps it.
void DrawThrottled(const bool force)
  {
   uint now=GetTickCount();
   if(!force && InpRefreshMs>0 && (now-g_lastDraw)<(uint)InpRefreshMs) return;
   g_lastDraw=now;
   Draw();
  }
void OnTimer(){ DrawThrottled(false); }
int OnCalculate(const int rates_total,const int prev_calculated,
                const datetime &time[],const double &open[],const double &high[],
                const double &low[],const double &close[],const long &tick_volume[],
                const long &volume[],const int &spread[])
  {
   static datetime lastBar=0;
   datetime cur=(rates_total>0)? time[rates_total-1] : 0;
   bool newBar=(cur!=lastBar);
   lastBar=cur;
   DrawThrottled(newBar || prev_calculated==0);
   return rates_total;
  }
//+------------------------------------------------------------------+
