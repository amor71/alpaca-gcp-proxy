#!/bin/bash

echo "Stop running container"
docker rm $(docker stop $(docker ps -a -q --filter ancestor=swaggerapi/swagger-ui --format="{{.ID}}"))


echo "Load latest SwaggerUI docker image"
docker pull swaggerapi/swagger-ui

echo "Run Swagger web-server"
docker run -d -p 8080:8080 -v $PWD:/usr/share/nginx/html/apigateway -e API_URL=apigateway/openapi.yaml swaggerapi/swagger-ui

echo "Give grace period"
sleep 45

echo "lets go!"
open http://localhost:8080

