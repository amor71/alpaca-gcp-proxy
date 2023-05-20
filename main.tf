terraform {
  backend "gcs" {
    bucket = "n30-tf-state-bucket"
    prefix = ""
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
provider "google-beta" {
  project = var.project_id
  region  = var.region
}
variable "slack_notification_url" {
  default = "https://hooks.slack.com/services/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"
}

variable "env" {
  default = "dev"
}

variable "project_id" {
  default = "development-380917"
}

variable "region" {
  default = "us-east4"
}

locals {
  resource_prefix = var.env == "prod" ? "" : "${var.env}-"
}

variable "token_bypass" {
  type = string
}


