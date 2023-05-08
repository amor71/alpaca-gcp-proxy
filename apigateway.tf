



#---------------------------
# App Gateway
#---------------------------
resource "google_api_gateway_api" "api_gw" {
  provider = google-beta
  api_id   = "api"
}

resource "google_api_gateway_api_config" "api_gw_config" {
  provider = google-beta
  api      = google_api_gateway_api.api_gw.api_id
  #api_config_id = "api-config"

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

resource "google_api_gateway_gateway" "api_gw_gw" {
  provider   = google-beta
  api_config = google_api_gateway_api_config.api_gw_config.id
  gateway_id = "api-gateway"
}

#---------------
# LB
#---------------

resource "google_compute_region_network_endpoint_group" "gw_neg_us" {
  provider              = google-beta
  name                  = "neg-gw"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  serverlessDeployment {
    platform = "apigateway.googleapis.com"
    resource = google_api_gateway_gateway.api_gw_gw.id
  }
}

module "lb-http-api_gw" {
  source  = "GoogleCloudPlatform/lb-http/google//modules/serverless_negs"
  version = "~> 4.5"
  name    = "app"
  project = var.project_id

  managed_ssl_certificate_domains = ["api.nine30.com"]
  ssl                             = true
  https_redirect                  = true

  backends = {
    default = {
      groups = [
        {
          group = google_compute_region_network_endpoint_group.gw_neg_us.id
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
