# pine-seeds — datos de opciones para los indicadores TWMMPRO

## GEX PROFILE v3/v4 — perfil Gamma por ticker (259 CSV)

Un perfil por ticker para los 37 símbolos (MONITOREO 25 + radar 12):
7 archivos `<TICKER>_GEX1..7.csv` por ticker, misma fila de fecha en
todos, generados por `build_gex_seeds.py` (perfil CUMULATIVO hasta el
viernes más cercano, cadena CBOE delayed, método en
`ordr_options_flow_B/collect_gex_profile.py`; BTCUSD usa la cadena de
IBIT convertida a escala BTC). La codificación de los 35 valores está
documentada en la cabecera de `build_gex_seeds.py` y es espejo exacto
del bloque seeds del Pine v4.

Publicación: subir **todos** los `*_GEX*.csv` (y los `*_WALLS.csv` de
abajo) a la raíz de este repo y cargar `TU_USUARIO/pine-seeds` en el
input "Pine-seeds repo" del GEX PROFILE v4. Al cambiar de símbolo en
TradingView, la tabla y la escalera muestran los niveles de ESE
ticker. Actualización: correr `build_gex_seeds.py <fecha>` y volver a
subir los CSV (reemplaza la fila del día).

## BLOCK ORDR v10 — muros de opciones

Datos diarios de muros de opciones (OI real, CBOE delayed) que BLOCK ORDR v10
lee con `request.seed`. Un CSV por ticker: `<TICKER>_WALLS.csv`.

## Formato (Pine Seeds)
Columnas: `Date,Open,High,Low,Close,Volume`
- Open = put wall | High = call wall | Low = put wall | Close = call wall
- Volume = PCR por volumen del día

Call wall = strike de calls con mayor OI por encima del spot, dentro de
±20% del spot y vencimientos ≤45 días. Put wall = espejo con puts por
debajo del spot. Fuente: cadena CBOE delayed (~15 min), corrida al cierre.

## Cómo publicarlo (una sola vez, ~2 minutos)
1. En GitHub: New repository → nombre `pine-seeds`, **Public**, Create.
2. Subir todos los `*_WALLS.csv` de esta carpeta a la raíz del repo
   (Add file → Upload files → commit). Este README puede ir también.
3. En TradingView, en los Inputs de BLOCK ORDR v10, grupo
   "OPTIONS WALLS (SEED, REAL OI)", escribir en "Pine-seeds repo":
   `TU_USUARIO/pine-seeds`. Los muros aparecen como líneas escalón
   naranja (call) y teal (put), con etiqueta a la derecha.

## Actualización diaria
`python3 build_walls_seed.py <YYYY-MM-DD último día de mercado> GOOGL SPY ...`
agrega/actualiza la fila del día en cada CSV; después se sube el repo
(git push o re-upload). Pendiente: automatizar con git autenticado +
tarea programada al cierre de mercado.

## Estado inicial
Snapshot del cierre del viernes 2026-10-30 (corrida 2026-10-31):
GOOGL 300/280 · SPY 800/750 · QQQ 760/680 · NVDA 230/190 · AMD 600/440 ·
MSFT 550/500 · AMZN 280/240 · TSLA 420/380 · PLTR 200/180 · MU 1000/800 ·
ASTS 45/40 · SNDK 1300/1000 · MRNA 250/180 · VZ 45/42 · T 24/21
(call wall / put wall).
