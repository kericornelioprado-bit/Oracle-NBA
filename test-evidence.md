# [UNIT TEST REPORT] - Setup de Proyecto
- **Scope**: Estructura de carpetas y archivos base (HU1)
- **Command**: `ls -R`
- **Output**:
```text
.:
Dockerfile
README.md
Sprints.md
data
infra
notebooks
plan.md
proyectoinicial.md
requirements.txt
src
test-evidence.md
tests

./data:
external
processed
raw

./infra:

./notebooks:

./src:
data
models
utils

./tests:
```

- **Validation**:
  - Estructura de carpetas creada según plan.md: ✅
  - Git inicializado: ✅
  - .gitignore configurado para Python y Terraform: ✅
  - Dockerfile base (Fedora) listo: ✅
  - Requirements iniciales definidos: ✅

# [UNIT TEST REPORT] - Ingestión de Datos (HU2)
- **Scope**: Extracción desde nba_api y guardado en Parquet.
- **Command**: `env PYTHONPATH=. uv run --with pandas,nba_api,pyarrow,fastparquet python3 src/data/ingestion.py`
- **Output**:
```text
2026-03-22 21:48:55,958 - oracle-nba - INFO - Datos guardados exitosamente en data/raw/nba_games_raw.parquet
```
- **File Info**:
```bash
-rw-r--r--. 1 keri keri 203K mar 22 21:48 data/raw/nba_games_raw.parquet
```
- **Validation**:
  - Extracción de temporadas 2021-22 a 2023-24: ✅
  - Almacenamiento en Parquet (eficiencia): ✅

# [UNIT TEST REPORT] - Infraestructura (HU3)
- **Scope**: Creación de archivos Terraform e integración en Python.
- **Files**: `infra/main.tf`, `infra/variables.tf`, `infra/outputs.tf`
- **Validation**:
  - Definición de Bucket GCS con versionado: ✅
  - Script `ingestion.py` ahora soporta `upload_to_gcs`: ✅
  - Uso de `python-dotenv` para manejar el nombre del bucket: ✅

# [UNIT TEST REPORT] - Análisis Exploratorio (HU4)
- **Scope**: Análisis de correlación y calidad de datos.
- **Command**: `env PYTHONPATH=. uv run --with pandas,pyarrow,fastparquet python3 src/data/eda_report.py`
- **Output (Correlación):**
  - PLUS_MINUS: 0.80
  - FG_PCT: 0.46
  - DREB: 0.37
  - TOV: -0.11 (Negativa)
- **Validation**:
  - Limpieza de datos (WL -> Win/Loss): ✅
  - Reporte generado: `data/processed/eda_report.txt` ✅
  - Selección de features candidatas completada: ✅

# [UNIT TEST REPORT] - Entrenamiento de Modelos (Sprint 2 HU1-2)
- **Scope**: Entrenamiento con validación temporal.
- **Models**: Logistic Regression, XGBoost.
- **Results**:
  - Logistic Regression: **61.76% Accuracy**
  - XGBoost: **61.47% Accuracy**
- **Validation**:
  - Split temporal (no aleatorio): ✅
  - Superado umbral del 55%: ✅
  - Modelo guardado en `models/nba_best_model.joblib`: ✅

# [UNIT TEST REPORT] - Evaluación Financiera (Sprint 2 HU3)
- **Scope**: Simulación de ROI y Backtesting.
- **Command**: `env PYTHONPATH=. uv run --with pandas,pyarrow,fastparquet,scikit-learn,joblib python3 src/models/evaluator.py`
- **Financial Results**:
  - Win Rate: **62.93%**
  - Profit: **$12,964** (Units of 100)
  - ROI: **20.19%**
- **Validation**:
  - Estrategia de apuestas de unidad fija (100).
  - Umbral de confianza del modelo aplicado.
  - Resultados guardados en `data/results/simulation_results.csv`: ✅

# [UNIT TEST REPORT] - Advanced Tuning (Sprint 2.5 HU1)
- **Scope**: Optimización Bayesiana con Optuna.
- **Results**:
  - Best LogLoss: **0.6400**
  - Tuned ROI: **22.22%**
  - Win Rate: **63.99%**
- **Validation**:
  - Integración MLflow Tuning: ✅
  - Modelo guardado en `models/nba_best_model_tuned.joblib`: ✅

# [UNIT TEST REPORT] - Stacking Ensemble (Sprint 2.5 HU2)
- **Scope**: Meta-modelo con validación cruzada interna.
- **Results**:
  - Max Accuracy: **62.89%**
  - Stacking ROI: **21.27%**
  - Win Rate: **63.49%**
- **Validation**:
  - Ensamble de Regresión Logística y XGBoost Tuned: ✅
  - Modelo guardado en `models/nba_best_model_stacking.joblib`: ✅

# [UNIT TEST REPORT] - Ventanas Dinámicas y Stacking (Sprint 2.5 HU3)
- **Scope**: Ingeniería de características multiventana.
- **Results**:
  - Accuracy: **63.91%**
  - ROI: **24.29%**
  - Win Rate: **65.07%**
- **Validation**:
  - Ventanas [3, 5, 10, 20] integradas: ✅
  - Stacking con mejores parámetros de Optuna: ✅
  - Tracking completo en MLflow: ✅

# [UNIT TEST REPORT] - Inferencia Diaria (Sprint 3 HU1)
- **Scope**: Generación de cartelera de apuestas en vivo.
- **Command**: `env PYTHONPATH=. uv run --with pandas,pyarrow,fastparquet,scikit-learn,xgboost,joblib,nba_api python3 src/models/inference.py`
- **Output**:
```text
=== CARTELERA DE APUESTAS DEL DÍA (ORÁCULO NBA) ===
      HOME_ID     AWAY_ID  PROB_HOME_WIN RECOMMENDATION
0  1610612743  1610612757       0.537534           HOME
...
```
- **Validation**:
  - Extracción de Scoreboard en tiempo real: ✅
  - Imputación robusta de nulos: ✅
  - Predicciones generadas con Stacking Model: ✅

# [UNIT TEST REPORT] - Cobertura Global
- **Scope**: Análisis de cobertura con pytest-cov.
- **Current Coverage**: **32%** (Incrementado desde 11%).
- **Key Modules Protected**:
  - `ingestion.py` (59%): Extracción y fallos de API.
  - `trainer.py` (50%): Lógica de split temporal.
  - `feature_engineering.py` (46%): Rolling windows y rest days.
  - `evaluator.py` (20%): Cálculo matemático de beneficios.
- **Validation**:
  - Mocking de API externa completado: ✅
  - Verificación matemática de ROI: ✅
  - Pruebas de integración de inferencia pasando: ✅
