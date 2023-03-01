# alpaca-gcp-proxy

GCP Function to securely proxy API calls to [Alpaca Broker API](https://alpaca.markets/docs/broker/).

All calls abbreviated by `/alpaca` will be forwarded to Alpaca, using the predefined Alpaca.Markets Broker API base URL.

The proxy function can log requests & responses (based on the `DEBUG` environment variable)

The function uses security best practices to ensure compliance and security of Alpaca credentials.

## deployment

The project is deployed using [GCP Cloud Build](https://cloud.google.com/build). The deployment will create a `proxy` end-point. It is suggested to set up a deployment trigger in CloudBuild.

## Secrets

Add two secrets to [GCP Secrets Manager](https://console.cloud.google.com/security/secret-manager):

* _alpaca_api_key_
* _alpaca_api_secret_

That should be obtained after registering to [Alpaca Broker API](https://broker-app.alpaca.markets/sign-up)

## Environment Variables

* _PROJECT_ID_ -> GCP project-id hosting GCP Function and secret
* _ALPACA_BASE_URL_ -> Alpaca base URL defaults to Sandbox
* _DEBUG_ -> "True"/"False" (default "True") log both request and response
