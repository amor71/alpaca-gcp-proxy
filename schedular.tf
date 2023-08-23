resource "google_pubsub_topic" "alpaca_account_events" {
  name = "alpaca_account_events"
}

resource "google_cloud_scheduler_job" "alpaca_account_events_collector" {
  name     = "alpaca_account_events_collector"
  schedule = "0 * * * *" # This runs every hour, adjust as needed.

  pubsub_target {
    topic_name = google_pubsub_topic.scheduler_topic.name
    data       = base64encode("Your message data here")
  }
}