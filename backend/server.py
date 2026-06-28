import http.server
import urllib.request
import urllib.error
import json
import os
import mimetypes

PORT = int(os.environ.get("PORT", 8080))
NVIDIA_API = "https://integrate.api.nvidia.com/v1/chat/completions"
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "").strip()

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_json({"status": "ok"})
        elif self.path == "/":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/proxy":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            api_key = self.headers.get("X-Api-Key", "").strip() or NVIDIA_API_KEY
            if not api_key:
                self.send_json({"error": "API key not configured"}, 400)
                return
            base_url = self.headers.get("X-Base-Url", "").strip()
            api_url = base_url.rstrip('/') + '/chat/completions' if base_url else NVIDIA_API
            try:
                req = urllib.request.Request(
                    api_url,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                        "User-Agent": "CampaignPlanner/1.0"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    self.send_response(resp.status)
                    self.send_cors()
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(resp.read())
            except urllib.error.HTTPError as e:
                err_body = e.read().decode()
                self.send_json({"error": e.reason, "detail": err_body}, e.code)
            except urllib.error.URLError as e:
                self.send_json({"error": str(e.reason)}, 502)
        else:
            self.send_json({"error": "Not found"}, 404)

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Api-Key, X-Base-Url")
        self.send_header("Access-Control-Max-Age", "86400")

    def send_json(self, obj, status=200):
        self.send_response(status)
        self.send_cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def log_message(self, format, *args):
        msg = format % args
        if "200" in msg or "POST" in msg or "400" in msg:
            print(f"  {msg}")

if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n  Campaign Planner Server")
    print(f"  Port: {PORT}")
    print(f"  Frontend: {FRONTEND_DIR}")
    print(f"  NVIDIA Key set: {'Yes' if NVIDIA_API_KEY else 'No'}")
    print(f"  URL: http://0.0.0.0:{PORT}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.server_close()
