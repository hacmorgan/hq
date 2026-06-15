# Dashboard

A general dashboard for life

## Setup

To set up the dashboard from scratch on a new machine, run:

```bash
sysbs --setup-dashboard
```

This will:
1. Build the Flutter web app (`build_dashboard.sh`)
2. Symlink `dashboard-api.service` and `dashboard-ui.service` from `hq/etc/systemd/` to `/etc/systemd/system/`
3. Run `systemctl daemon-reload`
4. Enable and start both services

## Rebuilding after changes

When you change the Flutter app, rebuild and restart the UI service:

```bash
hq/gui/dashboard/build_dashboard.sh
sudo systemctl restart dashboard-ui.service
```

The API service (`server.py`) does not need a rebuild — restart it directly if you change it:

```bash
sudo systemctl restart dashboard-api.service
```

## Services

| Service | File | Purpose |
|---|---|---|
| `dashboard-api.service` | `lib/server.py` | FastAPI backend (port 10498) |
| `dashboard-ui.service` | `lib/serve_dashboard.py` | Static file server for the built Flutter app (port 10499) |

The UI service serves the pre-built output from `build/web/` using Python's `http.server`. It registers the `application/wasm` MIME type before starting so Flutter's WASM files load correctly in the browser.

## Running manually for debugging

### API
```bash
hq/gui/dashboard/lib/server.py
```

### UI (Flutter dev server, hot reload)
```bash
cd hq/gui/dashboard
flutter run -d chrome --debug
```

Or as a remote web server:
```bash
cd hq/gui/dashboard
flutter run -d web-server --debug --web-hostname 192.168.0.247 --web-port 10499
```

### UI (static server, same as service)
```bash
cd hq/gui/dashboard
flutter build web --release
lib/serve_dashboard.py
```
