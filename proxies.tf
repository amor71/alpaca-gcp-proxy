# --------------------------
# -- Load Balancer
# --------------------------
resource "google_compute_region_network_endpoint_group" "proxies_neg" {
  name                  = "proxies-neg"
  network_endpoint_type = "SERVERLESS"
  region                = "us-east4"
  cloud_function {
    function = google_cloudfunctions_function.proxy.name
  }
}

resource "google_compute_global_address" "proxies-lb-ip" {
  name       = "proxies-address"
  ip_version = "IPV4"
  address    = "34.111.194.44"
}

module "proxies-lb-http" {
  source  = "GoogleCloudPlatform/lb-http/google//modules/serverless_negs"
  version = "~> 9.0.0"

  project = var.project_id
  name    = "proxies"

  managed_ssl_certificate_domains = ["proxies.nine30.com"]
  ssl                             = true
  https_redirect                  = false
  address                         = google_compute_global_address.proxies-lb-ip.address
  create_address                  = false
  http_forward                    = false

  backends = {
    default = {
      groups = [
        {
          group = google_compute_region_network_endpoint_group.proxies_neg.id
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
