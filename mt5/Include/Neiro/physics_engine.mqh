//+------------------------------------------------------------------+
//|                                               physics_engine.mqh |
//|                                     Copyright 2026, Neiro-Gold   |
//+------------------------------------------------------------------+
#property copyright "Neiro-Gold"
#property version   "1.00"

//--- Cac kieu du lieu
enum ENUM_SL_UNIT
  {
   SLU_ATR  = 0,
   SLU_PIPS = 1,
   SLU_RAW  = 2
  };
  
enum ENUM_PHYSICS_STATE
  {
   PHYSICS_STATE_NONE          = 0,
   PHYSICS_STATE_ACCUMULATION  = 1,
   PHYSICS_STATE_EXPLOSION_UP  = 2,
   PHYSICS_STATE_EXPLOSION_DN  = 3,
   PHYSICS_STATE_INERTIA_UP    = 4,
   PHYSICS_STATE_INERTIA_DN    = 5,
   PHYSICS_STATE_PULLBACK_LIGHT_UP = 6,
   PHYSICS_STATE_PULLBACK_LIGHT_DN = 7,
   PHYSICS_STATE_PULLBACK_DEEP_UP  = 8,
   PHYSICS_STATE_PULLBACK_DEEP_DN  = 9,
   PHYSICS_STATE_REVERSAL_CONFIRMED_UP = 10,
   PHYSICS_STATE_REVERSAL_CONFIRMED_DN = 11,
   PHYSICS_STATE_MAX_TENSION_UP    = 12,
   PHYSICS_STATE_MAX_TENSION_DN    = 13,
   PHYSICS_STATE_NOISE         = 14,
   PHYSICS_STATE_OTHER         = 15
  };

struct PHYSICS_CFG
  {
   ENUM_APPLIED_PRICE src;
   double             flatThreshold;
   double             r2Min;
   ENUM_SL_UNIT       unit;
   ENUM_APPLIED_VOLUME volType;
   int                volMA;
   int                baseMA;
   bool               p2On;
   bool               p2Acc;
   double             p2AccMul;
   double             r2Gap;
   int                atrLen;
   bool               energyOn;
   int                slLen;
   double             slKAmp;
  };

PHYSICS_CFG p_cfg;

//--- Trang thai hien tai
ENUM_PHYSICS_STATE p_state = PHYSICS_STATE_NONE;

//--- Nhan bien toan cuc
double p_bRaw = 0;
double p_bNorm= 0;
double p_r2   = 0;
double p_sd   = 0;
double p_atr  = 0;
bool   p_ok   = false;

bool   p_p2ok = false;
double p_p2Slope = 0;
double p_p2Acc = 0;
double p_p2r2  = 0;

double p_mass = 0;
double p_ek   = 0;
double p_ep   = 0;
double p_mom  = 0;

double Px(const MqlRates &r)
  {
   switch(p_cfg.src)
     {
      case PRICE_OPEN:     return r.open;
      case PRICE_HIGH:     return r.high;
      case PRICE_LOW:      return r.low;
      case PRICE_CLOSE:    return r.close;
      case PRICE_MEDIAN:   return (r.high+r.low)/2.0;
      case PRICE_TYPICAL:  return (r.high+r.low+r.close)/3.0;
      case PRICE_WEIGHTED: return (r.high+r.low+r.close*2.0)/4.0;
     }
   return r.close;
  }

bool LinReg(const MqlRates &rt[],const int end,const int N,
            double &b,double &a,double &r2,double &sd)
  {
   b=0.0; a=0.0; r2=0.0; sd=0.0;
   int st=end-N+1;
   if(st<0 || N<3) return(false);

   double sx  = N*(N-1)/2.0;
   double sxx = (N-1)*N*(2.0*N-1)/6.0;
   double den = N*sxx - sx*sx;
   if(MathAbs(den)<1e-12) return(false);

   double sy=0.0, sxy=0.0;
   for(int k=0;k<N;k++)
     {
      double y=Px(rt[st+k]);
      sy  += y;
      sxy += k*y;
     }

   b = (N*sxy - sx*sy)/den;
   a = (sy - b*sx)/N;

   double ybar=sy/N, ssTot=0.0, ssRes=0.0;
   for(int k=0;k<N;k++)
     {
      double y   = Px(rt[st+k]);
      double res = y-(a+b*k);
      ssTot += (y-ybar)*(y-ybar);
      ssRes += res*res;
     }
   r2 = (ssTot>1e-12) ? 1.0-ssRes/ssTot : 0.0;
   if(r2<0.0) r2=0.0;
   sd = (N>2) ? MathSqrt(ssRes/(N-2)) : 0.0;
   return(true);
  }

bool LinReg2(const MqlRates &rt[],const int end,const int N,const int offset,const bool is3Point,
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
      double y1 = Px(rt[st]);
      double y2 = Px(rt[st + N - 1]);
      double y3 = Px(rt[end]);

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
      double x=k-half;
      double y=Px(rt[st+k]);
      T0 += y;
      T1 += x*y;
      T2 += x*x*y;
     }

   b = T1/S2;
   a = (dN*T2 - S2*T0)/den;
   c = (T0 - S2*a)/dN;

   double ybar=T0/dN, ssTot=0.0, ssRes=0.0;
   for(int k=0;k<N;k++)
     {
      double x   = k-half;
      double y   = Px(rt[st+k]);
      double res = y-(c + b*x + a*x*x);
      ssTot += (y-ybar)*(y-ybar);
      ssRes += res*res;
     }
   r2 = (ssTot>1e-12) ? 1.0-ssRes/ssTot : 0.0;
   if(r2<0.0) r2=0.0;
   return(true);
  }

//+------------------------------------------------------------------+
//| Cap nhat trang thai vat ly cho NEN CUOI                          |
//+------------------------------------------------------------------+
void PhysicsEngineUpdate(const MqlRates &rt[], int got, int N, int offset=0, bool is3Point=false)
  {
   p_ok = false;
   p_p2ok = false;
   p_state = PHYSICS_STATE_NONE;
   
   if(got < N || N < 3) return;
   int last = got-1;
   
   double curAtr = 0.0;
   if(p_cfg.atrLen > 0 && got >= p_cfg.atrLen + offset + 1)
     {
      double sumTr = 0;
      for(int i = 1; i <= p_cfg.atrLen; i++)
        {
         int idx = last - offset - i + 1;
         double tr = MathMax(rt[idx].high - rt[idx].low,
                     MathMax(MathAbs(rt[idx].high - rt[idx-1].close),
                             MathAbs(rt[idx].low - rt[idx-1].close)));
         sumTr += tr;
        }
      curAtr = sumTr / p_cfg.atrLen;
     }
   else if (p_cfg.atrLen <= 0)
     {
      // Fallback if atrLen is 0
      curAtr = 1.0;
     }
   
   double bb, aa, rr, ss;
   p_ok = LinReg(rt, last - offset, N, bb, aa, rr, ss);
   
   if(p_ok)
     {
      p_bRaw = bb;
      p_r2   = rr;
      p_sd   = ss;
      p_atr  = curAtr;
      p_bNorm= (p_atr>0.0) ? bb/p_atr : 0.0;
      
      // Tinh Toan Nang Luong
      if(p_cfg.energyOn)
        {
         double sumV = 0;
         for(int k=0; k<N; k++) {
            sumV += (p_cfg.volType==VOLUME_TICK) ? (double)rt[last-N+1+k].tick_volume : (double)rt[last-N+1+k].real_volume;
         }
         double avgV = sumV / N;
         
         double sumMA = 0;
         int p = p_cfg.volMA;
         if(p > last+1) p = last+1;
         if(p <= 0) p = 1;
         for(int k=0; k<p; k++) {
            sumMA += (p_cfg.volType==VOLUME_TICK) ? (double)rt[last-k].tick_volume : (double)rt[last-k].real_volume;
         }
         double avgMA = sumMA / p;
         
         double mass = (avgMA > 0) ? (avgV / avgMA) : 1.0;
         if(mass > 3.0) mass = 3.0; 
         p_mass = mass;
         double vv = p_bNorm;
         p_ek = 0.5 * mass * vv * MathAbs(vv) * 100.0;
         p_mom = mass * vv;
         
         double sumBase = 0;
         int bMA = p_cfg.baseMA;
         if(bMA <= 0) bMA = N; 
         if(bMA > last+1) bMA = last+1;
         for(int k=0; k<bMA; k++) {
            sumBase += Px(rt[last-k]);
         }
         double avgBase = sumBase / bMA;
         
         double omega = (bMA > 0) ? (2.0 * 3.1415926535 / bMA) : 1.0;
         double ybar = aa + bb * (N - 1.0) / 2.0;
         double x = (p_atr > 0) ? (ybar - avgBase) / p_atr : 0.0;
         p_ep = 0.5 * mass * MathPow(omega * x, 2) * 100.0;
        }
        
      // Tinh Toan Gia Toc
      if(p_cfg.p2On)
        {
         double q2a, q2b, q2c, q2r2;
         p_p2ok = LinReg2(rt, last, N, offset, is3Point, q2a, q2b, q2c, q2r2);
         if(p_p2ok)
           {
            p_p2r2 = q2r2;
            double half = (N-1.0)/2.0;
            double k = (is3Point && p_cfg.slKAmp > 0.0 && p_cfg.slLen > 0) ? MathPow((double)N / p_cfg.slLen, p_cfg.slKAmp) : 1.0;
            double slp = q2b + 2.0 * q2a * (half + offset);
            p_p2Slope = (p_atr>0.0) ? (slp/p_atr) * k : 0.0;
            if(p_cfg.p2Acc && p_atr>0.0) p_p2Acc = (2.0 * q2a / p_atr) * k * k;
            else p_p2Acc = 0;
           }
        }
        
      //--- PHAN LOAI TRANG THAI ---
      bool haveP2 = (p_cfg.p2On && p_p2ok);
      // NEN SUY XET NOISE SAU KHI KIEM TRA REVERSAL, hoac ket hop p_p2r2!
      // Voi Judas/TS (dao chieu manh), r2 tuyen tinh se luon < 0.5 vi no la duong cong.
      // Neu ta ep vao NOISE luon, EA se block 100% lenh Judas/TS!
      bool isNoise = (p_r2 < p_cfg.r2Min && (!haveP2 || p_p2r2 < p_cfg.r2Min));
      
      if(isNoise)
        {
         p_state = PHYSICS_STATE_NOISE;
        }
      else if(p_cfg.energyOn && MathAbs(p_bNorm) > p_cfg.flatThreshold)
        {
         bool isUptrend = (p_bNorm > 0);
         bool isBraking = (haveP2 && ((isUptrend && p_p2Acc < 0) || (!isUptrend && p_p2Acc > 0)));
         bool epDominates = (MathAbs(p_ep) >= MathAbs(p_ek));
         bool isP2Flip = (haveP2 && ((isUptrend && p_p2Slope < 0) || (!isUptrend && p_p2Slope > 0)));
         bool isCurve = (haveP2 && p_p2r2 >= p_cfg.r2Min && (p_p2r2 - p_r2) >= p_cfg.r2Gap);
         
         if(isCurve)
           {
            // Trạng thái ĐANG CONG (Gia tốc rõ rệt hơn Đường thẳng)
            if(epDominates)
              {
               if(isP2Flip)
                  p_state = isUptrend ? PHYSICS_STATE_REVERSAL_CONFIRMED_DN : PHYSICS_STATE_REVERSAL_CONFIRMED_UP;
               else
                  p_state = isUptrend ? PHYSICS_STATE_MAX_TENSION_UP : PHYSICS_STATE_MAX_TENSION_DN;
              }
            else
              {
               if(isP2Flip)
                  p_state = isUptrend ? PHYSICS_STATE_PULLBACK_DEEP_UP : PHYSICS_STATE_PULLBACK_DEEP_DN;
               else
                  p_state = isUptrend ? PHYSICS_STATE_PULLBACK_LIGHT_UP : PHYSICS_STATE_PULLBACK_LIGHT_DN;
              }
           }
         else if(isBraking)
           {
            if(epDominates)
              {
               if(isP2Flip)
                  p_state = isUptrend ? PHYSICS_STATE_REVERSAL_CONFIRMED_DN : PHYSICS_STATE_REVERSAL_CONFIRMED_UP;
               else
                  p_state = isUptrend ? PHYSICS_STATE_MAX_TENSION_UP : PHYSICS_STATE_MAX_TENSION_DN;
              }
            else
              {
               if(isP2Flip)
                  p_state = isUptrend ? PHYSICS_STATE_PULLBACK_DEEP_UP : PHYSICS_STATE_PULLBACK_DEEP_DN;
               else
                  p_state = isUptrend ? PHYSICS_STATE_PULLBACK_LIGHT_UP : PHYSICS_STATE_PULLBACK_LIGHT_DN;
              }
           }
         else
           {
            if(!epDominates)
               p_state = isUptrend ? PHYSICS_STATE_EXPLOSION_UP : PHYSICS_STATE_EXPLOSION_DN;
            else
              {
               if(p_mass > 1.5)
                  p_state = isUptrend ? PHYSICS_STATE_INERTIA_UP : PHYSICS_STATE_INERTIA_DN;
               else
                  p_state = PHYSICS_STATE_ACCUMULATION;
              }
           }
        }
      else
        {
         if(MathAbs(p_bNorm) <= p_cfg.flatThreshold) p_state = PHYSICS_STATE_ACCUMULATION;
         else p_state = PHYSICS_STATE_OTHER;
        }
     }
  }
