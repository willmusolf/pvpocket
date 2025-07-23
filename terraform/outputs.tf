output "app_engine_url" {
  description = "The URL of the App Engine application"
  value       = "https://${var.project_id}.uc.r.appspot.com"
}

output "app_engine_service_account_email" {
  description = "Email of the App Engine service account"
  value       = google_service_account.app_engine.email
}

output "cloud_run_jobs_service_account_email" {
  description = "Email of the Cloud Run jobs service account"
  value       = google_service_account.cloud_run_jobs.email
}

output "firebase_storage_bucket" {
  description = "Name of the Firebase storage bucket"
  value       = google_storage_bucket.firebase_storage.name
}

output "cdn_bucket" {
  description = "Name of the CDN bucket"
  value       = google_storage_bucket.cdn_bucket.name
}

output "cdn_url" {
  description = "URL for CDN bucket"
  value       = "https://storage.googleapis.com/${google_storage_bucket.cdn_bucket.name}"
}

output "secret_manager_secrets" {
  description = "List of Secret Manager secret names"
  value       = [for secret in google_secret_manager_secret.secrets : secret.secret_id]
}

output "logs_bucket" {
  description = "Name of the logs storage bucket"
  value       = google_storage_bucket.logs_bucket.name
}

output "uptime_check_id" {
  description = "ID of the uptime monitoring check"
  value       = google_monitoring_uptime_check_config.app_uptime.uptime_check_id
}