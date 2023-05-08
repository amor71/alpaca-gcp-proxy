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

locals {
  resource_prefix = var.env == "prod" ? "" : "${var.env}-"
}



# --------------------------
# -- Function Storage Bucket
# --------------------------
resource "google_storage_bucket" "serverless_function_bucket" {
  name     = "${local.resource_prefix}serverless-function-bucket"
  location = "US"
}

#---------------------------
# Pub/Sub Events
#---------------------------
resource "google_pubsub_topic" "alpaca_events" {
  name = "alpaca_events"
}

data "archive_file" "alpaca_state" {
  type        = "zip"
  output_path = "/tmp/alpaca_state.zip"
  source_dir  = "functions/alpaca_state"
}
resource "google_storage_bucket_object" "alpaca_state_zip" {
  name         = format("alpaca_state-%s.zip", data.archive_file.alpaca_state.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.alpaca_state.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]

}

resource "google_cloudfunctions_function" "alpaca_events" {
  name                  = "alpaca_state"
  description           = "Handling Alpaca.Market states"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.alpaca_state_zip.name

  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = "projects/${var.project_id}/topics/alpaca_events"
  }

  entry_point         = "alpaca_state"
  available_memory_mb = 128
}

#---------------------------
# API Functions
#---------------------------
data "archive_file" "new_user" {
  type        = "zip"
  output_path = "/tmp/new_user.zip"
  source_dir  = "apigateway/new_user"
}
resource "google_storage_bucket_object" "new_user_zip" {
  name         = format("new_user-%s.zip", data.archive_file.new_user.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.new_user.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}

resource "google_cloudfunctions_function" "new_user" {
  name                  = "new_user"
  description           = "new_user API"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.new_user_zip.name

  trigger_http = true

  entry_point         = "new_user"
  available_memory_mb = 128
}

# --------------------------
# -- Slack Notifier Function
# --------------------------
data "archive_file" "slack_notifier" {
  type        = "zip"
  output_path = "/tmp/slack_notifier.zip"
  source_dir  = "functions/notifier"
}

resource "google_storage_bucket_object" "slack_notifier_zip" {
  name         = "${local.resource_prefix}slack-notifier.zip"
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.slack_notifier.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}

resource "google_cloudfunctions_function" "slack_notifier" {
  name                  = "${local.resource_prefix}slack-notifier"
  description           = "Slack Notifier Function"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.slack_notifier_zip.name
  trigger_http          = true
  entry_point           = "slackNotifier"
  available_memory_mb   = 128
}

