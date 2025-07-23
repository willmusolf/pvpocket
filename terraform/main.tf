terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  # Uncomment for remote state management
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "pokemon-tcg-pocket"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Local variables
locals {
  app_name = "pokemon-tcg-pocket"
  environment = var.environment
  
  common_labels = {
    app         = local.app_name
    environment = local.environment
    managed_by  = "terraform"
  }
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "appengine.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "run.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudscheduler.googleapis.com"
  ])
  
  service = each.key
  disable_on_destroy = false
}

# App Engine Application
resource "google_app_engine_application" "app" {
  project       = var.project_id
  location_id   = var.app_engine_location
  database_type = "CLOUD_FIRESTORE"
  
  depends_on = [google_project_service.apis]
}

# Firestore database (already created with App Engine, but ensuring configuration)
resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"
  
  depends_on = [google_app_engine_application.app]
}

# Firebase Storage bucket
resource "google_storage_bucket" "firebase_storage" {
  name          = "${var.project_id}.firebasestorage.app"
  location      = var.storage_location
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  labels = local.common_labels
}

# CDN bucket for static assets
resource "google_storage_bucket" "cdn_bucket" {
  name          = "${var.project_id}-cdn"
  location      = var.storage_location
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  website {
    main_page_suffix = "index.html"
    not_found_page   = "404.html"
  }
  
  labels = local.common_labels
}

# Make CDN bucket publicly readable
resource "google_storage_bucket_iam_member" "cdn_public_read" {
  bucket = google_storage_bucket.cdn_bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# Secret Manager secrets
resource "google_secret_manager_secret" "secrets" {
  for_each = toset([
    "flask-secret-key",
    "refresh-secret-key", 
    "google-oauth-client-id",
    "google-oauth-client-secret",
    "task-auth-token",
    "firebase-admin-sdk-json"
  ])
  
  secret_id = each.key
  
  labels = local.common_labels
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

# Service accounts
resource "google_service_account" "app_engine" {
  account_id   = "${local.app_name}-appengine"
  display_name = "Pokemon TCG Pocket App Engine Service Account"
  description  = "Service account for App Engine application"
}

resource "google_service_account" "cloud_run_jobs" {
  account_id   = "${local.app_name}-jobs"
  display_name = "Pokemon TCG Pocket Cloud Run Jobs Service Account"
  description  = "Service account for background job processing"
}

# IAM permissions for App Engine service account
resource "google_project_iam_member" "app_engine_permissions" {
  for_each = toset([
    "roles/datastore.user",
    "roles/storage.objectAdmin",
    "roles/secretmanager.secretAccessor",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.app_engine.email}"
}

# IAM permissions for Cloud Run jobs service account
resource "google_project_iam_member" "cloud_run_jobs_permissions" {
  for_each = toset([
    "roles/datastore.user",
    "roles/storage.objectAdmin",
    "roles/secretmanager.secretAccessor"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloud_run_jobs.email}"
}

# Cloud Scheduler for periodic tasks
resource "google_cloud_scheduler_job" "data_refresh" {
  name        = "${local.app_name}-data-refresh"
  description = "Periodic data refresh job"
  schedule    = "0 */6 * * *"  # Every 6 hours
  time_zone   = "UTC"
  
  http_target {
    http_method = "POST"
    uri         = "https://${var.project_id}.uc.r.appspot.com/api/refresh-cards"
    
    headers = {
      "X-Refresh-Key" = "scheduled-refresh"
    }
  }
  
  retry_config {
    retry_count = 3
  }
}

# Monitoring - Uptime check
resource "google_monitoring_uptime_check_config" "app_uptime" {
  display_name = "${local.app_name} Uptime Check"
  timeout      = "10s"
  period       = "300s"
  
  http_check {
    use_ssl = true
    path    = "/health"
    port    = "443"
  }
  
  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "${var.project_id}.uc.r.appspot.com"
    }
  }
  
  content_matchers {
    content = "healthy"
    matcher = "CONTAINS_STRING"
  }
}

# Logging sink for error monitoring
resource "google_logging_project_sink" "error_sink" {
  name        = "${local.app_name}-error-sink"
  destination = "storage.googleapis.com/${google_storage_bucket.logs_bucket.name}"
  
  filter = "severity >= ERROR"
  
  unique_writer_identity = true
}

# Logs storage bucket
resource "google_storage_bucket" "logs_bucket" {
  name          = "${var.project_id}-logs"
  location      = var.storage_location
  force_destroy = false
  
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }
  
  labels = local.common_labels
}

# Grant log sink permission to write to bucket
resource "google_storage_bucket_iam_member" "logs_sink_writer" {
  bucket = google_storage_bucket.logs_bucket.name
  role   = "roles/storage.objectCreator"
  member = google_logging_project_sink.error_sink.writer_identity
}