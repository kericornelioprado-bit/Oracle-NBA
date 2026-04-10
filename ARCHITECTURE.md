# ARCHITECTURE.md - Oracle Sports Suite (Monorepo)

## 1. Visión Técnica
El sistema ha evolucionado de "Oráculo NBA" a un **Oracle Sports Suite** multi-deporte. La arquitectura se basa en el principio de **"Intervención Cero"** e incluye un enfoque de Monorepo por capas.

## 2. Estructura de Monorepo (Fase 1)
El código se organiza para maximizar la reutilización y el aislamiento:
- **`src/shared/`**: Clientes genéricos (`BigQueryClient`, `BallDontLieClient`, `EmailService`). Parametrizados por `sport`.
- **`src/nba/`**: (Actualmente en `src/utils` / `src/models`) Mantiene el motor de NBA V2 intacto.
- **`src/mlb/`**: (En construcción) Contendrá `data/`, `models/` y `jobs/` específicos para Diamante MLB.

## 3. Topología de GCP (Cloud-Native)
El sistema se despliega como una imagen unificada en **Cloud Run**, pero es orquestado de forma granular por **Cloud Scheduler** utilizando parámetros CLI:

1.  **Oráculo NBA:**
    - `predict` (16:30 CST): Genera predicciones de Moneyline y Props.
    - `settle` (03:00 AM): Liquidación de apuestas del día anterior.

2.  **Diamante MLB (Próximamente):**
    - `ingest` (Temprano): Ingesta de box scores de la noche anterior.
    - `predict` (Pre-juego): Evaluación de líneas de props basadas en lineups confirmados.

## 4. Esquema de Datos (BigQuery)
Los datasets se asignan dinámicamente por deporte (`oracle_nba_ds`, `oracle_nba_v2`, `oracle_mlb_ds`, `oracle_mlb_v2`).
- **`bet_history`**: Ledger universal de Paper Trading.
- **`virtual_bankroll`**: Balance actual separado por deporte.
- Tablas específicas de logs de juegos (ej. `mlb_pitcher_game_logs`).

## 5. Estrategia de Inferencia y Monitoreo
- Modelos de Stacking (LightGBM + XGBoost + Ridge).
- Evaluación constante del CLV (Closing Line Value).
- Alertas generadas dinámicamente por el `EmailService` compartido.
