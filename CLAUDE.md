# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Oráculo NBA** is a production NBA value-betting prediction system that runs daily on GCP. It fetches live game data via the NBA API, runs a Stacking Ensemble model (LR + XGBoost, 63.91% accuracy, 24.29% ROI), stores predictions in BigQuery, and emails HTML reports — all triggered by Cloud Scheduler at 14:00 UTC.

## Commands

### Development

```bash
# Start Flask server locally (uses uv)
./ctl.sh start

# Stop / restart
./ctl.sh stop
./ctl.sh restart
```

### Testing

```bash
# Full test suite with coverage (79 tests, target 94%+)
uv run python -m pytest tests/ --cov=src --cov=main -q

# Single test file
uv run python -m pytest tests/test_inference_extended.py -q

# Single test by name
uv run python -m pytest tests/test_stacking_trainer.py::TestClass::test_name -q
```

### CI/CD — GitHub Actions

Push to `main` triggers:
1. **test job** — runs `pytest tests/test_email_service.py` (blocks deploy on failure)
2. **deploy job** — builds Docker image, pushes to Artifact Registry, deploys to Cloud Run

### Infrastructure (Terraform)

```bash
cd infra/
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

## Architecture

### System Flow (Daily)

```
Cloud Scheduler (14:00 UTC)
    → Cloud Run (Flask / main.py)
        → NBAOracleInference.predict_today()   # NBA API → features → Stacking model
        → NBABigQueryClient.insert_predictions() # oracle_nba_ds.predictions
        → NBAReportGenerator.generate_html_report()
        → NBAEmailService.send_prediction_report() # Gmail SMTP port 587
```

Error path: `send_error_alert()` emails full traceback and returns HTTP 500.

### Source Modules (`src/`)

| Module | Class | Role |
|--------|-------|------|
| `data/ingestion.py` | `NBADataIngestor` | Fetches 2021-24 seasons from NBA API; saves Parquet to local + GCS |
| `data/feature_engineering.py` | `NBAFeatureEngineer` | 66 rolling-window features (windows 3/5/10/20, `shift(1)` anti-leakage) |
| `models/stacking_trainer.py` | `NBAStackingTrainer` | Trains StackingClassifier (LR meta + XGB base, CV=5); saves `.joblib` |
| `models/tuner.py` | `NBAHyperTuner` | Optuna Bayesian hyper-tuning (20 trials, log_loss) |
| `models/inference.py` | `NBAOracleInference` | Production daily pipeline — loads model, applies recommendation thresholds |
| `models/evaluator.py` | `NBAProfitSim` | ROI simulation with unit-fixed betting |
| `utils/bigquery_client.py` | `NBABigQueryClient` | Writes to BigQuery; degrades gracefully if `GCP_PROJECT_ID` unset |
| `utils/email_service.py` | `NBAEmailService` | Gmail SMTP with TLS |
| `utils/report_generator.py` | `NBAReportGenerator` | Color-coded HTML prediction table |
| `utils/logger.py` | `setup_logger()` | Centralized logger (`oracle-nba`) |

### Feature Engineering

- **66 features** = 8 stats × 4 windows × 2 teams (HOME/AWAY) + 2 rest-day columns
- Stats: `PTS, FG_PCT, FG3_PCT, FT_PCT, AST, REB, TOV, PLUS_MINUS`
- `shift(1)` prevents current-game leakage
- NaN cascade: `ROLL_20 ← ROLL_10 ← ROLL_5 ← ROLL_3 ← 0`
- Feature column order is locked in `config/model_features.json`

### Recommendation Logic

- Odds assumed 1.91 → break-even = 52.36%
- `prob_home_win > 0.524` → **HOME**
- `prob_home_win < 0.476` → **AWAY**
- Otherwise → **SKIP**

### Model Artifacts

- `models/nba_best_model_stacking.joblib` — production model (do not delete)
- `data/processed/nba_games_features.parquet` — feature-engineered dataset
- `config/model_features.json` — ordered feature list used at inference time (versioned in git)

## Environment Variables

Required locally (copy to `.env`):

```
GOOGLE_APPLICATION_CREDENTIALS=config/gcp-sa-key.json
GCS_BUCKET_NAME=oracle-nba-nba-data-lake
GMAIL_USER=<gmail address>
GMAIL_APP_PASSWORD=<app-specific password>
GCP_PROJECT_ID=oracle-nba
```

The GCP service account key (`config/oracle-nba-*.json`) is gitignored and must be provisioned separately.

## GCP Resources

| Resource | Name |
|----------|------|
| Cloud Run service | `oracle-nba-service` (1 vCPU, 512 Mi, 600s timeout) |
| Cloud Scheduler | `oracle-nba-daily-trigger` — `0 14 * * *` UTC |
| BigQuery dataset | `oracle_nba_ds`, table `predictions` |
| GCS bucket | `oracle-nba-nba-data-lake` (`us-central1`) |
| Artifact Registry | `us-central1-docker.pkg.dev/oracle-nba/...` |

## Key Constraints

- **Temporal split is mandatory** — model training uses 80/20 chronological split; never shuffle before splitting
- **`shift(1)` must remain on all rolling features** — removing it causes data leakage
- **NBA API rate limiting** — 1.5s pause between team calls, 5 retries with exponential backoff, 60s timeout
- **BigQuery deletions** — `delete_contents_on_destroy = false` in Terraform protects production data
