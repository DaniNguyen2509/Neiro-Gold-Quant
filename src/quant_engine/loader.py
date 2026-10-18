"""
Data Ingestion and Parser Module for Neiro-Quant.
Loads options_prices.csv and volatility-greeks.csv from data/.
"""

import os
import re
import numpy as np
import pandas as pd

def clean_val(v):
    if v is None or v == 'N/A' or v == '':
        return 0.0
    v = str(v).replace('s', '').replace('%', '').replace(',', '').replace('"', '').strip()
    try:
        return float(v)
    except:
        return 0.0

def load_options_data(data_dir=None):
    if data_dir is None:
        candidates = ['data', '../data', 'C:/Users/Daniel/Documents/My-Projects/Neiro-Quant/data']
        for c in candidates:
            if os.path.exists(os.path.join(c, 'options_prices.csv')):
                data_dir = c
                break
    if data_dir is None:
        data_dir = 'data'
        
    prices_file = os.path.join(data_dir, 'options_prices.csv')
    greeks_file = os.path.join(data_dir, 'volatility-greeks.csv')
    
    if os.path.exists(prices_file):
        return parse_dual_files(prices_file, greeks_file if os.path.exists(greeks_file) else None)
        
    raise FileNotFoundError(f"Could not find options_prices.csv in {data_dir}")

def parse_dual_files(prices_path, greeks_path=None):
    greeks_map = {}
    if greeks_path and os.path.exists(greeks_path):
        with open(greeks_path, 'r', encoding='utf-8-sig') as f:
            g_lines = [l.strip() for l in f if l.strip()]
            
        for i in range(266, len(g_lines), 10):
            if i + 5 < len(g_lines):
                try:
                    strike_k = float(g_lines[i].replace('"', '').replace(',', ''))
                    iv_val = clean_val(g_lines[i+3]) / 100.0
                    delta_val = clean_val(g_lines[i+4])
                    gamma_val = clean_val(g_lines[i+5])
                    greeks_map[strike_k] = {'iv': iv_val, 'delta': delta_val, 'gamma': gamma_val}
                except Exception:
                    pass
                    
    with open(prices_path, 'r', encoding='utf-8-sig') as f:
        p_lines = [l.strip() for l in f if l.strip()]
        
    calls = {}
    puts = {}
    
    for i in range(14, min(254, len(p_lines)), 12):
        chunk = p_lines[i:i+12]
        if len(chunk) >= 10:
            m = re.match(r'^"?(\d{1,2},\d{3}\.\d{2})C"?$', chunk[0])
            if m:
                strike = float(m.group(1).replace(',', ''))
                latest = clean_val(chunk[4])
                bid = clean_val(chunk[6])
                ask = clean_val(chunk[7])
                vol = clean_val(chunk[8])
                oi = clean_val(chunk[9])
                calls[strike] = {'latest': latest, 'bid': bid, 'ask': ask, 'vol': vol, 'oi': oi}
                
    for i in range(268, len(p_lines), 12):
        chunk = p_lines[i:i+12]
        if len(chunk) >= 10:
            m = re.match(r'^"?(\d{1,2},\d{3}\.\d{2})P"?$', chunk[0])
            if m:
                strike = float(m.group(1).replace(',', ''))
                latest = clean_val(chunk[4])
                bid = clean_val(chunk[6])
                ask = clean_val(chunk[7])
                vol = clean_val(chunk[8])
                oi = clean_val(chunk[9])
                puts[strike] = {'latest': latest, 'bid': bid, 'ask': ask, 'vol': vol, 'oi': oi}
                
    all_strikes = sorted(set(calls.keys()).intersection(set(puts.keys())))
    if not all_strikes:
        raise ValueError("No matching Calls and Puts in " + prices_path)
        
    ref_strikes = np.array(sorted(greeks_map.keys())) if greeks_map else np.array([])
    ref_gammas = np.array([greeks_map[k]['gamma'] for k in ref_strikes]) if greeks_map else np.array([])
    ref_ivs = np.array([greeks_map[k]['iv'] for k in ref_strikes]) if greeks_map else np.array([])
    
    rows = []
    for k in all_strikes:
        c = calls[k]
        p = puts[k]
        
        c_mid = (c['bid'] + c['ask']) / 2.0 if (c['bid'] > 0 and c['ask'] > 0) else c['latest']
        p_mid = (p['bid'] + p['ask']) / 2.0 if (p['bid'] > 0 and p['ask'] > 0) else p['latest']
        
        if len(ref_strikes) > 0:
            interp_gamma = float(np.interp(k, ref_strikes, ref_gammas))
            interp_iv = float(np.interp(k, ref_strikes, ref_ivs))
        else:
            interp_gamma = 0.0035
            interp_iv = 0.215
            
        rows.append({
            'strike': k,
            'callBid': c['bid'] if c['bid'] > 0 else c_mid - 0.20,
            'callAsk': c['ask'] if c['ask'] > 0 else c_mid + 0.20,
            'callMid': c_mid,
            'callLatest': c['latest'],
            'callOpenInterest': c['oi'],
            'callVolume': c['vol'],
            'callGamma': interp_gamma,
            'callIV': interp_iv,
            
            'putBid': p['bid'] if p['bid'] > 0 else p_mid - 0.20,
            'putAsk': p['ask'] if p['ask'] > 0 else p_mid + 0.20,
            'putMid': p_mid,
            'putLatest': p['latest'],
            'putOpenInterest': p['oi'],
            'putVolume': p['vol'],
            'putGamma': interp_gamma,
            'putIV': interp_iv,
        })
        
    return pd.DataFrame(rows)
