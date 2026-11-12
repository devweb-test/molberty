#!/usr/bin/env python3
"""Exercise the handoff HTTP checker against the frozen site, not a WordPress claim."""
import json, re, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from export_snapshot import source_path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = source_path()
REDIRECTS = {row["source"]: row["target"] for row in json.loads((ROOT / "exports/redirects.json").read_text())}

class Handler(BaseHTTPRequestHandler):
    inject_duplicate = False
    def log_message(self, *args):
        pass
    def do_GET(self):
        route = urlsplit(self.path).path
        base = "http://127.0.0.1:" + str(self.server.server_port)
        if route in REDIRECTS:
            self.send_response(301)
            self.send_header("Location", base + REDIRECTS[route])
            self.end_headers()
            return
        relative = "index.html" if route == "/" else route.lstrip("/")
        file = SOURCE / relative
        if file.is_dir():
            file /= "index.html"
        if not file.is_file() or file.suffix != ".html":
            file, status = SOURCE / "404.html", 404
        else:
            status = 404 if route == "/404.html" else 200
        source = file.read_text()
        source = re.sub(r'(<link rel="canonical" href=")[^"]*(">)',
                        lambda m: m[1] + base + route + m[2], source)
        if self.inject_duplicate and route == "/":
            source = source.replace("</head>", "<title>Unwanted duplicate</title></head>")
        body = source.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "check.json"
            command = [sys.executable, str(ROOT / "tools/check_target.py"),
                "--base", "http://127.0.0.1:" + str(server.server_port),
                "--mode", "staging", "--check-redirects", "--output", str(output)]
            good = subprocess.run(command, capture_output=True, text=True)
            if good.returncode:
                raise RuntimeError(good.stdout + good.stderr + output.read_text())
            good_report = json.loads(output.read_text())
            Handler.inject_duplicate = True
            bad = subprocess.run(command, capture_output=True, text=True)
            bad_report = json.loads(output.read_text())
            assert bad.returncode == 1 and not bad_report["passed"]
            assert any(row["route"] == "/" and "title mismatch or duplicate" in row["errors"]
                       for row in bad_report["results"])
            print(json.dumps({"passed": True, "routesAndRedirects": good_report["checked"],
                              "duplicateTitleDetected": True, "targetWordPressTested": False}))
    finally:
        server.shutdown()
        server.server_close()
if __name__ == "__main__":
    main()
