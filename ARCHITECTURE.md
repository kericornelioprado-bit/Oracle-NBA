# ARCHITECTURE.md - Oráculo NBA V2: Prop Arbitrage & Paper Trading

## 1. Visión Técnica
El sistema Oráculo NBA V2 evoluciona de un predictor de victorias a un motor de arbitraje de valor en **Player Props**. La arquitectura se basa en el principio de **"Intervención Cero"**, donde el sistema se auto-regula, se auto-programa y se auto-evalúa financieramente sin participación humana.

## 2. Topología de GCP (Estrategia Cloud-Native)
El sistema se despliega como un servicio único en **Cloud Run**, orquestado por tres disparadores de **Cloud Scheduler**:

1.  **Job Diario de Predicción (16:30 CST):**
    - Ejecución "One-Shot" del pipeline de 14 minutos.
    - Genera predicciones de Moneyline -> Game Script -> Proyección de Minutos -> Predicción de Stats.
    - Calcula EV y Kelly 1/4 sobre la banca virtual de $20k.
    - Envía el reporte final por correo.

2.  **Job de Liquidación (03:00 AM):**
    - Cierre de apuestas del día anterior.
    - Consulta resultados reales en `nba_api`.
    - Calcula ROI real vs. esperado y actualiza el saldo en BigQuery.
    - Mide el CLV (Closing Line Value) comparando cuota de apertura vs. cierre de Pinnacle.

3.  **Job de Portafolio (Domingo 23:59 CST):**
    - Re-cálculo automático del "Top 20" de jugadores.
    - Ejecuta queries de `minute_swing` (sensibilidad al margen) e `injury_heir` (redistribución de minutos).
    - Actualiza la tabla de referencia en BigQuery para la semana entrante.

## 3. Esquema de Datos (BigQuery)
Dataset centralizado: `oracle_nba_v2`

### `virtual_bankroll`
- `current_balance`: FLOAT (Inicia en 20,000.00).
- `last_updated`: TIMESTAMP.

### `bet_history` (Paper Trading Ledger)
- `bet_id`: STRING (UUID).
- `player_name`: STRING.
- `market`: STRING (REB, AST, PRA).
- `line`: FLOAT.
- `odds_open`: FLOAT (Cuota al momento del pick).
- `odds_close`: FLOAT (Cuota de cierre para CLV).
- `stake_usd`: FLOAT (Monto apostado).
- `result`: STRING (PENDING, WIN, LOSS, PUSH).
- `payout`: FLOAT (Ganancia/Pérdida neta).

### `top_20_portfolio`
- `tier`: INTEGER (1: Núcleo, 2: Volatilidad, 3: Señuelo).
- `player_id`: INTEGER.
- `minute_swing`: FLOAT.
- `updated_at`: TIMESTAMP.

## 4. El "Motor de Minutos" (Lógica de Negocio)
Componente modular dentro de Cloud Run que procesa:
- **Input:** Game Script (Margen ML), Injury Report, B2B, Rest Days.
- **Filtro GTD:** Si un jugador clave es `Questionable` a las 16:30 CST -> `SKIP_GAME` (Incertidumbre cero).
- **Heurísticas:**
    - `Blowout Win (>+15)`: Boost de minutos para Tier 1 (Bench).
    - `Injury Heir`: Si el titular está OUT, el backup del Tier 2 hereda ~60% de sus minutos.

## 5. Estrategia de Inferencia
- **Modelos:** Regresión (Ridge/XGBoost) entrenados por estadística (REB, AST, Puntos).
- **Feature Clave:** `projected_minutes` (generado por el Motor de Minutos).
- **Conversión de Probabilidad:** Distribución histórica del jugador para calcular `P(Over > Line)`.

## 6. Monitoreo y Logging
- **Alertas:** El sistema debe registrar en **Cloud Logging** cada decisión de `SKIP` o `PICK`.
- **Salud:** Registro de cada ejecución de Cloud Scheduler para detectar fallos del Cron.
- **Reporting:** El correo de las 16:30 es el único punto de contacto con el usuario.
