# Manual de Infraestructura GCP — Oráculo NBA

> Generado por `/technical-writer` + `/devops-deploy` | 2026-03-23
> IaC: Terraform `>= 5.0.0` | Región: `us-central1` | Proyecto: `oracle-nba`

---

## 1. Prerrequisitos

```bash
# Herramientas requeridas
terraform >= 1.5.0
gcloud CLI >= 450.0.0
docker >= 24.0.0
uv >= 0.4.0
```

Autenticación local:
```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project oracle-nba
```

---

## 2. Recursos GCP Declarados (Terraform)

### 2.1 Cloud Storage — Data Lake

| Campo | Valor |
|-------|-------|
| Nombre del bucket | `oracle-nba-nba-data-lake` |
| Región | `us-central1` |
| Versionado | Habilitado |
| Acceso | Uniform Bucket Level Access |
| Destrucción | `force_destroy = true` (datos experimentales) |

**Uso:** Almacenamiento de archivos Parquet crudos y procesados subidos por `NBADataIngestor`.

### 2.2 BigQuery — Dataset y Tabla de Predicciones

| Campo | Valor |
|-------|-------|
| Dataset ID | `oracle_nba_ds` |
| Tabla | `predictions` |
| Región | `us-central1` |
| Destrucción | `delete_contents_on_destroy = false` (protegido) |

**Schema de la tabla `predictions`:**

| Campo | Tipo | Modo | Descripción |
|-------|------|------|-------------|
| `game_id` | STRING | REQUIRED | ID único del partido (NBA API) |
| `game_date` | DATE | REQUIRED | Fecha del partido |
| `home_team_id` | INTEGER | REQUIRED | ID equipo local |
| `away_team_id` | INTEGER | REQUIRED | ID equipo visitante |
| `prob_home_win` | FLOAT64 | REQUIRED | Probabilidad local (0–1) |
| `recommendation` | STRING | REQUIRED | HOME / AWAY / SKIP |
| `model_version` | STRING | NULLABLE | Versión del modelo |
| `experiment_id` | STRING | NULLABLE | MLflow run ID |
| `timestamp` | TIMESTAMP | REQUIRED | Momento de inserción |

### 2.3 Service Account (IAM)

| Campo | Valor |
|-------|-------|
| Account ID | `oracle-nba-service-sa` |
| Email | `oracle-nba-service-sa@oracle-nba.iam.gserviceaccount.com` |
| Roles asignados | `roles/bigquery.dataEditor`, `roles/storage.objectAdmin` |

> ⚠️ **Principio de Mínimo Privilegio:** La SA NO tiene `roles/editor` ni `roles/owner`. Solo puede escribir en BigQuery y GCS.

### 2.4 Cloud Run v2

| Campo | Valor |
|-------|-------|
| Nombre del servicio | `oracle-nba-service` |
| Región | `us-central1` |
| Imagen | `us-central1-docker.pkg.dev/oracle-nba/oracle-nba-repo/oracle-nba:latest` |
| CPU | 1 vCPU |
| Memoria | 512 Mi |
| Escala mínima | 0 instancias (cold start) |
| Escala máxima | 1 instancia |
| Ingress | `INGRESS_TRAFFIC_ALL` |
| Service Account | `oracle-nba-service-sa` |
| Timeout | 600 segundos (Gunicorn) |

**Variables de entorno inyectadas:**

| Variable | Fuente | Descripción |
|----------|--------|-------------|
| `GCP_PROJECT_ID` | Terraform (valor directo) | ID del proyecto GCP |
| `GMAIL_USER` | GitHub Secret → `gcloud run deploy` | Email remitente |
| `GMAIL_APP_PASSWORD` | GitHub Secret → `gcloud run deploy` | App password de Gmail |
| `GCS_BUCKET_NAME` | (manual o Terraform output) | Nombre del bucket de datos |

### 2.5 Cloud Scheduler

| Campo | Valor |
|-------|-------|
| Nombre del job | `oracle-nba-daily-trigger` |
| Schedule | `0 14 * * *` (14:00 UTC diario) |
| Zona horaria | UTC |
| Método HTTP | POST |
| URL destino | `${google_cloud_run_v2_service.default.uri}` |
| Autenticación | OIDC token (SA: `oracle-nba-service-sa`) |
| Intentos | 1 retry |
| Deadline | 320 segundos |

### 2.6 Artifact Registry

| Campo | Valor |
|-------|-------|
| Repositorio | `oracle-nba-repo` |
| Región | `us-central1` |
| URL | `us-central1-docker.pkg.dev/oracle-nba/oracle-nba-repo/` |
| Imagen | `oracle-nba:{github.sha}` |

---

## 3. Secret Manager (Pendiente de implementar)

> Los secretos actualmente se inyectan vía GitHub Secrets directo a `gcloud run deploy`. La migración a Secret Manager está pendiente.

**Secretos requeridos (nombres sugeridos):**

| Nombre en Secret Manager | Variable de entorno | Descripción |
|--------------------------|---------------------|-------------|
| `oracle-nba-gmail-user` | `GMAIL_USER` | Email remitente de Gmail |
| `oracle-nba-gmail-password` | `GMAIL_APP_PASSWORD` | App password de Gmail |
| `oracle-nba-gcs-bucket` | `GCS_BUCKET_NAME` | Nombre del bucket de datos |

**Pasos de migración:**
```bash
# Crear secretos en Secret Manager
echo -n "tu@gmail.com" | gcloud secrets create oracle-nba-gmail-user --data-file=-
echo -n "apppassword" | gcloud secrets create oracle-nba-gmail-password --data-file=-

# Dar acceso a la SA al secreto
gcloud secrets add-iam-policy-binding oracle-nba-gmail-user \
  --member="serviceAccount:oracle-nba-service-sa@oracle-nba.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 4. Despliegue desde Cero

### 4.1 Infraestructura (Terraform)

```bash
cd infra/

# Inicializar providers
terraform init

# Revisar plan (sin cambios destructivos)
terraform plan -var-file="terraform.tfvars"

# Aplicar
terraform apply -var-file="terraform.tfvars"
```

> 💡 Mover el estado a GCS backend para trabajo en equipo:
> ```hcl
> terraform {
>   backend "gcs" {
>     bucket = "oracle-nba-nba-data-lake"
>     prefix = "terraform/state"
>   }
> }
> ```

### 4.2 Primera imagen Docker (manual)

```bash
# Autenticar Docker con Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build y push
docker build -t us-central1-docker.pkg.dev/oracle-nba/oracle-nba-repo/oracle-nba:latest .
docker push us-central1-docker.pkg.dev/oracle-nba/oracle-nba-repo/oracle-nba:latest
```

### 4.3 Deploy manual (sin CI/CD)

```bash
gcloud run deploy oracle-nba-service \
  --image us-central1-docker.pkg.dev/oracle-nba/oracle-nba-repo/oracle-nba:latest \
  --region us-central1 \
  --set-env-vars "GMAIL_USER=tu@gmail.com,GMAIL_APP_PASSWORD=xxx,GCP_PROJECT_ID=oracle-nba"
```

---

## 5. Control Local (ctl.sh)

El script `ctl.sh` en la raíz del repositorio gestiona el servicio Flask localmente.

```bash
# Iniciar (usa uv run python3 main.py con nohup)
./ctl.sh start

# Ver estado
./ctl.sh status

# Detener
./ctl.sh stop

# Reiniciar
./ctl.sh restart
```

**Logs locales:** `oracle-nba_local.log`
**PID file:** `.oracle-nba.pid`

---

## 6. GitHub Actions — Secrets Requeridos

Configurar en: `Settings → Secrets and variables → Actions`

| Secret | Descripción |
|--------|-------------|
| `GCP_SA_KEY` | JSON de la Service Account con permisos de Artifact Registry y Cloud Run |
| `GCP_PROJECT_ID` | `oracle-nba` |
| `GMAIL_USER` | Email de Gmail remitente |
| `GMAIL_APP_PASSWORD` | App Password de Gmail (no la contraseña real) |

---

## 7. Comandos de Diagnóstico

```bash
# Ver logs del servicio en Cloud Run
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=oracle-nba-service" \
  --limit=50 --format="table(timestamp,textPayload)"

# Ver última ejecución del Scheduler
gcloud scheduler jobs describe oracle-nba-daily-trigger --location=us-central1

# Consultar predicciones en BigQuery
bq query --use_legacy_sql=false \
  'SELECT game_date, COUNT(*) as predicciones,
   COUNTIF(recommendation="HOME") as home,
   COUNTIF(recommendation="AWAY") as away,
   COUNTIF(recommendation="SKIP") as skip
   FROM oracle_nba_ds.predictions
   GROUP BY game_date ORDER BY game_date DESC LIMIT 7'

# Smoke test manual contra Cloud Run
curl -X POST https://oracle-nba-service-xxxx.a.run.app/ \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"
```

---

## 8. Estimación de Costos Mensuales

| Recurso | Uso estimado | Costo aproximado |
|---------|-------------|------------------|
| Cloud Run (1 ejecución/día, ~5 min) | ~150 min/mes | < $0.10 |
| Cloud Scheduler (1 job) | 1 invocación/día | $0.10 |
| BigQuery (inserción + query) | < 1 MB/día | < $0.01 |
| Cloud Storage (parquets) | < 500 MB | < $0.01 |
| Artifact Registry (imágenes) | ~1 GB | ~$0.10 |
| **Total estimado** | | **< $0.50 / mes** |

> ✅ Muy por debajo del umbral de $5 USD del cost gate de `/devops-deploy`.
