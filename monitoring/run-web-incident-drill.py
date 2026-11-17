#!/usr/bin/env python3
import json
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = root / "docs/evidence/robot-shop" / ("incident-" + stamp)
out.mkdir(parents=True, exist_ok=True)

processes = []
outage_started = False
observed = False

def log(message):
    line = datetime.now(timezone.utc).isoformat() + " " + message
    print(line, flush=True)
    with (out / "timeline.txt").open("a") as f:
        f.write(line + "\n")

def kube(*args, timeout=30):
    result = subprocess.run(
        ["kubectl", *args],
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()

def fetch(url):
    with urllib.request.urlopen(url, timeout=7) as response:
        return json.load(response)

def query(expression):
    params = urllib.parse.urlencode({"query": expression})
    return fetch("http://127.0.0.1:19092/api/v1/query?" + params)

def forward(name, pod, local, remote):
    handle = (out / (name + "-forward.log")).open("w")
    process = subprocess.Popen(
        ["kubectl", "-n", "monitoring", "port-forward",
         "pod/" + pod, f"{local}:{remote}"],
        stdout=handle, stderr=subprocess.STDOUT
    )
    processes.append((process, handle))

probe_expr = 'probe_success{job="robot-shop-blackbox",service="web"}'
alert_expr = 'ALERTS{alertname="RobotShopWebUnavailable",alertstate="firing"}'

try:
    baseline = kube(
        "get", "deployment", "web", "-n", "robot-shop",
        "-o", "jsonpath={.spec.replicas}"
    )
    guard = kube(
        "get", "job", "robotshop-web-recovery-guard",
        "-n", "robot-shop", "-o", "jsonpath={.status.active}"
    )
    guard_logs = kube(
        "logs", "-n", "robot-shop",
        "job/robotshop-web-recovery-guard", "--tail=15"
    )

    if baseline != "1" or guard != "1":
        raise RuntimeError("Baseline or recovery guard is not ready")
    if "GUARD ARMED" not in guard_logs or "OUTAGE DETECTED" in guard_logs:
        raise RuntimeError("Recovery guard is not in its initial armed state")

    log("PASS: Web baseline=1; in-cluster recovery guard active")

    forward(
        "prometheus",
        "prometheus-observability-kube-prometh-prometheus-0",
        19092, 9090
    )
    forward(
        "alertmanager",
        "alertmanager-observability-kube-prometh-alertmanager-0",
        19093, 9093
    )

    for attempt in range(30):
        try:
            baseline_data = query(probe_expr)
            fetch("http://127.0.0.1:19093/api/v2/status")
            break
        except Exception:
            time.sleep(2)
    else:
        raise RuntimeError("Monitoring APIs unavailable; outage cancelled")

    values = baseline_data.get("data", {}).get("result", [])
    if not values or any(float(v["value"][1]) != 1 for v in values):
        raise RuntimeError("Web probe is not healthy; outage cancelled")

    (out / "baseline.json").write_text(json.dumps(baseline_data, indent=2))
    log("PASS: Web synthetic probe healthy; Alertmanager reachable")

    outage_started = True
    log("DRILL: scaling Web from one replica to zero")
    kube(
        "scale", "deployment/web", "-n", "robot-shop",
        "--current-replicas=1", "--replicas=0"
    )

    deadline = time.monotonic() + 190

    while time.monotonic() < deadline:
        try:
            probe = query(probe_expr)
            alert = query(alert_expr)
            am = fetch("http://127.0.0.1:19093/api/v2/alerts")

            samples = probe.get("data", {}).get("result", [])
            status = samples[0]["value"][1] if samples else "missing"
            prom_firing = bool(alert.get("data", {}).get("result", []))
            am_received = any(
                x.get("labels", {}).get("alertname")
                == "RobotShopWebUnavailable" for x in am
            )

            log(
                f"probe={status} "
                f"prometheus_firing={prom_firing} "
                f"alertmanager_received={am_received}"
            )

            if prom_firing and am_received:
                (out / "firing-prometheus.json").write_text(
                    json.dumps(alert, indent=2)
                )
                (out / "firing-alertmanager.json").write_text(
                    json.dumps([
                        x for x in am
                        if x.get("labels", {}).get("alertname")
                        == "RobotShopWebUnavailable"
                    ], indent=2)
                )
                log("PASS: Prometheus fired; Alertmanager received alert")
                observed = True
                break
        except Exception as exc:
            log("MONITOR RETRY: " + str(exc))

        time.sleep(8)

finally:
    if outage_started:
        log("RECOVERY: restoring Web to one replica")
        try:
            log(kube(
                "scale", "deployment/web", "-n", "robot-shop",
                "--replicas=1", timeout=30
            ))
            log(kube(
                "rollout", "status", "deployment/web",
                "-n", "robot-shop", "--timeout=120s",
                timeout=135
            ))
            log("PASS: Web Deployment restored")
        except Exception as exc:
            log("RECOVERY WARNING: " + str(exc))
            log("In-cluster recovery guard remains the fallback")

        for attempt in range(12):
            try:
                recovered = query(probe_expr)
                samples = recovered.get("data", {}).get("result", [])
                if samples and all(
                    float(x["value"][1]) == 1 for x in samples
                ):
                    (out / "recovery.json").write_text(
                        json.dumps(recovered, indent=2)
                    )
                    log("PASS: Web synthetic probe recovered")
                    break
            except Exception:
                pass
            time.sleep(5)

    for process, handle in processes:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        handle.close()

    log("Evidence directory: " + str(out))

if not observed:
    raise SystemExit(
        "INCOMPLETE: Full alert chain not observed; inspect evidence"
    )

log("DRILL COMPLETED: alert and recovery evidence collected")
