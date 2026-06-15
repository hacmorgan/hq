#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

/home/hamish/flutter/bin/flutter build web --release

echo "Build complete. Restart dashboard-ui.service to serve the new build."
