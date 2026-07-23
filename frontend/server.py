"""
NEXUS Dashboard Server
─────────────────────
Serves the dashboard HTML and Rule Engine API.
Standard library only. No frameworks.
"""

import http.server
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.public_api import get_scenario_data
from rules.rule_engine import run as run_rule_engine
from rules.explainer import explain as explain_result

PORT = 8080
HOST = "0.0.0.0"


class DashboardHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path.startswith("/api/result"):
            # Fault injection: /api/result?fault=1 triggers 500 (for demo fallback test)
            parsed = self.path.split("?")
            params = {}
            if len(parsed) > 1:
                for pair in parsed[1].split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        params[k] = v
            if params.get("fault") == "1":
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                body = json.dumps({"error": "Simulated fault"}, ensure_ascii=False).encode("utf-8")
                self.wfile.write(body)
                return
            try:
                scenario = get_scenario_data()
                data = run_rule_engine(scenario_data=scenario)
                lang = scenario.get("passenger", {}).get("language", "ko")
                data = explain_result(data, override_language=lang)
                self._json_response(data)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                body = json.dumps({
                    "error": "Rule Engine unavailable",
                    "detail": str(e)
                }, ensure_ascii=False).encode("utf-8")
                self.wfile.write(body)
        elif self.path in ("/", "/index.html"):
            self._serve_file("index.html", "text/html; charset=utf-8")
        else:
            self.send_response(404)
            self.end_headers()

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.wfile.write(body)

    def _serve_file(self, filename, content_type):
        path = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.exists(path):
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("ETag", '"nexus-dashboard-v1"')
        self.end_headers()
        with open(path, encoding="utf-8") as f:
            self.wfile.write(f.read().encode("utf-8"))

    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}")


if __name__ == "__main__":
    server = http.server.HTTPServer((HOST, PORT), DashboardHandler)
    print(f"NEXUS Dashboard → http://localhost:{PORT}")
    server.serve_forever()
