import os
import json
import threading
import traceback
import time
import random
import string
from datetime import datetime
from collections import deque
from flask import Flask, request, render_template_string, redirect, url_for, jsonify, send_file

app = Flask(__name__)

# ==================== 全局数据结构 ====================
MAX_HISTORY = 50

# 分类别存储，避免互相污染
history_status = deque(maxlen=MAX_HISTORY)     # /mt4/status
history_positions = deque(maxlen=MAX_HISTORY)  # /mt4/positions
history_report = deque(maxlen=MAX_HISTORY)     # /mt4/report
history_poll = deque(maxlen=MAX_HISTORY)       # /mt4/commands 轮询请求（account/max）
history_echo = deque(maxlen=MAX_HISTORY)       # /web/api/echo

history_lock = threading.RLock()

commands = []
commands_lock = threading.RLock()
cmd_counter = 0

paused = False
pause_lock = threading.RLock()

def generate_unique_cmd_id():
    """生成全局唯一且单调递增的命令 ID"""
    global cmd_counter
    ms = int(time.time() * 1000)
    with commands_lock:
        cmd_counter += 1
        return f"{ms}_{cmd_counter}"

# ==================== 产品规则表 ====================
PRODUCT_SPECS = {
    # 1. 贵金属 / 原油
    "XAGUSD": {"size": 5000, "lev": 500, "currency": "USD", "type": "metal"},
    "XAUUSD": {"size": 100, "lev": 500, "currency": "USD", "type": "metal"},
    "UKOUSD": {"size": 1000, "lev": 500, "currency": "USD", "type": "commodity"},
    "USOUSD": {"size": 1000, "lev": 500, "currency": "USD", "type": "commodity"},
    
    # 2. 指数
    "U30USD": {"size": 10, "lev": 100, "currency": "USD", "type": "index"},
    "NASUSD": {"size": 10, "lev": 100, "currency": "USD", "type": "index"},
    "SPXUSD": {"size": 100, "lev": 100, "currency": "USD", "type": "index"},
    "100GBP": {"size": 10, "lev": 100, "currency": "GBP", "type": "index"},
    "D30EUR": {"size": 10, "lev": 100, "currency": "EUR", "type": "index"},
    "E50EUR": {"size": 10, "lev": 100, "currency": "EUR", "type": "index"},
    "H33HKD": {"size": 100, "lev": 100, "currency": "HKD", "type": "index"},
    
    # 3. 虚拟货币
    "BTCUSD": {"size": 1, "lev": 500, "currency": "USD", "type": "crypto"},
    "BCHUSD": {"size": 100, "lev": 500, "currency": "USD", "type": "crypto"},
    "RPLUSD": {"size": 10000, "lev": 500, "currency": "USD", "type": "crypto"},
    "LTCUSD": {"size": 100, "lev": 500, "currency": "USD", "type": "crypto"},
    "ETHUSD": {"size": 10, "lev": 500, "currency": "USD", "type": "crypto"},
    "XMRUSD": {"size": 100, "lev": 500, "currency": "USD", "type": "crypto"},
    "BNBUSD": {"size": 100, "lev": 500, "currency": "USD", "type": "crypto"},
    "SOLUSD": {"size": 100, "lev": 500, "currency": "USD", "type": "crypto"},
    "XSIUSD": {"size": 1000, "lev": 500, "currency": "USD", "type": "crypto"},
    "DOGUSD": {"size": 100000, "lev": 500, "currency": "USD", "type": "crypto"},
    "ADAUSD": {"size": 10000, "lev": 500, "currency": "USD", "type": "crypto"},
    "AVEUSD": {"size": 100, "lev": 500, "currency": "USD", "type": "crypto"},
    "DSHUSD": {"size": 1000, "lev": 500, "currency": "USD", "type": "crypto"},
}

# 外汇品种
PRODUCT_SPECS.update({
    "USDCHF":{"size":100000,"lev":500,"currency":"CHF","type":"forex"},
    "GBPUSD":{"size":100000,"lev":500,"currency":"USD","type":"forex"},
    "EURUSD":{"size":100000,"lev":500,"currency":"USD","type":"forex"},
    "USDJPY":{"size":100000,"lev":500,"currency":"JPY","type":"forex"},
    "USDCAD":{"size":100000,"lev":500,"currency":"CAD","type":"forex"},
    "AUDUSD":{"size":100000,"lev":500,"currency":"USD","type":"forex"},
    "EURGBP":{"size":100000,"lev":500,"currency":"GBP","type":"forex"},
    "EURAUD":{"size":100000,"lev":500,"currency":"AUD","type":"forex"},
    "EURCHF":{"size":100000,"lev":500,"currency":"CHF","type":"forex"},
    "EURJPY":{"size":100000,"lev":500,"currency":"JPY","type":"forex"},
    "GBPCHF":{"size":100000,"lev":500,"currency":"CHF","type":"forex"},
    "CADJPY":{"size":100000,"lev":500,"currency":"JPY","type":"forex"},
    "GBPJPY":{"size":100000,"lev":500,"currency":"JPY","type":"forex"},
    "AUDNZD":{"size":100000,"lev":500,"currency":"NZD","type":"forex"},
    "AUDCAD":{"size":100000,"lev":500,"currency":"CAD","type":"forex"},
    "AUDCHF":{"size":100000,"lev":500,"currency":"CHF","type":"forex"},
    "AUDJPY":{"size":100000,"lev":500,"currency":"JPY","type":"forex"},
    "CHFJPY":{"size":100000,"lev":500,"currency":"JPY","type":"forex"},
    "EURNZD":{"size":100000,"lev":500,"currency":"NZD","type":"forex"},
    "EURCAD":{"size":100000,"lev":500,"currency":"CAD","type":"forex"},
    "CADCHF":{"size":100000,"lev":500,"currency":"CHF","type":"forex"},
    "NZDJPY":{"size":100000,"lev":500,"currency":"JPY","type":"forex"},
    "NZDUSD":{"size":100000,"lev":500,"currency":"USD","type":"forex"},
    "GBPAUD":{"size":100000,"lev":500,"currency":"AUD","type":"forex"},
    "GBPCAD":{"size":100000,"lev":500,"currency":"CAD","type":"forex"},
    "GBPNZD":{"size":100000,"lev":500,"currency":"NZD","type":"forex"},
    "NZDCAD":{"size":100000,"lev":500,"currency":"CAD","type":"forex"},
    "NZDCHF":{"size":100000,"lev":500,"currency":"CHF","type":"forex"},
    "USDSGD":{"size":100000,"lev":500,"currency":"SGD","type":"forex"},
    "USDHKD":{"size":100000,"lev":500,"currency":"HKD","type":"forex"},
    "USDCNH":{"size":100000,"lev":500,"currency":"CNH","type":"forex"},
    "LNKUSD":{"size":1000,"lev":500,"currency":"USD","type":"crypto"},
    "AAPL":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "AMZN":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "BABA":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "GOOGL":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "META":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "MSFT":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "NFLX":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "NVDA":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "TSLA":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "ABBV":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "ABNB":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "ABT":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "ADBE":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "AMD":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "AVGO":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "C":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "CRM":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "DIS":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "GS":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "INTC":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "JNJ":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "MA":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "MCD":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "KO":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "MMM":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "NIO":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "PLTR":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "SHOP":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "TSM":{"size":100,"lev":10,"currency":"USD","type":"stock"},
    "V":{"size":100,"lev":10,"currency":"USD","type":"stock"},
})

DEFAULT_FOREX_SPEC = {"size": 100000, "lev": 500, "type": "forex"}
DEFAULT_STOCK_SPEC = {"size": 100, "lev": 10, "currency": "USD", "type": "stock"}

# ==================== 品种名归一化 ====================
KNOWN_SYMBOLS = set(PRODUCT_SPECS.keys())

def normalize_symbol(raw_symbol: str) -> str:
    if not raw_symbol:
        return ""
    s = raw_symbol.strip().upper()
    if s in KNOWN_SYMBOLS:
        return s
    for trim in range(1, 5):
        candidate = s[:-trim] if len(s) > trim else ""
        if candidate and candidate in KNOWN_SYMBOLS:
            return candidate
    if '.' in s:
        candidate = s.split('.')[0]
        if candidate in KNOWN_SYMBOLS:
            return candidate
    if '_' in s:
        candidate = s.split('_')[0]
        if candidate in KNOWN_SYMBOLS:
            return candidate
    return s

# ==================== 报价缓存 ====================
latest_quote_cache = {}
quote_cache_lock   = threading.Lock()

def _to_float(v):
    if v is None: return None
    try:    return float(v)
    except: return None

def _bid_ask_from_dict(d):
    if not isinstance(d, dict): return None, None
    for bk, ak in (("bid","ask"),("Bid","Ask"),("BID","ASK")):
        b, a = _to_float(d.get(bk)), _to_float(d.get(ak))
        if b is not None and a is not None:
            return b, a
    return None, None

def _message_to_quote_dict(p):
    m = p.get("message")
    if m is None: return None
    if isinstance(m, dict): return m
    if isinstance(m, str) and m.strip():
        try:
            o = json.loads(m)
            return o if isinstance(o, dict) else None
        except: return None
    return None

def cache_tick_quote(raw_symbol, bid, ask, spread=None, ts=None):
    norm = normalize_symbol(raw_symbol or "")
    if not norm: return
    b, a = _to_float(bid), _to_float(ask)
    if b is None or a is None: return
    with quote_cache_lock:
        latest_quote_cache[norm] = {
            "bid": b, "ask": a, "symbol": norm,
            "spread": spread, "ts": ts,
            "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

def ingest_quote_from_parsed(p):
    if not isinstance(p, dict): return
    rs = p.get("symbol") or p.get("Symbol") or ""
    b, a = _bid_ask_from_dict(p)
    qd = None
    if b is None or a is None:
        qd = _message_to_quote_dict(p)
        if qd: b, a = _bid_ask_from_dict(qd)
    if b is None or a is None: return
    sp = p.get("spread")
    if sp is None and qd: sp = qd.get("spread")
    ts = p.get("ts") or p.get("time") or p.get("Time")
    cache_tick_quote(rs, b, a, spread=sp, ts=ts)

# ==================== K线数据结构 ====================
KLINE_MAX  = {"5min": 300, "10min": 250, "1hour": 200}
kline_data  = {}
kline_locks = {}

def _get_kline_lock(symbol):
    if symbol not in kline_locks:
        kline_locks[symbol] = threading.Lock()
    return kline_locks[symbol]

def _floor_ts(ts_ms, tf):
    step = {"5min": 5*60*1000, "10min": 10*60*1000, "1hour": 60*60*1000}.get(tf, 60*1000)
    return (ts_ms // step) * step

def update_kline(raw_symbol, bid, ask, tick_ts_ms):
    mid  = (float(bid) + float(ask)) / 2.0
    norm = normalize_symbol(raw_symbol)
    with _get_kline_lock(norm):
        if norm not in kline_data:
            kline_data[norm] = {tf: [] for tf in KLINE_MAX}
        for tf in KLINE_MAX:
            bar_ts = _floor_ts(tick_ts_ms, tf)
            bars   = kline_data[norm][tf]
            if bars and bars[-1][0] == bar_ts:
                bar    = bars[-1]
                bar[2] = max(bar[2], mid)
                bar[3] = min(bar[3], mid)
                bar[4] = mid
            else:
                bars.append([bar_ts, mid, mid, mid, mid])
                if len(bars) > KLINE_MAX[tf]:
                    bars[:] = bars[-KLINE_MAX[tf]:]

# ==================== 命令过期清理 ====================
def cleanup_expired_commands():
    now = int(time.time())
    with commands_lock:
        expired = [c for c in commands if now - c.get("created_at", 0) >= c.get("ttl_sec", 600)]
        commands[:] = [c for c in commands if now - c.get("created_at", 0) < c.get("ttl_sec", 600)]
        if expired:
            print(f"[CLEANUP] 清理了 {len(expired)} 条过期命令")
            with history_lock:
                for cmd in expired:
                    record = {
                        "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "ip": "127.0.0.1",
                        "method": "INTERNAL",
                        "path": "cleanup",
                        "category": "report",
                        "headers": {},
                        "body_raw": "{}",
                        "parsed": {
                            "cmd_id": cmd.get("id"),
                            "ok": False,
                            "ticket": 0,
                            "error": "ORDER_EXPIRED",
                            "message": f"订单超时未执行 (TTL {cmd.get('ttl_sec', 600)}s)",
                            "exec_ms": 0,
                            "desc": "ORDER_EXPIRED"
                        }
                    }
                    history_report.appendleft(record)

def cleanup_scheduler():
    while True:
        time.sleep(5)
        cleanup_expired_commands()

cleanup_thread = threading.Thread(target=cleanup_scheduler, daemon=True)
cleanup_thread.start()

# ==================== 时间限制 ====================
def is_restricted_time():
    return False

# ==================== 工具函数 ====================
def generate_nonce():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def norm_str(x):
    if x is None:
        return ""
    return str(x).strip()

def norm_side(x):
    s = norm_str(x).lower()
    if s in ("buy", "sell"):
        return s
    if s in ("b", "long"):
        return "buy"
    if s in ("s", "short"):
        return "sell"
    return ""

def norm_symbol(x):
    s = norm_str(x).strip().upper()
    return s

def norm_volume(x):
    try:
        v = float(x)
        return v if v > 0 else 0
    except (ValueError, TypeError):
        return 0

def get_client_ip():
    return request.headers.get('X-Real-Ip') or request.headers.get('X-Forwarded-For', request.remote_addr)

def try_parse_json(raw_body: str):
    cleaned = (raw_body or "").strip()
    if not cleaned:
        return None, None, None, None

    parsed_json = None
    parse_error = None
    parse_error_detail = None
    remaining_data = None

    try:
        decoder = json.JSONDecoder()
        parsed_json, idx = decoder.raw_decode(cleaned)
        remaining = cleaned[idx:].strip()
        if remaining:
            remaining_data = remaining[:200]
    except json.JSONDecodeError as e:
        parse_error = str(e)
        parse_error_detail = traceback.format_exc()
        print(f"[ERR] JSON解析错误: {e}")
    except Exception as e:
        parse_error = f"未知异常: {str(e)}"
        parse_error_detail = traceback.format_exc()

    return parsed_json, parse_error, parse_error_detail, remaining_data

def detect_category(path: str, parsed_json: dict):
    if path.endswith("/web/api/mt4/status"):
        return "status"
    if path.endswith("/web/api/mt4/positions"):
        return "positions"
    if path.endswith("/web/api/mt4/report"):
        return "report"
    if path.endswith("/web/api/echo"):
        return "echo"
    if path.endswith("/web/api/mt4/commands"):
        return "poll"
    return "other"

def store_mt4_data(raw_body, client_ip, headers_dict):
    parsed_json, parse_error, parse_error_detail, remaining_data = try_parse_json(raw_body)
    category = detect_category(request.path, parsed_json if isinstance(parsed_json, dict) else None)

    record = {
        "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": client_ip,
        "method": request.method,
        "path": request.path,
        "category": category,
        "headers": headers_dict,
        "body_raw": raw_body,
        "parsed": parsed_json,
        "parse_error": parse_error,
        "parse_error_detail": parse_error_detail,
        "remaining_data": remaining_data,
        "account": parsed_json.get("account") if isinstance(parsed_json, dict) else None,
        "server": parsed_json.get("server") if isinstance(parsed_json, dict) else None,
        "balance": parsed_json.get("balance") if isinstance(parsed_json, dict) else None,
        "equity": parsed_json.get("equity") if isinstance(parsed_json, dict) else None,
        "floating_pnl": parsed_json.get("floating_pnl") if isinstance(parsed_json, dict) else None,
        "leverage_used": parsed_json.get("leverage_used") if isinstance(parsed_json, dict) else None,
        "risk_flags": parsed_json.get("risk_flags") if isinstance(parsed_json, dict) else None,
        "exposure_notional": parsed_json.get("exposure_notional") if isinstance(parsed_json, dict) else None,
        "positions": parsed_json.get("positions") if isinstance(parsed_json, dict) else None,
    }

    if isinstance(parsed_json, dict) and category in ("report", "other"):
        ingest_quote_from_parsed(parsed_json)

    with history_lock:
        if category == "status":
            history_status.appendleft(record)
        elif category == "positions":
            history_positions.appendleft(record)
        elif category == "report":
            history_report.appendleft(record)
            if record.get("parsed"):
                parsed = record["parsed"]
                desc = parsed.get("desc", "")
                cmd_id_str = str(parsed.get("cmd_id", ""))
                if desc != "QUOTE_DATA" and record.get("method") != "INTERNAL" and parsed.get("cmd_id") and not cmd_id_str.startswith("q_"):
                    msg_extra = {}
                    try:
                        raw_msg = parsed.get("message", "")
                        if isinstance(raw_msg, str) and raw_msg.startswith("{"):
                            msg_extra = json.loads(raw_msg)
                    except Exception:
                        pass
                    def _pick(*keys):
                        for k in keys:
                            v = parsed.get(k)
                            if v is not None: return v
                            v = msg_extra.get(k)
                            if v is not None: return v
                        return None
                    trade_record = {
                        "received_at": record.get("received_at"),
                        "cmd_id":      parsed.get("cmd_id"),
                        "ok":          parsed.get("ok"),
                        "ticket":      _pick("ticket"),
                        "error":       _pick("error"),
                        "message":     parsed.get("message"),
                        "exec_ms":     _pick("exec_ms"),
                        "symbol":      _pick("symbol"),
                        "side":        _pick("side", "type", "action"),
                        "volume":      _pick("volume", "lots"),
                        "open_price":  _pick("open_price", "open"),
                        "close_price": _pick("close_price", "price", "close"),
                        "open_time":   _pick("open_time"),
                        "profit":      _pick("profit", "pnl"),
                        "desc":        parsed.get("desc", ""),
                    }
                    save_history_trade(trade_record)

                if desc in ("SPREAD_REJECT", "SPREAD_OK", "SPREAD_EXCEED_ON_FILL"):
                    print(f"[SPREAD_LOG] {parsed.get('code')} {desc} "
                          f"account={parsed.get('account')} "
                          f"spread={parsed.get('spread')} "
                          f"threshold={parsed.get('threshold')} "
                          f"cmd_id={parsed.get('cmd_id')}")
        elif category == "poll":
            history_poll.appendleft(record)
        elif category == "echo":
            history_echo.appendleft(record)

    return parsed_json, record

def safe_num(x):
    return isinstance(x, (int, float))

# ==================== 风控逻辑 ====================
risk_state = {
    "is_fused": False,
    "cooldown_until": 0,
    "consecutive_losses": 0,
    "last_reset_day": None,
    "locked_tickets": set()
}
risk_lock = threading.RLock()

def get_utc8_date_str():
    return datetime.utcfromtimestamp(time.time() + 8*3600).strftime("%Y-%m-%d")

def check_risk_status(account, current_equity, day_start_equity):
    global risk_state
    now = int(time.time())
    today_str = get_utc8_date_str()
    
    with risk_lock:
        if risk_state["last_reset_day"] != today_str:
            risk_state["is_fused"] = False
            risk_state["consecutive_losses"] = 0
            risk_state["cooldown_until"] = 0
            risk_state["last_reset_day"] = today_str
            print(f"[RISK] New day {today_str}, reset risk state.")

        if risk_state["is_fused"]:
            return False, "触发熔断机制，今日交易已停止", "fused"

        if now < risk_state["cooldown_until"]:
            remaining = int((risk_state["cooldown_until"] - now) / 60)
            return False, f"处于冷静期，还需等待 {remaining} 分钟", "cooldown"

        if day_start_equity > 0:
            daily_pnl_pct = (current_equity - day_start_equity) / day_start_equity
            if daily_pnl_pct < -0.09:
                risk_state["is_fused"] = True
                print(f"[RISK] Daily loss {daily_pnl_pct*100:.2f}% > 9%, FUSED.")
                return False, "日内亏损超限，触发熔断", "fused"

        if is_restricted_time():
             return False, "交易已暂停 (系统维护时段)", "restricted_time"

    return True, "交易正常", "normal"

def update_risk_after_trade(trade_profit, open_price, close_price, side):
    global risk_state
    with risk_lock:
        if trade_profit < 0:
            risk_state["consecutive_losses"] += 1
            print(f"[RISK] Loss detected. Consecutive: {risk_state['consecutive_losses']}")
            if risk_state["consecutive_losses"] >= 3:
                risk_state["is_fused"] = True
                print("[RISK] Consecutive losses >= 3, FUSED.")
            elif risk_state["consecutive_losses"] == 2:
                risk_state["cooldown_until"] = int(time.time()) + 3600
                print("[RISK] Consecutive losses == 2, Cooldown 1h.")
        else:
            if trade_profit > 0:
                risk_state["consecutive_losses"] = 0

# ==================== 数据持久化 ====================
DAILY_STATS_FILE = "daily_stats.json"
HISTORY_TRADES_FILE = "history_trades.json"
daily_stats_lock = threading.RLock()
history_file_lock = threading.RLock()

def load_daily_stats():
    if not os.path.exists(DAILY_STATS_FILE):
        return {}
    try:
        with open(DAILY_STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_daily_stats(stats):
    try:
        with open(DAILY_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERR] Save daily stats failed: {e}")

def load_history_trades():
    if not os.path.exists(HISTORY_TRADES_FILE):
        return []
    try:
        with open(HISTORY_TRADES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []

def save_history_trade(trade_record):
    with history_file_lock:
        current_history = load_history_trades()
        if trade_record.get("cmd_id"):
            if any(t.get("cmd_id") == trade_record["cmd_id"] for t in current_history):
                return
        current_history.insert(0, trade_record)
        if len(current_history) > 1000:
            current_history = current_history[:1000]
        try:
            with open(HISTORY_TRADES_FILE, "w", encoding="utf-8") as f:
                json.dump(current_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERR] Save history trade failed: {e}")

def delete_history_trade_by_id(cmd_id):
    with history_file_lock:
        current_history = load_history_trades()
        new_history = [t for t in current_history if str(t.get("cmd_id")) != str(cmd_id)]
        if len(new_history) != len(current_history):
            try:
                with open(HISTORY_TRADES_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_history, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                print(f"[ERR] Delete history trade failed: {e}")
        return False

def update_daily_stats_from_record(record):
    if not record or not record.get("parsed"):
        return
    parsed = auto_fill_status(record["parsed"])
    daily_pnl = parsed.get("daily_pnl")
    if daily_pnl is None:
        return
    ts = parsed.get("ts") or int(time.time())
    dt_utc8 = datetime.utcfromtimestamp(ts + 8*3600)
    date_str = dt_utc8.strftime("%Y-%m-%d")
    with daily_stats_lock:
        stats = load_daily_stats()
        current_val = round(float(daily_pnl), 2)
        if stats.get(date_str) != current_val:
            stats[date_str] = current_val
            save_daily_stats(stats)
            print(f"[DAILY_STATS] Saved {date_str}: {current_val} (Account: {parsed.get('account')})")

# ==================== 日内计算（UTC+8）====================
day_start_equity_store = {}

def get_utc8_now():
    return int(time.time()) + 8 * 3600

def is_utc8_new_day(last_ts, current_ts):
    from datetime import datetime
    def utc8_date(ts):
        return datetime.utcfromtimestamp(ts + 8*3600).date()
    return utc8_date(last_ts) != utc8_date(current_ts)

def get_day_start_equity(account, current_equity):
    global day_start_equity_store
    now = get_utc8_now()
    if account not in day_start_equity_store:
        day_start_equity_store[account] = (now, current_equity)
        return current_equity
    last_ts, last_equity = day_start_equity_store[account]
    if is_utc8_new_day(last_ts, now):
        day_start_equity_store[account] = (now, current_equity)
        return current_equity
    return last_equity

def calc_lots_from_margin_usd(symbol, margin_usd, data):
    price = get_latest_price(symbol)
    if not price or price <= 0:
        print(f"[CALC_LOTS] Error: Price 0 or missing for {symbol}")
        return 0.0
    spec = PRODUCT_SPECS.get(symbol)
    if not spec:
        if len(symbol) == 6 and symbol.isupper():
            spec = DEFAULT_FOREX_SPEC.copy()
            spec["currency"] = symbol[3:]
        else:
            spec = DEFAULT_STOCK_SPEC.copy()
    settle_currency = spec.get("currency", "USD")
    rate_to_usd = get_rate_to_usd(settle_currency)
    contract_size = spec["size"]
    leverage = spec["lev"]
    if price <= 0 or rate_to_usd <= 0:
        return 0.0
    lots = (margin_usd * leverage) / (price * contract_size * rate_to_usd)
    print(f"[CALC_LOTS] {symbol} Margin=${margin_usd} Lev={leverage} Price={price} Rate={rate_to_usd} -> Lots={lots:.4f}")
    return lots

def get_rate_to_usd(currency):
    if currency == "USD":
        return 1.0
    pair1 = f"{currency}USD"
    price1 = get_latest_price(pair1)
    if price1:
        return price1
    pair2 = f"USD{currency}"
    price2 = get_latest_price(pair2)
    if price2 and price2 > 0:
        return 1.0 / price2
    if currency == "HKD": return 1.0 / 7.8
    print(f"[WARN] Cannot find rate for {currency} -> USD, using 1.0")
    return 1.0

# ★ FIX #2: get_latest_price 优先走 O(1) 缓存，消除每次扫描 history_report 的延迟
def get_latest_price(symbol):
    """优先从 O(1) 报价缓存取价，fallback 到 history_report 扫描"""
    norm = normalize_symbol(symbol or "")
    # 优先走缓存，避免每次都加 history_lock 做线性扫描
    with quote_cache_lock:
        cq = latest_quote_cache.get(norm)
    if cq:
        b, a = _to_float(cq.get("bid")), _to_float(cq.get("ask"))
        if b and a:
            return (b + a) / 2.0

    # fallback：扫描 history_report（兼容旧 EA 不推 /api/tick 的情况）
    with history_lock:
        for record in history_report:
            parsed = record.get("parsed")
            if parsed and parsed.get("desc") == "QUOTE_DATA" and parsed.get("symbol") == symbol:
                try:
                    msg = json.loads(parsed.get("message", "{}"))
                    if "bid" in msg:
                        return (msg["bid"] + msg["ask"]) / 2
                except:
                    pass
    print(f"[PRICE] Warn: No quote found for {symbol}")
    return None

def calc_lot_info(symbol, price, lots):
    spec = PRODUCT_SPECS.get(symbol)
    if not spec:
        if len(symbol) == 6: spec = DEFAULT_FOREX_SPEC.copy(); spec["currency"] = symbol[3:]
        else: spec = DEFAULT_STOCK_SPEC.copy()
    settle_curr = spec.get("currency", "USD")
    rate = get_rate_to_usd(settle_curr)
    margin_per_lot_usd = (price * spec["size"] / spec["lev"]) * rate
    point_val_usd = 0
    if spec["type"] == "forex":
        if "JPY" in symbol:
            point_val_usd = (spec["size"] * 0.001) * rate 
        else:
            point_val_usd = (spec["size"] * 0.00001) * rate
    elif spec["type"] == "metal":
        point_val_usd = spec["size"] * 0.01
    else:
        point_val_usd = spec["size"] * 0.01 * rate
    return {
        "margin_per_lot_usd": margin_per_lot_usd,
        "point_val_usd": point_val_usd,
        "spec": spec
    }

def calc_exposure_signal(margin_level, position_pct, leverage=1):
    if not margin_level or margin_level <= 0:
        return "green"
    effective_leverage = margin_level * (position_pct / 100.0)
    YELLOW_THRESHOLD = 3.0
    RED_THRESHOLD = 5.0
    if effective_leverage >= RED_THRESHOLD:
        return "red"
    elif effective_leverage >= YELLOW_THRESHOLD:
        return "yellow"
    else:
        return "green"

def auto_fill_status(parsed: dict, positions=None, position_pct=0):
    if not isinstance(parsed, dict):
        return parsed

    equity = parsed.get("equity")
    balance = parsed.get("balance")
    margin = parsed.get("margin")
    free_margin = parsed.get("free_margin")
    account = parsed.get("account")

    if parsed.get("floating_pnl") is None:
        parsed["floating_pnl"] = 0.0

    if parsed.get("margin_level") is None:
        if safe_num(equity) and safe_num(margin) and margin > 0:
            parsed["margin_level"] = (equity / margin) * 100
        else:
            parsed["margin_level"] = None

    if account and safe_num(equity):
        day_start_eq = get_day_start_equity(account, equity)
        parsed["day_start_equity"] = day_start_eq
        daily_pnl = equity - day_start_eq
        parsed["daily_pnl"] = daily_pnl
        if day_start_eq and day_start_eq != 0:
            parsed["daily_return"] = (daily_pnl / day_start_eq) * 100
        else:
            parsed["daily_return"] = None
    else:
        if parsed.get("day_start_equity") is None:
            parsed["day_start_equity"] = None
        if parsed.get("daily_pnl") is None:
            dcp = parsed.get("daily_closed_pnl", 0)
            fp = parsed.get("floating_pnl", 0)
            if safe_num(dcp) and safe_num(fp):
                parsed["daily_pnl"] = dcp + fp
            else:
                parsed["daily_pnl"] = None
        if parsed.get("daily_return") is None:
            dse = parsed.get("day_start_equity")
            dpnl = parsed.get("daily_pnl")
            if safe_num(dse) and dse != 0 and safe_num(dpnl):
                parsed["daily_return"] = (dpnl / dse) * 100
            else:
                parsed["daily_return"] = None

    user_position_pct = position_pct if position_pct > 0 else parsed.get("position_pct", 0)
    total_point_value = 0.0
    if positions and isinstance(positions, list):
        for pos in positions:
            pv = pos.get("point_value", 0) or pos.get("point", 0)
            lots = pos.get("lots", 0)
            if pv and lots:
                total_point_value += pv * lots

    if positions and safe_num(equity) and equity > 0:
        position_value = equity * (user_position_pct / 100.0)
        leverage = parsed.get("leverage_used", 20) or 20
        if total_point_value > 0:
            exp_notional = position_value * leverage * total_point_value
        else:
            exp_notional = position_value * leverage * 0.0001
        parsed["exposure_notional"] = round(exp_notional, 2)
        if exp_notional and equity:
            parsed["leverage_used"] = round((exp_notional / equity) * 100, 2)
        else:
            parsed["leverage_used"] = None
    else:
        if parsed.get("exposure_notional") is None:
            parsed["exposure_notional"] = None
        if parsed.get("leverage_used") is None:
            en = parsed.get("exposure_notional")
            if safe_num(en) and safe_num(equity) and equity != 0:
                parsed["leverage_used"] = round((en / equity) * 100, 2)
            else:
                parsed["leverage_used"] = None

    margin_level = parsed.get("margin_level")
    if margin_level and user_position_pct > 0:
        parsed["exposure_signal"] = calc_exposure_signal(margin_level, user_position_pct)
    else:
        parsed["exposure_signal"] = "green"

    if parsed.get("risk_flags") is None:
        parsed["risk_flags"] = ""

    if parsed.get("free_margin") is None:
        if safe_num(equity) and safe_num(margin):
            parsed["free_margin"] = equity - margin
        else:
            parsed["free_margin"] = None

    metrics = parsed.get("metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    metric_fields = {
        "poll_latency_ms": None,
        "last_http_code": None,
        "last_error": "",
        "queue_batch_size": 0,
        "reports_sent_count": 0,
        "executed_commands": 0,
        "failed_commands": 0,
        "position_pct": user_position_pct,
    }
    for k, default in metric_fields.items():
        if k not in metrics:
            metrics[k] = default
    parsed["metrics"] = metrics

    parsed["balance"] = balance
    parsed["equity"] = equity
    parsed["margin"] = margin
    if parsed.get("free_margin") is None and free_margin is not None:
        parsed["free_margin"] = free_margin

    return parsed

def extract_latest_details_from_status(record, positions=None):
    if not record:
        return None

    base_info = {
        "received_at": record.get("received_at"),
        "ip": record.get("ip"),
        "body_raw_preview": (record.get("body_raw", "")[:500] + ("..." if len(record.get("body_raw", "")) > 500 else "")),
        "remaining_data": record.get("remaining_data"),
    }

    if record.get("parse_error"):
        return {
            **base_info,
            "error": f"JSON 解析失败: {record['parse_error']}",
            "full_error": record.get("parse_error_detail", ""),
        }

    parsed = record.get("parsed")
    if not isinstance(parsed, dict):
        return {**base_info, "error": "JSON 解析失败或不是对象"}

    if positions is None:
        positions = record.get("positions")
    parsed = auto_fill_status(parsed, positions)
    metrics = parsed.get("metrics", {})
    
    global risk_state
    current_risk_status = "normal"
    risk_msg = ""
    locked_tickets_list = []
    
    with risk_lock:
        if risk_state["is_fused"]:
            current_risk_status = "fused"
            risk_msg = "触发熔断机制"
        elif int(time.time()) < risk_state["cooldown_until"]:
            current_risk_status = "cooldown"
            risk_msg = "处于冷静期"
        locked_tickets_list = list(risk_state["locked_tickets"])
    
    if is_restricted_time():
        current_risk_status = "restricted_time"
        risk_msg = "系统维护时段"

    return {
        **base_info,
        "account": parsed.get("account"),
        "server": parsed.get("server"),
        "ts": parsed.get("ts"),
        "balance": parsed.get("balance"),
        "equity": parsed.get("equity"),
        "margin": parsed.get("margin"),
        "free_margin": parsed.get("free_margin"),
        "margin_level": parsed.get("margin_level"),
        "floating_pnl": parsed.get("floating_pnl"),
        "day_start_equity": parsed.get("day_start_equity"),
        "daily_closed_pnl": parsed.get("daily_closed_pnl"),
        "daily_pnl": parsed.get("daily_pnl"),
        "daily_return": parsed.get("daily_return"),
        "exposure_notional": parsed.get("exposure_notional"),
        "exposure_signal": parsed.get("exposure_signal"),
        "leverage_used": parsed.get("leverage_used"),
        "risk_flags": parsed.get("risk_flags"),
        "poll_latency_ms": metrics.get("poll_latency_ms"),
        "last_http_code": metrics.get("last_http_code"),
        "last_error": metrics.get("last_error"),
        "queue_batch_size": metrics.get("queue_batch_size"),
        "reports_sent_count": metrics.get("reports_sent_count"),
        "executed_commands": metrics.get("executed_commands"),
        "failed_commands": metrics.get("failed_commands"),
        "position_pct": metrics.get("position_pct", 0),
        "positions": positions if positions else [],
        "risk_status": current_risk_status,
        "risk_msg": risk_msg,
        "locked_tickets": locked_tickets_list
    }

# ==================== 暂停控制接口 ====================
@app.route("/api/pause", methods=["POST"])
def api_pause():
    global paused
    with pause_lock:
        paused = True
    return jsonify({"paused": paused})

@app.route("/api/resume", methods=["POST"])
def api_resume():
    global paused
    with pause_lock:
        paused = False
    return jsonify({"paused": paused})

@app.route("/api/status", methods=["GET"])
def api_status():
    with pause_lock:
        return jsonify({"paused": paused})

@app.route("/api/latest_status", methods=["GET"])
def api_latest_status():
    symbol_filter = request.args.get("symbol", "").upper().strip()
    norm_filter   = normalize_symbol(symbol_filter) if symbol_filter else ""

    detail        = None
    latest_quote  = None
    current_price = 0

    if norm_filter:
        with quote_cache_lock:
            cq = latest_quote_cache.get(norm_filter)
        if cq:
            latest_quote  = dict(cq)
            current_price = _to_float(cq.get("bid")) or 0

    with history_lock:
        latest_status_record    = history_status[0]    if history_status    else None
        latest_positions_record = history_positions[0] if history_positions else None

        if not latest_quote:
            for record in history_report:
                parsed = record.get("parsed")
                if not isinstance(parsed, dict): continue
                if parsed.get("desc") == "QUOTE_DATA":
                    rs = parsed.get("symbol", "")
                    if norm_filter and normalize_symbol(rs) != norm_filter:
                        continue
                    qd = _message_to_quote_dict(parsed)
                    if not qd:
                        try:    qd = json.loads(parsed.get("message") or "{}")
                        except: qd = None
                    if isinstance(qd, dict):
                        b, a = _bid_ask_from_dict(qd)
                        if b is not None and a is not None:
                            latest_quote  = {"bid": b, "ask": a,
                                "symbol": normalize_symbol(rs) or rs,
                                "spread": parsed.get("spread"), "ts": parsed.get("ts")}
                            current_price = b
                            break

        if not latest_quote:
            for record in history_report:
                parsed = record.get("parsed")
                if not isinstance(parsed, dict): continue
                rs = parsed.get("symbol", "")
                if norm_filter and normalize_symbol(rs) != norm_filter: continue
                b, a = _bid_ask_from_dict(parsed)
                if b is not None and a is not None:
                    latest_quote  = {"bid": b, "ask": a,
                        "symbol": normalize_symbol(rs) or rs,
                        "spread": parsed.get("spread"), "ts": parsed.get("ts")}
                    current_price = b
                    break

        positions_data = None
        if latest_positions_record:
            positions_data = latest_positions_record.get("parsed", {}).get("positions", [])
        detail = extract_latest_details_from_status(latest_status_record, positions_data)

    if detail:
        if latest_quote:
            detail["latest_quote"] = latest_quote
        if norm_filter and current_price > 0:
            lot_info = calc_lot_info(norm_filter, current_price, 1.0)
            detail["symbol_rules"] = lot_info
        return jsonify(detail)
    else:
        return jsonify({})

@app.route("/api/history_trades", methods=["GET"])
def api_history_trades():
    limit = request.args.get("limit", 20, type=int)
    all_trades = load_history_trades()
    trades = all_trades[:limit]
    return jsonify({"trades": trades})

@app.route("/api/history_trades/delete", methods=["POST"])
def delete_history_trade_api():
    data = request.json
    cmd_id = data.get("cmd_id")
    password = data.get("password", "")
    if password != "1234567dads":
        return jsonify({"success": False, "message": "密码错误"}), 403
    if not cmd_id:
        return jsonify({"success": False, "message": "缺少指令ID"}), 400
    if delete_history_trade_by_id(cmd_id):
        return jsonify({"success": True, "message": "删除成功"})
    else:
        return jsonify({"success": False, "message": "记录不存在或删除失败"}), 404

@app.route("/api/all_quotes", methods=["GET"])
def api_all_quotes():
    with quote_cache_lock:
        result = {sym: dict(q) for sym, q in latest_quote_cache.items()}
    return jsonify(result)

@app.route("/api/kline", methods=["GET"])
def api_kline():
    symbol = request.args.get("symbol", "XAUUSD").upper().strip()
    norm   = normalize_symbol(symbol)
    tf     = request.args.get("tf", "5min")
    if tf not in KLINE_MAX: tf = "5min"
    limit  = min(request.args.get("limit", KLINE_MAX[tf], type=int), KLINE_MAX[tf])
    with _get_kline_lock(norm):
        bars = list(kline_data.get(norm, {}).get(tf, []))
    return jsonify({"symbol": norm, "tf": tf, "bars": bars[-limit:]})

# ==================== 主页 ====================
HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover" />
  <title>量化交易终端</title>
  <style>
    :root {
      --blue: #007aff;
      --red: #ff3b30;
      --green: #34c759;
      --bg: #ffffff;
      --text: #333333;
      --muted: #8e8e93;
      --line: #c6c6c8;
      --nav-bg: #f8f8f8;
    }
    * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; outline: none; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); padding-bottom: 60px; padding-top: 50px; }
    
    .top-bar { position: fixed; top: 0; left: 0; right: 0; height: 50px; background: var(--bg); border-bottom: 1px solid var(--line); display: flex; align-items: center; justify-content: space-between; padding: 0 15px; font-size: 18px; font-weight: bold; z-index: 100; }
    .top-bar-title { flex: 1; }
    .top-bar-actions { display: flex; gap: 15px; font-size: 24px; color: var(--blue); cursor: pointer; }
    .top-bar-actions span:active { opacity: 0.7; }

    .top-clock {
      display: flex; align-items: center; gap: 5px;
      font-size: 12px; font-weight: 500; color: var(--muted);
      font-variant-numeric: tabular-nums; letter-spacing: 0.3px;
      white-space: nowrap;
    }
    .clock-dot {
      width: 7px; height: 7px; border-radius: 50%;
      background: var(--green); flex-shrink: 0;
      animation: dotPulse 1.5s ease-in-out infinite;
    }
    @keyframes dotPulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50%       { opacity: 0.35; transform: scale(0.7); }
    }
    .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; height: 55px; background: var(--nav-bg); border-top: 1px solid var(--line); display: flex; justify-content: space-around; align-items: center; z-index: 100; padding-bottom: env(safe-area-inset-bottom); }
    .nav-item { display: flex; flex-direction: column; align-items: center; color: var(--muted); font-size: 10px; cursor: pointer; flex: 1; }
    .nav-item.active { color: var(--blue); }
    .nav-icon { font-size: 22px; margin-bottom: 2px; }
    
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    
    .q-row { padding: 10px 15px; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; align-items: center; cursor: pointer; position: relative; }
    .q-row.edit-mode .q-left { margin-left: 30px; }
    .q-delete-btn { position: absolute; left: -30px; top: 50%; transform: translateY(-50%); color: var(--red); font-size: 24px; transition: 0.3s; opacity: 0; pointer-events: none; }
    .q-row.edit-mode .q-delete-btn { left: 10px; opacity: 1; pointer-events: auto; }
    .q-left { display: flex; flex-direction: column; transition: 0.3s; }
    .q-sym { font-size: 16px; font-weight: bold; }
    .q-time, .q-spread { font-size: 12px; color: var(--muted); margin-top: 2px; }
    .q-right { display: flex; flex-direction: column; align-items: flex-end; }
    .q-prices { display: flex; gap: 15px; font-size: 18px; font-weight: bold; }
    .q-prices .blue { color: var(--blue); }
    .q-prices .red { color: var(--red); }
    .q-hl { display: flex; gap: 10px; font-size: 11px; color: var(--muted); margin-top: 4px; }

    .trade-header { padding: 10px 15px; border-bottom: 1px solid var(--line); display: flex; align-items: center; gap: 10px; }
    .sym-title { font-size: 20px; font-weight: bold; }
    .sym-desc { font-size: 14px; color: var(--muted); }
    .trade-type { text-align: center; padding: 15px; font-size: 16px; font-weight: bold; border-bottom: 1px solid var(--line); cursor: pointer; }
    
    .lots-stepper { display: flex; justify-content: space-between; align-items: center; padding: 15px; border-bottom: 1px solid var(--line); }
    .l-btn { color: var(--blue); font-weight: bold; font-size: 16px; padding: 5px; cursor: pointer; min-width: 40px; text-align: center; }
    .lots-stepper input { text-align: center; font-size: 22px; font-weight: bold; border: none; outline: none; width: 80px; color: var(--text); }
    
    .trade-prices { display: flex; justify-content: space-around; padding: 20px 15px; font-size: 32px; font-weight: bold; }
    .trade-prices .red { color: var(--red); }
    .trade-prices .blue { color: var(--blue); }
    
    .t-row { display: flex; align-items: center; padding: 10px 15px; border-bottom: 1px solid var(--line); }
    .t-btn { color: var(--blue); font-size: 24px; width: 40px; text-align: center; cursor: pointer; font-weight: 300; }
    .t-input-wrap { flex: 1; display: flex; justify-content: center; align-items: center; gap: 10px; }
    .t-input-wrap .t-label { color: var(--muted); font-size: 14px; }
    .t-input-wrap input { font-size: 18px; border: none; outline: none; width: 100px; text-align: center; font-weight: bold; }
    
    .sl-tp-row { display: flex; border-bottom: 1px solid var(--line); }
    .t-col { flex: 1; display: flex; align-items: center; padding: 10px 5px; }
    .sl-col { border-bottom: 2px solid var(--red); margin-right: 5px; }
    .tp-col { border-bottom: 2px solid var(--green); margin-left: 5px; }
    .t-col input { flex: 1; width: 100%; text-align: center; border: none; outline: none; font-size: 18px; font-weight: bold; }
    
    .t-duration { padding: 15px; display: flex; justify-content: space-between; border-bottom: 1px solid var(--line); font-size: 14px; }
    .t-duration .t-label { color: var(--muted); }
    .t-duration .t-val { color: var(--text); }
    
    .trade-actions { display: flex; padding: 15px; gap: 10px; margin-top: 10px; }
    .btn-sell, .btn-buy, .btn-place { flex: 1; padding: 15px; border: none; border-radius: 5px; font-size: 16px; font-weight: bold; color: #fff; cursor: pointer; }
    .btn-sell { background: var(--red); }
    .btn-buy { background: var(--blue); }
    .btn-place { background: var(--text); }
    .btn-sell:active, .btn-buy:active, .btn-place:active { opacity: 0.8; }

    .pos-header { padding: 15px; background: var(--nav-bg); border-bottom: 1px solid var(--line); }
    .pos-h-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }
    .pos-h-row:last-child { margin-bottom: 0; }
    .pos-h-row .label { color: var(--muted); }
    .pos-h-row .val { font-weight: bold; }
    .pos-list-title { background: #f0f0f0; padding: 5px 15px; font-size: 12px; color: #666; font-weight: bold; }
    
    .pos-item { padding: 10px 15px; border-bottom: 1px solid var(--line); cursor: pointer; }
    .p-row1 { display: flex; justify-content: space-between; margin-bottom: 5px; align-items: center; }
    .p-sym { font-weight: bold; font-size: 16px; }
    .p-type { font-size: 14px; margin-left: 5px; }
    .p-type.buy { color: var(--blue); }
    .p-type.sell { color: var(--red); }
    .p-lots { font-size: 14px; margin-left: 5px; }
    .p-profit { font-weight: bold; font-size: 16px; }
    .p-profit.blue { color: var(--blue); }
    .p-profit.red { color: var(--red); }
    .p-row2 { display: flex; justify-content: space-between; font-size: 13px; color: var(--muted); }

    .h-card { padding: 12px 15px; border-bottom: 1px solid var(--line); }
    .h-row1 { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .h-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: #fff; margin-left: 6px; }
    .h-badge.buy  { background: var(--blue); }
    .h-badge.sell { background: var(--red); }
    .h-badge.ok   { background: var(--green); }
    .h-badge.fail { background: #aaa; }
    .h-sym  { font-size: 16px; font-weight: bold; }
    .h-profit { font-size: 16px; font-weight: bold; }
    .h-profit.pos { color: var(--green); }
    .h-profit.neg { color: var(--red); }
    .h-profit.zero{ color: var(--muted); }
    .h-row2 { display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); margin-bottom: 3px; }
    .h-row3 { font-size: 12px; color: var(--muted); }

    .modalMask { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: none; align-items: flex-end; z-index: 1000; }
    .modal { width: 100%; background: #fff; border-radius: 15px 15px 0 0; padding-bottom: env(safe-area-inset-bottom); animation: slideUp 0.3s ease-out; max-height: 80vh; overflow-y: auto; }
    @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
    .modalHeader { padding: 15px; text-align: center; font-weight: bold; font-size: 16px; border-bottom: 1px solid var(--line); position: relative; }
    .modalHeader .close { position: absolute; right: 15px; top: 15px; color: var(--blue); cursor: pointer; }
    .select-item { padding: 15px; border-bottom: 1px solid var(--line); font-size: 16px; text-align: center; cursor: pointer; }
    .select-item:active { background: #f0f0f0; }

    .modalBody { padding: 15px; }
    .quiz-item { margin-bottom: 15px; }
    .quiz-q { font-size: 14px; font-weight: bold; margin-bottom: 10px; }
    .quiz-opts { display: flex; gap: 10px; flex-direction: column; }
    .quiz-opt { padding: 10px; border: 1px solid var(--line); border-radius: 8px; text-align: center; font-size: 14px; cursor: pointer; }
    .quiz-opt.selected { background: var(--blue); color: #fff; border-color: var(--blue); }
    .cta { width: 100%; padding: 15px; background: var(--blue); color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; margin-top: 10px; }
    .cat-tabs { display: flex; overflow-x: auto; border-bottom: 1px solid var(--line); background: var(--nav-bg); }
    .cat-tab { padding: 12px 15px; white-space: nowrap; color: var(--muted); font-weight: bold; cursor: pointer; }
    .cat-tab.active { color: var(--blue); border-bottom: 2px solid var(--blue); }
    .sym-add-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; border-bottom: 1px solid var(--line); }
    .sym-add-info { display: flex; flex-direction: column; }
    .sym-add-name { font-weight: bold; font-size: 16px; }
    .sym-add-desc { font-size: 12px; color: var(--muted); }
    .sym-add-btn { color: var(--green); font-size: 24px; cursor: pointer; }
    .sym-add-btn.added { color: var(--muted); cursor: default; }

    .kline-section { margin: 0 0 0 0; border-top: 1px solid var(--line); }
    .kline-header { display: flex; align-items: center; justify-content: space-between;
      padding: 8px 15px; background: #f8f8f8; border-bottom: 1px solid var(--line); }
    .kline-title { font-size: 13px; font-weight: bold; color: var(--muted); }
    .kline-ohlc  { font-size: 11px; color: var(--muted); font-family: "SF Mono", Menlo, monospace; }
    .kline-tfs   { display: flex; gap: 6px; }
    .kline-tf    { padding: 2px 10px; border-radius: 4px; border: 1px solid var(--line);
      background: transparent; color: var(--muted); font-weight: 600; font-size: 12px;
      cursor: pointer; transition: .15s; }
    .kline-tf:hover { color: var(--blue); border-color: var(--blue); }
    .kline-tf.on    { background: var(--blue); color: #fff; border-color: var(--blue); }
    .kline-wrap  { position: relative; height: 260px; cursor: crosshair;
      background: #fff; }
    #klineCanvas, #klineCursor { position: absolute; inset: 0; width: 100%; height: 100%; }
    #klineCursor { pointer-events: none; }

    .success-overlay {
      position: fixed; inset: 0; z-index: 9999;
      display: flex; align-items: center; justify-content: center;
      background: rgba(0,0,0,0.45);
      opacity: 0; pointer-events: none;
      transition: opacity 0.2s ease;
    }
    .success-overlay.show { opacity: 1; pointer-events: auto; }

    .success-card {
      background: #fff; border-radius: 20px;
      padding: 36px 40px 28px;
      display: flex; flex-direction: column; align-items: center; gap: 16px;
      transform: scale(0.78); opacity: 0;
      transition: transform 0.28s cubic-bezier(0.34,1.56,0.64,1), opacity 0.22s ease;
      min-width: 200px;
    }
    .success-overlay.show .success-card { transform: scale(1); opacity: 1; }

    .success-ring { width: 72px; height: 72px; }
    .success-ring circle {
      fill: none; stroke: #e5e5ea; stroke-width: 5;
    }
    .success-ring .ring-progress {
      fill: none; stroke-width: 5; stroke-linecap: round;
      stroke-dasharray: 188; stroke-dashoffset: 188;
      transform-origin: center; transform: rotate(-90deg);
      transition: none;
    }
    .success-ring .ring-progress.buy-ring  { stroke: var(--blue); }
    .success-ring .ring-progress.close-ring { stroke: var(--green); }
    .success-overlay.show .ring-progress {
      animation: drawRing 0.45s ease-out 0.05s forwards;
    }
    @keyframes drawRing { to { stroke-dashoffset: 0; } }

    .success-ring .tick {
      fill: none; stroke-width: 5; stroke-linecap: round; stroke-linejoin: round;
      stroke-dasharray: 60; stroke-dashoffset: 60;
    }
    .success-ring .tick.buy-tick  { stroke: var(--blue); }
    .success-ring .tick.close-tick { stroke: var(--green); }
    .success-overlay.show .tick {
      animation: drawTick 0.3s ease-out 0.45s forwards;
    }
    @keyframes drawTick { to { stroke-dashoffset: 0; } }

    .success-label {
      font-size: 18px; font-weight: bold; color: var(--text);
      letter-spacing: 1px;
    }
    .success-sub {
      font-size: 13px; color: var(--muted); margin-top: -8px;
    }
  </style>
</head>
<body>
  <div class="top-bar">
    <div class="top-bar-title" id="topBarTitle">行情</div>
    <div class="top-clock">
      <div class="clock-dot"></div>
      <span id="liveClock">--:--:--</span>
      <span style="font-size:10px;color:#b0b0b5;">UTC+8</span>
    </div>
    <div class="top-bar-actions" id="quotesActions">
      <span onclick="openAddSymbol()">+</span>
      <span id="btnEditQuotes" onclick="toggleEditQuotes()">✎</span>
    </div>
  </div>

  <div class="tab-content active" id="tab-quotes">
    <div id="quotesList"></div>
  </div>

  <div class="tab-content" id="tab-trade">
    <div class="trade-header">
      <div class="sym-title" id="tradeSym">XAUUSD</div>
      <div class="sym-desc" id="tradeSymDesc">Spot Gold</div>
    </div>
    <div class="trade-type" onclick="$('orderTypeMask').style.display='flex'">
      <span id="orderTypeText">市价执行</span>
    </div>
    <div class="lots-stepper">
      <div class="l-btn" onclick="adjustLots(-0.1)">-0.1</div>
      <div class="l-btn" onclick="adjustLots(-0.01)">-0.01</div>
      <input type="number" id="inpLots" value="0.11" step="0.01" oninput="onLotsChange(this)">
      <div class="l-btn" onclick="adjustLots(0.01)">+0.01</div>
      <div class="l-btn" onclick="adjustLots(0.1)">+0.1</div>
    </div>
    <div class="trade-prices">
      <div class="t-bid red" id="tBid">--</div>
      <div class="t-ask blue" id="tAsk">--</div>
    </div>
    <div class="t-row" id="rowPrice" style="display:none;">
      <div class="t-btn" onclick="adjustInput('inpPrice', -1)">-</div>
      <div class="t-input-wrap">
        <span class="t-label">价格:</span>
        <input type="number" id="inpPrice" placeholder="0.00">
      </div>
      <div class="t-btn" onclick="adjustInput('inpPrice', 1)">+</div>
    </div>
    <div class="sl-tp-row">
      <div class="t-col sl-col">
        <div class="t-btn" onclick="adjustInput('inpSl', -1)">-</div>
        <input type="number" id="inpSl" placeholder="0.00">
        <div class="t-btn" onclick="adjustInput('inpSl', 1)">+</div>
      </div>
      <div class="t-col tp-col">
        <div class="t-btn" onclick="adjustInput('inpTp', -1)">-</div>
        <input type="number" id="inpTp" placeholder="0.00">
        <div class="t-btn" onclick="adjustInput('inpTp', 1)">+</div>
      </div>
    </div>
    <div class="t-duration" onclick="$('ttlMask').style.display='flex'">
      <span class="t-label">期限:</span>
      <span class="t-val" id="ttlDisplay">直到取消</span>
      <input type="hidden" id="inpTTL" value="0">
    </div>
    
    <div class="trade-actions" id="actionMarket">
      <button class="btn-sell" onclick="initiateOrder('SELL')">Sell by Market</button>
      <button class="btn-buy" onclick="initiateOrder('BUY')">Buy by Market</button>
    </div>
    <div class="trade-actions" id="actionPending" style="display:none;">
      <button class="btn-place" onclick="initiateOrder('PENDING')">下单</button>
    </div>

  <div class="kline-section" id="klineSection">
    <div class="kline-header">
      <span class="kline-title" id="klineSymLabel">K线</span>
      <span class="kline-ohlc" id="klineOHLC"></span>
      <div class="kline-tfs">
        <button class="kline-tf on" data-tf="5min"  onclick="kSetTF(this)">5m</button>
        <button class="kline-tf"    data-tf="10min" onclick="kSetTF(this)">10m</button>
        <button class="kline-tf"    data-tf="1hour" onclick="kSetTF(this)">1H</button>
      </div>
    </div>
    <div class="kline-wrap" id="klineWrap">
      <canvas id="klineCanvas"></canvas>
      <canvas id="klineCursor"></canvas>
    </div>
  </div>
</div>

  <div class="tab-content" id="tab-positions">
    <div class="pos-header">
      <div class="pos-h-row"><span class="label">结余:</span><span class="val" id="valBalance"></span></div>
      <div class="pos-h-row"><span class="label">净值:</span><span class="val" id="valEquity"></span></div>
      <div class="pos-h-row"><span class="label">可用预付款:</span><span class="val" id="valFreeMargin"></span></div>
    </div>
    <div class="pos-list-title">持仓</div>
    <div id="list-positions"></div>
    <div class="pos-list-title">订单</div>
    <div id="list-orders"></div>
  </div>

  <div class="tab-content" id="tab-history">
    <div class="pos-header">
      <div class="pos-h-row"><span class="label">利润:</span><span class="val" id="valProfit"></span></div>
      <div class="pos-h-row"><span class="label">结余:</span><span class="val" id="valHistBalance"></span></div>
    </div>
    <div id="list-history"></div>
  </div>

  <div class="success-overlay" id="successOverlay" onclick="hideSuccess()">
    <div class="success-card" id="successCard">
      <svg class="success-ring" viewBox="0 0 72 72" id="successSvg">
        <circle cx="36" cy="36" r="30"/>
        <circle class="ring-progress" id="ringProgress" cx="36" cy="36" r="30"/>
        <polyline class="tick" id="successTick" points="20,37 30,47 52,25"/>
      </svg>
      <div class="success-label" id="successLabel">下单成功</div>
      <div class="success-sub" id="successSub">指令已发送至 MT4</div>
    </div>
  </div>

  <div class="bottom-nav">
    <div class="nav-item active" onclick="switchTab('quotes', '行情', this)">
      <div class="nav-icon">📊</div>
      <span>行情</span>
    </div>
    <div class="nav-item" onclick="switchTab('trade', '交易', this)">
      <div class="nav-icon">⚖️</div>
      <span>交易</span>
    </div>
    <div class="nav-item" onclick="switchTab('positions', '持仓', this)">
      <div class="nav-icon">💼</div>
      <span>持仓</span>
    </div>
    <div class="nav-item" onclick="switchTab('history', '历史', this)">
      <div class="nav-icon">🕒</div>
      <span>历史</span>
    </div>
  </div>

  <div class="modalMask" id="orderTypeMask" onclick="closeModal(event, 'orderTypeMask')">
    <div class="modal">
      <div class="modalHeader">选择交易类型 <span class="close" onclick="$('orderTypeMask').style.display='none'">取消</span></div>
      <div class="modalBody" style="padding:0;">
        <div class="select-item" onclick="setOrderType('market', '市价执行', '')">市价执行</div>
        <div class="select-item" onclick="setOrderType('limit', 'Buy Limit', 'BUY')">Buy Limit</div>
        <div class="select-item" onclick="setOrderType('limit', 'Sell Limit', 'SELL')">Sell Limit</div>
        <div class="select-item" onclick="setOrderType('limit', 'Buy Stop', 'BUY')">Buy Stop</div>
        <div class="select-item" onclick="setOrderType('limit', 'Sell Stop', 'SELL')">Sell Stop</div>
      </div>
    </div>
  </div>

  <div class="modalMask" id="ttlMask" onclick="closeModal(event, 'ttlMask')">
    <div class="modal">
      <div class="modalHeader">期限 <span class="close" onclick="$('ttlMask').style.display='none'">取消</span></div>
      <div class="modalBody" style="padding:0;">
        <div class="select-item" onclick="setTTL(0, '直到取消')">直到取消 (GTC)</div>
        <div class="select-item" onclick="setTTL(10, '10 分钟')">10 分钟</div>
        <div class="select-item" onclick="setTTL(60, '1 小时')">1 小时</div>
        <div class="select-item" onclick="setTTL(1440, '1 天')">1 天</div>
      </div>
    </div>
  </div>

  <div class="modalMask" id="modifyMask" onclick="closeModal(event, 'modifyMask')">
    <div class="modal">
      <div class="modalHeader">修改订单 <span class="close" onclick="$('modifyMask').style.display='none'">取消</span></div>
      <div class="modalBody">
        <div class="sl-tp-row" style="border:none; margin-bottom: 20px;">
          <div class="t-col sl-col">
            <div class="t-btn" onclick="adjustInput('modSlPrice', -1)">-</div>
            <input type="number" id="modSlPrice" placeholder="止损">
            <div class="t-btn" onclick="adjustInput('modSlPrice', 1)">+</div>
          </div>
          <div class="t-col tp-col">
            <div class="t-btn" onclick="adjustInput('modTpPrice', -1)">-</div>
            <input type="number" id="modTpPrice" placeholder="止盈">
            <div class="t-btn" onclick="adjustInput('modTpPrice', 1)">+</div>
          </div>
        </div>
        <button class="cta" onclick="submitModifyOrder()">修改</button>
        <button class="cta" style="background:var(--red); margin-top:10px;" onclick="closePosition()">平仓</button>
      </div>
    </div>
  </div>

  <div class="modalMask" id="quizMask" onclick="closeModal(event, 'quizMask')">
    <div class="modal">
      <div class="modalHeader">执行前风控检查 <span class="close" onclick="$('quizMask').style.display='none'">取消</span></div>
      <div class="modalBody">
        <div class="quiz-item">
          <div class="quiz-q">1. 该笔交易是否顺应大级别趋势？</div>
          <div class="quiz-opts">
            <div class="quiz-opt" onclick="selectQuiz(this, 1, 'A')">A. 是的，顺势</div>
            <div class="quiz-opt" onclick="selectQuiz(this, 1, 'B')">B. 否，逆势博弈</div>
          </div>
        </div>
        <div class="quiz-item">
          <div class="quiz-q">2. 盈亏比是否达到你的交易系统标准？</div>
          <div class="quiz-opts">
            <div class="quiz-opt" onclick="selectQuiz(this, 2, 'A')">A. 已达标</div>
            <div class="quiz-opt" onclick="selectQuiz(this, 2, 'B')">B. 未达标</div>
          </div>
        </div>
        <button class="cta" onclick="confirmOrderAfterQuiz()">确认并发送订单</button>
      </div>
    </div>
  </div>

  <div class="modalMask" id="addSymbolMask" onclick="closeModal(event, 'addSymbolMask')">
    <div class="modal" style="height: 90vh;">
      <div class="modalHeader">添加品种 <span class="close" onclick="$('addSymbolMask').style.display='none'">取消</span></div>
      <div class="cat-tabs" id="addSymbolCats"></div>
      <div class="modalBody" id="addSymbolList" style="padding:0; overflow-y: auto; height: calc(100% - 100px);"></div>
    </div>
  </div>

  <script>
    const $ = id => document.getElementById(id);
    window.quantState = {
      price: 0,
      lots: 0.11,
      orderType: 'market',
      pendingSide: '',
      currentModifyTicket: null,
      currentModifySymbol: null,
      currentModifyLots: 0
    };
    let quoteInterval = null;
    let quizAnswers = {};

    function fmtNum(n, d) {
      if (n === null || n === undefined || n === '' || isNaN(parseFloat(n))) return '';
      return parseFloat(n).toFixed(d);
    }

    function calcDigits(price, sym) {
      if (sym) {
        const u = sym.toUpperCase();
        if (["XAUUSD","XAGUSD","UKOUSD","USOUSD"].includes(u))  return 2;
        if (["BTCUSD","ETHUSD"].includes(u))                     return 2;
        if (u.endsWith("JPY"))                                    return 3;
        if (["DOGUSD","ADAUSD","RPLUSD","XSIUSD","LNKUSD"].includes(u)) return 5;
        if (["LTCUSD","SOLUSD","BCHUSD","XMRUSD","BNBUSD","AVEUSD","DSHUSD"].includes(u)) return 2;
        if (["U30USD","NASUSD","SPXUSD","100GBP","D30EUR","E50EUR","H33HKD"].includes(u)) return 1;
        const fx = ["USD","GBP","EUR","JPY","CHF","AUD","NZD","CAD","HKD","SGD","CNH"];
        if (fx.some(c => u.includes(c) && !["BTCUSD","ETHUSD"].includes(u))) return 5;
        return 2;
      }
      const p = parseFloat(price);
      if (isNaN(p) || p <= 0) return 4;
      if (p < 10)   return 5;
      if (p < 100)  return 3;
      return 2;
    }

    const categoryPairs = {
      'Forex': [
        { name: 'USDCHF', desc: 'US Dollar vs Swiss Franc', price: 0.8840 },
        { name: 'GBPUSD', desc: 'Great Britain Pound vs US Dollar', price: 1.2640 },
        { name: 'EURUSD', desc: 'Euro vs US Dollar', price: 1.1561 },
        { name: 'USDJPY', desc: 'US Dollar vs Japanese Yen', price: 149.50 },
        { name: 'USDCAD', desc: 'US Dollar vs Canadian Dollar', price: 1.3580 },
        { name: 'AUDUSD', desc: 'Australian Dollar vs US Dollar', price: 0.6520 },
        { name: 'EURGBP', desc: 'Euro vs Great Britain Pound', price: 0.8580 },
        { name: 'EURAUD', desc: 'Euro vs Australian Dollar', price: 1.6533 },
        { name: 'EURCHF', desc: 'Euro vs Swiss Franc', price: 0.9050 },
        { name: 'EURJPY', desc: 'Euro vs Japanese Yen', price: 162.74 },
        { name: 'GBPCHF', desc: 'Great Britain Pound vs Swiss Franc', price: 1.0418 },
        { name: 'CADJPY', desc: 'Canadian Dollar vs Japanese Yen', price: 115.48 },
        { name: 'GBPJPY', desc: 'Great Britain Pound vs Japanese Yen', price: 210.35 },
        { name: 'AUDNZD', desc: 'Australian Dollar vs New Zealand Dollar', price: 1.1918 },
        { name: 'AUDCAD', desc: 'Australian Dollar vs Canadian Dollar', price: 0.9568 },
        { name: 'AUDCHF', desc: 'Australian Dollar vs Swiss Franc', price: 0.5473 },
        { name: 'AUDJPY', desc: 'Australian Dollar vs Japanese Yen', price: 110.51 },
        { name: 'CHFJPY', desc: 'Swiss Franc vs Japanese Yen', price: 201.88 },
        { name: 'EURNZD', desc: 'Euro vs New Zealand Dollar', price: 1.9707 },
        { name: 'EURCAD', desc: 'Euro vs Canadian Dollar', price: 1.5822 },
        { name: 'CADCHF', desc: 'Canadian Dollar vs Swiss Franc', price: 0.5719 },
        { name: 'NZDJPY', desc: 'New Zealand Dollar vs Japanese Yen', price: 92.71 },
        { name: 'NZDUSD', desc: 'New Zealand Dollar vs US Dollar', price: 0.5872 },
        { name: 'GBPAUD', desc: 'Great Britain Pound vs Australian Dollar', price: 1.9032 },
        { name: 'GBPCAD', desc: 'Great Britain Pound vs Canadian Dollar', price: 1.8213 },
        { name: 'GBPNZD', desc: 'Great Britain Pound vs New Zealand Dollar', price: 2.2686 },
        { name: 'NZDCAD', desc: 'New Zealand Dollar vs Canadian Dollar', price: 0.8027 },
        { name: 'NZDCHF', desc: 'New Zealand Dollar vs Swiss Franc', price: 0.4591 },
        { name: 'USDSGD', desc: 'US Dollar vs Singapore Dollar', price: 1.2805 },
        { name: 'USDHKD', desc: 'US Dollar vs Hong Kong Dollar', price: 7.8190 },
        { name: 'USDCNH', desc: 'US Dollar vs Chinese Yuan', price: 6.9147 }
      ],
      'Metals': [
        { name: 'XAGUSD', desc: 'Spot Silver', price: 82.76 },
        { name: 'XAUUSD', desc: 'Spot Gold', price: 5110.43 }
      ],
      'Indices': [
        { name: 'U30USD', desc: 'Wall Street 30', price: 47836.1 },
        { name: 'NASUSD', desc: 'US Tech 100', price: 24922.8 },
        { name: 'SPXUSD', desc: 'US SPX 500', price: 6803.72 },
        { name: '100GBP', desc: 'UK 100', price: 10428.9 },
        { name: 'D30EUR', desc: 'Germany 30', price: 23822.2 },
        { name: 'E50EUR', desc: 'Euro STOXX 50', price: 5773.4 },
        { name: 'H33HKD', desc: 'Hong Kong 50', price: 25503.1 }
      ],
      'Commodities': [
        { name: 'UKOUSD', desc: 'UK Brent Oil', price: 87.35 },
        { name: 'USOUSD', desc: 'US Crude Oil', price: 84.29 }
      ],
      'Crypto': [
        { name: 'BTCUSD', desc: 'Bitcoin', price: 70594 },
        { name: 'BCHUSD', desc: 'Bitcoin Cash', price: 456.94 },
        { name: 'RPLUSD', desc: 'Ripple', price: 1.4003 },
        { name: 'LTCUSD', desc: 'Litecoin', price: 55.28 },
        { name: 'ETHUSD', desc: 'Ethereum', price: 2061.8 },
        { name: 'XMRUSD', desc: 'Monero', price: 357.28 },
        { name: 'BNBUSD', desc: 'Binance Coin', price: 641.10 },
        { name: 'SOLUSD', desc: 'Solana', price: 87.5 },
        { name: 'LNKUSD', desc: 'Chainlink', price: 9.123 },
        { name: 'XSIUSD', desc: 'Shiba Inu', price: 0.201 },
        { name: 'DOGUSD', desc: 'Dogecoin', price: 0.0933 },
        { name: 'ADAUSD', desc: 'Cardano', price: 0.2673 },
        { name: 'AVEUSD', desc: 'Aave', price: 116.35 },
        { name: 'DSHUSD', desc: 'Dash', price: 34.063 }
      ],
      'Stocks': [
        { name: 'AAPL', desc: 'Apple Inc', price: 260.39 },
        { name: 'AMZN', desc: 'Amazon.com', price: 218.76 },
        { name: 'BABA', desc: 'Alibaba Group', price: 130.22 },
        { name: 'GOOGL', desc: 'Alphabet Inc', price: 301.18 },
        { name: 'META', desc: 'Meta Platforms', price: 660.93 },
        { name: 'MSFT', desc: 'Microsoft Corp', price: 410.64 },
        { name: 'NFLX', desc: 'Netflix Inc', price: 99.14 },
        { name: 'NVDA', desc: 'NVIDIA Corp', price: 178.51 },
        { name: 'TSLA', desc: 'Tesla Inc', price: 405.46 },
        { name: 'ABBV', desc: 'AbbVie Inc', price: 232.09 },
        { name: 'ABNB', desc: 'Airbnb Inc', price: 135.71 },
        { name: 'ABT', desc: 'Abbott Laboratories', price: 110.86 },
        { name: 'ADBE', desc: 'Adobe Inc', price: 281.64 },
        { name: 'AMD', desc: 'Advanced Micro Devices', price: 198.97 },
        { name: 'AVGO', desc: 'Broadcom Inc', price: 332.70 },
        { name: 'C', desc: 'Citigroup Inc', price: 108.86 },
        { name: 'CRM', desc: 'Salesforce Inc', price: 201.29 },
        { name: 'DIS', desc: 'Walt Disney Co', price: 102.35 },
        { name: 'GS', desc: 'Goldman Sachs', price: 835.15 },
        { name: 'INTC', desc: 'Intel Corp', price: 45.80 },
        { name: 'JNJ', desc: 'Johnson & Johnson', price: 239.52 },
        { name: 'MA', desc: 'Mastercard Inc', price: 524.28 },
        { name: 'MCD', desc: 'McDonalds Corp', price: 327.32 },
        { name: 'KO', desc: 'Coca-Cola Co', price: 76.91 },
        { name: 'MMM', desc: '3M Co', price: 156.12 },
        { name: 'NIO', desc: 'NIO Inc', price: 4.56 },
        { name: 'PLTR', desc: 'Palantir Tech', price: 152.50 },
        { name: 'SHOP', desc: 'Shopify Inc', price: 134.68 },
        { name: 'TSM', desc: 'Taiwan Semiconductor', price: 344.40 },
        { name: 'V', desc: 'Visa Inc', price: 319.47 }
      ]
    };
    
    const allAvailablePairs = Object.values(categoryPairs).flat();

    let savedQuotes = [];
    try {
        const stored = localStorage.getItem('mt4_saved_quotes');
        if (stored) {
            savedQuotes = JSON.parse(stored);
        } else {
            savedQuotes = ['D30EUR', 'NASUSD', 'U30USD', 'XAUUSD', 'EURUSD', 'USOUSD', 'H33HKD'];
            localStorage.setItem('mt4_saved_quotes', JSON.stringify(savedQuotes));
        }
    } catch(e) {
        savedQuotes = ['XAUUSD', 'EURUSD'];
    }
    
    let isEditMode = false;

    (function() {
      function tickClock() {
        var el = document.getElementById('liveClock');
        if (!el) return;
        var now = new Date(Date.now() + 8 * 3600 * 1000);
        el.innerText = [now.getUTCHours(), now.getUTCMinutes(), now.getUTCSeconds()]
          .map(function(n){ return String(n).padStart(2,'0'); }).join(':');
      }
      tickClock();
      setInterval(tickClock, 1000);
    })();

    window.onload = () => {
      renderQuotes();
      selectSymbol('XAUUSD', 'Spot Gold');
      setInterval(refreshData, 1500);
      setInterval(refreshAllQuotes, 1500);
    };

    function renderQuotes() {
      let html = '';
      const displayPairs = allAvailablePairs.filter(p => savedQuotes.includes(p.name));
      displayPairs.forEach(p => {
        html += `
        <div class="q-row ${isEditMode ? 'edit-mode' : ''}" onclick="${isEditMode ? '' : `selectSymbol('${p.name}', '${p.desc}')`}">
          <div class="q-delete-btn" onclick="removeQuote('${p.name}', event)">⊖</div>
          <div class="q-left">
            <div class="q-sym">${p.name}</div>
            <div class="q-time" id="q_time_${p.name}">--</div>
            <div class="q-spread" id="q_spread_${p.name}">点差: --</div>
          </div>
          <div class="q-right">
            <div class="q-prices">
              <div class="blue" id="q_bid_${p.name}">--</div>
              <div class="red" id="q_ask_${p.name}">--</div>
            </div>
            <div class="q-hl">
              <div>最低: <span id="q_low_${p.name}">--</span></div>
              <div>最高: <span id="q_high_${p.name}">--</span></div>
            </div>
          </div>
        </div>`;
      });
      $('quotesList').innerHTML = html || '<div style="padding:20px;text-align:center;color:#888;">暂无收藏品种，请点击右上角添加</div>';
    }

    window.toggleEditQuotes = function() {
        isEditMode = !isEditMode;
        $('btnEditQuotes').style.color = isEditMode ? 'var(--red)' : 'var(--blue)';
        renderQuotes();
    };

    window.removeQuote = function(name, event) {
        event.stopPropagation();
        savedQuotes = savedQuotes.filter(q => q !== name);
        localStorage.setItem('mt4_saved_quotes', JSON.stringify(savedQuotes));
        renderQuotes();
    };

    window.openAddSymbol = function() {
        renderAddSymbolCats();
        renderAddSymbolList(Object.keys(categoryPairs)[0]);
        $('addSymbolMask').style.display = 'flex';
    };

    function renderAddSymbolCats() {
        let html = '';
        Object.keys(categoryPairs).forEach((cat, idx) => {
            html += `<div class="cat-tab ${idx === 0 ? 'active' : ''}" onclick="switchAddCat(this, '${cat}')">${cat}</div>`;
        });
        $('addSymbolCats').innerHTML = html;
    }

    window.switchAddCat = function(el, cat) {
        document.querySelectorAll('.cat-tab').forEach(t => t.classList.remove('active'));
        el.classList.add('active');
        renderAddSymbolList(cat);
    };

    function renderAddSymbolList(cat) {
        let html = '';
        const pairs = categoryPairs[cat] || [];
        pairs.forEach(p => {
            const isAdded = savedQuotes.includes(p.name);
            html += `
            <div class="sym-add-item">
                <div class="sym-add-info">
                    <div class="sym-add-name">${p.name}</div>
                    <div class="sym-add-desc">${p.desc}</div>
                </div>
                <div class="sym-add-btn ${isAdded ? 'added' : ''}" onclick="${isAdded ? '' : `addQuote('${p.name}', this)`}">
                    ${isAdded ? '✓' : '⊕'}
                </div>
            </div>`;
        });
        $('addSymbolList').innerHTML = html;
    }

    window.addQuote = function(name, btnEl) {
        if (!savedQuotes.includes(name)) {
            savedQuotes.push(name);
            localStorage.setItem('mt4_saved_quotes', JSON.stringify(savedQuotes));
            btnEl.innerHTML = '✓';
            btnEl.classList.add('added');
            btnEl.onclick = null;
            renderQuotes();
        }
    };

    window.switchTab = function(tabId, title, el) {
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      $('tab-' + tabId).classList.add('active');
      el.classList.add('active');
      $('topBarTitle').innerText = title;
      _activeTab = tabId;
      if(tabId === 'history') fetchHistoryTrades();
      if(tabId === 'positions') refreshData();
    };

    window.selectSymbol = function(name, desc) {
      $('tradeSym').innerText = name;
      if (desc) $('tradeSymDesc').innerText = desc;
      $('tBid').innerText = '--';
      $('tAsk').innerText = '--';
      window.quantState.price = 0;
      
      if(quoteInterval) clearInterval(quoteInterval);
      window.API.submitOrder(name, 'QUOTE', 'quote', 0, 0, 0, {}); 
      quoteInterval = setInterval(() => {
          window.API.submitOrder(name, 'QUOTE', 'quote', 0, 0, 0, {});
      }, 1000);
      
      setTimeout(refreshData, 500);
      switchTab('trade', '交易', document.querySelectorAll('.nav-item')[1]);
    };

    window.adjustLots = function(delta) {
        let val = parseFloat($('inpLots').value) || 0;
        val += delta;
        if(val < 0.01) val = 0.01;
        $('inpLots').value = val.toFixed(2);
        window.quantState.lots = val;
    };
    window.onLotsChange = function(el) {
        let val = parseFloat(el.value);
        if(isNaN(val) || val < 0) val = 0.01;
        window.quantState.lots = val;
    };

    window.adjustInput = function(id, delta) {
        let el = $(id);
        let val = parseFloat(el.value) || 0;
        let step = val < 10 ? 0.0001 : 0.01;
        val += delta * step;
        if(val < 0) val = 0;
        el.value = val.toFixed(step < 0.01 ? 4 : 2);
    };

    window.setOrderType = function(typeCode, typeName, pendingSide) {
      window.quantState.orderType = typeCode;
      window.quantState.pendingSide = pendingSide;
      $('orderTypeText').innerText = typeName;
      $('orderTypeMask').style.display = 'none';
      if (typeCode === 'market') {
        $('rowPrice').style.display = 'none';
        $('actionMarket').style.display = 'flex';
        $('actionPending').style.display = 'none';
      } else {
        $('rowPrice').style.display = 'flex';
        $('actionMarket').style.display = 'none';
        $('actionPending').style.display = 'flex';
        if(!$('inpPrice').value || $('inpPrice').value == 0) $('inpPrice').value = window.quantState.price;
      }
    };

    window.setTTL = function(val, text) {
      $('inpTTL').value = val;
      $('ttlDisplay').innerText = text;
      $('ttlMask').style.display = 'none';
    };

    window.closeModal = function(e, id) { if(e.target.id === id) $(id).style.display = 'none'; };

    window.initiateOrder = function(side) {
      if(side !== 'PENDING') window.quantState.pendingSide = side;
      quizAnswers = {};
      document.querySelectorAll('.quiz-opt').forEach(el => el.classList.remove('selected'));
      $('quizMask').style.display = 'flex';
    };

    window.selectQuiz = function(el, qIndex, answer) {
      el.parentElement.querySelectorAll('.quiz-opt').forEach(opt => opt.classList.remove('selected'));
      el.classList.add('selected');
      quizAnswers[qIndex] = answer;
    };

    // ★ FIX #3: 修复 confirmOrderAfterQuiz — 去掉 marginPct=0 硬编码，
    //    直接读取手数输入框，确保 lots 正确传递，不再走断裂的 marginPct 计算链路
    window.confirmOrderAfterQuiz = function() {
      if(Object.keys(quizAnswers).length < 2) return alert('请先完成风控检查！');
      $('quizMask').style.display = 'none';
      
      // ★ 直接从输入框读取手数，保证不为 0
      const lotsToSend = Math.max(parseFloat($('inpLots').value) || 0.01, 0.01);

      const params = {
          inpPrice: parseFloat($('inpPrice').value) || 0,
          inpTp:    parseFloat($('inpTp').value)    || 0,
          inpSl:    parseFloat($('inpSl').value)    || 0,
          inpTTL:   parseFloat($('inpTTL').value)   || 0
      };
      
      window.API.submitOrder(
        $('tradeSym').innerText, 
        window.quantState.pendingSide, 
        window.quantState.orderType,
        0,            // marginPct 不使用，统一走 lots 路径
        20, 
        lotsToSend,   // ★ 确保 lots 正确传递
        params
      ).then(res => {
        if(res && res.success) {
          const sideType = (window.quantState.pendingSide||'').toLowerCase() === 'sell' ? 'sell' : 'buy';
          showSuccess(sideType);
          refreshData();
        } else {
          alert('发送失败: ' + ((res && res.message) || '请检查网络或重试'));
        }
      }).catch(e => {
        alert('网络错误，请重试');
        console.error(e);
      });
    };

    window.API = {
      submitOrder: async function(symbol, side, type, marginPct, leverage, lots, params) {
        try {
          const res = await fetch('/api/v1/order', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, side, type, marginPct, leverage, lots, ...params })
          });
          return await res.json();
        } catch (e) { return { success: false, message: 'Network error' }; }
      },
      modifyPosition: async function(positionId, tpPrice, slPrice) {
        try {
          const res = await fetch('/api/v1/position/modify', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ positionId, tpPrice, slPrice })
          });
          return await res.json();
        } catch (e) { return { success: false }; }
      },
      cancelCommand: async function(id) { alert("暂不支持前端撤单"); }
    };

    async function refreshAllQuotes() {
      try {
        const res = await fetch('/api/all_quotes');
        if (!res.ok) return;
        const quotes = await res.json();
        for (const [sym, q] of Object.entries(quotes)) {
          const bidEl    = $('q_bid_'    + sym);
          const askEl    = $('q_ask_'    + sym);
          const spreadEl = $('q_spread_' + sym);
          const timeEl   = $('q_time_'   + sym);
          if (!bidEl) continue;
          const bid = parseFloat(q.bid);
          const ask = parseFloat(q.ask);
          const digits = calcDigits(bid, sym);
          bidEl.innerText = isNaN(bid) ? '--' : bid.toFixed(digits);
          askEl.innerText = isNaN(ask) ? '--' : ask.toFixed(digits);
          if (spreadEl) spreadEl.innerText = q.spread != null ? '点差: ' + q.spread : '点差: --';
          if (timeEl)   timeEl.innerText   = q.ts ? new Date(q.ts * 1000).toLocaleTimeString('en-US', {hour12:false}) : '--';
        }
      } catch(e) {}
    }

    let _successTimer = null;
    function showSuccess(type) {
      const overlay = $('successOverlay');
      const label   = $('successLabel');
      const sub     = $('successSub');
      const ring    = $('ringProgress');
      const tick    = $('successTick');
      overlay.classList.remove('show');
      ring.classList.remove('buy-ring','close-ring');
      tick.classList.remove('buy-tick','close-tick');
      void overlay.offsetWidth;
      if (type === 'close') {
        label.innerText = '平仓成功';
        sub.innerText   = '平仓指令已发送至 MT4';
        ring.classList.add('close-ring');
        tick.classList.add('close-tick');
      } else if (type === 'sell') {
        label.innerText = '做空成功';
        sub.innerText   = '卖出指令已发送至 MT4';
        ring.classList.add('buy-ring');
        tick.classList.add('buy-tick');
      } else {
        label.innerText = '下单成功';
        sub.innerText   = '买入指令已发送至 MT4';
        ring.classList.add('buy-ring');
        tick.classList.add('buy-tick');
      }
      overlay.classList.add('show');
      clearTimeout(_successTimer);
      _successTimer = setTimeout(hideSuccess, 1800);
    }

    function hideSuccess() {
      clearTimeout(_successTimer);
      $('successOverlay').classList.remove('show');
    }

    let _activeTab = 'quotes';

    async function refreshData() {
        try {
            const sym = $('tradeSym').innerText;
            const res = await fetch(`/api/latest_status?symbol=${sym}`);
            if(!res.ok) {
                ['valBalance','valEquity','valFreeMargin','valHistBalance','valProfit'].forEach(id => { if($(id)) $(id).innerText = ''; });
                return;
            }
            const data = await res.json();
            const hasData = data && (data.balance !== undefined || data.equity !== undefined);
            if(hasData) {
                $('valBalance').innerText    = fmtNum(data.balance, 2);
                $('valEquity').innerText     = fmtNum(data.equity, 2);
                $('valFreeMargin').innerText = fmtNum(data.free_margin, 2);
                $('valHistBalance').innerText= fmtNum(data.balance, 2);
                $('valProfit').innerText     = fmtNum(data.daily_pnl, 2);
            } else {
                ['valBalance','valEquity','valFreeMargin','valHistBalance','valProfit'].forEach(id => { if($(id)) $(id).innerText = ''; });
            }
            if(data) {
                if(data.latest_quote) {
                    const bid = parseFloat(data.latest_quote.bid);
                    const ask = parseFloat(data.latest_quote.ask);
                    const dg  = calcDigits(bid, sym);
                    window.quantState.price = bid;
                    $('tBid').innerText = isNaN(bid) ? '--' : bid.toFixed(dg);
                    $('tAsk').innerText = isNaN(ask) ? '--' : ask.toFixed(dg);
                    if($('q_bid_'+sym)) $('q_bid_'+sym).innerText = isNaN(bid) ? '--' : bid.toFixed(dg);
                    if($('q_ask_'+sym)) $('q_ask_'+sym).innerText = isNaN(ask) ? '--' : ask.toFixed(dg);
                }
                updatePositionsList(data.positions || []);
                const pendingRes = await fetch('/api/pending_commands');
                if(pendingRes.ok) {
                    const pendingData = await pendingRes.json();
                    updatePendingOrdersList(pendingData.commands || []);
                }
                if(_activeTab === 'history') fetchHistoryTrades();
            }
        } catch(e) {
            ['valBalance','valEquity','valFreeMargin','valHistBalance','valProfit'].forEach(id => { if($(id)) $(id).innerText = ''; });
        }
    }

    function updatePositionsList(positions) {
        let html = '';
        (positions || []).forEach(pos => {
            const side = (pos.side || '').toLowerCase();
            const isBuy = side === 'buy';
            const sym   = pos.symbol || '';
            const symDigits = calcDigits(parseFloat(pos.open_price) || parseFloat(pos.current_price) || 1);
            const openPrice    = isNaN(parseFloat(pos.open_price))    ? '--' : parseFloat(pos.open_price).toFixed(symDigits);
            const currentPrice = isNaN(parseFloat(pos.current_price)) ? '--' : parseFloat(pos.current_price).toFixed(symDigits);
            const ticket = pos.ticket != null ? pos.ticket : '';
            const tp     = pos.tp   != null ? pos.tp   : 0;
            const sl     = pos.sl   != null ? pos.sl   : 0;
            const lots   = pos.lots != null ? pos.lots : 0;
            html += `
            <div class="pos-item" onclick="openModifyOrder('${ticket}', '${tp}', '${sl}', '${sym}', '${lots}')">
              <div class="p-row1">
                <div><span class="p-sym">${sym}</span>, <span class="p-type ${isBuy?'buy':'sell'}">${pos.side||''}</span> <span class="p-lots">${lots}</span></div>
                <div class="p-profit ${(pos.profit||0)>=0?'blue':'red'}">${fmtNum(pos.profit, 2)}</div>
              </div>
              <div class="p-row2">
                <span>${openPrice} → ${currentPrice}</span>
                <span>#${ticket}</span>
              </div>
            </div>`;
        });
        $('list-positions').innerHTML = html || '<div style="padding:15px;text-align:center;color:#888;">暂无持仓</div>';
    }

    function updatePendingOrdersList(commands) {
        const visible = (commands || []).filter(c => c.action !== 'quote');
        let html = '';
        visible.forEach(cmd => {
            const isBuy = (cmd.side||'').toLowerCase() === 'buy';
            html += `
            <div class="pos-item">
              <div class="p-row1">
                <div><span class="p-sym">${cmd.symbol}</span>, <span class="p-type ${isBuy?'buy':'sell'}">${cmd.action} ${cmd.side||''}</span> <span class="p-lots">${cmd.volume}</span></div>
                <div class="p-profit" style="color:var(--red)" onclick="window.API.cancelCommand('${cmd.id}')">撤单</div>
              </div>
              <div class="p-row2">
                <span>${cmd.price || 'Market'}</span>
                <span>${new Date(cmd.created_at*1000).toLocaleTimeString()}</span>
              </div>
            </div>`;
        });
        $('list-orders').innerHTML = html || '<div style="padding:15px;text-align:center;color:#888;">暂无订单</div>';
    }

    async function fetchHistoryTrades() {
        try {
            const res = await fetch('/api/history_trades?limit=50');
            const data = await res.json();
            renderHistoryList(data.trades || []);
        } catch(e) {}
    }

    function renderHistoryList(trades) {
        let html = '';
        trades.forEach(t => {
            if(String(t.cmd_id).startsWith('q_')) return;
            let msgExtra = {};
            try {
                const raw = t.message || '';
                if(raw.startsWith('{')) msgExtra = JSON.parse(raw);
            } catch(e) {}
            const pick = (...keys) => {
                for(const k of keys){
                    if(t[k] != null && t[k] !== '') return t[k];
                    if(msgExtra[k] != null && msgExtra[k] !== '') return msgExtra[k];
                }
                return null;
            };
            const sym        = pick('symbol') || '--';
            const side       = (pick('side','type','action') || '').toLowerCase();
            const vol        = pick('volume','lots');
            const openPrice  = pick('open_price','open');
            const closePrice = pick('close_price','price','close');
            const openTime   = pick('open_time');
            const profit     = pick('profit','pnl');
            const ticket     = pick('ticket');
            const ok         = t.ok;
            const sideLabel  = side === 'buy' ? 'BUY' : side === 'sell' ? 'SELL' : side.toUpperCase() || '?';
            const sideCls    = (side === 'buy') ? 'buy' : (side === 'sell') ? 'sell' : 'ok';
            let profitHtml = '--';
            if(profit != null){
                const pNum   = parseFloat(profit);
                const pCls   = pNum > 0 ? 'pos' : pNum < 0 ? 'neg' : 'zero';
                const pSign  = pNum > 0 ? '+' : '';
                profitHtml   = `<span class="h-profit ${pCls}">${pSign}${pNum.toFixed(2)}</span>`;
            }
            const fmtTime = (ts) => {
                if(!ts) return '--';
                const n = typeof ts === 'number' ? ts : parseInt(ts);
                if(isNaN(n)) return String(ts);
                return new Date(n < 1e12 ? n*1000 : n).toLocaleString('zh-CN', {
                    month:'2-digit', day:'2-digit',
                    hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false
                });
            };
            const fmtP = (p) => {
                if(p == null) return '--';
                const n = parseFloat(p);
                return isNaN(n) ? '--' : n.toFixed(n >= 100 ? 2 : 4);
            };
            html += `
            <div class="h-card">
              <div class="h-row1">
                <div>
                  <span class="h-sym">${sym}</span>
                  <span class="h-badge ${sideCls}">${sideLabel}</span>
                  <span class="h-badge ${ok?'ok':'fail'}">${ok?'成交':'失败'}</span>
                  ${vol != null ? `<span style="font-size:13px;color:var(--muted);margin-left:4px">${parseFloat(vol)}手</span>` : ''}
                </div>
                <div>${profitHtml}</div>
              </div>
              <div class="h-row2">
                <span>开仓: ${fmtP(openPrice)} → 平仓: ${fmtP(closePrice)}</span>
                <span>#${ticket || t.cmd_id}</span>
              </div>
              <div class="h-row3">
                <span>开仓时间: ${fmtTime(openTime)}</span>
                &nbsp;·&nbsp;
                <span>报告时间: ${t.received_at || '--'}</span>
              </div>
              ${t.error ? `<div style="font-size:11px;color:var(--red);margin-top:3px">错误: ${t.error}</div>` : ''}
            </div>`;
        });
        $('list-history').innerHTML = html || '<div style="padding:15px;text-align:center;color:#888;">暂无记录</div>';
    }

    // ★ FIX #1: openModifyOrder — 确保 lots 正确存储，支持字符串和数字
    window.openModifyOrder = function(ticket, tp, sl, symbol, lots) {
        window.quantState.currentModifyTicket = ticket;
        window.quantState.currentModifySymbol = symbol;
        // ★ 确保 lots 转为数字，0 时用输入框值兜底
        const parsedLots = parseFloat(lots);
        window.quantState.currentModifyLots = isNaN(parsedLots) ? 0 : parsedLots;
        $('modTpPrice').value = tp && tp !== 'undefined' && tp !== '0' ? tp : '';
        $('modSlPrice').value = sl && sl !== 'undefined' && sl !== '0' ? sl : '';
        $('modifyMask').style.display = 'flex';
    };

    window.submitModifyOrder = function() {
        if(!window.quantState.currentModifyTicket) {
            alert('未选中持仓，请先点击持仓行');
            return;
        }
        const tp = parseFloat($('modTpPrice').value) || 0;
        const sl = parseFloat($('modSlPrice').value) || 0;
        window.API.modifyPosition(window.quantState.currentModifyTicket, tp, sl)
        .then(res => {
            if(res && res.success) { showSuccess('buy'); $('modifyMask').style.display='none'; refreshData(); }
            else alert('修改失败: ' + ((res && res.message) || '请检查网络或重试'));
        });
    };
    
    // ★ FIX #1: closePosition — lots=0 时从手数输入框兜底，确保平仓命令有效
    window.closePosition = function() {
        if(!window.quantState.currentModifyTicket) {
            alert('未选中持仓，请先点击持仓行');
            return;
        }
        const sym    = window.quantState.currentModifySymbol || $('tradeSym').innerText;
        const ticket = window.quantState.currentModifyTicket;
        // ★ lots=0 或未设置时，fallback 到手数输入框，确保不传 0
        const lots = window.quantState.currentModifyLots > 0
                     ? window.quantState.currentModifyLots
                     : (parseFloat($('inpLots').value) || 0.01);

        window.API.submitOrder(sym, 'CLOSE', 'market', 0, 20, lots, { ticket: ticket })
        .then(res => {
            if(res && res.success) {
                showSuccess('close');
                $('modifyMask').style.display = 'none';
                refreshData();
            } else {
                alert('平仓失败: ' + ((res && res.message) || '请检查网络或重试'));
            }
        }).catch(e => {
            alert('网络错误，请重试');
            console.error(e);
        });
    };

    // ======================== K线绘制引擎 ========================
    let _kBars = [], _kTF = '5min', _kSym = 'XAUUSD', _kL = null;

    function kSetTF(btn) {
      document.querySelectorAll('.kline-tf').forEach(b => b.classList.remove('on'));
      btn.classList.add('on');
      _kTF = btn.dataset.tf;
      kFetch();
    }

    async function kFetch() {
      const sym = $('tradeSym') ? $('tradeSym').innerText : _kSym;
      _kSym = sym;
      if ($('klineSymLabel')) $('klineSymLabel').innerText = sym + ' K线';
      try {
        const r = await fetch('/api/kline?symbol=' + encodeURIComponent(sym) + '&tf=' + encodeURIComponent(_kTF));
        const d = await r.json();
        if (d.bars && d.bars.length > 0) { _kBars = d.bars; kDraw(_kBars); }
        else { _kBars = []; kDrawEmpty(); }
      } catch(e) { kDrawEmpty(); }
    }

    function kNiceScale(lo, hi, maxTicks) {
      if (lo === hi) { const d = Math.abs(lo) * 0.01 || 1; lo -= d; hi += d; }
      const range = hi - lo, pad = range * 0.08;
      let mn = lo - pad, mx = hi + pad;
      const rs = (mx - mn) / (maxTicks - 1);
      const mg = Math.pow(10, Math.floor(Math.log10(rs)));
      const res = rs / mg;
      let ns;
      if (res <= 1) ns = mg; else if (res <= 2) ns = 2*mg;
      else if (res <= 2.5) ns = 2.5*mg; else if (res <= 5) ns = 5*mg; else ns = 10*mg;
      const tI = Math.floor(mn / ns) * ns, tA = Math.ceil(mx / ns) * ns, tks = [];
      for (let v = tI; v <= tA + ns * 0.5; v += ns) tks.push(v);
      return { tI, tA, ns, tks };
    }

    function kDraw(bars) {
      const cv = $('klineCanvas'); if (!cv) return;
      const ctx = cv.getContext('2d');
      const dpr = devicePixelRatio || 1;
      const w = cv.offsetWidth, h = cv.offsetHeight;
      if (w <= 0 || h <= 0) return;
      cv.width = w * dpr; cv.height = h * dpr;
      ctx.scale(dpr, dpr); ctx.clearRect(0, 0, w, h);
      if (!bars || !bars.length) { kDrawEmpty(); return; }

      const PL = 8, PR = 68, PT = 14, PB = 22;
      const cW = w - PL - PR, cH = h - PT - PB;
      if (cW <= 0 || cH <= 0) return;

      const vn = Math.max(5, Math.min(bars.length, Math.floor(cW / 6), 80));
      const vb = bars.slice(-vn), n = vb.length;
      let dMin = Infinity, dMax = -Infinity;
      for (const b of vb) { if (b[2] > dMax) dMax = b[2]; if (b[3] < dMin) dMin = b[3]; }

      const D = calcDigits(null, _kSym);
      const sc = kNiceScale(dMin, dMax, 6);
      const { tI, tA, tks } = sc;
      const yR = tA - tI || 1;
      const p2y = p => PT + cH * (1 - (p - tI) / yR);
      const y2p = y => tI + (1 - (y - PT) / cH) * yR;
      const bT = cW / n, gap = Math.max(1, Math.round(bT * 0.2));
      const bW = Math.max(1, Math.floor(bT - gap)), hB = bW / 2;
      const bx = i => PL + (i + 0.5) * bT;

      _kL = { PL, PR, PT, PB, cW, cH, n, bT, tI, tA, yR, p2y, y2p, bx, D, vb };

      const G = '#34c759', R = '#ff3b30', gridC = 'rgba(0,0,0,0.05)', axC = '#8e8e93';

      ctx.font = '10px "SF Mono",Menlo,monospace';
      ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
      for (const t of tks) {
        const y = p2y(t);
        if (y < PT - 2 || y > PT + cH + 2) continue;
        ctx.strokeStyle = gridC; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(PL, Math.round(y) + 0.5); ctx.lineTo(PL + cW, Math.round(y) + 0.5); ctx.stroke();
        ctx.fillStyle = axC; ctx.fillText(t.toFixed(D), PL + cW + 6, y);
      }

      for (let i = 0; i < n; i++) {
        const b = vb[i], o = b[1], hi = b[2], lo = b[3], cl = b[4];
        const up = cl >= o, col = up ? G : R, x = bx(i);
        ctx.strokeStyle = col; ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(Math.round(x) + 0.5, Math.round(p2y(hi)));
        ctx.lineTo(Math.round(x) + 0.5, Math.round(p2y(lo)));
        ctx.stroke();
        const yO = p2y(o), yC = p2y(cl);
        const bt = Math.min(yO, yC), bb = Math.max(yO, yC);
        ctx.fillStyle = col;
        ctx.fillRect(Math.round(x - hB), Math.round(bt), bW, Math.max(1, bb - bt));
      }

      if (n > 0) {
        const lc = vb[n-1][4], up = lc >= vb[n-1][1], col = up ? G : R;
        const yL = p2y(lc);
        ctx.setLineDash([4, 3]); ctx.strokeStyle = col; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(PL, Math.round(yL) + 0.5); ctx.lineTo(PL + cW, Math.round(yL) + 0.5); ctx.stroke();
        ctx.setLineDash([]);
        const tW = PR - 4, tHt = 16, tX = PL + cW + 2, tY = Math.round(yL) - tHt / 2;
        ctx.fillStyle = col;
        ctx.beginPath(); ctx.roundRect(tX, tY, tW, tHt, 3); ctx.fill();
        ctx.fillStyle = '#fff'; ctx.font = 'bold 10px "SF Mono",Menlo,monospace';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(lc.toFixed(D), tX + tW / 2, Math.round(yL));
      }

      ctx.fillStyle = axC; ctx.font = '10px "SF Mono",Menlo,monospace';
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      let lX = -Infinity;
      for (let i = 0; i < n; i++) {
        const ts = vb[i][0], x = bx(i);
        if (x - lX < 55) continue;
        const d = new Date(ts + 8 * 3600000);
        const lb = _kTF === '1hour'
          ? (d.getUTCMonth()+1)+'/'+d.getUTCDate()+' '+String(d.getUTCHours()).padStart(2,'0')+':00'
          : String(d.getUTCHours()).padStart(2,'0')+':'+String(d.getUTCMinutes()).padStart(2,'0');
        ctx.fillStyle = axC; ctx.fillText(lb, x, PT + cH + 5); lX = x;
      }
      kClearCursor();
    }

    function kDrawEmpty() {
      const cv = $('klineCanvas'); if (!cv) return;
      const ctx = cv.getContext('2d'), dpr = devicePixelRatio || 1;
      const w = cv.offsetWidth, h = cv.offsetHeight;
      cv.width = w * dpr; cv.height = h * dpr; ctx.scale(dpr, dpr); ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = '#8e8e93'; ctx.font = '13px sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText('暂无 K 线数据（等待 Tick 推送）', w / 2, h / 2);
      kClearCursor(); _kL = null;
    }

    function kClearCursor() {
      const cv = $('klineCursor'); if (!cv) return;
      const dpr = devicePixelRatio || 1;
      cv.width = cv.offsetWidth * dpr; cv.height = cv.offsetHeight * dpr;
      cv.getContext('2d').scale(dpr, dpr);
      if ($('klineOHLC')) $('klineOHLC').innerText = '';
    }

    function kDrawCursor(mx, my) {
      const cv = $('klineCursor'); if (!cv || !_kL) return;
      const dpr = devicePixelRatio || 1;
      const w = cv.offsetWidth, h = cv.offsetHeight;
      cv.width = w * dpr; cv.height = h * dpr;
      const ctx = cv.getContext('2d'); ctx.scale(dpr, dpr);
      const { PL, PT, cW, cH, n, bT, D, vb, p2y, y2p, bx } = _kL;
      const cx = Math.max(PL, Math.min(mx, PL + cW));
      const cy = Math.max(PT, Math.min(my, PT + cH));
      const idx = Math.max(0, Math.min(Math.round((cx - PL) / bT - 0.5), n - 1));
      const sx = bx(idx);
      ctx.setLineDash([3, 3]); ctx.strokeStyle = 'rgba(0,0,0,0.2)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(Math.round(sx) + 0.5, PT); ctx.lineTo(Math.round(sx) + 0.5, PT + cH); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(PL, Math.round(cy) + 0.5); ctx.lineTo(PL + cW, Math.round(cy) + 0.5); ctx.stroke();
      ctx.setLineDash([]);
      const pr = y2p(cy);
      const tW2 = 60, tH2 = 16, tX2 = PL + cW + 2, tY2 = Math.round(cy) - tH2 / 2;
      ctx.fillStyle = '#333';
      ctx.beginPath(); ctx.roundRect(tX2, tY2, tW2, tH2, 3); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.font = '10px "SF Mono",Menlo,monospace';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(pr.toFixed(D), tX2 + tW2 / 2, Math.round(cy));
      if (idx >= 0 && idx < n && $('klineOHLC')) {
        const b = vb[idx], up = b[4] >= b[1], col = up ? '#34c759' : '#ff3b30';
        $('klineOHLC').innerHTML =
          `<span style="color:${col}">O:${b[1].toFixed(D)} H:${b[2].toFixed(D)} L:${b[3].toFixed(D)} C:${b[4].toFixed(D)}</span>`;
      }
    }

    (function() {
      const wr = $('klineWrap'); if (!wr) return;
      const pos = e => {
        const r = wr.getBoundingClientRect();
        return e.touches
          ? { x: e.touches[0].clientX - r.left, y: e.touches[0].clientY - r.top }
          : { x: e.clientX - r.left, y: e.clientY - r.top };
      };
      wr.addEventListener('mousemove', e => { const p = pos(e); kDrawCursor(p.x, p.y); });
      wr.addEventListener('mouseleave', kClearCursor);
      wr.addEventListener('touchmove', e => { e.preventDefault(); const p = pos(e); kDrawCursor(p.x, p.y); }, { passive: false });
      wr.addEventListener('touchend', kClearCursor);
    })();

    const _origSelectSymbol = window.selectSymbol;
    window.selectSymbol = function(name, desc) {
      _origSelectSymbol(name, desc);
      kFetch();
    };

    window.addEventListener('resize', () => {
      clearTimeout(window._krt);
      window._krt = setTimeout(() => { if (_kBars.length) kDraw(_kBars); else kDrawEmpty(); }, 100);
    });

    setInterval(kFetch, 1500);
  </script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

# ==================== API 接口实现 (v1) ====================

@app.route('/api/v1/order', methods=['POST'])
def submit_order_v1():
    global cmd_counter
    
    if is_restricted_time():
        return jsonify({"success": False, "message": "非交易时段 (0:00-5:00)，禁止下单"}), 403

    data = request.json
    if not data:
        return jsonify({"success": False, "message": "请求体为空或非 JSON"}), 400

    print(f"[ORDER] Recv: {json.dumps(data)}")
    
    symbol = norm_symbol(data.get('symbol', ''))
    side_raw = data.get('side', '')
    cmd_type_raw = data.get('type', 'market')
    
    if side_raw != 'QUOTE' and side_raw != 'CLOSE' and cmd_type_raw != 'quote':
        account = None
        current_equity = 0
        day_start_equity = 0
        with history_lock:
            if history_status and isinstance(history_status[0].get("parsed"), dict):
                parsed = history_status[0]["parsed"]
                account = norm_str(parsed.get("account"))
                current_equity = parsed.get("equity", 0)
                day_start_equity = parsed.get("day_start_equity", 0)
        if account:
            allowed, msg, status_type = check_risk_status(account, current_equity, day_start_equity)
            if not allowed:
                print(f"[RISK] Order rejected: {msg}")
                return jsonify({"success": False, "message": msg, "risk_status": status_type}), 403

    if side_raw == 'CLOSE':
        ticket = str(data.get("ticket", ""))
        with risk_lock:
            if ticket in risk_state["locked_tickets"]:
                return jsonify({"success": False, "message": "该仓位已锁定，禁止手动平仓"}), 403

    # QUOTE 命令快速放行
    if side_raw == 'QUOTE' or cmd_type_raw == 'quote':
        now = int(time.time())
        cmd = {
            "id": "q_" + generate_unique_cmd_id(),
            "nonce": generate_nonce(),
            "created_at": now,
            "ttl_sec": 10,
            "symbol": symbol,
            "action": "quote",
            "account": ""
        }
        with history_lock:
            if history_status and isinstance(history_status[0].get("parsed"), dict):
                cmd["account"] = norm_str(history_status[0]["parsed"].get("account"))
        with commands_lock:
            commands.append(cmd)
        return jsonify({"success": True, "message": "报价请求已发送", "order": cmd})

    # ★ FIX #3: lots 计算 — 不再依赖断裂的 marginPct 链路，直接用前端传的 lots
    lots = float(data.get('lots', 0) or 0)
    
    # 如果前端传了 marginPct 且有行情价格，才走 margin->lots 转换（可选路径）
    inp_margin_usd = float(data.get('marginPct', 0) or 0)
    if lots <= 0 and inp_margin_usd > 0:
        current_price = get_latest_price(symbol) or float(data.get('price', 0) or 0)
        if current_price > 0:
            lots = calc_lots_from_margin_usd(symbol, inp_margin_usd, {"equity": 0})
            if 0 < lots < 0.01:
                lots = 0.01
            else:
                lots = round(lots, 2)

    # ★ FIX #3: lots 仍为 0 时使用最小手数兜底，不再直接拒绝（避免因价格未加载误杀正常下单）
    if lots <= 0 and side_raw != 'CLOSE':
        lots = 0.01
        print(f"[ORDER][WARN] lots was 0 or missing, using minimum 0.01")

    # 构造命令
    now = int(time.time())
    ttl_mins = float(data.get('inpTTL', 0) or 0)
    if ttl_mins <= 0:
        ttl_mins = 10
    ttl_sec = int(ttl_mins * 60)
    
    cmd = {
        "id": generate_unique_cmd_id(),
        "nonce": generate_nonce(),
        "created_at": now,
        "ttl_sec": ttl_sec,
        "symbol": symbol,
        "volume": lots,
        "lots": lots
    }
    
    account = None
    with history_lock:
        if history_status and isinstance(history_status[0].get("parsed"), dict):
            account = norm_str(history_status[0]["parsed"].get("account"))
        if not account and history_report:
            for rep in history_report:
                if rep.get("parsed") and rep["parsed"].get("account"):
                    account = norm_str(rep["parsed"].get("account"))
                    break
    
    if not account:
        print("[WARN] 无法获取当前账户信息，允许空账户下单")
        account = ""
    cmd["account"] = account

    # ★ FIX #1: 平仓命令补全 side/volume/lots 字段，EA 必需
    if side_raw == 'CLOSE':
        cmd["action"] = "close"
        cmd["side"] = "close"       # ★ EA 识别平仓动作
        raw_ticket = data.get("ticket")
        if raw_ticket is None:
            return jsonify({"success": False, "message": "平仓指令缺少 ticket 字段"}), 400
        try:
            cmd["ticket"] = int(raw_ticket)
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": f"ticket 格式无效: {raw_ticket}"}), 400
        # ★ 确保 lots > 0，0 会导致 EA 拒绝执行
        close_lots = float(data.get('lots', 0) or 0)
        if close_lots <= 0:
            close_lots = 0.01
            print(f"[ORDER][CLOSE][WARN] lots was 0, using 0.01 for ticket={cmd['ticket']}")
        cmd["volume"] = close_lots
        cmd["lots"]   = close_lots
    elif "limit" in cmd_type_raw:
        cmd["action"] = "limit"
        cmd["side"] = "buy" if side_raw.upper() == "BUY" else "sell"
        price = float(data.get('inpPrice', 0) or 0)
        if price <= 0:
             return jsonify({"success": False, "message": "限价单必须输入触发价格"}), 400
        cmd["price"] = price
    else:
        cmd["action"] = "market"
        cmd["side"] = "buy" if side_raw.upper() == "BUY" else "sell"
    
    tp = float(data.get('inpTp', 0) or 0)
    sl = float(data.get('inpSl', 0) or 0)
    if tp > 0: cmd["tp"] = tp
    if sl > 0: cmd["sl"] = sl
    
    with commands_lock:
        commands.append(cmd)
    
    print(f"[ORDER][QUEUE] action={cmd.get('action')} side={cmd.get('side')} symbol={symbol} lots={lots} account={account} id={cmd['id']}")
    return jsonify({
        "success": True, 
        "message": "指令已发送到队列",
        "order": cmd
    })

@app.route('/api/v1/position/modify', methods=['POST'])
def modify_position_v1():
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "请求体为空"}), 400

    position_id = data.get('positionId')
    if position_id:
        with risk_lock:
            if str(position_id) in risk_state["locked_tickets"]:
                return jsonify({"success": False, "message": "该仓位已锁定，禁止修改"}), 403

    tp = float(data.get('tpPrice', 0) or 0)
    sl = float(data.get('slPrice', 0) or 0)
    now = int(time.time())
    
    if position_id is None:
        return jsonify({"success": False, "message": "修改指令缺少 positionId 字段"}), 400
    try:
        ticket_int = int(position_id)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": f"positionId 格式无效: {position_id}"}), 400

    cmd = {
        "id": generate_unique_cmd_id(),
        "nonce": generate_nonce(),
        "created_at": now,
        "ttl_sec": 60,
        "action": "modify",
        "ticket": ticket_int,
        "tp": tp,
        "sl": sl
    }
    
    with history_lock:
        if history_status and isinstance(history_status[0].get("parsed"), dict):
            account = norm_str(history_status[0]["parsed"].get("account"))
            if account:
                cmd["account"] = account

    with commands_lock:
        commands.append(cmd)
        
    return jsonify({"success": True, "message": "修改指令已发送"})

@app.route('/api/v1/position/lock', methods=['POST'])
def lock_position_v1():
    data = request.json
    position_id = data.get('positionId')
    print(f"【API】执行锁仓: {position_id}")
    target_pos = None
    with history_lock:
        if history_positions and history_positions[0].get("parsed"):
            positions = history_positions[0]["parsed"].get("positions", [])
            for p in positions:
                if str(p.get("ticket")) == str(position_id):
                    target_pos = p
                    break
    if not target_pos:
        return jsonify({"success": False, "message": "未找到持仓，无法锁仓"}), 404
    global risk_state
    with risk_lock:
        risk_state["locked_tickets"].add(str(position_id))
    return jsonify({"success": True, "message": "仓位已锁定 (禁止手动平仓/修改，等待止盈止损结算)"})

@app.route('/api/v1/calendar', methods=['GET'])
def get_calendar_pnl_v1():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if not year or not month:
        now = datetime.now()
        year = now.year
        month = now.month
    with daily_stats_lock:
        stats = load_daily_stats()
    data = {}
    prefix = f"{year}-{month:02d}"
    for date_str, pnl in stats.items():
        if date_str.startswith(prefix):
            try:
                day = int(date_str.split("-")[2])
                data[day] = pnl
            except:
                continue
    return jsonify(data)

# ==================== 旧版 echo ====================
@app.route("/web/api/echo", methods=["POST"])
def mt4_webhook_echo():
    raw_body = request.get_data(as_text=True)
    client_ip = get_client_ip()
    headers_dict = dict(request.headers)
    store_mt4_data(raw_body, client_ip, headers_dict)

    response_lines = []
    with commands_lock:
        if commands:
            for cmd in commands:
                side = cmd.get("side", "")
                symbol = cmd.get("symbol", "")
                volume = cmd.get("volume", "")
                base = f"{side},{symbol},{volume}"
                sl = cmd.get("sl_price")
                tp = cmd.get("tp_price")
                if sl is not None and tp is not None:
                    response_lines.append(f"{base},{sl},{tp}")
                elif sl is not None:
                    response_lines.append(f"{base},{sl},0")
                elif tp is not None:
                    response_lines.append(f"{base},0,{tp}")
                else:
                    response_lines.append(base)
            commands.clear()

    if response_lines:
        return "\n".join(response_lines), 200, {"Content-Type": "text/plain; charset=utf-8"}
    return "NOCOMMAND", 200, {"Content-Type": "text/plain; charset=utf-8"}

# ==================== MT4 专用接口 ====================
@app.route("/web/api/mt4/commands", methods=["POST"])
def mt4_commands():
    if is_restricted_time():
        return jsonify({"commands": [], "paused": paused}), 200

    raw_body = request.get_data(as_text=True)
    client_ip = get_client_ip()
    headers_dict = dict(request.headers)

    parsed_json, _ = store_mt4_data(raw_body, client_ip, headers_dict)

    if parsed_json is None:
        return jsonify({"error": "Invalid JSON", "commands": []}), 400

    account = parsed_json.get("account") if isinstance(parsed_json, dict) else None
    account = norm_str(account)

    with commands_lock:
        account_commands = []
        remaining_commands = []
        for cmd in commands:
            cmd_acc = cmd.get("account")
            cmd_acc_normalized = norm_str(cmd_acc)
            request_acc_normalized = norm_str(account)
            if request_acc_normalized == "":
                if cmd_acc is None or cmd_acc_normalized == "":
                    account_commands.append(cmd)
                else:
                    remaining_commands.append(cmd)
            else:
                if cmd_acc is None or cmd_acc_normalized == "" or cmd_acc_normalized == request_acc_normalized:
                    account_commands.append(cmd)
                else:
                    remaining_commands.append(cmd)
        commands[:] = remaining_commands

    print("[SEND CMDS]:", json.dumps(account_commands, ensure_ascii=False))

    with pause_lock:
        current_paused = paused

    return jsonify({"commands": account_commands, "paused": current_paused}), 200

@app.route("/api/pending_commands", methods=["GET"])
def api_pending_commands():
    with commands_lock:
        visible_commands = [c for c in commands if c.get("action") != "quote"]
        return jsonify({"commands": visible_commands})

@app.route("/web/api/mt4/status", methods=["POST"])
def mt4_status():
    raw_body = request.get_data(as_text=True)
    client_ip = get_client_ip()
    headers_dict = dict(request.headers)
    _, record = store_mt4_data(raw_body, client_ip, headers_dict)
    update_daily_stats_from_record(record)
    return "OK", 200

@app.route("/web/api/mt4/positions", methods=["POST"])
def mt4_positions():
    raw_body = request.get_data(as_text=True)
    client_ip = get_client_ip()
    headers_dict = dict(request.headers)
    store_mt4_data(raw_body, client_ip, headers_dict)
    return "OK", 200

@app.route("/web/api/mt4/report", methods=["POST"])
def mt4_report():
    raw_body = request.get_data(as_text=True)
    client_ip = get_client_ip()
    headers_dict = dict(request.headers)
    store_mt4_data(raw_body, client_ip, headers_dict)
    return "OK", 200

@app.route("/web/api/mt4/quote", methods=["POST"])
def mt4_quote():
    raw_body = request.get_data(as_text=True)
    client_ip = get_client_ip()
    headers_dict = dict(request.headers)
    store_mt4_data(raw_body, client_ip, headers_dict)
    return "OK", 200

# ==================== Tick 推送接口 ====================
@app.route('/api/tick', methods=['POST'])
def receive_tick():
    try:
        ticks = request.json
        if not isinstance(ticks, list):
            ticks = [ticks]
        for tick in ticks:
            symbol   = tick.get('symbol')
            bid      = tick.get('bid')
            ask      = tick.get('ask')
            tick_time = tick.get('tick_time')
            if not symbol or bid is None or ask is None: continue
            bf, af = _to_float(bid), _to_float(ask)
            if bf is None or af is None: continue
            if tick_time is not None:
                tft   = float(tick_time)
                ts_ms = int(tft) if tft > 1e12 else int(tft * 1000)
            else:
                ts_ms = int(time.time() * 1000)
            cache_tick_quote(symbol, bf, af, spread=tick.get('spread'), ts=tick_time)
            update_kline(symbol, bf, af, ts_ms)
            quote_msg = json.dumps({"bid": bf, "ask": af})
            record = {
                "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ip": get_client_ip(), "method": "POST", "path": "/api/tick",
                "category": "report", "headers": {}, "body_raw": json.dumps(tick),
                "parsed": {
                    "desc": "QUOTE_DATA", "spread": tick.get('spread', 0),
                    "ts": tick_time, "message": quote_msg,
                    "symbol": symbol, "account": "tick_stream",
                }
            }
            with history_lock:
                history_report.appendleft(record)
        return '', 204
    except Exception as e:
        print(f"Error processing tick: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== 网页发单 ====================
@app.route("/send_command", methods=["POST"])
def send_command():
    if is_restricted_time():
        return redirect(url_for("index"))
    
    account_raw = request.form.get("account", "")
    cmd_type_raw = request.form.get("cmd_type", "MARKET")
    symbol_raw = request.form.get("symbol", "")
    side_raw = request.form.get("side", "")
    volume_raw = request.form.get("volume", "")
    price_raw = request.form.get("price", "")
    sl_raw = request.form.get("sl", "")
    tp_raw = request.form.get("tp", "")
    ticket_raw = request.form.get("ticket", "")
    lots_raw = request.form.get("lots", "")

    account = norm_str(account_raw)
    cmd_type = norm_str(cmd_type_raw).upper()
    symbol = norm_symbol(symbol_raw)
    side_ui = norm_str(side_raw).upper()
    volume = norm_volume(volume_raw)
    sl = norm_volume(sl_raw) if sl_raw else None
    tp = norm_volume(tp_raw) if tp_raw else None
    ticket = norm_str(ticket_raw)
    lots = norm_volume(lots_raw) if lots_raw else None
    price = norm_volume(price_raw) if price_raw else None

    if cmd_type in ("MARKET", "LIMIT"):
        if not symbol:
            return redirect(url_for("index"))
        if side_ui not in ("BUY", "SELL"):
            return redirect(url_for("index"))
        if volume <= 0:
            return redirect(url_for("index"))
        if volume > 5.0:
            return jsonify({"success": False, "message": "单笔手数超过限制 (Max 5.0)"}), 400
    elif cmd_type == "QUOTE":
        pass
    elif cmd_type == "CLOSE":
        if not ticket:
            return redirect(url_for("index"))
    else:
        return redirect(url_for("index"))

    if not account:
        with history_lock:
            if history_status and isinstance(history_status[0].get("parsed"), dict):
                account = norm_str(history_status[0]["parsed"].get("account"))

    now = int(time.time())
    cmd = {
        "id": generate_unique_cmd_id(),
        "nonce": generate_nonce(),
        "created_at": now,
        "ttl_sec": 10,
    }
    if account:
        cmd["account"] = account

    if cmd_type == "MARKET":
        cmd["action"] = "market"
        cmd["symbol"] = symbol
        cmd["side"] = "buy" if side_ui == "BUY" else "sell"
        cmd["volume"] = volume
        cmd["lots"] = volume
        if sl is not None and sl > 0:
            cmd["sl_price"] = sl
            cmd["sl"] = sl
        if tp is not None and tp > 0:
            cmd["tp_price"] = tp
            cmd["tp"] = tp
    elif cmd_type == "LIMIT":
        cmd["action"] = "limit"
        cmd["symbol"] = symbol
        cmd["side"] = "buy" if side_ui == "BUY" else "sell"
        cmd["volume"] = volume
        cmd["lots"] = volume
        cmd["price"] = price
        if sl is not None and sl > 0:
            cmd["sl"] = sl
        if tp is not None and tp > 0:
            cmd["tp"] = tp
    elif cmd_type == "CLOSE":
        cmd["action"] = "close"
        cmd["side"] = "close"
        cmd["ticket"] = int(ticket) if ticket else None
        if lots and lots > 0:
            cmd["lots"] = lots
            cmd["volume"] = lots

    print("[ADD CMD]:", json.dumps(cmd, ensure_ascii=False))
    with commands_lock:
        commands.append(cmd)

    return redirect(url_for("index"))

@app.route("/delete_command/<int:index>", methods=["POST"])
def delete_command(index):
    with commands_lock:
        if 0 <= index < len(commands):
            commands.pop(index)
    return redirect(url_for("index"))

@app.route("/clear_commands", methods=["POST"])
def clear_commands():
    with commands_lock:
        commands.clear()
    return redirect(url_for("index"))

# ==================== 启动 ====================
# ★ FIX #2: threaded=True 解决 EA 轮询阻塞 UI 请求的卡顿问题
#            debug=False 关闭单线程 reloader，必须与 threaded=True 同时设置
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
