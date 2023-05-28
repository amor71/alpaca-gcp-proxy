
#------------------------------
# -- Slackbot Cloud Run      --
#------------------------------

resource "google_compute_region_network_endpoint_group" "slackbot_cloudrun_neg" {
  name                  = "slackbot_cloudrun-neg"
  network_endpoint_type = "SERVERLESS"
  region                = "us-east4"
  cloud_run {
    service = google_cloud_run_service.slackbot.name
  }
}

resource "google_cloud_run_service" "slackbot" {
  name     = "slackbot"
  location = "us-east4"

  template {
    spec {
      containers {
        image = "us-east4-docker.pkg.dev/development-380917/docker-repository/slackbot"

        ports {
          container_port = 3000
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_policy" "slackbot-noauth" {
  location = google_cloud_run_service.slackbot.location
  project  = google_cloud_run_service.slackbot.project
  service  = google_cloud_run_service.slackbot.name

  policy_data = data.google_iam_policy.n30-noauth.policy_data
}

# --------------------------
# -- Load Balancer
# --------------------------
resource "google_compute_global_address" "slackbot-lb-ip" {
  name       = "app-address"
  ip_version = "IPV4"
}

module "slackbot-lb-http" {
  source  = "GoogleCloudPlatform/lb-http/google//modules/serverless_negs"
  version = "~> 9.0.0"

  project = var.project_id
  name    = "app"

  managed_ssl_certificate_domains = ["slackbot.nine30.com"]
  ssl                             = true
  https_redirect                  = false
  address                         = google_compute_global_address.slackbot-lb-ip.address
  create_address                  = false
  http_forward                    = false

  backends = {
    default = {
      groups = [
        {
          group = google_compute_region_network_endpoint_group.slackbot_cloudrun_neg.id
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
