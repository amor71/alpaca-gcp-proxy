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

#---------------------------
# -- FRONT END DEPLOYMENT --
#---------------------------

#---------------------------
# -- React Cloud Run      --
#---------------------------
resource "google_cloud_run_service" "react" {
  name     = "cloudrun-react"
  location = "us-east4"

  template {
    spec {
      containers {
        image = "gcr.io/development-380917/react-with-cloudrun"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location    = google_cloud_run_service.react.location
  project     = google_cloud_run_service.react.project
  service     = google_cloud_run_service.react.name

  policy_data = data.google_iam_policy.noauth.policy_data
}

# --------------------------
# -- Load Balancer
# --------------------------
resource "google_compute_managed_ssl_certificate" "load_balancer_ssl" {
  name = "${local.resource_prefix}load-balancer-ssl"
  managed {
    domains = ["${local.resource_prefix}app.nine30.com"]
  }
}

resource "google_compute_forwarding_rule" "lb_service_account" {
  name        = "app load balancer service account"
  project     = var.project_id
  description = "Service account for load balancer"
  backend_service = google_cloud_run_service.react.traffic.url
}

resource "google_compute_ssl_policy" "load_balancer_ssl_policy" {
  name = "${local.resource_prefix}load-balancer-ssl-policy"
  profile = "MODERN"
}

resource "google_compute_url_map" "url_map" {
  name            = "${local.resource_prefix}react-url-map"
  default_service = google_cloud_run_service.react.url
  host_rule {
    hosts        = ["${local.resource_prefix}app.nine30.com"]
    path_matcher = "react-path-matcher"
  }
}

resource "google_compute_global_forwarding_rule" "forwarding_rule" {
  name       = "${local.resource_prefix}forwarding-rule"
  ip_address = "IP_ADDRESS"
  target     = google_compute_target_https_proxy.target_proxy.self_link
  port_range = "443"
}

resource "google_compute_target_https_proxy" "target_proxy" {
  name         = "${local.resource_prefix}target-proxy"
  ssl_certificates = [google_compute_managed_ssl_certificate.load_balancer_ssl.self_link]
  ssl_policy = google_compute_ssl_policy.load_balancer_ssl_policy.self_link
  url_map      = google_compute_url_map.url_map.self_link
}