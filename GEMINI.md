# GEMINI.md - Instructional Context for Oráculo NBA 🏀

## Project Overview
**Oráculo NBA** is a predictive system designed for **Value Betting** in the NBA. It uses machine learning (Stacking Ensemble) to predict game outcomes and identify betting opportunities with a positive expected value (EV).

### Main Technologies
- **Language:** Python 3.11+ (managed with `uv`).
- **Data Engineering:** `pandas`, `pyarrow`, `nba_api`.
- **Machine Learning:** `scikit-learn`, `xgboost`, `lightgbm`, `optuna` (for hyperparameter tuning).
- **MLOps:** `mlflow` for experiment tracking.
- **Infrastructure:** Google Cloud Platform (Cloud Run, BigQuery, Cloud Scheduler, GCS).
- **IaC:** Terraform.
- **CI/CD:** GitHub Actions.
- **Web Framework:** Flask (used to wrap the inference script for Cloud Run).
- **Deployment:** Docker (Containerized service).

### Architecture
The system follows a modular, decoupled architecture:
1. **Data Ingestion:** Fetches real-time and historical data from the NBA API.
2. **Feature Engineering:** Calculates rolling averages and team rest days.
3. **Inference:** Uses a Stacking Classifier (Logistic Regression + XGBoost) to predict home win probabilities.
4. **Reporting:** Generates HTML reports and sends them via Gmail SMTP.
5. **Persistence:** Stores predictions and metadata in BigQuery for ROI tracking.
6. **Orchestration:** Cloud Scheduler triggers the daily prediction flow.

---

## Building and Running

### Local Control
Use the `ctl.sh` script for managing the application locally:
- **Start:** `./ctl.sh start` (Runs `main.py` using `uv`).
- **Stop:** `./ctl.sh stop`
- **Status:** `./ctl.sh status`
- **Restart:** `./ctl.sh restart`

### Docker
- **Build Image:** `docker build -t oracle-nba .`
- **Run Container:** `docker run -p 8080:8080 oracle-nba`

### Machine Learning Pipelines
- **Data Ingestion:** `PYTHONPATH=. python3 src/data/ingestion.py`
- **Training:** `PYTHONPATH=. python3 src/models/trainer.py`
- **Stacking Training:** `PYTHONPATH=. python3 src/models/stacking_trainer.py`
- **Inference Test:** `PYTHONPATH=. python3 src/models/inference.py`

### Testing
- **Run Unit Tests:** `pytest tests/` (e.g., `pytest tests/test_email_service.py`).
- **Coverage:** `pytest --cov=src tests/`.

---

## Development Conventions

### Coding Style
- **Modularity:** Logic is split into `src/data`, `src/models`, and `src/utils`.
- **Logging:** Use `src.utils.logger` for all operations.
- **Configuration:** Use `.env` files and `python-dotenv`.
- **Error Handling:** Global `try-except` in `main.py` sends email alerts on failure.

### Quality Gate (CI/CD)
- **Mandatory Tests:** GitHub Actions runs `pytest` on every push to `main`. If tests fail, deployment is blocked.
- **Dockerization:** Automated builds use the `python:3.11-slim` base image for stability.

### GCP Strategy
- **Cloud Run:** Stateless execution of the prediction flow.
- **BigQuery:** Centralized storage for "Post-Mortem" ROI analysis.
- **Secret Manager:** Use for sensitive credentials (though currently some are passed via ENV vars in the workflow).

---

## Key Files Summary
- `main.py`: Flask entry point for the Cloud Run service.
- `src/models/inference.py`: Core prediction logic with `nba_api` retry mechanisms.
- `infra/main.tf`: Terraform definition for GCP resources.
- `.github/workflows/deploy.yml`: CI/CD pipeline definition.
- `requirements.txt`: Python dependencies.
- `ARCHITECTURE.md`: Technical design documentation.
- `PRD.md`: Product requirements and history.
- `research.md`: Initial codebase research and findings.
