#!/usr/bin/env bash

cd ~/hq/hq/gui/dashboard

# Run the server
lib/server.py &

# Run the client
/home/hamish/flutter/bin/flutter \
    run \
    --device-id web-server \
    --web-hostname 192.168.0.247 \
    --web-port 10499
