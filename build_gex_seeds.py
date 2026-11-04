#!/usr/bin/env python3
# TWMMPRO — GEX PROFILE: constructor de Pine Seeds del perfil Gamma
# Para CADA ticker del universo (MONITOREO 25 + radar 12) calcula el
# perfil GEX con collect_gex_profile.py (CBOE delayed) en modo
# CUMULATIVO hasta el viernes mas cercano, y lo escribe en 7 CSV por
# ticker en formato Pine Seeds (Date,Open,High,Low,Close,Volume),
# que TWMMPRO — GEX PROFILE v3 lee con request.seed: al cambiar de
# simbolo en TradingView, el mapa se carga solo para ese ticker.
#
# CODIFICACION (35 valores, espejo exacto en el Pine v3):
#   <T>_GEX1: Open=HVL      High=C1       Low=P1      Close=cTrans  Volume=pTrans
#   <T>_GEX2: Open=NetGEX   High=C2       Low=C3      Close=C4      Volume=C5
#   <T>_GEX3: Open=C6       High=C7       Low=P2      Close=P3      Volume=P4
#   <T>_GEX4: Open=P5       High=P6       Low=P7      Close=Ab1     Volume=Ab2
#   <T>_GEX5: Open=Ab3      High=D+       Low=D-      Close=COI     Volume=POI
#   <T>_GEX6: Open=AbOI     High=CV       Low=PV      Close=MaxPain Volume=Pivot
#   <T>_GEX7: Open=MM Low   High=MM Up    Low=TotOI   Close=CallOI  Volume=PutOI
#   Sin dato = 0 (el Pine lo trata como nivel apagado).
#
# MAPEOS (igual que Tanuki): BTCUSD usa la cadena de IBIT y los strikes
# se convierten a escala BTC con el factor spot_BTC/spot_IBIT del dia
# (BTC spot de Coinbase). El simbolo seed es el del GRAFICO (BTCUSD).
#
# Uso:
#   python3 build_gex_seeds.py 2026-11-03            -> universo completo
#   python3 build_gex_seeds.py 2026-11-03 SPY QQQ    -> solo esos
# Publicacion (una vez): subir TODOS los *_GEX*.csv de ~/workspace/
# twmmpro/pine-seeds/ al repo publico de GitHub `pine-seeds` y cargar
# "usuario/pine-seeds" en el input del GEX PROFILE v3.
import datetime
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "ordr_options_flow_B"))
from collect_option_profile import fetch as cboe_fetch  # noqa: E402
from collect_gex_profile import analyze_gex  # noqa: E402
from collect_option_profile import parse as opt_parse  # noqa: E402

UNIVERSE = [
    # MONITOREO (25)
    "SPY", "QQQ", "DIA", "IWM", "RSP", "MAGS", "VIX",
    "XLK", "XLV", "XLF", "XLE", "XLI", "XLY", "XLP", "XLC", "XLB",
    "XLU", "XLRE", "IGV", "SOXX",
    "GLD", "SLV", "IBIT", "BTCUSD", "NBIS",
    # Radar (12, sin repetir)
    "MU", "ASTS", "NVDA", "AMD", "TSLA", "PLTR", "MSFT", "MRNA",
    "VZ", "AMZN", "SNDK", "T",
]
# Simbolo de grafico -> simbolo de la cadena CBOE (BTCUSD usa IBIT con
# conversion de escala; VIX usa el prefijo _VIX de CBOE).
UNDERLYING = {"BTCUSD": "IBIT", "VIX": "_VIX"}
FACTOR_TICKERS = {"BTCUSD"}
STRIKE_FIELDS = ["hvl", "c_trans", "p_trans", "max_pain", "pivot",
                 "mm_up", "mm_low", "d_plus", "d_minus", "coi", "poi",
                 "ab_oi", "cv", "pv"]


def btc_spot():
    raw = subprocess.run(["curl", "-sL", "https://api.coinbase.com/v2/prices/BTC-USD/spot"],
                         capture_output=True, check=True).stdout
    return float(json.loads(raw)["data"]["amount"])


def nearest_friday_exp(underlying, today):
    d = cboe_fetch(underlying)
    exps = set()
    for o in d["options"]:
        p = opt_parse(o["option"])
        if p:
            exps.add(p[0])
    future = sorted(e for e in exps if e >= today)
    if not future:
        return None
    fridays = [e for e in future if e.weekday() == 4]
    return fridays[0] if fridays else future[0]


def n(x):
    return 0.0 if x is None else float(x)


def encode(r):
    cw, pw, ab = r["c_walls"], r["p_walls"], r["abs_gex"]
    g = lambda lst, i: n(lst[i]) if i < len(lst) else 0.0  # noqa: E731
    return {
        1: [n(r["hvl"]), g(cw, 0), g(pw, 0), n(r["c_trans"]), n(r["p_trans"])],
        2: [float(r["net_gex_usd_per_1pct_bn"]), g(cw, 1), g(cw, 2), g(cw, 3), g(cw, 4)],
        3: [g(cw, 5), g(cw, 6), g(pw, 1), g(pw, 2), g(pw, 3)],
        4: [g(pw, 4), g(pw, 5), g(pw, 6), g(ab, 0), g(ab, 1)],
        5: [g(ab, 2), n(r["d_plus"]), n(r["d_minus"]), n(r["coi"]), n(r["poi"])],
        6: [n(r["ab_oi"]), n(r["cv"]), n(r["pv"]), n(r["max_pain"]), n(r["pivot"])],
        7: [n(r["mm_low"]), n(r["mm_up"]), float(r["total_oi"]), float(r["call_oi"]), float(r["put_oi"])],
    }


def write_seed(ticker, k, date_str, vals):
    f = HERE / f"{ticker}_GEX{k}.csv"
    row = f"{date_str}," + ",".join(f"{v:.2f}" for v in vals) + "\n"
    if f.exists():
        lines = f.read_text(encoding="utf-8").splitlines(keepends=True)
        if any(l.startswith(date_str) for l in lines):
            lines = [row if l.startswith(date_str) else l for l in lines]
        else:
            lines.append(row)
        f.write_text("".join(lines), encoding="utf-8")
    else:
        f.write_text("Date,Open,High,Low,Close,Volume\n" + row, encoding="utf-8")


def main():
    date_str = sys.argv[1]
    ref = datetime.date.fromisoformat(date_str)
    tickers = [t.upper() for t in sys.argv[2:]] or UNIVERSE
    ok, fail = [], []
    for t in tickers:
        und = UNDERLYING.get(t, t)
        try:
            exp = nearest_friday_exp(und, ref)
            if exp is None:
                raise SystemExit("sin vencimientos futuros")
            r = analyze_gex(und, exp, "cum")
            factor = 1.0
            if t in FACTOR_TICKERS:
                factor = btc_spot() / r["spot_cboe"]
                for f_name in STRIKE_FIELDS:
                    if r.get(f_name) is not None:
                        r[f_name] = round(r[f_name] * factor, 2)
                r["c_walls"] = [round(x * factor, 2) if x is not None else None for x in r["c_walls"]]
                r["p_walls"] = [round(x * factor, 2) if x is not None else None for x in r["p_walls"]]
                r["abs_gex"] = [round(x * factor, 2) if x is not None else None for x in r["abs_gex"]]
            enc = encode(r)
            for k in range(1, 8):
                write_seed(t, k, date_str, enc[k])
            ok.append(t)
            print(f"{t}: spot {r['spot_cboe']} exp {exp} cum · HVL {n(r['hvl'])} C1 {n(r['c_walls'][0])} "
                  f"P1 {n(r['p_walls'][0])} NetGEX {r['net_gex_usd_per_1pct_bn']}" +
                  (f" · factor x{factor:.1f} desde {und}" if factor != 1.0 else ""))
        except Exception as e:
            fail.append(t)
            print(f"{t}: ERROR {e}")
    print(f"OK {len(ok)}: {', '.join(ok)}")
    if fail:
        print(f"FALLO {len(fail)}: {', '.join(fail)}")


if __name__ == "__main__":
    main()
