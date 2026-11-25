//+------------------------------------------------------------------+
//|                                          Gann2CHoCH_Signals.mq5   |
//|  Indicator version of Gann2CHoCH_EA: same logic, signals only.   |
//|  - CHoCH + A : Gann Swing SF1 ; B / C : Bonova pullback points   |
//|  - Pending Buy/Sell Stop at B, SL = C -/+ buffer, TP = R:R       |
//|  - ZO4 zone at C (Bonova f_buildZones), C-x, FVG entry           |
//|  - Partial close levels, BE, statistics                          |
//|  - M30 + M5 mode: zones from Signal TF, FVG on chart bars        |
//|  Signals are evaluated on CLOSED bars (no repaint). ASCII source.|
//+------------------------------------------------------------------+
#property copyright "Gann 2CHoCH"
#property version   "1.15"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- enums
enum ENUM_NOC_MODE
  {
   NOC_ENTER = 0,   // (c) Enter anyway, C = lowest low since B
   NOC_DROP  = 1    // (a) Drop B, wait for next confirmed top
  };
enum ENUM_PC_SL
  {
   PCSL_KEEP = 0,   // Keep SL
   PCSL_BE   = 1,   // Move SL to break-even
   PCSL_LOCK = 2    // Move SL to previous level (level 1 -> BE)
  };
//--- inputs
input group "=== Setup 2 CHoCH ==="
input ENUM_TIMEFRAMES InpTF          = PERIOD_CURRENT; // Signal timeframe (M30 + M5 mode: M30)
input ENUM_NOC_MODE   InpNoC         = NOC_ENTER;      // Price breaks B before C is confirmed
input double          InpEntryOffset = 0.10;           // Stop beyond B (price units)
input double          InpSLBuffer    = 3.0;            // SL buffer beyond C (price units)
input double          InpRR          = 2.5;            // TP R:R  1 : x (stop entry)
input bool            InpBEOn        = true;           // Stop entry: move SL to break-even
input double          InpBE_R        = 1.0;            // ... when profit reaches x R
input double          InpBEBuffer    = 0.3;            // BE buffer (price units)
input bool            InpStopAfterFvg= true;           // Also take Stop at B when the setup already had an FVG entry
input int             InpBars        = 5000;           // History bars of the Signal TF to calculate

input group "=== FVG entry at ZO4 zone (C) ==="
input bool            InpFvgOn       = true;           // Show FVG entry signals
input int             InpFvgZoneBars = 20;             // Zone valid for n Signal TF bars (FVG bar 1 must be inside)
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

input group "=== Partial close: Stop entries at B ==="
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

input group "=== Drawing (common) ==="
input bool            InpDrawSetups  = true;           // Current setups: A / B / C, pending stop, SL / TP
input bool            InpDrawTrades  = true;           // Signals: entry arrow, SL / TP lines, result
input bool            InpTradeText   = true;           // Text "BUY 2CH E .. SL .. TP .." at each signal
input bool            InpDrawLevels  = true;           // Partial close levels (lines + marks)
input int             InpKeepTrades  = 40;             // Keep last n signals on chart
input bool            InpDrawZones   = true;           // ZO4 zones / C-x / FVG boxes
input int             InpZoneKeep    = 30;             // Keep last n zones / FVG boxes
input bool            InpDrawSwing   = true;           // Main / M30 layer: draw SF1 swing
input int             InpSwingKeep   = 40;             // Keep last n SF1 swings (max 60)
input bool            InpDrawChoch   = true;           // Main / M30 layer: draw CHoCH lines of SF1
input int             InpChochKeep   = 30;             // Keep last n CHoCH lines (per layer)
input color           InpChochUpClr  = clrDeepSkyBlue; // CHoCH color: broke a top (main / M30 layer)
input color           InpChochDnClr  = clrHotPink;     // CHoCH color: broke a bottom (main / M30 layer)
input color           InpSLClr       = clrOrangeRed;   // SL color
input color           InpTPClr       = clrDeepSkyBlue; // TP color
input color           InpPcClr       = clrGold;        // Partial level color
input bool            InpStats       = true;           // Show statistics (top-left)

input group "=== Style: main layer (M30 layer in M30 + M5 mode) ==="
input color           InpBuyClr      = clrLimeGreen;   // BUY color (labels, lines)
input color           InpSellClr     = clrTomato;      // SELL color (labels, lines)
input int             InpFontSize    = 8;              // Text size
input color           InpZoneClrBuy  = C'0,90,60';     // Zone fill BUY
input color           InpZoneClrSell = C'110,30,30';   // Zone fill SELL
input color           InpZoneBordBuy = clrLimeGreen;   // Zone border BUY
input color           InpZoneBordSell= clrTomato;      // Zone border SELL
input int             InpZoneBordW   = 1;              // Zone border width (0 = no border)
input ENUM_LINE_STYLE InpZoneBordSt  = STYLE_SOLID;    // Zone border style
input color           InpFvgClr      = C'30,60,140';   // FVG box color
input color           InpSwingClr    = clrOrange;      // SF1 swing color
input int             InpSwingWidth  = 2;              // SF1 swing width

input group "=== M5 layer (M30 + M5 mode): setups / zones / FVG of the chart TF itself ==="
input bool            InpL5On        = true;           // Show M5 layer (A/B/C, Buy/Sell Stop at B, ZO4, FVG of M5)
input bool            InpL5Fvg       = true;           // M5 layer: FVG entry signals at M5 zones
input bool            InpL5Alert     = true;           // M5 layer: alerts
input color           InpL5BuyClr    = C'120,200,150'; // BUY color (labels, lines)
input color           InpL5SellClr   = C'230,150,140'; // SELL color (labels, lines)
input int             InpL5FontSize  = 7;              // Text size
input color           InpL5ZoneBuy   = C'25,60,45';    // Zone fill BUY
input color           InpL5ZoneSell  = C'70,35,35';    // Zone fill SELL
input color           InpL5BordBuy   = C'120,200,150'; // Zone border BUY
input color           InpL5BordSell  = C'230,150,140'; // Zone border SELL
input int             InpL5BordW     = 1;              // Zone border width (0 = no border)
input ENUM_LINE_STYLE InpL5BordSt    = STYLE_DOT;      // Zone border style
input color           InpL5FvgClr    = C'40,55,90';    // FVG box color
input bool            InpL5Swing     = true;           // M5 layer: draw its own SF1 swing (dotted)
input color           InpL5SwingClr  = C'200,160,90';  // SF1 swing color (M5)
input int             InpL5SwingWidth= 1;              // SF1 swing width (M5)
input bool            InpL5Choch     = true;           // M5 layer: draw its own CHoCH lines

input group "=== Alerts ==="
input bool            InpAlert       = true;           // Popup alert (main / M30 layer)
input bool            InpPush        = false;          // Push notification (MT5 mobile)

//==================================================================
//==== LOGIC CORE (same logic as the EA core, wrapped in a class so two engines can run) ====
#define GMAX 64
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
#define RB 2048
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

class CEng
  {
public:
   datetime gX0[GMAX];
   double gY0[GMAX];
   int gN0;
   datetime gXF1[GMAX];
   double gYF1[GMAX];
   int gNF1;
   datetime gSX[GMAX];
   double gSY[GMAX];
   int gNS;
   double gMark;
   double gChMark;
   int gNEvCh;
   datetime gEvChX1[4], gEvChX2[4];
   double gEvChY[4];
   int gEvChDir[4];
   bool gInit;
   double gHpPrev, gLpPrev;
   long gBar;
   double pvH, pvL;
   long pvI;
   datetime pvT;
   int pvPh;
   int pvLast;
   bool pvTop, pvBot;
   double pvTopPx, pvBotPx;
   long pvTopI, pvBotI;
   datetime pvTopT, pvBotT;
   Setup gS[2];
   datetime gLastKey[2];
   bool gModeC;
   double gOffset;
   double gBuf;
   int gEvNew[2], gEvArm[2], gEvFill[2], gEvCancel[2];
   double gEvFillSL[2];
   double rbH[RB], rbL[RB], rbDnH[RB], rbUpL[RB];
   datetime rbT[RB], rbDnHT[RB], rbUpLT[RB];
   datetime zDnHT, zUpLT;
   int gCurKl;
   int pvSKl;
   bool pvSHDn, pvSHUp;
   double pvSDnH, pvSUpL;
   datetime pvSDnHT, pvSUpLT;
   int pvEKl;
   bool pvEHDn, pvEHUp;
   double pvEDnH, pvEUpL;
   datetime pvEDnHT, pvEUpLT;
   double pvEH, pvEL;
   long gZoneId;
   int rbKl[RB];
   bool rbHDn[RB], rbHUp[RB];
   bool zHaveDn, zHaveUp;
   double zDnH, zUpL;
   Zone gZ[ZMAX];
   int gNZ;
   bool gZMade[2];
   double gZC[2];
   int gZoneBars;
   bool gFvgPause;
   int gEvFvg[2];
   double gEvFvgC[2];
   datetime gEvFvgT1[2], gEvFvgT3[2];
   double gEvFvgLo[2], gEvFvgHi[2];
   long gEvFvgSid[2];
   Zone gEvZN[4];
   int gNEvZN;
   Zone gEvZX[32];
   int gNEvZX;
   Z5 gZ5[Z5MAX];
   int gNZ5;
   int gZ5Max;
   double m5H[3], m5L[3];
   datetime m5T[3];
   int gN5;
   int gEv5N;
   int gEv5Side[8];
   double gEv5C[8];
   long gEv5Sid[8];
   long gEv5Zid[8];
   int gEv5Cnt[8];
   datetime gEv5T1[8], gEv5T3[8];
   double gEv5Lo[8], gEv5Hi[8];

   void Init()
     {
      ZeroMemory(gX0);
      ZeroMemory(gY0);
      ZeroMemory(gXF1);
      ZeroMemory(gYF1);
      ZeroMemory(gSX);
      ZeroMemory(gSY);
      ZeroMemory(gEvChX1);
      ZeroMemory(gEvChX2);
      ZeroMemory(gEvChY);
      ZeroMemory(gEvChDir);
      ZeroMemory(gS);
      ZeroMemory(gLastKey);
      ZeroMemory(gEvNew);
      ZeroMemory(gEvArm);
      ZeroMemory(gEvFill);
      ZeroMemory(gEvCancel);
      ZeroMemory(gEvFillSL);
      ZeroMemory(rbH);
      ZeroMemory(rbL);
      ZeroMemory(rbDnH);
      ZeroMemory(rbUpL);
      ZeroMemory(rbT);
      ZeroMemory(rbDnHT);
      ZeroMemory(rbUpLT);
      ZeroMemory(rbKl);
      ZeroMemory(rbHDn);
      ZeroMemory(rbHUp);
      ZeroMemory(gZ);
      ZeroMemory(gZMade);
      ZeroMemory(gZC);
      ZeroMemory(gEvFvg);
      ZeroMemory(gEvFvgC);
      ZeroMemory(gEvFvgT1);
      ZeroMemory(gEvFvgT3);
      ZeroMemory(gEvFvgLo);
      ZeroMemory(gEvFvgHi);
      ZeroMemory(gEvFvgSid);
      ZeroMemory(gEvZN);
      ZeroMemory(gEvZX);
      ZeroMemory(gZ5);
      ZeroMemory(m5H);
      ZeroMemory(m5L);
      ZeroMemory(m5T);
      ZeroMemory(gEv5Side);
      ZeroMemory(gEv5C);
      ZeroMemory(gEv5Sid);
      ZeroMemory(gEv5Zid);
      ZeroMemory(gEv5Cnt);
      ZeroMemory(gEv5T1);
      ZeroMemory(gEv5T3);
      ZeroMemory(gEv5Lo);
      ZeroMemory(gEv5Hi);
      gN0 = 0;
      gNF1 = 0;
      gNS = 0;
      gMark = 0.0;
      gChMark = 0.0;
      gNEvCh = 0;
      gInit = false;
      gHpPrev = 0.0;
      gLpPrev = 0.0;
      gBar = 0;
      pvH = 0.0;
      pvL = 0.0;
      pvI = 0;
      pvT = 0;
      pvPh = -1;
      pvLast = 4;
      pvTop = false;
      pvBot = false;
      pvTopPx = 0.0;
      pvBotPx = 0.0;
      pvTopI = 0;
      pvBotI = 0;
      pvTopT = 0;
      pvBotT = 0;
      gModeC = true;
      gOffset = 0.10;
      gBuf = 3.0;
      zDnHT = 0;
      zUpLT = 0;
      gCurKl = 0;
      pvSKl = 0;
      pvSHDn = false;
      pvSHUp = false;
      pvSDnH = 0.0;
      pvSUpL = 0.0;
      pvSDnHT = 0;
      pvSUpLT = 0;
      pvEKl = 0;
      pvEHDn = false;
      pvEHUp = false;
      pvEDnH = 0.0;
      pvEUpL = 0.0;
      pvEDnHT = 0;
      pvEUpLT = 0;
      pvEH = 0.0;
      pvEL = 0.0;
      gZoneId = 0;
      zHaveDn = false;
      zHaveUp = false;
      zDnH = 0.0;
      zUpL = 0.0;
      gNZ = 0;
      gZoneBars = 20;
      gFvgPause = false;
      gNEvZN = 0;
      gNEvZX = 0;
      gNZ5 = 0;
      gZ5Max = 2;
      gN5 = 0;
      gEv5N = 0;
     }
   CEng() { Init(); }

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
  };

//==================================================================
//==== INDICATOR LAYER (drawing, simulated trades, alerts) =========
//==== Two engines: gE[0] = main / M30 layer, gE[1] = M5 layer =====
//==================================================================
CEng     gE[2];
string   gP = "G2CI_";               // object prefix
bool     gHist = true;               // true while processing history (no alerts)
int      gNext = 0;                  // next chart bar index to process
datetime gLastProcT = 0;
string   gObjQ[];                    // zone / FVG objects (oldest first)
string   gTrQ[];                     // trade objects (oldest first)
string   gChQ[];                     // CHoCH line objects (oldest first)
// signal TF feed (Signal TF higher than chart TF)
bool     gFeed = false;              // main layer bars come from another (higher) TF
bool     gM5 = false;                // M30 + M5 mode
bool     gL5 = false;                // M5 layer active
ENUM_TIMEFRAMES gSigTF = PERIOD_CURRENT;
int      gSigPer = 0, gChPer = 0;
MqlRates gSR[];
int      gSRp = 0;
datetime gLastSigT = 0;
long     gFvgSid[2][2];              // [layer][side] setup id that already had an FVG entry
// partial close sets: 0 = Stop, 1 = FVG
bool     gPcOn[2];
double   gPcR[2][3], gPcP[2][3];
int      gPcA[2][3];

struct LStyle
  {
   color buy, sell, zFillB, zFillS, zBordB, zBordS, fvg, swing;
   int   fs, bw, sw;
   ENUM_LINE_STYLE bs;
   string tag;
   bool  alert;
   int   per;            // bar seconds of this layer's engine
  };
LStyle   gSt[2];

struct Trade
  {
   bool     open;
   int      lay;       // 0 = main / M30, 1 = M5 layer
   int      dir;
   int      kind;      // 0 = Stop at B, 1 = FVG (zone TF), 2 = FVG M5 on M30 zone
   datetime t;
   double   e, sl, tp, risk, rr;
   bool     beOn; double beR; bool beDone;
   int      nxt;       // next partial level
   double   got, rem;  // R banked by partial closes, fraction still open
   int      seg;       // current SL segment number
   long     id;
  };
Trade    gTr[];
long     gTrId = 0;
// statistics [layer][class]: class 0 = Stop, 1 = FVG
int      gStN[2][2], gStTP[2][2], gStSL[2][2], gStBE[2][2], gStW[2][2];
double   gStR[2][2];

string KindName(int kind) { return (kind == 0) ? " 2CH" : (kind == 1) ? " FVG" : " FVG-M5"; }
string TfS(ENUM_TIMEFRAMES tf) { return StringSubstr(EnumToString(tf), 7); }
string ModeName()
  {
   string s = TfS(gSigTF);
   if(gFeed) s += (gM5 ? "+" : " on ") + TfS((ENUM_TIMEFRAMES)_Period);
   return s;
  }

void QPush(string &q[], string base, int keep)
  {
   int n = ArraySize(q);
   ArrayResize(q, n + 1);
   q[n] = base;
   while(ArraySize(q) > MathMax(1, keep))
     {
      ObjectsDeleteAll(0, q[0]);
      ArrayRemove(q, 0, 1);
     }
  }

string Fp(double p) { return DoubleToString(p, _Digits); }

void Say(int L, string msg)
  {
   if(gHist || !gSt[L].alert) return;
   string m = "2CHoCH " + _Symbol + " " + ((L == 0) ? ModeName() : TfS((ENUM_TIMEFRAMES)_Period)) + gSt[L].tag + " | " + msg;
   Alert(m);
   if(InpPush) SendNotification(m);
   Print(m);
  }

void MkText(string nm, datetime t, double p, string txt, color c, int fs, ENUM_ANCHOR_POINT anc, string tip = "")
  {
   if(ObjectFind(0, nm) < 0) ObjectCreate(0, nm, OBJ_TEXT, 0, t, p);
   ObjectMove(0, nm, 0, t, p);
   ObjectSetString(0, nm, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, fs);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, anc);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   if(tip != "") ObjectSetString(0, nm, OBJPROP_TOOLTIP, tip);
  }

void MkSeg(string nm, datetime t1, double p1, datetime t2, double p2, color c, ENUM_LINE_STYLE st, int w)
  {
   if(ObjectFind(0, nm) < 0) ObjectCreate(0, nm, OBJ_TREND, 0, t1, p1, t2, p2);
   ObjectMove(0, nm, 0, t1, p1);
   ObjectMove(0, nm, 1, t2, p2);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
   ObjectSetInteger(0, nm, OBJPROP_STYLE, st);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, w);
   ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_BACK, true);
  }

void MkBox(string nm, datetime t1, double p1, datetime t2, double p2, color c, string tip)
  {
   if(ObjectFind(0, nm) < 0) ObjectCreate(0, nm, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
   ObjectSetInteger(0, nm, OBJPROP_FILL, true);
   ObjectSetInteger(0, nm, OBJPROP_BACK, true);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetString(0, nm, OBJPROP_TOOLTIP, tip);
  }

void MkFrame(string nm, datetime t1, double p1, datetime t2, double p2, color c, int w, ENUM_LINE_STYLE st)
  {
   if(w <= 0) return;
   if(ObjectFind(0, nm) < 0) ObjectCreate(0, nm, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
   ObjectSetInteger(0, nm, OBJPROP_FILL, false);
   ObjectSetInteger(0, nm, OBJPROP_BACK, false);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, w);
   ObjectSetInteger(0, nm, OBJPROP_STYLE, st);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
  }

string TBase(long id) { return gP + "T" + IntegerToString(id) + "_"; }
string LP(int L) { return gP + "L" + IntegerToString(L) + "_"; }

//--- new simulated trade (signal)
void OpenTrade(int L, int dir, int kind, datetime t, double e, double sl, string extra = "")
  {
   double risk = MathAbs(e - sl);
   if(risk <= 0 || (dir == 1 ? e <= sl : e >= sl)) return;
   int n = ArraySize(gTr);
   ArrayResize(gTr, n + 1);
   double rr = (kind == 0) ? InpRR : (kind == 1) ? InpFvgRR : InpF5RR;
   gTr[n].open = true; gTr[n].lay = L; gTr[n].dir = dir; gTr[n].kind = kind; gTr[n].t = t;
   gTr[n].e = e; gTr[n].sl = sl; gTr[n].risk = risk; gTr[n].rr = rr; gTr[n].tp = e + dir * rr * risk;
   gTr[n].beOn = (kind == 0) ? InpBEOn : (kind == 1) ? InpFvgBEOn : InpF5BEOn;
   gTr[n].beR  = (kind == 0) ? InpBE_R : (kind == 1) ? InpFvgBE_R : InpF5BE_R;
   gTr[n].beDone = false; gTr[n].nxt = 0; gTr[n].got = 0.0; gTr[n].rem = 1.0;
   gTr[n].seg = 0; gTr[n].id = ++gTrId;
   string side = (dir == 1) ? "BUY" : "SELL";
   string kn = KindName(kind) + extra + gSt[L].tag;
   string base = TBase(gTrId);
   color col = (dir == 1) ? gSt[L].buy : gSt[L].sell;
   int per = gChPer;
   int ps = (kind == 0) ? 0 : 1;
   if(InpDrawTrades)
     {
      string na = base + "A";
      ObjectCreate(0, na, (dir == 1) ? OBJ_ARROW_BUY : OBJ_ARROW_SELL, 0, t, e);
      ObjectSetInteger(0, na, OBJPROP_COLOR, col);
      ObjectSetInteger(0, na, OBJPROP_WIDTH, 2);
      ObjectSetInteger(0, na, OBJPROP_SELECTABLE, false);
      MkSeg(base + "E", t, e, t + per, e, col, STYLE_SOLID, 1);
      MkSeg(base + "S0", t, sl, t + per, sl, InpSLClr, STYLE_DOT, 1);
      MkSeg(base + "P", t, gTr[n].tp, t + per, gTr[n].tp, InpTPClr, STYLE_DOT, 1);
      if(gPcOn[ps] && InpDrawLevels)
         for(int k = 0; k < 3; k++)
           {
            if(gPcR[ps][k] <= 0) break;
            double px = e + dir * gPcR[ps][k] * risk;
            MkSeg(base + "L" + IntegerToString(k), t, px, t + per, px, InpPcClr, STYLE_DOT, 1);
            MkText(base + "LT" + IntegerToString(k), t, px, DoubleToString(gPcR[ps][k], 1) + "R " + DoubleToString(gPcP[ps][k], 0) + "%",
                   InpPcClr, gSt[L].fs - 1, ANCHOR_RIGHT);
           }
      if(InpTradeText)
         MkText(base + "TX", t, sl, side + kn + "  E " + Fp(e) + "  SL " + Fp(sl) + "  TP " + Fp(gTr[n].tp),
                col, gSt[L].fs - 1, (dir == 1) ? ANCHOR_LEFT_UPPER : ANCHOR_LEFT_LOWER);
      QPush(gTrQ, base, InpKeepTrades);
     }
   Say(L, ((kind == 0) ? "FILLED " : "ENTRY ") + side + KindName(kind) + extra + " @ " + Fp(e) + " | SL " + Fp(sl) + " | TP " + Fp(gTr[n].tp) +
       " (1:" + DoubleToString(rr, 1) + ")");
  }

void CloseTrade(int k, datetime t, double px, double r, bool byTP)
  {
   gTr[k].open = false;
   int L = gTr[k].lay;
   int c = (gTr[k].kind == 0) ? 0 : 1;
   gStN[L][c]++; gStR[L][c] += r;
   if(r > 0.001) gStW[L][c]++;
   string res;
   if(byTP) { gStTP[L][c]++; res = "TP"; }
   else if(r < -0.05) { gStSL[L][c]++; res = "SL"; }
   else { gStBE[L][c]++; res = (r > 0.05) ? "SL +" + DoubleToString(r, 1) + "R" : "BE"; }
   int d = gTr[k].dir;
   string base = TBase(gTr[k].id);
   color rc = byTP ? InpTPClr : (r < -0.05 ? InpSLClr : InpPcClr);
   if(InpDrawTrades)
      MkText(base + "R", t, px, res + gSt[L].tag, rc, gSt[L].fs,
             byTP ? ((d == 1) ? ANCHOR_LOWER : ANCHOR_UPPER) : ((d == 1) ? ANCHOR_UPPER : ANCHOR_LOWER));
   Say(L, res + " " + ((d == 1) ? "BUY" : "SELL") + KindName(gTr[k].kind) + " (entry " + Fp(gTr[k].e) + ") result " +
       (r >= 0 ? "+" : "") + DoubleToString(r, 2) + "R");
  }

//--- check open trades on a closed chart bar: SL first, then partial levels, TP, BE (same order as the backtest)
void UpdateTrades(datetime t, double h, double l)
  {
   int n = ArraySize(gTr);
   for(int k = 0; k < n; k++)
     {
      if(!gTr[k].open || gTr[k].t >= t) continue;
      int d = gTr[k].dir;
      int L = gTr[k].lay;
      double e = gTr[k].e, R = gTr[k].risk;
      int ps = (gTr[k].kind == 0) ? 0 : 1;
      string base = TBase(gTr[k].id);
      if(InpDrawTrades)
        {
         ObjectMove(0, base + "E", 1, t, e);
         ObjectMove(0, base + "S" + IntegerToString(gTr[k].seg), 1, t, gTr[k].sl);
         ObjectMove(0, base + "P", 1, t, gTr[k].tp);
         for(int j = 0; j < 3; j++)
            if(ObjectFind(0, base + "L" + IntegerToString(j)) >= 0)
               ObjectMove(0, base + "L" + IntegerToString(j), 1, t, ObjectGetDouble(0, base + "L" + IntegerToString(j), OBJPROP_PRICE, 1));
        }
      bool hitSL = (d == 1) ? (l <= gTr[k].sl) : (h >= gTr[k].sl);
      if(hitSL)
        {
         CloseTrade(k, t, gTr[k].sl, gTr[k].got + gTr[k].rem * d * (gTr[k].sl - e) / R, false);
         continue;
        }
      double favR = d * (((d == 1) ? h : l) - e) / R;
      double newsl = gTr[k].sl;
      while(gPcOn[ps] && gTr[k].nxt < 3 && gPcR[ps][gTr[k].nxt] > 0 && favR >= gPcR[ps][gTr[k].nxt])
        {
         int j = gTr[k].nxt;
         double fr = MathMin(gPcP[ps][j] / 100.0, gTr[k].rem);
         gTr[k].got += fr * gPcR[ps][j];
         gTr[k].rem -= fr;
         if(gPcA[ps][j] == PCSL_BE) newsl = e + d * InpBEBuffer;
         else if(gPcA[ps][j] == PCSL_LOCK) newsl = (j == 0) ? e + d * InpBEBuffer : e + d * gPcR[ps][j - 1] * R;
         gTr[k].nxt++;
         if(InpDrawTrades && InpDrawLevels)
            MkText(base + "PX" + IntegerToString(j), t, e + d * gPcR[ps][j] * R, "P" + IntegerToString(j + 1), InpPcClr, gSt[L].fs - 1,
                   (d == 1) ? ANCHOR_LOWER : ANCHOR_UPPER, "Partial close " + DoubleToString(fr * 100.0, 0) + "% at " + DoubleToString(gPcR[ps][j], 1) + "R");
         Say(L, "PARTIAL " + ((d == 1) ? "BUY" : "SELL") + KindName(gTr[k].kind) + " (entry " + Fp(e) + "): close " +
             DoubleToString(fr * 100.0, 0) + "% at " + DoubleToString(gPcR[ps][j], 1) + "R");
        }
      if(gTr[k].rem <= 1e-9)
        {
         CloseTrade(k, t, e + d * gPcR[ps][gTr[k].nxt - 1] * R, gTr[k].got, true);
         continue;
        }
      if(favR >= gTr[k].rr)
        {
         CloseTrade(k, t, gTr[k].tp, gTr[k].got + gTr[k].rem * gTr[k].rr, true);
         continue;
        }
      if(gTr[k].beOn && !gTr[k].beDone && favR >= gTr[k].beR)
        {
         double b = e + d * InpBEBuffer;
         if(d * (b - newsl) > 0) newsl = b;
         gTr[k].beDone = true;
        }
      if(d * (newsl - gTr[k].sl) > 0)
        {
         gTr[k].sl = newsl;
         gTr[k].seg++;
         if(InpDrawTrades) MkSeg(base + "S" + IntegerToString(gTr[k].seg), t, newsl, t, newsl, InpSLClr, STYLE_DOT, 1);
        }
     }
   int w = 0;
   for(int k = 0; k < n; k++) if(gTr[k].open) { if(w != k) gTr[w] = gTr[k]; w++; }
   ArrayResize(gTr, w);
  }

//--- zones, C-x, FVG boxes of the bar just processed by engine L
void DrawZoneEvents(int L, bool fvgBoxes)
  {
   int per = gSt[L].per;
   for(int k = 0; k < gE[L].gNEvZN; k++)
     {
      Zone z = gE[L].gEvZN[k];
      string side = (z.dir == 1) ? "BUY" : "SELL";
      string cs = (z.cs == 2) ? " (case 2)" : (z.cs == 3) ? " (OSB)" : "";
      if(!InpDrawZones) continue;
      string base = LP(L) + "Z" + IntegerToString(z.id) + "_";
      color fill = (z.dir == 1) ? gSt[L].zFillB : gSt[L].zFillS;
      color bord = (z.dir == 1) ? gSt[L].zBordB : gSt[L].zBordS;
      datetime tEnd = z.created + (datetime)(InpFvgZoneBars * per);
      MkBox(base + "R", z.left, z.top, tEnd, z.bot, fill, "ZO4" + gSt[L].tag + " " + side + cs + " | C " + Fp(z.c) + " | " + Fp(z.bot) + " - " + Fp(z.top));
      MkFrame(base + "B", z.left, z.top, tEnd, z.bot, bord, gSt[L].bw, gSt[L].bs);
      MkText(base + "T", tEnd, (z.dir == 1) ? z.bot : z.top, "ZO4" + gSt[L].tag + cs, bord, gSt[L].fs - 1, (z.dir == 1) ? ANCHOR_RIGHT_LOWER : ANCHOR_RIGHT_UPPER);
      QPush(gObjQ, base, InpZoneKeep);
     }
   for(int k = 0; k < gE[L].gNEvZX; k++)
     {
      Zone z = gE[L].gEvZX[k];
      if(!InpDrawZones) continue;
      string base = LP(L) + "Z" + IntegerToString(z.id) + "_";
      ObjectDelete(0, base + "R");
      ObjectDelete(0, base + "B");
      ObjectDelete(0, base + "T");
      MkText(base + "X", z.tc, z.c, "C-x" + gSt[L].tag, clrGray, gSt[L].fs, (z.dir == 1) ? ANCHOR_UPPER : ANCHOR_LOWER, "ZO4 zone broken at C " + Fp(z.c));
     }
   if(fvgBoxes)
      for(int side = 0; side < 2; side++)
         if(gE[L].gEvFvg[side] != 0) DrawFvg(L, gE[L].gEvFvgT1[side], gE[L].gEvFvgT3[side], gE[L].gEvFvgLo[side], gE[L].gEvFvgHi[side], side, gE[L].gEvFvgC[side], "");
  }

void DrawFvg(int L, datetime t1, datetime t3, double lo, double hi, int side, double cPx, string extra)
  {
   if(!InpDrawZones) return;
   string base = LP(L) + "F" + IntegerToString((long)t3) + "_" + IntegerToString(side) + "_" + DoubleToString(cPx, _Digits) + "_";
   MkBox(base + "R", t1, hi, t3, lo, gSt[L].fvg, "FVG" + extra + gSt[L].tag + " " + ((side == 0) ? "BUY" : "SELL") + " at ZO4 (C " + Fp(cPx) + ")");
   QPush(gObjQ, base, InpZoneKeep);
  }

//--- current setups of engine L: points A / B / C, pending stop, expected SL / TP
void DrawSetups(int L, datetime tNow)
  {
   int per = gChPer;
   datetime tR = tNow + (datetime)((8 + 22 * L) * per);
   int fs = gSt[L].fs;
   string tg = gSt[L].tag;
   for(int side = 0; side < 2; side++)
     {
      string b = LP(L) + "S" + IntegerToString(side) + "_";
      ObjectsDeleteAll(0, b);
      if(L == 1 && !gL5) continue;
      Setup s = gE[L].gS[side];
      if(!s.active || !InpDrawSetups) continue;
      int d = s.dir;
      color col = (d == 1) ? gSt[L].buy : gSt[L].sell;
      string nB = (d == 1) ? "Buy" : "Sell", nO = (d == 1) ? "Sell" : "Buy";
      ENUM_ANCHOR_POINT up = ANCHOR_LOWER, dn = ANCHOR_UPPER;
      MkText(b + "AS", s.tAS, s.aS, "A " + nO + tg, clrGray, fs, (d == 1) ? up : dn);
      MkText(b + "A", s.tA, s.a, "B " + nO + " = A " + nB + tg, col, fs, (d == 1) ? dn : up);
      if(s.stage < 2) continue;
      MkText(b + "B", s.tB, s.b, "B " + nB + tg, col, fs, (d == 1) ? up : dn);
      double trg = s.b + d * gE[L].gOffset;
      bool waitC = (s.stage == 2 && !gE[L].gModeC);
      bool skip = (!InpStopAfterFvg && gFvgSid[L][side] == s.i0);
      MkSeg(b + "E", s.tB, trg, tR, trg, col, (waitC || skip) ? STYLE_DOT : STYLE_DASH, 1);
      MkText(b + "ET", tR, trg, ((d == 1) ? "BUY STOP" : "SELL STOP") + tg + " " + Fp(trg) + (waitC ? " (wait C)" : "") + (skip ? " (skip: FVG done)" : ""),
             col, fs - 1, ANCHOR_LEFT);
      double cv = 0.0; bool haveCv = false; datetime tc = 0;
      if(s.stage == 3 && s.hasC) { cv = s.c; haveCv = true; tc = s.tC; MkText(b + "C", s.tC, s.c, "C " + nB + tg, col, fs, (d == 1) ? dn : up); }
      else if(gE[L].gModeC && s.hasLowB)
        {
         cv = (d == 1) ? s.lowB : -s.lowB; haveCv = true; tc = s.tLowB;
         MkText(b + "C", s.tLowB, cv, "C? " + nB + tg, col, fs, (d == 1) ? dn : up, "C not confirmed yet: lowest since B " + Fp(cv));
        }
      if(!haveCv) continue;
      double sl = cv - d * gE[L].gBuf;
      double risk = MathAbs(trg - sl);
      MkSeg(b + "S", tc, sl, tR, sl, InpSLClr, STYLE_DOT, 1);
      MkText(b + "ST", tR, sl, ((s.stage == 3) ? "SL" : "SL temp") + tg + " " + Fp(sl), InpSLClr, fs - 1, ANCHOR_LEFT);
      if(risk > 0)
        {
         double tp = trg + d * InpRR * risk;
         MkSeg(b + "P", s.tB, tp, tR, tp, InpTPClr, STYLE_DOT, 1);
         MkText(b + "PT", tR, tp, "TP" + tg + " " + Fp(tp) + " (1:" + DoubleToString(InpRR, 1) + ")", InpTPClr, fs - 1, ANCHOR_LEFT);
         if(gPcOn[0] && InpDrawLevels)
            for(int k = 0; k < 3; k++)
              {
               if(gPcR[0][k] <= 0) break;
               double px = trg + d * gPcR[0][k] * risk;
               MkSeg(b + "L" + IntegerToString(k), s.tB, px, tR, px, InpPcClr, STYLE_DOT, 1);
               MkText(b + "LT" + IntegerToString(k), tR, px, DoubleToString(gPcR[0][k], 1) + "R " + DoubleToString(gPcP[0][k], 0) + "%", InpPcClr, fs - 1, ANCHOR_LEFT);
              }
        }
     }
  }

//--- Gann SF1 swings of engine L (the swings its setups use)
void DrawSwings(int L)
  {
   string pf = LP(L) + "W_";
   ObjectsDeleteAll(0, pf);
   if(L == 0 ? !InpDrawSwing : (!gL5 || !InpL5Swing)) return;
   int n = MathMin(gE[L].gNS, MathMin(GMAX, MathMax(2, InpSwingKeep) + 1));
   int seg = 0;
   for(int k = 0; k + 1 < n; k++)
     {
      if(gE[L].gSX[k + 1] == gE[L].gSX[k]) continue;      // start-up copies of the first bar
      string nm = pf + IntegerToString(seg++);
      MkSeg(nm, gE[L].gSX[k + 1], gE[L].gSY[k + 1], gE[L].gSX[k], gE[L].gSY[k], gSt[L].swing, (L == 0) ? STYLE_SOLID : STYLE_DOT, (L == 0) ? gSt[L].sw : 1);
      ObjectSetString(0, nm, OBJPROP_TOOLTIP, "Gann SF1" + gSt[L].tag + " " + Fp(gE[L].gSY[k + 1]) + " -> " + Fp(gE[L].gSY[k]));
     }
  }

//--- CHoCH lines of SF1 found on the bar just processed by engine L
void DrawChoch(int L)
  {
   if(L == 0 ? !InpDrawChoch : !InpL5Choch) return;
   for(int k = 0; k < gE[L].gNEvCh; k++)
     {
      int dir = gE[L].gEvChDir[k];
      color c = (L == 0) ? (dir > 0 ? InpChochUpClr : InpChochDnClr) : (dir > 0 ? gSt[1].buy : gSt[1].sell);
      string nm = LP(L) + "CH" + IntegerToString((long)gE[L].gEvChX2[k]) + "_" + IntegerToString(k) + "_";
      MkSeg(nm + "L", gE[L].gEvChX1[k], gE[L].gEvChY[k], gE[L].gEvChX2[k], gE[L].gEvChY[k], c, STYLE_DASH, 1);
      ObjectSetString(0, nm + "L", OBJPROP_TOOLTIP, string(dir > 0 ? "CHoCH up (broke top) " : "CHoCH down (broke bottom) ") + Fp(gE[L].gEvChY[k]) + gSt[L].tag);
      MkText(nm + "T", gE[L].gEvChX2[k], gE[L].gEvChY[k], "CHoCH" + gSt[L].tag, c, MathMax(6, gSt[L].fs - 2), dir > 0 ? ANCHOR_LEFT_LOWER : ANCHOR_LEFT_UPPER);
      int n = ArraySize(gChQ);
      ArrayResize(gChQ, n + 1);
      gChQ[n] = nm;
      while(ArraySize(gChQ) > MathMax(1, InpChochKeep) * 2)
        {
         ObjectsDeleteAll(0, gChQ[0]);
         ArrayRemove(gChQ, 0, 1);
        }
     }
  }

void EngInit(int L)
  {
   gE[L].Init();
   gE[L].gModeC = (InpNoC == NOC_ENTER);
   gE[L].gOffset = InpEntryOffset;
   gE[L].gBuf = InpSLBuffer;
   gE[L].gZoneBars = InpFvgZoneBars;
   gE[L].gZ5Max = MathMax(1, InpF5MaxPerZone);
  }

void ResetAll()
  {
   ObjectsDeleteAll(0, gP);
   ArrayResize(gObjQ, 0); ArrayResize(gTrQ, 0); ArrayResize(gTr, 0); ArrayResize(gChQ, 0);
   for(int L = 0; L < 2; L++)
      for(int c = 0; c < 2; c++) { gStN[L][c] = 0; gStTP[L][c] = 0; gStSL[L][c] = 0; gStBE[L][c] = 0; gStW[L][c] = 0; gStR[L][c] = 0.0; }
   EngInit(0); EngInit(1);
   for(int L = 0; L < 2; L++) { gFvgSid[L][0] = -1; gFvgSid[L][1] = -1; }
   ArrayResize(gSR, 0); gSRp = 0; gLastSigT = 0;
   gHist = true;
  }

//--- one CLOSED bar for engine L (L = 0: signal TF bar, L = 1: chart bar of the M5 layer)
void ProcessSig(int L, datetime t, double o, double h, double l, double c)
  {
   gE[L].ProcessBar(t, o, h, l, c);
   // FVG at the zone of this engine's own TF (main layer: not in M30 + M5 mode)
   bool fvgOn = (L == 0) ? (InpFvgOn && !gM5) : (InpL5Fvg);
   for(int side = 0; side < 2; side++)
     {
      int d = (side == 0) ? 1 : -1;
      if(gE[L].gEvCancel[side] != 0) Say(L, ((d == 1) ? "BUY" : "SELL") + " setup cancelled (price broke A)");
      if(gE[L].gEvArm[side] != 0 && gE[L].gS[side].active)
        {
         Setup s = gE[L].gS[side];
         Say(L, ((d == 1) ? "BUY STOP " : "SELL STOP ") + Fp(s.b + d * gE[L].gOffset) + (s.hasC ? " | SL " + Fp(s.c - d * gE[L].gBuf) : " | C not confirmed") + " | A " + Fp(s.a));
        }
      if(gE[L].gEvFvg[side] != 0 && fvgOn)
        {
         gFvgSid[L][side] = gE[L].gEvFvgSid[side];
         OpenTrade(L, d, 1, t, c, gE[L].gEvFvgC[side] - d * InpFvgSLBuffer);
        }
      if(gE[L].gEvFill[side] != 0)
        {
         Setup s = gE[L].gS[side];
         if(!InpStopAfterFvg && gFvgSid[L][side] == s.i0)
            Say(L, ((d == 1) ? "BUY" : "SELL") + " stop at B skipped (setup already had an FVG entry)");
         else
           {
            double trig = s.b + d * gE[L].gOffset;
            double e = (d == 1) ? MathMax(trig, o) : MathMin(trig, o);
            OpenTrade(L, d, 0, t, e, s.c - d * gE[L].gBuf);
           }
        }
     }
   if(L == 0 && gM5) for(int k = 0; k < gE[0].gNEvZN; k++) gE[0].Z5Add(gE[0].gEvZN[k], gSigPer);
   DrawZoneEvents(L, fvgOn);
   if(L == 0 || (gL5 && InpL5Choch)) DrawChoch(L);
  }

//--- feed signal bars (main layer) that closed by time "upto"
bool FeedSignal(datetime upto)
  {
   while(true)
     {
      if(gSRp >= ArraySize(gSR))
        {
         datetime stop = upto - gSigPer;
         if(stop < gLastSigT + 1) break;
         MqlRates tmp[];
         int n = CopyRates(_Symbol, gSigTF, gLastSigT + 1, stop, tmp);
         if(n <= 0) break;
         ArrayResize(gSR, n);
         for(int k = 0; k < n; k++) gSR[k] = tmp[k];
         gSRp = 0;
        }
      if(gSR[gSRp].time + gSigPer > upto) break;
      if(gSR[gSRp].time > gLastSigT)
        {
         ProcessSig(0, gSR[gSRp].time, gSR[gSRp].open, gSR[gSRp].high, gSR[gSRp].low, gSR[gSRp].close);
         gLastSigT = gSR[gSRp].time;
        }
      gSRp++;
     }
   return true;
  }

//--- one CLOSED chart bar
void ProcessChart(int i, const datetime &time[], const double &open[], const double &high[], const double &low[], const double &close[])
  {
   UpdateTrades(time[i], high[i], low[i]);
   if(!gFeed)
     {
      ProcessSig(0, time[i], open[i], high[i], low[i], close[i]);
      return;
     }
   FeedSignal(time[i] + gChPer);
   if(gM5)
     {
      gE[0].M5OnBar(time[i], high[i], low[i]);
      for(int k = 0; k < gE[0].gEv5N; k++)
        {
         int side = gE[0].gEv5Side[k], d = (side == 0) ? 1 : -1;
         if(!InpFvgOn) continue;
         DrawFvg(0, gE[0].gEv5T1[k], gE[0].gEv5T3[k], gE[0].gEv5Lo[k], gE[0].gEv5Hi[k], side, gE[0].gEv5C[k], " M5 #" + IntegerToString(gE[0].gEv5Cnt[k]));
         gFvgSid[0][side] = gE[0].gEv5Sid[k];
         OpenTrade(0, d, 2, time[i], close[i], gE[0].gEv5C[k] - d * InpF5SLBuffer, " #" + IntegerToString(gE[0].gEv5Cnt[k]));
        }
     }
   // M5 layer: the chart TF's own setups / zones / FVG
   if(gL5) ProcessSig(1, time[i], open[i], high[i], low[i], close[i]);
  }

void SetStyle(int L, bool alt)
  {
   if(!alt)
     {
      gSt[L].buy = InpBuyClr; gSt[L].sell = InpSellClr; gSt[L].fs = InpFontSize;
      gSt[L].zFillB = InpZoneClrBuy; gSt[L].zFillS = InpZoneClrSell; gSt[L].zBordB = InpZoneBordBuy; gSt[L].zBordS = InpZoneBordSell;
      gSt[L].bw = InpZoneBordW; gSt[L].bs = InpZoneBordSt; gSt[L].fvg = InpFvgClr; gSt[L].alert = InpAlert;
      gSt[L].swing = InpSwingClr; gSt[L].sw = InpSwingWidth;
     }
   else
     {
      gSt[L].buy = InpL5BuyClr; gSt[L].sell = InpL5SellClr; gSt[L].fs = InpL5FontSize;
      gSt[L].zFillB = InpL5ZoneBuy; gSt[L].zFillS = InpL5ZoneSell; gSt[L].zBordB = InpL5BordBuy; gSt[L].zBordS = InpL5BordSell;
      gSt[L].bw = InpL5BordW; gSt[L].bs = InpL5BordSt; gSt[L].fvg = InpL5FvgClr; gSt[L].alert = InpL5Alert;
      gSt[L].swing = InpL5SwingClr; gSt[L].sw = InpL5SwingWidth;
     }
   if(gSt[L].fs < 6) gSt[L].fs = 6;
  }

int OnInit()
  {
   gChPer = PeriodSeconds((ENUM_TIMEFRAMES)_Period);
   gSigTF = (InpTF == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : InpTF;
   gSigPer = PeriodSeconds(gSigTF);
   if(gSigPer < gChPer)
     {
      Print("2CHoCH: Signal TF lower than chart TF is not supported, using chart TF.");
      gSigTF = (ENUM_TIMEFRAMES)_Period; gSigPer = gChPer;
     }
   gFeed = (gSigPer > gChPer);
   gM5 = InpM5Mode && gFeed;
   gL5 = gM5 && InpL5On;
   if(InpM5Mode && !gM5) Print("2CHoCH: M30 + M5 mode needs Signal TF higher than the chart TF (chart M5, Signal TF M30). Mode is OFF.");
   SetStyle(0, false);
   SetStyle(1, true);
   gSt[0].tag = gM5 ? " " + TfS(gSigTF) : "";
   gSt[1].tag = " " + TfS((ENUM_TIMEFRAMES)_Period);
   gSt[0].per = gSigPer;
   gSt[1].per = gChPer;
   gPcOn[0] = InpPcS_On; gPcOn[1] = InpPcF_On;
   gPcR[0][0] = InpPcS_R1; gPcP[0][0] = InpPcS_P1; gPcA[0][0] = (int)InpPcS_A1;
   gPcR[0][1] = InpPcS_R2; gPcP[0][1] = InpPcS_P2; gPcA[0][1] = (int)InpPcS_A2;
   gPcR[0][2] = InpPcS_R3; gPcP[0][2] = InpPcS_P3; gPcA[0][2] = (int)InpPcS_A3;
   gPcR[1][0] = InpPcF_R1; gPcP[1][0] = InpPcF_P1; gPcA[1][0] = (int)InpPcF_A1;
   gPcR[1][1] = InpPcF_R2; gPcP[1][1] = InpPcF_P2; gPcA[1][1] = (int)InpPcF_A2;
   gPcR[1][2] = InpPcF_R3; gPcP[1][2] = InpPcF_P3; gPcA[1][2] = (int)InpPcF_A3;
   IndicatorSetString(INDICATOR_SHORTNAME, "Gann 2CHoCH " + ModeName());
   gNext = -1;
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0, gP);
   Comment("");
  }

string StatLine(int L, int c, string name)
  {
   if(gStN[L][c] == 0) return name + ": 0 trades";
   return name + ": " + IntegerToString(gStN[L][c]) + " trades  TP " + IntegerToString(gStTP[L][c]) + "  SL " + IntegerToString(gStSL[L][c]) +
          "  BE/partial " + IntegerToString(gStBE[L][c]) + "  win " + DoubleToString(100.0 * gStW[L][c] / gStN[L][c], 1) + "%" +
          "  total " + DoubleToString(gStR[L][c], 1) + "R  avg " + DoubleToString(gStR[L][c] / gStN[L][c], 2) + "R";
  }

int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[], const double &open[],
                const double &high[], const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
  {
   if(rates_total < 100) return 0;
   int last = rates_total - 2;                       // last CLOSED chart bar
   if(prev_calculated == 0 || gNext < 0 || gNext > last + 1 || (gNext > 0 && time[gNext - 1] != gLastProcT))
     {
      ResetAll();
      if(gFeed)
        {
         int n = CopyRates(_Symbol, gSigTF, 1, InpBars, gSR);
         if(n < 100) { gNext = -1; return 0; }       // signal TF data not ready yet, retry
         gSRp = 0;
         int st = 0;
         while(st < last && time[st] < gSR[0].time) st++;
         gNext = st;
        }
      else gNext = MathMax(0, last - InpBars + 1);
     }
   if(gNext > last) return rates_total;
   bool hist = (prev_calculated == 0 || gHist);
   for(int i = gNext; i <= last; i++)
     {
      gHist = hist;                                  // no alerts while loading history
      ProcessChart(i, time, open, high, low, close);
      gLastProcT = time[i];
     }
   gHist = false;
   gNext = last + 1;
   DrawSetups(0, time[last]);
   DrawSetups(1, time[last]);
   DrawSwings(0);
   DrawSwings(1);
   if(InpStats)
     {
      string be = "BE " + (InpBEOn ? DoubleToString(InpBE_R, 1) + "R" : "off");
      string pc = (InpPcS_On || InpPcF_On) ? "  partial: " + (InpPcS_On ? "Stop " : "") + (InpPcF_On ? "FVG" : "") : "";
      string tg0 = gM5 ? "[" + TfS(gSigTF) + "] " : "";
      string txt = "Gann 2CHoCH (signals only) " + ModeName() + " | FVG " + (InpFvgOn ? "ON" : "OFF") +
                   (gM5 ? " on M5 bars, max " + IntegerToString(MathMax(1, InpF5MaxPerZone)) + "/zone" : "") +
                   " | Stop " + be + pc + (InpStopAfterFvg ? "" : " | Stop skipped after FVG") + "\n" +
                   StatLine(0, 0, tg0 + "Stop at B (1:" + DoubleToString(InpRR, 1) + ")") + "\n" +
                   StatLine(0, 1, tg0 + (gM5 ? "FVG M5 (1:" + DoubleToString(InpF5RR, 1) : "FVG (1:" + DoubleToString(InpFvgRR, 1)) + ")");
      if(gL5)
         txt += "\n" + StatLine(1, 0, "[" + TfS((ENUM_TIMEFRAMES)_Period) + "] Stop at B (1:" + DoubleToString(InpRR, 1) + ")") +
                "\n" + StatLine(1, 1, "[" + TfS((ENUM_TIMEFRAMES)_Period) + "] FVG (1:" + DoubleToString(InpFvgRR, 1) + ")" + (InpL5Fvg ? "" : " OFF"));
      Comment(txt);
     }
   return rates_total;
  }
