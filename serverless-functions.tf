# --------------------------
# -- Function Storage Bucket
# --------------------------
resource "google_storage_bucket" "serverless_function_bucket" {
  name     = "${local.resource_prefix}serverless-function-bucket"
  location = "US"
}

# ------------------
# -- alpaca_state --
# ------------------
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
  available_memory_mb = 256
}

# -----------------
# -- plaid_state --
# -----------------
resource "google_pubsub_topic" "plaid_events" {
  name = "plaid_events"
}

data "archive_file" "plaid_state" {
  type        = "zip"
  output_path = "/tmp/plaid_state.zip"
  source_dir  = "functions/plaid_state"
}
resource "google_storage_bucket_object" "plaid_state_zip" {
  name         = format("plaid_state-%s.zip", data.archive_file.plaid_state.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.plaid_state.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]

}

resource "google_cloudfunctions_function" "plaid_state" {
  name                  = "plaid_state"
  description           = "Handling Plaid states"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.plaid_state_zip.name

  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = "projects/${var.project_id}/topics/plaid_events"
  }

  entry_point         = "plaid_state"
  available_memory_mb = 256
}

# --------------
# -- new_user --
# --------------
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
  available_memory_mb = 256

  environment_variables = {
    PROJECT_ID   = var.project_id
    TOKEN_BYPASS = var.token_bypass
  }
}

# --------------
# -- topup --
# --------------
data "archive_file" "topup" {
  type        = "zip"
  output_path = "/tmp/topup.zip"
  source_dir  = "apigateway/topup"
}
resource "google_storage_bucket_object" "topup_zip" {
  name         = format("topup-%s.zip", data.archive_file.topup.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.topup.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}

resource "google_cloudfunctions_function" "topup" {
  name                  = "topup"
  description           = "Set user's top-up schedule and amount"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.topup_zip.name

  trigger_http = true

  entry_point         = "topup"
  available_memory_mb = 128

  environment_variables = {
    PROJECT_ID   = var.project_id
    TOKEN_BYPASS = var.token_bypass
  }
}

# ----------------------
# -- get_user_details --
# ----------------------
data "archive_file" "get_user_details" {
  type        = "zip"
  output_path = "/tmp/get_user_details.zip"
  source_dir  = "apigateway/get_user_details"
}
resource "google_storage_bucket_object" "get_user_details" {
  name         = format("get_user_details-%s.zip", data.archive_file.get_user_details.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.get_user_details.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}

resource "google_cloudfunctions_function" "get_user_details" {
  name                  = "get_user_details"
  description           = "Set user's top-up schedule and amount"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.get_user_details.name

  trigger_http = true

  entry_point         = "get_user_details"
  available_memory_mb = 128

  environment_variables = {
    PROJECT_ID   = var.project_id
    TOKEN_BYPASS = var.token_bypass
  }
}

# -----------
# -- proxy --
# -----------
data "archive_file" "proxy" {
  type        = "zip"
  output_path = "/tmp/proxy.zip"
  source_dir  = "proxy"
}
resource "google_storage_bucket_object" "proxy_zip" {
  name         = format("proxy-%s.zip", data.archive_file.proxy.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.proxy.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}

resource "google_cloudfunctions_function" "proxy" {
  name                  = "proxy"
  description           = "proxy API"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.proxy_zip.name

  trigger_http = true

  entry_point         = "proxy"
  available_memory_mb = 256

  #ingress_settings = "ALLOW_INTERNAL_ONLY"

  environment_variables = {
    PROJECT_ID   = var.project_id
    TOKEN_BYPASS = var.token_bypass
  }
}

data "google_iam_policy" "n30-noauth-func" {
  binding {
    role = "roles/cloudfunctions.invoker"
    members = [
      "allUsers",
    ]
  }
}
resource "google_cloudfunctions_function_iam_policy" "function_iam_policy" {
  project        = var.project_id
  region         = var.region
  cloud_function = google_cloudfunctions_function.proxy.name

  policy_data = data.google_iam_policy.n30-noauth-func.policy_data
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
