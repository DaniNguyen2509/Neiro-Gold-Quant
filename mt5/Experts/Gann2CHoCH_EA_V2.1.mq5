//+------------------------------------------------------------------+
//|                                              Gann2CHoCH_EA.mq5   |
//|  Setup "2 CHoCH" (failed setup reversal)                         |
//|  - CHoCH + point A : Gann Swing SF1 (port of indicator Module 0) |
//|  - Points B / C    : Bonova pullback provider (f_class/f_provider)|
//|  - Same logic as TradingView indicator "Gann 2CHoCH" (Module 3)  |
//|  Account: Hedging. Source is ASCII only.                         |
//+------------------------------------------------------------------+
#property copyright "Gann 2CHoCH EA"
#property version   "1.15"
#property description "2 CHoCH setup: CHoCH from Gann SF1, B/C from Bonova pullback points."
#property description "Buy Stop at B (+offset), SL = C - buffer, TP = R:R from real fill, BE at 1R."

#include <Trade/Trade.mqh>

//--- enums
enum ENUM_NOC_MODE
  {
   NOC_ENTER = 0,   // (c) Enter anyway, C = lowest low since B
   NOC_DROP  = 1    // (a) Drop B, wait for next confirmed top
  };
enum ENUM_LOT_MODE
  {
   LOT_FIXED   = 0, // Fixed lot
   LOT_MONEY   = 1, // Fixed risk money per trade
   LOT_PERCENT = 2  // Risk % of balance per trade
  };
enum ENUM_SMALL_LOT
  {
   SMALL_USE_MIN = 0, // (a) Use minimum lot (0.01)
   SMALL_SKIP    = 1  // (b) Skip the trade
  };
enum ENUM_DL_UNIT
  {
   DL_MONEY = 0,    // Money (account currency)
   DL_PCT   = 1     // % of balance at start of day (server time)
  };
enum ENUM_DL_SCOPE
  {
   DLS_2CH        = 0,  // Only 2CHoCH EA trades (comment 2CH)
   DLS_2CH_MANUAL = 1,  // 2CHoCH EA trades + manual trades (magic 0)
   DLS_ALL        = 2   // Whole account (all trades)
  };
enum ENUM_DL_ACT
  {
   DL_KEEP  = 0,    // Keep open trades (SL/TP/BE keep working)
   DL_CLOSE = 1     // Close all open trades
  };
enum ENUM_PC_SL
  {
   PCSL_KEEP = 0,   // Keep SL
   PCSL_BE   = 1,   // Move SL to break-even
   PCSL_LOCK = 2    // Move SL to previous level (level 1 -> BE)
  };

//--- inputs
input group "=== Setup 2 CHoCH ==="
input ENUM_TIMEFRAMES InpTF          = PERIOD_CURRENT; // Signal timeframe (recommended M5 / M30)
input ENUM_NOC_MODE   InpNoC         = NOC_ENTER;      // Price breaks B before C is confirmed
input double          InpEntryOffset = 0.10;           // Stop order beyond B (price units, 0.10 = 1 tick GC)
input double          InpSLBuffer    = 3.0;            // SL buffer beyond C (price units)
input double          InpRR          = 1.5;            // TP R:R  1 : x
input double          InpMaxSL       = 40.0;           // Max SL distance (price units, 0 = off)
input bool            InpSpreadAdj   = true;           // Add spread to Buy Stop price / Sell SL (Ask side)
input int             InpWarmupBars  = 5000;           // History bars to rebuild state on start
input bool            InpStopOn      = true;           // Stop orders at B ON (false = only FVG entries)
input bool            InpStopAfterFvg= true;           // Also place Buy/Sell Stop at B when the setup already had an FVG entry
input bool            InpFvgAfterStop= true;           // Also take FVG entries when the setup's Stop at B already filled

input group "=== Trade management ==="
input bool            InpBEOn        = true;           // Move SL to break-even
input double          InpBE_R        = 1.0;            // ... when profit reaches x R
input double          InpBEBuffer    = 0.3;            // BE buffer (price units)

input group "=== FVG entry at ZO4 zone (C) ==="
input bool            InpFvgOn       = false;          // FVG entry ON at start (chart button FVG toggles it)
input int             InpFvgZoneBars = 20;             // Zone valid for n bars (FVG bar 1 must be inside)
input double          InpFvgSLBuffer = 3.0;            // FVG SL buffer beyond C (price units)
input double          InpFvgRR       = 3.0;            // FVG TP R:R  1 : x
input bool            InpFvgBEOn     = false;          // FVG: move SL to break-even
input double          InpFvgBE_R     = 1.5;            // FVG: ... when profit reaches x R

input group "=== M30 + M5 mode (zones from Signal TF, FVG on chart bars) ==="
input bool            InpM5Mode      = false;          // ON: attach to M5 chart, Signal TF = M30. FVG checked on M5 bars
input int             InpF5MaxPerZone= 2;              // Max FVG entries per zone
input double          InpF5SLBuffer  = 3.0;            // FVG M5: SL buffer beyond C (price units)
input double          InpF5RR        = 3.0;            // FVG M5: TP R:R  1 : x
input bool            InpF5BEOn      = true;           // FVG M5: move SL to break-even
input double          InpF5BE_R      = 1.0;            // FVG M5: ... when profit reaches x R

input group "=== Partial close: Stop orders at B ==="
input bool            InpPcS_On      = false;          // Partial close ON
input double          InpPcS_R1      = 1.0;            // Level 1 at x R (0 = off)
input double          InpPcS_P1      = 30.0;           // Level 1 close % of initial lot
input ENUM_PC_SL      InpPcS_A1      = PCSL_KEEP;      // Level 1 SL action
input double          InpPcS_R2      = 2.0;            // Level 2 at x R (0 = off)
input double          InpPcS_P2      = 30.0;           // Level 2 close % of initial lot
input ENUM_PC_SL      InpPcS_A2      = PCSL_KEEP;      // Level 2 SL action
input double          InpPcS_R3      = 0.0;            // Level 3 at x R (0 = off)
input double          InpPcS_P3      = 0.0;            // Level 3 close % of initial lot
input ENUM_PC_SL      InpPcS_A3      = PCSL_KEEP;      // Level 3 SL action

input group "=== Partial close: FVG entries (signal TF and M5) ==="
input bool            InpPcF_On      = false;          // Partial close ON
input double          InpPcF_R1      = 1.0;            // Level 1 at x R (0 = off)
input double          InpPcF_P1      = 30.0;           // Level 1 close % of initial lot
input ENUM_PC_SL      InpPcF_A1      = PCSL_KEEP;      // Level 1 SL action
input double          InpPcF_R2      = 2.0;            // Level 2 at x R (0 = off)
input double          InpPcF_P2      = 30.0;           // Level 2 close % of initial lot
input ENUM_PC_SL      InpPcF_A2      = PCSL_KEEP;      // Level 2 SL action
input double          InpPcF_R3      = 0.0;            // Level 3 at x R (0 = off)
input double          InpPcF_P3      = 0.0;            // Level 3 close % of initial lot
input ENUM_PC_SL      InpPcF_A3      = PCSL_KEEP;      // Level 3 SL action

input group "=== Drawing ==="
input bool            InpDrawZones   = true;           // Draw ZO4 zones / C-x / FVG boxes on chart
input color           InpZoneClrBuy  = C'0,120,80';    // Zone color BUY
input color           InpZoneClrSell = C'150,40,40';   // Zone color SELL
input color           InpFvgClr      = C'40,80,170';   // FVG box color
input int             InpZoneKeep    = 30;             // Keep last n zones / FVG boxes on chart
input bool            InpDrawSwing   = true;           // Draw Gann swing SF1 (swings the EA uses)
input color           InpSwingClr    = clrOrange;      // SF1 swing color
input int             InpSwingWidth  = 2;              // SF1 swing width
input ENUM_LINE_STYLE InpSwingStyle  = STYLE_SOLID;    // SF1 swing style
input int             InpSwingKeep   = 40;             // Keep last n SF1 swings (max 60)
input bool            InpDrawChoch   = true;           // Draw CHoCH lines of SF1 (like TradingView)
input color           InpChochUpClr  = clrDeepSkyBlue; // CHoCH color: price broke a top (bullish)
input color           InpChochDnClr  = clrHotPink;     // CHoCH color: price broke a bottom (bearish)
input int             InpChochKeep   = 30;             // Keep last n CHoCH lines
input bool            InpDrawABC     = true;           // Label A / B / C of the current setups
input color           InpABCBuyClr   = clrLime;        // A / B / C label color BUY setup
input color           InpABCSellClr  = clrTomato;      // A / B / C label color SELL setup
input int             InpABCFont     = 9;              // A / B / C label font size

input group "=== Lot size ==="
input ENUM_LOT_MODE   InpLotMode     = LOT_FIXED;      // Lot mode
input double          InpFixedLot    = 0.01;           // Fixed lot
input double          InpRiskMoney   = 10.0;           // Risk money per trade (account currency)
input double          InpRiskPercent = 1.0;            // Risk % of balance per trade
input ENUM_SMALL_LOT  InpSmallLot    = SMALL_USE_MIN;  // When computed lot < minimum lot
input double          InpMaxLot      = 5.0;            // Max lot per trade

input group "=== Guards ==="
input double          InpMaxSpread      = 0.60;        // Max spread to place/modify orders (price units, 0 = off)
input int             InpMaxTradesDay   = 0;           // Max new trades per day (0 = off)

input group "=== Daily limit: shared by ALL 2CHoCH EAs on this account ==="
input ENUM_DL_SCOPE   InpDLScope        = DLS_2CH_MANUAL; // Trades counted in the daily P/L
input ENUM_DL_UNIT    InpDLUnit         = DL_PCT;      // Unit of the daily limits
input double          InpDLLoss         = 0.0;         // Daily LOSS limit (closed today + floating, 0 = off)
input ENUM_DL_ACT     InpDLLossAct      = DL_KEEP;     // When LOSS limit is hit: open trades
input double          InpDLWin          = 0.0;         // Daily PROFIT target (closed today + floating, 0 = off)
input ENUM_DL_ACT     InpDLWinAct       = DL_KEEP;     // When PROFIT target is hit: open trades
input bool            InpDLCloseManual  = false;       // Action Close also closes manual trades (magic 0, all symbols)

input group "=== Prop firm: holding time ==="
input int             InpMaxHoldDays    = 2;           // Max holding days incl. entry day (trading days, 0 = off)
input string          InpCloseTime      = "23:30";     // Close time on the last day (server time HH:MM)
input bool            InpNoWeekend      = false;       // Close all on Friday at close time, no pending over weekend
input bool            InpNoEntryOn      = false;       // No-entry window ON (open trades still managed)
input string          InpNoEntryFrom    = "23:30";     // No-entry window from (server time HH:MM)
input string          InpNoEntryTo      = "01:00";     // No-entry window until (server time HH:MM, may pass midnight)

input group "=== Other ==="
input long            InpMagic       = 2026110901;     // Magic number
input bool            InpAlert       = true;           // Popup alert
input bool            InpPush        = false;          // Push notification (MT5 mobile)
input bool            InpDraw        = true;           // Draw pending entry / SL lines
input int             InpBtnX        = 10;             // Buttons X
input int             InpBtnY        = 25;             // Buttons Y

//==================================================================
//==== LOGIC CORE BEGIN (pure logic, no trading; mirrors Pine) =====
//==================================================================
#define GMAX 64

// Gann F0 / F1 / SF1 point arrays (index 0 = newest / developing point)
datetime gX0[GMAX];  double gY0[GMAX];  int gN0 = 0;
datetime gXF1[GMAX]; double gYF1[GMAX]; int gNF1 = 0;
datetime gSX[GMAX];  double gSY[GMAX];  int gNS = 0;
double   gMark   = 0.0;
// CHoCH on SF1 (Pine Module 0): (y3 > y2 && y3 < y1 && y0 < y2) || (y3 < y2 && y3 > y1 && y0 > y2) -> line at y2
double   gChMark = 0.0;
int      gNEvCh  = 0;
datetime gEvChX1[4], gEvChX2[4];
double   gEvChY[4];
int      gEvChDir[4];        // 1 = bullish CHoCH (price broke a top), -1 = bearish
bool     gInit   = false;
double   gHpPrev = 0.0, gLpPrev = 0.0;
long     gBar    = 0;          // running bar counter (= Pine bar_index)

// Bonova pullback provider state
double   pvH = 0.0, pvL = 0.0;
long     pvI = 0;
datetime pvT = 0;
int      pvPh = -1;            // 0 = up phase, 1 = down phase
int      pvLast = 4;           // class of last non-inside bar (1 = outside bar)
bool     pvTop = false, pvBot = false;
double   pvTopPx = 0.0, pvBotPx = 0.0;
long     pvTopI = 0, pvBotI = 0;
datetime pvTopT = 0, pvBotT = 0;

struct Setup
  {
   bool     active;
   int      dir;      // 1 = BUY, -1 = SELL
   int      stage;    // 1 = wait B, 2 = have B wait C, 3 = have C
   double   aS;       // A of the failed setup (A Sell for BUY)
   datetime tAS;
   double   a;        // A Buy (= B Sell)
   datetime tA;
   double   b;        // B (fixed when confirmed)
   datetime tB;
   bool     hasC;
   double   c;
   datetime tC;
   long     i0;       // bar counter when setup detected
   long     bI;       // bar counter of B reference bar
   bool     hasLowB;
   double   lowB;     // lowest low since B (normalized to BUY direction)
   datetime tLowB;
   long     cBar;     // bar counter of the C bar
   long     lowBBar;  // bar counter of lowest low since B
   // ZO4 data of the current C, built bar by bar (same as the Pine indicator)
   bool     zHP; double zProt; datetime zProtT; bool zOsb;
   bool     zHC; double zConf; datetime zConfT; bool zCB; bool zBrk;
   bool     zDone; double zCv;            // zone already created for C = zCv
   // same data for "lowest low since B" (used when (c) enters without confirmed C)
   bool     lbHP; double lbProt; datetime lbProtT; bool lbOsb;
   bool     lbHC; double lbConf; datetime lbConfT; bool lbCB; bool lbBrk;
  };

Setup    gS[2];               // 0 = BUY, 1 = SELL
datetime gLastKey[2];
bool     gModeC  = true;
double   gOffset = 0.10;
double   gBuf    = 3.0;
// per-bar events
int      gEvNew[2], gEvArm[2], gEvFill[2], gEvCancel[2];
double   gEvFillSL[2];
// ZO4 zone at C (port of Bonova f_buildZones) + FVG entry
#define RB 2048
double   rbH[RB], rbL[RB], rbDnH[RB], rbUpL[RB];
datetime rbT[RB], rbDnHT[RB], rbUpLT[RB];
datetime zDnHT = 0, zUpLT = 0;
int      gCurKl = 0;                 // class of the current bar
// snapshot of zone data at the current reference bar (= C bar when a pivot is confirmed)
int      pvSKl = 0; bool pvSHDn = false, pvSHUp = false; double pvSDnH = 0.0, pvSUpL = 0.0; datetime pvSDnHT = 0, pvSUpLT = 0;
// snapshot captured on the bar a pivot is emitted
int      pvEKl = 0; bool pvEHDn = false, pvEHUp = false; double pvEDnH = 0.0, pvEUpL = 0.0; datetime pvEDnHT = 0, pvEUpLT = 0;
double   pvEH = 0.0, pvEL = 0.0;
long     gZoneId = 0;
int      rbKl[RB];
bool     rbHDn[RB], rbHUp[RB];
bool     zHaveDn = false, zHaveUp = false;
double   zDnH = 0.0, zUpL = 0.0;
#define ZMAX 32
struct Zone
  {
   bool     alive;
   int      dir;
   double   c;
   double   top;
   double   bot;
   long     bar;
   bool     used;
   long     id;       // unique zone id (for chart objects)
   datetime left;     // left edge time (protect / confirm bar, like Bonova)
   datetime tc;       // time of C bar
   datetime created;  // time of the bar the zone appeared
   int      cs;       // case 1 / 2 / 3 (OSB)
   long     sid;      // setup id (i0 of the setup that made it)
  };
Zone     gZ[ZMAX];
int      gNZ = 0;
bool     gZMade[2];
double   gZC[2];
int      gZoneBars = 20;
bool     gFvgPause = false;    // EA no-entry window: FVG not taken and not counted (zone keeps waiting)
int      gEvFvg[2];
double   gEvFvgC[2];
datetime gEvFvgT1[2], gEvFvgT3[2];
double   gEvFvgLo[2], gEvFvgHi[2];
long     gEvFvgSid[2];
// zone events of the current bar (for drawing / logging)
Zone     gEvZN[4];  int gNEvZN = 0;    // zones created
Zone     gEvZX[32]; int gNEvZX = 0;    // zones broken at C

double Nz(int d, double v) { return d == 1 ? v : -v; }

void ResetSetup(Setup &s)
  {
   s.active = false; s.dir = 0; s.stage = 0;
   s.aS = 0.0; s.tAS = 0; s.a = 0.0; s.tA = 0;
   s.b = 0.0; s.tB = 0; s.hasC = false; s.c = 0.0; s.tC = 0;
   s.i0 = 0; s.bI = 0; s.hasLowB = false; s.lowB = 0.0; s.tLowB = 0; s.cBar = 0; s.lowBBar = 0;
   s.zHP = false; s.zProt = 0.0; s.zProtT = 0; s.zOsb = false; s.zHC = false; s.zConf = 0.0; s.zConfT = 0; s.zCB = false; s.zBrk = false;
   s.zDone = false; s.zCv = 0.0;
   s.lbHP = false; s.lbProt = 0.0; s.lbProtT = 0; s.lbOsb = false; s.lbHC = false; s.lbConf = 0.0; s.lbConfT = 0; s.lbCB = false; s.lbBrk = false;
  }

void UnshiftF0(datetime x, double y)
  {
   int m = (gN0 < GMAX) ? gN0 : GMAX - 1;
   for(int k = m; k > 0; k--) { gX0[k] = gX0[k - 1]; gY0[k] = gY0[k - 1]; }
   gX0[0] = x; gY0[0] = y;
   if(gN0 < GMAX) gN0++;
  }
void UnshiftF1(datetime x, double y)
  {
   int m = (gNF1 < GMAX) ? gNF1 : GMAX - 1;
   for(int k = m; k > 0; k--) { gXF1[k] = gXF1[k - 1]; gYF1[k] = gYF1[k - 1]; }
   gXF1[0] = x; gYF1[0] = y;
   if(gNF1 < GMAX) gNF1++;
  }
void UnshiftSF(datetime x, double y)
  {
   int m = (gNS < GMAX) ? gNS : GMAX - 1;
   for(int k = m; k > 0; k--) { gSX[k] = gSX[k - 1]; gSY[k] = gSY[k - 1]; }
   gSX[0] = x; gSY[0] = y;
   if(gNS < GMAX) gNS++;
  }

// F1 (port of f_CalculateFn1)
int CalcFn1(datetime px, double py)
  {
   if((gYF1[0] >= gYF1[1] && gY0[0] < gYF1[1]) || (gYF1[0] <= gYF1[1] && gY0[0] > gYF1[1]))
     { UnshiftF1(px, py); return 1; }
   if(gYF1[0] >= gYF1[1] && (gY0[0] < gY0[1] && gY0[0] < gY0[2] && gY0[1] < gY0[3]) && gY0[2] < gY0[3])
     { UnshiftF1(px, py); return 1; }
   if(gYF1[0] <= gYF1[1] && (gY0[0] > gY0[1] && gY0[0] > gY0[2] && gY0[1] > gY0[3]) && gY0[2] > gY0[3])
     { UnshiftF1(px, py); return 1; }
   if(gYF1[0] >= gYF1[1] && py >= gYF1[0])
     { gXF1[0] = px; gYF1[0] = py; return 2; }
   if(gYF1[0] <= gYF1[1] && py <= gYF1[0])
     { gXF1[0] = px; gYF1[0] = py; return 2; }
   return 0;
  }

// SF1 (port of f_CalculateSFn1)
int CalcSFn1(datetime px, double py)
  {
   if(gMark == 0.0)
     {
      if((gSY[0] >= gSY[1] && py >= gSY[0]) || (gSY[0] <= gSY[1] && py <= gSY[0]))
        { gSX[0] = px; gSY[0] = py; return 2; }
      if((gSY[0] >= gSY[1] && py < gSY[1]) || (gSY[0] <= gSY[1] && py > gSY[1]))
        { UnshiftSF(px, py); return 1; }
      if((gSY[0] >= gSY[1] && py < gSY[0] && py > gSY[1]) || (gSY[0] <= gSY[1] && py > gSY[0] && py < gSY[1]))
        { UnshiftSF(px, py); gMark = py; return 1; }
     }
   else if(gMark > 0.0)
     {
      if((gSY[0] >= gSY[1] && py < gSY[1]) || (gSY[0] <= gSY[1] && py > gSY[1]))
        { UnshiftSF(px, py); gMark = 0.0; return 1; }
      if((gSY[0] >= gSY[1] && py > gSY[2]) || (gSY[0] <= gSY[1] && py < gSY[2]))
        { gSX[0] = px; gSY[0] = py; gMark = 0.0; return 2; }
      if((gSY[0] >= gSY[1] && py <= gSY[2] && py >= gSY[0]) || (gSY[0] <= gSY[1] && py >= gSY[2] && py <= gSY[0]))
        { gSX[0] = px; gSY[0] = py; gMark = py; return 2; }
     }
   return 0;
  }

void CheckChoch(datetime px)
  {
   if(gNS < 4) return;
   double y0 = gSY[0], y1 = gSY[1], y2 = gSY[2], y3 = gSY[3];
   bool dn = (y3 > y2 && y3 < y1 && y0 < y2);
   bool up = (y3 < y2 && y3 > y1 && y0 > y2);
   if(!(dn || up) || y2 <= 0 || y2 == gChMark) return;
   gChMark = y2;
   if(gNEvCh < 4)
     {
      int k = gNEvCh++;
      gEvChX1[k] = gSX[2]; gEvChX2[k] = px; gEvChY[k] = y2; gEvChDir[k] = up ? 1 : -1;
     }
  }

void CalcF1(datetime px, double py)
  {
   UnshiftF0(px, py);
   if(CalcFn1(px, py) > 0)
      if(CalcSFn1(px, py) > 0) CheckChoch(px);
  }

void CalcPoints(datetime px, double y1, double y2)
  {
   if((gY0[0] > y1 && gY0[0] > y2) || (gY0[0] < y1 && gY0[0] < y2))
      CalcF1(px, gY0[1]);
   CalcF1(px, y1);
   CalcF1(px, y2);
  }

void NewSetup(Setup &s, int d, double aS, datetime tAS, double a, datetime tA, double b, datetime tB)
  {
   ResetSetup(s);
   s.active = true; s.dir = d; s.stage = 1;
   s.aS = aS; s.tAS = tAS; s.a = a; s.tA = tA; s.b = b; s.tB = tB;
   s.i0 = gBar;
  }

// Build ZO4 zone at C once it is valid (price broke "protect"), like Bonova.
// Same incremental logic as the Pine indicator (no look-back into old bars).
void ZoneHook(Setup &s, int side, datetime t, double h, double l)
  {
   if(s.zDone && s.zCv == s.c) return;
   int d = s.dir;
   if(!s.zHC && gBar > s.cBar && gCurKl == ((d == 1) ? 2 : 3))
     {
      s.zHC = true; s.zConf = (d == 1) ? h : l; s.zConfT = t;
      s.zCB = s.zHP && ((d == 1) ? (h >= s.zProt) : (l <= s.zProt));
     }
   if(s.zHP && ((d == 1) ? (h >= s.zProt) : (l <= s.zProt))) s.zBrk = true;
   if(!s.zHP || !s.zBrk) return;
   int cs = s.zOsb ? 3 : ((s.zHC && !s.zCB) ? 2 : 1);
   double other = (cs == 2) ? s.zConf : s.zProt;
   datetime otherT = (cs == 2) ? s.zConfT : s.zProtT;
   int idx = -1;
   for(int i = 0; i < gNZ; i++) if(!gZ[i].alive) { idx = i; break; }
   if(idx < 0)
     {
      if(gNZ < ZMAX) idx = gNZ++;
      else
        {
         idx = 0;
         for(int i = 1; i < gNZ; i++) if(gZ[i].bar < gZ[idx].bar) idx = i;
        }
     }
   gZ[idx].alive = true; gZ[idx].dir = d; gZ[idx].c = s.c; gZ[idx].bar = gBar; gZ[idx].used = false;
   gZ[idx].id = ++gZoneId; gZ[idx].tc = s.tC; gZ[idx].cs = cs; gZ[idx].sid = s.i0;
   gZ[idx].left = (otherT > 0 && otherT < s.tC) ? otherT : s.tC;
   gZ[idx].created = t;
   gZ[idx].top = (d == 1) ? ((other > s.c) ? other : s.c) : s.c;
   gZ[idx].bot = (d == 1) ? s.c : ((other < s.c) ? other : s.c);
   s.zDone = true; s.zCv = s.c;
   if(gNEvZN < 4) gEvZN[gNEvZN++] = gZ[idx];
  }

// Each closed bar: kill zones broken at C / expired; FVG entry signal (bar 1 touches zone, bar 3 makes FVG)
void ZonesOnBar(datetime t, double h, double l)
  {
   for(int i = 0; i < gNZ; i++)
     {
      if(!gZ[i].alive) continue;
      int d = gZ[i].dir;
      if((d == 1) ? (l < gZ[i].c) : (h > gZ[i].c))
        {
         gZ[i].alive = false;
         if(gNEvZX < 32) gEvZX[gNEvZX++] = gZ[i];
         continue;
        }
      if(gBar > gZ[i].bar + gZoneBars + 2) { gZ[i].alive = false; continue; }
      if(gZ[i].used) continue;
      long b1 = gBar - 2;
      if(b1 < gZ[i].bar + 1 || b1 > gZ[i].bar + gZoneBars) continue;
      int i1 = (int)(b1 % RB);
      bool touch = (d == 1) ? (rbL[i1] <= gZ[i].top) : (rbH[i1] >= gZ[i].bot);
      bool gap = (d == 1) ? (l > rbH[i1]) : (h < rbL[i1]);
      if(touch && gap && !gFvgPause)
        {
         gZ[i].used = true;
         int side = (d == 1) ? 0 : 1;
         gEvFvg[side] = 1; gEvFvgC[side] = gZ[i].c; gEvFvgSid[side] = gZ[i].sid;
         gEvFvgT1[side] = rbT[i1]; gEvFvgT3[side] = t;
         gEvFvgLo[side] = (d == 1) ? rbH[i1] : h; gEvFvgHi[side] = (d == 1) ? l : rbL[i1];
        }
     }
  }

void UpdateSetup(Setup &s, int side, datetime t, double o, double h, double l)
  {
   if(!s.active) return;
   int d = s.dir;
   double hN = Nz(d, d == 1 ? h : l);   // price moving with the trade
   double lN = Nz(d, d == 1 ? l : h);   // price moving against the trade
   // cancel: price breaks A before fill
   if(lN < Nz(d, s.a)) { s.active = false; gEvCancel[side] = 1; return; }
   if(s.i0 != gBar)
     {
      bool     tE  = d == 1 ? pvTop   : pvBot;
      double   tPx = d == 1 ? pvTopPx : pvBotPx;
      long     tI  = d == 1 ? pvTopI  : pvBotI;
      datetime tT  = d == 1 ? pvTopT  : pvBotT;
      bool     bE  = d == 1 ? pvBot   : pvTop;
      double   bPx = d == 1 ? pvBotPx : pvTopPx;
      long     bIx = d == 1 ? pvBotI  : pvTopI;
      datetime bT  = d == 1 ? pvBotT  : pvTopT;
      if(s.stage == 1 && tE && tI >= s.i0 - 1)
        {
         s.b = tPx; s.tB = tT; s.bI = tI; s.stage = 2; s.hasLowB = false; s.hasC = false;
         if(gModeC) gEvArm[side] = 1;
        }
      else if(s.stage == 2 && bE && bIx > s.bI)
        {
         s.c = bPx; s.tC = bT; s.hasC = true; s.stage = 3; s.cBar = bIx;
         // ZO4 data at the C bar (as Bonova f_buildZones)
         s.zHP = (d == 1) ? pvEHDn : pvEHUp;
         s.zProt = (d == 1) ? pvEDnH : pvEUpL;
         s.zProtT = (d == 1) ? pvEDnHT : pvEUpLT;
         s.zOsb = (pvEKl == 1);
         s.zHC = true;                                   // confirm bar = first break after C = this bar
         s.zConf = (d == 1) ? h : l; s.zConfT = t;
         s.zCB = (d == 1) ? (h >= s.zProt) : (l <= s.zProt);
         s.zBrk = (d == 1) ? (pvEH >= s.zProt || h >= s.zProt) : (pvEL <= s.zProt || l <= s.zProt);
         gEvArm[side] = 1;
        }
      if(s.stage >= 2)
        {
         if(!s.hasLowB || lN < s.lowB)
           {
            s.lowB = lN; s.tLowB = t; s.hasLowB = true; s.lowBBar = gBar;
            s.lbHP = (d == 1) ? zHaveDn : zHaveUp;
            s.lbProt = (d == 1) ? zDnH : zUpL;
            s.lbProtT = (d == 1) ? zDnHT : zUpLT;
            s.lbOsb = (gCurKl == 1);
            s.lbHC = false; s.lbConf = 0.0; s.lbConfT = 0; s.lbCB = false;
            s.lbBrk = s.lbHP && ((d == 1) ? (h >= s.lbProt) : (l <= s.lbProt));
           }
         else
           {
            if(!s.lbHC && gCurKl == ((d == 1) ? 2 : 3))
              {
               s.lbHC = true; s.lbConf = (d == 1) ? h : l; s.lbConfT = t;
               s.lbCB = s.lbHP && ((d == 1) ? (h >= s.lbProt) : (l <= s.lbProt));
              }
            if(s.lbHP && ((d == 1) ? (h >= s.lbProt) : (l <= s.lbProt))) s.lbBrk = true;
           }
        }
      // price breaks C before fill: drop C, wait for a new confirmed C
      if(s.stage == 3 && lN < Nz(d, s.c))
        {
         s.hasC = false; s.tC = 0; s.stage = 2; s.zDone = false;
         gEvArm[side] = 1;
        }
      if(s.stage == 2)
        {
         double trg0 = s.b + d * gOffset;
         if(hN >= Nz(d, trg0))
           {
            if(gModeC && s.hasLowB && s.lowB > Nz(d, s.a))
              {
               s.c = (d == 1) ? s.lowB : -s.lowB; s.tC = s.tLowB; s.hasC = true; s.stage = 3; s.cBar = s.lowBBar;   // (c)
               s.zHP = s.lbHP; s.zProt = s.lbProt; s.zProtT = s.lbProtT; s.zOsb = s.lbOsb;
               s.zHC = s.lbHC; s.zConf = s.lbConf; s.zConfT = s.lbConfT; s.zCB = s.lbCB; s.zBrk = s.lbBrk;
              }
            else
              {
               s.stage = 1; s.hasLowB = false;                                                // (a)
              }
           }
        }
     }
   if(s.active && s.stage == 3 && s.hasC) ZoneHook(s, side, t, h, l);
   if(s.active && s.stage == 3)
     {
      double trig = s.b + d * gOffset;
      if(hN >= Nz(d, trig) && s.hasC && Nz(d, s.c) > Nz(d, s.a))
        {
         gEvFill[side] = 1; gEvFillSL[side] = s.c - d * gBuf;
         s.active = false;
        }
     }
  }

// Process one CLOSED bar (oldest to newest)
void ProcessBar(datetime t, double o, double h, double l, double c)
  {
   for(int k = 0; k < 2; k++) { gEvNew[k] = 0; gEvArm[k] = 0; gEvFill[k] = 0; gEvCancel[k] = 0; gEvFillSL[k] = 0.0; gEvFvg[k] = 0; gEvFvgC[k] = 0.0; gEvFvgSid[k] = -1; }
   gNEvZN = 0; gNEvZX = 0; gNEvCh = 0;
   int ri = (int)(gBar % RB);
   rbH[ri] = h; rbL[ri] = l; rbT[ri] = t;
   if(!gInit)
     {
      for(int k = 0; k < 5; k++)
        {
         gX0[k] = t; gY0[k] = c; gXF1[k] = t; gYF1[k] = c; gSX[k] = t; gSY[k] = c;
        }
      gN0 = 5; gNF1 = 5; gNS = 5; gMark = 0.0; gChMark = 0.0;
      gHpPrev = h; gLpPrev = l;
      pvH = h; pvL = l; pvI = gBar; pvT = t; pvPh = -1; pvLast = 4;
      gCurKl = 0;
      pvSKl = 0; pvSHDn = false; pvSDnH = 0.0; pvSDnHT = 0; pvSHUp = false; pvSUpL = 0.0; pvSUpLT = 0;
      ResetSetup(gS[0]); ResetSetup(gS[1]);
      gLastKey[0] = 0; gLastKey[1] = 0;
      zHaveDn = false; zHaveUp = false; zDnH = 0.0; zUpL = 0.0; zDnHT = 0; zUpLT = 0;
      rbDnHT[ri] = 0; rbUpLT[ri] = 0;
      rbKl[ri] = 0; rbHDn[ri] = false; rbHUp[ri] = false; rbDnH[ri] = 0.0; rbUpL[ri] = 0.0;
      gNZ = 0; gZMade[0] = false; gZMade[1] = false; gZC[0] = 0.0; gZC[1] = 0.0;
      gInit = true;
      gBar++;
      return;
     }
   //--- Module 0: Gann swing F0 / F1 / SF1
   double hp = h, lp = l;
   if(h > gHpPrev && l > gLpPrev)       CalcPoints(t, l, h);
   else if(h < gHpPrev && l < gLpPrev)  CalcPoints(t, h, l);
   else if((h >= gHpPrev && l < gLpPrev) || (h > gHpPrev && l <= gLpPrev))
     {
      if(c > o) CalcPoints(t, l, h);
      else      CalcPoints(t, h, l);
     }
   else { hp = gHpPrev; lp = gLpPrev; }
   gHpPrev = hp; gLpPrev = lp;
   //--- Bonova pullback provider (f_class + f_provider)
   pvTop = false; pvBot = false;
   int kl = (h >= pvH && l <= pvL) ? 1 : (h >= pvH) ? 2 : (l <= pvL) ? 3 : 0;
   if(kl == 2) { zHaveUp = true; zUpL = pvL; zUpLT = pvT; }
   else if(kl == 3) { zHaveDn = true; zDnH = pvH; zDnHT = pvT; }
   rbKl[ri] = kl; rbHDn[ri] = zHaveDn; rbDnH[ri] = zDnH; rbHUp[ri] = zHaveUp; rbUpL[ri] = zUpL;
   rbDnHT[ri] = zDnHT; rbUpLT[ri] = zUpLT;
   gCurKl = kl;
   if(kl != 0)
     {
      bool emit = (kl == 2) ? (pvPh != 0 || pvLast == 1) : (kl == 3) ? (pvPh != 1 || pvLast == 1) : false;
      if(emit)
        {
         pvEKl = pvSKl; pvEHDn = pvSHDn; pvEDnH = pvSDnH; pvEDnHT = pvSDnHT;
         pvEHUp = pvSHUp; pvEUpL = pvSUpL; pvEUpLT = pvSUpLT; pvEH = pvH; pvEL = pvL;
         if(kl == 2) { pvBot = true; pvBotPx = pvL; pvBotI = pvI; pvBotT = pvT; }
         else        { pvTop = true; pvTopPx = pvH; pvTopI = pvI; pvTopT = pvT; }
        }
      if(kl == 2 || kl == 3) pvPh = (kl == 2) ? 0 : 1;
      pvLast = kl;
      pvH = h; pvL = l; pvI = gBar; pvT = t;
      pvSKl = kl; pvSHDn = zHaveDn; pvSDnH = zDnH; pvSDnHT = zDnHT; pvSHUp = zHaveUp; pvSUpL = zUpL; pvSUpLT = zUpLT;
     }
   //--- ZO4 zones: break / expiry / FVG entry signal
   ZonesOnBar(t, h, l);
   //--- Module 3: 2 CHoCH (strict)
   if(gNS >= 6)
     {
      double y0 = gSY[0], y1 = gSY[1], y2 = gSY[2], y3 = gSY[3], y4 = gSY[4];
      datetime x0 = gSX[0], x1 = gSX[1], x2 = gSX[2];
      bool patBuy  = y3 < y2 && y1 < y3 && y0 > y2 && y4 > y3 && y4 < y2;
      bool patSell = y3 > y2 && y1 > y3 && y0 < y2 && y4 < y3 && y4 > y2;
      if(patBuy && x1 != gLastKey[0])
        { gLastKey[0] = x1; NewSetup(gS[0], 1, y2, x2, y1, x1, y0, x0); gEvNew[0] = 1; }
      if(patSell && x1 != gLastKey[1])
        { gLastKey[1] = x1; NewSetup(gS[1], -1, y2, x2, y1, x1, y0, x0); gEvNew[1] = 1; }
      UpdateSetup(gS[0], 0, t, o, h, l);
      UpdateSetup(gS[1], 1, t, o, h, l);
     }
   gBar++;
  }

//--- M30 + M5 mode: ZO4 zones of the signal TF, FVG checked on chart (lower TF) bars
//    window: FVG bar 1 inside [zone appear, appear + n signal bars), C broken by any chart bar wick -> zone dead
#define Z5MAX 32
struct Z5
  {
   bool     alive;
   int      dir;
   double   c, top, bot;
   datetime appear;    // close time of the signal bar the zone appeared on
   datetime wend;      // FVG bar 1 must open before this time
   datetime resumeT;   // next FVG bar 1 must open at/after this time
   int      cnt;       // entries taken in this zone
   long     sid;
   long     id;
  };
Z5       gZ5[Z5MAX];
int      gNZ5 = 0;
int      gZ5Max = 2;
double   m5H[3], m5L[3];
datetime m5T[3];
int      gN5 = 0;
// events of the current chart bar
int      gEv5N = 0;
int      gEv5Side[8]; double gEv5C[8]; long gEv5Sid[8]; long gEv5Zid[8]; int gEv5Cnt[8];
datetime gEv5T1[8], gEv5T3[8]; double gEv5Lo[8], gEv5Hi[8];

void Z5Reset() { gNZ5 = 0; gN5 = 0; gEv5N = 0; }

void Z5Add(const Zone &z, int sigPer)
  {
   int idx = -1;
   for(int i = 0; i < gNZ5; i++) if(!gZ5[i].alive) { idx = i; break; }
   if(idx < 0)
     {
      if(gNZ5 < Z5MAX) idx = gNZ5++;
      else
        {
         idx = 0;
         for(int i = 1; i < gNZ5; i++) if(gZ5[i].appear < gZ5[idx].appear) idx = i;
        }
     }
   gZ5[idx].alive = true; gZ5[idx].dir = z.dir; gZ5[idx].c = z.c; gZ5[idx].top = z.top; gZ5[idx].bot = z.bot;
   gZ5[idx].appear = z.created + (datetime)sigPer;
   gZ5[idx].wend = gZ5[idx].appear + (datetime)(gZoneBars * sigPer);
   gZ5[idx].resumeT = gZ5[idx].appear;
   gZ5[idx].cnt = 0; gZ5[idx].sid = z.sid; gZ5[idx].id = z.id;
  }

// one CLOSED chart bar (oldest to newest)
void M5OnBar(datetime t, double h, double l)
  {
   gEv5N = 0;
   if(gN5 < 3) gN5++;
   m5H[0] = m5H[1]; m5L[0] = m5L[1]; m5T[0] = m5T[1];
   m5H[1] = m5H[2]; m5L[1] = m5L[2]; m5T[1] = m5T[2];
   m5H[2] = h; m5L[2] = l; m5T[2] = t;
   for(int i = 0; i < gNZ5; i++)
     {
      if(!gZ5[i].alive) continue;
      if(t < gZ5[i].appear) continue;
      int d = gZ5[i].dir;
      if((d == 1) ? (l < gZ5[i].c) : (h > gZ5[i].c)) { gZ5[i].alive = false; continue; }
      if(gN5 < 3) continue;
      datetime t1 = m5T[0];
      if(t1 >= gZ5[i].wend || gZ5[i].cnt >= gZ5Max) { gZ5[i].alive = false; continue; }
      if(t1 < gZ5[i].resumeT) continue;
      bool touch = (d == 1) ? (m5L[0] <= gZ5[i].top) : (m5H[0] >= gZ5[i].bot);
      bool gap = (d == 1) ? (l > m5H[0]) : (h < m5L[0]);
      if(touch && gap && !gFvgPause)
        {
         gZ5[i].cnt++;
         gZ5[i].resumeT = t + 1;
         if(gEv5N < 8)
           {
            int k = gEv5N++;
            gEv5Side[k] = (d == 1) ? 0 : 1; gEv5C[k] = gZ5[i].c; gEv5Sid[k] = gZ5[i].sid; gEv5Zid[k] = gZ5[i].id; gEv5Cnt[k] = gZ5[i].cnt;
            gEv5T1[k] = t1; gEv5T3[k] = t;
            gEv5Lo[k] = (d == 1) ? m5H[0] : h; gEv5Hi[k] = (d == 1) ? l : m5L[0];
           }
        }
     }
  }
//==================================================================
//==== LOGIC CORE END ==============================================
//==================================================================

//--- trading layer globals
CTrade   trade;
bool     gReady      = false;
datetime gLastBarT   = 0;
int      gDirMode    = 0;          // 0 = both, 1 = BUY ONLY, -1 = SELL ONLY
bool     gHold[2];                 // pending removed intrabar (A broken) until next bar close
bool     gDayBlocked = false;
bool     gNeedSync   = false;
bool     gFvgOn      = false;          // FVG entry on/off (chart button)
bool     gInWarmup   = false;
string   gZObj[];                          // chart objects of zones / FVG boxes (oldest first)
datetime gLastSyncTry = 0;
string   gWhy[2];
double   gLastCv[2];               // last C / temp C notified per side
string   gPrefix     = "G2CH_";
string   gChObj[];                 // CHoCH line objects (oldest first)
bool     gM5Mode     = false;      // M30 + M5 mode active
ENUM_TIMEFRAMES gSigTF = PERIOD_CURRENT;
int      gSigPer     = 1800;
datetime gLast5T     = 0;          // last processed chart bar (M30 + M5 mode)
long     gFvgSid[2];               // setup id that already had an FVG entry (per side)
long     gStopSid[2];              // setup id whose Stop at B already filled (per side)
// partial close sets: 0 = Stop at B, 1 = FVG (signal TF and M5)
bool     gPcOn[2];
double   gPcR[2][3], gPcP[2][3];
int      gPcA[2][3];
string   gGVName     = "";

string SideName(int side) { return side == 0 ? "BUY" : "SELL"; }
double TickSize()  { double t = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE); return t > 0 ? t : _Point; }
double NormP(double p) { double ts = TickSize(); return NormalizeDouble(MathRound(p / ts) * ts, _Digits); }
double Spread() { return SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID); }
double StopsDist() { return (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point; }
string Fmt(double p) { return DoubleToString(p, _Digits); }
string TFName() { return StringSubstr(EnumToString(InpTF == PERIOD_CURRENT ? (ENUM_TIMEFRAMES)_Period : InpTF), 7); }
string ModeName() { return gM5Mode ? TFName() + "+" + StringSubstr(EnumToString((ENUM_TIMEFRAMES)_Period), 7) : TFName(); }
string VolTag(double lot) { return " V" + IntegerToString((long)MathRound(lot * 100.0)); }

void Notify(string msg)
  {
   string m = "2CHoCH " + _Symbol + " " + ModeName() + " | " + msg;
   Print(m);
   if(InpAlert) Alert(m);
   if(InpPush)  SendNotification(m);
  }

//--- lot size
double CalcLot(int side, double price, double sl)
  {
   double minL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0) step = 0.01;
   double lot = InpFixedLot;
   if(InpLotMode != LOT_FIXED)
     {
      double riskMoney = (InpLotMode == LOT_MONEY) ? InpRiskMoney
                         : AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0;
      double pl = 0.0;
      if(!OrderCalcProfit(side == 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, _Symbol, 1.0, price, sl, pl)) return 0.0;
      pl = MathAbs(pl);
      if(pl <= 0.0) return 0.0;
      lot = riskMoney / pl;
     }
   lot = MathFloor(lot / step + 1e-9) * step;
   if(lot < minL - 1e-9)
     {
      if(InpSmallLot == SMALL_SKIP) return 0.0;
      lot = minL;
     }
   lot = MathMin(lot, MathMin(maxL, InpMaxLot));
   int vd = (int)MathMax(0, MathCeil(-MathLog10(step) - 1e-9));
   return NormalizeDouble(lot, vd);
  }

//--- what pending order should exist for this side now
bool Desired(int side, double &price, double &sl, double &tp, double &lot)
  {
   Setup s = gS[side];
   gWhy[side] = "";
   if(!s.active) { gWhy[side] = "no setup"; return false; }
   bool live = (s.stage == 3) || (s.stage == 2 && gModeC && s.hasLowB);
   if(!live) { gWhy[side] = (s.stage == 1) ? "wait B" : "wait C"; return false; }
   if((side == 0 && gDirMode == -1) || (side == 1 && gDirMode == 1)) { gWhy[side] = "blocked by button"; return false; }
   if(gDayBlocked) { gWhy[side] = "daily guard"; return false; }
   if(gDLHit != 0) { gWhy[side] = (gDLHit < 0) ? "daily loss limit hit" : "daily profit target hit"; return false; }
   if(WeekendCloseNow()) { gWhy[side] = "weekend"; return false; }
   if(NoEntryAt(TimeCurrent())) { gWhy[side] = "no-entry window " + InpNoEntryFrom + "-" + InpNoEntryTo; return false; }
   if(gHold[side]) { gWhy[side] = "hold until bar close"; return false; }
   if(!InpStopOn) { gWhy[side] = "Stop orders at B OFF"; return false; }
   if(gStopSid[side] == s.i0) { gWhy[side] = "stop already filled, wait bar close"; return false; }
   if(!InpStopAfterFvg && gFvgSid[side] == s.i0) { gWhy[side] = "setup already had FVG entry"; return false; }
   int d = s.dir;
   double cv = (s.stage == 3) ? s.c : ((d == 1) ? s.lowB : -s.lowB);
   double spr = InpSpreadAdj ? Spread() : 0.0;
   price = s.b + d * InpEntryOffset + ((d == 1) ? spr : 0.0);
   sl    = cv - d * InpSLBuffer + ((d == -1) ? spr : 0.0);
   price = NormP(price); sl = NormP(sl);
   double risk = MathAbs(price - sl);
   if(risk <= 0) { gWhy[side] = "risk 0"; return false; }
   if(InpMaxSL > 0 && risk > InpMaxSL) { gWhy[side] = "SL " + DoubleToString(risk, 2) + " > max"; return false; }
   tp  = NormP(price + d * InpRR * risk);
   lot = CalcLot(side, price, sl);
   if(lot <= 0) { gWhy[side] = "lot < min (skip)"; return false; }
   gWhy[side] = (s.stage == 3) ? "pending" : "pending (SL temp)";
   return true;
  }

double CurCv(int side)
  {
   Setup s = gS[side];
   if(s.stage == 3 && s.hasC) return s.c;
   if(s.hasLowB) return (s.dir == 1) ? s.lowB : -s.lowB;
   return 0.0;
  }

ulong FindOrder(int side, int &count)
  {
   count = 0; ulong found = 0;
   ENUM_ORDER_TYPE want = (side == 0) ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      if(OrderGetInteger(ORDER_MAGIC) != InpMagic) continue;
      if((ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE) != want) continue;
      count++;
      if(found == 0) found = tk;
      else trade.OrderDelete(tk);   // keep only one per side
     }
   return found;
  }

void DrawSide(int side, bool on, double price, double sl)
  {
   string nE = gPrefix + "E" + IntegerToString(side), nS = gPrefix + "S" + IntegerToString(side);
   if(!InpDraw || !on) { ObjectDelete(0, nE); ObjectDelete(0, nS); return; }
   color col = (side == 0) ? clrLime : clrRed;
   if(ObjectFind(0, nE) < 0) ObjectCreate(0, nE, OBJ_HLINE, 0, 0, price);
   ObjectSetDouble(0, nE, OBJPROP_PRICE, price);
   ObjectSetInteger(0, nE, OBJPROP_COLOR, col);
   ObjectSetInteger(0, nE, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetString(0, nE, OBJPROP_TEXT, SideName(side) + " STOP " + Fmt(price));
   if(ObjectFind(0, nS) < 0) ObjectCreate(0, nS, OBJ_HLINE, 0, 0, sl);
   ObjectSetDouble(0, nS, OBJPROP_PRICE, sl);
   ObjectSetInteger(0, nS, OBJPROP_COLOR, clrOrangeRed);
   ObjectSetInteger(0, nS, OBJPROP_STYLE, STYLE_DOT);
   ObjectSetString(0, nS, OBJPROP_TEXT, SideName(side) + " SL " + Fmt(sl));
  }

// returns false if a retry is needed
bool SyncSide(int side, bool quiet)
  {
   int cnt = 0;
   ulong tk = FindOrder(side, cnt);
   double price = 0, sl = 0, tp = 0, lot = 0;
   bool want = Desired(side, price, sl, tp, lot);
   DrawSide(side, want, price, sl);
   if(!want)
     {
      if(tk != 0)
        {
         if(!trade.OrderDelete(tk)) return false;
         if(!quiet) Notify("REMOVED " + SideName(side) + " STOP (" + gWhy[side] + ")");
        }
      return true;
     }
   if(InpMaxSpread > 0 && Spread() > InpMaxSpread) { gWhy[side] = "spread too high"; return false; }
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sd = StopsDist();
   // stop price must be beyond current market, SL/TP at least stops level away
   if(side == 0 && price <= ask + sd) { gWhy[side] = "price already above B"; return false; }
   if(side == 1 && price >= bid - sd) { gWhy[side] = "price already below B"; return false; }
   if(MathAbs(price - sl) < sd || MathAbs(tp - price) < sd) { gWhy[side] = "SL/TP too close"; return false; }
   string cmt = "2CH " + TFName() + " " + (side == 0 ? "B" : "S") + VolTag(lot);
   ENUM_ORDER_TYPE ot = (side == 0) ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP;
   double ts = TickSize();
   if(tk != 0 && OrderSelect(tk))
     {
      double oVol = OrderGetDouble(ORDER_VOLUME_INITIAL);
      double oP = OrderGetDouble(ORDER_PRICE_OPEN), oSL = OrderGetDouble(ORDER_SL), oTP = OrderGetDouble(ORDER_TP);
      if(MathAbs(oVol - lot) > 1e-8)
        {
         if(!trade.OrderDelete(tk)) return false;
         tk = 0;
        }
      else
        {
         double tol = InpSpreadAdj ? MathMax(ts / 2, 0.05) : ts / 2;   // ignore tiny spread changes
         if(MathAbs(oP - price) < tol && MathAbs(oSL - sl) < tol && MathAbs(oTP - tp) < tol) return true;
         if(!trade.OrderModify(tk, price, sl, tp, ORDER_TIME_GTC, 0)) return false;
         double cvNow = CurCv(side);
         if(!quiet && MathAbs(cvNow - gLastCv[side]) >= ts / 2)
            Notify("UPDATED " + SideName(side) + " STOP " + Fmt(price) + " | SL " + Fmt(sl) + " | TP " + Fmt(tp));
         gLastCv[side] = cvNow;
         return true;
        }
     }
   bool ok = (side == 0) ? trade.BuyStop(lot, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, cmt)
                         : trade.SellStop(lot, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, cmt);
   if(!ok) { Print("2CHoCH place failed: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription()); return false; }
   gLastCv[side] = CurCv(side);
   if(!quiet)
      Notify("PLACED " + SideName(side) + " STOP " + Fmt(price) + " | SL " + Fmt(sl) + " | TP " + Fmt(tp) +
             " | lot " + DoubleToString(lot, 2) + (gS[side].stage == 3 ? "" : " (C not confirmed, SL temp)"));
   return true;
  }

void SyncAll(bool quiet)
  {
   bool ok0 = SyncSide(0, quiet);
   bool ok1 = SyncSide(1, quiet);
   gNeedSync = !(ok0 && ok1);
   gLastSyncTry = TimeCurrent();
  }

//--- daily guard
void UpdateDayGuard()
  {
   if(InpMaxTradesDay <= 0) { gDayBlocked = false; return; }
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   datetime d0 = StructToTime(dt);
   if(!HistorySelect(d0, TimeCurrent() + 60)) return;
   int entries = 0; double pnl = 0.0;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong dk = HistoryDealGetTicket(i);
      if(dk == 0) continue;
      if(HistoryDealGetString(dk, DEAL_SYMBOL) != _Symbol) continue;
      if(HistoryDealGetInteger(dk, DEAL_MAGIC) != InpMagic) continue;
      long en = HistoryDealGetInteger(dk, DEAL_ENTRY);
      if(en == DEAL_ENTRY_IN) entries++;
      pnl += HistoryDealGetDouble(dk, DEAL_PROFIT) + HistoryDealGetDouble(dk, DEAL_SWAP)
             + HistoryDealGetDouble(dk, DEAL_COMMISSION) + HistoryDealGetDouble(dk, DEAL_FEE);
     }
   bool block = false;
   if(InpMaxTradesDay > 0 && entries >= InpMaxTradesDay) block = true;
   if(block && !gDayBlocked) Notify("Daily guard ON: no new orders today");
   gDayBlocked = block;
  }

//--- holding-time helpers (server time)
datetime DayStart(datetime t)
  {
   MqlDateTime d; TimeToStruct(t, d);
   d.hour = 0; d.min = 0; d.sec = 0;
   return StructToTime(d);
  }
int CloseSecs()
  {
   string p[];
   if(StringSplit(InpCloseTime, ':', p) == 2)
      return (int)StringToInteger(p[0]) * 3600 + (int)StringToInteger(p[1]) * 60;
   return 23 * 3600 + 30 * 60;
  }
datetime HoldDeadline(datetime openT)
  {
   datetime d = DayStart(openT);
   int added = 0;
   while(added < InpMaxHoldDays - 1)
     {
      d += 86400;
      MqlDateTime m; TimeToStruct(d, m);
      if(m.day_of_week != 0 && m.day_of_week != 6) added++;
     }
   return d + CloseSecs();
  }
int HhmmSecs(string v, int def)
  {
   string p[];
   if(StringSplit(v, ':', p) == 2) return (int)StringToInteger(p[0]) * 3600 + (int)StringToInteger(p[1]) * 60;
   return def;
  }
// true if time t is inside the no-entry window (server time)
bool NoEntryAt(datetime t)
  {
   if(!InpNoEntryOn || t <= 0) return false;
   int f = HhmmSecs(InpNoEntryFrom, 23 * 3600 + 30 * 60), e = HhmmSecs(InpNoEntryTo, 3600);
   if(f == e) return false;
   int sec = (int)(t - DayStart(t));
   return (f < e) ? (sec >= f && sec < e) : (sec >= f || sec < e);
  }
bool gLastNE = false;

bool WeekendCloseNow()
  {
   if(!InpNoWeekend) return false;
   datetime now = TimeCurrent();
   MqlDateTime m; TimeToStruct(now, m);
   return (m.day_of_week == 5 && now >= DayStart(now) + CloseSecs()) || m.day_of_week == 6 || m.day_of_week == 0;
  }
bool TimeUp(datetime openT)
  {
   datetime now = TimeCurrent();
   if(InpMaxHoldDays > 0 && now >= HoldDeadline(openT)) return true;
   if(WeekendCloseNow()) return true;
   if(InpNoWeekend)   // missed the Friday close (EA off): close on Monday
     {
      MqlDateTime m; TimeToStruct(now, m);
      if(m.day_of_week == 1 && openT < DayStart(now) - 2 * 86400) return true;
     }
   return false;
  }

//--- position kind from comment: "2CH M30 B V12" (Stop), "... FB ..." (FVG signal TF), "... 5B ..." (FVG M5)
int PosKind(string pc)
  {
   if(StringFind(pc, " 5B") >= 0 || StringFind(pc, " 5S") >= 0) return 2;
   if(StringFind(pc, " FB") >= 0 || StringFind(pc, " FS") >= 0) return 1;
   return 0;
  }
// initial lot from comment tag " V<lot*100>" (0 = unknown)
double InitLot(string pc)
  {
   int p = StringFind(pc, " V");
   if(p < 0) return 0.0;
   long v = StringToInteger(StringSubstr(pc, p + 2));
   return (v > 0) ? v / 100.0 : 0.0;
  }

// Partial close: at level k (x R) close up to the cumulative % of the initial lot, then apply the SL action.
// Returns true if a trade operation was sent.
bool Partial(ulong tk, int ps, int d, double op, double sl, double tp, double risk, string pc)
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID), ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double cur = (d == 1) ? bid : ask;
   double favR = d * (cur - op) / risk;
   int lvl = -1;
   double cum = 0.0;
   for(int k = 0; k < 3; k++)
     {
      if(gPcR[ps][k] <= 0) break;
      if(favR < gPcR[ps][k] - 1e-9) break;
      lvl = k; cum += gPcP[ps][k] / 100.0;
     }
   if(lvl < 0) return false;
   string who = (d == 1 ? "BUY" : "SELL") + string(" #") + IntegerToString((long)tk);
   //--- volume
   double initV = InitLot(pc);
   if(initV > 0 && cum > 0)
     {
      double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP), minL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      if(step <= 0) step = 0.01;
      double curV = PositionGetDouble(POSITION_VOLUME);
      double target = MathFloor(initV * MathMin(cum, 1.0) / step + 1e-6) * step;   // total closed volume wanted
      double want = target - (initV - curV);
      if(want >= step / 2)
        {
         if(curV - want < minL - 1e-9) want = (cum >= 0.999) ? curV : curV - minL;
         want = MathFloor(want / step + 1e-6) * step;
         if(want >= minL - 1e-9)
           {
            int vd = (int)MathMax(0, MathCeil(-MathLog10(step) - 1e-9));
            want = NormalizeDouble(want, vd);
            if(trade.PositionClosePartial(tk, want))
               Notify("PARTIAL " + who + ": closed " + DoubleToString(want, vd) + " lot at " + DoubleToString(gPcR[ps][lvl], 2) + "R");
            return true;
           }
        }
     }
   //--- SL action of the levels reached
   bool have = false; double best = 0.0;
   for(int k = 0; k <= lvl; k++)
     {
      double x;
      if(gPcA[ps][k] == PCSL_BE) x = op + d * InpBEBuffer;
      else if(gPcA[ps][k] == PCSL_LOCK) x = (k == 0) ? op + d * InpBEBuffer : op + d * gPcR[ps][k - 1] * risk;
      else continue;
      if(!have || d * (x - best) > 0) { best = x; have = true; }
     }
   if(!have) return false;
   double ts = TickSize(), sd = StopsDist();
   double nsl = NormP(best);
   if(sl > 0 && d * (nsl - sl) < ts / 2) return false;           // not better than current SL
   bool ok = (d == 1) ? (nsl <= bid - sd) : (nsl >= ask + sd);
   if(!ok) return false;
   if(trade.PositionModify(tk, nsl, tp))
      Notify("PARTIAL " + who + ": SL -> " + Fmt(nsl) + " (level " + DoubleToString(gPcR[ps][lvl], 2) + "R)");
   return true;
  }

//--- open positions: TP from real fill, break-even, BUY ONLY / SELL ONLY enforcement
void ManagePositions()
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID), ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sd = StopsDist(), ts = TickSize();
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      int d = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      double op = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL), tp = PositionGetDouble(POSITION_TP);
      double cur = (d == 1) ? bid : ask;                       // close price
      //--- prop firm: max holding time / no weekend
      if(TimeUp((datetime)PositionGetInteger(POSITION_TIME)))
        {
         if(trade.PositionClose(tk))
            Notify("TIME CLOSE " + (d == 1 ? "BUY" : "SELL") + " #" + IntegerToString((long)tk) + " (max holding time / weekend)");
         continue;
        }
      string pc = PositionGetString(POSITION_COMMENT);
      int kind = PosKind(pc);                                  // 0 = Stop, 1 = FVG signal TF, 2 = FVG M5
      double rrUse  = (kind == 2) ? InpF5RR   : (kind == 1) ? InpFvgRR   : InpRR;
      bool   beOn   = (kind == 2) ? InpF5BEOn : (kind == 1) ? InpFvgBEOn : InpBEOn;
      double beRUse = (kind == 2) ? InpF5BE_R : (kind == 1) ? InpFvgBE_R : InpBE_R;
      bool slLosing = (sl > 0) && ((d == 1) ? (sl < op) : (sl > op));
      double beSL = NormP(op + d * InpBEBuffer);
      bool atBE = (sl > 0) && ((d == 1) ? (sl >= beSL - ts / 2) : (sl <= beSL + ts / 2));

      //--- blocked direction (BUY ONLY blocks SELL, SELL ONLY blocks BUY)
      bool blocked = (d == 1 && gDirMode == -1) || (d == -1 && gDirMode == 1);
      if(blocked)
        {
         if(atBE) continue;
         bool inLoss = (d == 1) ? (cur <= op) : (cur >= op);
         bool canBE = (d == 1) ? (beSL <= bid - sd) : (beSL >= ask + sd);
         if(inLoss || !canBE)
           {
            if(trade.PositionClose(tk))
               Notify("CLOSED " + (d == 1 ? "BUY" : "SELL") + " #" + IntegerToString((long)tk) + " (blocked by button, " + (inLoss ? "in loss" : "profit too small for BE") + ")");
           }
         else if(trade.PositionModify(tk, beSL, tp))
            Notify("SL to BE " + Fmt(beSL) + " for " + (d == 1 ? "BUY" : "SELL") + " #" + IntegerToString((long)tk) + " (blocked by button)");
         continue;
        }
      //--- 1R: from SL while SL is still on the losing side, else from TP (TP = R:R from the real fill)
      double risk = 0.0;
      if(slLosing) risk = MathAbs(op - sl);
      else if(tp > 0 && rrUse > 0) risk = MathAbs(tp - op) / rrUse;
      if(risk <= 0) continue;
      if(slLosing)
        {
         //--- TP = R:R from the real fill price
         double tpWant = NormP(op + d * rrUse * risk);
         if(MathAbs(tp - tpWant) >= ts / 2)
           {
            bool tpOk = (d == 1) ? (tpWant >= bid + sd) : (tpWant <= ask - sd);
            if(tpOk && trade.PositionModify(tk, sl, tpWant)) tp = tpWant;
           }
        }
      //--- partial close (one trade operation per position per tick)
      int pset = (kind == 0) ? 0 : 1;
      if(gPcOn[pset] && Partial(tk, pset, d, op, sl, tp, risk, pc)) continue;
      if(!slLosing) continue;                                // already at BE or better
      //--- break-even at x R
      if(beOn)
        {
         double prof = (d == 1) ? (bid - op) : (op - ask);
         if(prof >= beRUse * risk)
           {
            bool ok = (d == 1) ? (beSL <= bid - sd) : (beSL >= ask + sd);
            if(ok && trade.PositionModify(tk, beSL, tp))
               Notify("BE: SL -> " + Fmt(beSL) + " for " + (d == 1 ? "BUY" : "SELL") + " #" + IntegerToString((long)tk));
           }
        }
     }
  }

//--- intrabar: price breaks A -> remove pending until bar close (logic cancels at close)
void CheckIntrabar()
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   for(int side = 0; side < 2; side++)
     {
      Setup s = gS[side];
      if(!s.active || gHold[side]) continue;
      bool brokeA = (s.dir == 1) ? (bid < s.a) : (bid > s.a);
      bool brokeC = (!gModeC && s.stage == 3 && s.hasC) && ((s.dir == 1) ? (bid < s.c) : (bid > s.c));
      if(brokeA || brokeC)
        {
         gHold[side] = true;
         SyncSide(side, true);
         Notify(SideName(side) + " setup: price broke " + (brokeA ? "A " + Fmt(s.a) + " -> setup cancelled" : "C " + Fmt(s.c) + " -> wait new C"));
        }
     }
  }

//--- history replay / new bars
bool Warmup()
  {
   ENUM_TIMEFRAMES tf = (InpTF == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : InpTF;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int got = CopyRates(_Symbol, tf, 1, InpWarmupBars, r);
   if(got < 200) return false;
   gInit = false; gBar = 0;
   for(int i = 0; i < ArraySize(gZObj); i++) ObjectsDeleteAll(0, gZObj[i]);
   ArrayResize(gZObj, 0);
   gInWarmup = true;
   Z5Reset();
   gFvgSid[0] = -1; gFvgSid[1] = -1;
   gStopSid[0] = -1; gStopSid[1] = -1;
   for(int q = 0; q < ArraySize(gChObj); q++) ObjectsDeleteAll(0, gChObj[q]);
   ArrayResize(gChObj, 0);
   for(int i = 0; i < got; i++)
     {
      gFvgPause = NoEntryAt(r[i].time + gSigPer);
      ProcessBar(r[i].time, r[i].open, r[i].high, r[i].low, r[i].close);
      AfterSignalBar(false, false);
     }
   gLastBarT = r[got - 1].time;
   RecoverStopFills();
   if(gM5Mode) WarmupChart();
   DrawStructure();
   gInWarmup = false;
   return true;
  }

// true if the deal is the fill of one of this EA's Buy/Sell Stop orders
bool IsStopFillDeal(ulong deal, int &side)
  {
   long ot = -1;
   ulong ord = (ulong)HistoryDealGetInteger(deal, DEAL_ORDER);
   if(ord != 0 && HistoryOrderSelect(ord)) ot = HistoryOrderGetInteger(ord, ORDER_TYPE);
   if(ot == ORDER_TYPE_BUY_STOP)  { side = 0; return true; }
   if(ot == ORDER_TYPE_SELL_STOP) { side = 1; return true; }
   // fallback: comment "2CH <TF> B ..." / "2CH <TF> S ..." (deal comment, else the position comment)
   if(ot < 0)
     {
      string c = HistoryDealGetString(deal, DEAL_COMMENT);
      if(StringFind(c, "2CH ") != 0)
        {
         ulong pid = (ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID);
         if(pid != 0 && PositionSelectByTicket(pid)) c = PositionGetString(POSITION_COMMENT);
        }
      if(PosKind(c) == 0 && StringFind(c, "2CH ") == 0)
        {
         side = (HistoryDealGetInteger(deal, DEAL_TYPE) == DEAL_TYPE_BUY) ? 0 : 1;
         return true;
        }
     }
   return false;
  }

// on start: a Stop at B that filled inside the still-open signal bar is not known to the replay -> read it from history
void RecoverStopFills()
  {
   datetime from = 0;
   for(int side = 0; side < 2; side++)
      if(gS[side].active && (from == 0 || gS[side].tB < from)) from = gS[side].tB;
   if(from == 0) return;
   if(!HistorySelect(from - 60, TimeCurrent() + 60)) return;
   for(int i = 0; i < HistoryDealsTotal(); i++)
     {
      ulong dk = HistoryDealGetTicket(i);
      if(dk == 0) continue;
      if(HistoryDealGetInteger(dk, DEAL_MAGIC) != InpMagic) continue;
      if(HistoryDealGetString(dk, DEAL_SYMBOL) != _Symbol) continue;
      if(HistoryDealGetInteger(dk, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
      int side = -1;
      if(!IsStopFillDeal(dk, side)) continue;
      if(!gS[side].active) continue;
      if((datetime)HistoryDealGetInteger(dk, DEAL_TIME) >= gS[side].tB) gStopSid[side] = gS[side].i0;
     }
  }

// M30 + M5 mode: replay chart bars from the oldest zone that can still trade
void WarmupChart()
  {
   datetime last = iTime(_Symbol, _Period, 1);
   gLast5T = last;
   datetime from = 0;
   for(int i = 0; i < gNZ5; i++)
     {
      if(!gZ5[i].alive) continue;
      if(gZ5[i].wend + 3 * PeriodSeconds(_Period) <= last) { gZ5[i].alive = false; continue; }
      if(from == 0 || gZ5[i].appear < from) from = gZ5[i].appear;
     }
   if(from == 0 || last == 0) return;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int got = CopyRates(_Symbol, _Period, from - 2 * PeriodSeconds(_Period), last, r);
   for(int i = 0; i < got; i++)
     {
      gFvgPause = NoEntryAt(r[i].time + PeriodSeconds(_Period));
      M5OnBar(r[i].time, r[i].high, r[i].low);
      AfterChartBar(false);
     }
  }

// after one signal-TF bar: drawing, M5 zones, FVG bookkeeping, FVG entry (signal TF)
void AfterSignalBar(bool live, bool latest)
  {
   DrawZoneEvents();
   DrawChochEvents();
   if(!live && InpStopOn)                       // replay: the stop of this setup filled on this bar
      for(int side = 0; side < 2; side++)
         if(gEvFill[side] != 0) gStopSid[side] = gS[side].i0;
   if(gM5Mode)
     {
      for(int k = 0; k < gNEvZN; k++) Z5Add(gEvZN[k], gSigPer);
      return;
     }
   for(int side = 0; side < 2; side++)
     {
      if(gEvFvg[side] == 0 || !gFvgOn) continue;
      if(!InpFvgAfterStop && gStopSid[side] == gEvFvgSid[side])
        {
         if(live && latest) Print("2CHoCH FVG ", SideName(side), " skipped: Stop at B of this setup already filled");
         continue;
        }
      if(!live) { gFvgSid[side] = gEvFvgSid[side]; continue; }
      if(latest && OpenFvg(side, gEvFvgC[side], 1)) gFvgSid[side] = gEvFvgSid[side];   // only on the latest closed bar
     }
  }

// after one chart bar (M30 + M5 mode): FVG boxes, FVG entry on M5
void AfterChartBar(bool latest)
  {
   for(int k = 0; k < gEv5N; k++)
     {
      int side = gEv5Side[k];
      DrawFvgBox(gEv5T1[k], gEv5T3[k], gEv5Lo[k], gEv5Hi[k], side, gEv5C[k], " M5 #" + IntegerToString(gEv5Cnt[k]));
      if(!gFvgOn) continue;
      if(!InpFvgAfterStop && gStopSid[side] == gEv5Sid[k])
        {
         if(latest) Print("2CHoCH FVG M5 ", SideName(side), " skipped: Stop at B of this setup already filled");
         continue;
        }
      if(!latest) { gFvgSid[side] = gEv5Sid[k]; continue; }
      if(OpenFvg(side, gEv5C[k], 2)) gFvgSid[side] = gEv5Sid[k];
     }
  }

bool ProcessChartBars()
  {
   if(!gM5Mode) return false;
   datetime t1 = iTime(_Symbol, _Period, 1);
   if(t1 == 0 || t1 <= gLast5T) return false;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int got = CopyRates(_Symbol, _Period, 1, 300, r);
   if(got <= 0) return false;
   for(int i = 0; i < got; i++)
     {
      if(r[i].time <= gLast5T) continue;
      gFvgPause = NoEntryAt(r[i].time + PeriodSeconds(_Period));
      M5OnBar(r[i].time, r[i].high, r[i].low);
      gLast5T = r[i].time;
      AfterChartBar(i == got - 1);
     }
   return true;
  }

//--- FVG entry at ZO4 zone: market order right after bar 3 of the FVG closes
bool OpenFvg(int side, double cPx, int kind)
  {
   string tag = (kind == 2 ? "FVG M5 " : "FVG ") + SideName(side);
   double slBuf = (kind == 2) ? InpF5SLBuffer : InpFvgSLBuffer;
   double rrUse = (kind == 2) ? InpF5RR : InpFvgRR;
   if(!gFvgOn) return false;
   if((side == 0 && gDirMode == -1) || (side == 1 && gDirMode == 1)) { Print("2CHoCH ", tag, " skipped: blocked by button"); return false; }
   if(gDayBlocked) { Notify(tag + " skipped: daily guard"); return false; }
   if(gDLHit != 0) { Notify(tag + " skipped: " + (gDLHit < 0 ? "daily loss limit hit" : "daily profit target hit")); return false; }
   if(WeekendCloseNow()) { Notify(tag + " skipped: weekend"); return false; }
   if(NoEntryAt(TimeCurrent())) { Notify(tag + " skipped: no-entry window"); return false; }
   if(InpMaxSpread > 0 && Spread() > InpMaxSpread) { Notify(tag + " skipped: spread " + DoubleToString(Spread(), 2)); return false; }
   int d = (side == 0) ? 1 : -1;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double price = (d == 1) ? ask : bid;
   double spr = InpSpreadAdj ? Spread() : 0.0;
   double sl = NormP(cPx - d * slBuf + ((d == -1) ? spr : 0.0));
   double risk = MathAbs(price - sl);
   if(((d == 1) ? (sl >= bid) : (sl <= ask)) || risk <= 0) { Notify(tag + " skipped: price already beyond SL"); return false; }
   if(InpMaxSL > 0 && risk > InpMaxSL) { Notify(tag + " skipped: SL " + DoubleToString(risk, 2) + " > max"); return false; }
   double tp = NormP(price + d * rrUse * risk);
   double sd = StopsDist();
   if(MathAbs(price - sl) < sd || MathAbs(tp - price) < sd) { Notify(tag + " skipped: SL/TP too close"); return false; }
   double lot = CalcLot(side, price, sl);
   if(lot <= 0) { Notify(tag + " skipped: lot < min"); return false; }
   string cmt = "2CH " + TFName() + " " + (kind == 2 ? (side == 0 ? "5B" : "5S") : (side == 0 ? "FB" : "FS")) + VolTag(lot);
   bool ok = (side == 0) ? trade.Buy(lot, _Symbol, 0, sl, tp, cmt) : trade.Sell(lot, _Symbol, 0, sl, tp, cmt);
   if(ok) Notify("ENTRY " + tag + " (ZO4 zone at C " + Fmt(cPx) + ") @ " + Fmt(price) + " | SL " + Fmt(sl) + " | TP " + Fmt(tp) + " | lot " + DoubleToString(lot, 2));
   else   Notify(tag + " order failed: " + IntegerToString((int)trade.ResultRetcode()) + " " + trade.ResultRetcodeDescription());
   return ok;
  }

//--- chart drawing of ZO4 zones, C-x marks and FVG boxes (same look as the TradingView indicator)
void ZObjPush(string base)
  {
   int n = ArraySize(gZObj);
   ArrayResize(gZObj, n + 1);
   gZObj[n] = base;
   while(ArraySize(gZObj) > MathMax(1, InpZoneKeep))
     {
      ObjectsDeleteAll(0, gZObj[0]);
      ArrayRemove(gZObj, 0, 1);
     }
  }

void DrawZoneEvents()
  {
   int per = gSigPer;
   for(int k = 0; k < gNEvZN; k++)
     {
      Zone z = gEvZN[k];
      string side = (z.dir == 1) ? "BUY" : "SELL";
      string cs = (z.cs == 2) ? " (case 2)" : (z.cs == 3) ? " (OSB)" : "";
      if(!gInWarmup)
         Print("2CHoCH ZO4 ", side, " zone at C ", Fmt(z.c), ": ", Fmt(z.bot), " - ", Fmt(z.top), cs,
               " | appeared on bar ", TimeToString(z.created), " | FVG bar 1 allowed up to ", InpFvgZoneBars, " bars later");
      if(!InpDrawZones) continue;
      string base = gPrefix + "Z" + IntegerToString(z.id) + "_";
      color col = (z.dir == 1) ? InpZoneClrBuy : InpZoneClrSell;
      datetime tEnd = z.created + (datetime)(InpFvgZoneBars * per);
      string nr = base + "R";
      ObjectCreate(0, nr, OBJ_RECTANGLE, 0, z.left, z.top, tEnd, z.bot);
      ObjectSetInteger(0, nr, OBJPROP_COLOR, col);
      ObjectSetInteger(0, nr, OBJPROP_FILL, true);
      ObjectSetInteger(0, nr, OBJPROP_BACK, true);
      ObjectSetInteger(0, nr, OBJPROP_SELECTABLE, false);
      ObjectSetString(0, nr, OBJPROP_TOOLTIP, "ZO4 " + side + cs + " C " + Fmt(z.c) + " | " + Fmt(z.bot) + " - " + Fmt(z.top));
      string nt = base + "T";
      ObjectCreate(0, nt, OBJ_TEXT, 0, tEnd, (z.dir == 1) ? z.bot : z.top);
      ObjectSetString(0, nt, OBJPROP_TEXT, "ZO4" + cs);
      ObjectSetInteger(0, nt, OBJPROP_COLOR, col);
      ObjectSetInteger(0, nt, OBJPROP_FONTSIZE, 7);
      ObjectSetInteger(0, nt, OBJPROP_ANCHOR, (z.dir == 1) ? ANCHOR_RIGHT_LOWER : ANCHOR_RIGHT_UPPER);
      ObjectSetInteger(0, nt, OBJPROP_SELECTABLE, false);
      ZObjPush(base);
     }
   for(int k = 0; k < gNEvZX; k++)
     {
      Zone z = gEvZX[k];
      if(!gInWarmup) Print("2CHoCH ZO4 ", (z.dir == 1) ? "BUY" : "SELL", " zone at C ", Fmt(z.c), " broken (C-x)");
      if(!InpDrawZones) continue;
      string base = gPrefix + "Z" + IntegerToString(z.id) + "_";
      ObjectDelete(0, base + "R");
      ObjectDelete(0, base + "T");
      string nx = base + "X";
      ObjectCreate(0, nx, OBJ_TEXT, 0, z.tc, z.c);
      ObjectSetString(0, nx, OBJPROP_TEXT, "C-x");
      ObjectSetInteger(0, nx, OBJPROP_COLOR, clrGray);
      ObjectSetInteger(0, nx, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, nx, OBJPROP_ANCHOR, (z.dir == 1) ? ANCHOR_UPPER : ANCHOR_LOWER);
      ObjectSetInteger(0, nx, OBJPROP_SELECTABLE, false);
     }
   if(!gM5Mode)
      for(int side = 0; side < 2; side++)
         if(gEvFvg[side] != 0) DrawFvgBox(gEvFvgT1[side], gEvFvgT3[side], gEvFvgLo[side], gEvFvgHi[side], side, gEvFvgC[side], "");
  }

void DrawFvgBox(datetime t1, datetime t3, double lo, double hi, int side, double cPx, string extra)
  {
   if(!InpDrawZones) return;
   string base = gPrefix + "F" + IntegerToString((long)t3) + "_" + IntegerToString(side) + "_" + DoubleToString(cPx, _Digits) + "_";
   string nf = base + "R";
   ObjectCreate(0, nf, OBJ_RECTANGLE, 0, t1, hi, t3, lo);
   ObjectSetInteger(0, nf, OBJPROP_COLOR, InpFvgClr);
   ObjectSetInteger(0, nf, OBJPROP_FILL, true);
   ObjectSetInteger(0, nf, OBJPROP_BACK, true);
   ObjectSetInteger(0, nf, OBJPROP_SELECTABLE, false);
   ObjectSetString(0, nf, OBJPROP_TOOLTIP, "FVG" + extra + " " + ((side == 0) ? "BUY" : "SELL") + " at ZO4 (C " + Fmt(cPx) + ")");
   ZObjPush(base);
  }

int AliveZones()
  {
   int n = 0;
   for(int i = 0; i < gNZ; i++) if(gZ[i].alive) n++;
   return n;
  }

bool ProcessNewBars()
  {
   ENUM_TIMEFRAMES tf = (InpTF == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : InpTF;
   datetime t1 = iTime(_Symbol, tf, 1);
   if(t1 == 0 || t1 <= gLastBarT) return false;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int got = CopyRates(_Symbol, tf, 1, 300, r);
   if(got <= 0) return false;
   if(r[0].time > gLastBarT)       // gap larger than buffer: rebuild
     {
      Warmup();
      return true;
     }
   for(int i = 0; i < got; i++)
     {
      if(r[i].time <= gLastBarT) continue;
      gFvgPause = NoEntryAt(r[i].time + gSigPer);
      ProcessBar(r[i].time, r[i].open, r[i].high, r[i].low, r[i].close);
      gLastBarT = r[i].time;
      AfterSignalBar(true, i == got - 1);
      for(int side = 0; side < 2; side++)
        {
         if(gEvCancel[side] != 0 && !gHold[side]) Notify(SideName(side) + " setup cancelled (price broke A)");
         if(gEvArm[side] != 0 && gS[side].active)
           {
            Setup s = gS[side];
            Notify(SideName(side) + " setup: B " + Fmt(s.b) + (s.hasC ? " | C " + Fmt(s.c) : " | C not confirmed") + " | A " + Fmt(s.a));
           }
        }
     }
   gHold[0] = false; gHold[1] = false;
   return true;
  }

//--- buttons
void DrawButtons()
  {
   string nb = gPrefix + "BTN_BUY", ns = gPrefix + "BTN_SELL", nf = gPrefix + "BTN_FVG";
   if(ObjectFind(0, nf) < 0) ObjectCreate(0, nf, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, nf, OBJPROP_XDISTANCE, InpBtnX + 210);
   ObjectSetInteger(0, nf, OBJPROP_YDISTANCE, InpBtnY);
   ObjectSetInteger(0, nf, OBJPROP_XSIZE, 100); ObjectSetInteger(0, nf, OBJPROP_YSIZE, 24);
   ObjectSetString(0, nf, OBJPROP_TEXT, gFvgOn ? "FVG: ON" : "FVG: OFF");
   ObjectSetInteger(0, nf, OBJPROP_STATE, gFvgOn);
   ObjectSetInteger(0, nf, OBJPROP_BGCOLOR, gFvgOn ? clrRoyalBlue : clrDimGray);
   ObjectSetInteger(0, nf, OBJPROP_COLOR, clrWhite);
   if(ObjectFind(0, nb) < 0) ObjectCreate(0, nb, OBJ_BUTTON, 0, 0, 0);
   if(ObjectFind(0, ns) < 0) ObjectCreate(0, ns, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, nb, OBJPROP_XDISTANCE, InpBtnX);
   ObjectSetInteger(0, nb, OBJPROP_YDISTANCE, InpBtnY);
   ObjectSetInteger(0, ns, OBJPROP_XDISTANCE, InpBtnX + 105);
   ObjectSetInteger(0, ns, OBJPROP_YDISTANCE, InpBtnY);
   ObjectSetInteger(0, nb, OBJPROP_XSIZE, 100); ObjectSetInteger(0, nb, OBJPROP_YSIZE, 24);
   ObjectSetInteger(0, ns, OBJPROP_XSIZE, 100); ObjectSetInteger(0, ns, OBJPROP_YSIZE, 24);
   ObjectSetString(0, nb, OBJPROP_TEXT, "BUY ONLY");
   ObjectSetString(0, ns, OBJPROP_TEXT, "SELL ONLY");
   ObjectSetInteger(0, nb, OBJPROP_STATE, gDirMode == 1);
   ObjectSetInteger(0, ns, OBJPROP_STATE, gDirMode == -1);
   ObjectSetInteger(0, nb, OBJPROP_BGCOLOR, gDirMode == 1 ? clrGreen : clrDimGray);
   ObjectSetInteger(0, ns, OBJPROP_BGCOLOR, gDirMode == -1 ? clrFireBrick : clrDimGray);
   ObjectSetInteger(0, nb, OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, ns, OBJPROP_COLOR, clrWhite);
   ChartRedraw();
  }

void SetDirMode(int m)
  {
   gDirMode = m;
   GlobalVariableSet(gGVName, (double)m);
   DrawButtons();
   Notify(m == 1 ? "Mode: BUY ONLY" : m == -1 ? "Mode: SELL ONLY" : "Mode: BOTH directions");
   ManagePositions();
   SyncAll(false);
  }

//--- daily limit shared by all 2CHoCH EAs (each EA computes the same total; first hit is latched in a terminal global variable)
int      gDLHit = 0;            // 0 = none, -1 = loss limit hit, +1 = profit target hit (today)
datetime gDLDay = 0;
datetime gDLLast = 0;
double   gDLPnl = 0.0, gDLStartBal = 0.0, gDLLossAmt = 0.0, gDLWinAmt = 0.0;
bool     gDLDirty = true;

bool Is2CH(string c) { return StringFind(c, "2CH ") == 0; }
// selected open position counted in the daily P/L?
bool InScopePos()
  {
   if(Is2CH(PositionGetString(POSITION_COMMENT))) return true;
   if(InpDLScope == DLS_ALL) return true;
   return (InpDLScope == DLS_2CH_MANUAL && PositionGetInteger(POSITION_MAGIC) == 0);
  }
bool IsManualPos() { return PositionGetInteger(POSITION_MAGIC) == 0 && !Is2CH(PositionGetString(POSITION_COMMENT)); }

string DLKey(datetime day)
  {
   MqlDateTime m; TimeToStruct(day, m);
   return "G2CH_DL_" + IntegerToString(m.year * 10000 + m.mon * 100 + m.day);
  }

// realized P/L today (all 2CH positions, all symbols) + floating of open 2CH positions; start-of-day balance
void CalcDayPnl()
  {
   datetime now = TimeCurrent();
   datetime d0 = DayStart(now);
   double realized = 0.0, allToday = 0.0;
   long ids[]; int nIds = 0;
   if(HistorySelect(d0 - 10 * 86400, now + 60))
     {
      int n = HistoryDealsTotal();
      // positions in scope: opened by a 2CH order (entry deal comment, else its order comment),
      // + manual positions (magic 0) or every position, depending on the scope
      for(int i = 0; i < n; i++)
        {
         ulong dk = HistoryDealGetTicket(i);
         if(dk == 0) continue;
         if(HistoryDealGetInteger(dk, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
         long dt = HistoryDealGetInteger(dk, DEAL_TYPE);
         if(dt != DEAL_TYPE_BUY && dt != DEAL_TYPE_SELL) continue;
         string c = HistoryDealGetString(dk, DEAL_COMMENT);
         if(!Is2CH(c))
           {
            ulong ord = (ulong)HistoryDealGetInteger(dk, DEAL_ORDER);
            if(ord != 0 && HistoryOrderSelect(ord)) c = HistoryOrderGetString(ord, ORDER_COMMENT);
           }
         bool inScope = Is2CH(c) || InpDLScope == DLS_ALL ||
                   (InpDLScope == DLS_2CH_MANUAL && HistoryDealGetInteger(dk, DEAL_MAGIC) == 0);
         if(!inScope) continue;
         ArrayResize(ids, nIds + 1); ids[nIds++] = HistoryDealGetInteger(dk, DEAL_POSITION_ID);
        }
      for(int i = 0; i < n; i++)
        {
         ulong dk = HistoryDealGetTicket(i);
         if(dk == 0) continue;
         if((datetime)HistoryDealGetInteger(dk, DEAL_TIME) < d0) continue;
         double v = HistoryDealGetDouble(dk, DEAL_PROFIT) + HistoryDealGetDouble(dk, DEAL_SWAP)
                    + HistoryDealGetDouble(dk, DEAL_COMMISSION) + HistoryDealGetDouble(dk, DEAL_FEE);
         allToday += v;                                   // every deal incl. deposits -> start-of-day balance
         long pid = HistoryDealGetInteger(dk, DEAL_POSITION_ID);
         if(pid == 0) continue;                           // balance / credit operations
         for(int k = 0; k < nIds; k++) if(ids[k] == pid) { realized += v; break; }
        }
     }
   double floating = 0.0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(!InScopePos()) continue;
      floating += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
     }
   gDLPnl = realized + floating;
   gDLStartBal = AccountInfoDouble(ACCOUNT_BALANCE) - allToday;
   gDLLossAmt = (InpDLLoss > 0) ? ((InpDLUnit == DL_PCT) ? gDLStartBal * InpDLLoss / 100.0 : InpDLLoss) : 0.0;
   gDLWinAmt  = (InpDLWin > 0)  ? ((InpDLUnit == DL_PCT) ? gDLStartBal * InpDLWin / 100.0 : InpDLWin) : 0.0;
  }

// close every open position of THIS EA (magic + symbol)
void CloseAllMine(string why)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      int d = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      if(trade.PositionClose(tk))
         Notify("DAILY LIMIT CLOSE " + (d == 1 ? "BUY" : "SELL") + " #" + IntegerToString((long)tk) + " (" + why + ")");
     }
   if(!InpDLCloseManual || InpDLScope == DLS_2CH) return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)           // manual trades, any symbol (another 2CH EA may close it first)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || !IsManualPos()) continue;
      string sym = PositionGetString(POSITION_SYMBOL);
      int d = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      if(trade.PositionClose(tk))
         Notify("DAILY LIMIT CLOSE manual " + sym + " " + (d == 1 ? "BUY" : "SELL") + " #" + IntegerToString((long)tk) + " (" + why + ")");
     }
  }

// returns true if the state changed (entries blocked / unblocked)
bool UpdateDailyLimit()
  {
   if(InpDLLoss <= 0 && InpDLWin <= 0) { bool ch = (gDLHit != 0); gDLHit = 0; return ch; }
   datetime now = TimeCurrent();
   datetime day = DayStart(now);
   bool changed = false;
   if(day != gDLDay)                                      // new server day: limits reset
     {
      if(gDLHit != 0) { Notify("DAILY LIMIT reset (new day): entries allowed again"); changed = true; }
      gDLDay = day; gDLHit = 0; gDLDirty = true;
     }
   if(!gDLDirty && now - gDLLast < 2) return changed;
   gDLDirty = false; gDLLast = now;
   CalcDayPnl();
   string key = DLKey(day);
   int hit = 0;
   if(GlobalVariableCheck(key)) hit = (int)GlobalVariableGet(key);          // already hit by any 2CH EA today
   if(hit == 0)
     {
      if(gDLLossAmt > 0 && gDLPnl <= -gDLLossAmt) hit = -1;
      else if(gDLWinAmt > 0 && gDLPnl >= gDLWinAmt) hit = 1;
      if(hit != 0) GlobalVariableSet(key, hit);
     }
   if(hit != gDLHit)
     {
      gDLHit = hit;
      changed = true;
      Notify(string(hit < 0 ? "DAILY LOSS LIMIT hit" : "DAILY PROFIT TARGET hit") + ": day P/L " +
             DoubleToString(gDLPnl, 2) + " -> no new entries today" +
             (((hit < 0) ? InpDLLossAct : InpDLWinAct) == DL_CLOSE ? ", closing open trades" : ", open trades kept"));
     }
   if(gDLHit != 0 && (((gDLHit < 0) ? InpDLLossAct : InpDLWinAct) == DL_CLOSE))
      CloseAllMine(gDLHit < 0 ? "daily loss limit" : "daily profit target");
   return changed;
  }

string DLText()
  {
   if(InpDLLoss <= 0 && InpDLWin <= 0) return "";
   string t = string(InpDLScope == DLS_2CH ? "Day P/L all 2CH: " : InpDLScope == DLS_2CH_MANUAL ? "Day P/L 2CH+manual: " : "Day P/L account: ")
              + DoubleToString(gDLPnl, 2);
   if(gDLStartBal > 0) t += " (" + DoubleToString(100.0 * gDLPnl / gDLStartBal, 2) + "%)";
   if(gDLLossAmt > 0) t += "   loss limit -" + DoubleToString(gDLLossAmt, 2) + (InpDLLossAct == DL_CLOSE ? " [close]" : " [keep]");
   if(gDLWinAmt > 0)  t += "   target +" + DoubleToString(gDLWinAmt, 2) + (InpDLWinAct == DL_CLOSE ? " [close]" : " [keep]");
   if(gDLHit != 0) t += (gDLHit < 0 ? "   >> LOSS LIMIT HIT: no new entries today" : "   >> TARGET HIT: no new entries today");
   return t + "\n";
  }

//--- Gann SF1 swings (signal TF) and A / B / C labels of the current setups
void DrawSwings()
  {
   string pf = gPrefix + "W_";
   ObjectsDeleteAll(0, pf);
   if(!InpDrawSwing) return;
   int n = MathMin(gNS, MathMin(GMAX, MathMax(2, InpSwingKeep) + 1));
   int seg = 0;
   for(int k = 0; k + 1 < n; k++)
     {
      if(gSX[k + 1] == gSX[k]) continue;                  // start-up copies of the first bar
      string nm = pf + IntegerToString(seg++);
      ObjectCreate(0, nm, OBJ_TREND, 0, gSX[k + 1], gSY[k + 1], gSX[k], gSY[k]);
      ObjectSetInteger(0, nm, OBJPROP_COLOR, InpSwingClr);
      ObjectSetInteger(0, nm, OBJPROP_WIDTH, InpSwingWidth);
      ObjectSetInteger(0, nm, OBJPROP_STYLE, InpSwingStyle);
      ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_BACK, true);
      ObjectSetString(0, nm, OBJPROP_TOOLTIP, "Gann SF1 " + Fmt(gSY[k + 1]) + " -> " + Fmt(gSY[k]));
     }
  }

void DrawChochEvents()
  {
   if(!InpDrawChoch) return;
   for(int k = 0; k < gNEvCh; k++)
     {
      string nm = gPrefix + "CH_" + IntegerToString((long)gEvChX2[k]) + "_" + IntegerToString(k);
      color c = (gEvChDir[k] > 0) ? InpChochUpClr : InpChochDnClr;
      ObjectCreate(0, nm, OBJ_TREND, 0, gEvChX1[k], gEvChY[k], gEvChX2[k], gEvChY[k]);
      ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
      ObjectSetInteger(0, nm, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetInteger(0, nm, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_BACK, true);
      ObjectSetString(0, nm, OBJPROP_TOOLTIP, string(gEvChDir[k] > 0 ? "CHoCH up (broke top) " : "CHoCH down (broke bottom) ") + Fmt(gEvChY[k]));
      string nt = nm + "T";
      ObjectCreate(0, nt, OBJ_TEXT, 0, gEvChX2[k], gEvChY[k]);
      ObjectSetString(0, nt, OBJPROP_TEXT, "CHoCH");
      ObjectSetInteger(0, nt, OBJPROP_COLOR, c);
      ObjectSetInteger(0, nt, OBJPROP_FONTSIZE, 7);
      ObjectSetInteger(0, nt, OBJPROP_ANCHOR, gEvChDir[k] > 0 ? ANCHOR_LEFT_LOWER : ANCHOR_LEFT_UPPER);
      ObjectSetInteger(0, nt, OBJPROP_SELECTABLE, false);
      int n = ArraySize(gChObj);
      ArrayResize(gChObj, n + 1);
      gChObj[n] = nm;
      while(ArraySize(gChObj) > MathMax(1, InpChochKeep))
        {
         ObjectsDeleteAll(0, gChObj[0]);
         ArrayRemove(gChObj, 0, 1);
        }
     }
  }

void AbcText(string nm, datetime t, double p, string txt, color c, bool above, string tip)
  {
   if(ObjectFind(0, nm) < 0) ObjectCreate(0, nm, OBJ_TEXT, 0, t, p);
   ObjectMove(0, nm, 0, t, p);
   ObjectSetString(0, nm, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, InpABCFont);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, above ? ANCHOR_LOWER : ANCHOR_UPPER);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetString(0, nm, OBJPROP_TOOLTIP, tip);
  }

void DrawABC()
  {
   for(int side = 0; side < 2; side++)
     {
      string pf = gPrefix + "L" + IntegerToString(side) + "_";
      ObjectsDeleteAll(0, pf);
      Setup s = gS[side];
      if(!InpDrawABC || !s.active) continue;
      int d = s.dir;
      color col = (d == 1) ? InpABCBuyClr : InpABCSellClr;
      string nB = (d == 1) ? "Buy" : "Sell", nO = (d == 1) ? "Sell" : "Buy";
      // BUY: A Sell is a top (label above), A Buy a bottom (below), B a top, C a bottom
      AbcText(pf + "AS", s.tAS, s.aS, "A " + nO, clrSilver, d == 1, "CHoCH level " + Fmt(s.aS) + " (A " + nO + ")");
      AbcText(pf + "A", s.tA, s.a, "A " + nB + " = B " + nO, col, d != 1, "A " + nB + " " + Fmt(s.a) + " (setup cancelled if broken)");
      if(s.stage >= 2) AbcText(pf + "B", s.tB, s.b, "B " + nB, col, d == 1, "B " + nB + " " + Fmt(s.b) + " -> stop " + Fmt(s.b + d * gOffset));
      if(s.stage == 3 && s.hasC) AbcText(pf + "C", s.tC, s.c, "C " + nB, col, d != 1, "C " + nB + " " + Fmt(s.c) + " (SL " + Fmt(s.c - d * gBuf) + ")");
      else if(s.stage == 2 && gModeC && s.hasLowB)
        {
         double cv = (d == 1) ? s.lowB : -s.lowB;
         AbcText(pf + "C", s.tLowB, cv, "C? " + nB, col, d != 1, "C not confirmed yet: lowest since B " + Fmt(cv));
        }
     }
  }

void DrawStructure() { DrawSwings(); DrawABC(); }

void UpdatePanel()
  {
   string txt = "2CHoCH EA  " + _Symbol + " " + ModeName() + "   mode: " +
                (gDirMode == 1 ? "BUY ONLY" : gDirMode == -1 ? "SELL ONLY" : "BOTH") +
                (gDayBlocked ? "   [DAILY GUARD]" : "") + "\n\n\n" + DLText();
   for(int side = 0; side < 2; side++)
     {
      Setup s = gS[side];
      txt += SideName(side) + ": ";
      if(!s.active) txt += "-";
      else
        {
         txt += "A " + Fmt(s.a);
         if(s.stage >= 2) txt += "  B " + Fmt(s.b);
         if(s.hasC) txt += "  C " + Fmt(s.c);
         else if(s.stage == 2 && s.hasLowB) txt += "  lowB " + Fmt(s.dir == 1 ? s.lowB : -s.lowB);
        }
      txt += "  [" + gWhy[side] + "]\n";
     }
   //--- orders / positions owned by this EA (same symbol + magic)
   txt += "FVG entry: " + (gFvgOn ? "ON" : "OFF") + (gM5Mode ? " (on " + StringSubstr(EnumToString((ENUM_TIMEFRAMES)_Period), 7) + " bars, max " + IntegerToString(gZ5Max) + "/zone)" : "") +
          "   ZO4 zones alive: " + IntegerToString(AliveZones()) + (InpStopOn ? "" : "   Stop at B: OFF") + (InpNoEntryOn ? (NoEntryAt(TimeCurrent()) ? "   NO-ENTRY NOW" : "   No-entry " + InpNoEntryFrom + "-" + InpNoEntryTo) : "") + (InpStopAfterFvg ? "" : "   Stop skipped after FVG") + (InpFvgAfterStop ? "" : "   FVG skipped after Stop") +
          (gPcOn[0] || gPcOn[1] ? "   Partial: " + (gPcOn[0] ? "Stop " : "") + (gPcOn[1] ? "FVG" : "") : "") + "\n";
   txt += "\nMagic " + IntegerToString(InpMagic) + " - orders of this EA:\n";
   int nOwn = 0;
   for(int i = 0; i < PositionsTotal(); i++)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      nOwn++;
      txt += "  POS " + (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "BUY " : "SELL ") +
             DoubleToString(PositionGetDouble(POSITION_VOLUME), 2) + " @ " + Fmt(PositionGetDouble(POSITION_PRICE_OPEN)) +
             "  SL " + Fmt(PositionGetDouble(POSITION_SL)) + "  TP " + Fmt(PositionGetDouble(POSITION_TP)) +
             "  #" + IntegerToString((long)tk) + "  (" + PositionGetString(POSITION_COMMENT) + ")\n";
     }
   for(int i = 0; i < OrdersTotal(); i++)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0 || OrderGetString(ORDER_SYMBOL) != _Symbol || OrderGetInteger(ORDER_MAGIC) != InpMagic) continue;
      nOwn++;
      txt += "  PENDING " + ((ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE) == ORDER_TYPE_BUY_STOP ? "BUY STOP " : "SELL STOP ") +
             DoubleToString(OrderGetDouble(ORDER_VOLUME_INITIAL), 2) + " @ " + Fmt(OrderGetDouble(ORDER_PRICE_OPEN)) +
             "  SL " + Fmt(OrderGetDouble(ORDER_SL)) + "  TP " + Fmt(OrderGetDouble(ORDER_TP)) +
             "  #" + IntegerToString((long)tk) + "\n";
     }
   if(nOwn == 0) txt += "  (none)\n";
   Comment(txt);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   gModeC = (InpNoC == NOC_ENTER);
   gSigTF = (InpTF == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : InpTF;
   gSigPer = PeriodSeconds(gSigTF);
   gM5Mode = InpM5Mode && PeriodSeconds((ENUM_TIMEFRAMES)_Period) < gSigPer;
   if(InpM5Mode && !gM5Mode)
      Print("2CHoCH WARNING: M30 + M5 mode needs a chart TF lower than the Signal TF (e.g. chart M5, Signal TF M30). Mode is OFF.");
   gZ5Max = MathMax(1, InpF5MaxPerZone);
   gFvgSid[0] = -1; gFvgSid[1] = -1;
   gStopSid[0] = -1; gStopSid[1] = -1;
   gPcOn[0] = InpPcS_On; gPcOn[1] = InpPcF_On;
   gPcR[0][0] = InpPcS_R1; gPcP[0][0] = InpPcS_P1; gPcA[0][0] = (int)InpPcS_A1;
   gPcR[0][1] = InpPcS_R2; gPcP[0][1] = InpPcS_P2; gPcA[0][1] = (int)InpPcS_A2;
   gPcR[0][2] = InpPcS_R3; gPcP[0][2] = InpPcS_P3; gPcA[0][2] = (int)InpPcS_A3;
   gPcR[1][0] = InpPcF_R1; gPcP[1][0] = InpPcF_P1; gPcA[1][0] = (int)InpPcF_A1;
   gPcR[1][1] = InpPcF_R2; gPcP[1][1] = InpPcF_P2; gPcA[1][1] = (int)InpPcF_A2;
   gPcR[1][2] = InpPcF_R3; gPcP[1][2] = InpPcF_P3; gPcA[1][2] = (int)InpPcF_A3;
   gZoneBars = InpFvgZoneBars;
   gFvgOn = InpFvgOn;
   gOffset = InpEntryOffset;
   gBuf = InpSLBuffer;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(50);
   if((ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
      Print("2CHoCH WARNING: account is not HEDGING. EA is designed for hedging accounts.");
   gGVName = "G2CH_" + _Symbol + "_" + IntegerToString(InpMagic);
   gDirMode = GlobalVariableCheck(gGVName) ? (int)GlobalVariableGet(gGVName) : 0;
   gHold[0] = false; gHold[1] = false;
   gWhy[0] = ""; gWhy[1] = "";
   gLastCv[0] = 0.0; gLastCv[1] = 0.0;
   DrawButtons();
   gReady = Warmup();
   if(gReady) { UpdateDayGuard(); SyncAll(true); }
   EventSetTimer(2);
   UpdatePanel();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   ObjectsDeleteAll(0, gPrefix);
   Comment("");
  }

void OnTick()
  {
   if(!gReady)
     {
      gReady = Warmup();
      if(!gReady) return;
      UpdateDayGuard();
      SyncAll(true);
     }
   bool nb = ProcessNewBars();
   bool nc = ProcessChartBars();
   bool ne = NoEntryAt(TimeCurrent());
   bool neChg = (ne != gLastNE);
   if(neChg)
     {
      gLastNE = ne;
      Notify(ne ? "NO-ENTRY window started (" + InpNoEntryFrom + "-" + InpNoEntryTo + "): pending stops removed, open trades still managed"
                : "NO-ENTRY window ended: entries allowed again");
     }
   bool dlChg = UpdateDailyLimit();
   static datetime lastPanel = 0;
   if(nb) DrawStructure();
   if(nb || nc || neChg || dlChg) { UpdateDayGuard(); SyncAll(false); UpdatePanel(); lastPanel = TimeCurrent(); }
   else
     {
      if(gNeedSync && TimeCurrent() - gLastSyncTry >= 2) SyncAll(false);
      if((InpDLLoss > 0 || InpDLWin > 0) && TimeCurrent() - lastPanel >= 5) { UpdatePanel(); lastPanel = TimeCurrent(); }
     }
   CheckIntrabar();
   ManagePositions();
  }

void OnTimer()
  {
   if(!gReady) return;
   UpdatePanel();
  }

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(id != CHARTEVENT_OBJECT_CLICK) return;
   if(sparam == gPrefix + "BTN_BUY")  SetDirMode(gDirMode == 1 ? 0 : 1);
   if(sparam == gPrefix + "BTN_SELL") SetDirMode(gDirMode == -1 ? 0 : -1);
   if(sparam == gPrefix + "BTN_FVG")
     {
      gFvgOn = !gFvgOn;
      DrawButtons();
      Notify(gFvgOn ? "FVG entry: ON" : "FVG entry: OFF");
      UpdatePanel();
     }
  }

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic) return;
   if(HistoryDealGetString(trans.deal, DEAL_SYMBOL) != _Symbol) return;
   long en = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   long ty = HistoryDealGetInteger(trans.deal, DEAL_TYPE);
   double px = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
   if(en == DEAL_ENTRY_IN)
     {
      int side = -1;
      if(IsStopFillDeal(trans.deal, side) && gS[side].active)
        {
         gStopSid[side] = gS[side].i0;              // do not place this setup's stop again before the bar closes
         SyncSide(side, true);
        }
      Notify("FILLED " + (ty == DEAL_TYPE_BUY ? "BUY" : "SELL") + " @ " + Fmt(px));
     }
   else if(en == DEAL_ENTRY_OUT || en == DEAL_ENTRY_INOUT)
     {
      long rs = HistoryDealGetInteger(trans.deal, DEAL_REASON);
      double pr = HistoryDealGetDouble(trans.deal, DEAL_PROFIT) + HistoryDealGetDouble(trans.deal, DEAL_SWAP)
                  + HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
      string why = (rs == DEAL_REASON_TP) ? "TP" : (rs == DEAL_REASON_SL) ? (pr >= 0 ? "SL at BE" : "SL") : "CLOSE";
      Notify(why + " @ " + Fmt(px) + " | P/L " + DoubleToString(pr, 2));
     }
   UpdateDayGuard();
   gDLDirty = true;
  }
//+------------------------------------------------------------------+
