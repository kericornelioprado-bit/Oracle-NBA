# Oráculo NBA 🏀

> Sistema automatizado de predicción de apuestas de valor (Value Betting) en la NBA.
> Stacking Ensemble (LR + XGBoost) | ROI: **24.29%** | Accuracy: **63.91%** | Cobertura: **94%**

---

## Qué hace

1. Cada día a las **14:00 UTC**, Cloud Scheduler dispara el pipeline.
2. Se obtienen los **partidos del día** desde la NBA API.
3. Se calculan **features de rolling window** [3,5,10,20] para cada equipo.
4. El **Stacking Ensemble** genera probabilidades de victoria local.
5. Se aplican **umbrales de break-even** (odds 1.91 → 52.4%) para recomendar HOME / AWAY / SKIP.
6. Las predicciones se persisten en **BigQuery** y se envían por **email** como tabla HTML.

---

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.11 (gestionado con `uv`) |
| ML | scikit-learn, XGBoost, Optuna, MLflow |
| API datos | nba_api |
| Web | Flask + Gunicorn |
| Persistencia | BigQuery (`oracle_nba_ds.predictions`) |
| Storage | Google Cloud Storage |
| Cómputo | Cloud Run v2 (0→1 instancias) |
| Orquestación | Cloud Scheduler (cron `0 14 * * *`) |
| IaC | Terraform >= 5.0.0 |
| CI/CD | GitHub Actions |
| Contenedor | Docker (`python:3.11-slim`) |

---

## Estructura del Proyecto

```
Oracle_NBA/
├── src/
│   ├── data/
│   │   ├── ingestion.py          # NBADataIngestor — extrae datos de la NBA API
│   │   ├── feature_engineering.py # NBAFeatureEngineer — rolling windows + rest days
│   │   └── eda_report.py         # Análisis exploratorio
│   ├── models/
│   │   ├── inference.py          # NBAOracleInference — predicción diaria (PRODUCCIÓN)
│   │   ├── stacking_trainer.py   # NBAStackingTrainer — entrena el modelo productivo
│   │   ├── trainer.py            # NBAModelTrainer — modelos base
│   │   ├── tuner.py              # NBAHyperTuner — Optuna
│   │   └── evaluator.py          # NBAProfitSim — backtesting ROI
│   └── utils/
│       ├── bigquery_client.py    # NBABigQueryClient — persistencia
│       ├── email_service.py      # NBAEmailService — Gmail SMTP
│       ├── report_generator.py   # NBAReportGenerator — HTML
│       └── logger.py             # Logger centralizado
├── tests/                        # 79 tests, 94% cobertura
├── infra/                        # Terraform (GCP)
├── docs/
│   ├── api/openapi.yaml          # Spec OpenAPI 3.0
│   ├── architecture/             # Diagramas Mermaid
│   ├── infrastructure/gcp-setup.md
│   └── requirements/user-stories.json
├── system-heartbeat/
│   ├── ARCHEOLOGY_REPORT.md
│   ├── SECURITY-AUDIT.md
│   └── PEER-REVIEW.md
├── data/
│   ├── raw/                      # nba_games_raw.parquet
│   └── processed/                # nba_games_features.parquet
├── models/                       # Artefactos ML (.joblib)
├── main.py                       # Flask entry point
├── ctl.sh                        # Script de control local
├── Dockerfile
└── requirements.txt
```

---

## Inicio Rápido

### 1. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales:
# GCP_PROJECT_ID=oracle-nba
# GCS_BUCKET_NAME=oracle-nba-nba-data-lake
# GMAIL_USER=tu@gmail.com
# GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 2. Instalar dependencias

```bash
# Con uv (recomendado)
uv pip install -r requirements.txt

# O con pip
pip install -r requirements.txt
```

### 3. Control local

```bash
./ctl.sh start    # Inicia Flask en background (puerto 8080)
./ctl.sh status   # Verifica si está corriendo
./ctl.sh stop     # Detiene el proceso
./ctl.sh restart  # Reinicia
```

### 4. Docker

```bash
docker build -t oracle-nba .
docker run -p 8080:8080 --env-file .env oracle-nba
```

### 5. Disparar predicción manual

```bash
curl -X POST http://localhost:8080/
```

---

## Pipelines de ML

```bash
# 1. Ingestión de datos (temporadas 2021-22 a 2023-24)
PYTHONPATH=. uv run python3 src/data/ingestion.py

# 2. Feature engineering
PYTHONPATH=. uv run python3 src/data/feature_engineering.py

# 3. Entrenamiento base (LR + XGBoost)
PYTHONPATH=. uv run python3 src/models/trainer.py

# 4. Optimización Optuna
PYTHONPATH=. uv run python3 src/models/tuner.py

# 5. Stacking Ensemble (MODELO DE PRODUCCIÓN)
PYTHONPATH=. uv run python3 src/models/stacking_trainer.py

# 6. Test de inferencia en vivo
PYTHONPATH=. uv run python3 src/models/inference.py
```

---

## Tests

```bash
# Suite completa con cobertura
uv run python -m pytest tests/ --cov=src --cov=main -q

# Resultado esperado
# 79 passed, 0 failed | TOTAL: 94%
```

---

## Resultados del Modelo

| Métrica | Valor |
|---------|-------|
| Accuracy (Stacking) | **63.91%** |
| ROI estimado | **24.29%** |
| Win Rate | **65.07%** |
| Odds referencia | 1.91 (-110 americano) |
| Break-even | 52.36% |
| Umbral HOME | > 52.4% |
| Umbral AWAY | < 47.6% |

---

## Infraestructura GCP

Ver [docs/infrastructure/gcp-setup.md](docs/infrastructure/gcp-setup.md) para el manual completo.

```bash
cd infra/
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

**GitHub Secrets requeridos para CI/CD:**

| Secret | Descripción |
|--------|-------------|
| `GCP_SA_KEY` | JSON de Service Account |
| `GCP_PROJECT_ID` | `oracle-nba` |
| `GMAIL_USER` | Email remitente |
| `GMAIL_APP_PASSWORD` | App Password de Gmail |

---

## Documentación

| Documento | Descripción |
|-----------|-------------|
| [docs/api/openapi.yaml](docs/api/openapi.yaml) | Spec OpenAPI 3.0 del endpoint Flask |
| [docs/architecture/flow-diagram.md](docs/architecture/flow-diagram.md) | Diagramas Mermaid del sistema |
| [docs/infrastructure/gcp-setup.md](docs/infrastructure/gcp-setup.md) | Manual de GCP y Terraform |
| [docs/requirements/user-stories.json](docs/requirements/user-stories.json) | Historias de usuario estructuradas |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Diseño técnico del sistema |
| [system-heartbeat/SECURITY-AUDIT.md](system-heartbeat/SECURITY-AUDIT.md) | Auditoría de seguridad |
| [system-heartbeat/PEER-REVIEW.md](system-heartbeat/PEER-REVIEW.md) | Revisión de código |
| [system-heartbeat/ARCHEOLOGY_REPORT.md](system-heartbeat/ARCHEOLOGY_REPORT.md) | Estado técnico del repositorio |
| [test-evidence.md](test-evidence.md) | Evidencia completa de tests |

---

## Changelog

| Versión | Sprint | Cambios |
|---------|--------|---------|
| 3.2.0 | Sprint 3.2 | Suite de tests 94% cobertura (79 tests), documentación completa |
| 3.1.0 | Sprint 3.1 | Pipeline CI/CD GitHub Actions, Flask endpoint, BigQuery + Email |
| 2.5.0 | Sprint 2.5 | Stacking Ensemble, Optuna tuning, ventanas [3,5,10,20] — ROI 24.29% |
| 2.0.0 | Sprint 2 | LR + XGBoost base, simulación ROI, evaluador financiero |
| 1.0.0 | Sprint 1 | Ingestión NBA API, EDA, estructura base, Terraform GCP |
