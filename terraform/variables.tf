variable "project_id" {
  description = "The GCP project ID"
  type        = string
  default     = "pvpocket-dd286"
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "app_engine_location" {
  description = "The location for App Engine application"
  type        = string
  default     = "us-central"
}

variable "firestore_location" {
  description = "The location for Firestore database"
  type        = string
  default     = "us-central1"
}

variable "storage_location" {
  description = "The location for Cloud Storage buckets"
  type        = string
  default     = "US"
}

variable "environment" {
  description = "The environment (dev, staging, prod)"
  type        = string
  default     = "prod"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}