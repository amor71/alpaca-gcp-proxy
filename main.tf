terraform {
  backend "gcs" {
    bucket = "n30-tf-state-bucket"
    prefix = ""
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
provider "google-beta" {
  project = var.project_id
  region  = var.region
}
variable "slack_notification_url" {
  default = "https://hooks.slack.com/services/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"
}

variable "env" {
  default = "dev"
}

variable "project_id" {
  default = "development-380917"
}

variable "region" {
  default = "us-east4"
}

variable "rebalance_queue" {
  default = "rebalance"
}

locals {
  resource_prefix = var.env == "prod" ? "" : "${var.env}-"
}

variable "token_bypass" {
  type = string
}

resource "google_project_service" "enable_cloud_resource_manager_api" {
  service = "cloudresourcemanager.googleapis.com"
}

resource "google_project_service" "enable_cloud_tasks_api" {
  service    = "tasks.googleapis.com"
  depends_on = [google_project_service.enable_cloud_resource_manager_api]
}

resource "google_project_service" "enable_redis_api" {
  service    = "redis.googleapis.com"
  depends_on = [google_project_service.enable_cloud_resource_manager_api]
}
resource "google_redis_instance" "cache" {
  name           = "memory-cache"
  memory_size_gb = 1
  depends_on     = [google_project_service.enable_redis_api]
}
