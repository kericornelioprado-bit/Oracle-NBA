# Oráculo NBA

Sistema predictivo de **Value Betting** para la NBA. Combina un Stacking Ensemble para moneyline con un motor de Player Props impulsado por cuotas reales de mercado. 100% automatizado en Google Cloud.

## Características

- **Moneyline (Game Picks):** Stacking Ensemble (LR + XGBoost, 63.91% accuracy, 24.29% ROI en backtest) con split cronológico 80/20.
- **Player Props:** The Odds API (paid) define el universo de jugadores disponibles hoy → el modelo evalúa todos con EV real → solo los picks con EV > umbral llegan al reporte.
- **Automatización completa:** Cloud Scheduler dispara a las 14:00 UTC → Cloud Run ejecuta el pipeline → BigQuery persiste → Gmail entrega el reporte HTML.
- **Kelly Fraccional:** Sizing de apuestas proporcional al edge calculado sobre cuotas reales (Pinnacle como sharp reference).

## Flujo diario

```
Cloud Scheduler (14:00 UTC)
  → Cloud Run
      → Moneyline: NBA API → features → Stacking model → picks ML
      → Props:     The Odds API → 100+ jugadores con cuotas hoy
                   BDL últimos 30 días → rolling features (L10)
                   EV = (prob_modelo × odds) - 1  → filtro EV > 5%
                   Kelly fraccional → stake sugerido
      → BigQuery: predictions + prop_bets
      → Gmail: reporte HTML con picks del día
```

## Arquitectura de módulos

| Módulo | Clase | Rol |
|--------|-------|-----|
| `src/data/ingestion.py` | `NBADataIngestor` | Historial de equipos 2021-24 desde NBA API → Parquet/GCS |
| `src/data/feature_engineering.py` | `NBAFeatureEngineer` | 66 features rolling (ventanas 3/5/10/20, `shift(1)` anti-leakage) |
| `src/data/player_ingestion.py` | `PlayerStatsIngestion` | Logs de jugadores vía BallDontLie → features L10 + std |
| `src/models/stacking_trainer.py` | `NBAStackingTrainer` | Entrena StackingClassifier; guarda `.joblib` |
| `src/models/inference.py` | `NBAOracleInference` | Pipeline diario: moneyline + props end-to-end |
| `src/models/props_model.py` | `PlayerPropsModel` | Predicción stat esperada → P(Over) normal → EV |
| `src/models/minutes_projector.py` | `MinutesProjector` | Proyecta minutos ajustados por game script y lesiones |
| `src/utils/odds_api.py` | `OddsAPIClient` | The Odds API v4: eventos, props consolidados por jugador |
| `src/utils/bdl_client.py` | `BallDontLieClient` | BallDontLie v1: juegos y stats con paginación |
| `src/utils/bigquery_client.py` | `NBABigQueryClient` | Escribe en BigQuery; degrada si GCP no disponible |
| `src/utils/email_service.py` | `NBAEmailService` | Gmail SMTP con TLS |
| `src/utils/report_generator.py` | `NBAReportGenerator` | Reporte HTML con tabla de picks ML y props |

## Variables de entorno

```env
GOOGLE_APPLICATION_CREDENTIALS=config/gcp-sa-key.json
GCS_BUCKET_NAME=oracle-nba-nba-data-lake
GCP_PROJECT_ID=oracle-nba
GMAIL_USER=tu@gmail.com
GMAIL_APP_PASSWORD=app-specific-password
THE_ODDS_API_KEY=tu-api-key-pagada
BOOKMAKERS=pinnacle,bet365,betway
MIN_EV_THRESHOLD=0.05
KELLY_FRACTION=0.25
BANKROLL_VIRTUAL=1000
```

## Desarrollo local

```bash
./ctl.sh start     # Inicia Flask en :8080
./ctl.sh stop
./ctl.sh restart

# Tests (239 tests)
uv run python -m pytest tests/ -q

# Simulación manual del pipeline
uv run python -c "from src.models.inference import NBAOracleInference; NBAOracleInference().predict_today()"
```

## Despliegue en GCP

1. Configura GitHub Secrets: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `GCP_PROJECT_ID`, `GCP_SA_KEY`, `THE_ODDS_API_KEY`.
2. Push a `main` → GitHub Actions corre tests → build Docker → deploy a Cloud Run.

```bash
# Infraestructura (primera vez)
cd infra/
terraform init
terraform apply -var-file="terraform.tfvars"
```

## Recursos GCP

| Recurso | Nombre |
|---------|--------|
| Cloud Run | `oracle-nba-service` (1 vCPU, 512 Mi, 600s timeout) |
| Cloud Scheduler | `oracle-nba-daily-trigger` — `0 14 * * *` UTC |
| BigQuery | `oracle_nba_ds` → `predictions`, `prop_bets` |
| GCS | `oracle-nba-nba-data-lake` (us-central1) |
| Artifact Registry | `us-central1-docker.pkg.dev/oracle-nba/...` |
