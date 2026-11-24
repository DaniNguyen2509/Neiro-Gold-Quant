import { DurableObject } from "cloudflare:workers";

/**
 * Neiro-Gold-Quant Cloud Feed Relay (Cloudflare Worker + SQLite Durable Object)
 * - Stage A (Day 1, $0): Stateless CORS proxy for CME Gold Futures (GC=F)
 * - Stage B (0s Real-Time, $0): On-demand Pepperstone cTrader Open API (XAUUSDF, Demo read-only)
 *   Strictly raw XAUUSD-F prices with 0.00 artificial basis offset (per owner spec).
 *
 * Official cTrader Open API References:
 * - JSON WebSocket endpoints: wss://demo.ctraderapi.com:5036 | wss://live.ctraderapi.com:5036
 * - Payload IDs (OpenApiModelMessages.proto):
 *   51 Heartbeat, 2100/2101 AppAuth, 2149/2150 AccountList, 2102/2103 AccountAuth,
 *   2114/2115 SymbolsList, 2127/2128 SubscribeSpots, 2131 SpotEvent,
 *   2135 SubscribeLiveTrendbar, 2137/2138 GetTrendbars, 2142 ErrorRes, 2147 TokenInvalidated
 */

const CTRADER_PRICE_SCALE = 100000.0;
const CACHE_TTL_MS = 2500;
const IDLE_DISCONNECT_MS = 5 * 60 * 1000;
const HEARTBEAT_INTERVAL_MS = 20 * 1000;
const TOKEN_REFRESH_MARGIN_MS = 24 * 3600 * 1000;

const TF_CONFIG = {
    "1m": { yahooInterval: "1m", yahooRange: "1d", ctraderPeriod: 1, barSec: 60, lookbackMs: 6 * 3600 * 1000, maxBars: 360 },
    "5m": { yahooInterval: "5m", yahooRange: "5d", ctraderPeriod: 5, barSec: 300, lookbackMs: 24 * 3600 * 1000, maxBars: 288 },
    "15m": { yahooInterval: "15m", yahooRange: "5d", ctraderPeriod: 7, barSec: 900, lookbackMs: 3 * 24 * 3600 * 1000, maxBars: 288 },
    "1h": { yahooInterval: "60m", yahooRange: "1mo", ctraderPeriod: 9, barSec: 3600, lookbackMs: 14 * 24 * 3600 * 1000, maxBars: 336 },
    "1d": { yahooInterval: "1d", yahooRange: "6mo", ctraderPeriod: 12, barSec: 86400, lookbackMs: 180 * 24 * 3600 * 1000, maxBars: 180 },
};

function normalizeTf(tf) {
    const key = String(tf || "1m").trim().toLowerCase();
    return Object.prototype.hasOwnProperty.call(TF_CONFIG, key) ? key : "1m";
}

function corsHeaders(env, originHeader = null) {
    const configured = String((env && env.ALLOWED_ORIGIN) || "*").trim();
    const allowOrigin = configured === "*" ? "*" : (originHeader && configured.split(",").map(s => s.trim()).includes(originHeader) ? originHeader : configured.split(",")[0].trim());
    return {
        "Access-Control-Allow-Origin": allowOrigin || "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Content-Type": "application/json; charset=utf-8",
    };
}

function jsonResponse(data, env, status = 200, originHeader = null) {
    return new Response(JSON.stringify(data), {
        status,
        headers: corsHeaders(env, originHeader),
    });
}

function isCmeGlobexOpenUtc(nowMs = Date.now()) {
    try {
        const parts = new Intl.DateTimeFormat("en-US", {
            timeZone: "America/New_York",
            weekday: "short",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
        }).formatToParts(new Date(nowMs));
        const map = {};
        for (const p of parts) map[p.type] = p.value;
        const wd = map.weekday || "";
        const hh = Number(map.hour || 0) % 24;
        if (wd === "Sat") return false;
        if (wd === "Sun" && hh < 18) return false;
        if (wd === "Fri" && hh >= 17) return false;
        if (hh === 17) return false;
        return true;
    } catch (_) {
        const d = new Date(nowMs);
        const wd = d.getUTCDay();
        return wd !== 6;
    }
}

function decodeCTraderTrendbar(bar, digits = 2, basisOffset = 0.0) {
    if (!bar || bar.low === undefined || bar.low === null) return null;
    const lowRaw = Number(bar.low);
    if (!Number.isFinite(lowRaw)) return null;
    const dOpen = Number(bar.deltaOpen || 0);
    const dHigh = Number(bar.deltaHigh || 0);
    const dClose = bar.deltaClose !== undefined && bar.deltaClose !== null ? Number(bar.deltaClose) : 0;
    const prec = Math.max(0, Math.min(5, Number.isFinite(Number(digits)) ? Number(digits) : 2));
    const factor = Math.pow(10, prec);
    const roundPx = (raw) => Math.round(((raw / CTRADER_PRICE_SCALE) + basisOffset) * factor) / factor;

    const tsSec = bar.utcTimestampInMinutes !== undefined
        ? Number(bar.utcTimestampInMinutes) * 60
        : (bar.timestamp !== undefined ? Math.floor(Number(bar.timestamp) / 1000) : 0);
    if (!tsSec || !Number.isFinite(tsSec)) return null;

    const lowPx = roundPx(lowRaw);
    const openPx = roundPx(lowRaw + dOpen);
    const highPx = Math.max(openPx, lowPx, roundPx(lowRaw + dHigh));
    const closePx = roundPx(lowRaw + dClose);

    return {
        time: tsSec,
        open: openPx,
        high: highPx,
        low: Math.min(lowPx, openPx, closePx),
        close: closePx,
        volume: Math.max(0, Number(bar.volume || 0)),
    };
}

function normalizeYahooChart(yahooJson, tf = "1m") {
    const result = yahooJson && yahooJson.chart && Array.isArray(yahooJson.chart.result)
        ? yahooJson.chart.result[0]
        : null;
    if (!result) return null;

    const normTf = normalizeTf(tf);
    const barSec = (TF_CONFIG[normTf] && TF_CONFIG[normTf].barSec) || 60;
    const timestamps = Array.isArray(result.timestamp) ? result.timestamp : [];
    const quote = result.indicators && Array.isArray(result.indicators.quote) ? result.indicators.quote[0] : {};
    const opens = quote.open || [];
    const highs = quote.high || [];
    const lows = quote.low || [];
    const closes = quote.close || [];
    const vols = quote.volume || [];

    const rawCandles = [];
    for (let i = 0; i < timestamps.length; i++) {
        const t = Number(timestamps[i]);
        const o = Number(opens[i]);
        const h = Number(highs[i]);
        const l = Number(lows[i]);
        const c = Number(closes[i]);
        const v = Number(vols[i] || 0);
        if (!Number.isFinite(t) || !Number.isFinite(o) || !Number.isFinite(h) || !Number.isFinite(l) || !Number.isFinite(c)) continue;
        if (o <= 0 || h <= 0 || l <= 0 || c <= 0) continue;
        rawCandles.push({
            time: Math.floor(t),
            open: Math.round(o * 100) / 100,
            high: Math.round(Math.max(h, o, c) * 100) / 100,
            low: Math.round(Math.min(l, o, c) * 100) / 100,
            close: Math.round(c * 100) / 100,
            volume: Math.max(0, Math.round(v)),
        });
    }

    // Discard Yahoo trailing regularMarketTime snapshot dot (0 volume and flat spread)
    while (
        rawCandles.length > 1 &&
        rawCandles[rawCandles.length - 1].volume <= 0 &&
        (rawCandles[rawCandles.length - 1].high - rawCandles[rawCandles.length - 1].low) < 0.05 &&
        (barSec >= 86400 || (rawCandles[rawCandles.length - 1].time % barSec) !== 0)
    ) {
        rawCandles.pop();
    }

    // Bucket intraday timestamps to barSec so unaligned ticks never spawn duplicate bars
    const candles = [];
    for (let i = 0; i < rawCandles.length; i++) {
        const rc = rawCandles[i];
        const bucketTime = barSec < 86400 ? (rc.time - (rc.time % barSec)) : rc.time;
        if (candles.length > 0 && candles[candles.length - 1].time === bucketTime) {
            const prev = candles[candles.length - 1];
            prev.high = Math.round(Math.max(prev.high, rc.high) * 100) / 100;
            prev.low = Math.round(Math.min(prev.low, rc.low) * 100) / 100;
            prev.close = rc.close;
            prev.volume += rc.volume;
        } else {
            candles.push({ ...rc, time: bucketTime });
        }
    }

    const maxBars = (TF_CONFIG[normTf] && TF_CONFIG[normTf].maxBars) || 360;
    const sliced = candles.slice(-maxBars);
    const metaPrice = Number(result.meta && result.meta.regularMarketPrice);
    const latestPrice = Number.isFinite(metaPrice) && metaPrice > 0
        ? Math.round(metaPrice * 100) / 100
        : (sliced.length ? sliced[sliced.length - 1].close : 0.0);

    if (sliced.length > 0 && latestPrice > 500 && Math.abs(latestPrice - sliced[sliced.length - 1].close) <= 25.0) {
        const last = sliced[sliced.length - 1];
        last.close = latestPrice;
        last.high = Math.round(Math.max(last.high, latestPrice) * 100) / 100;
        last.low = Math.round(Math.min(last.low, latestPrice) * 100) / 100;
    }

    return {
        available: sliced.length > 0 && latestPrice > 0,
        market_open: isCmeGlobexOpenUtc(Date.now()),
        latest_price: latestPrice,
        tf: normTf,
        symbol: "GC=F",
        source: "yahoo_gcf",
        basis_offset: 0.0,
        candles: sliced,
    };
}

async function fetchYahooGcPayload(tf = "1m") {
    const normTf = normalizeTf(tf);
    const cfg = TF_CONFIG[normTf];
    const hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"];
    let lastErr = null;

    for (const host of hosts) {
        const url = `https://${host}/v8/finance/chart/GC%3DF?interval=${cfg.yahooInterval}&range=${cfg.yahooRange}&includePrePost=true`;
        try {
            const resp = await fetch(url, {
                headers: {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
            });
            if (!resp.ok) {
                lastErr = `HTTP ${resp.status}`;
                continue;
            }
            const data = await resp.json();
            const normalized = normalizeYahooChart(data, normTf);
            if (normalized && normalized.available) return normalized;
            lastErr = "Empty chart result";
        } catch (err) {
            lastErr = String(err && err.message ? err.message : err);
        }
    }

    return {
        available: false,
        market_open: isCmeGlobexOpenUtc(Date.now()),
        latest_price: 0.0,
        tf: normTf,
        symbol: "GC=F",
        source: "yahoo_gcf",
        basis_offset: 0.0,
        candles: [],
        error: lastErr || "Yahoo fetch failed",
    };
}

function findMatchingCTraderSymbol(symbols, targetName = "XAUUSDF") {
    const list = Array.isArray(symbols) ? symbols : [];
    const want = String(targetName || "XAUUSDF").toUpperCase().replace(/[^A-Z0-9]/g, "");
    let exact = null;
    let fuzzy = null;
    for (const s of list) {
        if (!s || !s.symbolName || s.symbolId === undefined) continue;
        const norm = String(s.symbolName).toUpperCase().replace(/[^A-Z0-9]/g, "");
        if (norm === want) {
            exact = s;
            break;
        }
        if (!fuzzy && (norm.startsWith(want) || norm.includes("XAUUSDF"))) {
            fuzzy = s;
        }
    }
    return exact || fuzzy;
}

export class CTraderFeedDO extends DurableObject {
    constructor(ctx, env) {
        super(ctx, env);
        this.ctx = ctx;
        this.env = env;
        this.ws = null;
        this.connectPromise = null;
        this.refreshPromise = null;
        this.pendingRpc = new Map();
        this.msgSeq = 0;
        this.symbolInfo = null;
        this.liveSpotPrice = 0.0;
        this.liveSpotTsMs = 0;
        this.lastHeartbeatMs = 0;
        this.lastClientPollMs = 0;
        this.tfCache = new Map();
        this.tokens = null;
        this.lastError = "";
    }

    async loadTokens() {
        if (this.tokens) return this.tokens;
        const stored = await this.ctx.storage.get("tokens");
        if (stored && stored.accessToken) {
            this.tokens = stored;
            return this.tokens;
        }
        const envAccess = String(this.env.CTRADER_ACCESS_TOKEN || "").trim();
        const envRefresh = String(this.env.CTRADER_REFRESH_TOKEN || "").trim();
        const envAccId = String(this.env.CTRADER_ACCOUNT_ID || "").trim();
        if (envAccess || envRefresh) {
            this.tokens = {
                accessToken: envAccess,
                refreshToken: envRefresh,
                expiresAtMs: envAccess ? (Date.now() + 25 * 24 * 3600 * 1000) : 0,
                accountId: envAccId ? Number(envAccId) : 0,
            };
            await this.ctx.storage.put("tokens", this.tokens);
            return this.tokens;
        }
        return null;
    }

    async saveTokens(next) {
        this.tokens = next;
        await this.ctx.storage.put("tokens", next);
    }

    async refreshAccessToken(force = false) {
        if (this.refreshPromise) return this.refreshPromise;
        this.refreshPromise = (async () => {
            const cur = await this.loadTokens();
            const clientId = String(this.env.CTRADER_CLIENT_ID || "").trim();
            const clientSecret = String(this.env.CTRADER_CLIENT_SECRET || "").trim();
            if (!cur || !cur.refreshToken || !clientId || !clientSecret) {
                throw new Error("Missing cTrader refresh token or app secrets");
            }
            if (!force && cur.accessToken && cur.expiresAtMs && (cur.expiresAtMs - Date.now()) > TOKEN_REFRESH_MARGIN_MS) {
                return cur;
            }
            const tokenUrl = new URL("https://openapi.ctrader.com/apps/token");
            tokenUrl.searchParams.set("grant_type", "refresh_token");
            tokenUrl.searchParams.set("refresh_token", cur.refreshToken);
            tokenUrl.searchParams.set("client_id", clientId);
            tokenUrl.searchParams.set("client_secret", clientSecret);

            const resp = await fetch(tokenUrl.toString(), { method: "GET" });
            if (!resp.ok) {
                throw new Error(`cTrader token refresh HTTP ${resp.status}`);
            }
            const data = await resp.json();
            if (!data || !data.accessToken) {
                throw new Error(data && data.description ? data.description : "Invalid refresh response");
            }
            const expiresInSec = Number(data.expiresIn || 2628000);
            const updated = {
                accessToken: String(data.accessToken),
                refreshToken: String(data.refreshToken || cur.refreshToken),
                expiresAtMs: Date.now() + expiresInSec * 1000,
                accountId: Number(cur.accountId || 0),
            };
            await this.saveTokens(updated);
            return updated;
        })().finally(() => {
            this.refreshPromise = null;
        });
        return this.refreshPromise;
    }

    closeUpstream(reason = "reset") {
        for (const [, p] of this.pendingRpc.entries()) {
            clearTimeout(p.timer);
            p.reject(new Error(`Upstream closed (${reason})`));
        }
        this.pendingRpc.clear();
        if (this.ws) {
            try { this.ws.close(1000, reason); } catch (_) { }
            this.ws = null;
        }
        this.symbolInfo = null;
    }

    sendRaw(obj) {
        if (!this.ws) throw new Error("WebSocket not connected");
        this.ws.send(JSON.stringify(obj));
        this.lastHeartbeatMs = Date.now();
    }

    sendRpc(payloadType, payload, expectedResType, timeoutMs = 6000) {
        const clientMsgId = "n_" + (++this.msgSeq);
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this.pendingRpc.delete(clientMsgId);
                reject(new Error(`RPC timeout for payloadType=${payloadType}`));
            }, timeoutMs);
            this.pendingRpc.set(clientMsgId, { expectedResType, resolve, reject, timer });
            try {
                this.sendRaw({ clientMsgId, payloadType, payload });
            } catch (err) {
                clearTimeout(timer);
                this.pendingRpc.delete(clientMsgId);
                reject(err);
            }
        });
    }

    handleSocketMessage(rawData) {
        let msg = null;
        try {
            msg = JSON.parse(typeof rawData === "string" ? rawData : new TextDecoder().decode(rawData));
        } catch (_) {
            return;
        }
        if (!msg) return;

        const pt = Number(msg.payloadType);
        const pl = msg.payload || {};

        if (pt === 51) return; // ProtoHeartbeatEvent

        if (pt === 2147) {
            // PROTO_OA_ACCOUNTS_TOKEN_INVALIDATED_EVENT
            this.closeUpstream("token invalidated");
            this.refreshAccessToken(true).catch((err) => { this.lastError = String(err.message || err); });
            return;
        }

        if (pt === 2131 && this.symbolInfo && Number(pl.symbolId) === Number(this.symbolInfo.symbolId)) {
            // PROTO_OA_SPOT_EVENT: 0.00 artificial basis offset (raw XAUUSD-F)
            const bidRaw = pl.bid !== undefined ? Number(pl.bid) : null;
            const askRaw = pl.ask !== undefined ? Number(pl.ask) : null;
            const spotRaw = bidRaw !== null && askRaw !== null ? ((bidRaw + askRaw) / 2.0) : (bidRaw !== null ? bidRaw : askRaw);
            if (spotRaw !== null && spotRaw > 0) {
                const factor = Math.pow(10, Math.min(5, this.symbolInfo.digits || 2));
                this.liveSpotPrice = Math.round((spotRaw / CTRADER_PRICE_SCALE) * factor) / factor;
                this.liveSpotTsMs = Date.now();
            }
            if (Array.isArray(pl.trendbar) && pl.trendbar.length > 0 && this.tfCache.has("1m")) {
                const cached1m = this.tfCache.get("1m");
                if (cached1m && cached1m.data && Array.isArray(cached1m.data.candles)) {
                    for (const rawBar of pl.trendbar) {
                        const bar = decodeCTraderTrendbar(rawBar, this.symbolInfo.digits || 2, 0.0);
                        if (!bar) continue;
                        const arr = cached1m.data.candles;
                        const idx = arr.findIndex(b => b.time === bar.time);
                        if (idx >= 0) arr[idx] = bar;
                        else if (!arr.length || bar.time > arr[arr.length - 1].time) {
                            arr.push(bar);
                            if (arr.length > 360) arr.shift();
                        }
                    }
                    if (this.liveSpotPrice > 0) cached1m.data.latest_price = this.liveSpotPrice;
                }
            }
            return;
        }

        const id = msg.clientMsgId;
        if (id && this.pendingRpc.has(id)) {
            const waiter = this.pendingRpc.get(id);
            this.pendingRpc.delete(id);
            clearTimeout(waiter.timer);
            if (pt === 2142) {
                const code = pl.errorCode || "OA_ERROR";
                const desc = pl.description || "cTrader Open API error";
                waiter.reject(new Error(`${code}: ${desc}`));
                return;
            }
            if (waiter.expectedResType && pt !== waiter.expectedResType) {
                waiter.reject(new Error(`Unexpected payloadType=${pt}, expected=${waiter.expectedResType}`));
                return;
            }
            waiter.resolve(pl);
        }
    }

    async ensureConnected() {
        if (this.ws && this.symbolInfo && this.ws.readyState === 1) {
            if (Date.now() - this.lastHeartbeatMs > HEARTBEAT_INTERVAL_MS) {
                try { this.sendRaw({ payloadType: 51, payload: {} }); } catch (_) { }
            }
            return;
        }
        if (this.connectPromise) return this.connectPromise;

        this.connectPromise = (async () => {
            this.closeUpstream("reconnect");
            const clientId = String(this.env.CTRADER_CLIENT_ID || "").trim();
            const clientSecret = String(this.env.CTRADER_CLIENT_SECRET || "").trim();
            let tok = await this.loadTokens();
            if (!clientId || !clientSecret || !tok || (!tok.accessToken && !tok.refreshToken)) {
                throw new Error("cTrader credentials not configured");
            }
            if (!tok.accessToken || (tok.expiresAtMs && (tok.expiresAtMs - Date.now()) <= TOKEN_REFRESH_MARGIN_MS)) {
                tok = await this.refreshAccessToken(true);
            }

            const envName = String(this.env.CTRADER_ENV || "demo").trim().toLowerCase();
            const host = envName === "live" ? "live.ctraderapi.com" : "demo.ctraderapi.com";
            const resp = await fetch(`https://${host}:5036`, { headers: { Upgrade: "websocket" } });
            const ws = resp && resp.webSocket;
            if (!ws) throw new Error(`WebSocket upgrade failed on ${host}:5036`);
            ws.accept();
            this.ws = ws;
            ws.addEventListener("message", (evt) => this.handleSocketMessage(evt.data));
            ws.addEventListener("close", () => this.closeUpstream("broker_close"));
            ws.addEventListener("error", () => this.closeUpstream("broker_error"));

            // 1. App Auth (2100 -> 2101)
            await this.sendRpc(2100, { clientId, clientSecret }, 2101, 6000);

            // 2. Account ID discovery if unset (2149 -> 2150)
            let accountId = Number(tok.accountId || this.env.CTRADER_ACCOUNT_ID || 0);
            if (!accountId) {
                const accRes = await this.sendRpc(2149, { accessToken: tok.accessToken }, 2150, 6000);
                const accounts = Array.isArray(accRes.ctidTraderAccount) ? accRes.ctidTraderAccount : [];
                const wantLive = envName === "live";
                const match = accounts.find(a => Boolean(a.isLive) === wantLive) || accounts[0];
                if (!match || !match.ctidTraderAccountId) {
                    throw new Error("No cTrader trading account found for accessToken");
                }
                accountId = Number(match.ctidTraderAccountId);
                await this.saveTokens({ ...tok, accountId });
            }

            // 3. Account Auth (2102 -> 2103), auto-refresh once on expired token
            try {
                await this.sendRpc(2102, { ctidTraderAccountId: accountId, accessToken: tok.accessToken }, 2103, 6000);
            } catch (authErr) {
                if (tok.refreshToken && /TOKEN|INVALID|EXPIRED|AUTH/i.test(String(authErr.message))) {
                    tok = await this.refreshAccessToken(true);
                    await this.sendRpc(2102, { ctidTraderAccountId: accountId, accessToken: tok.accessToken }, 2103, 6000);
                } else {
                    throw authErr;
                }
            }

            // 4. Resolve Pepperstone Gold Forward symbol (XAUUSDF) via 2114 -> 2115
            const targetSym = String(this.env.CTRADER_SYMBOL || "XAUUSDF").trim();
            const symRes = await this.sendRpc(2114, { ctidTraderAccountId: accountId, includeArchivedSymbols: false }, 2115, 7000);
            const found = findMatchingCTraderSymbol(symRes.symbol, targetSym);
            if (!found) {
                throw new Error(`Symbol ${targetSym} not found on broker account ${accountId}`);
            }
            this.symbolInfo = {
                symbolId: Number(found.symbolId),
                symbolName: String(found.symbolName),
                digits: Number(found.digits !== undefined ? found.digits : 2),
                accountId,
            };

            // 5. Subscribe live spot quotes (2127) and M1 live trendbars (2135)
            await this.sendRpc(2127, { ctidTraderAccountId: accountId, symbolId: [this.symbolInfo.symbolId], subscribeToSpotTimestamp: true }, 2128, 5000);
            try {
                await this.sendRpc(2135, { ctidTraderAccountId: accountId, symbolId: this.symbolInfo.symbolId, period: 1 }, 2136, 5000);
            } catch (_) {
                // Spot quotes + GetTrendbars already keep prices real-time even if live trendbar sub is unsupported
            }
            await this.ctx.storage.setAlarm(Date.now() + IDLE_DISCONNECT_MS);
            this.lastError = "";
        })().finally(() => {
            this.connectPromise = null;
        });

        return this.connectPromise;
    }

    async alarm() {
        if (Date.now() - this.lastClientPollMs >= IDLE_DISCONNECT_MS) {
            this.closeUpstream("idle_sleep");
            return;
        }
        if (this.ws && this.ws.readyState === 1) {
            await this.ctx.storage.setAlarm(Date.now() + IDLE_DISCONNECT_MS);
        }
    }

    async handleExchangeCode(code, redirectUri, pin = "") {
        const clientId = String(this.env.CTRADER_CLIENT_ID || "").trim();
        const clientSecret = String(this.env.CTRADER_CLIENT_SECRET || "").trim();
        if (!clientId || !clientSecret) {
            return { ok: false, error: "CTRADER_CLIENT_ID / CTRADER_CLIENT_SECRET not configured in Worker secrets" };
        }
        const existing = await this.loadTokens();
        const validPin = Boolean(this.env.SETUP_PIN && pin && pin === String(this.env.SETUP_PIN));
        if (existing && existing.refreshToken && !validPin) {
            return { ok: false, error: "Token already initialized; delete DO state or pass valid ?state=<SETUP_PIN> to re-bind" };
        }
        const u = new URL("https://openapi.ctrader.com/apps/token");
        u.searchParams.set("grant_type", "authorization_code");
        u.searchParams.set("code", code);
        u.searchParams.set("redirect_uri", redirectUri);
        u.searchParams.set("client_id", clientId);
        u.searchParams.set("client_secret", clientSecret);

        const resp = await fetch(u.toString(), { method: "GET" });
        const data = await resp.json();
        if (!resp.ok || !data || !data.accessToken) {
            return { ok: false, error: (data && data.description) || `HTTP ${resp.status}` };
        }
        const expiresInSec = Number(data.expiresIn || 2628000);
        await this.saveTokens({
            accessToken: String(data.accessToken),
            refreshToken: String(data.refreshToken || ""),
            expiresAtMs: Date.now() + expiresInSec * 1000,
            accountId: Number(this.env.CTRADER_ACCOUNT_ID || 0),
        });
        this.tfCache.clear();
        this.lastError = "";
        return { ok: true, message: "Authorized cTrader read-only token stored encrypted inside DO storage." };
    }

    async fetch(request) {
        const url = new URL(request.url);
        const origin = request.headers.get("Origin");

        if (url.pathname === "/internal/callback") {
            const code = url.searchParams.get("code") || "";
            const redirectUri = url.searchParams.get("redirect_uri") || "";
            const pin = url.searchParams.get("pin") || "";
            if (!code) return jsonResponse({ ok: false, error: "Missing code" }, this.env, 400, origin);
            const res = await this.handleExchangeCode(code, redirectUri, pin);
            return jsonResponse(res, this.env, res.ok ? 200 : 400, origin);
        }

        if (url.pathname === "/health") {
            const tok = await this.loadTokens();
            return jsonResponse({
                ok: true,
                feed_mode: String(this.env.FEED_MODE || "auto"),
                ctrader_env: String(this.env.CTRADER_ENV || "demo"),
                ctrader_configured: Boolean(this.env.CTRADER_CLIENT_ID && this.env.CTRADER_CLIENT_SECRET && tok && (tok.accessToken || tok.refreshToken)),
                ws_connected: Boolean(this.ws && this.ws.readyState === 1),
                symbol: this.symbolInfo ? this.symbolInfo.symbolName : String(this.env.CTRADER_SYMBOL || "XAUUSDF"),
                live_spot_price: this.liveSpotPrice || 0.0,
                basis_offset: 0.0,
                last_error: this.lastError || null,
            }, this.env, 200, origin);
        }

        this.lastClientPollMs = Date.now();
        const tf = normalizeTf(url.searchParams.get("tf"));
        const feedMode = String((this.env && this.env.FEED_MODE) || "auto").trim().toLowerCase();
        const targetSym = (this.symbolInfo && this.symbolInfo.symbolName) || String((this.env && this.env.CTRADER_SYMBOL) || "XAUUSDF");
        const targetSource = `ctrader_${String((this.env && this.env.CTRADER_ENV) || "demo").toLowerCase()}_xauusdf`;
        const tok = await this.loadTokens();
        if (!tok || (!tok.accessToken && !tok.refreshToken)) {
            if (feedMode === "ctrader_only") {
                return jsonResponse({
                    available: false,
                    market_open: isCmeGlobexOpenUtc(Date.now()),
                    latest_price: 0.0,
                    tf,
                    symbol: targetSym,
                    source: targetSource,
                    basis_offset: 0.0,
                    candles: [],
                    error: "cTrader OAuth token not authorized yet (ctrader_only mode)",
                }, this.env, 503, origin);
            }
            return jsonResponse(await fetchYahooGcPayload(tf), this.env, 200, origin);
        }
        const cached = this.tfCache.get(tf);
        if (cached && (Date.now() - cached.ts) < CACHE_TTL_MS && cached.data && cached.data.available) {
            if (this.liveSpotPrice > 0 && cached.data.candles.length > 0) {
                const clone = { ...cached.data, candles: cached.data.candles.slice() };
                const last = { ...clone.candles[clone.candles.length - 1] };
                last.close = this.liveSpotPrice;
                last.high = Math.max(last.high, this.liveSpotPrice);
                last.low = Math.min(last.low, this.liveSpotPrice);
                clone.candles[clone.candles.length - 1] = last;
                clone.latest_price = this.liveSpotPrice;
                return jsonResponse(clone, this.env, 200, origin);
            }
            return jsonResponse(cached.data, this.env, 200, origin);
        }

        try {
            await this.ensureConnected();
            const cfg = TF_CONFIG[tf];
            const toMs = Date.now();
            const fromMs = toMs - cfg.lookbackMs;
            const maxBars = cfg.maxBars || 360;
            const res = await this.sendRpc(2137, {
                ctidTraderAccountId: this.symbolInfo.accountId,
                symbolId: this.symbolInfo.symbolId,
                period: cfg.ctraderPeriod,
                fromTimestamp: fromMs,
                toTimestamp: toMs,
                count: maxBars,
            }, 2138, 7000);

            const candles = (Array.isArray(res.trendbar) ? res.trendbar : [])
                .map(b => decodeCTraderTrendbar(b, this.symbolInfo.digits, 0.0))
                .filter(Boolean)
                .sort((a, b) => a.time - b.time)
                .slice(-maxBars);

            let latestPrice = candles.length ? candles[candles.length - 1].close : 0.0;
            if (this.liveSpotPrice > 0) {
                latestPrice = this.liveSpotPrice;
                if (candles.length > 0) {
                    const last = { ...candles[candles.length - 1] };
                    last.close = latestPrice;
                    last.high = Math.max(last.high, latestPrice);
                    last.low = Math.min(last.low, latestPrice);
                    candles[candles.length - 1] = last;
                }
            }

            const payload = {
                available: candles.length > 0 && latestPrice > 0,
                market_open: isCmeGlobexOpenUtc(Date.now()),
                latest_price: latestPrice,
                tf,
                symbol: this.symbolInfo.symbolName,
                source: `ctrader_${String(this.env.CTRADER_ENV || "demo").toLowerCase()}_xauusdf`,
                basis_offset: 0.0,
                candles,
            };
            this.tfCache.set(tf, { ts: Date.now(), data: payload });
            await this.ctx.storage.setAlarm(Date.now() + IDLE_DISCONNECT_MS);
            return jsonResponse(payload, this.env, 200, origin);
        } catch (err) {
            this.lastError = String(err && err.message ? err.message : err);
            // Zero-Mixing Guard: Once OAuth token exists (Pepperstone mode active),
            // never fall back to -10m delayed Yahoo candles on a transient WS hiccup.
            return jsonResponse({
                available: false,
                market_open: isCmeGlobexOpenUtc(Date.now()),
                latest_price: this.liveSpotPrice || 0.0,
                tf,
                symbol: targetSym,
                source: targetSource,
                basis_offset: 0.0,
                candles: [],
                error: this.lastError,
            }, this.env, 503, origin);
        }
    }
}

export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        const origin = request.headers.get("Origin");

        if (request.method === "OPTIONS") {
            return new Response(null, { status: 204, headers: corsHeaders(env, origin) });
        }

        const feedMode = String((env && env.FEED_MODE) || "auto").trim().toLowerCase();
        const hasCTraderAppSecrets = Boolean(
            env && env.FEED_DO && env.CTRADER_CLIENT_ID && env.CTRADER_CLIENT_SECRET
        );

        if (url.pathname === "/auth/url") {
            const clientId = String((env && env.CTRADER_CLIENT_ID) || "").trim();
            if (!clientId) {
                return jsonResponse({ ok: false, error: "Set CTRADER_CLIENT_ID in Cloudflare Worker Secrets first" }, env, 400, origin);
            }
            const authUrl = new URL("https://id.ctrader.com/my/settings/openapi/grantingaccess/");
            authUrl.searchParams.set("client_id", clientId);
            authUrl.searchParams.set("redirect_uri", `${url.origin}/callback`);
            authUrl.searchParams.set("scope", "accounts");
            authUrl.searchParams.set("product", "web");
            return jsonResponse({
                ok: true,
                scope: "accounts",
                redirect_uri: `${url.origin}/callback`,
                authorize_url: authUrl.toString(),
            }, env, 200, origin);
        }

        if (url.pathname === "/callback") {
            if (!env || !env.FEED_DO) {
                return jsonResponse({ ok: false, error: "Durable Object FEED_DO binding required for OAuth storage" }, env, 500, origin);
            }
            const code = url.searchParams.get("code") || "";
            if (!code) return jsonResponse({ ok: false, error: "Missing OAuth ?code= parameter" }, env, 400, origin);
            const stub = env.FEED_DO.get(env.FEED_DO.idFromName("gold-feed"));
            const forwardUrl = new URL(request.url);
            forwardUrl.pathname = "/internal/callback";
            forwardUrl.searchParams.set("redirect_uri", `${url.origin}/callback`);
            forwardUrl.searchParams.set("pin", url.searchParams.get("state") || "");
            return stub.fetch(new Request(forwardUrl.toString(), request));
        }

        if (url.pathname === "/health") {
            if (env && env.FEED_DO) {
                const stub = env.FEED_DO.get(env.FEED_DO.idFromName("gold-feed"));
                return stub.fetch(request);
            }
            return jsonResponse({
                ok: true,
                feed_mode: feedMode,
                ctrader_configured: false,
                symbol: "GC=F",
                basis_offset: 0.0,
            }, env, 200, origin);
        }

        if (url.pathname === "/api/trigger_sync") {
            const authHeader = request.headers.get("Authorization") || "";
            const token = String(
                (env && env.GITHUB_DISPATCH_TOKEN) || (authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "")
            ).trim();

            if (!token) {
                return jsonResponse({
                    ok: false,
                    error: "Missing GITHUB_DISPATCH_TOKEN secret or Bearer token header.",
                    hint: "Add GITHUB_DISPATCH_TOKEN to Cloudflare Worker Secrets (or enter your GitHub PAT in Terminal UI prompt).",
                }, env, 401, origin);
            }

            const repo = String((env && env.GITHUB_REPO) || "DaniNguyen2509/Neiro-Gold-Quant").trim();
            const ghUrl = `https://api.github.com/repos/${repo}/dispatches`;

            try {
                const ghResp = await fetch(ghUrl, {
                    method: "POST",
                    headers: {
                        "User-Agent": "Neiro-Gold-Feed-Worker/2.0",
                        "Accept": "application/vnd.github+json",
                        "Authorization": `Bearer ${token}`,
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        event_type: "sync-options",
                        client_payload: {
                            triggered_at: new Date().toISOString(),
                            source: "mobile_hud_remote_sync",
                        },
                    }),
                });

                if (ghResp.status === 204 || ghResp.ok) {
                    return jsonResponse({
                        ok: true,
                        message: "CME Options scrape triggered successfully on GitHub Actions! Running Playwright on cloud...",
                        status_code: ghResp.status,
                        repo,
                        queued_at: new Date().toISOString(),
                        eta_seconds: 60,
                    }, env, 200, origin);
                }

                const errBody = await ghResp.text();
                return jsonResponse({
                    ok: false,
                    error: `GitHub API error (${ghResp.status}): ${errBody}`,
                }, env, 502, origin);
            } catch (err) {
                return jsonResponse({
                    ok: false,
                    error: `Fetch error calling GitHub API: ${err.message}`,
                }, env, 500, origin);
            }
        }

        if (url.pathname === "/api/yahoo_gc" || url.pathname === "/") {
            const tf = normalizeTf(url.searchParams.get("tf"));
            if (feedMode === "ctrader_only" && !hasCTraderAppSecrets) {
                return jsonResponse({
                    available: false,
                    market_open: isCmeGlobexOpenUtc(Date.now()),
                    latest_price: 0.0,
                    tf,
                    symbol: String((env && env.CTRADER_SYMBOL) || "XAUUSDF"),
                    source: `ctrader_${String((env && env.CTRADER_ENV) || "demo").toLowerCase()}_xauusdf`,
                    basis_offset: 0.0,
                    candles: [],
                    error: "cTrader secrets or FEED_DO binding missing in ctrader_only mode",
                }, env, 503, origin);
            }
            if (feedMode !== "yahoo" && hasCTraderAppSecrets) {
                const stub = env.FEED_DO.get(env.FEED_DO.idFromName("gold-feed"));
                return stub.fetch(request);
            }
            const yahooPayload = await fetchYahooGcPayload(tf);
            return jsonResponse(yahooPayload, env, 200, origin);
        }

        return jsonResponse({ error: "Not found" }, env, 404, origin);
    },
};

export {
    decodeCTraderTrendbar,
    findMatchingCTraderSymbol,
    isCmeGlobexOpenUtc,
    normalizeTf,
    normalizeYahooChart,
};
