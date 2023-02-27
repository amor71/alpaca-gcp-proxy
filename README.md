# alpaca-gcp-proxy

GCP Function to securely proxy APIs calls to Alpaca Broker API

## Secrets

Add two secrets to [GCP Secrets Manager](https://console.cloud.google.com/security/secret-manager):

* _alpaca_api_key_
* _alpaca_api_secret_

That should be obtained after registering to [Alpaca Broker API](https://broker-app.alpaca.markets/sign-up)

## Environment Variables 

- _PROJECT_ID_ -> GCP project-id hosting GCP Function and secret
- _ALPACA_BASE_URL_ -> Alpaca base URL, defaults to Sandbox



