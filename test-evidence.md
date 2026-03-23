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
