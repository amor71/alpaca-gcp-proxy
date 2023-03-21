[![pdm-managed](https://img.shields.io/badge/pdm-managed-blueviolet)](https://pdm.fming.dev)
[![Sourcery](https://img.shields.io/badge/Sourcery-enabled-brightgreen)](https://sourcery.ai)

# alpaca-gcp-proxy

GCP Function to securely proxy API calls to [Alpaca Broker API](https://alpaca.markets/docs/broker/), including Plaid. The repo is intended to simplify development of mobile / web apps on top Alpaca.

## Proxies

### Alpaca

All calls abbreviated by `/alpaca` will be forwarded to Alpaca, using the predefined Alpaca.Markets Broker API base URL.

### Plaid

All calls abbreviated by `/plaid` will be forwarded to Plaid.

### General

The proxy function can log requests & responses (based on the `DEBUG` environment variable)

The function uses security best practices to ensure compliance and security of Alpaca credentials.

## Deployment

The project is deployed using [GCP Cloud Build](https://cloud.google.com/build). The deployment will create a `proxy` end-point. It is suggested to set up a deployment trigger in CloudBuild.

## Secrets

### Alpaca

Add two secrets to [GCP Secrets Manager](https://console.cloud.google.com/security/secret-manager):

* _alpaca_api_key_
* _alpaca_api_secret_

Obtained after registering to [Alpaca Broker API](https://broker-app.alpaca.markets/sign-up)

### Plaid

* _plaid_client_id_
* _plaid_secret_

Obtained after registering to [Plaid](https://dashboard.plaid.com/overview)

### General

Once deployed, the GCP Function service account needs to be added to the Secrets with role `Secret Accessor`

## Environment Variables

* _PROJECT_ID_: GCP project-id hosting GCP Function and secret
* _ALPACA_BASE_URL_: Alpaca base URL defaults to sandbox
* _PLAID_BASE_URL_: Plaid base URL default to sandbox
* _DEBUG_: "True"/"False" (default "True") log both request and response
