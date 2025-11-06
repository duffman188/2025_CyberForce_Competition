from flask import Flask, render_template_string, request, jsonify
import json, os, time, socket

app = Flask(__name__)

TEMPLATE = '''
<!doctype html>
<html>
<head><meta charset="utf-8"><title>Team 42 — SOC Dashboard</title></head>
<body style="font-family:sans-serif;margin:30px">
<h1>Team 42 — SOC Dashboard</h1>
<p><b>Host:</b> {{host}} | <b>Updated:</b> {{ts}}</p>
<h2>Service Uptime</h2>
<table border="1" cellpadding="4">
<tr><th>Service</th><th>Host</th><th>Port</th><th>Status</th></tr>
{% for s in services %}
<tr><td>{{s.name}}</td><td>{{s.host}}</td><td>{{s.port}}</td>
<td style="color:{% if s.up %}green{% else %}red{% endif %}">
{{'UP' if s.up else 'DOWN'}}</td></tr>
{% endfor %}
</table>
<form method="post" action="/run_checks"><button>Run Checks</button></form>
<h2>Alerts</h2>
<ul>
{% for a in alerts[-10:] %}
<li><b>{{a.ts}}</b> — {{a.summary}}</li>
{% else %}
<li>No alerts yet</li>
{% endfor %}
</ul>
<form method="post" action="/ingest">
<textarea name="summary" rows="3" cols="60"
 placeholder='{"summary":"Test alert"}'></textarea><br>
<button>Ingest Alert</button>
</form>
</body></html>
'''

DATA = "apps/soc-dashboard/data"
SERVICES = os.path.join(DATA, "services.json")
ALERTS = os.path.join(DATA, "alerts.json")

def load(path, default): 
    try: return json.load(open(path))
    except: return default

def save(path, data): 
    json.dump(data, open(path,"w"), indent=2)

@app.get("/")
def home():
    return render_template_string(TEMPLATE,
        host=socket.gethostname(),
        ts=time.strftime("%Y-%m-%d %H:%M:%S"),
        services=[type("S",(),s) for s in load(SERVICES,[])],
        alerts=[type("A",(),a) for a in load(ALERTS,[])]
    )

@app.post("/run_checks")
def run_checks():
    items=load(SERVICES,[])
    for s in items:
        try:
            with socket.create_connection((s["host"],int(s["port"])),2):
                s["up"]=True
        except Exception:
            s["up"]=False
    save(SERVICES,items)
    return "checks done"

@app.post("/ingest")
def ingest():
    data=request.form.get("summary","")
    try: a=json.loads(data)
    except: a={"summary":data}
    a["ts"]=time.strftime("%Y-%m-%d %H:%M:%S")
    alerts=load(ALERTS,[])
    alerts.append(a)
    save(ALERTS,alerts)
    return "ok"

if __name__=="__main__":
    os.makedirs(DATA,exist_ok=True)
    if not os.path.exists(SERVICES):
        save(SERVICES,[{"name":"HTTP (OpenSUSE)","host":"10.0.0.145","port":80,"up":False},
                       {"name":"MariaDB (Win22)","host":"10.0.0.140","port":3306,"up":False}])
    if not os.path.exists(ALERTS): save(ALERTS,[])
    app.run(host="0.0.0.0",port=5000)
