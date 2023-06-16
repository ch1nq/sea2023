#!/bin/bash

# Build Docker image
docker build . -t sea2023

# Remove any existing Docker container with the same name
docker rm -f sea2023

# Run the Docker container
docker run --name sea2023 -d -p 1337:6000 sea2023:latest

sleep 2

# Open the URL in a browser
if [[ "$OSTYPE" == "darwin"* ]]; then
  open "http://0.0.0.0:1337"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  xdg-open "http://0.0.0.0:1337"
fi

