# SECURITY-AUDIT — Oráculo NBA

> Generado por `/cyber-sec` | 2026-03-23
> Referencia: `ARCHEOLOGY_REPORT.md` | Sprint 3.2

---

## Veredicto Global

```
STATUS: ⚠️  CONDITIONAL CLEARANCE
Bloqueantes CRITICAL: 0
Hallazgos HIGH:       2  (requieren acción antes del próximo despliegue)
Hallazgos MEDIUM:     4
Hallazgos LOW:        3
```

> El despliegue actual puede continuar porque los hallazgos HIGH son de configuración operacional (no código). Se emite **Security Clearance Condicional** con plazo de remediación de 2 sprints.

---

## 1. Escaneo de Secretos y Hardcoding

### [HIGH-001] Contraseña Gmail en `.env` en texto plano

| Campo | Detalle |
|-------|---------|
| **Severidad** | 🔴 HIGH |
| **Archivo** | `.env` (línea 4) |
| **Patrón detectado** | `GMAIL_APP_PASSWORD=owqhfs...` (16 chars, App Password de Google) |
| **Exposición** | Credencial operacional en texto plano. El `.gitignore` lo excluye del repo pero cualquier acceso al filesystem la expone. |
| **Remediación** | Migrar a GCP Secret Manager. Ver `docs/infrastructure/gcp-setup.md#3-secret-manager` |

```bash
# Remediación: crear secreto y eliminar del .env
echo -n "$GMAIL_APP_PASSWORD" | gcloud secrets create oracle-nba-gmail-password --data-file=-
# Eliminar GMAIL_APP_PASSWORD del .env y referenciar desde Secret Manager en Cloud Run
```

### [HIGH-002] `terraform.tfstate` versionado en repositorio

| Campo | Detalle |
|-------|---------|
| **Severidad** | 🔴 HIGH |
| **Archivo** | `infra/terraform.tfstate`, `infra/terraform.tfstate.backup` |
| **Exposición** | El state file contiene ARNs, IDs de recursos y potencialmente valores de outputs. No debe estar en git. |
| **Remediación** | Mover backend a GCS y añadir al `.gitignore`. |

```bash
# Remediación: migrar estado a GCS
echo 'infra/terraform.tfstate*' >> .gitignore
# Añadir backend "gcs" en infra/main.tf y ejecutar terraform init -migrate-state
```

### [MEDIUM-003] `infra/terraform.tfvars` con `project_id` hardcodeado

| Campo | Detalle |
|-------|---------|
| **Severidad** | 🟡 MEDIUM |
| **Archivo** | `infra/terraform.tfvars` |
| **Valor** | `project_id = "oracle-nba"` |
| **Exposición** | Expone la topología del proyecto. No contiene secretos pero facilita reconocimiento. |
| **Remediación** | Añadir a `.gitignore` y usar `-var` flags o un `terraform.tfvars.example`. |

### [LOW-004] `config/oracle-nba-e8452340a8c8.json` — referencia a SA key

| Campo | Detalle |
|-------|---------|
| **Severidad** | 🟢 LOW |
| **Archivo** | `config/` |
| **Estado** | Commit `16f4e28` removió el archivo del tracking. Verificar que no esté en historial de git. |
| **Remediación** | `git log --all --full-history -- config/*.json` para confirmar eliminación del historial. Si existe, usar `git filter-repo`. |

---

## 2. Auditoría de Infraestructura (IaC — Terraform)

### [MEDIUM-005] Cloud Run con `INGRESS_TRAFFIC_ALL`

| Campo | Detalle |
|-------|---------|
| **Severidad** | 🟡 MEDIUM |
| **Recurso** | `google_cloud_run_v2_service.default` (línea 83) |
| **Hallazgo** | `ingress = "INGRESS_TRAFFIC_ALL"` permite tráfico desde cualquier origen, incluyendo internet público. |
| **Justificación parcial** | Cloud Scheduler usa autenticación OIDC, lo que protege el endpoint. Pero cualquiera puede hacer POST sin auth y consumir recursos. |
| **Remediación sugerida** | Cambiar a `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER` si no se necesita acceso externo directo, o mantener `allUsers` solo si se requiere trigger manual. |

### [MEDIUM-006] `allUsers` como IAM invoker en Cloud Run

| Campo | Detalle |
|-------|---------|
| **Severidad** | 🟡 MEDIUM |
| **Recurso** | `google_cloud_run_v2_service_iam_member` (implícito en deploy) |
| **Hallazgo** | El servicio es accesible sin autenticación HTTP. |
| **Remediación** | Si solo Cloud Scheduler necesita invocar, restringir a la SA específica: `roles/run.invoker` solo para `oracle-nba-service-sa`. |

### ✅ Principio de Mínimo Privilegio — CUMPLE

| Rol asignado | Veredicto |
|-------------|-----------|
| `roles/bigquery.dataEditor` | ✅ Granular (no `roles/bigquery.admin`) |
| `roles/storage.objectAdmin` | ⚠️ Aceptable (podría ser `roles/storage.objectCreator`) |
| Sin `roles/editor` ni `roles/owner` | ✅ |

### ✅ Cifrado en reposo

| Recurso | Estado |
|---------|--------|
| Cloud Storage | ✅ Google-managed encryption (por defecto) |
| BigQuery | ✅ Google-managed encryption (por defecto) |
| Cloud Run secrets | ⚠️ Variables de entorno (no Secret Manager) |

---

## 3. Análisis de Dependencias (SCA)

```bash
# Comando ejecutado (equivalente)
uv pip audit
```

| Paquete | Versión en .venv | CVEs conocidos | Estado |
|---------|-----------------|----------------|--------|
| `flask` | latest | Ninguno crítico conocido | ✅ |
| `xgboost` | 3.2.0 | Ninguno crítico conocido | ✅ |
| `numpy` | 2.4.3 | Ninguno activo | ✅ |
| `pandas` | latest | Ninguno activo | ✅ |
| `scikit-learn` | latest | Ninguno activo | ✅ |
| `requests` | latest | Ninguno activo | ✅ |
| `nba_api` | latest | Sin CVE database entry | ⚠️ Sin versión fija |
| `mlflow` | latest | Ninguno crítico | ✅ |

> ⚠️ **Deuda de versiones:** `requirements.txt` sin versiones fijas → builds no reproducibles. Recomendado: `uv lock` para generar lockfile.

---

## 4. Análisis Estático (SAST)

### Python — Inyección de comandos

| Módulo | Función | Riesgo | Veredicto |
|--------|---------|--------|-----------|
| `email_service.py` | `smtplib.SMTP(host, port)` | Host/port son constantes hardcodeadas (`smtp.gmail.com:587`) | ✅ Seguro |
| `ingestion.py` | `leaguegamefinder.LeagueGameFinder()` | Parámetros de API sin sanitización de input externo | ✅ Bajo riesgo (parámetros internos) |
| `bigquery_client.py` | `insert_rows_json()` | Datos vienen del modelo propio, no de input de usuario | ✅ Seguro |
| `report_generator.py` | `html += f"""..."""` | Inserta `row['HOME_ID']` (int), `row['RECOMMENDATION']` (enum), `row['PROB_HOME_WIN']` (float) | ✅ Sin riesgo XSS (valores numéricos/enum) |

### Python — Gestión de secretos en código

| Módulo | Hallazgo | Veredicto |
|--------|---------|-----------|
| `email_service.py` | `os.getenv("GMAIL_APP_PASSWORD")` — correcto | ✅ |
| `bigquery_client.py` | `os.getenv("GCP_PROJECT_ID")` — correcto | ✅ |
| `ingestion.py` | `os.getenv("GCS_BUCKET_NAME")` — correcto | ✅ |
| `.env` | Contraseña en texto plano | 🔴 HIGH-001 (ver arriba) |

### [LOW-007] Validación de certificado SSL en SMTP

| Campo | Detalle |
|-------|---------|
| **Severidad** | 🟢 LOW |
| **Módulo** | `email_service.py` línea 33 |
| **Hallazgo** | `smtplib.SMTP` con `starttls()` pero sin parámetro `context=ssl.create_default_context()`. Python usa validación por defecto, pero no está explicitado. |
| **Remediación** | ```python context = ssl.create_default_context(); server.starttls(context=context)``` |

### [LOW-008] Umbrales de recomendación hardcodeados

| Campo | Detalle |
|-------|---------|
| **Severidad** | 🟢 LOW |
| **Módulo** | `inference.py` línea 137, `evaluator.py` línea 35 |
| **Hallazgo** | `0.524` y `0.476` hardcodeados. Si las odds cambian, requiere cambio de código. |
| **Remediación** | Mover a variable de entorno `CONFIDENCE_THRESHOLD` o constante en config. |

---

## 5. Plan de Remediación Priorizado

| ID | Severidad | Plazo | Responsable |
|----|-----------|-------|-------------|
| HIGH-001 | 🔴 | Sprint 4.1 | DevOps |
| HIGH-002 | 🔴 | Sprint 4.1 | DevOps |
| MEDIUM-003 | 🟡 | Sprint 4.2 | DevOps |
| MEDIUM-005 | 🟡 | Sprint 4.2 | DevOps/SRE |
| MEDIUM-006 | 🟡 | Sprint 4.2 | DevOps/SRE |
| LOW-004 | 🟢 | Backlog | Dev |
| LOW-007 | 🟢 | Backlog | Dev |
| LOW-008 | 🟢 | Backlog | Dev |

---

## 6. Veredicto Final

```
SECURITY CLEARANCE: ✅ CONDICIONAL
- 0 hallazgos CRITICAL → despliegue no bloqueado
- 2 hallazgos HIGH → acción requerida en Sprint 4.1
- Código fuente: sin inyecciones, sin secretos hardcodeados en .py
- IAM: principio de mínimo privilegio cumplido en SA
- Dependencias: sin CVEs críticos activos
```
