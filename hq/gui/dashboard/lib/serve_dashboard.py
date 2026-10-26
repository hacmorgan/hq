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


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    """
    Make browsers revalidate on every load (cheap 304s on a LAN), so a rebuild
    reaches every client instead of Flutter's service worker serving a stale app.
    """

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


with http.server.ThreadingHTTPServer((HOST, PORT), NoCacheHandler) as httpd:
    print(f'Serving {SERVE_DIR} on http://{HOST}:{PORT}')
    httpd.serve_forever()
