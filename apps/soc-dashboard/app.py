#!/usr/bin/env python3
import os, json, time, socket, threading, datetime, http.client
from pathlib import Path
from flask import Flask, jsonify, request, render_template, Response

# === Directories ===
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SERVICES_JSON = DATA_DIR / "services.json"
STATE_JSON = DATA_DIR / "STATE.json"
ALERTS_JSONL = DATA_DIR / "ALERTS.jsonl"
ALERTS_RECENT = DATA_DIR / "ALERTS_recent.json"

from pathlib import Path
from flask import Flask, render_template, jsonify

BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)


LOCK = threading.RLock()
RUNNER_STOP = False

# === Helpers ===
def utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def atomic_write_json(path, data):
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)

def append_jsonl(path, obj):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, separators=(",", ":")) + "\n")

# === Networking Checks ===
def tcp_check(host, port, timeout=2.0):
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            t1 = time.perf_counter()
            return True, int((t1 - t0) * 1000)
    except Exception:
        return False, None

def http_check(host, port, path="/", timeout=2.0, tls=False):
    t0 = time.perf_counter()
    conn_cls = http.client.HTTPSConnection if tls else http.client.HTTPConnection
    conn = conn_cls(host, port, timeout=timeout)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        _ = resp.read(8 * 1024)
        t1 = time.perf_counter()
        return 200 <= resp.status < 400, int((t1 - t0) * 1000), resp.status
    except Exception:
        return False, None, None
    finally:
        try: conn.close()
        except Exception: pass

# === State & Classification ===
def classify_status(ok, latency):
    if not ok:
        return "DOWN"
    if latency and latency > 500:
        return "DEGRADED"
    return "UP"

def run_all_checks():
    now = utc_now_iso()
    with LOCK:
        services = load_json(SERVICES_JSON, [])
        state = load_json(STATE_JSON, {})
        alerts = load_json(ALERTS_RECENT, [])

    emitted = []
    for svc in services:
        host, port = svc.get("host"), int(svc.get("port", 0))
        stype = (svc.get("type") or "tcp").lower()

        if stype == "http":
            ok, latency, code = http_check(host, port)
        else:
            ok, latency = tcp_check(host, port)
            code = None

        status = classify_status(ok, latency)
        prev = state.get(f"{host}:{port}", {})
        if prev.get("status") != status:
            alert = {
                "time": now,
                "service": svc.get("name", f"{host}:{port}"),
                "host": host,
                "port": port,
                "status": status,
                "latency_ms": latency,
                "details": {"http_code": code},
            }
            emitted.append(alert)
            alerts.append(alert)
        state[f"{host}:{port}"] = {
            "status": status,
            "last_check": now,
            "latency_ms": latency,
        }

    if emitted:
        for a in emitted: append_jsonl(ALERTS_JSONL, a)
        alerts = alerts[-500:]
        atomic_write_json(ALERTS_RECENT, alerts)
    atomic_write_json(STATE_JSON, state)
    return {"emitted": len(emitted)}

# === Background Runner ===
def runner_loop(interval=30):
    while not RUNNER_STOP:
        try:
            run_all_checks()
        except Exception as e:
            print("[!] runner error:", e)
        time.sleep(interval)

# === Flask ===
# at the top you already have: BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
@app.route("/")
def index():
    # If templates/index.html exists, render it
    try:
        return render_template("index.html")
    except Exception as e:
        # Fallback so you never 404 at "/"
        return f"<h1>SOC Dashboard</h1><p>Template error: {e}</p>", 200

@app.get("/health")
def health():
    return jsonify({"ok": True}), 200


@app.get("/api/debug/paths")
def api_debug_paths():
    return jsonify({
        "base": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "services_json": str(SERVICES_JSON),
        "state_json": str(STATE_JSON),
        "alerts_jsonl": str(ALERTS_JSONL),
        "alerts_recent": str(ALERTS_RECENT),
        "services_exist": SERVICES_JSON.exists(),
    })

@app.get("/api/services")
def api_services():
    with LOCK:
        svcs = load_json(SERVICES_JSON, [])
    return jsonify({"count": len(svcs), "services": svcs})

@app.post("/api/run")
def api_run():
    result = run_all_checks()
    return jsonify({"ok": True, **result})

@app.get("/api/alerts")
def api_alerts():
    with LOCK:
        alerts = load_json(ALERTS_RECENT, [])
    return jsonify({"count": len(alerts), "alerts": alerts[-20:]})

@app.get("/api/stream")
def api_stream():
    def event_stream():
        while True:
            yield f"data: {json.dumps(run_all_checks())}\n\n"
            time.sleep(10)
    return Response(event_stream(), mimetype="text/event-stream")

def start_runner():
    t = threading.Thread(target=runner_loop, daemon=True)
    t.start()

if __name__ == "__main__":
    start_runner()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

