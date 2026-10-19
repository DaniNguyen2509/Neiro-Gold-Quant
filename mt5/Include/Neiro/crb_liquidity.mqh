//+------------------------------------------------------------------+
//|                                                crb_liquidity.mqh |
//|                                  Liquidity Sweep Engine for EA   |
//+------------------------------------------------------------------+
#property copyright "Neiro-Gold"

struct LiquidityPools {
   double pdh; // Previous Day High
   double pdl; // Previous Day Low
   double ah;  // Asian High
   double al;  // Asian Low
};

LiquidityPools GetLiquidityPools(datetime currentTime) {
    LiquidityPools pools;
    pools.pdh = 0; pools.pdl = 0; pools.ah = 0; pools.al = 0;

    double h[], l[];
    ArraySetAsSeries(h, true); ArraySetAsSeries(l, true);
    if(CopyHigh(_Symbol, PERIOD_D1, 1, 1, h) > 0) pools.pdh = h[0];
    if(CopyLow(_Symbol, PERIOD_D1, 1, 1, l) > 0)  pools.pdl = l[0];

    MqlDateTime dt;
    TimeToStruct(currentTime, dt);
    
    dt.hour = 0; dt.min = 0; dt.sec = 0;
    datetime dayStart = StructToTime(dt);
    dt.hour = 8;
    datetime asianEnd = StructToTime(dt);

    if(currentTime >= dayStart) {
        datetime endSearch = (currentTime < asianEnd) ? currentTime : asianEnd;
        int barStart = iBarShift(_Symbol, PERIOD_M15, endSearch);
        int barEnd = iBarShift(_Symbol, PERIOD_M15, dayStart);
        if(barStart >= 0 && barEnd >= 0 && barEnd >= barStart) {
            int count = barEnd - barStart + 1;
            double ah_arr[], al_arr[];
            if(CopyHigh(_Symbol, PERIOD_M15, barStart, count, ah_arr) == count) {
                pools.ah = ah_arr[ArrayMaximum(ah_arr)];
            }
            if(CopyLow(_Symbol, PERIOD_M15, barStart, count, al_arr) == count) {
                pools.al = al_arr[ArrayMinimum(al_arr)];
            }
        }
    }
    return pools;
}

bool IsLiquiditySwept(int dir, datetime currentTime, int lookbackMinutes = 60, double bufferPts = 5) {
    LiquidityPools pools = GetLiquidityPools(currentTime);
    
    int startBar = iBarShift(_Symbol, PERIOD_M1, currentTime);
    if(startBar < 0) return false;
    
    double h[], l[];
    ArraySetAsSeries(h, true); ArraySetAsSeries(l, true);
    int copiedH = CopyHigh(_Symbol, PERIOD_M1, startBar, lookbackMinutes, h);
    int copiedL = CopyLow(_Symbol, PERIOD_M1, startBar, lookbackMinutes, l);
    
    if(copiedH <= 0 || copiedL <= 0) return false;
    
    double maxH = h[ArrayMaximum(h, 0, copiedH)];
    double minL = l[ArrayMinimum(l, 0, copiedL)];
    
    double buffer = bufferPts * _Point;

    if(dir == 1) { 
        if(pools.pdl > 0 && minL <= pools.pdl + buffer) return true;
        if(pools.al > 0 && minL <= pools.al + buffer) return true;
    } else if(dir == -1) { 
        if(pools.pdh > 0 && maxH >= pools.pdh - buffer) return true;
        if(pools.ah > 0 && maxH >= pools.ah - buffer) return true;
    }
    
    return false;
}
