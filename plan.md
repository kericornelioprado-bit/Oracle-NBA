# Implementation Plan - Oráculo NBA

## Estado del Proyecto
- [ ] Planning (En discusión)
- [x] Approved (Listo para código)
- [ ] In Progress
- [ ] Done

## Arquitectura Refinada
- **Lenguaje:** Python 3.11+
- **Gestión de Dependencias:** `uv` (por recomendación de skill python-ai-engineer)
- **Contenedores:** Docker (Fedora base + CUDA support)
- **Infraestructura:** Terraform (GCP)
- **Estructura de Carpetas:**
  - `data/`: Raw, processed y external data.
  - `notebooks/`: EDA y experimentación.
  - `src/`: Código fuente modular (ingestion, models, utils).
  - `infra/`: Código de Terraform.
  - `tests/`: Pruebas unitarias e integración.

## Roadmap & Checklist
### Sprint 1: Data Ingestion & EDA [Status: 100%]
- [x] **Tarea 1: Setup del repo y Entorno (HU1)**
  - [x] Estructura de carpetas
  - [x] Configuración de `uv` y `requirements.txt`
  - [x] Dockerfile base (Fedora + Python)
  - [x] **Verificación (QA Mandatory)**: Evidencia en `test-evidence.md`
- [x] **Tarea 2: Extracción de Datos Históricos (HU2)**
  - [x] Script de extracción `nba_api`
  - [x] Manejo de errores y rate limiting
  - [x] **Verificación**: Extracción exitosa de 3 temporadas (7,380 juegos) en formato Parquet
- [x] **Tarea 3: Infraestructura GCP (HU3)**
  - [x] Terraform para Bucket GCS (archivos creados en infra/)
  - [x] Integración script -> GCS (soporte añadido en ingestion.py)
  - [x] **Verificación**: Código de Terraform listo e integración validada mediante logs
- [x] **Tarea 4: EDA Inicial (HU4)**
  - [x] Script de limpieza y reporte de correlación
  - [x] Identificación de features candidatas (DREB, FG_PCT, AST, TOV)
  - [x] **Verificación**: Reporte generado en data/processed/eda_report.txt

### Sprint 2: Modelado, Backtesting y MLOps [Status: 0%]
- [ ] **Tarea 1: Pipeline de Entrenamiento Multi-Modelo (HU1)**
- [ ] **Tarea 2: Validación Temporal y Ponderación (HU2)**
- [ ] **Tarea 3: Evaluación ROI y EV (HU3)**
- [ ] **Tarea 4: Tracking con MLflow (HU4)**
