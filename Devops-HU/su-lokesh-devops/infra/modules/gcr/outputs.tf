output "secret_arn" {
  description = "ARN of the Secrets Manager secret storing GCR SA key"
  value       = aws_secretsmanager_secret.gcr_key.arn
}

output "gcr_service_account_email" {
  description = "GCR service account email"
  value       = google_service_account.gcr.email
}
