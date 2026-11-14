//+------------------------------------------------------------------+
//|  crb_engine.mqh - 24-08-2026   (LUAT BAN v3)                      |
//|  ENGINE JUDAS + TURTLE SOUP. MOT NGUON SU THAT cho ca             |
//|  Indicators/CRB-Model-v3.mq5 lan Experts/CRB-EA-v3.mq5.           |
//|  Doi ung 1:1 voi tradingview/CRB-Model-v3.pine - xem              |
//|  docs/architecture.md va docs/model-crb-v3.md                     |
//|                                                                   |
//|  FILE NAY KHONG VE GI, KHONG DAT LENH, KHONG DOC ACCOUNT.         |
//|  No chi tinh vao mang ban ghi:  fv[]  jd[]  ts[]  cx[]  xd*       |
//|  Ai ve, ai vao lenh la viec cua lop tren.                         |
//|                                                                   |
//|  KHONG doc thang o input. Moi tham so di qua g_cfg (CRB_CFG);     |
//|  lop tren tu nap truoc khi chay. Cum CRB (Sweep&Engulf) va Daily  |
//|  Bias KHONG nam o day - chi indicator dung hai cum do.            |
//|                                                                   |
//|  HAI FIELD chi EA dung, indicator bo qua:                         |
//|    sigBar - nen RA QUYET DINH. KHAC sigMk (nen dat dau, co the    |
//|             nam TRUOC sigBar). Vao lenh tai sigMk la NHIN TRUOC.  |
//|    fvPick - chi so khe ho VAO LENH trong fv[], de lay CANH GAN.   |
//|                                                                   |
//|  ====== KHAC BAN v2 O DAU (doi theo CRB-Model-v3.pine) ======     |
//|   1. CAY NEO CISD. Ban v2 dem tu cay cuc tri sang trai roi dung o |
//|      cay nghich mau GAN NHAT (ham CiAncCisd + o tsAncBack) - SAI. |
//|      Nay vach CISD = ci_orig tai ci_oidx, hai so ma chinh may     |
//|      CISD da tinh de BAT su kien: GIA MO CUC TRI cua chuoi nen    |
//|      cung chieu bias cu = cay NGHICH MAU DAU TIEN cua chuoi.      |
//|      Khop tradingview/vendor/kent_combo_v9.pine.                  |
//|      Ham CiAncCisd va o cfg tsAncBack DA GO HAN.                  |
//|   2. BO LOC BIAS H1 (nhom 12). Hai o cfg moi: biasOn / biasDir.   |
//|      Chan dat DUNG CHO RA TIN HIEU, khong phai luc de cu.         |
//|   3. CrbComputeH1Bias() - chay CHINH engine nay lai lan nua tren  |
//|      du lieu H1 de tinh bias. KHONG phai bo luat thu hai.         |
//+------------------------------------------------------------------+
#property copyright "Neiro-Gold"
#property version   "3.00"
#property strict

//==================================================================
//   THAM SO ENGINE - lop tren nap vao truoc moi lan chay
//==================================================================
//==================================================================
//   ENUM cua engine - lop tren dung chung, khong khai lai
//==================================================================
enum ENUM_JDIR
  {
   JDIR_BOTH,   // Ca hai
   JDIR_BULL,   // Chi tang
   JDIR_BEAR    // Chi giam
  };

enum ENUM_JDMARK
  {
   JDM_MID,     // Nen giua FVG
   JDM_DONE,    // Nen hoan tat FVG
   JDM_EXT      // Nen cuc tri
  };

enum ENUM_TSMARK
  {
   TSM_FILL,    // Nen lap iFVG
   TSM_MID,     // Nen giua iFVG
   TSM_EXT      // Nen cuc tri
  };

enum ENUM_XDOT
  {
   XD_SWEPT,    // Chi nen cuc tri co quet
   XD_ALL       // Moi nen cuc tri CISD
  };
struct CRB_CFG
  {
   bool         enJudas;
   bool         enTs;
   ENUM_JDIR    jdDir;
   bool         jdSweep;
   int          jdFvgLen;
   double       jdFvgMult;
   int          jdFvgWin;
   bool         jdNeedMss;
   int          jdAncBack;
   int          jdKeep;
   ENUM_JDMARK  jdMark;
   double       jdGap;
   int          mssLen;
   ENUM_JDIR    tsDir;
   bool         tsSweep;
   int          tsFvgLen;
   double       tsFvgMult;
   int          tsFvgWin;
   bool         tsNeedCisd;
   bool         tsNeedIfvg;
   int          tsKeep;
   bool         jdCont;      // Danh tiep dien Judas
   bool         tsCont;      // Danh tiep dien Turtle Soup
   ENUM_TSMARK  tsMark;
   double       tsGap;
   int          cisdLen;
   bool         xdShow;
   ENUM_XDOT    xdMode;
   int          xdKeep;
   bool         cxShow;
   int          cxKeepOld;
   int          dgKeep;
   //--- BO LOC BIAS H1 (nhom 12, ban v3). Engine H1 tu chay voi
   //    biasOn = false, neu khong no se tu loc chinh no.
   bool         biasOn;
   int          biasDir;      // 1 = BUY, -1 = SELL, 0 = chua co -> KHONG chan
  };
CRB_CFG g_cfg;

datetime gT[];
double   gO[], gH[], gL[], gC[];
double   gA14[];          // ATR 14 - day mui ten / chu ra khoi nen (Pine: sAtr)
double   gAJ[];           // ATR chu ky cua JUDAS  (Pine: jdFvgAtr)
double   gAT[];           // ATR chu ky cua T.SOUP (Pine: tsFvgAtr)
int      gN = 0;

//--- KHO KHE HO DUNG CHUNG (Pine: fvgArr) -------------------------
struct FVGZ
  {
   bool   bull;
   double top, btm, w;
   int    midAbs;            // cay GIUA bo 3 nen = cay TAO RA khe ho
   double hiM, loM;          // dinh/day cay giua
   double hi3, lo3;          // dinh/day cay THU BA - cay lam khe THANH HINH
   bool   alive;
   int    fillAbs;           // nen DONG xuyen han mep xa (-1 = chua bi lap)
   double fillCls, fillHi, fillLo;
  };
FVGZ fv[]; int fv_n = 0;

//--- MOT CU cua co che JUDAS (Pine: JdRec) ------------------------
struct JDREC
  {
   int    dir, extAbs;
   double extPx;
   int    ancAbs;
   double lvl;
   int    brkBar;            // nen DONG CUA xuyen qua vach (-1 = chua)
   bool   done, dead;
   int    lnX2;              // moc phai cua vach
   double ancAtr;            // ATR14 tai nen su kien - day chu MSS
   bool   hasSig;
   int    sigMk;             // cay DAT DAU (hien thi) - CO THE nam TRUOC sigBar
   int    sigBar;            // nen RA QUYET DINH. EA vao lenh O DAY, khong phai sigMk
   int    fvPick;            // chi so khe ho VAO LENH trong fv[] (-1 = chua chon)
   double sigMkPx, sigY, sigAtr;
   int    bxL, bxR;          // hop khe ho VAO LENH
   double bxTop, bxBtm;
   bool   bxBull;
  };
JDREC jd[]; int jd_n = 0;
int    jdsig[]; int jdsig_n = 0;

//--- MOT CU cua co che TURTLE SOUP (Pine: TsRec) ------------------
struct TSREC
  {
   int    dir, extAbs;
   double extPx;
   int    ancAbs;
   double lvl;
   int    brkBar;
   bool   done, dead;
   int    lnX2;
   double ancAtr;
   double ancHi, ancLo;      // dinh/day CAY NEO - chu CISD bam cay nay
   bool   hasSig;
   int    sigMk;             // cay DAT DAU (hien thi) - CO THE nam TRUOC sigBar
   int    sigBar;            // nen RA QUYET DINH. EA vao lenh O DAY, khong phai sigMk
   int    fvPick;            // chi so khe ho VAO LENH trong fv[] (-1 = chua chon)
   double sigMkPx, sigY, sigAtr;
   int    bxL, bxR;
   double bxTop, bxBtm;
   bool   bxBull;
  };
TSREC ts[]; int ts_n = 0;
int    tssig[]; int tssig_n = 0;

//--- Vach cuc tri CISD "CISD Max" (Pine: ExtLine) -----------------
struct CXREC { int startAbs; double px; int dir; int endAbs; bool active; };
CXREC cx[]; int cx_n = 0;
int   cxOld[]; int cxOld_n = 0;      // thu tu RETIRE, cat theo g_cfg.cxKeepOld

//--- Cham nen cuc tri (lop soi) ----------------------------------
int    xdBar[]; double xdPx[]; int xdDir[]; int xd_n = 0;

//--- may CISD (khuc goc dung chung) -------------------------------
int    ci_bias = 0;
double ci_orig = 0.0;
int    ci_oidx = -1;
double ci_thr  = 0.0;
bool   ci_init = false;

//--- co bao tin hieu moi tren CAY VUA DONG ------------------------
bool   g_alJd = false;
bool   g_alTs = false;

//--- BIAS H1 (nhom 12) --------------------------------------------
// Ket qua cua CrbComputeH1Bias() o cuoi file. Lop tren doc de ve bang,
// va nap g_bhDir vao g_cfg.biasDir truoc lan chay chinh.
int      g_bhDir     = 0;   // 1 = BUY, -1 = SELL, 0 = chua co bias
int      g_bhSrc     = 0;   // 1 = JD, 2 = TS, 3 = ca hai cung mot nen H1
int      g_bhAgo     = -1;  // cu giu bias cach day bao nhieu nen H1
double   g_bhPx      = 0;   // gia CUC TRI cua cu dang giu bias
datetime g_bhTime    = 0;   // thoi diem nen H1 ra tin hieu
int      g_bhBlocked = 0;   // dem tin hieu bi bias chan trong lan chay chinh

int    JdDirV(){ return (g_cfg.jdDir==JDIR_BULL)? 1 : ((g_cfg.jdDir==JDIR_BEAR)? -1 : 0); }
int    TsDirV(){ return (g_cfg.tsDir==JDIR_BULL)? 1 : ((g_cfg.tsDir==JDIR_BEAR)? -1 : 0); }

// Ro khe ho phai giu du lau: T.SOUP di tim khe CU ben TRAI cuc tri ma su kien
// CISD co the no ra rat lau sau do. Nguyen van cong thuc fvgKeepEff cua Pine.
int    FvKeepEff(){ return MathMax(g_cfg.dgKeep,120); }

//==================================================================
//   ATR (Wilder) - ba chu ky: 14 chung + chu ky rieng cua tung co che
//==================================================================
void AtrSeries(int per,double &out[])
  {
   if(per<1) per=1;
   ArrayResize(out,gN);
   double tr, prev=0, sum=0;
   for(int b=0;b<gN;b++)
     {
      if(b==0) tr=gH[0]-gL[0];
      else
        {
         double a1=gH[b]-gL[b], a2=MathAbs(gH[b]-gC[b-1]), a3=MathAbs(gL[b]-gC[b-1]);
         tr=MathMax(a1,MathMax(a2,a3));
        }
      double v;
      if(b<per){ sum+=tr; v=sum/(b+1); }
      else if(b==per){ sum+=tr; v=sum/per; }
      else v=(prev*(per-1)+tr)/per;
      prev=v; out[b]=v;
     }
  }
void ComputeAtr()
  {
   AtrSeries(14,gA14);
   AtrSeries(g_cfg.jdFvgLen,gAJ);
   AtrSeries(g_cfg.tsFvgLen,gAT);
  }

//==================================================================
//   KHO KHE HO - chay TRUOC may CISD trong cung nen, de khe ho vua
//   hoan tat tren chinh cay nay da dung duoc ngay (nguyen van Pine).
//   Ghi theo NGUONG LONG HON trong hai nguong; luc CHON vao lenh moi
//   co che ap nguong rieng cua no.
//==================================================================
void FvProcessBar(int b)
  {
   if(b<2) return;
   // 1) khe ho bi LAP: THAN nen DONG xuyen qua mep XA. BAN GHI VAN GIU LAI
   //    (co che Turtle Soup song bang chinh may cai da bi lap), chi tat alive.
   for(int i=0;i<fv_n;i++)
     {
      if(!fv[i].alive) continue;
      if(fv[i].bull ? (gC[b]<fv[i].btm) : (gC[b]>fv[i].top))
        {
         fv[i].alive=false;
         fv[i].fillAbs=b; fv[i].fillCls=gC[b]; fv[i].fillHi=gH[b]; fv[i].fillLo=gL[b];
        }
     }
   // 2) khe ho moi tai nen vua dong (cay 3 = b, cay 1 = b-2)
   bool up=(gL[b] > gH[b-2]);
   bool dn=(gH[b] < gL[b-2]);
   if(!up && !dn) return;
   double tG = up ? gL[b]   : gL[b-2];
   double bG = up ? gH[b-2] : gH[b];
   double wG = tG-bG;
   double storeNeedW = MathMin(gAJ[b]*g_cfg.jdFvgMult, gAT[b]*g_cfg.tsFvgMult);
   if(wG < storeNeedW) return;
   ArrayResize(fv,fv_n+1,256);
   fv[fv_n].bull=up; fv[fv_n].top=tG; fv[fv_n].btm=bG; fv[fv_n].w=wG;
   fv[fv_n].midAbs=b-1;
   fv[fv_n].hiM=gH[b-1]; fv[fv_n].loM=gL[b-1];
   fv[fv_n].hi3=gH[b];   fv[fv_n].lo3=gL[b];
   fv[fv_n].alive=true;  fv[fv_n].fillAbs=-1;
   fv[fv_n].fillCls=0;   fv[fv_n].fillHi=0; fv[fv_n].fillLo=0;
   fv_n++;
   int keepEff=FvKeepEff();
   if(fv_n>keepEff)
     {
      int drop=fv_n-keepEff;
      for(int k=drop;k<fv_n;k++) fv[k-drop]=fv[k];
      fv_n=keepEff; ArrayResize(fv,keepEff);
     }
  }

//==================================================================
//   MAY CISD (nguyen van tu CRB-Model)
//==================================================================
int CiAtt(int idx)
  {
   if(idx<0 || idx>=gN) return 0;
   if(gC[idx]>gO[idx]) return 1;
   if(gC[idx]<gO[idx]) return -1;
   return 0;
  }
void CiConsult(int bias,int ref_idx,double &out_ex,int &out_idx)
  {
   double ex=gO[ref_idx]; int exi=ref_idx;
   int a0=CiAtt(ref_idx);
   if(a0==0 || a0!=bias){ out_ex=ex; out_idx=exi; return; }
   for(int i=1;i<=500;i++)
     {
      int j=ref_idx-i; if(j<0) break;
      int a=CiAtt(j);
      if(a!=0)
        {
         if(a!=bias) break;
         if(bias==1){ if(gO[j]<ex){ ex=gO[j]; exi=j; } }
         else       { if(gO[j]>ex){ ex=gO[j]; exi=j; } }
        }
     }
   out_ex=ex; out_idx=exi;
  }
void CiArch(int bias,int ref_idx,double &out_ex,int &out_idx)
  {
   bool found=false; int maxi=-1; double ex=0.0;
   for(int j=1;j<=500;j++)
     {
      int idx=ref_idx-j; if(idx<0) break;
      int a=CiAtt(idx);
      if(a!=0)
        {
         bool okEra=(a==bias);
         if(!found){ if(okEra){ found=true; maxi=idx; ex=gO[idx]; } }
         else
           {
            if(!okEra) break;
            maxi=idx;
            if(bias==1){ if(gO[idx]<ex) ex=gO[idx]; }
            else       { if(gO[idx]>ex) ex=gO[idx]; }
           }
        }
     }
   if(maxi<0){ out_ex=gO[ref_idx]; out_idx=ref_idx; return; }
   int exi=maxi;
   for(int k=maxi;k<ref_idx;k++){ if(gO[k]==ex){ exi=k; break; } }
   out_ex=ex; out_idx=exi;
  }
//--- CISD: dir=1 -> DAY thap nhat (cu MUA); dir=-1 -> DINH cao nhat (cu BAN)
int CiFindExt(int dir,int from,int to)
  {
   if(from<0 || to<from) return -1;
   int best=from;
   double bv=(dir==1)? gL[from] : gH[from];
   for(int i=from+1;i<=to;i++)
     {
      if(dir==1){ if(gL[i]<bv){ bv=gL[i]; best=i; } }
      else      { if(gH[i]>bv){ bv=gH[i]; best=i; } }
     }
   return best;
  }

// LUAT DISPLACEMENT: cay cuc tri phai tho rau qua nen lien truoc roi keo THAN
// ve. Do MOT LAN moi su kien, roi tung co che tu quyet co ap hay khong.
bool CiSwept(int dir,int extAbs)
  {
   if(extAbs-1<0) return false;
   int o=extAbs, p=extAbs-1;
   if(dir==1)
     {
      double bodyLow=MathMin(gO[o],gC[o]);
      return (gL[o]<gL[p] && bodyLow>gL[p]);
     }
   double bodyHigh=MathMax(gO[o],gC[o]);
   return (gH[o]>gH[p] && bodyHigh<gH[p]);
  }
// CAY NEO cua JUDAS: tu cuc tri dem NGUOC sang trai (TINH CA cay cuc tri), lay
// cay DAU TIEN "thut" so voi cay ben trai lien ke -> vach MSS tai DINH/DAY cay do.
int CiAncMss(int dir,int extAbs)
  {
   int n=g_cfg.jdAncBack; if(n<1) n=1;
   for(int j=0;j<n;j++)
     {
      int bar=extAbs-j;
      if(bar-1<0) break;
      if(dir==1 ? (gL[bar]>gL[bar-1]) : (gH[bar]<gH[bar-1])) return bar;
     }
   return -1;
  }
// CAY NEO cua TURTLE SOUP: KHONG con ham rieng nua (sua 24-08, ban v3).
// Vach CISD = ci_orig tai ci_oidx - hai so ma may CISD o tren da tinh san de
// BAT su kien. Xem khoi chu thich tai cho dung, trong CiProcessBar().

//--- CISD Max: bien vach hien hanh thanh "cu" -----------------------
void CxRetire(int idx,int lockX)
  {
   if(idx<0 || idx>=cx_n) return;
   cx[idx].active=false;
   cx[idx].endAbs=lockX;
   ArrayResize(cxOld,cxOld_n+1,64);
   cxOld[cxOld_n]=idx; cxOld_n++;
   int keep=g_cfg.cxKeepOld; if(keep<0) keep=0;
   if(cxOld_n>keep)
     {
      int drop=cxOld_n-keep;
      for(int k=drop;k<cxOld_n;k++) cxOld[k-drop]=cxOld[k];
      cxOld_n=keep;
     }
  }
int CxCur(){ return (cx_n>0 && cx[cx_n-1].active)? cx_n-1 : -1; }

//--- Cham nen cuc tri (lop soi) -------------------------------------
void XdPush(int bar,double px,int dir)
  {
   ArrayResize(xdBar,xd_n+1,64); ArrayResize(xdPx,xd_n+1,64); ArrayResize(xdDir,xd_n+1,64);
   xdBar[xd_n]=bar; xdPx[xd_n]=px; xdDir[xd_n]=dir; xd_n++;
   int keep=g_cfg.xdKeep; if(keep<1) keep=1;
   if(xd_n>keep)
     {
      int drop=xd_n-keep;
      for(int k=drop;k<xd_n;k++){ xdBar[k-drop]=xdBar[k]; xdPx[k-drop]=xdPx[k]; xdDir[k-drop]=xdDir[k]; }
      xd_n=keep;
     }
  }

//==================================================================
//   KHUC GOC: may CISD -> su kien -> cay cuc tri -> cong quet ->
//   DE RA CU CHO CA HAI CO CHE (doc lap: ben nay truot thi ben kia
//   van ra binh thuong).
//==================================================================
void CiProcessBar(int b)
  {
   if(b<11) return;
   if(ci_bias==0)
     {
      int fi=CiAtt(b);
      if(fi==0)
         for(int k=1;k<=50;k++){ int a=CiAtt(b-k); if(a!=0){ fi=a; break; } }
      if(fi!=0)
        {
         ci_bias=fi;
         CiConsult(fi,b,ci_orig,ci_oidx);
         ci_thr=(fi==1)? gH[b] : gL[b];
         ci_init=true;
        }
     }
   if(!ci_init) return;

   int pers=CiAtt(b);
   if(ci_bias==1)
     {
      if(gH[b]>ci_thr)
        {
         ci_thr=gH[b];
         if(pers==1) CiConsult(1,b,ci_orig,ci_oidx); else CiArch(1,b,ci_orig,ci_oidx);
        }
     }
   else if(ci_bias==-1)
     {
      if(gL[b]<ci_thr)
        {
         ci_thr=gL[b];
         if(pers==-1) CiConsult(-1,b,ci_orig,ci_oidx); else CiArch(-1,b,ci_orig,ci_oidx);
        }
     }

   bool shortsSq =(ci_bias==-1 && gC[b]>ci_orig);
   bool longsRekt=(ci_bias==1  && gC[b]<ci_orig);
   if(!shortsSq && !longsRekt) return;

   int    dir   = shortsSq? 1 : -1;
   int    extAbs= CiFindExt(dir,ci_oidx,b);
   double extPx = (dir==1)? gL[extAbs] : gH[extAbs];

   if(g_cfg.xdShow && g_cfg.xdMode==XD_ALL) XdPush(extAbs,extPx,dir);
   bool swept=CiSwept(dir,extAbs);
   if(g_cfg.xdShow && g_cfg.xdMode==XD_SWEPT && swept) XdPush(extAbs,extPx,dir);

   //--- CO CHE JUDAS: cong displacement RIENG ---
   if(g_cfg.enJudas && (JdDirV()==0 || JdDirV()==dir) && (!g_cfg.jdSweep || swept))
     {
      int aM=CiAncMss(dir,extAbs);
      if(aM>=0)
        {
         ArrayResize(jd,jd_n+1,128);
         jd[jd_n].dir=dir; jd[jd_n].extAbs=extAbs; jd[jd_n].extPx=extPx;
         jd[jd_n].ancAbs=aM; jd[jd_n].lvl=(dir==1)? gH[aM] : gL[aM];
         jd[jd_n].brkBar=-1; jd[jd_n].done=false; jd[jd_n].dead=false;
         jd[jd_n].lnX2=(g_cfg.mssLen>0)? (aM+g_cfg.mssLen) : b;
         jd[jd_n].ancAtr=gA14[b];
         jd[jd_n].hasSig=false; jd[jd_n].sigMk=-1; jd[jd_n].sigBar=-1; jd[jd_n].fvPick=-1; jd[jd_n].sigMkPx=0;
         jd[jd_n].sigY=0; jd[jd_n].sigAtr=0;
         jd[jd_n].bxL=0; jd[jd_n].bxR=0; jd[jd_n].bxTop=0; jd[jd_n].bxBtm=0; jd[jd_n].bxBull=false;
         jd_n++;
        }
     }
   //--- CO CHE TURTLE SOUP: cong displacement RIENG ---
   if(g_cfg.enTs && (TsDirV()==0 || TsDirV()==dir) && (!g_cfg.tsSweep || swept))
     {
      // ===== LUAT CAY NEO CISD (sua 24-08, khop kent_combo_v9) =====
      // Vach CISD = ci_orig: GIA MO CUC TRI cua chuoi nen cung chieu bias CU,
      // tuc cay NGHICH MAU DAU TIEN cua chuoi (dao len thi la cay GIAM cao
      // nhat cua chuoi giam; dao xuong thi la cay TANG thap nhat cua chuoi
      // tang). Chinh may CISD o tren da tinh san hai so nay de BAT su kien
      // (close vuot ci_orig) - khong tinh lai.
      //
      // ci_orig / ci_oidx o day VAN LA GIA TRI TRUOC KHI DAO: khuc gan
      // ci_bias=dir nam BEN DUOI khoi nay.
      int aC=ci_oidx;
      if(aC>=0)
        {
         ArrayResize(ts,ts_n+1,128);
         ts[ts_n].dir=dir; ts[ts_n].extAbs=extAbs; ts[ts_n].extPx=extPx;
         ts[ts_n].ancAbs=aC; ts[ts_n].lvl=ci_orig;
         ts[ts_n].brkBar=-1; ts[ts_n].done=false; ts[ts_n].dead=false;
         ts[ts_n].lnX2=(g_cfg.cisdLen>0)? (aC+g_cfg.cisdLen) : b;
         ts[ts_n].ancAtr=gA14[b]; ts[ts_n].ancHi=gH[aC]; ts[ts_n].ancLo=gL[aC];
         ts[ts_n].hasSig=false; ts[ts_n].sigMk=-1; ts[ts_n].sigBar=-1; ts[ts_n].fvPick=-1; ts[ts_n].sigMkPx=0;
         ts[ts_n].sigY=0; ts[ts_n].sigAtr=0;
         ts[ts_n].bxL=0; ts[ts_n].bxR=0; ts[ts_n].bxTop=0; ts[ts_n].bxBtm=0; ts[ts_n].bxBull=false;
         ts_n++;
        }
     }
   //--- Vach cuc tri CISD (chan doan chung) ---
   // LUON ghi lai cuc tri cho cac co che khac dung (nhu Slope Song Cuc Tri).
   // Viec hien thi se do Indicator tu quyet dinh thong qua g_cfg.cxShow o phan ve.
   int cur=CxCur();
   if(cur>=0) CxRetire(cur,b);
   ArrayResize(cx,cx_n+1,64);
   cx[cx_n].startAbs=extAbs; cx[cx_n].px=extPx; cx[cx_n].dir=dir;
   cx[cx_n].endAbs=b; cx[cx_n].active=true;
   cx_n++;

   ci_bias=dir;
   CiConsult(dir,b,ci_orig,ci_oidx);
   ci_thr=(dir==1)? gH[b] : gL[b];
  }

//==================================================================
//   CO CHE (1) JUDAS - vach MSS + khe ho TUOI ben PHAI cuc tri
//   Khong doc mot bien nao cua co che Turtle Soup.
//==================================================================
void JdUpdateBar(int b)
  {
   int keep=g_cfg.jdKeep; if(keep<1) keep=1;
   int lo=(jd_n>keep)? jd_n-keep : 0;      // ban ghi con nam trong jdArr cua Pine
   for(int i=jd_n-1;i>=lo;i--)
     {
      bool killed=(jd[i].dead && !jd[i].done);   // vach da bi xoa o nen truoc
      //--- 1) vach MSS: keo dai + xet nen dong cua xuyen qua ---
      if(!killed)
        {
         if(g_cfg.mssLen==0 && !jd[i].done) jd[i].lnX2=b;
         if(jd[i].brkBar<0)
            if(jd[i].dir==1 ? (gC[b]>jd[i].lvl) : (gC[b]<jd[i].lvl)) jd[i].brkBar=b;
        }
      //--- 2) khe ho TUOI thuan chieu, DAT NGUONG CUA JUDAS ---
      if(jd[i].dead) continue;
      if(jd[i].done && !g_cfg.jdCont) continue;
      // CUA SO CHINH LA HAN: het cua so ma chua ra tin hieu -> BO CU.
      if(b > jd[i].extAbs-1+g_cfg.jdFvgWin){ jd[i].dead=true; continue; }
      if(g_cfg.jdNeedMss && jd[i].brkBar<0) continue;

      int    loW=jd[i].extAbs-1;
      int    hiW=jd[i].extAbs-2+g_cfg.jdFvgWin;
      double needW=gAJ[b]*g_cfg.jdFvgMult;
      int    pick=-1;
      for(int k=0;k<fv_n;k++)
        {
         if(!fv[k].alive) continue;
         if(fv[k].bull != (jd[i].dir==1)) continue;
         if(fv[k].midAbs<loW || fv[k].midAbs>hiW) continue;
         if(fv[k].w < needW) continue;
         if(jd[i].done && k <= jd[i].fvPick) continue;
         pick=k; break;                       // lay cai DAU TIEN hinh thanh, con TUOI
        }
      if(pick<0) continue;

      // ---- CONG BIAS H1 (nhom 12) ----
      // Loc dat DUNG CHO RA TIN HIEU: bias luc de cu va bias luc ra tin hieu
      // co the khac nhau, ma cai dang ke la bias TAI KHOANH KHAC VAO LENH.
      // Ban Pine danh dau done roi xoa hinh; ben MT5 danh dau DEAD - nhin
      // thay y het: khong vach MSS, khong mui ten, khong alert.
      if(g_cfg.biasOn && g_cfg.biasDir!=0 && g_cfg.biasDir!=jd[i].dir)
        { jd[i].dead=true; g_bhBlocked++; continue; }

      int    dir=jd[i].dir;
      int    mk; double mkPx;
      if(g_cfg.jdMark==JDM_EXT)      { mk=jd[i].extAbs;     mkPx=jd[i].extPx; }
      else if(g_cfg.jdMark==JDM_MID) { mk=fv[pick].midAbs;  mkPx=(dir==1)? fv[pick].loM : fv[pick].hiM; }
      else                        { mk=fv[pick].midAbs+1;mkPx=(dir==1)? fv[pick].lo3 : fv[pick].hi3; }
      // RA NGOAI HOP: cay dat dau mac dinh nam trong be ngang cua hop, de nguyen
      // thi mui ten va chu chim vao nen hop -> lay MEP HOP lam moc day ra.
      if(g_cfg.jdMark!=JDM_EXT && mk>=fv[pick].midAbs-1 && mk<=fv[pick].midAbs+1)
         mkPx=(dir==1)? MathMin(mkPx,fv[pick].btm) : MathMax(mkPx,fv[pick].top);

      double aOff=gA14[b]*g_cfg.jdGap;
      jd[i].sigMk   = mk;
      jd[i].sigMkPx = mkPx;
      jd[i].sigY    = (dir==1)? mkPx-aOff : mkPx+aOff;
      jd[i].sigAtr  = gA14[b];
      jd[i].bxL     = fv[pick].midAbs-1;
      jd[i].bxR     = fv[pick].midAbs+1;
      jd[i].bxTop   = fv[pick].top;
      jd[i].bxBtm   = fv[pick].btm;
      jd[i].bxBull  = fv[pick].bull;
      jd[i].sigBar  = b;          // NEN RA QUYET DINH - docs/model-crb-v3.md 15.3
      jd[i].fvPick  = pick;
      jd[i].hasSig  = true;
      jd[i].done    = true;
      ArrayResize(jdsig,jdsig_n+1,128);
      jdsig[jdsig_n]=i; jdsig_n++;
      if(b==gN-2) g_alJd=true;
     }
  }

//==================================================================
//   CO CHE (2) TURTLE SOUP - vach CISD + khe ho CU ben TRAI bi lap
//   Khong doc mot bien nao cua co che Judas.
//==================================================================
void TsUpdateBar(int b)
  {
   int keep=g_cfg.tsKeep; if(keep<1) keep=1;
   int lo=(ts_n>keep)? ts_n-keep : 0;
   for(int i=ts_n-1;i>=lo;i--)
     {
      bool killed=(ts[i].dead && !ts[i].done);
      //--- 1) vach CISD: keo dai + xet nen dong cua xuyen qua ---
      if(!killed)
        {
         if(g_cfg.cisdLen==0 && !ts[i].done) ts[i].lnX2=b;
         if(ts[i].brkBar<0)
            if(ts[i].dir==1 ? (gC[b]>ts[i].lvl) : (gC[b]<ts[i].lvl)) ts[i].brkBar=b;
        }
      //--- 2) khe ho NGUOC chieu DA BI LAP, DAT NGUONG CUA T.SOUP ---
      if(ts[i].dead) continue;
      if(ts[i].done && !g_cfg.tsCont) continue;
      // CUA SO CHINH LA HAN: iFVG nam san ben TRAI cuc tri, cai phai cho la NEN LAP.
      if(b > ts[i].extAbs+g_cfg.tsFvgWin){ ts[i].dead=true; continue; }

      int    loW=ts[i].extAbs-g_cfg.tsFvgWin+1;
      int    hiW=ts[i].extAbs;
      double needW=gAT[b]*g_cfg.tsFvgMult;
      int    pick=-1, best=-1;
      int    dir=ts[i].dir;
      for(int k=0;k<fv_n;k++)
        {
         if(fv[k].bull != (dir==-1)) continue;
         if(fv[k].midAbs<loW || fv[k].midAbs>hiW) continue;
         if(fv[k].w < needW) continue;
         if(fv[k].fillAbs < ts[i].extAbs) continue;       // phai bi lap TU cuc tri tro di
         // O TUY CHON, MAC DINH BAT: chinh NEN LAP phai dong cua xuyen qua vach
         // CISD trong CUNG mot nen. Tat di thi ve luat goc cua Turtle Soup.
         if(g_cfg.tsNeedCisd)
            if(!(dir==1 ? (fv[k].fillCls>ts[i].lvl) : (fv[k].fillCls<ts[i].lvl))) continue;

         // --- NEW TS FILTER: FVG MUST BE FILLED BY AN OPPOSITE FVG ---
         bool filledByOpposite = false;
         if(g_cfg.tsNeedIfvg)
           {
            for(int kn=0; kn<fv_n; kn++)
              {
               if(fv[kn].bull == (dir==1) && fv[kn].midAbs > ts[i].extAbs)
                 {
                  if(fv[kn].btm <= fv[k].top && fv[kn].top >= fv[k].btm)
                    {
                     filledByOpposite = true;
                     break;
                    }
                 }
              }
           }
         else
           {
            filledByOpposite = true;
           }
         if(!filledByOpposite) continue;
         if(ts[i].done && k <= ts[i].fvPick) continue;

         if(pick<0 || fv[k].fillAbs<best){ best=fv[k].fillAbs; pick=k; }  // lay cai LAP SOM NHAT
        }
      if(pick<0) continue;

      // ---- CONG BIAS H1 (nhom 12) - y het ben Judas, xem chu thich o do.
      if(g_cfg.biasOn && g_cfg.biasDir!=0 && g_cfg.biasDir!=dir)
        { ts[i].dead=true; g_bhBlocked++; continue; }

      int    mk; double mkPx;
      if(g_cfg.tsMark==TSM_EXT)      { mk=ts[i].extAbs;    mkPx=ts[i].extPx; }
      else if(g_cfg.tsMark==TSM_MID) { mk=fv[pick].midAbs; mkPx=(dir==1)? fv[pick].loM  : fv[pick].hiM; }
      else                        { mk=fv[pick].fillAbs;mkPx=(dir==1)? fv[pick].fillLo : fv[pick].fillHi; }
      int bxR=MathMax(fv[pick].fillAbs,fv[pick].midAbs+1);
      if(g_cfg.tsMark!=TSM_EXT && mk>=fv[pick].midAbs-1 && mk<=bxR)
         mkPx=(dir==1)? MathMin(mkPx,fv[pick].btm) : MathMax(mkPx,fv[pick].top);

      double aOff=gA14[b]*g_cfg.tsGap;
      ts[i].sigMk   = mk;
      ts[i].sigMkPx = mkPx;
      ts[i].sigY    = (dir==1)? mkPx-aOff : mkPx+aOff;
      ts[i].sigAtr  = gA14[b];
      // Hop KEO DAI tu cay 1 cua bo 3 nen (luc khe SINH RA) toi dung NEN LAP.
      ts[i].bxL     = fv[pick].midAbs-1;
      ts[i].bxR     = bxR;
      ts[i].bxTop   = fv[pick].top;
      ts[i].bxBtm   = fv[pick].btm;
      ts[i].bxBull  = fv[pick].bull;
      ts[i].sigBar  = b;          // NEN RA QUYET DINH - docs/model-crb-v3.md 15.3
      ts[i].fvPick  = pick;
      ts[i].hasSig  = true;
      ts[i].done    = true;
      ArrayResize(tssig,tssig_n+1,128);
      tssig[tssig_n]=i; tssig_n++;
      if(b==gN-2) g_alTs=true;
     }
  }

//==================================================================
//   VACH CUC TRI CISD: keo dai + xet pha vo (chay SAU hai co che)
//==================================================================
void CxUpdateBar(int b)
  {
   int cur=CxCur();
   if(cur<0) return;
   cx[cur].endAbs=b;
   if(cx[cur].dir==1 ? (gC[b]<cx[cur].px) : (gC[b]>cx[cur].px)) CxRetire(cur,b);
  }

//==================================================================
//   Reset state cua engine - lop tren goi truoc moi lan chay lai
//==================================================================
void CrbEngineReset()
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
   g_alJd=false; g_alTs=false;
  }

//==================================================================
//   BIAS H1  (nhom 12 cua ban v3)
//
//   Chay CHINH engine tren lai lan nua tren du lieu H1 roi lay chieu
//   cua cu JD/TS RA TIN HIEU gan nhat lam bias. KHONG phai bo luat
//   thu hai: cung ham, cung mang, chi khac nguon nen va hai he so be
//   rong khe ho.
//
//   BIAS song VO THOI HAN toi khi co cu H1 NGUOC CHIEU ra tin hieu.
//   Cung mot nen H1 ma hai cu nguoc chieu cung ra thi cu co CAY CUC
//   TRI MOI HON thang (owner chot 23-08).
//
//   KHONG doc enJudas/enTs va jdDir/tsDir cua lop tren: hai bo o do
//   la "hien cai gi tren chart", con bias thi luon xet CA HAI co che
//   va CA HAI chieu.
//
//   ==== THU TU GOI (bat buoc) ====
//   Ham nay dung CHUNG mang fv/jd/ts voi lan chay chinh nen no XOA
//   SACH state. Lop tren phai goi theo dung thu tu:
//        CfgFill()  ->  CrbComputeH1Bias(...)  ->  nap lai series cua
//        khung chart  ->  vong lap chinh (mo dau bang CrbEngineReset).
//
//   ==== KHONG NHIN TRUOC ====
//   Vong lap dung o gN-2: nen H1 DANG HINH THANH (gN-1) khong bao gio
//   duoc tinh. Nho vay bias chi doi dung luc nen H1 dong.
//==================================================================
bool CrbComputeH1Bias(const double jdMult,const double tsMult,const int winBars)
  {
   g_bhDir=0; g_bhSrc=0; g_bhAgo=-1; g_bhPx=0; g_bhTime=0;

   int wb=winBars; if(wb<200) wb=200; if(wb>5000) wb=5000;
   MqlRates rt[];
   ArraySetAsSeries(rt,false);
   int got=CopyRates(_Symbol,PERIOD_H1,0,wb,rt);
   int minBars=MathMax(g_cfg.jdFvgLen,g_cfg.tsFvgLen)+30;
   if(got<minBars) return false;

   //--- cfg TAM: hai he so rieng cua engine H1; hai co che va hai chieu MO HET
   CRB_CFG save=g_cfg;
   g_cfg.enJudas   = true;        g_cfg.enTs      = true;
   g_cfg.jdDir     = JDIR_BOTH;   g_cfg.tsDir     = JDIR_BOTH;
   g_cfg.jdFvgMult = jdMult;      g_cfg.tsFvgMult = tsMult;
   g_cfg.biasOn    = false;       g_cfg.biasDir   = 0;
   g_cfg.xdShow    = false;       g_cfg.cxShow    = false;

   gN=got;
   ArrayResize(gT,gN); ArrayResize(gO,gN); ArrayResize(gH,gN);
   ArrayResize(gL,gN); ArrayResize(gC,gN);
   for(int b=0;b<gN;b++)
     { gT[b]=rt[b].time; gO[b]=rt[b].open; gH[b]=rt[b].high; gL[b]=rt[b].low; gC[b]=rt[b].close; }

   CrbEngineReset();
   ComputeAtr();
   int warm=MathMax(MathMax(g_cfg.jdFvgLen,g_cfg.tsFvgLen),20)+5;
   for(int b=warm;b<gN-1;b++)   // gN-1 = nen H1 DANG HINH THANH, khong tinh
     {
      FvProcessBar(b);          // kho khe ho chay TRUOC may CISD trong cung nen
      CiProcessBar(b);
      JdUpdateBar(b);
      TsUpdateBar(b);
      CxUpdateBar(b);
     }

   //--- cu RA TIN HIEU gan nhat thang; cung nen thi CUC TRI MOI HON thang
   int    wBar=-1, wExt=-1, wDir=0, wSrc=0;
   double wPx=0;
   for(int k=0;k<jdsig_n;k++)
     {
      int i=jdsig[k]; if(i<0 || i>=jd_n) continue;
      if(!jd[i].hasSig) continue;
      if(jd[i].sigBar>wBar || (jd[i].sigBar==wBar && jd[i].extAbs>wExt))
        { wBar=jd[i].sigBar; wExt=jd[i].extAbs; wDir=jd[i].dir; wPx=jd[i].extPx; wSrc=1; }
     }
   for(int k=0;k<tssig_n;k++)
     {
      int i=tssig[k]; if(i<0 || i>=ts_n) continue;
      if(!ts[i].hasSig) continue;
      if(ts[i].sigBar>wBar || (ts[i].sigBar==wBar && ts[i].extAbs>wExt))
        { wBar=ts[i].sigBar; wExt=ts[i].extAbs; wDir=ts[i].dir; wPx=ts[i].extPx; wSrc=2; }
      else
         if(ts[i].sigBar==wBar && ts[i].extAbs==wExt && ts[i].dir==wDir) wSrc=3;
     }

   if(wDir!=0)
     {
      g_bhDir=wDir; g_bhSrc=wSrc; g_bhPx=wPx;
      g_bhAgo=(gN-2)-wBar;             // nen H1 DA DONG gan nhat = gN-2
      if(wBar>=0 && wBar<gN) g_bhTime=gT[wBar];
     }

   g_cfg=save;
   return true;
  }

//==================================================================
//   BANG HE SO THEO KHUNG (nhom 11) - LOP CHON, KHONG PHAI LUAT
//==================================================================
// CHI CRB-Model-v3.mq5 DUNG. Owner chot 25-08: EA KHONG can bang nay, no
// van giu nguyen "de 0 = BO nguong be rong" nhu truoc gio. Ba ham duoi de o
// day chu khong de trong indicator vi chung la LUAT CHON, khong phai code ve.
// Engine KHONG doc bang - no chi nhan g_cfg.jdFvgMult da chot roi.
// Ba ham duoi la lop NAP INPUT, dung TRUOC khi goi CfgFill().
//
// !! O HE SO CUA EA MANG NGHIA KHAC. Ben EA, InpJdFvgMult = 0 van la BO HAN
// nguong be rong. Dung chep so 0 qua lai giua hai file.
//
// CONG TAC nam o CHINH O HE SO: de 0 = giao o do cho bang lai, go so khac 0
// thi so do thang va bang khong dung toi. Hai co che DOC LAP - giao Judas cho
// bang ma van giu tay Turtle Soup cung duoc.
//
// Chon dong theo nguyen tac DONG GAN NHAT BEN DUOI:
//   < M5  -> dong M1   (ke ca chart giay, M2, M3, M4)
//   < M15 -> dong M5   (M5 .. M14, vi du M10)
//   < H1  -> dong M15  (M15 .. M59, vi du M30)
//   >= H1 -> dong H1   (H1, H4, D1, W1, MN)
int CrbTfRow(const ENUM_TIMEFRAMES tf)
  {
   int s=PeriodSeconds(tf);
   if(s<300)  return 0;
   if(s<900)  return 1;
   if(s<3600) return 2;
   return 3;
  }

// Lay o cua dong dang chon. Bon tham so xep theo thu tu M1, M5, M15, H1.
double CrbTfPick(const ENUM_TIMEFRAMES tf,const double m1,const double m5,
                 const double m15,const double h1)
  {
   int r=CrbTfRow(tf);
   if(r==0) return m1;
   if(r==1) return m5;
   if(r==2) return m15;
   return h1;
  }

// He so THAT SU chay. inpMult == 0 la cong tac giao cho bang.
double CrbMultEff(const double inpMult,const ENUM_TIMEFRAMES tf,
                  const double m1,const double m5,const double m15,const double h1)
  {
   return (inpMult==0.0) ? CrbTfPick(tf,m1,m5,m15,h1) : inpMult;
  }
