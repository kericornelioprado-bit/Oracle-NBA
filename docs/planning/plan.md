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

### Sprint 2: Modelado, Backtesting y MLOps [Status: 80%]
- [x] **Tarea 1: Pipeline de Entrenamiento Multi-Modelo (HU1)**
- [x] **Tarea 2: Validación Temporal y Ponderación (HU2)**
- [x] **Tarea 3: Evaluación ROI y EV (HU3)**
- [x] **Tarea 4: Tracking con MLflow (HU4)**

### Sprint 2.5: Experimentación Avanzada (PM Request) [Status: 100%]
- [x] **Tarea 1: Tuning Inteligente con Optuna (HU1)**
  - [x] ROI incrementado al 22.2%.
- [x] **Tarea 2: Meta-Modelo de Stacking (HU2)**
  - [x] Accuracy incrementado al 62.9%.
- [x] **Tarea 3: Ingeniería de Ventanas Dinámicas (HU3)**
  - [x] **ROI FINAL: 24.29%** | **Win Rate: 65.1%**
  - [x] Ventanas [3, 5, 10, 20] implementadas.

### Sprint 3: Despliegue y Paper Trading [Status: 100%]
- [x] **Tarea 1: Pipeline de Inferencia Diaria (HU1)**
  - [x] Script `inference.py` operativo con live data.
- [x] **Tarea 2: Contenerización y Cloud Run (HU2)**
  - [x] Dockerfile y CI/CD implementados.
- [x] **Tarea 3: Automatización con Cloud Scheduler (HU3)**
  - [x] Flujo de email programado y persistencia en BigQuery.

### Sprint 4: Value Betting & Capital Management (v2) [Status: 100%]
- [x] **Tarea 1: Integración de Cuotas Reales (HU1)**
  - [x] Módulo `odds_api.py` creado con *Line Shopping* (Bet365, Betway, Pinnacle).
- [x] **Tarea 2: Motor de Valor Esperado (HU2)**
  - [x] Cálculo dinámico de EV y filtro de seguridad > 2% en `inference.py`.
- [x] **Tarea 3: Gestión de Riesgo Kelly (HU3)**
  - [x] Implementación de Fraction Kelly (0.25) para sizing de apuestas.
- [x] **Tarea 4: UX de Inversión (HU4)**
  - [x] Nuevo reporte HTML financiero (Banca virtual de $1,000 USD, métricas y colores dinámicos).
- [x] **Tarea 5: Orquestación Estratégica (HU5)**
  - [x] Ventana dorada establecida para ejecución óptima.
