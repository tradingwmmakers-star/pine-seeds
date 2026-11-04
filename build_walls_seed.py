#!/usr/bin/env python3
# BLOCK ORDR v10 — constructor de seeds de muros de opciones (ruta ORDR-B)
# Fuente: CBOE delayed quotes (cdn.cboe.com), cadena completa por ticker.
# Walls v2 (cercanos al precio, como los de TARGET BLOCKS): dentro de una
# ventana de +/-20% del spot y vencimientos <=45 dias, el strike con mayor
# OI de calls por encima del spot (call wall) y el de puts por debajo
# (put wall). Escribe un CSV por ticker en formato Pine Seeds:
#   <TICKER>_WALLS.csv  con columnas Date,Open,High,Low,Close,Volume
#   Open = put wall | High = call wall | Low = put wall | Close = call wall
#   Volume = PCR por volumen (calls/puts del dia, todas las expiraciones)
# Uso: python3 build_walls_seed.py 2026-10-30 GOOGL SPY QQQ ...
import json, re, subprocess, sys, datetime, pathlib

OUT_DIR = pathlib.Path(__file__).parent
CONTRACT = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")
WINDOW = 0.20
MAX_DAYS = 45

def fetch(ticker):
    url = f"https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json"
    raw = subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", url],
                         capture_output=True, check=True).stdout
    return json.loads(raw)["data"]

def parse(sym):
    m = CONTRACT.match(sym)
    if not m:
        return None
    exp = datetime.datetime.strptime(m.group(2), "%y%m%d").date()
    return exp, m.group(3), int(m.group(4)) / 1000.0

def analyze(ticker, ref_date):
    d = fetch(ticker)
    spot = float(d["current_price"])
    call_vol = put_vol = 0.0
    call_oi, put_oi = {}, {}
    for o in d["options"]:
        p = parse(o["option"])
        if not p:
            continue
        exp, cp, strike = p
        vol = float(o.get("volume") or 0)
        oi = float(o.get("open_interest") or 0)
        if cp == "C":
            call_vol += vol
        else:
            put_vol += vol
        if (exp - ref_date).days <= MAX_DAYS and abs(strike / spot - 1.0) <= WINDOW:
            book = call_oi if cp == "C" else put_oi
            book[strike] = book.get(strike, 0.0) + oi
    pcr = put_vol / call_vol if call_vol > 0 else float("nan")
    cw = max((s for s in call_oi if s > spot), key=lambda s: call_oi[s], default=None)
    pw = max((s for s in put_oi if s < spot), key=lambda s: put_oi[s], default=None)
    return spot, pcr, cw, pw

if __name__ == "__main__":
    date_str = sys.argv[1]
    ref = datetime.date.fromisoformat(date_str)
    tickers = sys.argv[2:]
    for t in tickers:
        try:
            spot, pcr, cw, pw = analyze(t, ref)
        except Exception as e:
            print(f"{t}: ERROR {e}")
            continue
        if cw is None or pw is None:
            print(f"{t}: sin walls en ventana (spot {spot}) cw={cw} pw={pw}")
            continue
        f = OUT_DIR / f"{t}_WALLS.csv"
        header = "Date,Open,High,Low,Close,Volume\n"
        row = f"{date_str},{pw:.2f},{cw:.2f},{pw:.2f},{cw:.2f},{pcr:.3f}\n"
        if f.exists():
            lines = f.read_text(encoding="utf-8").splitlines(keepends=True)
            if any(l.startswith(date_str) for l in lines):
                lines = [row if l.startswith(date_str) else l for l in lines]
            else:
                lines.append(row)
            f.write_text("".join(lines), encoding="utf-8")
        else:
            f.write_text(header + row, encoding="utf-8")
        print(f"{t}: spot {spot} call_wall {cw} put_wall {pw} pcr {pcr:.3f} -> {f.name}")
