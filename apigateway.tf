provider "google-beta" {
  project = var.project_id
  region  = var.region
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
  name         = "new_user.zip"
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

#---------------------------
# App Gateway
#---------------------------
resource "google_api_gateway_api" "api_gw" {
  provider = google-beta
  api_id   = "api"
}

resource "google_api_gateway_api_config" "api_gw" {
  provider      = google-beta
  api           = google_api_gateway_api.api_gw.api_id
  api_config_id = "api-config"

  openapi_documents {
    document {
      path     = "spec.yaml"
      contents = filebase64("./apigateway/openapi.yaml")
    }
  }
  lifecycle {
    create_before_destroy = true
  }
}

resource "google_api_gateway_gateway" "api_gw" {
  provider   = google-beta
  api_config = google_api_gateway_api_config.api_gw.id
  gateway_id = "api-gateway"
}

#---------------------------
# App Gateway LB
#---------------------------
resource "google_compute_region_network_endpoint_group" "gw_neg" {
  name                  = "cloudrun-neg"
  network_endpoint_type = "SERVERLESS"
  region                = "us-east4"
  cloud_run {
    service = google_api_gateway_gateway.api_gw.default_hostname
  }
}

module "gw-lb" {
  source  = "GoogleCloudPlatform/lb-http/google//modules/serverless_negs"
  version = "~> 4.5"

  project = var.project_id
  name    = "gw-lb"

  managed_ssl_certificate_domains = ["api.nine30.com"]
  ssl                             = true
  https_redirect                  = true

  backends = {
    default = {
      groups = [
        {
          group = google_compute_region_network_endpoint_group.gw_neg.id
        }
      ]

      enable_cdn = false

      log_config = {
        enable      = true
        sample_rate = 1.0
      }

      iap_config = {
        enable               = false
        oauth2_client_id     = null
        oauth2_client_secret = null
      }

      description            = null
      custom_request_headers = null
      security_policy        = null
    }
  }
}
