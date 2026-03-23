variable "project_id" {
  description = "El ID del proyecto de Google Cloud"
  type        = string
}

variable "region" {
  description = "Región de despliegue"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Nombre del microservicio Cloud Run"
  type        = string
  default     = "oracle-nba-service"
}

variable "image_url" {
  description = "URL de la imagen Docker"
  type        = string
  default     = "us-central1-docker.pkg.dev/project-id/repo/oracle-nba:latest"
}
