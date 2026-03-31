# Configuración de Terraform para el Oráculo NBA v2

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. BUCKET PARA DATA LAKE (Ya existente en la versión previa)
resource "google_storage_bucket" "nba_data_lake" {
  name          = "${var.project_id}-nba-data-lake"
  location      = var.region
  force_destroy = true
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

# 2. BIGQUERY: Dataset y Tabla para Predicciones e Histórico
resource "google_bigquery_dataset" "oracle_ds" {
  dataset_id                  = "oracle_nba_ds"
  friendly_name               = "NBA Predictions Dataset"
  description                 = "Almacena las predicciones diarias y metadatos del Oráculo NBA"
  location                    = var.region
  delete_contents_on_destroy  = false
}

resource "google_bigquery_table" "predictions_table" {
  dataset_id = google_bigquery_dataset.oracle_ds.dataset_id
  table_id   = "predictions"
  deletion_protection = false

  schema = <<EOF
[
  {"name": "game_id", "type": "STRING", "mode": "REQUIRED", "description": "ID único del partido"},
  {"name": "game_date", "type": "DATE", "mode": "REQUIRED", "description": "Fecha del partido"},
  {"name": "home_team_id", "type": "INTEGER", "mode": "REQUIRED", "description": "ID equipo local"},
  {"name": "away_team_id", "type": "INTEGER", "mode": "REQUIRED", "description": "ID equipo visitante"},
  {"name": "prob_home_win", "type": "FLOAT64", "mode": "REQUIRED", "description": "Probabilidad local"},
  {"name": "recommendation", "type": "STRING", "mode": "REQUIRED", "description": "HOME/AWAY/SKIP"},
  {"name": "model_version", "type": "STRING", "mode": "NULLABLE", "description": "Versión del modelo"},
  {"name": "experiment_id", "type": "STRING", "mode": "NULLABLE", "description": "ID MLflow"},
  {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED", "description": "Momento de inserción"}
]
EOF
}

# 3. IDENTIDAD: Service Account aislada (Golden Path)
resource "google_service_account" "cloud_run_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "SA para Cloud Run ${var.service_name}"
  project      = var.project_id
}

# Permisos para BigQuery Data Editor y Storage Object Admin
resource "google_project_iam_member" "bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "gcs_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# 4. CÓMPUTO: Cloud Run V2 (Golden Path)
resource "google_cloud_run_v2_service" "default" {
  name     = var.service_name
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.cloud_run_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = var.image_url

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      # Secretos inyectados desde Secret Manager (Definidos en ARCHITECTURE.md)
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      
      # Nota: GMAIL_USER y GMAIL_APP_PASSWORD se asumen creados en Secret Manager
      # El CI/CD o el SRE los configurará manualmente para seguridad total.
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image
    ]
  }
}

# 5. ORQUESTACIÓN: Cloud Scheduler (Ejecución Diaria)
resource "google_cloud_scheduler_job" "daily_job" {
  name             = "oracle-nba-daily-trigger"
  description      = "Disparador diario para predicciones NBA"
  schedule         = "30 16 * * *"
  time_zone        = "America/Chicago"
  attempt_deadline = "320s"
  project          = var.project_id
  region           = var.region

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = google_cloud_run_v2_service.default.uri
    oidc_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }
}

# 6. PERMISOS: Permitir que la SA invoque Cloud Run (Arregla error 401)
resource "google_cloud_run_v2_service_iam_member" "invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.default.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# --- NUEVA INFRAESTRUCTURA V2 (SPRINTS 4 Y 5) ---

resource "google_bigquery_dataset" "oracle_v2_ds" {
  dataset_id                  = "oracle_nba_v2"
  friendly_name               = "NBA Props V2 Dataset"
  description                 = "Almacena bankroll, historial y portafolio de V2"
  location                    = var.region
  delete_contents_on_destroy  = false
}

resource "google_bigquery_table" "virtual_bankroll_table" {
  dataset_id = google_bigquery_dataset.oracle_v2_ds.dataset_id
  table_id   = "virtual_bankroll"
  deletion_protection = false

  schema = <<EOF
[
  {"name": "current_balance", "type": "FLOAT64", "mode": "REQUIRED", "description": "Saldo actual en USD"},
  {"name": "last_updated", "type": "TIMESTAMP", "mode": "REQUIRED", "description": "Última fecha de modificación"}
]
EOF
}

resource "google_bigquery_table" "bet_history_table" {
  dataset_id = google_bigquery_dataset.oracle_v2_ds.dataset_id
  table_id   = "bet_history"
  deletion_protection = false

  schema = <<EOF
[
  {"name": "bet_id", "type": "STRING", "mode": "REQUIRED", "description": "UUID de la apuesta"},
  {"name": "player_name", "type": "STRING", "mode": "REQUIRED", "description": "Nombre del jugador"},
  {"name": "market", "type": "STRING", "mode": "REQUIRED", "description": "Mercado (REB, AST)"},
  {"name": "line", "type": "FLOAT64", "mode": "REQUIRED", "description": "Línea de la casa"},
  {"name": "odds_open", "type": "FLOAT64", "mode": "REQUIRED", "description": "Cuota al apostar"},
  {"name": "odds_close", "type": "FLOAT64", "mode": "NULLABLE", "description": "Cuota de cierre (CLV)"},
  {"name": "stake_usd", "type": "FLOAT64", "mode": "REQUIRED", "description": "Monto apostado"},
  {"name": "result", "type": "STRING", "mode": "REQUIRED", "description": "PENDING/WIN/LOSS"},
  {"name": "payout", "type": "FLOAT64", "mode": "REQUIRED", "description": "Retorno neto"},
  {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED", "description": "Momento de inserción"}
]
EOF
}

resource "google_bigquery_table" "top_20_portfolio_table" {
  dataset_id = google_bigquery_dataset.oracle_v2_ds.dataset_id
  table_id   = "top_20_portfolio"
  deletion_protection = false

  schema = <<EOF
[
  {"name": "tier", "type": "INTEGER", "mode": "REQUIRED", "description": "Tier del jugador"},
  {"name": "player_id", "type": "INTEGER", "mode": "REQUIRED", "description": "ID NBA"},
  {"name": "minute_swing", "type": "FLOAT64", "mode": "REQUIRED", "description": "Sensibilidad al margen"},
  {"name": "updated_at", "type": "TIMESTAMP", "mode": "REQUIRED", "description": "Fecha de actualización"}
]
EOF
}

# Job de Liquidación (03:00 AM)
resource "google_cloud_scheduler_job" "settle_bets_job" {
  name             = "oracle-nba-settle-bets"
  description      = "Liquida apuestas del día anterior y actualiza Bankroll"
  schedule         = "0 3 * * *"
  time_zone        = "America/Chicago"
  attempt_deadline = "320s"
  project          = var.project_id
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.default.uri}/settle"
    oidc_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }
}

# Job del Portafolio (Domingos 23:59)
resource "google_cloud_scheduler_job" "sunday_update_job" {
  name             = "oracle-nba-sunday-update"
  description      = "Recalcula el Top 20 semanalmente"
  schedule         = "59 23 * * 0"
  time_zone        = "America/Chicago"
  attempt_deadline = "320s"
  project          = var.project_id
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.default.uri}/update_portfolio"
    oidc_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }
}
