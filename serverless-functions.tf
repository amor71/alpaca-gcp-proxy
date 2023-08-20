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
  timeout               = 540
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.alpaca_state_zip.name

  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = "projects/${var.project_id}/topics/alpaca_events"
  }

  environment_variables = {
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
  }
  entry_point         = "alpaca_state"
  available_memory_mb = 256
}

# -------------------
# -- post_ach_link --
# -------------------
resource "google_pubsub_topic" "post_ach_link" {
  name = "post_ach_link"
}

data "archive_file" "post_ach_link" {
  type        = "zip"
  output_path = "/tmp/post_ach_link.zip"
  source_dir  = "functions/post_ach_link"
}
resource "google_storage_bucket_object" "post_ach_link_zip" {
  name         = format("post_ach_link-%s.zip", data.archive_file.post_ach_link.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.post_ach_link.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]

}

resource "google_cloudfunctions_function" "post_ach_link" {
  name                  = "post_ach_link"
  description           = "Handling post ach link complete"
  runtime               = "python311"
  timeout               = 540
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.post_ach_link_zip.name

  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = "projects/${var.project_id}/topics/post_ach_link"
  }

  environment_variables = {
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
  }
  entry_point         = "post_ach_link"
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

  environment_variables = {
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
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
    PROJECT_ID      = var.project_id
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
    TOKEN_BYPASS    = var.token_bypass
  }
}

# --------------
# -- topup --
# --------------
resource "google_vpc_access_connector" "connector" {
  name          = "vpc-con"
  ip_cidr_range = "10.8.0.0/28"
  network       = "default"
}

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
  available_memory_mb = 256

  vpc_connector = google_vpc_access_connector.connector.name

  environment_variables = {
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
  }
}


resource "google_service_account" "tasks_service_account" {
  account_id   = "my-task-account"
  display_name = "Service Account for Cloud Tasks"
}

resource "google_project_iam_binding" "task_enqueue_binding" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  members = ["serviceAccount:${google_service_account.tasks_service_account.email}"]
}

resource "google_cloudfunctions_function_iam_member" "function_invoker" {
  project        = var.project_id
  region         = var.region
  cloud_function = google_cloudfunctions_function.topup.name

  role   = "roles/cloudfunctions.invoker"
  member = "serviceAccount:${google_service_account.tasks_service_account.email}"
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
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
  }
}

# -------------
# -- slackbot --
# -------------

data "archive_file" "slackbot" {
  type        = "zip"
  output_path = "/tmp/slackbot.zip"
  source_dir  = "apigateway/slackbot"
}
resource "google_storage_bucket_object" "slackbot" {
  name         = format("slackbot-%s.zip", data.archive_file.slackbot.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.slackbot.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}

resource "google_cloudfunctions_function" "slackbot" {
  name                  = "slackbot"
  description           = "Converse with slackbot"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.slackbot.name

  trigger_http = true

  entry_point         = "slackbot"
  available_memory_mb = 256

  environment_variables = {
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
  }
}

# -------------
# -- chatbot --
# -------------

data "archive_file" "chatbot" {
  type        = "zip"
  output_path = "/tmp/chatbot.zip"
  source_dir  = "apigateway/chatbot"
}
resource "google_storage_bucket_object" "chatbot" {
  name         = format("chatbot-%s.zip", data.archive_file.chatbot.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.chatbot.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}

resource "google_cloudfunctions_function" "chatbot" {
  name                  = "chatbot"
  description           = "Converse with chatbot"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.chatbot.name

  trigger_http = true

  entry_point         = "chatbot"
  available_memory_mb = 256

  environment_variables = {
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
  }
}

# --------------
# -- missions --
# --------------
data "archive_file" "missions" {
  type        = "zip"
  output_path = "/tmp/missions.zip"
  source_dir  = "apigateway/missions"
}
resource "google_storage_bucket_object" "missions" {
  name         = format("missions-%s.zip", data.archive_file.missions.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.missions.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}
resource "google_cloudfunctions_function" "missions" {
  name                  = "missions"
  description           = "Missions control"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.missions.name

  trigger_http = true

  entry_point         = "missions"
  available_memory_mb = 256

  environment_variables = {
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
  }
}

# -----------------
# -- preferences --
# -----------------

data "archive_file" "preferences" {
  type        = "zip"
  output_path = "/tmp/preferences.zip"
  source_dir  = "apigateway/preferences"
}
resource "google_storage_bucket_object" "preferences" {
  name         = format("preferences-%s.zip", data.archive_file.preferences.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.preferences.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}
resource "google_cloudfunctions_function" "preferences" {
  name                  = "preferences"
  description           = "User Preferences"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.preferences.name

  trigger_http = true

  entry_point         = "preferences"
  available_memory_mb = 128

  environment_variables = {
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
  }
}
# --------------------
# -- plaid_callback --
# --------------------
data "archive_file" "plaid_callback" {
  type        = "zip"
  output_path = "/tmp/plaid_callback.zip"
  source_dir  = "apigateway/plaid_callback"
}
resource "google_storage_bucket_object" "plaid_callback" {
  name         = format("plaid_callback-%s.zip", data.archive_file.plaid_callback.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.plaid_callback.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}
resource "google_cloudfunctions_function" "plaid_callback" {
  name                  = "plaid_callback"
  description           = "Plaid Callback"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.plaid_callback.name

  trigger_http = true

  entry_point         = "plaid_callback"
  available_memory_mb = 256

  environment_variables = {
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
  }
}

# --------------------
# -- plaid_accounts --
# --------------------
data "archive_file" "plaid_accounts" {
  type        = "zip"
  output_path = "/tmp/plaid_accounts.zip"
  source_dir  = "apigateway/plaid_accounts"
}
resource "google_storage_bucket_object" "plaid_accounts" {
  name         = format("plaid_accounts-%s.zip", data.archive_file.plaid_accounts.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.plaid_accounts.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}
resource "google_cloudfunctions_function" "plaid_accounts" {
  name                  = "plaid_accounts"
  description           = "Plaid Accounts"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.plaid_accounts.name

  trigger_http = true

  entry_point         = "plaid_accounts"
  available_memory_mb = 256

  environment_variables = {
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
  }
}

# -----------
# -- plaid --
# -----------
data "archive_file" "plaid" {
  type        = "zip"
  output_path = "/tmp/plaid.zip"
  source_dir  = "apigateway/plaid"
}
resource "google_storage_bucket_object" "plaid" {
  name         = format("plaid-%s.zip", data.archive_file.plaid.output_md5)
  bucket       = google_storage_bucket.serverless_function_bucket.name
  content_type = "application/zip"
  source       = data.archive_file.plaid.output_path
  depends_on = [
    google_storage_bucket.serverless_function_bucket
  ]
}
resource "google_cloudfunctions_function" "plaid" {
  name                  = "plaid"
  description           = "Plaid connectivity"
  runtime               = "python311"
  source_archive_bucket = google_storage_bucket.serverless_function_bucket.name
  source_archive_object = google_storage_bucket_object.plaid.name

  trigger_http = true

  entry_point         = "plaid"
  available_memory_mb = 256

  environment_variables = {
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
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
    PROJECT_ID      = var.project_id
    TOKEN_BYPASS    = var.token_bypass
    LOCATION        = var.region
    REBALANCE_QUEUE = var.rebalance_queue
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
