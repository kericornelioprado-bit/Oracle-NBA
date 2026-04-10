# GEMINI.md - Instructional Context for Oracle Sports Suite 🏀⚾

## Project Overview
**Oracle Sports Suite** (formerly Oráculo NBA) is a predictive system designed for **Value Betting**. It uses machine learning (Stacking Ensembles) to predict game outcomes and identify betting opportunities with a positive expected value (EV).

### Expansion to MLB (Diamante V1)
The project is currently transitioning into a **Monorepo** to support both NBA and MLB (Diamante). 
- **Phase 1 (Monorepo Setup):** COMPLETED. `src/shared` created, `main.py` refactored to support `--sport nba|mlb`.
- **Phase 2 (MLB Data):** IN PROGRESS. Setting up BigQuery schema and ingesting BallDontLie `/mlb/v1/stats`.

### Main Technologies
- **Language:** Python 3.11+ (managed with `uv`).
- **Data Engineering:** `pandas`, `pyarrow`, `nba_api`, `requests`.
- **Machine Learning:** `scikit-learn`, `xgboost`, `lightgbm`.
- **Infrastructure:** Google Cloud Platform (Cloud Run, BigQuery, Cloud Scheduler, GCS).
- **IaC:** Terraform.

### Architecture (Monorepo)
1. **`src/shared/`:** Agnostic clients (BigQuery, BallDontLie, Email).
2. **`src/nba/`:** (Alias to `src/utils` currently) Legacy NBA logic.
3. **`src/mlb/`:** New module for Diamante MLB.
4. **Dispatcher:** `main.py` routes requests based on `--sport` and `--job` args.

---

## Building and Running

### CLI Execution
- **NBA Predict:** `uv run python main.py --sport nba --job predict`
- **NBA Settle:** `uv run python main.py --sport nba --job settle`
- **MLB Ingest (WIP):** `uv run python main.py --sport mlb --job ingest`

### Docker
- **Build Image:** `docker build -t oracle-suite .`

---

## Key Files Summary
- `main.py`: Unified entry point (Flask & CLI).
- `plan.md`: Current execution plan and roadmap tracking.
- `Diamante_MLB_V1.md`: MLB Expansion strategy.
- `monorepo_structure.md`: Architectural shift strategy.
