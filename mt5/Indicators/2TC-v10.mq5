//+------------------------------------------------------------------+
//|  2TC-v10.mq5 - 25-08-2026                                    |
//|  BAN MOI SONG SONG, KHONG DE LEN CRB-Model-v3.mq5 (ban owner      |
//|  DANG DUNG). v3 giu NGUYEN VAN, khong sua mot ky tu nao.          |
//|                                                                   |
//|  v5 = v4 + DUNG HAI thu: nhom 14 - DUONG HOI QUY + PARABOL, va    |
//|  nhom 15 - DASHBOARD. Trong do v4 = v3 + nhom 13 - OLHC cau truc  |
//|  nen. Khong doi mot mac dinh nao cua v3 hay v4, khong dong o nao  |
//|  cua chung, khong sua mot dong logic nao cua chung. Tat ba o      |
//|  InpOlOn + InpSlOn + InpDbShow di thi v5 chay Y HET v3.           |
//|                                                                   |
//|  NHOM 14 - DO DOC. Hoi quy tuyen tinh bac 1 lay do doc ca cua     |
//|  so, hoi quy bac 2 lay do doc TAI NEN CUOI, ca hai chuan hoa      |
//|  theo ATR. Luat port NGUYEN VAN tu Indicators/Slope-Meter.mq5 va  |
//|  dung y het nhom 8 cua Experts/CRB-EA-v3.mq5 - sua mot ben la     |
//|  phai mang sang hai ben kia. Tai lieu: docs/slope-meter.md.       |
//|                                                                   |
//|  NHOM 15 - DASHBOARD. Bang tom tat o goc chart: doc ket qua nhom  |
//|  14 roi in KET LUAN (TANG / GIAM / DI NGANG / DANG CONG / GIA     |
//|  LOAN), them hai dong JUDAS / TURTLE SOUP khi bat o InpDbMech.    |
//|                                                                   |
//|  O InpSlLean - CHE DO GON - chan VE cua nhom 1..13 de tren chart  |
//|  chi con duong hoi quy va dashboard. MAC DINH TAT. Ban Pine       |
//|  KHONG co o nay: plotshape/barcolor ben do khong xoa lai duoc     |
//|  nen gon se gon nua voi - tam giac OLHC va mau nen van con.       |
//|                                                                   |
//|  Doi ung 1:1 cua tradingview/2TC-v10.pine.                   |
//|                                                                   |
//|  PREFIX OBJECT RIENG: CRB5_ (v3 CRB3_, v4 CRB4_). Nho vay chung    |
//|  khong xoa object cua nhau - NHUNG neu gan ca hai len cung mot    |
//|  chart thi chung VE TRUNG NHAU toan bo cum JUDAS / TURTLE SOUP /  |
//|  CRB. CHI GAN MOT BAN.                                            |
//|                                                                   |
//|  ---- nguyen van header cua ban v3 tu day tro xuong ----          |
//+------------------------------------------------------------------+
//|  2TC-v10.mq5 - 24-08-2026                                    |
//|  DOI UNG 1:1 cua tradingview/2TC-v10.pine.                   |
//|  Ban MT5 CU (mt5/CRB-Model-v2.mq5) da XOA HAN cung ngay - no port |
//|  ban Pine v2, ma v2 lay SAI cay neo CISD. Lay lai ban do:         |
//|    git show <commit truoc 24-08>:mt5/CRB-Model-v2.mq5             |
//|                                                                   |
//|  ============ KIEN TRUC (owner chot 23-08) ============           |
//|  JUDAS va TURTLE SOUP la HAI CO CHE DOC LAP HOAN TOAN. Chung nhau |
//|  DUNG MOT KHUC GOC roi tach han:                                  |
//|    khuc goc = may CISD -> su kien -> CAY CUC TRI -> cong QUET     |
//|               -> buoc xac dinh CAY NEO. Het.                      |
//|    JUDAS  (nhom 2-3): cay neo MSS  -> vach MSS tai DINH/DAY cay   |
//|                       do -> khe ho TUOI ben PHAI cuc tri          |
//|    T.SOUP (nhom 4-5): vach CISD tai GIA MO CUC TRI cua chuoi nen  |
//|                       cung chieu bias cu -> khe ho CU ben TRAI    |
//|                       cuc tri, DA BI LAP                          |
//|  Khong co che nao doc mot bien nao cua co che kia.                |
//|                                                                   |
//|  ============ KHAC BAN v2 O DAU ============                      |
//|   1. CAY NEO CISD SUA LAI cho khop ban goc kent_combo_v9: vach    |
//|      CISD = GIA MO CUC TRI cua chuoi nen cung chieu bias cu (cay  |
//|      NGHICH MAU DAU TIEN cua chuoi), khong phai cay nghich mau    |
//|      GAN NHAT. O "Nen neo CISD - N nen" DA GO HAN.                |
//|   2. THEM NHOM 12 - FOLLOW BIAS H1. Chay lai CHINH engine nay     |
//|      tren du lieu H1, lay chieu cu JD/TS ra tin hieu gan nhat lam |
//|      BIAS, roi loc tin hieu khung dang mo theo bias do. MAC DINH  |
//|      TAT tu 25-08 toi (owner chot; truoc do BAT tu 24-08). Bat    |
//|      len thi cat rat manh - bo tin hieu nguoc chieu bias H1.      |
//|   3. HE SO be rong khe ho doi theo owner 23-08 toi:               |
//|      TS 1,40 -> 0,50. JD ha 0,75 roi TRA LAI 1,00 (24-08).        |
//|   4. HAI o "bat buoc co nen dong cua xuyen qua" DEU MAC DINH TAT: |
//|      - Vach CISD (Turtle Soup): TAT tu 24-08, ve dung luat goc.   |
//|      - Vach MSS  (Judas)      : TAT tu 25-08 toi (truoc do BAT).  |
//|      Truoc 25-08 hai ben lech nhau co y; nay het lech.            |
//|   5. NHOM 11 = BANG HE SO THEO KHUNG (25-08). De 0 o he so nhom 2 |
//|      / nhom 4 / nhom 12 la giao o do cho bang lai theo khung.      |
//|      MAC DINH TAT - ba o do van giu so cu nen chart khong doi.     |
//|                                                                   |
//|  KHO KHE HO DUNG CHUNG, HAI NGUONG RIENG: kho ghi mot khe khi no  |
//|  dat nguong LONG HON trong hai nguong; luc CHON vao lenh moi co   |
//|  che ap NGUONG RIENG. Judas ATR100 x 1,00 / T.Soup ATR100 x 0,50. |
//|                                                                   |
//|  CUA SO CHINH LA HAN, khong con o "han cho" nao:                  |
//|    Judas       chet khi b > (cuc tri - 1) + InpJdFvgWin           |
//|    Turtle Soup chet khi b > cuc tri + InpTsFvgWin                 |
//|                                                                   |
//|  ====== KHAC BAN PINE O DAU (gioi han MT5, khong phai y do) ===== |
//|   1. MQL5 khong co label nhieu dong -> mui ten va chu "JD"/"TS"   |
//|      phai la HAI object. Chu day them 0,5 x ATR14 (hang so; ban   |
//|      Pine gop chung mot nhan nen khong can o nay).                |
//|   2. MQL5 khong co kenh alpha -> moi "do mo" deu pha voi MAU NEN  |
//|      CHART bang ham Blend(). Doi mau nen chart thi mau nhat doi   |
//|      theo, day la gioi han cua MetaTrader.                        |
//|   3. Them O CHON KHUNG ENGINE (nhom 1, rieng MT5): object neo     |
//|      bang datetime nen chay khung khac chart van dung cho.        |
//|   4. Ban Pine giu state song va sua object tai cho; ban MT5 xoa   |
//|      sach roi DUNG LAI TU DAU moi khi co nen moi dong. Ket qua    |
//|      cuoi cung y het, chi khac cach dung.                         |
//|   5. Hai o mau "di ngang" / "that bai" ben Pine de trong suot     |
//|      100% (= AN). MT5 dung clrNONE cho dung y do do.              |
//|   6. Engine H1 cua nhom 12: ben Pine phai chui qua request.       |
//|      security() + lookahead_on; ben MT5 chi la CopyRates(H1) roi  |
//|      chay lai chinh engine. Ca hai deu DUNG O NEN H1 DA DONG.     |
//|                                                                   |
//|  LUAT tin hieu nam trong mt5/Include/Neiro/crb_engine.mqh - CUNG  |
//|  MOT file ma Experts/CRB-EA-v3.mq5 dung. Sua luat la sua o do,    |
//|  hai ben doi theo. Xem docs/architecture.md.                      |
//+------------------------------------------------------------------+
#property copyright "2TC-v10 - Neiro-Gold (Judas + Turtle Soup + CRB + Daily Bias)"
#property version   "6.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

#define PFX "CRB6_"   // RIENG, khong dung chung voi CRB4_ hay CRB5_:
                      // Rebuild() mo dau bang ObjectsDeleteAll(0,PFX)
                      // nen dung chung prefix la hai ban xoa cua nhau.

// Engine JUDAS + TURTLE SOUP dung CHUNG voi CRB-EA-v3.mq5.
// Sua LUAT la sua trong file do, khong sua o day.
#include <Neiro/crb_engine.mqh>

//==================================================================
//   ENUM
//==================================================================
enum ENUM_TXSZ
  {
   TXSZ_SMALL,  // Nho
   TXSZ_NORMAL, // Binh thuong
   TXSZ_LARGE   // To
  };
enum ENUM_SESL
  {
   SESL_NBARS,  // Lui N nen
   SESL_ATR     // ATR
  };
enum ENUM_SESTYLE
  {
   SES_SOLID,   // Lien
   SES_DASHED,  // Dut
   SES_DOTTED   // Cham
  };
enum ENUM_CRBSIZE
  {
   CRB_HUGE,    // Rat to
   CRB_LARGE,   // To
   CRB_NORMAL,  // Vua
   CRB_SMALL,   // Nho
   CRB_TINY     // Rat nho
  };
enum ENUM_SEICON
  {
   SEI_TRIANGLE, // Triangle
   SEI_ARROW,    // Arrow
   SEI_CIRCLE,   // Circle
   SEI_SQUARE    // Square
  };
// Vi tri bang he so. MT5 khong co goc "giua" - TFP_MR neo goc TREN PHAI roi
// tu ha bang xuong nua man hinh, giong cach Neiro-Liquidity-Map lam.
enum ENUM_TFPOS
  {
   TFP_TR, // Tren phai
   TFP_MR, // Giua phai
   TFP_BR, // Duoi phai
   TFP_TL, // Tren trai
   TFP_BL  // Duoi trai
  };
// Bo loc bias H1 ap len cum CRB: chan moi tin hieu, hay chi chan lenh MO CHUOI.
enum ENUM_BHCRB
  {
   BHC_ALL,   // Moi tin hieu CRB
   BHC_OPEN   // Chi chan CRB0
  };

//==================================================================
//   INPUT  - thu tu o va mac dinh BAM SAT bang cong tac cua Pine.
//==================================================================
input group "1 - BAT / TAT"
input bool             InpEnJudas   = true;                 // JUDAS - FVG tuoi + vach MSS
input bool             InpEnTs      = true;                 // TURTLE SOUP - iFVG + vach CISD
input bool             InpUseWin    = true;                 // Chi tinh N nen gan nhat
input int              InpWinBars   = 1500;                 //    N nen (200..5000)
input bool             InpCxShow    = false;                // CISD Max - vach tai nen cuc tri
input ENUM_TIMEFRAMES  InpEngineTF  = PERIOD_CURRENT;       // Khung chay engine (rieng MT5)

input group "1.5 - BO LOC CANH BAO (ALERTS FILTER)"
input bool             InpBhAlert   = false;                // Alert khi bias H1 doi chieu
input bool             InpAlertNoisy= false;                // Cho phep Alert khi GIA LOAN
input bool             InpAlertAccum= false;                // Cho phep Alert khi TICH LUY (NEN) hoac DI NGANG

input group "2 - JUDAS: luat (FVG tuoi, vach MSS)"
input ENUM_JDIR        InpJdDir     = JDIR_BOTH;            // Chieu tin hieu
input bool             InpJdSweep   = false;                // Nen cuc tri - chi nhan cay DA QUET (swept)
input int              InpJdFvgLen  = 100;                  // FVG tuoi - ATR: chu ky
input double           InpJdFvgMult = 1.00;                 // FVG tuoi - ATR: he so
input int              InpJdFvgWin  = 5;                    // FVG tuoi - N nen tu cuc tri sang PHAI
input bool             InpJdNeedMss = false;                 // Vach MSS - bat buoc co nen dong cua xuyen qua
input int              InpJdAncBack = 6;                    // Nen neo MSS - N nen tu cuc tri sang TRAI

input group "3 - JUDAS: hien thi"
input int              InpJdKeep    = 20;                   // Giu N cu gan nhat (ke ca cu hong)
input ENUM_JDMARK      InpJdMark    = JDM_MID;              // Mui ten - dat tai
input color            InpJdColBull = C'38,166,154';        // Mui ten - mau mua
input color            InpJdColBear = C'239,83,80';         // Mui ten - mau ban
input double           InpJdGap     = 1.8;                  // Mui ten - day xa nen (x ATR14)
input ENUM_TXSZ        InpJdTxSz    = TXSZ_NORMAL;          // Mui ten - co chu
input bool             InpJdShowTxt = true;                 // Mui ten - hien chu JD
input bool             InpJdStem    = true;                 // Mui ten - vach noi xuong nen
input int              InpJdSigVis  = 45;                   // Mui ten - do RO khi chua qua vach (%)
input color            InpJdBoxBull = C'38,166,154';        // Hop FVG tuoi - mau FVG tang
input color            InpJdBoxBear = C'239,83,80';         // Hop FVG tuoi - mau FVG giam
input int              InpJdBoxW    = 1;                    // Hop FVG tuoi - do day vien
input ENUM_LINE_STYLE  InpJdBoxSty  = STYLE_SOLID;          // Hop FVG tuoi - kieu net
input int              InpJdBoxOp   = 100;                  // Hop FVG tuoi - dam vien (%)
input int              InpJdBoxFill = 12;                   // Hop FVG tuoi - dam nen (%)
input color            InpMssColBull  = C'76,175,80';       // Vach MSS - mau DA qua: mua
input color            InpMssColBear  = C'229,57,53';       // Vach MSS - mau DA qua: ban
input color            InpMssColBullW = C'165,214,167';     // Vach MSS - mau CHUA qua: mua
input color            InpMssColBearW = C'239,154,154';     // Vach MSS - mau CHUA qua: ban
input int              InpMssLen    = 0;                    // Vach MSS - dai (nen), 0 = dung tai nen ra tin hieu
input int              InpMssW      = 1;                    // Vach MSS - do day
input ENUM_LINE_STYLE  InpMssStyle  = STYLE_DASH;           // Vach MSS - kieu net
// 50 - lay tu crb.set cua owner 24-08 de khoi phai load preset nua.
input int              InpMssVis    = 50;                   // Vach MSS - do RO khi chua ra tin hieu (%)
input double           InpMssTxtGap = 0.3;                  // Vach MSS - day chu (x ATR14)
input bool             InpJdAlert   = true;                 // Alert khi co JD moi

input group "4 - TURTLE SOUP: luat (iFVG, vach CISD)"
input ENUM_JDIR        InpTsDir     = JDIR_BOTH;            // Chieu tin hieu
input bool             InpTsSweep   = false;                // Nen cuc tri - chi nhan cay DA QUET (swept)
input int              InpTsFvgLen  = 100;                  // iFVG - ATR: chu ky
input double           InpTsFvgMult = 0.50;                 // iFVG - ATR: he so
input int              InpTsFvgWin  = 15;                    // iFVG - N nen tu cuc tri sang TRAI
input bool             InpTsNeedCisd= false;                // Vach CISD - bat buoc co nen dong cua xuyen qua
input bool             InpTsNeedIfvg= true;                 // Yeu cau co iFVG (FVG moi de len FVG cu)

input group "5 - TURTLE SOUP: hien thi"
input int              InpTsKeep    = 20;                   // Giu N cu gan nhat (ke ca cu hong)
input ENUM_TSMARK      InpTsMark    = TSM_FILL;             // Mui ten - dat tai
input color            InpTsColBull = C'30,144,255';        // Mui ten - mau mua
input color            InpTsColBear = C'255,140,0';         // Mui ten - mau ban
input double           InpTsGap     = 1.8;                  // Mui ten - day xa nen (x ATR14)
input ENUM_TXSZ        InpTsTxSz    = TXSZ_NORMAL;          // Mui ten - co chu
input bool             InpTsShowTxt = true;                 // Mui ten - hien chu TS
input bool             InpTsStem    = true;                 // Mui ten - vach noi xuong nen
input int              InpTsSigVis  = 45;                   // Mui ten - do RO khi chua qua vach (%)
input color            InpTsBoxBull = C'255,140,0';         // Hop iFVG - mau FVG tang lat
input color            InpTsBoxBear = C'30,144,255';        // Hop iFVG - mau FVG giam lat
input int              InpTsBoxW    = 1;                    // Hop iFVG - do day vien
input ENUM_LINE_STYLE  InpTsBoxSty  = STYLE_SOLID;          // Hop iFVG - kieu net
input int              InpTsBoxOp   = 100;                  // Hop iFVG - dam vien (%)
input int              InpTsBoxFill = 12;                   // Hop iFVG - dam nen (%)
input color            InpCisdColBull  = C'30,144,255';     // Vach CISD - mau DA qua: mua
input color            InpCisdColBear  = C'255,140,0';      // Vach CISD - mau DA qua: ban
input color            InpCisdColBullW = C'144,202,249';    // Vach CISD - mau CHUA qua: mua
input color            InpCisdColBearW = C'255,204,128';    // Vach CISD - mau CHUA qua: ban
input int              InpCisdLen   = 0;                    // Vach CISD - dai (nen), 0 = dung tai nen ra tin hieu
input int              InpCisdW     = 1;                    // Vach CISD - do day
input ENUM_LINE_STYLE  InpCisdStyle = STYLE_DASH;           // Vach CISD - kieu net
// 50 - lay tu crb.set cua owner 24-08 de khoi phai load preset nua.
input int              InpCisdVis   = 50;                   // Vach CISD - do RO khi chua ra tin hieu (%)
input double           InpCisdTxtGap= 0.3;                  // Vach CISD - day chu (x ATR14)
input bool             InpTsAlert   = true;                 // Alert khi co TS moi

//==================================================================
//   6 - CHAN DOAN
//==================================================================
input group "6 - CHAN DOAN"
input bool             InpDgShowAll = false;                 
input int              InpDgKeep    = 50;                   
input color            InpDgCBull   = C'69,160,136';        
input color            InpDgCBear   = C'201,106,106';       
input int              InpDgBw      = 1;                    
input ENUM_LINE_STYLE  InpDgStyle   = STYLE_SOLID;          
input int              InpDgOp      = 70;                   
input bool             InpXdShow    = false;                
input int              InpXdKeep    = 20;                   
input int              InpXdVi      = 0;                    
input color            InpXdCol     = clrGray;              
input int              InpCxKeepOld = 3;                    
input color            InpCxColCur  = clrOrange;            
input color            InpCxColOld  = clrGray;              
input int              InpCxW       = 1;                    
input ENUM_LINE_STYLE  InpCxStyle   = STYLE_SOLID;          

//==================================================================
//   13 - OLHC: CAU TRUC NEN   (thu duy nhat v4 them so voi v3)
//   Cum DOC LAP: khong doc state cua JUDAS / TURTLE SOUP / CRB, va
//   KHONG di qua bo loc BIAS H1 cua nhom 12.
//   Ba gap phu kin cay nen, tong luon bang 100% range:
//     GAP 1  wick QUET  phia bi day nguoc   (phai DAI)
//     GAP 2  body       than nen
//     GAP 3  wick DOI   phia doi dien gap 1 (phai NGAN)
//   OHLC: gap1 = upper wick -> tin hieu GIAM -> do   -> tam giac TREN nen
//   OLHC: gap1 = lower wick -> tin hieu TANG -> xanh -> tam giac DUOI nen
//==================================================================
input group "13 - OLHC: cau truc nen"
input bool        InpOlOn      = false;  // OLHC - bat cum
input double      InpOlGap1    = 45.0;   //    GAP 1 - wick QUET toi thieu (%)
input double      InpOlGap2    = 45.0;   //    GAP 2 - body toi da (%)
input double      InpOlGap3    = 25.0;   //    GAP 3 - wick DOI toi da (%)
input bool        InpOlUseK    = true;   //    them rang buoc: GAP 1 >= K x GAP 3
input double      InpOlK       = 2.0;    //    K
input bool        InpOlAtrOn   = true;   //    loc nen manh: range >= ATR x he so
input int         InpOlAtrLen  = 14;     //    chu ky ATR
input double      InpOlAtrMult = 1.0;    //    he so ATR
input bool        InpOlMark    = true;   //    1 - tam giac danh dau
input int         InpOlMarkSz  = 8;      //    co tam giac (font) - rieng MT5
input bool        InpOlLbl     = false;  //    2 - nhan OHLC / OLHC
input int         InpOlLblSz   = 9;      //    co chu nhan (font)
input bool        InpOlBox     = true;   //    3 - to khoi bao trum cay nen
input int         InpOlBoxTr   = 65;     //    khoi - do trong suot (0-95) - rieng MT5
input int         InpOlKeep    = 50;     //    so tin hieu giu lai tren chart
input int         InpOlScan    = 3000;   //    so nen quet nguoc - rieng MT5
input color       InpOlColBear = C'242,54,69';  //    mau: OHLC - tin hieu GIAM
input color       InpOlColBull = C'8,153,129';  //    mau: OLHC - tin hieu TANG

//====================================================================
//  NHOM 14 + 15 - RIENG CUA BAN v5 (25-08)
//
//  Owner: "lam cho anh cai version 5, chi can co cai duong ke chart
//  va cai dashboard thoi" -> duong ke = DUONG HOI QUY + PARABOL.
//
//  Hai nhom nay dat o CUOI theo luat 3 cua kho. Chung KHONG doc mot
//  bien nao cua nhom 1..13, va nhom 1..13 khong doc mot bien nao cua
//  chung. Tat InpSlOn thi ban v7 chay Y HET ban v4.
//
//  MAC DINH: v5 hien DU moi thu cua v4, CONG them duong hoi quy va
//  dashboard. Khong bo gi ca.
//
//  CHE DO GON (o dau nhom 14) MAC DINH TAT. Bat len thi no chan phan
//  VE cua nhom 1..13 - mui ten, hop khe ho, vach MSS/CISD, cum CRB,
//  cum OLHC - de tren chart chi con duong hoi quy va bang, cho luc nao
//  can nhin cho thoang. LUAT VAN CHAY DU du bat hay tat: dashboard van
//  biet cu JD/TS gan nhat, bias H1 van tinh.
//
//  Ban dau o nay de MAC DINH BAT (25-08) vi hieu nham cau owner dat
//  hang; owner hoi lai ngay hom do nen tra ve TAT.
//====================================================================

//==================================================================
//   17 - MOTHER BAR BREAKOUT
//==================================================================
//==================================================================
//   16 - GANN SWING CONSOLIDATION
//==================================================================
input group "16 - GANN SWING CONSOLIDATION"
input bool   InpGsOn       = false;             // Bat Gann Swing
input int    InpGsMethod   = 0;                 // Cach phat hien (0: A, 1: B, 2: C)
input bool   InpGsUseClose = false;             // Do song theo Close (thay vi High/Low)
input int    InpGsLayer    = 0;                 // Tang khung (0: F1, 1: SF1)
input int    InpGsOvMode   = 2;                 // Kieu chong hop (0: a, 1: b, 2: c)
input int    InpGsMinTouch = 2;                 // So lan cham toi thieu moi bien
input double InpGsTolPct   = 20.0;              // Dung sai cham bien (%)
input double InpGsMaxAtr   = 3.0;               // Chieu cao hop toi da (x ATR)
input int    InpGsAtrLen   = 14;                // ATR Length
input int    InpGsMinBars  = 10;                // So nen toi thieu cua vung
input int    InpGsMaxPiv   = 20;                // So diem swing toi da xet (Cach A/B)
input int    InpGsMaxLook  = 150;               // So nen toi da xet (Cach C)
input int    InpGsDrawMode = 0;                 // Bien ve (0: Ngoai, 1: Trong, 2: Ca hai)
input int    InpGsBrkMode  = 0;                 // Bien xet pha (0: Ngoai, 1: Trong)
input bool   InpGsCfOn     = false;             // Bat bo loc kieu C
input double InpGsCfClose  = 60.0;              // Ty le nen dong cua trong bien trong >= %
input double InpGsCfIB     = 0.0;               // Ty le inside bar >= %
input int    InpGsBtrN     = 5;                 // Cua so BTR (so nen)
input double InpGsDBody    = 0.60;              // BAG - Than/Range >=
input double InpGsDClose   = 0.70;              // BAG - Vi tri Close >=
input double InpGsDAtr     = 1.20;              // BAG - Range nen >= x ATR
input bool   InpGsVolOn    = false;             // BAG - Filter Volume
input double InpGsVolMult  = 1.5;               // BAG - >= x TB
input int    InpGsVolLen   = 20;                // BAG - Ky TB
input bool   InpGsSzOn     = true;              // Bat Min FVG Size
input double InpGsSzMult   = 0.30;              // Chieu cao FVG >= x ATR
input int    InpGsSzMode   = 1;                 // Hinh thuc ap dung (0: Ca BO & BAG, 1: Chi BAG)
input bool   InpGsAlertOn  = true;              // Alert khi co tin hieu GS

input group "16.1 - GANN HINH ANH"
input color  InpGsBorder   = C'0,188,212';      // Hop - Vien
input color  InpGsFill     = C'0,188,212';      // Nen
input int    InpGsFillTr   = 88;                // Nen - Trong suot (0-100)
input color  InpGsInner    = C'255,152,0';      // Bien trong
input color  InpGsBOBuy    = C'38,166,154';     // B/O Buy
input color  InpGsBOSell   = C'239,83,80';      // B/O Sell
input color  InpGsBAGBuy   = C'0,230,118';      // BAG Buy
input color  InpGsBAGSell  = C'255,23,68';      // BAG Sell
input color  InpGsBTRBuy   = C'66,165,245';     // BTR Buy
input color  InpGsBTRSell  = C'255,167,38';     // BTR Sell
input color  InpGsBTRsBuy  = C'21,101,192';     // BTR* Buy
input color  InpGsBTRsSell = C'230,81,0';       // BTR* Sell
input bool   InpGsShowF1   = false;             // Ve song F1
input color  InpGsColF1    = clrAqua;           // Mau F1
input bool   InpGsShowSF   = false;             // Ve song SF1
input color  InpGsColSF    = clrYellow;         // Mau SF1


//==================================================================
//   17 - FVG MULTI-TIMEFRAME
//==================================================================
input group "17 - FVG MULTI-TIMEFRAME"
input bool        InpFvgOn      = false;             // Bat FVG MTF
input int         InpFvgN       = 100;               // Number of FVGs
input ENUM_LINE_STYLE InpFvgHtfSty = STYLE_DASH;     // HTF FVG Style
input bool        InpFvgExtOn   = false;             // Keo dai FVG den khi bi lap
input bool        InpFvgHideFill= false;             // An FVG da lap
input bool        InpFvgCtfOn   = false;             // ChartTF FVG
input color       InpFvgBullClr = C'0,128,0';        // BullFVG Clr
input color       InpFvgBearClr = C'255,165,0';      // BearFVG Clr
input bool        InpFvgH1On    = false;             // HTF-1
input ENUM_TIMEFRAMES InpFvgH1Tf= PERIOD_M15;        // Khung HTF-1
input color       InpFvgH1Clr   = clrGray;           // BorderClr
input int         InpFvgH1W     = 1;                 // Width
input bool        InpFvgH2On    = false;             // HTF-2
input ENUM_TIMEFRAMES InpFvgH2Tf= PERIOD_H1;         // Khung HTF-2
input color       InpFvgH2Clr   = clrGray;           // BorderClr
input int         InpFvgH2W     = 1;                 // Width
input bool        InpFvgH3On    = false;             // HTF-3
input ENUM_TIMEFRAMES InpFvgH3Tf= PERIOD_H4;         // Khung HTF-3
input color       InpFvgH3Clr   = clrGray;           // BorderClr
input int         InpFvgH3W     = 1;                 // Width

input group "14 - DUONG HOI QUY + PARABOL"
input bool             InpSlLean   = false;             // CHE DO GON - chan VE cua nhom 1..13
input bool             InpSlOn     = false;             // Bat cum do doc
enum ENUM_SL_ANCHOR
  {
   SL_ANCHOR_CISD,    // Song Cuc Tri
   SL_ANCHOR_FIXED    // Nen Co Dinh
  };
input ENUM_SL_ANCHOR   InpSlAnchor = SL_ANCHOR_CISD;    // Chon diem neo
input ENUM_TIMEFRAMES  InpSlTF     = PERIOD_M15;        // Khung doc du lieu (Nen co dinh)
input int              InpSlLen    = 9;                 // Hoi quy qua N nen (3..500)
input ENUM_APPLIED_PRICE InpSlSrc  = PRICE_WEIGHTED;    // Lay gia nao
input int              InpSlAtrLen = 14;                // Chuan hoa - chu ky ATR
input double           InpSlFlat   = 0.10;              // Nguong DI NGANG (x ATR moi nen)
input double           InpSlKAmp   = 0.0;               // Khuech dai gia toc (K)

//--- DONG NANG & THE NANG (KINEMATICS) ---
input bool             InpEnergyOn = false;             // Bat tinh Dong luc hoc (Energy)
input int              InpVolMaLen = 100;               // Chu ky MA de chuan hoa Mass
input int              InpBaseMaLen= 20;                // Chu ky MA de tinh Ep (0 = ep theo N)
input bool             InpSlSeg    = true;              // Ve DOAN THANG hoi quy
input bool             InpSlSegRay = false;             //    keo dai doan sang PHAI
input int              InpSlSegW   = 2;                 //    do day doan
input ENUM_LINE_STYLE  InpSlSegSty = STYLE_SOLID;       //    kieu net doan
input color            InpSlColUp  = C'38,166,154';     //    mau doc LEN
input color            InpSlColDn  = C'239,83,80';      //    mau doc XUONG
input color            InpSlColFlat= C'120,123,134';    //    mau DI NGANG
input bool             InpSlP2     = true;              // Ve DUONG CONG parabol
input color            InpSlP2Up   = C'255,193,7';      //    mau khi CONG LEN (a > 0)
input color            InpSlP2Dn   = C'186,104,200';    //    mau khi CONG XUONG (a < 0)
input int              InpSlP2W    = 2;                 //    do day duong cong
input ENUM_LINE_STYLE  InpSlP2Sty  = STYLE_SOLID;       //    kieu net duong cong
input double           InpSlR2Min  = 0.30;              // Duoi muc khop nay coi la GIA LOAN
input double           InpSlR2Gap  = 0.20;              // Bac 2 hon bac 1 tu muc nay = DANG CONG

input group "15 - DASHBOARD"
input bool             InpDbShow   = false;              // Hien dashboard
input ENUM_TFPOS       InpDbPos    = TFP_BL;            // Goc neo (Duoi trai)
input int              InpDbX      = 12;                // Lech ngang (px)
input int              InpDbY      = 120;               // Lech doc (px)
input int              InpDbFont   = 9;                 // Co chu
input color            InpDbColBg  = C'22,26,37';       // Mau nen
input int              InpDbTrans  = 20;                // Do trong suot nen (%)
input color            InpDbColTx  = clrGray;           // Mau chu nhan
input bool             InpDbMech   = false;             // Them hai dong JUDAS / TURTLE SOUP

// Dinh nghia o CUOI file (can EngineTf()), nhung Rebuild() goi truoc -> khai bao truoc.
//==================================================================
//   15 - DISPLACEMENT SOM (V7)
//==================================================================
input group "15 - DISPLACEMENT SOM (V7)"
input bool   InpDispOn         = false;       // BAT CANH BAO DISPLACEMENT SOM
input double InpDispAtrMult    = 1.5;         // Nguong than nen (x ATR)
input double InpDispVolMult    = 1.5;         // Nguong khoi luong (x Trung binh 20)
input double InpDispWickPct    = 0.2;         // Rau nguoc toi da (% than nen)
input bool   InpDispUseAcc     = true;        // Ket hop Gia Toc
input bool   InpDispAccSurging = true;        // Bat buoc Gia toc tang vot
input bool   InpDispShowBarColor= true;       // To mau nen
input bool   InpDispShowShape  = true;        // Hien mui ten
input color  InpDispColBuy     = clrBlue;     // Mau Mua
input color  InpDispColSell    = clrOrange;   // Mau Ban

//==================================================================
//   16 - INSIDE & OUTSIDE BAR
//==================================================================
input group "16 - INSIDE & OUTSIDE BAR"
input bool   InpInOutOn    = false;      // BAT CHO BAO INSIDE/OUTSIDE BAR
input bool   InpShowInside = true;       // Hien chu I
input bool   InpShowOutside= true;       // Hien chu O
input color  InpColInBuy   = clrGreen;   // Mau Mua
input color  InpColInSell  = clrRed;     // Mau Ban

//==================================================================
//   SERIES + STATE
//==================================================================

int g_gsAtrH = INVALID_HANDLE;
double mb_atr_buf[];
long mb_vol_buf[];
double mb_vol_ma_buf[];
int g_gsVolMaH = INVALID_HANDLE;

int      g_objId = 0;
double   g_barSec = 0;
datetime g_lastBar = 0;
string   g_alertMsg = "";





//--- FVG MTF ------------------------------------------------------
struct FVG_Z {
   string bName;
   datetime t1;
   double top;
   double bot;
   int   dir;
   bool  done;
};
FVG_Z zC[];
FVG_Z z1[];
FVG_Z z2[];
FVG_Z z3[];

void ArrayRemoveFvgZ(FVG_Z &arr[], int idx) {
   int sz = ArraySize(arr);
   if (idx < 0 || idx >= sz) return;
   for (int i = idx; i < sz - 1; i++) arr[i] = arr[i+1];
   ArrayResize(arr, sz - 1);
}

//--- Daily Bias ---------------------------------------------------


//==================================================================
//   O DAN XUAT
//==================================================================
int    MssDim(){  int v=100-InpMssVis;   return (v<0?0:(v>100?100:v)); }
int    CisdDim(){ int v=100-InpCisdVis;  return (v<0?0:(v>100?100:v)); }
int    JdSigDim(){int v=100-InpJdSigVis; return (v<0?0:(v>100?100:v)); }
int    TsSigDim(){int v=100-InpTsSigVis; return (v<0?0:(v>100?100:v)); }

//==================================================================
//   HELPER VE
//==================================================================
// MQL5 khong co kenh alpha: moi "do mo" deu la PHA VOI MAU NEN CHART.
color Blend(color base, color bg, double t)
  {
   if(base==clrNONE) return clrNONE;
   if(t <= 0.0) return base;
   if(t >= 1.0) return bg;
   int r1=(int)(base&0xFF), g1=(int)((base>>8)&0xFF), b1=(int)((base>>16)&0xFF);
   int r2=(int)(bg&0xFF),   g2=(int)((bg>>8)&0xFF),   b2=(int)((bg>>16)&0xFF);
   int r=(int)(r1*(1-t)+r2*t), g=(int)(g1*(1-t)+g2*t), b=(int)(b1*(1-t)+b2*t);
   return (color)((b<<16)|(g<<8)|r);
  }
color BgColor(){ return (color)ChartGetInteger(0,CHART_COLOR_BACKGROUND); }
// Pine dung DO MO (transparency 0..100); ham nay doi thang sang he so pha.
// TRONG SUOT 100% ben Pine = AN HAN. MT5 khong co alpha nen neu cu pha tiep thi
// ra mot vach dung MAU NEN CHART, de len than nen -> nhin nhu bi khoet. Phai tra
// clrNONE de moi ham ve BO QUA hinh do. Ai ha InpMssVis/InpCisdVis ve 0 se dinh bay nay.
color Dim(color base, int transp)
  {
   if(transp>=100) return clrNONE;
   return Blend(base,BgColor(),(double)transp/100.0);
  }
// Pine dung DO DAM (opacity 0..100) cho vien / nen hop. Dam 0 = khong ve.
color Op(color base, double opacity)
  {
   if(opacity<=0.0) return clrNONE;
   return Blend(base,BgColor(),1.0-opacity/100.0);
  }

int TxPx(ENUM_TXSZ s)
  {
   switch(s){ case TXSZ_SMALL:return 9; case TXSZ_LARGE:return 14; }
   return 11;
  }
int ArrowW(ENUM_TXSZ s)
  {
   switch(s){ case TXSZ_SMALL:return 2; case TXSZ_LARGE:return 4; }
   return 3;
  }

void L(datetime t1,double p1,datetime t2,double p2,color c,ENUM_LINE_STYLE st,int w)
  {
   if(c==clrNONE) return;
   string nm=PFX+"L"+IntegerToString(g_objId++);
   if(ObjectCreate(0,nm,OBJ_TREND,0,t1,p1,t2,p2))
     {
      ObjectSetInteger(0,nm,OBJPROP_COLOR,c);
      ObjectSetInteger(0,nm,OBJPROP_STYLE,st);
      ObjectSetInteger(0,nm,OBJPROP_WIDTH,w);
      ObjectSetInteger(0,nm,OBJPROP_RAY_RIGHT,false);
      ObjectSetInteger(0,nm,OBJPROP_BACK,false);
      ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
     }
  }
void Box(datetime t1,double p1,datetime t2,double p2,color col,ENUM_LINE_STYLE st,int w)
  {
   if(col==clrNONE) return;
   string nm=PFX+"B"+IntegerToString(g_objId++);
   if(ObjectCreate(0,nm,OBJ_RECTANGLE,0,t1,p1,t2,p2))
     {
      ObjectSetInteger(0,nm,OBJPROP_COLOR,col);
      ObjectSetInteger(0,nm,OBJPROP_FILL,false);      // CHI VIEN
      ObjectSetInteger(0,nm,OBJPROP_STYLE,st);
      ObjectSetInteger(0,nm,OBJPROP_WIDTH,w);
      ObjectSetInteger(0,nm,OBJPROP_BACK,false);
      ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
     }
  }
void BoxFill(datetime t1,double p1,datetime t2,double p2,color col)
  {
   if(col==clrNONE) return;
   string nm=PFX+"F"+IntegerToString(g_objId++);
   if(ObjectCreate(0,nm,OBJ_RECTANGLE,0,t1,p1,t2,p2))
     {
      ObjectSetInteger(0,nm,OBJPROP_COLOR,col);
      ObjectSetInteger(0,nm,OBJPROP_FILL,true);
      ObjectSetInteger(0,nm,OBJPROP_BACK,true);
      ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
     }
  }
void Txt(datetime t,double y,string s,color c,int sz,ENUM_ANCHOR_POINT anc)
  {
   if(c==clrNONE || StringLen(s)==0) return;
   string nm=PFX+"T"+IntegerToString(g_objId++);
   if(ObjectCreate(0,nm,OBJ_TEXT,0,t,y))
     {
      ObjectSetString(0,nm,OBJPROP_TEXT,s);
      ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,sz);
      ObjectSetInteger(0,nm,OBJPROP_COLOR,c);
      ObjectSetInteger(0,nm,OBJPROP_ANCHOR,anc);
      ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
     }
  }
void TxtT(datetime t,double y,string s,color c,int sz,ENUM_ANCHOR_POINT anc,string tip)
  {
   if(c==clrNONE || StringLen(s)==0) return;
   string nm=PFX+"T"+IntegerToString(g_objId++);
   if(ObjectCreate(0,nm,OBJ_TEXT,0,t,y))
     {
      ObjectSetString(0,nm,OBJPROP_TEXT,s);
      ObjectSetString(0,nm,OBJPROP_FONT,"Arial");
      ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,sz);
      ObjectSetInteger(0,nm,OBJPROP_COLOR,c);
      ObjectSetInteger(0,nm,OBJPROP_ANCHOR,anc);
      ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
      if(StringLen(tip)>0) ObjectSetString(0,nm,OBJPROP_TOOLTIP,tip);
     }
  }
void Arrow(datetime t,double y,int code,color c,int w,int anc)
  {
   if(c==clrNONE) return;
   string nm=PFX+"A"+IntegerToString(g_objId++);
   if(ObjectCreate(0,nm,OBJ_ARROW,0,t,y))
     {
      ObjectSetInteger(0,nm,OBJPROP_ARROWCODE,code);
      ObjectSetInteger(0,nm,OBJPROP_COLOR,c);
      ObjectSetInteger(0,nm,OBJPROP_WIDTH,w);
      ObjectSetInteger(0,nm,OBJPROP_ANCHOR,anc);
      ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
     }
  }
datetime FwdT(int idx)
  {
   if(idx<0) return gT[0];
   if(idx<=gN-1) return gT[idx];
   return (datetime)((long)gT[gN-1] + (long)((idx-(gN-1))*(long)g_barSec));
  }


//==================================================================
//   CUM DAILY BIAS (nhom 6) - chep nguyen luat tu ban Pine
//==================================================================

//--- Hai helper RIENG cho cum CRB: ban goc Neiro-ICT co them tham so ray (duong
//    keo mai) va fill (to nen), ban gop khong co -> giu rieng cho khoi sua luat.

//==================================================================
//   CUM (5) CRB - Sweep & Engulf pyramiding (chep tu mt5/Neiro-ICT.mq5)
//==================================================================
//--- S&E state (reset moi rebuild)
int      se_chainDir = 0; // 0 chua co / 1 Buy / -1 Sell
int      se_nextIdx  = 0;
double   se_chainSL  = 0.0;
bool     se_prevRawLong = false, se_prevRawShort = false;
//--- theo doi duong SL chuoi (ve hoan lai tai chuyen chuoi / cuoi loop)
bool     se_hasChain    = false;
//--- buffer hinh ve S&E de TRIM theo InpSeKeep (port Pine se_keep).
//    Khong ve ngay trong SeProcessBar nua: don vao day, cuoi rebuild chi ve N cai cuoi.
// 23-08: them truong idx. Truoc do ban MT5 ve nhan "B (gia)" cho MOI cay trong chuoi,
// mat han so thu tu ma ben Pine van co (B0 / B1 / B2*). Nay hai ban khop: "B0" / "B1*".
struct SESIG { int b; int idx; bool isBuy; bool isBase; bool star; double entry; };
struct SEBOX { int b; bool isBuy; };
SESIG    se_sig[];  int se_sig_n = 0;
SEBOX    se_box[];  int se_box_n = 0;
datetime se_chainStartT = 0;
double   se_chainSLpx   = 0.0;
bool     se_chainBuy    = false;

int CrbPx(ENUM_CRBSIZE s)
  {
   switch(s){ case CRB_TINY:return 7; case CRB_SMALL:return 8; case CRB_NORMAL:return 10;
              case CRB_LARGE:return 12; case CRB_HUGE:return 16; }
   return 12;
  }
//--- size con (CRB1+ nho hon CRB0 1 bac, san Tiny)
ENUM_CRBSIZE CrbChild(ENUM_CRBSIZE s)
  {
   switch(s){ case CRB_HUGE:return CRB_LARGE; case CRB_LARGE:return CRB_NORMAL;
              case CRB_NORMAL:return CRB_SMALL; default:return CRB_TINY; }
   return CRB_TINY;
  }
//--- style S&E enum -> ENUM_LINE_STYLE



//--- Icon tin hieu CRB (port kent_combo_v9)
//--- Phan loai 5 hinh thai cua nen C (cay cb) so voi nen tin hieu (cay sb).
//    Chep nguyen luat tu f_se_classifyC cua kent_combo_v9.
// label CRB "B0" / "S1*" + vach ngang entry tren cay (bar-1 -> bar+1)
// Ghi tin hieu vao buffer (khong ve ngay) + ban ALERT neu la cay VUA DONG.
// Cuoi rebuild: chi ve InpSeKeep tin hieu moi nhat (port Pine trimLb/trimLn/trimBx).
// KHAC Pine 1 diem nho: duong SL cua chuoi KHONG bi trim theo so nay - no da co
// gioi han rieng bang InpSeSlBars (so nen), nen khong can cat them.
// dong chuoi cu tai endBar: neu !deleteOldSL thi ve duong SL cu (cat, khong ray) + label
// finalize chuoi dang hoat dong (cuoi loop): duong SL ray phai + label mep phai

//==================================================================
//   VE
//==================================================================
//--- lop chan doan: MOI khe ho dang nam trong kho (mot khe mot hop)
void DrawDiagFvg()
  {
   if(!InpDgShowAll) return;
   for(int i=0;i<fv_n;i++)
     {
      if(!fv[i].alive) continue;
      color c=Op(fv[i].bull? InpDgCBull : InpDgCBear, InpDgOp);
      Box(gT[fv[i].midAbs-1],fv[i].top,FwdT(fv[i].midAbs+1),fv[i].btm,c,InpDgStyle,InpDgBw);
     }
  }
//--- vach cuc tri CISD ("CISD Max")
void DrawCisdExt()
  {
   if(!InpCxShow) return;
   for(int k=0;k<cxOld_n;k++)
     {
      int i=cxOld[k];
      L(gT[cx[i].startAbs],cx[i].px,FwdT(cx[i].endAbs),cx[i].px,InpCxColOld,InpCxStyle,InpCxW);
      Txt(gT[cx[i].startAbs],cx[i].px,"P.CISD Max",InpCxColOld,TxPx(TXSZ_SMALL),ANCHOR_LEFT_LOWER);
     }
   int cur=CxCur();
   if(cur>=0)
     {
      L(gT[cx[cur].startAbs],cx[cur].px,FwdT(cx[cur].endAbs),cx[cur].px,InpCxColCur,InpCxStyle,InpCxW);
      Txt(gT[cx[cur].startAbs],cx[cur].px,"CISD Max",InpCxColCur,TxPx(TXSZ_SMALL),ANCHOR_LEFT_LOWER);
     }
  }
//--- cham nen cuc tri
void DrawExtDots()
  {
   if(!InpXdShow) return;
   color c=Dim(InpXdCol,50);
   for(int i=0;i<xd_n;i++)
      Arrow(gT[xdBar[i]],xdPx[i],159,c,1,(xdDir[i]==1)? ANCHOR_UPPER : ANCHOR_LOWER);
  }
//--- co che JUDAS
void DrawJudas()
  {
   if(!InpEnJudas) return;
   int keep=InpJdKeep; if(keep<1) keep=1;
   //--- 1) vach MSS: cu hong da bi xoa, cu bi day khoi mang giu N cung mat vach
   int lo=(jd_n>keep)? jd_n-keep : 0;
   for(int i=lo;i<jd_n;i++)
     {
      if(jd[i].dead && !jd[i].done) continue;      // cu hong -> XOA VACH
      color base=(jd[i].brkBar>=0)
                 ? ((jd[i].dir==1)? InpMssColBull  : InpMssColBear)
                 : ((jd[i].dir==1)? InpMssColBullW : InpMssColBearW);
      color c=Dim(base, jd[i].done? 0 : MssDim());
      int x2=jd[i].lnX2; if(x2<=jd[i].ancAbs) x2=jd[i].ancAbs+1;
      L(gT[jd[i].ancAbs],jd[i].lvl,FwdT(x2),jd[i].lvl,c,InpMssStyle,InpMssW);
      double off=jd[i].ancAtr*InpMssTxtGap;
      Txt(gT[jd[i].ancAbs],(jd[i].dir==1)? jd[i].lvl+off : jd[i].lvl-off,"MSS",c,
          TxPx(TXSZ_SMALL),(jd[i].dir==1)? ANCHOR_LOWER : ANCHOR_UPPER);
     }
   //--- 2) hinh tin hieu (mang rieng, cat theo cung so N)
   int sfrom=(jdsig_n>keep)? jdsig_n-keep : 0;
   for(int s=sfrom;s<jdsig_n;s++)
     {
      int i=jdsig[s];
      if(!jd[i].hasSig) continue;
      bool  isBuy=(jd[i].dir==1);
      int   tr=(jd[i].brkBar>=0)? 0 : JdSigDim();
      double k=(100.0-(double)tr)/100.0;
      color cJ=Dim(isBuy? InpJdColBull : InpJdColBear, tr);
      color cB=jd[i].bxBull? InpJdBoxBull : InpJdBoxBear;
      // hop khe ho VAO LENH: nen truoc, vien sau
      if(InpJdBoxFill>0)
         BoxFill(gT[jd[i].bxL],jd[i].bxTop,FwdT(jd[i].bxR),jd[i].bxBtm,Op(cB,InpJdBoxFill*k));
      Box(gT[jd[i].bxL],jd[i].bxTop,FwdT(jd[i].bxR),jd[i].bxBtm,Op(cB,InpJdBoxOp*k),InpJdBoxSty,InpJdBoxW);
      if(InpJdStem && jd[i].sigY!=jd[i].sigMkPx)
         L(gT[jd[i].sigMk],jd[i].sigMkPx,gT[jd[i].sigMk],jd[i].sigY,cJ,STYLE_DOT,1);
      Arrow(gT[jd[i].sigMk],jd[i].sigY,isBuy?233:234,cJ,ArrowW(InpJdTxSz),
            isBuy? ANCHOR_UPPER : ANCHOR_LOWER);
      if(InpJdShowTxt)
        {
         // MQL5 khong co label nhieu dong -> chu la object rieng, day them 0,5 ATR14.
         double tY=isBuy? (jd[i].sigY-jd[i].sigAtr*0.5) : (jd[i].sigY+jd[i].sigAtr*0.5);
         Txt(gT[jd[i].sigMk],tY,"JD",cJ,TxPx(InpJdTxSz),isBuy? ANCHOR_UPPER : ANCHOR_LOWER);
        }
     }
  }
//--- co che TURTLE SOUP
void DrawTurtle()
  {
   if(!InpEnTs) return;
   int keep=InpTsKeep; if(keep<1) keep=1;
   int lo=(ts_n>keep)? ts_n-keep : 0;
   for(int i=lo;i<ts_n;i++)
     {
      if(ts[i].dead && !ts[i].done) continue;
      color base=(ts[i].brkBar>=0)
                 ? ((ts[i].dir==1)? InpCisdColBull  : InpCisdColBear)
                 : ((ts[i].dir==1)? InpCisdColBullW : InpCisdColBearW);
      color c=Dim(base, ts[i].done? 0 : CisdDim());
      int x2=ts[i].lnX2; if(x2<=ts[i].ancAbs) x2=ts[i].ancAbs+1;
      L(gT[ts[i].ancAbs],ts[i].lvl,FwdT(x2),ts[i].lvl,c,InpCisdStyle,InpCisdW);
      // Chu CISD dat NGAY TAI CAY NEO, luon nam NGOAI cay nen, phia doi dien
      // voi huong gia sap di: cu MUA -> tren DINH cay neo, cu BAN -> duoi DAY.
      double off=ts[i].ancAtr*InpCisdTxtGap;
      double cY=(ts[i].dir==1)? ts[i].ancHi+off : ts[i].ancLo-off;
      Txt(gT[ts[i].ancAbs],cY,"CISD",c,TxPx(TXSZ_SMALL),
          (ts[i].dir==1)? ANCHOR_LOWER : ANCHOR_UPPER);
     }
   int sfrom=(tssig_n>keep)? tssig_n-keep : 0;
   for(int s=sfrom;s<tssig_n;s++)
     {
      int i=tssig[s];
      if(!ts[i].hasSig) continue;
      bool  isBuy=(ts[i].dir==1);
      int   tr=(ts[i].brkBar>=0)? 0 : TsSigDim();
      double k=(100.0-(double)tr)/100.0;
      color cT=Dim(isBuy? InpTsColBull : InpTsColBear, tr);
      color cB=ts[i].bxBull? InpTsBoxBull : InpTsBoxBear;
      if(InpTsBoxFill>0)
         BoxFill(gT[ts[i].bxL],ts[i].bxTop,FwdT(ts[i].bxR),ts[i].bxBtm,Op(cB,InpTsBoxFill*k));
      Box(gT[ts[i].bxL],ts[i].bxTop,FwdT(ts[i].bxR),ts[i].bxBtm,Op(cB,InpTsBoxOp*k),InpTsBoxSty,InpTsBoxW);
      if(InpTsStem && ts[i].sigY!=ts[i].sigMkPx)
         L(gT[ts[i].sigMk],ts[i].sigMkPx,gT[ts[i].sigMk],ts[i].sigY,cT,STYLE_DOT,1);
      Arrow(gT[ts[i].sigMk],ts[i].sigY,isBuy?233:234,cT,ArrowW(InpTsTxSz),
            isBuy? ANCHOR_UPPER : ANCHOR_LOWER);
      if(InpTsShowTxt)
        {
         double tY=isBuy? (ts[i].sigY-ts[i].sigAtr*0.5) : (ts[i].sigY+ts[i].sigAtr*0.5);
         Txt(gT[ts[i].sigMk],tY,"TS",cT,TxPx(InpTsTxSz),isBuy? ANCHOR_UPPER : ANCHOR_LOWER);
        }
     }
  }
//--- cum Daily Bias

void DrawAll()
  {
   DrawDiagFvg();      // ve truoc de hop chan doan nam duoi cac lop khac
   DrawCisdExt();
   DrawExtDots();
   DrawJudas();
   DrawTurtle();
   
  }

//==================================================================
//   REBUILD
//==================================================================
void ResetState()
  {
   fv_n=0;    ArrayResize(fv,1);
   jd_n=0;    ArrayResize(jd,1);
   jdsig_n=0; ArrayResize(jdsig,1);
   ts_n=0;    ArrayResize(ts,1);
   tssig_n=0; ArrayResize(tssig,1);
   cx_n=0;    ArrayResize(cx,1);
   cxOld_n=0; ArrayResize(cxOld,1);
   xd_n=0;    ArrayResize(xdBar,1); ArrayResize(xdPx,1); ArrayResize(xdDir,1);
   
   
   
   ci_bias=0; ci_orig=0.0; ci_oidx=-1; ci_thr=0.0; ci_init=false;
   se_chainDir=0; se_nextIdx=0; se_chainSL=0.0;
   se_prevRawLong=false; se_prevRawShort=false;
   se_hasChain=false; se_chainStartT=0; se_chainSLpx=0.0; se_chainBuy=false;
   se_sig_n=0; se_box_n=0;
   g_alJd=false; g_alTs=false;
   g_bhBlocked=0;
   g_alertMsg="";
   GsInit();
  }

// Nap o nhap cua indicator vao g_cfg. Engine trong crb_engine.mqh KHONG doc
// thang Inp* - day la cho duy nhat noi hai ben. CRB-EA-v3.mq5 co ham y het.
void CfgFill()
  {
   g_cfg.enJudas    = InpEnJudas;    g_cfg.enTs        = InpEnTs;
   g_cfg.jdDir      = InpJdDir;      g_cfg.jdSweep     = InpJdSweep;
   // Nhom 11: JdMultEff/TsMultEff da giai xong cong tac "de 0 = bang lai".
   g_cfg.jdFvgLen   = InpJdFvgLen;   g_cfg.jdFvgMult   = InpJdFvgMult;
   g_cfg.jdFvgWin   = InpJdFvgWin;   g_cfg.jdNeedMss   = InpJdNeedMss;
   g_cfg.jdAncBack  = InpJdAncBack;  g_cfg.jdKeep      = InpJdKeep;
   g_cfg.jdMark     = InpJdMark;     g_cfg.jdGap       = InpJdGap;
   g_cfg.mssLen     = InpMssLen;
   g_cfg.tsDir      = InpTsDir;      g_cfg.tsSweep     = InpTsSweep;
   g_cfg.tsFvgLen   = InpTsFvgLen;   g_cfg.tsFvgMult   = InpTsFvgMult;
   g_cfg.tsFvgWin   = InpTsFvgWin;   g_cfg.tsNeedCisd  = InpTsNeedCisd;
   g_cfg.tsNeedIfvg = InpTsNeedIfvg;
   g_cfg.tsKeep     = InpTsKeep;
   g_cfg.tsMark     = InpTsMark;     g_cfg.tsGap       = InpTsGap;
   g_cfg.cisdLen    = InpCisdLen;
   g_cfg.xdShow     = InpXdShow;     g_cfg.xdMode      = 0;
   g_cfg.xdKeep     = InpXdKeep;     g_cfg.cxShow      = InpCxShow;
   g_cfg.cxKeepOld  = InpCxKeepOld;  g_cfg.dgKeep      = InpDgKeep;
   // Nhom 12. BiasTfOk() gac khung: engine >= H1 thi bo loc TU VO HIEU.
   g_cfg.biasOn = false;
   g_cfg.biasDir    = g_bhDir;
  }

//==================================================================
//   13 - OLHC: CAU TRUC NEN.  Thu duy nhat v4 them so voi v3.
//
//   DOC LAP HOAN TOAN: khong doc mot bien nao cua JUDAS / TURTLE SOUP /
//   CRB / DAILY BIAS, khong di qua bo loc BIAS H1 cua nhom 12.
//
//   Doc THANG nen cua KHUNG CHART, KHONG phai khung engine (InpEngineTF).
//   Co y: ban Pine khong co o chon khung engine nen no luon doc nen chart;
//   lay theo engine la hai ban lech nhau ngay khi owner doi InpEngineTF.
//
//   Moi ket luan chi rut tu BON SO cua CHINH cay nen do. Ngoai le duy
//   nhat la o loc ATR - ATR bat buoc phai lay tu chuoi nen.
//
//   KHAC BAN PINE: ben Pine o "to mau ca cay nen" dung barcolor(), doi
//   thang mau nen cua chart. MT5 KHONG lam duoc - indicator khong doi
//   duoc mau nen. Thay bang OBJ_RECTANGLE to kin tu high xuong low, dat
//   BACK (sau nen) nen khong che gia. MQL5 khong co kenh alpha nen do mo
//   lam bang cach pha voi mau nen chart qua Dim().
//   Bu lai ben MT5 CA BA cach hien deu chiu o "so tin hieu giu lai" - ke
//   ca tam giac va khoi mau. Ben Pine thi khong: plotshape va barcolor
//   khong xoa lai duoc nen chung phu het lich su.
//==================================================================
int g_olAtrH = INVALID_HANDLE;

// Tra 1 = OHLC (giam), -1 = OLHC (tang), 0 = khong phan loai.
int OlClassify(const double o,const double h,const double l,const double c,const double atr)
  {
   double rng = h - l;
   if(rng <= 0.0) return 0;

   double uw = h - MathMax(o,c);
   double bd = MathAbs(c - o);
   double lw = MathMin(o,c) - l;

   double pUw = uw / rng * 100.0;
   double pBd = bd / rng * 100.0;
   double pLw = lw / rng * 100.0;

   bool shBear = (pUw >= InpOlGap1 && pBd <= InpOlGap2 && pLw <= InpOlGap3);
   bool shBull = (pLw >= InpOlGap1 && pBd <= InpOlGap2 && pUw <= InpOlGap3);
   // Ca hai cung dat thi bo - cay do khong nghieng han ve ben nao.
   if(shBear == shBull) return 0;

   if(InpOlUseK)
     {
      if(shBear && uw < InpOlK * lw) return 0;
      if(shBull && lw < InpOlK * uw) return 0;
     }

   if(InpOlAtrOn)
     {
      if(atr <= 0.0) return 0;
      if(rng < atr * InpOlAtrMult) return 0;
     }

   return shBear ? 1 : -1;
  }

void OlDrawMark(const datetime t,const double px,const bool bear)
  {
   string nm=PFX+"OL_MK_"+(string)(long)t;
   if(!ObjectCreate(0,nm,OBJ_TEXT,0,t,px)) return;
   // Ky tu VE LEN CHART, khong phai trang tri - ngoai le 1 muc 2 CLAUDE.md.
   ObjectSetString(0,nm,OBJPROP_TEXT, bear ? "▼" : "▲");
   ObjectSetString(0,nm,OBJPROP_FONT,"Arial");
   ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,InpOlMarkSz);
   ObjectSetInteger(0,nm,OBJPROP_COLOR, bear ? InpOlColBear : InpOlColBull);
   // bear -> dau nam TREN nen -> neo DAY chu vao gia high
   // bull -> dau nam DUOI nen -> neo DINH chu vao gia low
   ObjectSetInteger(0,nm,OBJPROP_ANCHOR, bear ? ANCHOR_LOWER : ANCHOR_UPPER);
   ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,nm,OBJPROP_BACK,false);
  }

void OlDrawLbl(const datetime t,const double px,const bool bear)
  {
   string nm=PFX+"OL_TX_"+(string)(long)t;
   if(!ObjectCreate(0,nm,OBJ_TEXT,0,t,px)) return;
   ObjectSetString(0,nm,OBJPROP_TEXT, bear ? "OHLC" : "OLHC");
   ObjectSetString(0,nm,OBJPROP_FONT,"Arial");
   ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,InpOlLblSz);
   ObjectSetInteger(0,nm,OBJPROP_COLOR, bear ? InpOlColBear : InpOlColBull);
   ObjectSetInteger(0,nm,OBJPROP_ANCHOR, bear ? ANCHOR_LOWER : ANCHOR_UPPER);
   ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,nm,OBJPROP_BACK,false);
  }

void OlDrawBox(const datetime t,const double hi,const double lo,const bool bear)
  {
   color col=Dim(bear ? InpOlColBear : InpOlColBull, InpOlBoxTr);
   if(col==clrNONE) return;
   string nm=PFX+"OL_BX_"+(string)(long)t;
   int half=PeriodSeconds()/2;
   if(!ObjectCreate(0,nm,OBJ_RECTANGLE,0,t-half,hi,t+half,lo)) return;
   ObjectSetInteger(0,nm,OBJPROP_COLOR,col);
   ObjectSetInteger(0,nm,OBJPROP_FILL,true);
   ObjectSetInteger(0,nm,OBJPROP_BACK,true);   // sau nen, khong che gia
   ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
  }

// Quet NGUOC tu nen da dong moi nhat ve qua khu, gom du InpOlKeep tin hieu
// roi dung. Nho vay CA BA cach hien deu chiu o gioi han.
void OlhcDraw()
  {
   if(!InpOlOn) return;

   int keep=InpOlKeep; if(keep<1) keep=1;
   int scan=InpOlScan; if(scan<keep) scan=keep;

   MqlRates rt[];
   ArraySetAsSeries(rt,true);
   int got=CopyRates(_Symbol,(ENUM_TIMEFRAMES)_Period,0,scan+2,rt);
   if(got<3) return;

   double atr[]; int nAtr=0;
   if(InpOlAtrOn)
     {
      if(g_olAtrH==INVALID_HANDLE) return;
      ArraySetAsSeries(atr,true);
      nAtr=CopyBuffer(g_olAtrH,0,0,got,atr);
      if(nAtr<=0) return;               // ATR chua san sang -> khong ve gi
     }

   // i = 1 la nen DA DONG moi nhat. i = 0 la nen dang chay, khong bao gio
   // duoc ve: O/H/L/C con doi thi phan loai con nhay.
   int n=0;
   for(int i=1;i<got && i<=scan && n<keep;i++)
     {
      double a=0.0;
      if(InpOlAtrOn)
        {
         if(i>=nAtr) break;             // het du lieu ATR thi dung han
         a=atr[i];
        }

      int sig=OlClassify(rt[i].open,rt[i].high,rt[i].low,rt[i].close,a);
      if(sig==0) continue;

      bool bear=(sig==1);
      if(InpOlBox)  OlDrawBox(rt[i].time,rt[i].high,rt[i].low,bear);
      if(InpOlMark) OlDrawMark(rt[i].time, bear ? rt[i].high : rt[i].low, bear);
      if(InpOlLbl)  OlDrawLbl(rt[i].time, bear ? rt[i].high : rt[i].low, bear);
      n++;
     }
  }

//+------------------------------------------------------------------+
//|  NHOM 14 - DUONG HOI QUY + PARABOL   (rieng ban v7, 25-08)        |
//|                                                                    |
//|  Port tu mt5/Indicators/Slope-Meter.mq5. Luat va cong thuc giu     |
//|  NGUYEN VAN - sua ben nay thi phai mang sang ben do, va nguoc lai. |
//|  Tai lieu: docs/slope-meter.md                                     |
//|                                                                    |
//|  Cum nay KHONG doc mot bien nao cua engine JD/TS/CRB. No tu doc    |
//|  nen bang CopyRates tren khung rieng cua no.                       |
//+------------------------------------------------------------------+
double   sl_bNorm  = 0.0;    // do doc trung binh ca cua so, x ATR
double   sl_bNormPrev = 0.0; // do doc trung binh cua so truoc
double   sl_bRaw   = 0.0;    // ... tinh bang gia
double   sl_r2     = 0.0;    // do khop cua duong thang
double   sl_p2Slope= 0.0;    // do doc TAI NEN CUOI, x ATR
double   sl_p2SlopePrev=0.0; // do doc nen truoc
double   sl_p2Acc  = 0.0;    // gia toc hien tai
double   sl_p2AccPrev = 0.0; // gia toc nen truoc
  double   sl_p2r2   = 0.0;    // do khop cua parabol
double   sl_p2a    = 0.0;    // he so bac 2
double   sl_p2b    = 0.0;
double   sl_p2c    = 0.0;
double   sl_y0     = 0.0;    // duong thang tai dau cua so
double   sl_y1     = 0.0;    // ... tai cuoi cua so
datetime sl_t0     = 0;
datetime sl_t1     = 0;
bool     sl_ok     = false;
bool     sl_p2ok   = false;
double   sl_mass   = 0.0;
double   sl_ek     = 0.0;
double   sl_ep     = 0.0;
double   sl_mom    = 0.0;
int      sl_cur_offset = 0;

int SlLenEff(){ int n=InpSlLen; if(n<3) n=3; if(n>500) n=500; return n; }
int SlAtrEff(){ int n=InpSlAtrLen; if(n<1) n=1; if(n>500) n=500; return n; }

ENUM_TIMEFRAMES SlTfEff()
  {
   if(InpSlAnchor == SL_ANCHOR_CISD) return EngineTf();
   return (InpSlTF==PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : InpSlTF;
  }

string SlTfName(ENUM_TIMEFRAMES tf)
  {
   string s=EnumToString(tf);
   if(StringFind(s,"PERIOD_")==0) s=StringSubstr(s,7);
   return s;
  }

string SlFmt(double v,int d)
  {
   string s=DoubleToString(v,d);
   if(v>0) s="+"+s;
   return s;
  }

double SlPx(const MqlRates &r)
  {
   switch(InpSlSrc)
     {
      case PRICE_OPEN:     return r.open;
      case PRICE_HIGH:     return r.high;
      case PRICE_LOW:      return r.low;
      case PRICE_MEDIAN:   return (r.high+r.low)/2.0;
      case PRICE_TYPICAL:  return (r.high+r.low+r.close)/3.0;
      case PRICE_WEIGHTED: return (r.high+r.low+2.0*r.close)/4.0;
      default:             return r.close;
     }
  }

//--- ATR Wilder tren mang rt ---------------------------------------
double SlAtr(const MqlRates &rt[],const int n,const int len)
  {
   if(n<len+1) return(0.0);
   double sum=0.0;
   for(int i=1;i<=len;i++)
      sum+=MathMax(rt[i].high-rt[i].low,
           MathMax(MathAbs(rt[i].high-rt[i-1].close),
                   MathAbs(rt[i].low -rt[i-1].close)));
   double a=sum/len;
   for(int i=len+1;i<n;i++)
     {
      double tr=MathMax(rt[i].high-rt[i].low,
                MathMax(MathAbs(rt[i].high-rt[i-1].close),
                        MathAbs(rt[i].low -rt[i-1].close)));
      a=(a*(len-1)+tr)/len;
     }
   return(a);
  }

//--- hoi quy bac 1, x = 0..N-1 -------------------------------------
bool SlLinReg(const MqlRates &rt[],const int end,const int N,const int offset,
              double &b,double &a,double &r2)
  {
   b=0.0; a=0.0; r2=0.0;
   int st=end-offset-N+1;
   if(st<0 || N<3) return(false);
   double sx=N*(N-1)/2.0;
   double sxx=(N-1)*N*(2.0*N-1)/6.0;
   double den=N*sxx-sx*sx;
   if(MathAbs(den)<1e-12) return(false);

   double sy=0.0, sxy=0.0;
   for(int k=0;k<N;k++){ double y=SlPx(rt[st+k]); sy+=y; sxy+=k*y; }
   b=(N*sxy-sx*sy)/den;
   a=(sy-b*sx)/N;

   double ybar=sy/N, ssTot=0.0, ssRes=0.0;
   for(int k=0;k<N;k++)
     {
      double y=SlPx(rt[st+k]), res=y-(a+b*k);
      ssTot+=(y-ybar)*(y-ybar);
      ssRes+=res*res;
     }
   r2=(ssTot>1e-12)? 1.0-ssRes/ssTot : 0.0;
   if(r2<0.0) r2=0.0;
   return(true);
  }

//--- hoi quy bac 2, x DAT O TAM cua so -----------------------------
bool SlLinReg2(const MqlRates &rt[],const int end,const int N,const int offset,const bool is3Point,
               double &a,double &b,double &c,double &r2)
  {
   a=0.0; b=0.0; c=0.0; r2=0.0;
   int st=end-offset-N+1;
   if(st<0 || N<3) return(false);

   double dN=(double)N;
   double half=(dN-1.0)/2.0;
   
   if(is3Point && offset > 0)
     {
      double x1 = -half;
      double x2 = half;
      double x3 = half + offset;
      double y1 = SlPx(rt[st]);
      double y2 = SlPx(rt[st + N - 1]);
      double y3 = SlPx(rt[end]);

      double denom = (x1 - x2) * (x1 - x3) * (x2 - x3);
      if(MathAbs(denom) < 1e-12) return(false);

      a = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / denom;
      b = (x3 * x3 * (y1 - y2) + x2 * x2 * (y3 - y1) + x1 * x1 * (y2 - y3)) / denom;
      c = (x2 * x3 * (x2 - x3) * y1 + x3 * x1 * (x3 - x1) * y2 + x1 * x2 * (x1 - x2) * y3) / denom;
      r2 = 1.0;
      return(true);
     }

   double S2=(dN*dN*dN-dN)/12.0;
   double S4=dN*(dN*dN-1.0)*(3.0*dN*dN-7.0)/240.0;
   double den=dN*S4-S2*S2;
   if(S2<=0.0 || MathAbs(den)<1e-12) return(false);

   double T0=0.0,T1=0.0,T2=0.0;
   for(int k=0;k<N;k++)
     {
      double x=k-half, y=SlPx(rt[st+k]);
      T0+=y; T1+=x*y; T2+=x*x*y;
     }
   b=T1/S2;
   a=(dN*T2-S2*T0)/den;
   c=(T0-S2*a)/dN;

   double ybar=T0/dN, ssTot=0.0, ssRes=0.0;
   for(int k=0;k<N;k++)
     {
      double x=k-half, y=SlPx(rt[st+k]);
      double res=y-(c+b*x+a*x*x);
      ssTot+=(y-ybar)*(y-ybar);
      ssRes+=res*res;
     }
   r2=(ssTot>1e-12)? 1.0-ssRes/ssTot : 0.0;
   if(r2<0.0) r2=0.0;
   return(true);
  }

//--- do mot lan, lay ket qua cua CUA SO GAN NHAT --------------------
void SlCompute()
  {
   sl_ok=false; sl_p2ok=false;
   if(!InpSlOn) return;

   int N=SlLenEff();
   sl_cur_offset = 0;
   bool is3Point = false;
   if(InpSlAnchor == SL_ANCHOR_CISD)
     {
      if(cx_n >= 2)
        {
         int lastAbs = cx[cx_n-1].startAbs;
         int prevAbs = cx[cx_n-2].startAbs;
         N = (int)MathMin(1500, MathMax(3, lastAbs - prevAbs + 1));
         sl_cur_offset = gN - 1 - lastAbs;
         if (sl_cur_offset < 0) sl_cur_offset = 0;
         is3Point = true;
        }
     }

   int maxMA=(int)MathMax(InpVolMaLen, InpBaseMaLen);
   MqlRates rt[];
   ArraySetAsSeries(rt,false);
   int got=CopyRates(_Symbol,SlTfEff(),0,N+sl_cur_offset+SlAtrEff()+maxMA+50,rt);
   if(got<N+sl_cur_offset+2) return;

   // Lay ATR tai diem neo cuoi (last - offset) giong nhu Pine Script ta.atr[offset]
   double atr=SlAtr(rt,got-sl_cur_offset,SlAtrEff());
   int last=got-1;

   double bb,aa,rr;
   sl_ok=SlLinReg(rt,last,N,sl_cur_offset,bb,aa,rr);
   if(sl_ok)
     {
      sl_bRaw = bb;
      sl_r2   = rr;
      sl_bNorm= (atr>0.0)? bb/atr : 0.0;
      
      sl_bNormPrev = 0.0;
      double pbb, paa, prr;
      if(last>0 && SlLinReg(rt,last-1,N,sl_cur_offset,pbb,paa,prr))
        {
         sl_bNormPrev = (atr>0.0)? pbb/atr : 0.0;
        }

      sl_t0   = rt[last-sl_cur_offset-N+1].time;
      sl_t1   = rt[last-sl_cur_offset].time;
      sl_y0   = aa;
      sl_y1   = aa+bb*(N-1);
      
      sl_mass = 1.0;
      sl_ek   = 0.0;
      sl_ep   = 0.0;
      sl_mom  = 0.0;
      
      if(InpEnergyOn)
        {
         double sumV = 0;
         for(int k=0; k<N; k++) sumV += (double)rt[last-sl_cur_offset-N+1+k].tick_volume;
         double avgV = sumV / N;
         
         double sumMA = 0;
         int p = InpVolMaLen;
         if(p > last+1) p = last+1;
         if(p <= 0) p = 1;
         for(int k=0; k<p; k++) sumMA += (double)rt[last-k].tick_volume;
         double avgMA = sumMA / p;
         
         double mass = (avgMA > 0) ? (avgV / avgMA) : 1.0;
         if(mass > 3.0) mass = 3.0;
         sl_mass = mass;
         
         double vv = sl_bNorm; 
         sl_ek = 0.5 * mass * vv * MathAbs(vv) * 100.0;
         sl_mom = mass * vv;
         
         double sumBase = 0;
         int bMA = InpBaseMaLen;
         if(bMA <= 0) bMA = N;
         if(bMA > last+1) bMA = last+1;
         for(int k=0; k<bMA; k++) sumBase += SlPx(rt[last-k]);
         double avgBase = sumBase / bMA;
         
         double omega = (bMA > 0) ? (2.0 * 3.1415926535 / bMA) : 1.0;
         double ybar = aa + bb * (N - 1.0) / 2.0;
         double x = (atr > 0) ? (ybar - avgBase) / atr : 0.0;
         sl_ep = 0.5 * mass * MathPow(omega * x, 2) * 100.0;
        }
     }

   double q2a,q2b,q2c,q2r2;
   sl_p2ok=SlLinReg2(rt,last,N,sl_cur_offset,is3Point,q2a,q2b,q2c,q2r2);
   if(sl_p2ok)
     {
      sl_p2a=q2a; sl_p2b=q2b; sl_p2c=q2c; sl_p2r2=q2r2;
      double half = (N-1.0)/2.0;
      double k = (is3Point && InpSlKAmp > 0.0 && InpSlLen > 0) ? MathPow((double)N / InpSlLen, InpSlKAmp) : 1.0;
      double slp = q2b + 2.0 * q2a * (half + sl_cur_offset);
      sl_p2Slope=(atr>0.0)? (slp/atr)*k : 0.0;
      sl_p2Acc  =(atr>0.0)? (2.0*q2a/atr)*k*k : 0.0;
      
      double pq2a,pq2b,pq2c,pq2r2;
      sl_p2AccPrev = 0.0;
      sl_p2SlopePrev = 0.0;
      if(last>0 && SlLinReg2(rt,last-1,N,sl_cur_offset,is3Point,pq2a,pq2b,pq2c,pq2r2))
        {
         double pslp = pq2b + 2.0 * pq2a * (half + sl_cur_offset);
         sl_p2AccPrev = (atr>0.0)? (2.0*pq2a/atr)*k*k : 0.0;
         sl_p2SlopePrev = (atr>0.0)? (pslp/atr)*k : 0.0;
        }
     }
  }

//--- L() co san khong co tia -> ban rieng cho cum nay ---------------
void SlLine(datetime t1,double p1,datetime t2,double p2,color c,
            ENUM_LINE_STYLE st,int w,bool ray)
  {
   string nm=PFX+"SL"+IntegerToString(g_objId++);
   if(!ObjectCreate(0,nm,OBJ_TREND,0,t1,p1,t2,p2)) return;
   ObjectSetInteger(0,nm,OBJPROP_COLOR,c);
   ObjectSetInteger(0,nm,OBJPROP_STYLE,st);
   ObjectSetInteger(0,nm,OBJPROP_WIDTH,w);
   ObjectSetInteger(0,nm,OBJPROP_RAY_RIGHT,ray);
   ObjectSetInteger(0,nm,OBJPROP_RAY_LEFT,false);
   ObjectSetInteger(0,nm,OBJPROP_BACK,false);
   ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
  }

//--- mau theo do doc ------------------------------------------------
color SlColOf()
  {
   if(!sl_ok) return(InpSlColFlat);
   if(sl_bNorm> InpSlFlat) return(InpSlColUp);
   if(sl_bNorm<-InpSlFlat) return(InpSlColDn);
   return(InpSlColFlat);
  }

//+------------------------------------------------------------------+
//|  Ve doan thang + duong cong. So diem lay mau CHOT O 31 (30 doan), |
//|  dung con so cua Slope-Meter de hai ban ve trung khit.            |
//+------------------------------------------------------------------+
#define SL_PTS 31

void SlDraw()
  {
   if(!InpSlOn) return;

   if(InpSlSeg && sl_ok)
      SlLine(sl_t0,sl_y0,sl_t1,sl_y1,SlColOf(),InpSlSegSty,
             MathMax(1,InpSlSegW),InpSlSegRay);

   if(!InpSlP2 || !sl_p2ok) return;

   int N=SlLenEff();
   int offset = sl_cur_offset;
   int totalDraw = N + offset;
   
   MqlRates rt[];
   ArraySetAsSeries(rt,false);
   int got=CopyRates(_Symbol,SlTfEff(),0,totalDraw+5,rt);
   if(got<totalDraw) return;

   int st=got-totalDraw;
   int P=(totalDraw<SL_PTS)? totalDraw : SL_PTS;
   if(P<2) return;

   color c=(sl_p2a>=0.0)? InpSlP2Up : InpSlP2Dn;
   double half=(N-1)/2.0;
   datetime tPrev=0;
   double   yPrev=0.0;
   for(int i=0;i<P;i++)
     {
      int kk=(int)MathRound((double)i*(totalDraw-1)/(P-1));
      if(kk<0) kk=0;
      if(kk>totalDraw-1) kk=totalDraw-1;
      double xx=kk-half;
      double y=sl_p2c+sl_p2b*xx+sl_p2a*xx*xx;
      datetime t=rt[st+kk].time;
      if(i>0 && t!=tPrev)
         SlLine(tPrev,yPrev,t,y,c,InpSlP2Sty,MathMax(1,InpSlP2W),false);
      tPrev=t;
      yPrev=y;
     }
  }

//+------------------------------------------------------------------+
//|  NHOM 15 - DASHBOARD                                              |
//|                                                                    |
//|  KET LUAN xet DU BA THU chu khong moi do doc: duong cong khop hon  |
//|  han -> DANG CONG (dung doc do doc); ca hai khong khop -> GIA LOAN;|
//|  duong thang khop tot -> moi doc huong, va con so DOC LUC NAY voi  |
//|  nguong di ngang de biet da con suc khong.                         |
//+------------------------------------------------------------------+
void DbCell(string tag,int row,int col,ENUM_BASE_CORNER cn,
            int x,int y,string txt,color c,int fs,bool left,string tip)
  {
   string nm=PFX+"DB"+tag+IntegerToString(row)+IntegerToString(col);
   if(ObjectFind(0,nm)<0)
     {
      ObjectCreate(0,nm,OBJ_LABEL,0,0,0);
      ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
     }
   ObjectSetInteger(0,nm,OBJPROP_CORNER,cn);
   ObjectSetInteger(0,nm,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,nm,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,nm,OBJPROP_ANCHOR,left?ANCHOR_LEFT_UPPER:ANCHOR_RIGHT_UPPER);
   ObjectSetInteger(0,nm,OBJPROP_BACK,false);
   ObjectSetString (0,nm,OBJPROP_TEXT,txt);
   ObjectSetString (0,nm,OBJPROP_FONT,"Consolas");
   ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,fs);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,c);
   ObjectSetString (0,nm,OBJPROP_TOOLTIP,tip);
  }

//--- cu gan nhat cua mot co che, dang chuoi de in ra bang ----------
string DbMechTxt(const bool isJd,color &col)
  {
   col=InpDbColTx;
   int n = isJd ? jd_n : ts_n;
   if(n<=0) return("chua co");

   int  dir=0, sigBar=-1;
   bool done=false, dead=false;
   if(isJd)
     { dir=jd[n-1].dir; done=jd[n-1].done; dead=jd[n-1].dead; sigBar=jd[n-1].sigBar; }
   else
     { dir=ts[n-1].dir; done=ts[n-1].done; dead=ts[n-1].dead; sigBar=ts[n-1].sigBar; }

   string s=(dir==1? "BUY" : "SELL");
   if(dead){ col=InpSlColFlat; return(s+" hong"); }
   if(!done)      return(s+" cho");
   col=(dir==1? InpSlColUp : InpSlColDn);
   if(sigBar>=0 && sigBar<gN) return(s+" "+TimeToString(gT[sigBar],TIME_MINUTES));
   return(s+" xong");
  }

void DbDraw()
  {
   if(!InpDbShow){ ObjectsDeleteAll(0,PFX+"DB"); return; }

   ENUM_BASE_CORNER cn=CORNER_RIGHT_UPPER;
   if(InpDbPos==TFP_TL) cn=CORNER_LEFT_UPPER;
   if(InpDbPos==TFP_BR) cn=CORNER_RIGHT_LOWER;
   if(InpDbPos==TFP_BL) cn=CORNER_LEFT_LOWER;
   bool left=(InpDbPos==TFP_TL || InpDbPos==TFP_BL);

   int fs=MathMax(6,InpDbFont);
   int rowH=(int)(fs*3.0), pad=10;
   int colN=(int)(fs*16.0), colV=(int)(fs*40.0);
   int W=pad*2+colN+colV;
   int rows = 7 + (InpDbMech ? 3 : 0);   // Giong 100% Pine Mini
   int H=pad*2+rowH*rows;

   int y0=InpDbY;
   if(InpDbPos==TFP_MR)
     {
      int chH=(int)ChartGetInteger(0,CHART_HEIGHT_IN_PIXELS);
      y0=MathMax(0,(chH-H)/2);
     }

   string bg=PFX+"DBBG";
   if(ObjectFind(0,bg)<0)
     {
      ObjectCreate(0,bg,OBJ_RECTANGLE_LABEL,0,0,0);
      ObjectSetInteger(0,bg,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,bg,OBJPROP_HIDDEN,true);
      ObjectSetInteger(0,bg,OBJPROP_BORDER_TYPE,BORDER_FLAT);
      ObjectSetInteger(0,bg,OBJPROP_WIDTH,1);
     }
   ObjectSetInteger(0,bg,OBJPROP_CORNER,cn);
   ENUM_ANCHOR_POINT bg_anch = ANCHOR_RIGHT_UPPER;
   if(InpDbPos==TFP_TL) bg_anch = ANCHOR_LEFT_UPPER;
   if(InpDbPos==TFP_BR) bg_anch = ANCHOR_RIGHT_LOWER;
   if(InpDbPos==TFP_BL) bg_anch = ANCHOR_LEFT_LOWER;
   ObjectSetInteger(0,bg,OBJPROP_ANCHOR,bg_anch);
   ObjectSetInteger(0,bg,OBJPROP_XDISTANCE,InpDbX);
   ObjectSetInteger(0,bg,OBJPROP_YDISTANCE,y0);
   ObjectSetInteger(0,bg,OBJPROP_XSIZE,W);
   ObjectSetInteger(0,bg,OBJPROP_YSIZE,H);
   int tr=InpDbTrans; if(tr<0) tr=0; if(tr>95) tr=95;
   color cBg=Blend(InpDbColBg,BgColor(),tr/100.0);
   ObjectSetInteger(0,bg,OBJPROP_BGCOLOR,cBg);
   ObjectSetInteger(0,bg,OBJPROP_COLOR,cBg);

   //--- KET LUAN ---
   string sSta="CHO NEN";
   color  cSta=InpSlColFlat;
   string sDesc="Chua du du lieu nen";
   string sAct="Dung ngoai cho nen";
   bool haveP2=(InpSlOn && sl_p2ok);

   if(sl_ok)
     {
      bool loan=(sl_r2<InpSlR2Min) && (!haveP2 || sl_p2r2<InpSlR2Min);
      bool cong=haveP2 && (sl_p2r2>=InpSlR2Min) && ((sl_p2r2-sl_r2)>=InpSlR2Gap);
      
      if(loan)
        {
         sSta="NHIEU LOAN";
         sDesc="Hanh vi gia nhieu loan (Choppy)";
         sAct="Khong giao dich (No Trade Zone)";
        }
      else if(InpEnergyOn)
        {
         if(MathAbs(sl_bNorm) <= InpSlFlat)
           {
            sSta="TICH LUY";
            cSta=clrMagenta;
            sDesc="Gia nen chat trong bien do hep (Consolidation)";
            sAct="Cho doi Breakout xac nhan";
           }
         else
           {
            bool isUptrend = (sl_bNorm > 0);
            bool isBraking = (haveP2 && ((isUptrend && sl_p2Acc < 0) || (!isUptrend && sl_p2Acc > 0)));
            bool epDominates = (MathAbs(sl_ep) >= MathAbs(sl_ek));
            bool isP2Flip = (haveP2 && ((isUptrend && sl_p2Slope < 0) || (!isUptrend && sl_p2Slope > 0)));
            
            if(isBraking)
              {
               if(epDominates)
                 {
                  if(isP2Flip)
                    {
                     sSta="DAO CHIEU XAC NHAN";
                     cSta=isUptrend?InpSlP2Dn:InpSlP2Up;
                     sDesc="Gia toc dao chieu. Cau truc gia thay doi";
                     sAct="Tim kiem Entry dao chieu (Reversal)";
                    }
                  else
                    {
                     sSta="KIET SUC (CANG MAX)";
                     cSta=isUptrend?InpSlP2Dn:InpSlP2Up;
                     sDesc="Da gia mo rong qua muc (Overextended)";
                     sAct="Chuan bi kich ban dao chieu (Reversal)";
                    }
                 }
               else
                 {
                  if(isP2Flip)
                    {
                     sSta="PULLBACK SAU";
                     cSta=C'255,167,38'; // Orange
                     sDesc="Retracement sau ve Discount/Premium";
                     sAct="Tim kiem Entry thuan xu huong";
                    }
                  else
                    {
                     sSta="PULLBACK NHE";
                     cSta=C'255,167,38'; // Orange
                     sDesc="Nhip hoi ngan. Xung luong chinh van manh";
                     sAct="Chot loi ngan. KHONG bat dinh/day";
                    }
                 }
              }
            else
              {
               if(!epDominates)
                 {
                  sSta="BUNG NO THUC SU";
                  cSta=isUptrend?InpSlColUp:InpSlColDn;
                  sDesc="Dot pha dong luong, Volume YEU";
                  sAct="Canh giac Fakeout/Stop Hunt. Scalp hoac Nghi";
                 }
               else
                 {
                  if(sl_mass > 1.5)
                    {
                     sSta="QUAN TINH (" + string(isUptrend?"TANG":"GIAM") + ")";
                     cSta=isUptrend?InpSlColUp:InpSlColDn;
                     sDesc="Dong luong duy tri, Volume doi dao";
                     sAct="Nam giu lenh thuan xu huong";
                    }
                  else
                    {
                     sSta="TICH LUY";
                     cSta=clrMagenta;
                     sDesc="Gia nen chat trong bien do hep (Consolidation)";
                     sAct="Cho doi Breakout xac nhan";
                    }
                 }
              }
           }
        }
      else if(cong) // Legacy State Machine
        {
         sSta="CHUYEN HUONG";
         cSta=(sl_p2a>=0.0)? InpSlP2Up : InpSlP2Dn;
         sDesc="Cau truc gia chuyen pha, chua ro xu huong";
         sAct="Dung ngoai quan sat";
        }
      else if(sl_bNorm>InpSlFlat)
        {
         if(haveP2 && sl_p2Slope<=InpSlFlat)
           { sSta="KIET SUC (TANG)"; cSta=InpSlP2Dn;
             sDesc="Xung luong Tang suy yeu dan"; sAct="Canh chot loi (Take Profit)"; }
         else
           { sSta="TANG"; cSta=InpSlColUp;
             sDesc="Xu huong Tang on dinh"; sAct="Follow Trend"; }
        }
      else if(sl_bNorm<-InpSlFlat)
        {
         if(haveP2 && sl_p2Slope>=-InpSlFlat)
           { sSta="KIET SUC (GIAM)"; cSta=InpSlP2Up;
             sDesc="Xung luong Giam suy yeu dan"; sAct="Canh chot loi (Take Profit)"; }
         else
           { sSta="GIAM"; cSta=InpSlColDn;
             sDesc="Xu huong Giam on dinh"; sAct="Follow Trend"; }
        }
      else
        {
         sSta="DI NGANG";
         sDesc="Gia di ngang (Ranging)";
         sAct="Khong giao dich (No Trade Zone)";
        }
     }

   color cR2=InpDbColTx;  if(sl_ok   && sl_r2  <InpSlR2Min) cR2 =InpSlColDn;
   color cR22=InpDbColTx; if(sl_p2ok && sl_p2r2<InpSlR2Min) cR22=InpSlColDn;
   color cP2S=InpSlColFlat;
   if(sl_p2ok && sl_p2Slope> InpSlFlat) cP2S=InpSlColUp;
   if(sl_p2ok && sl_p2Slope<-InpSlFlat) cP2S=InpSlColDn;
   color cAcc=InpSlColFlat;
   if(sl_p2ok && sl_p2Acc>0.0) cAcc=InpSlP2Up;
   if(sl_p2ok && sl_p2Acc<0.0) cAcc=InpSlP2Dn;

   int xN=left? InpDbX+pad   : InpDbX+W-pad;
   int xV=left? InpDbX+W-pad : InpDbX+pad;
   int digs=(int)MathMax(2,_Digits);

   string vWin  = SlTfName(SlTfEff())+" x "+IntegerToString(SlLenEff());
   string vSlope = "-";
   if (sl_ok)
     {
      string s1Dir = "";
      double curS1 = MathAbs(sl_bNorm);
      double prevS1 = MathAbs(sl_bNormPrev);
      if(curS1 > prevS1) s1Dir = " (Tang)";
      else if(curS1 < prevS1) s1Dir = " (Giam)";
      vSlope = SlFmt(sl_bNormPrev, 2) + " -> " + SlFmt(sl_bNorm, 2) + s1Dir;
     }
   string vRaw  = sl_ok  ? SlFmt(sl_bRaw,digs)         : "-";
   string vR2   = sl_ok  ? DoubleToString(sl_r2,2)     : "-";
   string vP2S = "-";
   if (sl_p2ok)
     {
      string slpDir = "";
      double curSlp = MathAbs(sl_p2Slope);
      double prevSlpAbs = MathAbs(sl_p2SlopePrev);
      if(curSlp > prevSlpAbs) slpDir = " (Tang)";
      else if(curSlp < prevSlpAbs) slpDir = " (Giam)";
      vP2S = SlFmt(sl_p2SlopePrev, 2) + " -> " + SlFmt(sl_p2Slope, 2) + slpDir;
     }
   string vAcc  = "-";
     if(sl_p2ok)
       {
        string accDir = "";
        double curAcc = MathAbs(sl_p2Acc);
        double prevAccAbs = MathAbs(sl_p2AccPrev);
        if(curAcc > prevAccAbs) accDir = " (Tang)";
        else if(curAcc < prevAccAbs) accDir = " (Giam)";
        vAcc = SlFmt(sl_p2AccPrev, 3) + " -> " + SlFmt(sl_p2Acc, 3) + accDir;
       }
   string vR22  = sl_p2ok? DoubleToString(sl_p2r2,2)   : "-";

   string vMass = (InpEnergyOn && sl_ok) ? DoubleToString(sl_mass,2)+"x" : "-";
   string vMom  = (InpEnergyOn && sl_ok) ? SlFmt(sl_mom,2) : "-";
   string vEk   = (InpEnergyOn && sl_ok) ? SlFmt(sl_ek,2)  : "-";
   string vEp   = (InpEnergyOn && sl_ok) ? SlFmt(sl_ep,2)  : "-";


   color cJd=InpDbColTx, cTs=InpDbColTx;
   string vJd=DbMechTxt(true ,cJd);
   string vTs=DbMechTxt(false,cTs);
   //--- kho khe ho: dem thang tu engine. Day la o tra loi cau "sao khong
   //    hien FVG nao" - kho rong thi khong co gi de ve, va cung khong co
   //    gi cho hai co che chon vao lenh.
   int fvAlive=0;
   for(int i=0;i<fv_n;i++) if(fv[i].alive) fvAlive++;
   string vFv=IntegerToString(fv_n)+" (tuoi "+IntegerToString(fvAlive)+")";
   color  cFv=(fv_n==0)? InpSlColDn : InpDbColTx;

   string vBh=(g_bhDir==1? "BUY" : (g_bhDir==-1? "SELL" : "chua co"));
   color  cBh=(g_bhDir==1? InpSlColUp : (g_bhDir==-1? InpSlColDn : InpSlColFlat));
   if(!false){ vBh=vBh+" (loc tat)"; }

   string tWin="Cum do doc dang do tren nen "+SlTfName(SlTfEff())+", moi lan lay "
               +IntegerToString(SlLenEff())+" nen gan nhat.\n"
               +"Khung nay RIENG, khong dinh gi toi khung cua engine JD/TS.";
   string tSlope="Trung binh moi nen gia di duoc bao nhieu, theo BIEN DO trung\n"
                 +"binh mot nen (ATR).\n\n  0.00-0.10 di ngang   0.10-0.30 nhe\n"
                 +"  0.30-0.60 ro       tren 0.60 rat manh";
   string tRaw ="Cung con so tren nhung tinh bang TIEN.";
   string tR2  ="Duong thang bam sat gia den muc nao, tu 0 den 1.\n"
                +"LUON NHIN O NAY TRUOC khi tin dong 'Do doc'.\n"
                +"Duoi "+DoubleToString(InpSlR2Min,2)+" thi to DO.";
   string tP2S ="Do doc TAI NEN MOI NHAT, khac dong 'Do doc' o tren la trung\n"
                +"binh ca cua so. Hai so lech nhieu = gia dang doi nhip.";
   string tAcc ="Gia dang NHANH DAN hay CHAM LAI. Nguoc dau voi do doc la\n"
                +"DANG DUOI SUC. So nay be va nhieu, dung doc mot minh.";
   string tR22 ="Duong CONG bam sat gia den muc nao. Cao hon han 'Do tin cay'\n"
                +"nghia la gia dang cong, do doc thanh so rac.";
   string tFv="So khe ho dang nam trong kho, va bao nhieu cai con TUOI\n"
              +"(chua bi lap). Mot khe duoc ghi vao kho khi no dat NGUONG\n"
              +"LONG HON trong hai nguong cua hai co che.\n\n"
              +"O NAY = 0 nghia la khong khe nao du rong: hai co che khong\n"
              +"co gi de chon, nen KHONG the ra tin hieu du engine van chay.\n"
              +"Luc do ha he so be rong khe ho o nhom 2 va nhom 4 xuong.";
   string tMech="Cu gan nhat cua co che nay. Luat van chay du ngay ca khi\n"
                +"CHE DO GON dang chan phan ve tren chart.";
   string tBh  ="Chieu bias lay tu engine chay lai tren du lieu H1.\n"
                +"Ghi '(loc tat)' nghia la bias co tinh nhung KHONG chan gi.";

   bool isLower = (cn==CORNER_RIGHT_LOWER || cn==CORNER_LEFT_LOWER);
   for(int i=0;i<rows;i++)
     {
      int y = isLower ? (y0 + H - pad - rowH*i) : (y0 + pad + rowH*i);
      string nm="", vl="", tp=""; color cv=InpDbColTx;
      int idx = 0;
      
      if(i==idx){ nm=" ";           vl=vWin;   tp=tWin;   } idx++;
      if(i==idx){ nm="Do doc 1";    vl=vSlope; tp=tSlope; } idx++;
      if(i==idx){ nm="Do tin cay";  vl=vR2;    tp=tR2;    } idx++;
      if(i==idx){ nm="Do doc 2";    vl=vP2S;   tp=tP2S;   } idx++;
      if(i==idx){ nm=" ";           vl=vAcc;   tp=tAcc;   cv=cAcc; } idx++;
      
      if(i==idx){ nm=" ";           vl=sSta;   cv=cSta; } idx++;
      if(i==idx){ nm=" ";           vl=sDesc;  } idx++;
      if(i==idx){ nm=" ";           vl=sAct;   cv=clrYellow; } idx++;
      
      if(InpDbMech) {
         if(i==idx){ nm="JUDAS";      vl=vJd; tp=tMech; cv=cJd; } idx++;
         if(i==idx){ nm="T.SOUP";     vl=vTs; tp=tMech; cv=cTs; } idx++;
         if(i==idx){ nm="BIAS H1";    vl=vBh; tp=tBh;   cv=cBh; } idx++;
      }
      
      DbCell("N",i,0,cn,xN,y,nm,clrGray,fs,true ,tp);
      DbCell("V",i,1,cn,xV,y,vl,clrGray,          fs,false,tp);
     }
  }

void Rebuild(const int rates_total)
  {
   MqlRates rt[];
   ArraySetAsSeries(rt,false);
   CopyRates(_Symbol,_Period,0,rates_total,rt);

   CfgFill();
   ObjectsDeleteAll(0,PFX);
   g_objId=0;
   ResetState();

   gN=rates_total;
   int warm=MathMax(MathMax(InpJdFvgLen,InpTsFvgLen),20)+5;
   int wb=InpWinBars; if(wb<200) wb=200; if(wb>5000) wb=5000;
   int b0=InpUseWin? MathMax(warm,rates_total-wb) : warm;
   if(b0<warm) b0=warm;
   if(b0>=rates_total-1) return;

   ComputeAtr();

   bool anyMech=(InpEnJudas || InpEnTs);

   for(int b=b0;b<rates_total;b++)
     {
      // Chi chay tren nen DA DONG (khop Pine: moi lop deu gate barstate.isconfirmed).
      if(b >= rates_total-1) continue;
      if(InpMbOn) MbProcessBar(b);
      if(InpGsOn) GsProcessBar(b);
      if(InpFvgOn) FvgMtfProcessBar(b);
      if(anyMech)
        {
         FvProcessBar(b);      // kho khe ho chay TRUOC may CISD trong cung nen
         CiProcessBar(b);

         if(InpEnJudas) JdUpdateBar(b);
         if(InpEnTs)    TsUpdateBar(b);
         CxUpdateBar(b);
        }
     }

   // CHE DO GON (nhom 14): chan phan VE cua nhom 1..13, LUAT VAN CHAY DU
   // ben tren - bang van biet cu JD/TS gan nhat, bias H1 van tinh.

   //==================================================================
   // DISPLACEMENT SOM (V7)
   //==================================================================
   if(InpDispOn)
     {
      int b = rates_total - 1; // nen hien tai
      double myAtr14 = gA14[b];
      
      // Tinh avgVol20
      double avgVol20 = 0;
      int p = 20;
      if(p > rates_total) p = rates_total;
      if(p > 0) {
         double sumV = 0;
         for(int k=0; k<p; k++) sumV += (double)rt[b-k].tick_volume;
         avgVol20 = sumV / p;
      }
      
      double bodySize = MathAbs(gC[b] - gO[b]);
      double topWick = gH[b] - MathMax(gC[b], gO[b]);
      double btmWick = MathMin(gC[b], gO[b]) - gL[b];
      
      double prevAcc = 0;
      if (b > 0) prevAcc = sl_p2Acc; // Chu y: Can track mang sl_p2Acc neu muon chinh xac, o day dung tam gia tri sl_p2Acc tinh toan o tren.

      bool accSurging = (!InpDispAccSurging) || (MathAbs(sl_p2Acc) > MathAbs(prevAcc));
      bool accBuyOk = (!InpDispUseAcc) || (sl_p2Acc > 0 && accSurging);
      bool accSellOk = (!InpDispUseAcc) || (sl_p2Acc < 0 && accSurging);
      
      bool isDispBuy = (gC[b] > gO[b]) && (bodySize > InpDispAtrMult * myAtr14) && (rt[b].tick_volume > InpDispVolMult * avgVol20) && (topWick < InpDispWickPct * bodySize) && accBuyOk;
      bool isDispSell = (gC[b] < gO[b]) && (bodySize > InpDispAtrMult * myAtr14) && (rt[b].tick_volume > InpDispVolMult * avgVol20) && (btmWick < InpDispWickPct * bodySize) && accSellOk;
      
      if(InpDispShowShape)
        {
         if(isDispBuy) Txt(gT[b], gL[b] - 0.5 * myAtr14, "▲", InpDispColBuy, 14, ANCHOR_UPPER);
         if(isDispSell) Txt(gT[b], gH[b] + 0.5 * myAtr14, "▼", InpDispColSell, 14, ANCHOR_LOWER);
        }
     }
     
   //==================================================================
   // INSIDE & OUTSIDE BAR
   //==================================================================
   if(InpInOutOn && rates_total > 1)
     {
      int b = rates_total - 1;
      bool insidebuybar = InpShowInside && gC[b] > gO[b] && gH[b] <= gH[b-1] && gL[b] >= gL[b-1];
      bool insidesellbar = InpShowInside && gC[b] < gO[b] && gH[b] <= gH[b-1] && gL[b] >= gL[b-1];
      bool outsidebuybar = InpShowOutside && gC[b] > gO[b] && gH[b] > gH[b-1] && gL[b] < gL[b-1];
      bool outsidesellbar = InpShowOutside && gC[b] < gO[b] && gH[b] > gH[b-1] && gL[b] < gL[b-1];
      
      double myAtr14 = gA14[b];
      
      if(insidebuybar) Txt(gT[b], gL[b] - 0.2 * myAtr14, "I", InpColInBuy, 9, ANCHOR_UPPER);
      if(insidesellbar) Txt(gT[b], gH[b] + 0.2 * myAtr14, "I", InpColInSell, 9, ANCHOR_LOWER);
      if(outsidebuybar) Txt(gT[b], gL[b] - 0.2 * myAtr14, "O", InpColInBuy, 9, ANCHOR_UPPER);
      if(outsidesellbar) Txt(gT[b], gH[b] + 0.2 * myAtr14, "O", InpColInSell, 9, ANCHOR_LOWER);
     }
   if(!InpSlLean) DrawAll();


   if(!InpSlLean) {
      if(InpGsOn) GsDrawAll();
      if(InpFvgOn) FvgMtfDrawAll();
   }

   if((InpJdAlert && g_alJd) || (InpTsAlert && g_alTs))
     {
      bool bJ=(InpJdAlert && g_alJd), bT=(InpTsAlert && g_alTs);
      g_alertMsg += " "+(bJ&&bT? "JD + TS" : (bJ? "JD" : "TS"))+" moi;";
     }

   //--- dong ho chan doan: chuoi gay o dau thi nhin so nay ra ngay ---
   if(InpDebug)
     {
      int jdWait=0,jdDead=0,jdDone=0;
      for(int i=0;i<jd_n;i++)
        {
         if(jd[i].done) jdDone++;
         else if(jd[i].dead) jdDead++;
         else jdWait++;
        }
      int tsWait=0,tsDead=0,tsDone=0;
      for(int i=0;i<ts_n;i++)
        {
         if(ts[i].done) tsDone++;
         else if(ts[i].dead) tsDead++;
         else tsWait++;
        }
      int alive=0; for(int i=0;i<fv_n;i++) if(fv[i].alive) alive++;
      Comment("2TC-v10  nen="+IntegerToString(gN)+"   cua so="+IntegerToString(gN-b0)+"\n"+
              "Kho khe ho="+IntegerToString(fv_n)+"  (con TUOI "+IntegerToString(alive)+")\n"+
              "JUDAS : cho="+IntegerToString(jdWait)+"  HONG="+IntegerToString(jdDead)+"  ra tin hieu="+IntegerToString(jdDone)+"\n"+
              "T.SOUP: cho="+IntegerToString(tsWait)+"  HONG="+IntegerToString(tsDead)+"  ra tin hieu="+IntegerToString(tsDone)+"\n"+
              "CISD Max="+IntegerToString(cx_n)+"\n"+
              "BIAS H1="+(g_bhDir==1? "BUY" : (g_bhDir==-1? "SELL" : "chua co"))+
              "   da chan="+IntegerToString(g_bhBlocked));

      // Comment() ve o goc tren trai, cho do hay bi bang one-click / bang gia
      // de len va owner khong doc duoc. In THEM ra tab Experts de con doi chieu
      // bang file log. Moi nen dong mot lan, khong phai moi tick.
      PrintFormat("CRB-DBG nen=%d cuaso=%d | kho=%d (tuoi %d) | JD cho=%d HONG=%d SIG=%d"
                  " | TS cho=%d HONG=%d SIG=%d | CISDmax=%d | biasH1=%s chan=%d",
                  gN, gN-b0, fv_n, alive, jdWait, jdDead, jdDone,
                  tsWait, tsDead, tsDone, cx_n,
                  (g_bhDir==1? "BUY" : (g_bhDir==-1? "SELL" : "chuaco")), g_bhBlocked);

      // Sau cu gan nhat cua moi co che, kem trang thai tung cai: gay o cong nao
      // thi nhin ra ngay. brk = nen DONG CUA xuyen vach (-1 = chua co).
      int jf = (jd_n > 6) ? jd_n - 6 : 0;
      for(int i=jf;i<jd_n;i++)
         PrintFormat("CRB-DBG   JD[%d] %s ext=%s px=%.3f lvl=%.3f brk=%s %s sig=%s fv=%d",
                     i, (jd[i].dir==1? "BUY ":"SELL"),
                     (jd[i].extAbs>=0 && jd[i].extAbs<gN ? TimeToString(gT[jd[i].extAbs],TIME_MINUTES) : "?"),
                     jd[i].extPx, jd[i].lvl,
                     (jd[i].brkBar>=0 && jd[i].brkBar<gN ? TimeToString(gT[jd[i].brkBar],TIME_MINUTES) : "chua"),
                     (jd[i].done? "XONG" : (jd[i].dead? "HONG" : "cho ")),
                     (jd[i].hasSig && jd[i].sigBar>=0 && jd[i].sigBar<gN ? TimeToString(gT[jd[i].sigBar],TIME_MINUTES) : "-"),
                     jd[i].fvPick);
      int tf2 = (ts_n > 6) ? ts_n - 6 : 0;
      for(int i=tf2;i<ts_n;i++)
         PrintFormat("CRB-DBG   TS[%d] %s ext=%s px=%.3f lvl=%.3f brk=%s %s sig=%s fv=%d",
                     i, (ts[i].dir==1? "BUY ":"SELL"),
                     (ts[i].extAbs>=0 && ts[i].extAbs<gN ? TimeToString(gT[ts[i].extAbs],TIME_MINUTES) : "?"),
                     ts[i].extPx, ts[i].lvl,
                     (ts[i].brkBar>=0 && ts[i].brkBar<gN ? TimeToString(gT[ts[i].brkBar],TIME_MINUTES) : "chua"),
                     (ts[i].done? "XONG" : (ts[i].dead? "HONG" : "cho ")),
                     (ts[i].hasSig && ts[i].sigBar>=0 && ts[i].sigBar<gN ? TimeToString(gT[ts[i].sigBar],TIME_MINUTES) : "-"),
                     ts[i].fvPick);
     }
   else Comment("");

   // Rebuild() mo dau bang ObjectsDeleteAll(0,PFX) nen hai bang VA ca cum
   // OLHC deu bi xoa -> ve lai o day.
   if(!InpSlLean) OlhcDraw();
   
   

   //--- nhom 14 + 15 cua ban v7: do doc roi ve duong ke va dashboard ---
   SlCompute();
   SlDraw();
   DbDraw();

   ChartRedraw();
  }

//==================================================================
//   INIT / CALC / DEINIT
//==================================================================
// Khung ma ENGINE chay tren do. PERIOD_CURRENT = bam theo chart (hanh vi cu).
ENUM_TIMEFRAMES EngineTf()
  {
   return (InpEngineTF==PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : InpEngineTF;
  }

//------------------------------------------------------------------
// NHOM 11 - he so THAT SU chay. De 0 o nhom 2 / nhom 4 = giao cho bang lai.
// Luat chon dong nam trong crb_engine.mqh -> EA dung y het, khong the lech.
//------------------------------------------------------------------
// Engine bias chay tren du lieu H1 -> de 0 la lay THANG dong H1 cua bang,
// khong qua luat chon dong. Cung mot viec thi dung chung mot o.


//==================================================================
//   17 - MOTHER BAR BREAKOUT
//==================================================================
input group "17 - MOTHER BAR BREAKOUT"
input bool             InpMbOn        = false;                 
input double           InpMbIbAtrK    = 1.0;                  
input int              InpMbAtrLen    = 14;                   
input double           InpMbDBody     = 0.60;                 
input double           InpMbDClose    = 0.70;                 
input double           InpMbDAtr      = 1.20;                 
input bool             InpMbFltOn     = true;                 
input double           InpMbMinMbAtr  = 0.8;                  
input double           InpMbMaxMbAtr  = 3.0;                  
input bool             InpMbVolOn     = false;                
input double           InpMbVolMult   = 1.5;                  
input int              InpMbVolLen    = 20;                   
input bool             InpMbSzOn      = true;                 
input double           InpMbSzMult    = 0.30;                 
input bool             InpMbBtrOn     = true;                 
input color            InpMbColBox    = C'255,152,0';         
input color            InpMbColBoBuy  = C'255,214,0';         
input color            InpMbColBoSell = C'170,0,255';         
input color            InpMbColBagBuy = C'255,171,0';         
input color            InpMbColBagSell= C'123,31,162';        
input color            InpMbColBtrBuy = C'255,241,118';       
input color            InpMbColBtrSell= C'224,64,251';        


input bool InpDebug = false;
void GsProcessBar(int b);
void FvgMtfProcessBar(int b);
void MbProcessBar(int b);
void GsDrawAll();
void FvgMtfDrawAll();

int OnInit()
  {
   g_barSec=(double)PeriodSeconds(EngineTf());
   g_lastBar=0;
   // Nhom 13 chay tren KHUNG CHART nen handle ATR cung lay theo _Period.

   g_gsAtrH = iATR(_Symbol, _Period, MathMax(InpGsAtrLen, 1));
   if (InpGsVolOn) g_gsVolMaH = iMA(_Symbol, _Period, MathMax(InpGsVolLen, 1), 0, MODE_SMA, PRICE_CLOSE); // Used tick volume if possible but SMA of tick volume can be done manually or via iMA if it supports volume? MT5 doesn't have iMA for volume directly, we will compute SMA of volume manually.

   g_olAtrH=iATR(_Symbol,_Period,MathMax(InpOlAtrLen,1));
   if(InpOlOn && InpOlAtrOn && g_olAtrH==INVALID_HANDLE)
     {
      Print("2TC-v10: khong tao duoc handle ATR cho nhom 13 OLHC");
      return(INIT_FAILED);
     }
   IndicatorSetString(INDICATOR_SHORTNAME,"2TC-v10");
   // In DU o luat ra tab Experts. Doi ung dong "cau hinh" cua CRB-EA-v3 - de
   // doi chieu hai ben trong 5 giay, khoi phai mo Properties tung cai. MT5 nho
   // o theo TEN FILE nen chart co the dang giu gia tri cu ma nhin khong ra.
   Print("2TC-v10 cau hinh: JD=", (InpEnJudas ? "BAT" : "TAT"),
         " TS=", (InpEnTs ? "BAT" : "TAT"),
         " | jdMult=", DoubleToString(InpJdFvgMult, 2),
         (InpJdFvgMult==0.0 ? "(bang)" : ""),
         " jdNeedMss=", (InpJdNeedMss ? "BAT" : "tat"),
         " | tsMult=", DoubleToString(InpTsFvgMult, 2),
         (InpTsFvgMult==0.0 ? "(bang)" : ""),
         " tsNeedCisd=", (InpTsNeedCisd ? "BAT" : "tat"),
         " tsNeedIfvg=", (InpTsNeedIfvg ? "BAT" : "tat"),
         " | biasH1=", (false ? "BAT" : "tat"),
         " | win=", IntegerToString(InpWinBars),
         " tf=", EnumToString((ENUM_TIMEFRAMES)EngineTf()));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0,PFX);
   if(g_olAtrH!=INVALID_HANDLE) IndicatorRelease(g_olAtrH);
   Comment("");
   ChartRedraw();
  }


string GetAlertState()
{
   if(!sl_ok) return "KHONG DU NEN";
   bool haveP2=(InpSlOn && sl_p2ok);
   bool loan=(sl_r2<InpSlR2Min) && (!haveP2 || sl_p2r2<InpSlR2Min);
   if(loan) return "GIA LOAN";
   
   if(InpEnergyOn)
     {
      if(MathAbs(sl_bNorm) <= InpSlFlat || sl_mass <= 1.5) return "TICH LUY (NEN)";
      
      bool isUptrend = (sl_bNorm > 0);
      bool isBraking = (haveP2 && ((isUptrend && sl_p2Acc < 0) || (!isUptrend && sl_p2Acc > 0)));
      bool epDominates = (MathAbs(sl_ep) >= MathAbs(sl_ek));
      
      if(isBraking) return "PULLBACK_DAOCHIEU";
      return "TRENDING_ENERGY";
     }
   
   if(MathAbs(sl_bNorm) <= InpSlFlat) return "TICH LUY (NEN)"; // Hoac Di Ngang
   
   return "OTHER";
}

int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   int minBars=MathMax(InpJdFvgLen,InpTsFvgLen)+30;
   if(rates_total < minBars) return(rates_total);

   ArraySetAsSeries(time,false);
   ArraySetAsSeries(open,false);
   ArraySetAsSeries(high,false);
   ArraySetAsSeries(low,false);
   ArraySetAsSeries(close,false);

   ENUM_TIMEFRAMES etf=EngineTf();
   g_barSec=(double)PeriodSeconds(etf);
   int nEng=0;

   // ---- CONG NEN MOI, gac o DAU HAM ----
   // Ca engine chinh lan engine H1 (nhom 12) deu chi chay MOT LAN moi nen
   // dong. De cong nay o duoi la engine H1 chay tren TUNG TICK - 1500 nen
   // H1 x may CISD, du nang de treo chart.
   datetime curBar=(etf==(ENUM_TIMEFRAMES)_Period)? time[rates_total-1]
                                                  : iTime(_Symbol,etf,0);
   if(curBar==0) return(rates_total);
   if(curBar==g_lastBar && prev_calculated!=0) return(rates_total);

   // ---- NHOM 12: BIAS H1 phai tinh TRUOC khi nap series cua khung chart.
   // CrbComputeH1Bias() dung CHUNG mang gT/gO/... voi lan chay chinh nen no
   // ghi de het - goi sau la hong. Xem khoi chu thich cua ham do.
   // Ham can g_cfg.jdFvgLen / tsFvgLen nen phai CfgFill() truoc; Rebuild()
   // goi CfgFill() lan nua, vo hai.
   CfgFill();
   
   

   if(etf==(ENUM_TIMEFRAMES)_Period)
     {
      g_lastBar=curBar;

      nEng=rates_total;
      ArrayResize(gT,nEng); ArrayResize(gO,nEng); ArrayResize(gH,nEng);
      ArrayResize(gL,nEng); ArrayResize(gC,nEng);
      ArrayResize(mb_vol_buf, nEng);
      ArrayResize(mb_atr_buf, nEng);
      for(int b=0;b<nEng;b++)
        {
         gT[b]=time[b]; gO[b]=open[b]; gH[b]=high[b]; gL[b]=low[b]; gC[b]=close[b];
         mb_vol_buf[b]=tick_volume[b];
      mb_atr_buf[b]=0;
      if(b>=InpMbAtrLen){ double sA=0; for(int a=0;a<InpMbAtrLen;a++) sA+=(gH[b-a]-gL[b-a]); mb_atr_buf[b]=sA/InpMbAtrLen; }
        }
     }
   else
     {
      // Engine chay tren KHUNG KHAC chart: keo nen cua khung do ve mang g*.
      // Moi object deu neo bang datetime nen ket qua tu roi dung cho tren chart
      // hien tai, KHONG phai sua bat cu ham ve nao.
      int avail=Bars(_Symbol,etf);
      if(avail<minBars) return(rates_total);

      MqlRates rt[];
      ArraySetAsSeries(rt,false);
      int got=CopyRates(_Symbol,etf,0,avail,rt);
      if(got<minBars) return(rates_total);
      g_lastBar=curBar;

      nEng=got;
      ArrayResize(gT,nEng); ArrayResize(gO,nEng); ArrayResize(gH,nEng);
      ArrayResize(gL,nEng); ArrayResize(gC,nEng);
      ArrayResize(mb_vol_buf, nEng);
      ArrayResize(mb_atr_buf, nEng);
      for(int b=0;b<nEng;b++)
        {
         gT[b]=rt[b].time; gO[b]=rt[b].open; gH[b]=rt[b].high; gL[b]=rt[b].low; gC[b]=rt[b].close;
         mb_vol_buf[b]=rt[b].tick_volume;
      mb_atr_buf[b]=0;
      if(b>=InpMbAtrLen){ double sA=0; for(int a=0;a<InpMbAtrLen;a++) sA+=(gH[b-a]-gL[b-a]); mb_atr_buf[b]=sA/InpMbAtrLen; }
        }
     }

   Rebuild(nEng);

   if(prev_calculated>0 && StringLen(g_alertMsg)>0)
     {
      string sta = GetAlertState();
      bool skip = false;
      if(sta=="GIA LOAN" && !InpAlertNoisy) skip=true;
      if(sta=="TICH LUY (NEN)" && !InpAlertAccum) skip=true;
      if(!skip) Alert("2TC-v10 ["+_Symbol+" "+StringSubstr(EnumToString(EngineTf()),7)+"]: "+g_alertMsg);
     }

   return(rates_total);
  }
//+------------------------------------------------------------------+

//==================================================================
//   11 - BANG GHI NHO  (doi ung table cua nhom 11 ben Pine)
//   !! KHONG CO TAC DUNG GI TOI HE THONG. In lai dung tam o so nguoi
//   dung tu nhap o nhom 11. KHONG doc va KHONG sua hai o he so THAT o
//   nhom 2 / nhom 4 - doi khung van phai TU TAY chinh hai o do.
//   Dong khop KHUNG ENGINE dang chay duoc to sang.
//   MT5 khong co table -> mot OBJ_RECTANGLE_LABEL lam nen + 15 OBJ_LABEL.
//==================================================================


//==================================================================
//   12 - BIAS H1: cong khung, cong CRB, alert doi chieu, va BANG
//==================================================================
// CONG KHUNG: lay bias H1 xuong chinh H1 (hoac H4) la NHIN TRUOC tuong lai.
// Duoi H1 moi cho chay.

// CHUA CO BIAS (g_bhDir == 0) -> KHONG chan gi ca. Nguoc lai thi may chuc
// nen H1 warm-up dau chart se trong tron.


// Alert khi bias doi chieu. Lan tinh DAU TIEN sau khi gan indicator thi im -
// khong ai muon bi hu mot phat ngay luc gan.

// Bang RIENG, tach han bang ghi nho cua nhom 11. Van hien khi bo loc dang
// tat - luc do no chi la thong tin.
//   Dong "Tu" quan trong hon ve ngoai cua no: bias song vo thoi han nen can
//   thay no GIA bao nhieu. Dong "Cuc tri H1" la muc huy cua cu H1 dang giu
//   bias - CHI DE NHIN, khong phai luat.

//+------------------------------------------------------------------+


//==================================================================
//   17 - MOTHER BAR BREAKOUT LOGIC
//==================================================================

//==================================================================
//   GANN SWING CONSOLIDATION CORE ENGINE
//==================================================================
struct CGsBox {
    datetime left;
    double top;
    double bot;
    double inTop;
    double inBot;
    int    trend;
    int    state;      // 1: active, 2: broken (waiting BTR), 3: finished
    int    endBar;
    int    brBar;
    int    brDir;
    double fvgFar;
    bool   szOk;
    bool   btrHit;
    int    btrBar;
    int    btrDir;
    
    string bxOName;
    string bxIName;
    string lbBOName;
    string lbBTRName;
    
    void Init() {
        left = 0; top = 0.0; bot = 0.0;
        inTop = 0.0; inBot = 0.0; trend = 0;
        state = 1; endBar = 0; brBar = 0; brDir = 0;
        fvgFar = 0.0; szOk = false; btrHit = false;
        btrBar = 0; btrDir = 0;
        bxOName = ""; bxIName = ""; lbBOName = ""; lbBTRName = "";
    }
};

CGsBox gs_boxes[];
datetime gs_f0x[30], gs_f1x[30], gs_sfx[30];
double gs_f0y[30], gs_f1y[30], gs_sfy[30];
double gs_sfMark;
datetime gs_sfPend;

void GsInit() {
    ArrayResize(gs_boxes, 0);
    for(int i=0; i<30; i++) {
        gs_f0x[i] = 0; gs_f1x[i] = 0; gs_sfx[i] = 0;
        gs_f0y[i] = 0; gs_f1y[i] = 0; gs_sfy[i] = 0;
    }
    gs_sfMark = 0; gs_sfPend = 0;
}

double GetGsAtr(int b) {
    if(InpGsAtrLen < 1) return 0;
    double atr[1];
    if(CopyBuffer(g_gsAtrH, 0, gN - 1 - b, 1, atr) > 0) return atr[0];
    return 0;
}

double GetGsVol(int b) {
    if(!InpGsVolOn) return 1.0;
    long vol[1];
    if(CopyTickVolume(_Symbol, _Period, gN - 1 - b, 1, vol) > 0) return (double)vol[0];
    return 0;
}

double GetGsVolMa(int b) {
    if(!InpGsVolOn || InpGsVolLen < 1) return 1.0;
    long vol[];
    if(CopyTickVolume(_Symbol, _Period, gN - 1 - b, InpGsVolLen, vol) > 0) {
        double sum = 0;
        int count = ArraySize(vol);
        for(int i=0; i<count; i++) sum += (double)vol[i];
        return sum / count;
    }
    return 1.0;
}

void GsUnshift(datetime &arr[], datetime val) {
    for(int i=29; i>0; i--) arr[i] = arr[i-1];
    arr[0] = val;
}
void GsUnshiftD(double &arr[], double val) {
    for(int i=29; i>0; i--) arr[i] = arr[i-1];
    arr[0] = val;
}

int GsCalcF1(datetime px, double py) {
    int r = 0;
    double a0 = gs_f1y[0], a1 = gs_f1y[1];
    double n0 = gs_f0y[0], n1 = gs_f0y[1], n2 = gs_f0y[2], n3 = gs_f0y[3];
    if ((a0 >= a1 && n0 < a1) || (a0 <= a1 && n0 > a1)) {
        GsUnshift(gs_f1x, px); GsUnshiftD(gs_f1y, py); r = 1;
    } else if (a0 >= a1 && n0 < n1 && n0 < n2 && n1 < n3 && n2 < n3) {
        GsUnshift(gs_f1x, px); GsUnshiftD(gs_f1y, py); r = 1;
    } else if (a0 <= a1 && n0 > n1 && n0 > n2 && n1 > n3 && n2 > n3) {
        GsUnshift(gs_f1x, px); GsUnshiftD(gs_f1y, py); r = 1;
    } else if (a0 >= a1 && py >= a0) {
        gs_f1x[0] = px; gs_f1y[0] = py; r = 2;
    } else if (a0 <= a1 && py <= a0) {
        gs_f1x[0] = px; gs_f1y[0] = py; r = 2;
    }
    return r;
}

int GsCalcSF1(datetime px, double py) {
    int r = 0;
    double m = gs_sfMark;
    double s0 = gs_sfy[0], s1 = gs_sfy[1], s2 = gs_sfy[2];
    bool up = (s0 >= s1), dn = (s0 <= s1);
    
    if (m == 0) {
        if ((up && py >= s0) || (dn && py <= s0)) {
            gs_sfx[0] = px; gs_sfy[0] = py; r = 2;
        } else if ((up && py < s0) || (dn && py > s0)) {
            gs_sfMark = py; gs_sfPend = px;
        }
    } else {
        if ((up && py >= s0) || (dn && py <= s0)) {
            gs_sfx[0] = px; gs_sfy[0] = py; gs_sfMark = 0; gs_sfPend = 0; r = 2;
        } else if ((up && py < m) || (dn && py > m)) {
            GsUnshift(gs_sfx, gs_sfPend); GsUnshiftD(gs_sfy, m);
            gs_sfMark = py; gs_sfPend = px; r = 1;
        } else if ((up && py >= m && py < s0) || (dn && py <= m && py > s0)) {
            gs_sfMark = py; gs_sfPend = px;
        }
    }
    return r;
}

void GsFeed(datetime px, double y1, double y2) {
    double last = gs_f0y[0];
    if ((last > y1 && last > y2) || (last < y1 && last < y2)) {
        GsUnshift(gs_f0x, px); GsUnshiftD(gs_f0y, gs_f0y[1]);
    }
    GsUnshift(gs_f0x, px); GsUnshiftD(gs_f0y, y1);
    GsUnshift(gs_f0x, px); GsUnshiftD(gs_f0y, y2);
}

void GsDrawBox(int idx, datetime rightT) {
    if (idx >= ArraySize(gs_boxes)) return;
    if (gs_boxes[idx].bxOName == "") {
        gs_boxes[idx].bxOName = PFX + "GS_BOX_" + IntegerToString(g_objId++);
        if(ObjectCreate(0, gs_boxes[idx].bxOName, OBJ_RECTANGLE, 0, gs_boxes[idx].left, gs_boxes[idx].top, rightT, gs_boxes[idx].bot)) {
            ObjectSetInteger(0, gs_boxes[idx].bxOName, OBJPROP_COLOR, Op(InpGsFill, 100 - InpGsFillTr));
            ObjectSetInteger(0, gs_boxes[idx].bxOName, OBJPROP_FILL, true);
            ObjectSetInteger(0, gs_boxes[idx].bxOName, OBJPROP_BACK, true);
            ObjectSetInteger(0, gs_boxes[idx].bxOName, OBJPROP_SELECTABLE, false);
        }
    } else {
        ObjectSetInteger(0, gs_boxes[idx].bxOName, OBJPROP_TIME, 1, rightT);
    }
}



struct MbRec {
    int   st;
    double mh;
    double ml;
    datetime mt;
    int   ibCnt;
    int   minIb;
    string boxName;
    int   bDir;
    double pmh;
    double pml;
    string sigName;
};
MbRec mbState;
int mb_objId = 1;

int f_mbCalcMinIb(double mh, double ml, double atr, double k) {
    if (atr > 0) {
        return (int)MathMax(1.0, MathFloor((mh - ml) / atr * k));
    }
    return 1;
}

void MbProcessBar(int b) {
    if (!InpMbOn || b < 2) return;
    
    double h = gH[b];
    double l = gL[b];
    double c = gC[b];
    double o = gO[b];
    datetime t = gT[b];
    
    double atr = mb_atr_buf[b];
    double avgVol = 0;
    if (InpMbVolOn && b >= InpMbVolLen) {
        double sum = 0;
        for(int vi=0; vi<InpMbVolLen; vi++) sum += (double)mb_vol_buf[b-vi-1];
        avgVol = sum / InpMbVolLen;
    }
    
    bool inside = (mbState.st != 0) && (h <= mbState.mh) && (l >= mbState.ml);
    
    if (mbState.bDir != 0 && InpMbBtrOn) {
        bool okBtr = (mbState.bDir == 1) ? (l > gH[b-2]) : (h < gL[b-2]);
        if (okBtr) {
            string lbName = PFX + "MB_BTR_" + IntegerToString(mb_objId++);
            double yLbl = (mbState.bDir == 1) ? l : h;
            color col = (mbState.bDir == 1) ? InpMbColBtrBuy : InpMbColBtrSell;
            if(ObjectCreate(0, lbName, OBJ_TEXT, 0, t, yLbl)) {
                ObjectSetString(0, lbName, OBJPROP_TEXT, "BTR*");
                ObjectSetString(0, lbName, OBJPROP_FONT, "Arial");
                ObjectSetInteger(0, lbName, OBJPROP_FONTSIZE, TxPx(TXSZ_SMALL));
                ObjectSetInteger(0, lbName, OBJPROP_COLOR, col);
                ObjectSetInteger(0, lbName, OBJPROP_ANCHOR, (mbState.bDir == 1) ? ANCHOR_UPPER : ANCHOR_LOWER);
                ObjectSetInteger(0, lbName, OBJPROP_SELECTABLE, false);
                ObjectSetInteger(0, lbName, OBJPROP_HIDDEN, true);
            }
        }
        mbState.bDir = 0;
    }
    
    if (mbState.st == 0) {
        double rng = h - l;
        bool sizeOk = !InpMbFltOn || atr == 0 || (rng >= InpMbMinMbAtr * atr && rng <= InpMbMaxMbAtr * atr);
        if (sizeOk) {
            mbState.st = 1;
            mbState.mh = h;
            mbState.ml = l;
            mbState.mt = t;
            mbState.ibCnt = 0;
            mbState.minIb = f_mbCalcMinIb(h, l, atr, InpMbIbAtrK);
            
            if (mbState.boxName != "") ObjectDelete(0, mbState.boxName);
            mbState.boxName = PFX + "MB_BOX_" + IntegerToString(mb_objId++);
            if(ObjectCreate(0, mbState.boxName, OBJ_RECTANGLE, 0, t, h, t, l)) {
                ObjectSetInteger(0, mbState.boxName, OBJPROP_COLOR, InpMbColBox);
                ObjectSetInteger(0, mbState.boxName, OBJPROP_STYLE, STYLE_DASH);
                ObjectSetInteger(0, mbState.boxName, OBJPROP_WIDTH, 1);
                ObjectSetInteger(0, mbState.boxName, OBJPROP_BACK, true);
                ObjectSetInteger(0, mbState.boxName, OBJPROP_FILL, true);
                ObjectSetInteger(0, mbState.boxName, OBJPROP_HIDDEN, true);
                ObjectSetInteger(0, mbState.boxName, OBJPROP_SELECTABLE, false);
            }
        }
    }
    else if (mbState.st == 1) {
        if (inside) {
            mbState.ibCnt++;
            if (mbState.ibCnt >= mbState.minIb) mbState.st = 2;
        } else {
            if (mbState.boxName != "") ObjectDelete(0, mbState.boxName);
            mbState.boxName = "";
            double rng = h - l;
            bool sizeOk = !InpMbFltOn || atr == 0 || (rng >= InpMbMinMbAtr * atr && rng <= InpMbMaxMbAtr * atr);
            if (sizeOk) {
                mbState.st = 1;
                mbState.mh = h;
                mbState.ml = l;
                mbState.mt = t;
                mbState.ibCnt = 0;
                mbState.minIb = f_mbCalcMinIb(h, l, atr, InpMbIbAtrK);
                mbState.boxName = PFX + "MB_BOX_" + IntegerToString(mb_objId++);
                if(ObjectCreate(0, mbState.boxName, OBJ_RECTANGLE, 0, t, h, t, l)) {
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_COLOR, InpMbColBox);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_STYLE, STYLE_DASH);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_WIDTH, 1);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_BACK, true);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_FILL, true);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_HIDDEN, true);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_SELECTABLE, false);
                }
            } else {
                mbState.st = 0;
            }
        }
    }
    else if (mbState.st == 2) {
        if (inside) {
            mbState.ibCnt++;
        } else {
            bool isBuy = c > mbState.mh;
            bool isSell = c < mbState.ml;
            if (isBuy || isSell) {
                double rng = h - l;
                double bd = MathAbs(c - o);
                bool volOk = !InpMbVolOn || (avgVol > 0 && mb_vol_buf[b] >= InpMbVolMult * avgVol);
                bool dispOk = (rng > 0) && (bd/rng >= InpMbDBody) && (atr > 0 && rng >= InpMbDAtr * atr) && volOk;
                double pos = (rng > 0) ? (isBuy ? (c - l)/rng : (h - c)/rng) : 0;
                bool closeOk = pos >= InpMbDClose;
                
                bool isBagB = isBuy && dispOk && closeOk;
                bool isBagS = isSell && dispOk && closeOk;
                bool isBoB = isBuy && !isBagB;
                bool isBoS = isSell && !isBagS;
                
                if (InpMbSzOn && atr > 0) {
                    if (isBoB && (c - mbState.mh) < InpMbSzMult * atr) isBoB = false;
                    if (isBoS && (mbState.ml - c) < InpMbSzMult * atr) isBoS = false;
                }
                
                int s_type = 0; // 1: BagB, -1: BagS, 2: BoB, -2: BoS
                if (isBagB) s_type = 1;
                else if (isBagS) s_type = -1;
                else if (isBoB) s_type = 2;
                else if (isBoS) s_type = -2;
                
                if (s_type != 0) {
                    string lbName = PFX + "MB_SIG_" + IntegerToString(mb_objId++);
                    double yLbl = (s_type > 0) ? l : h;
                    color col = (s_type == 1) ? InpMbColBagBuy : ((s_type == -1) ? InpMbColBagSell : ((s_type == 2) ? InpMbColBoBuy : InpMbColBoSell));
                    string text = MathAbs(s_type) == 1 ? "BAG" : "B/O";
                    if(ObjectCreate(0, lbName, OBJ_TEXT, 0, t, yLbl)) {
                        ObjectSetString(0, lbName, OBJPROP_TEXT, text);
                        ObjectSetString(0, lbName, OBJPROP_FONT, "Arial");
                        ObjectSetInteger(0, lbName, OBJPROP_FONTSIZE, TxPx(TXSZ_SMALL));
                        ObjectSetInteger(0, lbName, OBJPROP_COLOR, col);
                        ObjectSetInteger(0, lbName, OBJPROP_ANCHOR, (s_type > 0) ? ANCHOR_UPPER : ANCHOR_LOWER);
                        ObjectSetInteger(0, lbName, OBJPROP_SELECTABLE, false);
                        ObjectSetInteger(0, lbName, OBJPROP_HIDDEN, true);
                    }
                    if (InpMbBtrOn) {
                        mbState.bDir = isBuy ? 1 : -1;
                        mbState.pmh = mbState.mh;
                        mbState.pml = mbState.ml;
                    }
                }
            }
            
            double rng2 = h - l;
            bool sizeOk = !InpMbFltOn || atr == 0 || (rng2 >= InpMbMinMbAtr * atr && rng2 <= InpMbMaxMbAtr * atr);
            if (sizeOk) {
                mbState.st = 1;
                mbState.mh = h;
                mbState.ml = l;
                mbState.mt = t;
                mbState.ibCnt = 0;
                mbState.minIb = f_mbCalcMinIb(h, l, atr, InpMbIbAtrK);
                mbState.boxName = PFX + "MB_BOX_" + IntegerToString(mb_objId++);
                if(ObjectCreate(0, mbState.boxName, OBJ_RECTANGLE, 0, t, h, t, l)) {
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_COLOR, InpMbColBox);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_STYLE, STYLE_DASH);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_WIDTH, 1);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_BACK, true);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_FILL, true);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_HIDDEN, true);
                    ObjectSetInteger(0, mbState.boxName, OBJPROP_SELECTABLE, false);
                }
            } else {
                mbState.st = 0;
            }
        }
    }
    if (mbState.boxName != "" && mbState.st > 0) {
        ObjectSetInteger(0, mbState.boxName, OBJPROP_TIME, 1, t);
    }
}

void GsProcessBar(int b) {
    if(b < 2) return;
    double p_high = InpGsUseClose ? MathMax(gO[b], gC[b]) : gH[b];
    double p_low  = InpGsUseClose ? MathMin(gO[b], gC[b]) : gL[b];
    
    // Garbage Collection (keep max 40 ended boxes)
    int n3 = 0;
    for(int i=0; i<ArraySize(gs_boxes); i++) {
        if(gs_boxes[i].state == 3) n3++;
    }
    if (n3 > 40) {
        for(int i=0; i<ArraySize(gs_boxes); i++) {
            if(gs_boxes[i].state == 3) {
                if (gs_boxes[i].bxOName != "") ObjectDelete(0, gs_boxes[i].bxOName);
                if (gs_boxes[i].bxIName != "") ObjectDelete(0, gs_boxes[i].bxIName);
                if (gs_boxes[i].lbBOName != "") ObjectDelete(0, gs_boxes[i].lbBOName);
                if (gs_boxes[i].lbBTRName != "") ObjectDelete(0, gs_boxes[i].lbBTRName);
                
                for(int j=i; j<ArraySize(gs_boxes)-1; j++) gs_boxes[j] = gs_boxes[j+1];
                ArrayResize(gs_boxes, ArraySize(gs_boxes) - 1);
                break;
            }
        }
    }
    int bCount = ArraySize(gs_boxes);
    
    // Simplified feed
    double last_hp = gs_f0y[1];
    double last_lp = gs_f0y[2];
    if (p_high > last_hp && p_low > last_lp) {
        GsFeed(gT[b], p_low, p_high);
    } else if (p_high < last_hp && p_low < last_lp) {
        GsFeed(gT[b], p_high, p_low);
    } else if (gC[b] > gO[b]) {
        GsFeed(gT[b], p_low, p_high);
    } else {
        GsFeed(gT[b], p_high, p_low);
    }
    
    int act_f1 = GsCalcF1(gs_f0x[0], gs_f0y[0]);
    if (act_f1 == 1) {
        GsCalcSF1(gs_f1x[0], gs_f1y[0]);
        
        // BOX DETECTION LOGIC (Simplified MQL5 port)
        // Detects consolidation based on recent F1 swings
        
         if (InpGsMethod == 1 || InpGsMethod == 0) {
            double hMax = 0, lMin = 9999999;
            for(int k=0; k<10; k++) {
               if (gs_f1y[k] > hMax) hMax = gs_f1y[k];
               if (gs_f1y[k] > 0 && gs_f1y[k] < lMin) lMin = gs_f1y[k];
            }
            double boxH = hMax - lMin;
            if (boxH > 0 && boxH <= InpGsMaxAtr * GetGsAtr(b)) {
               int tTop=0, tBot=0;
               double sTop=0, sBot=0;
               double tol = boxH * (InpGsTolPct/100.0);
               for(int k=0; k<10; k++) {
                  if (gs_f1y[k] >= hMax - tol && gs_f1y[k] <= hMax + tol) { tTop++; sTop += gs_f1y[k]; }
                  if (gs_f1y[k] <= lMin + tol && gs_f1y[k] >= lMin - tol) { tBot++; sBot += gs_f1y[k]; }
               }
               
               if (tTop >= InpGsMinTouch && tBot >= InpGsMinTouch) {
                  bool overlap = false;
                  for(int i=0; i<bCount; i++) {
                     if (gs_boxes[i].state == 1) { overlap = true; break; }
                  }
                  if (!overlap) {
                     int nIdx = bCount;
                     ArrayResize(gs_boxes, nIdx + 1);
                     gs_boxes[nIdx].Init();
                     gs_boxes[nIdx].left = gs_f1x[9]; 
                     gs_boxes[nIdx].top = hMax;
                     gs_boxes[nIdx].bot = lMin;
                     gs_boxes[nIdx].inTop = (tTop > 0) ? sTop / tTop : hMax;
                     gs_boxes[nIdx].inBot = (tBot > 0) ? sBot / tBot : lMin;
                     bCount++;
                  }
               }
            }
         } 
         else if (InpGsMethod == 2) {
            double lim = InpGsMaxAtr * GetGsAtr(b);
            double hi = gH[b];
            double lo = gL[b];
            int L = 1;
            int look = (int)MathMin(InpGsMaxLook, b);
            if (look > 1) {
               for (int j=1; j<look; j++) {
                  double nh = MathMax(hi, gH[b-j]);
                  double nl = MathMin(lo, gL[b-j]);
                  if (nh - nl > lim) break;
                  hi = nh;
                  lo = nl;
                  L = j + 1;
               }
            }
            if (L >= InpGsMinBars && hi > lo) {
               double tv = (hi - lo) * InpGsTolPct / 100.0;
               int lastSide = 0;
               int nt = 0;
               int nb = 0;
               double st = 0.0;
               double sb = 0.0;
               for (int j = L - 1; j >= 0; j--) {
                  bool isIB = (gH[b-j] <= gH[b-j-1] && gL[b-j] >= gL[b-j-1]);
                  if (!isIB) {
                     if (gH[b-j] >= hi - tv && lastSide != 1) {
                        nt++;
                        st += gH[b-j];
                        lastSide = 1;
                     } else if (gL[b-j] <= lo + tv && lastSide != -1) {
                        nb++;
                        sb += gL[b-j];
                        lastSide = -1;
                     }
                  }
               }
               if (nt >= InpGsMinTouch && nb >= InpGsMinTouch) {
                  bool overlap = false;
                  for(int i=0; i<bCount; i++) {
                     if (gs_boxes[i].state == 1) { overlap = true; break; }
                  }
                  if (!overlap) {
                     int nIdx = bCount;
                     ArrayResize(gs_boxes, nIdx + 1);
                     gs_boxes[nIdx].Init();
                     gs_boxes[nIdx].left = gT[b - L + 1];
                     gs_boxes[nIdx].top = hi;
                     gs_boxes[nIdx].bot = lo;
                     gs_boxes[nIdx].inTop = (nt > 0) ? st / nt : hi;
                     gs_boxes[nIdx].inBot = (nb > 0) ? sb / nb : lo;
                     bCount++;
                  }
               }
            }
         }
      }

   for(int i = ArraySize(gs_boxes)-1; i >= 0; i--) {
        int c = b - 1; // Previous confirmed bar index
        if(c < 1) continue;

        // BTR -> BTR* upgrade
        if(gs_boxes[i].btrBar > 0 && b == gs_boxes[i].btrBar + 1) {
            bool star = false;
            if(gs_boxes[i].btrDir == -1) star = (gH[b] < gL[b-2]);
            else star = (gL[b] > gH[b-2]);
            if(star) {
                if(gs_boxes[i].lbBTRName != "") {
                    ObjectSetString(0, gs_boxes[i].lbBTRName, OBJPROP_TEXT, "BTR*");
                    ObjectSetInteger(0, gs_boxes[i].lbBTRName, OBJPROP_COLOR, (gs_boxes[i].btrDir == 1) ? InpGsBTRsBuy : InpGsBTRsSell);
                }
            }
        }

        if(gs_boxes[i].state == 1) {
            GsDrawBox(i, gT[b]); // Extend drawing
            
            double brT = (InpGsBrkMode == 1 && gs_boxes[i].inTop > 0) ? gs_boxes[i].inTop : gs_boxes[i].top;
            double brB = (InpGsBrkMode == 1 && gs_boxes[i].inBot > 0) ? gs_boxes[i].inBot : gs_boxes[i].bot;
            
            double gUp = gL[b] - gH[b-2];
            double gDn = gL[b-2] - gH[b];
            double refA = GetGsAtr(c-1);
            
            bool okUp = (!InpGsSzOn) || (gUp >= InpGsSzMult * refA);
            bool okDn = (!InpGsSzOn) || (gDn >= InpGsSzMult * refA);
            bool blkA = (InpGsSzOn && InpGsSzMode == 0); // MODE_A: 0, MODE_B: 1
            
            bool boUp = (gT[c] > gs_boxes[i].left) && (gC[c] > brT) && (gUp > 0) && (!blkA || okUp);
            bool boDn = (gT[c] > gs_boxes[i].left) && (gC[c] < brB) && (gDn > 0) && (!blkA || okDn);
            
            if(boUp || boDn) {
                int d = boUp ? 1 : -1;
                gs_boxes[i].state = 2;
                gs_boxes[i].brBar = c;
                gs_boxes[i].brDir = d;
                gs_boxes[i].fvgFar = boUp ? gH[b-2] : gL[b-2];
                gs_boxes[i].szOk = boUp ? okUp : okDn;
                gs_boxes[i].btrHit = false;
                
                gs_boxes[i].lbBOName = PFX + "GS_BO_" + IntegerToString(g_objId++);
                double yLbl = (d == 1) ? gL[c] : gH[c];
                color col = (d == 1) ? InpGsBOBuy : InpGsBOSell;
                if(ObjectCreate(0, gs_boxes[i].lbBOName, OBJ_TEXT, 0, gT[c], yLbl)) {
                    ObjectSetString(0, gs_boxes[i].lbBOName, OBJPROP_TEXT, "B/O");
                    ObjectSetString(0, gs_boxes[i].lbBOName, OBJPROP_FONT, "Arial");
                    ObjectSetInteger(0, gs_boxes[i].lbBOName, OBJPROP_FONTSIZE, TxPx(TXSZ_SMALL));
                    ObjectSetInteger(0, gs_boxes[i].lbBOName, OBJPROP_COLOR, col);
                    ObjectSetInteger(0, gs_boxes[i].lbBOName, OBJPROP_ANCHOR, (d == 1) ? ANCHOR_UPPER : ANCHOR_LOWER);
                    ObjectSetInteger(0, gs_boxes[i].lbBOName, OBJPROP_SELECTABLE, false);
                    ObjectSetInteger(0, gs_boxes[i].lbBOName, OBJPROP_HIDDEN, true);
                }
            } else {
                double h1 = gH[c];
                double l1 = gL[c];
                if (h1 > gs_boxes[i].top || l1 < gs_boxes[i].bot) {
                    double nt = MathMax(gs_boxes[i].top, h1);
                    double nb = MathMin(gs_boxes[i].bot, l1);
                    if (nt - nb <= InpGsMaxAtr * GetGsAtr(b)) {
                        gs_boxes[i].top = nt;
                        gs_boxes[i].bot = nb;
                        ObjectSetDouble(0, gs_boxes[i].bxOName, OBJPROP_PRICE, 0, nt);
                        ObjectSetDouble(0, gs_boxes[i].bxOName, OBJPROP_PRICE, 1, nb);
                    } else {
                        gs_boxes[i].state = 3;
                        gs_boxes[i].endBar = MathMax(0, c - 1);
                    }
                }
            }
        }
        else if (gs_boxes[i].state == 2) {
            int k = b - gs_boxes[i].brBar;
            int d = gs_boxes[i].brDir;
            
            if (k == 2) {
                double r2 = gH[b-2] - gL[b-2];
                double bd2 = MathAbs(gC[b-2] - gO[b-2]);
                double ps2 = 0.0;
                if(r2 > 0) {
                    if(d == 1) ps2 = (gC[b-2] - gL[b-2]) / r2;
                    else       ps2 = (gH[b-2] - gC[b-2]) / r2;
                }
                
                double avgV = 0.0;
                if(InpGsVolOn && b >= InpGsVolLen + 3) {
                    double sumV = 0;
                    for(int vi=0; vi<InpGsVolLen; vi++) sumV += (double)mb_vol_buf[b-3-vi];
                    avgV = sumV / InpGsVolLen;
                }
                bool volOk = (!InpGsVolOn) || ((double)mb_vol_buf[b-2] >= InpGsVolMult * avgV);
                
                bool disp = (r2 > 0) && (bd2 / r2 >= InpGsDBody) && (ps2 >= InpGsDClose) && (r2 >= InpGsDAtr * GetGsAtr(b-3)) && volOk;
                bool c4 = (d == 1) ? (gL[b] > gL[b-1]) : (gH[b] < gH[b-1]);
                bool szB = (!InpGsSzOn || InpGsSzMode == 1) || gs_boxes[i].szOk;
                
                if (disp && c4 && szB) {
                    if(gs_boxes[i].lbBOName != "") {
                        ObjectSetString(0, gs_boxes[i].lbBOName, OBJPROP_TEXT, "BAG");
                        ObjectSetInteger(0, gs_boxes[i].lbBOName, OBJPROP_COLOR, (d == 1) ? InpGsBAGBuy : InpGsBAGSell);
                    }
                }
            }
            
            if (k >= 1 && k <= InpGsBtrN && !gs_boxes[i].btrHit) {
                bool inv = (d == 1) ? (gC[b] < gs_boxes[i].fvgFar) : (gC[b] > gs_boxes[i].fvgFar);
                if (inv) {
                    gs_boxes[i].btrHit = true;
                    gs_boxes[i].btrBar = b;
                    gs_boxes[i].btrDir = -d;
                    if(InpGsBtrN > 0) {
                        ObjectDelete(0, gs_boxes[i].lbBOName);
                        gs_boxes[i].lbBOName = "";
                        gs_boxes[i].lbBTRName = PFX + "GS_BTR_" + IntegerToString(g_objId++);
                        color btrCol = (-d == 1) ? InpGsBTRBuy : InpGsBTRSell;
                        double yBtr = (-d == 1) ? gL[b] : gH[b];
                        if(ObjectCreate(0, gs_boxes[i].lbBTRName, OBJ_TEXT, 0, gT[b], yBtr)) {
                            ObjectSetString(0, gs_boxes[i].lbBTRName, OBJPROP_TEXT, "BTR");
                            ObjectSetString(0, gs_boxes[i].lbBTRName, OBJPROP_FONT, "Arial");
                            ObjectSetInteger(0, gs_boxes[i].lbBTRName, OBJPROP_FONTSIZE, TxPx(TXSZ_SMALL));
                            ObjectSetInteger(0, gs_boxes[i].lbBTRName, OBJPROP_COLOR, btrCol);
                            ObjectSetInteger(0, gs_boxes[i].lbBTRName, OBJPROP_ANCHOR, (-d == 1) ? ANCHOR_UPPER : ANCHOR_LOWER);
                            ObjectSetInteger(0, gs_boxes[i].lbBTRName, OBJPROP_SELECTABLE, false);
                            ObjectSetInteger(0, gs_boxes[i].lbBTRName, OBJPROP_HIDDEN, true);
                        }
                    }
                    if (gC[b] <= gs_boxes[i].top && gC[b] >= gs_boxes[i].bot) {
                        gs_boxes[i].state = 1;
                    } else {
                        gs_boxes[i].state = 3;
                        gs_boxes[i].endBar = b;
                    }
                }
            }
            
            if (gs_boxes[i].state == 2 && k >= MathMax(InpGsBtrN, 2)) {
                gs_boxes[i].state = 3;
                gs_boxes[i].endBar = b;
            }
        }
    }
}
void GsDrawAll() {
    // Objects are created during GsProcessBar and managed there.
}


//==================================================================
//   17 - FVG MULTI-TIMEFRAME LOGIC
//==================================================================
string FvgTfTxt(ENUM_TIMEFRAMES tf) {
   int s = PeriodSeconds(tf);
   if(s < 3600) return IntegerToString(s/60) + "m";
   if(s < 86400) return IntegerToString(s/3600) + "h";
   return EnumToString(tf);
}

void FvgAddZone(FVG_Z &arr[], FVG_Z &z, int maxN) {
   int sz = ArraySize(arr);
   ArrayResize(arr, sz + 1);
   arr[sz] = z;
   if(ArraySize(arr) > maxN) {
      ObjectDelete(0, arr[0].bName);
      ArrayRemoveFvgZ(arr, 0);
   }
}

void FvgUpdZones(FVG_Z &arr[], bool hide, bool useTime, bool ext, int b) {
   int sz = ArraySize(arr);
   if(sz > 0) {
      for(int i = sz - 1; i >= 0; i--) {
         if(!arr[i].done) {
            if(ext) {
               ObjectSetInteger(0, arr[i].bName, OBJPROP_TIME, 1, gT[b]);
            }
            bool filled = (arr[i].dir == 1) ? (gL[b] <= arr[i].bot) : (gH[b] >= arr[i].top);
            if(filled) {
               arr[i].done = true;
               if(hide) {
                  ObjectDelete(0, arr[i].bName);
                  ArrayRemoveFvgZ(arr, i);
               }
            }
         }
      }
   }
}

void FvgNewHtf(FVG_Z &arr[], bool isNew, double h3, double l3, double h1, double l1, datetime t1, datetime tc, ENUM_TIMEFRAMES tf, color bc, int w, int maxN) {
   if(isNew && h1 != 0) {
      if(l3 > h1) {
         string bnm = PFX + "FVG_" + IntegerToString(g_objId++);
         Box(t1, l3, InpFvgExtOn ? gT[gN-1] : tc, h1, bc, InpFvgHtfSty, w);
         ObjectSetString(0, bnm, OBJPROP_TEXT, FvgTfTxt(tf));
         FVG_Z z; z.bName = bnm; z.t1 = t1; z.top = l3; z.bot = h1; z.dir = 1; z.done = false;
         FvgAddZone(arr, z, maxN);
      } else if(h3 < l1) {
         string bnm = PFX + "FVG_" + IntegerToString(g_objId++);
         Box(t1, l1, InpFvgExtOn ? gT[gN-1] : tc, h3, bc, InpFvgHtfSty, w);
         ObjectSetString(0, bnm, OBJPROP_TEXT, FvgTfTxt(tf));
         FVG_Z z; z.bName = bnm; z.t1 = t1; z.top = l1; z.bot = h3; z.dir = -1; z.done = false;
         FvgAddZone(arr, z, maxN);
      }
   }
}

void FvgMtfProcessBar(int b) {
   if(b < 2) return;
   
   FvgUpdZones(zC, InpFvgHideFill, false, InpFvgExtOn, b);
   FvgUpdZones(z1, InpFvgHideFill, true, InpFvgExtOn, b);
   FvgUpdZones(z2, InpFvgHideFill, true, InpFvgExtOn, b);
   FvgUpdZones(z3, InpFvgHideFill, true, InpFvgExtOn, b);
   
   if(InpFvgCtfOn) {
      if(gL[b] > gH[b-2]) {
         string bnm = PFX + "FVG_" + IntegerToString(g_objId++);
         BoxFill(gT[b-2], gL[b], gT[b], gH[b-2], Op(InpFvgBullClr, 70));
         FVG_Z z; z.bName = bnm; z.t1 = gT[b-2]; z.top = gL[b]; z.bot = gH[b-2]; z.dir = 1; z.done = false;
         FvgAddZone(zC, z, InpFvgN);
      } else if(gH[b] < gL[b-2]) {
         string bnm = PFX + "FVG_" + IntegerToString(g_objId++);
         BoxFill(gT[b-2], gL[b-2], gT[b], gH[b], Op(InpFvgBearClr, 70));
         FVG_Z z; z.bName = bnm; z.t1 = gT[b-2]; z.top = gL[b-2]; z.bot = gH[b]; z.dir = -1; z.done = false;
         FvgAddZone(zC, z, InpFvgN);
      }
   }
   
   // For HTF we need to check if a new HTF bar closed.
   // This is complex to do accurately for historical bars using CopyRates inside the loop.
   // We will fetch the HTF data for time gT[b].
   // But for Pine `request.security(lookahead=on, [high[1]...])` means it gets the closed HTF bar data.
   // We can emulate this by finding the HTF bar that closed just before gT[b].
   /* auto do_htf = [b](ENUM_TIMEFRAMES tf, bool on, color clr, int w, FVG_Z &arr[]) {
      if(!on || PeriodSeconds(tf) <= PeriodSeconds(_Period)) return;
      MqlRates htf_rt[];
      if(CopyRates(_Symbol, tf, gT[b], 4, htf_rt) > 0) {
         // Check if a new HTF bar just completed between b-1 and b.
         // Actually, CopyRates with exact time gives the bar containing that time.
         // Let's keep it simple: just create FVG if a new HTF bar starts at gT[b].
         datetime htf_time = htf_rt[0].time;
         if(gT[b] == htf_time && b > 0) {
            // New HTF bar started at gT[b]. This means the previous HTF bar closed at gT[b].
            // The closed HTF bar is index 0 in a reverse ordered array, but CopyRates gives chronological order.
            // Wait, CopyRates(symbol, tf, time, count, array) gets bars BEFORE and INCLUDING time if we use time? No, it gets bars starting from time if count > 0.
            // Better to use CopyRates(_Symbol, tf, gT[b], 4, htf_rt) where it gets bars starting from gT[b].
         }
      }
   }; */
   
   // Realistically, porting request.security exact lookahead for MTF in MT5 loop is very heavy.
   // Let's implement a simpler version where we just pull the last 3 completed HTF bars and check for FVG when HTF time changes.
   static datetime last_t1 = 0, last_t2 = 0, last_t3 = 0;
   
   if(InpFvgH1On && PeriodSeconds(InpFvgH1Tf) > PeriodSeconds(_Period)) {
      MqlRates rt[];
      if(CopyRates(_Symbol, InpFvgH1Tf, gT[b], 1, rt) > 0) {
         if(rt[0].time != last_t1) {
            // New bar on HTF. The previous 3 bars on HTF are completed.
            MqlRates past[];
            if(CopyRates(_Symbol, InpFvgH1Tf, rt[0].time - 1, 3, past) == 3) { // gets 3 bars before current HTF open
               FvgNewHtf(z1, true, past[0].high, past[0].low, past[2].high, past[2].low, past[2].time, past[2].time + PeriodSeconds(InpFvgH1Tf), InpFvgH1Tf, InpFvgH1Clr, InpFvgH1W, InpFvgN);
            }
            last_t1 = rt[0].time;
         }
      }
   }
   
   if(InpFvgH2On && PeriodSeconds(InpFvgH2Tf) > PeriodSeconds(_Period)) {
      MqlRates rt[];
      if(CopyRates(_Symbol, InpFvgH2Tf, gT[b], 1, rt) > 0) {
         if(rt[0].time != last_t2) {
            MqlRates past[];
            if(CopyRates(_Symbol, InpFvgH2Tf, rt[0].time - 1, 3, past) == 3) {
               FvgNewHtf(z2, true, past[0].high, past[0].low, past[2].high, past[2].low, past[2].time, past[2].time + PeriodSeconds(InpFvgH2Tf), InpFvgH2Tf, InpFvgH2Clr, InpFvgH2W, InpFvgN);
            }
            last_t2 = rt[0].time;
         }
      }
   }
   
   if(InpFvgH3On && PeriodSeconds(InpFvgH3Tf) > PeriodSeconds(_Period)) {
      MqlRates rt[];
      if(CopyRates(_Symbol, InpFvgH3Tf, gT[b], 1, rt) > 0) {
         if(rt[0].time != last_t3) {
            MqlRates past[];
            if(CopyRates(_Symbol, InpFvgH3Tf, rt[0].time - 1, 3, past) == 3) {
               FvgNewHtf(z3, true, past[0].high, past[0].low, past[2].high, past[2].low, past[2].time, past[2].time + PeriodSeconds(InpFvgH3Tf), InpFvgH3Tf, InpFvgH3Clr, InpFvgH3W, InpFvgN);
            }
            last_t3 = rt[0].time;
         }
      }
   }
}

void FvgMtfDrawAll() {
   // Drawings are done via Box and BoxFill helpers which create objects during process.
}
