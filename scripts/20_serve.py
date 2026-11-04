import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, "src")

from lifeline.agent.ask import ask


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path != "/ask":
            return super().do_GET()

        q = parse_qs(url.query).get("q", [""])[0].strip()[:300]
        if not q:
            body = {"live": True}
        else:
            body = None
            for _ in range(2):
                try:
                    body = ask(q)
                    break
                except Exception:
                    pass
            if body is None:
                body = {"answer": "The model service declined this request. Try rewording the question.",
                        "unsupported": []}

        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), partial(Handler, directory="app"))
    print("Lifeline running at http://localhost:8000  (Ctrl+C to stop)")
    server.serve_forever()