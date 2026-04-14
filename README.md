# TunnelDesk

A lightweight desktop application for managing SSH port forwarding tunnels through a jumphost. Built with Python and Tkinter, TunnelDesk provides a clean graphical interface to quickly spin up and tear down port forwards to internal services — no terminal required.

---

## Features

- Connect to internal services through an SSH jumphost
- Manage multiple port forwarding tunnels simultaneously
- Service configuration loaded from a local file or a remote endpoint
- One-click tunnel start, stop, and refresh
- Open forwarded services directly in your browser
- Packaged as a single standalone executable via PyInstaller

---

## Requirements

- Python 3.9 or higher
- pip

---

## Setup

**1. Create and activate a virtual environment**

```bash
python -m venv venv
```

```bash
# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## Running from source

```bash
python main.py
```

---

## Building a standalone executable

Use the included build script (requires PyInstaller):

```bash
./build.sh
```

The output binary will be placed at:

```
dist/TunnelDesk
```

**Files required in the project root before building:**

| File               | Description                          |
|--------------------|--------------------------------------|
| `main.py`          | Application entry point              |
| `build.sh`         | PyInstaller build script             |
| `requirements.txt` | Python dependencies                  |
| `connections.json` | Fallback connection configuration    |
| `icon.ico`         | Application icon                     |

---

## Usage

1. Launch the application (`dist/TunnelDesk` or `python main.py`)
2. Select a **jumphost** from the dropdown
3. Enter your **jumphost password**
4. Select a **service** from the table
5. Click **Start Forwarding** to open the tunnel
6. Optionally click **Open in Browser** to access the service via its configured URL
7. Click **Stop Forwarding** or **Stop All** to close tunnels when done

The **Refresh Active** button reconnects all currently running tunnels — useful when a connection drops.

---

## Configuration

On startup, TunnelDesk first looks for a local `connections.json` file. If the file is not present, it attempts to fetch the configuration from a remote HTTP endpoint. If both sources are unavailable, the app will display a warning.

To configure the remote endpoint, update the `GCP_URL` variable in `main.py`.

Expected JSON structure:

```json
{
  "jumphosts": ["user@jumphost.example.com"],
  "services": {
    "MyService": [8080, "internal-host.local", 80, "http://localhost:8080"]
  }
}
```

Each service entry follows the format:
```
"ServiceName": [local_port, remote_host, remote_port, browser_url]
```

---

## Dependencies

| Package    | Version     | Purpose              |
|------------|-------------|----------------------|
| `paramiko` | >= 2.11.0   | SSH client           |
| `requests` | latest      | Remote config fetch  |
| `tkinter`  | stdlib      | GUI framework        |

---

## Version

**TunnelDesk v1.1**
