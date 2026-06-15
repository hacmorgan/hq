#!/usr/bin/env python3

"""
Static file server for the dashboard Flutter web build.
Run `build_dashboard.sh` to rebuild before starting this.
"""

import http.server
import mimetypes
import os
from pathlib import Path

mimetypes.add_type('application/wasm', '.wasm')

HOST = '192.168.0.247'
PORT = 10499
SERVE_DIR = Path(__file__).parent.parent / 'build' / 'web'

os.chdir(SERVE_DIR)

with http.server.ThreadingHTTPServer((HOST, PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    print(f'Serving {SERVE_DIR} on http://{HOST}:{PORT}')
    httpd.serve_forever()
