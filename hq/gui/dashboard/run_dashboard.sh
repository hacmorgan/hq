#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Run the API server
lib/server.py &

# Serve the pre-built Flutter web app
# Run build_dashboard.sh first if the build is stale
lib/serve_dashboard.py
