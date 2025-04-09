#!/usr/bin/env bash

# Run the server
python3 -m hq.gui.dashboard.server

# Run the client
flutter run -d chrome --release --web-host=192.168.0.247 --web-port=10499
