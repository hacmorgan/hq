# Dashboard

A general dashboard for life

# Hooking into systemd
The UI and API both have systemd services ready to run them under `hq/etc/systemd`

n.b. The web server will need to be recompiled when changes are made outside debug mode

# Compiling the client
To compile the client, run:
```bash
(cd hq/gui/dashboard && flutter build web)
```

# Running manually for debugging

## Running the API/server
The API is executable, simply run the file:
```bash
hq/gui/dashboard/lib/server.py
```

## Running the UI/client
To run the client locally
```bash
(cd hq/gui/dashboard && flutter run -d chrome --debug)
```

To run as a web server (e.g. to dev remotely)
```bash
(cd hq/gui/dashboard && flutter run -d web-server --debug --web-hostname 192.168.0.247 --web-port 10499)
```

