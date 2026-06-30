#!/usr/bin/env python3
"""
AirNode USB Bridge
==================
Reads CSV data from Arduino Uno over USB serial and serves it
as a JSON API on http://localhost:8080/data

No WiFi. No NodeMCU. Just:
  1. pip install pyserial
  2. python airnode_bridge.py
  3. Open iot-air-quality-dashboard-usb.html in browser

Auto-detects the Arduino port, or set SERIAL_PORT manually below.
"""

import serial
import serial.tools.list_ports
import threading
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Config — change port if auto-detect fails ────────────────
SERIAL_PORT  = None   # e.g. "COM3" or "/dev/ttyUSB0" — None = auto-detect
SERIAL_BAUD  = 9600
SERVER_PORT  = 8080

# ── Latest reading (shared between serial thread and HTTP) ───
latest = {
    "temp": None,
    "humidity": None,
    "airQuality": None,
    "ledState": "unknown",
    "timestamp": 0,
    "error": None,
    "connected": False
}
lock = threading.Lock()

# ── Auto-detect Arduino port ─────────────────────────────────
def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        if any(x in desc for x in ["arduino", "ch340", "cp210", "uno", "usb serial"]):
            print(f"[Auto] Found Arduino on {p.device} ({p.description})")
            return p.device
    # fallback: return first available port
    if ports:
        print(f"[Auto] No Arduino found by name, trying {ports[0].device}")
        return ports[0].device
    return None

# ── Serial reader thread ─────────────────────────────────────
def serial_reader():
    global latest
    port = SERIAL_PORT or find_arduino_port()
    if not port:
        print("[Error] No serial port found. Plug in the Arduino and retry.")
        return

    while True:
        try:
            print(f"[Serial] Connecting to {port} at {SERIAL_BAUD} baud...")
            with serial.Serial(port, SERIAL_BAUD, timeout=3) as ser:
                print(f"[Serial] Connected!")
                with lock:
                    latest["connected"] = True
                    latest["error"] = None

                while True:
                    raw = ser.readline().decode("utf-8", errors="ignore").strip()
                    if not raw or raw == "AIRNODE_START":
                        continue
                    if raw.startswith("ERROR"):
                        with lock:
                            latest["error"] = raw
                        print(f"[Arduino] {raw}")
                        continue

                    parts = raw.split(",")
                    if len(parts) == 4:
                        try:
                            with lock:
                                latest["temp"]       = float(parts[0])
                                latest["humidity"]   = float(parts[1])
                                latest["airQuality"] = int(parts[2])
                                latest["ledState"]   = parts[3].strip()
                                latest["timestamp"]  = int(time.time())
                                latest["error"]      = None
                            print(f"[Data] {raw}")
                        except ValueError:
                            print(f"[Parse error] {raw}")

        except serial.SerialException as e:
            print(f"[Serial] Disconnected: {e}. Retrying in 3s...")
            with lock:
                latest["connected"] = False
                latest["error"] = str(e)
            time.sleep(3)

# ── HTTP request handler ─────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/data":
            with lock:
                data = dict(latest)
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/data")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # silence HTTP logs

# ── Main ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  AirNode USB Bridge")
    print("=" * 50)
    print(f"  API:  http://localhost:{SERVER_PORT}/data")
    print(f"  Baud: {SERIAL_BAUD}")
    print("  Open the dashboard and enter: localhost")
    print("=" * 50)

    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()

    httpd = HTTPServer(("0.0.0.0", SERVER_PORT), Handler)
    print(f"[HTTP] Server running on port {SERVER_PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Bye] Bridge stopped.")
