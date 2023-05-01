provider "google-beta" {
  project = var.project_id
  region  = var.region
}



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
