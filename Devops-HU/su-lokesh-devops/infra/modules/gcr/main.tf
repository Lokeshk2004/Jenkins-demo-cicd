# -----------------------------------------------
# GCR Module — GCP Service Account for Container Registry
# -----------------------------------------------

resource "google_service_account" "gcr" {
  account_id   = "${var.project_tag}-gcr-sa"
  display_name = "GCR Service Account for ${var.project_tag}"
  project      = var.gcp_project_id
}

resource "google_project_iam_member" "gcr_storage_admin" {
  project = var.gcp_project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.gcr.email}"
}

resource "google_service_account_key" "gcr" {
  service_account_id = google_service_account.gcr.name
}

# Store the GCR SA key in AWS Secrets Manager
resource "aws_secretsmanager_secret" "gcr_key" {
  name        = "${var.project_tag}-gcr-sa-key"
  description = "GCP Service Account key for GCR access"

  tags = { Name = "${var.project_tag}-gcr-sa-key" }
}

resource "aws_secretsmanager_secret_version" "gcr_key" {
  secret_id     = aws_secretsmanager_secret.gcr_key.id
  secret_string = base64decode(google_service_account_key.gcr.private_key)
}
