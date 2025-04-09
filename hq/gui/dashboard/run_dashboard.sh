#!/usr/bin/env bash

cd ~/hq/hq/gui/dashboard

# Run the server
lib/server.py &

# Run the client
flutter run -d web-server --web-hostname=192.168.0.247 --web-port=10499
