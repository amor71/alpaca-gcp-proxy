#---------------------------
# -- FRONT END DEPLOYMENT --
#---------------------------

#---------------------------
# -- React Cloud Run      --
#---------------------------

resource "google_compute_region_network_endpoint_group" "cloudrun_neg" {
  name                  = "cloudrun-neg"
  network_endpoint_type = "SERVERLESS"
  region                = "us-east4"
  cloud_run {
    service = google_cloud_run_service.react.name
  }
}

resource "google_cloud_run_service" "react" {
  name     = "cloudrun-react"
  location = "us-east4"

  template {
    spec {
      containers {
        image = "gcr.io/development-380917/react-with-cloudrun"

        ports {
          container_port = 8080
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

data "google_iam_policy" "n30-noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "n30-noauth" {
  location = google_cloud_run_service.react.location
  project  = google_cloud_run_service.react.project
  service  = google_cloud_run_service.react.name

  policy_data = data.google_iam_policy.n30-noauth.policy_data
}

# --------------------------
# -- Load Balancer
# --------------------------
resource "google_compute_global_address" "app-lb-ip" {
  name       = "app-address"
  ip_version = "IPV4"
  address    = "34.160.236.191"
}

module "lb-http" {
  source  = "GoogleCloudPlatform/lb-http/google//modules/serverless_negs"
  version = "~> 9.0.0"

  project = var.project_id
  name    = "app"

  managed_ssl_certificate_domains = ["app.nine30.com"]
  ssl                             = true
  https_redirect                  = false
  address                         = google_compute_global_address.app-lb-ip.address
  create_address                  = false
  http_forward                    = false

  backends = {
    default = {
      groups = [
        {
          group = google_compute_region_network_endpoint_group.cloudrun_neg.id
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
