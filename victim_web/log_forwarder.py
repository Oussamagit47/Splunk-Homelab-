#!/usr/bin/env python3
# log_forwarder.py - tail /var/log/app.log and POST to Splunk HEC
import time, json, os, sys
import requests
import os
print(os.getcwd())

SPLUNK_HOST = os.getenv("SPLUNK_HOST", "localhost")  # default for local
HEC_TOKEN   = os.getenv("HEC_TOKEN", "")
HEC_INDEX   = os.getenv("HEC_INDEX", "main")
VERIFY_SSL  = os.getenv("VERIFY_SSL", "False").lower() == "true"
LOGFILE     = os.getenv("LOGFILE", "/var/log/app.log")
# -----------------------------------

HEC_URL = f"https://{SPLUNK_HOST}:8088/services/collector/event"
HEADERS = {"Authorization": f"Splunk {HEC_TOKEN}"}

def send_event(obj):
    payload = {
        "index": HEC_INDEX,
        "sourcetype": "homelab:app_log",
        "event": obj
    }
    try:
        r = requests.post(HEC_URL, json=payload, headers=HEADERS, verify=VERIFY_SSL, timeout=6)
        print("Sending line:", obj)
        print("HEC response:", r.status_code, r.text)

        if r.status_code not in (200,201):
            print("HEC error:", r.status_code, r.text, file=sys.stderr)
    except Exception as e:
        print("Exception posting to HEC:", e, file=sys.stderr)
def tail_file(path):
    with open(path, "r", errors="ignore") as f:
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            line = line.strip()
            if not line:
                continue
            # try parse JSON, otherwise send raw string
            try:
                obj = json.loads(line)
                print(obj)
            except Exception:
                obj = {"message": line}
            send_event(obj)

if __name__ == "__main__":
    print("Starting log_forwarder. Forwarding", 'app.log', "to", HEC_URL, file=sys.stderr)
    tail_file(LOGFILE)