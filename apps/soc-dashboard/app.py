#!/usr/bin/env python3
import os, json, time, socket
from contextlib import closing
from flask import Flask, request, jsonify, render_template_string

# ---------- Paths (stable relative to this file) ----------
BASE     = os.path.dirname(os.path.abspath(__file__))
DATA     = os.path.join(BASE, "DATA")
SERVICES = os.path.join(DATA, "SERVICES")
ALERTS   = os.path.join(DATA, "ALERTS")
os.makedirs(DATA, exist_ok=True)

# ---------- Helpers ----------
def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)

def port_up(host, port, timeout=1.0):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except Exception:
            return False

# ---------- Flask ----------
app = Flask(__name__)

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Team 42 — SOC Dashboard</title>
<style>
 body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica,Arial,sans-serif;margin:2rem;background:#0e0e10;color:#e6e6e6}
 h1{margin:0 0 .25rem 0} p{margin:.25rem 0 1rem;color:#aaa}
 table{border-collapse:collapse;width:100%;margin:1rem 0 2rem}
 th,td{border:1px solid #333;padding:.5rem .7rem;text-align:left}
 th{background:#1a1a1d}
 .up{color:#15e69c;font-weight:600}
 .down{color:#ff6b6b;font-weight:600}
 .btn{padding:.4rem .8rem;background:#222;border:1px solid #333;color:#eee;border-radius:.4rem;cursor:pointer}
 .btn:hover{background:#2b2b2f}
 ul{margin:.5rem 0 0 1rem}
</style>
</head>
<body>
  <h1>Team 42 — SOC Dashboard</h1>
  <p>Host: {{ host }} | Updated: {{ updated }}</p>

  <form method="post" action="/check">
    <button class="btn">Re-check Services</button>
  </form>

  <h2>Service Uptime</h2>
  <table>
    <tr><th>Service</th><th>Host</th><th>Port</th><th>Status</th></tr>
    {% for s in services %}
    <tr>
      <td>{{ s.name }}</td>
      <td>{{ s.host }}</td>
      <td>{{ s.port }}</td>
      <td class="{{ 'up' if s.up else 'down' }}">{{ 'UP' if s.up else 'DOWN' }}</td>
    </tr>
    {% endfor %}
  </table>

  <h2>Alerts</h2>
  {% if alerts %}
    <ul>
      {% for a in alerts|reverse %}
        <li>{{ a.ts }} — {{ a.summary }}</li>
      {% endfor %}
    </ul>
  {% else %}
    <p>No alerts yet</p>
  {% endif %}
</body>
</html>"""

# ---------- Routes ----------
@app.get("/")
def index():
    services = load(SERVICES, [])
    alerts   = load(ALERTS, [])
    return render_template_string(
        TEMPLATE,
        services=services,
        alerts=alerts,
        updated=time.strftime("%Y-%m-%d %H:%M:%S"),
        host=socket.gethostname()
    )

@app.post("/ingest")
def ingest():
    data = request.form.get("summary", "")
    try:
        alert = json.loads(data)
    except Exception:
        alert = {"summary": data}
    alert["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    alerts = load(ALERTS, [])
    alerts.append(alert)
    save(ALERTS, alerts)
    return "ok"

@app.post("/check")
def check():
    services = load(SERVICES, [])
    for s in services:
        s["up"] = port_up(s["host"], s["port"])
    save(SERVICES, services)
    return jsonify({"checked": len(services)})

# ---------- Seed + Run ----------
if __name__ == "__main__":
    if not os.path.exists(SERVICES):
        seed = [
            {"name":"Web (WinSrv)","host":"10.0.200.140","port":80,"up":False},
            {"name":"HTTPS (WinSrv)","host":"10.0.200.140","port":443,"up":False},
            {"name":"MariaDB (WinSrv)","host":"10.0.200.140","port":3306,"up":False},
            {"name":"RDP (WinSrv)","host":"10.0.200.140","port":3389,"up":False},
            {"name":"DNS (Infra)","host":"10.0.200.142","port":53,"up":False},
            {"name":"MySQL (Infra)","host":"10.0.200.142","port":3306,"up":False},
            {"name":"RDP (Infra)","host":"10.0.200.142","port":3389,"up":False},
            {"name":"SSH (Linux)","host":"10.0.200.145","port":22,"up":False},
            {"name":"nginx (Linux)","host":"10.0.200.145","port":80,"up":False},
            {"name":"Zeek Sensor","host":"10.0.200.181","port":22,"up":False},
            {"name":"Suricata Sensor","host":"10.0.200.188","port":22,"up":False},
            {"name":"Syslog Collector","host":"10.0.200.129","port":514,"up":False},
            {"name":"SNMP Monitor","host":"10.0.200.129","port":161,"up":False},
            {"name":"NTP Server","host":"10.0.200.129","port":123,"up":False}
        ]
        save(SERVICES, seed)
    if not os.path.exists(ALERTS):
        save(ALERTS, [])
    app.run(host="0.0.0.0", port=5000)

