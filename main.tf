provider "google" {
  project     = var.project_id
  region      = var.region
}

terraform {
  backend "gcs" {
    bucket  = "n30-tf-state-bucket"
    prefix  = ""
  }
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

locals {
  resource_prefix = var.env == "prod" ? "" : "${var.env}-"
}



# --------------------------
# -- Function Storage Bucket
# --------------------------
resource "google_storage_bucket" "serverless_function_bucket" {
  name          = "${local.resource_prefix}serverless-function-bucket"
  location      = "US"
}



# --------------------------
# -- Slack Notifier Function
# --------------------------
data "archive_file" "slack_notifier" {
  type        = "zip"
  output_path = "/tmp/slack_notifier.zip"
  source_dir = "functions/notifier"
}

resource "google_storage_bucket_object" "slack_notifier_zip" {
  name   = "${local.resource_prefix}slack-notifier.zip"
  bucket = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source = data.archive_file.slack_notifier.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}

resource "google_cloudfunctions_function" "slack_notifier" {
  name        = "${local.resource_prefix}slack-notifier"
  description = "Slack Notifier Function"
  runtime     = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.slack_notifier_zip.name
  trigger_http = true
  entry_point = "slackNotifier"
  available_memory_mb = 128
}


resource "google_compute_region_backend_service" "slack_notifier_service" {
  name        = "${local.resource_prefix}slack-notifier-service"
  region      = var.region
  backend {
    group = google_cloudfunctions_function.slack_notifier.https_trigger_url
  }
  depends_on = [
    google_cloudfunctions_function.slack_notifier
  ]
  security_policy = google_compute_security_policy.nine30_security_policy.self_link
}