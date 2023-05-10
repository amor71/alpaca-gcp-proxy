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

resource "google_compute_region_network_endpoint_group" "api-gw_neg" {
  provider              = google-beta
  name                  = "neg-gw"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  serverless_deployment {
    platform = "apigateway.googleapis.com"
    resource = google_api_gateway_gateway.api_gw_gw.gateway_id
  }
}

resource "google_compute_global_address" "api-gw-address" {
  name       = "lb-api-gw-static-ip"
  ip_version = "IPV4"
}

module "lb-http-api-gw" {
  source  = "GoogleCloudPlatform/lb-http/google//modules/serverless_negs"
  version = "~> 9.0.0"

  project = var.project_id
  name    = "apigw"

  managed_ssl_certificate_domains = ["api.nine30.com"]
  ssl                             = true
  https_redirect                  = false
  address                         = google_compute_global_address.api-gw-address.address
  create_address                  = false
  http_forward                    = false

  backends = {
    default = {
      groups = [
        {
          group = google_compute_region_network_endpoint_group.api-gw_neg.id
        }
      ]
      protocol                        = "HTTP"
      port_name                       = "http"
      description                     = null
      enable_cdn                      = false
      custom_request_headers          = null
      custom_response_headers         = null
      security_policy                 = null
      edge_security_policy            = null
      compression_mode                = null
      connection_draining_timeout_sec = null
      session_affinity                = null
      affinity_cookie_ttl_sec         = null

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

