# alpaca-gcp-proxy

GCP Function to securely proxy APIs calls to Alpaca Broker API

## Secrets

Add two secrets to [GCP Secrets Manager](https://console.cloud.google.com/security/secret-manager):

* alpaca_api_key
* alpaca_api_secret

That should be obtained after registering to [Alpaca Broker API](https://broker-app.alpaca.markets/sign-up)

## Environment Variables 

"PROJECT_ID" -> GCP project-id hosting GCP Function and secret




