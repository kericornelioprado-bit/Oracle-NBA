provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "nba_data_lake" {
  name          = "${var.project_id}-nba-data-lake"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}
