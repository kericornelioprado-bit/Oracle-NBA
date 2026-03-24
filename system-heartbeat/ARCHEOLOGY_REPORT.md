# ARCHEOLOGY_REPORT.md
> Auditoría técnica industrial del repositorio **Oráculo NBA**
> Fecha: 2026-03-23 (actualizado) | Agente: `/archeology` | Destino: `/factory-lead`

---

## 1. Project_State

```
STATUS: BROWNFIELD
```

| Métrica | Valor |
|---------|-------|
| Archivos totales (excl. .git, .venv, mlruns) | **73** |
| Archivos Python en `src/` | 16 |
| Archivos de test en `tests/` | 11 |
| Commits en rama `main` | 3 |
| Cobertura de tests actual | **95%** |
| Tamaño lógico del repo | ~1.4 GB (incl. datos) |

**Diagnóstico:** Proyecto Python de Data Science / MLOps en etapa Sprint 3. Arquitectura modular (`src/data`, `src/models`, `src/utils`), infraestructura GCP vía Terraform, CI/CD con GitHub Actions. Funcional y con suite de tests robusta.

---

## 2. Structural_Debt (STRUCTURAL_DEBT_LIST)

Contraste contra `GEMINI.md` — Lista Blanca de archivos permitidos en raíz:
`main.py`, `ctl.sh`, `Dockerfile`, `requirements.txt`, `ARCHITECTURE.md`, `PRD.md`, `research.md`, `GEMINI.md`, `README.md`, `.gitignore`, `.env.example`, `infra/`, `src/`, `tests/`, `.github/`, `data/`, `models/`, `config/`, `notebooks/`

### Archivos Infractores

| # | Archivo | Ubicación Actual | Carpeta Destino Sugerida | Severidad | Justificación |
|---|---------|-----------------|--------------------------|-----------|---------------|
| 1 | `mlflow.db` | `/` (raíz) | `data/mlflow/` | 🔴 Alta | Artefacto de base de datos MLflow. No pertenece a la raíz; debe estar en `data/` o ignorado. |
| 2 | `mlruns/` | `/` (raíz) | `data/mlruns/` | 🔴 Alta | Directorio de experimentos MLflow. Dato volátil que no debería vivir en raíz. |
| 3 | `Sprints.md` | `/` (raíz) | `docs/` | 🟡 Media | Documento de planificación ágil. No es artefacto técnico del sistema. |
| 4 | `plan.md` | `/` (raíz) | `docs/` | 🟡 Media | Plan de trabajo interno. No referenciado en `GEMINI.md`. |
| 5 | `test-evidence.md` | `/` (raíz) | `docs/` o `tests/` | 🟡 Media | Evidencia de tests manuales. Debería residir junto a los tests. |
| 6 | `pruebas.md` | `/` (raíz) | `docs/` o `tests/` | 🟡 Media | Notas de pruebas ad-hoc. Candidato a eliminar o migrar. |
| 7 | `proyectoinicial.md` | `/` (raíz) | `docs/` | 🟡 Media | Documento de ideación inicial. Histórico, no operacional. |
| 8 | `.coverage` | `/` (raíz) | Gitignore | 🟢 Baja | Artefacto de cobertura. Debe añadirse a `.gitignore`. |
| 9 | `__pycache__/` | `/` (raíz) | Gitignore | 🟢 Baja | Cache Python en raíz. Ya está en `.gitignore` pero persiste localmente. |
| 10 | `.pytest_cache/` | `/` (raíz) | Gitignore | 🟢 Baja | Cache pytest. Idem anterior. |

**Total deuda estructural detectada:** 10 elementos (2 altos, 5 medios, 3 bajos)

### Adiciones Sugeridas al `.gitignore`
```gitignore
# MLflow local artifacts
mlflow.db
mlruns/

# Coverage artifacts
.coverage
htmlcov/

# Python cache
__pycache__/
*.pyc
.pytest_cache/
```

---

## 3. Tech_Stack_Audit

### Backend / Sidecar (Python)

| Componente | Versión Detectada | Gestor | Fuente |
|-----------|-------------------|--------|--------|
| **Python** | `3.11` (Dockerfile) / `3.12.13` (.venv actual) | `uv` | `Dockerfile`, `.venv` |
| **Flask** | Sin versión fija | `pip/uv` | `requirements.txt` |
| **XGBoost** | Sin versión fija (`3.2.0` en .venv) | `pip/uv` | `requirements.txt` |
| **scikit-learn** | Sin versión fija | `pip/uv` | `requirements.txt` |
| **MLflow** | Sin versión fija | `pip/uv` | `requirements.txt` |
| **Optuna** | Sin versión fija | `pip/uv` | `requirements.txt` |
| **pandas** | Sin versión fija | `pip/uv` | `requirements.txt` |
| **nba_api** | Sin versión fija | `pip/uv` | `requirements.txt` |
| **google-cloud-bigquery** | Sin versión fija | `pip/uv` | `requirements.txt` |
| **pytest** | `9.0.2` (.venv) | `pip/uv` | `.venv` |
| **pytest-cov** | `7.1.0` (.venv) | `pip/uv` | `.venv` |

> ⚠️ **Deuda de Versiones:** `requirements.txt` usa dependencias sin versiones fijas (`pandas`, `numpy`, etc.). No hay `pyproject.toml` en la raíz. Riesgo de builds no reproducibles. Recomendado: generar `uv lock` / `requirements-lock.txt`.

### Frontend

| Componente | Estado |
|-----------|--------|
| **React** | ❌ No existe |
| **Shadcn/ui** | ❌ No existe |
| **Tailwind CSS** | ❌ No existe |
| **package.json** | ❌ No encontrado |

> ℹ️ Proyecto sin frontend. Solo API backend (Flask) + email HTML estático.

### Backend Go

| Componente | Estado |
|-----------|--------|
| **Go** | ❌ No existe |
| **go.mod** | ❌ No encontrado |

> ℹ️ Stack Python puro, sin servicios Go.

---

## 4. Infra_Inventory (Terraform / GCP)

**Proveedor:** `hashicorp/google` | **Región:** `us-central1`

| Recurso Terraform | Nombre GCP | Tipo | Estado |
|-------------------|-----------|------|--------|
| `google_storage_bucket.nba_data_lake` | `oracle-nba-nba-data-lake` | Cloud Storage | Declarado |
| `google_bigquery_dataset.oracle_ds` | `oracle_nba_ds` | BigQuery Dataset | Declarado |
| `google_bigquery_table.predictions` | `oracle_nba_ds.predictions` | BigQuery Table | Declarado |
| `google_service_account.cloud_run_sa` | `cloud-run-sa@oracle-nba.iam...` | IAM Service Account | Declarado |
| `google_project_iam_member` (x2) | roles/bigquery.dataEditor, roles/storage.objectAdmin | IAM Binding | Declarado |
| `google_cloud_run_v2_service.default` | `oracle-nba-service` | Cloud Run v2 | Declarado |
| `google_cloud_scheduler_job.daily_job` | `daily-nba-oracle-job` | Cloud Scheduler | Declarado |
| `google_cloud_run_v2_service_iam_member` | AllUsers → invoker | IAM (Cloud Run) | ⚠️ Público |

### Schema BigQuery (`oracle_nba_ds.predictions`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `game_id` | STRING | ID de partido (NBA API) |
| `game_date` | DATE | Fecha del partido |
| `home_team_id` | INTEGER | ID equipo local |
| `away_team_id` | INTEGER | ID equipo visitante |
| `prob_home_win` | FLOAT | Probabilidad victoria local |
| `recommendation` | STRING | HOME / AWAY / SKIP |
| `model_version` | STRING | stacking_v1 |
| `experiment_id` | STRING | MLflow run ID |
| `timestamp` | TIMESTAMP | Momento de inserción |

### Observaciones de Seguridad en Infra

| Hallazgo | Severidad | Detalle |
|---------|-----------|---------|
| Cloud Run con `INGRESS_TRAFFIC_ALL` | 🔴 Alta | Servicio expuesto públicamente sin autenticación HTTP |
| Secrets (GMAIL_*) NO gestionados por Terraform | 🟡 Media | Comentados en `main.tf` línea 110–111; inyectados vía CI/CD |
| `terraform.tfvars` en repo | 🟡 Media | `project_id` hardcodeado; no contiene secretos pero expone topología |
| `terraform.tfstate` en repo | 🔴 Alta | Estado Terraform versionado localmente; debería estar en GCS backend |
| `allUsers` como invoker | 🔴 Alta | Cloud Run sin control de acceso (válido si es trigger público de Scheduler) |

---

## 5. Control_Status (ctl.sh)

**Archivo:** `ctl.sh` | **Permisos:** `-rwxr-xr-x` (755) | **Estado:** ✅ Ejecutable

### Cobertura de Servicios

| Servicio | Cubierto por ctl.sh | Comandos | Observación |
|---------|---------------------|----------|-------------|
| **Backend Flask** (`main.py`) | ✅ **SÍ** | start, stop, status, restart | Usa `uv run python3 main.py`, logs en `oracle-nba_local.log` |
| **Frontend** | ➖ N/A | — | No existe frontend |
| **Sidecar / ML Pipelines** | ❌ **Huérfano** | — | `ingestion.py`, `trainer.py`, `stacking_trainer.py` no tienen comando en ctl.sh |
| **Infraestructura (Terraform)** | ❌ **Huérfano** | — | No hay `deploy`, `plan`, `apply` en ctl.sh |
| **Tests** | ❌ **Huérfano** | — | No hay comando `test` en ctl.sh |

### Implementación Actual del ctl.sh

```bash
./ctl.sh start    → nohup uv run python3 main.py > oracle-nba_local.log 2>&1 &
./ctl.sh stop     → kill -15 <PID>
./ctl.sh status   → verifica PID file + ps
./ctl.sh restart  → stop + sleep 1 + start
```

### Comandos Huérfanos Sugeridos para Próxima Iteración

```bash
./ctl.sh ingest        → PYTHONPATH=. uv run python3 src/data/ingestion.py
./ctl.sh train         → PYTHONPATH=. uv run python3 src/models/stacking_trainer.py
./ctl.sh test          → uv run pytest tests/ --cov=src
./ctl.sh deploy-infra  → cd infra && terraform apply -auto-approve
./ctl.sh logs          → tail -f oracle-nba_local.log
```

---

## 6. Mapa de Riesgos Consolidado

| # | Hallazgo | Categoría | Severidad | Acción Recomendada |
|---|---------|-----------|-----------|-------------------|
| 1 | `.env` con `GMAIL_APP_PASSWORD` en texto plano | 🔐 Seguridad | 🔴 Crítico | Migrar a GitHub Secrets + GCP Secret Manager |
| 2 | `terraform.tfstate` versionado en repo | 🔐 Seguridad | 🔴 Crítico | Mover backend a GCS (`backend "gcs"`) |
| 3 | Cloud Run público (`allUsers`) | 🔐 Seguridad | 🔴 Alta | Restringir a Cloud Scheduler SA únicamente |
| 4 | `mlflow.db` y `mlruns/` en raíz | 🏗️ Estructura | 🔴 Alta | Mover a `data/mlflow/` y actualizar `.gitignore` |
| 5 | `requirements.txt` sin versiones fijas | 📦 Dependencias | 🟡 Media | Generar `uv lock` / `pip freeze > requirements-lock.txt` |
| 6 | CI/CD solo ejecuta `test_email_service.py` | 🧪 Calidad | 🟡 Media | Actualizar `deploy.yml` a `pytest tests/` |
| 7 | ML pipelines sin comandos en `ctl.sh` | 🏗️ Operacional | 🟡 Media | Añadir `ingest`, `train`, `test` al script |
| 8 | 7 archivos `.md` fuera de `docs/` | 🏗️ Estructura | 🟢 Baja | Crear `docs/` y migrar documentación |
| 9 | `.coverage` y `__pycache__` en raíz | 🏗️ Estructura | 🟢 Baja | Añadir a `.gitignore` |

---

## 7. Hand-off al Orquestador (`/factory-lead`)

```
PARA:    /factory-lead
DE:      /archeology
ESTADO:  BROWNFIELD — Proyecto Python MLOps funcional, Sprint 3 completo

RESUMEN EJECUTIVO:
  El repositorio Oráculo NBA es un sistema BROWNFIELD maduro con:
  - 73 archivos relevantes (excl. .git/.venv)
  - Stack Python 3.11/3.12 + GCP (Cloud Run + BigQuery + Scheduler)
  - Cobertura de tests: 95% (79 tests, 0 fallos)
  - CI/CD: GitHub Actions funcional (build → test → deploy)

DEUDA ESTRUCTURAL:
  - 10 elementos a mover/limpiar (STRUCTURAL_DEBT_LIST sección 2)
  - Prioridad 1 (bloqueante): mlflow.db/mlruns/ en raíz + .env con secretos
  - Prioridad 2 (mejora): requirements.txt sin versiones fijas
  - Prioridad 3 (cosmético): docs markdown dispersos en raíz

SERVICIOS HUÉRFANOS EN CTL.SH:
  - ML pipelines (ingestion, training)
  - Suite de tests
  - Terraform deploy

RESTRICCIÓN:
  Este agente NO ha realizado cambios. Solo diagnóstico factual.
  El ejecutor (/execute) debe procesar STRUCTURAL_DEBT_LIST.
```

---

*Reporte generado por `/archeology` — 2026-03-23 — Solo lectura, sin modificaciones al código fuente.*
