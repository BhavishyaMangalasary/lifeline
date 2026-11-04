import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, "src")

from lifeline.agent.ask import ask
from lifeline.agent.voice import transcribe

MIN_BYTES = 24000 * 2 // 4     # 0.25 s of audio
MAX_BYTES = 24000 * 2 * 20     # 20 s of audio


class Handler(SimpleHTTPRequestHandler):
    def _json(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path != "/ask":
            return super().do_GET()

        q = parse_qs(url.query).get("q", [""])[0].strip()[:300]
        if not q:
            return self._json({"live": True})
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
        self._json(body)

    def do_POST(self):
        if urlparse(self.path).path != "/transcribe":
            return self.send_error(404)
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_BYTES:
            return self._json({"error": "That recording is too long. Keep it under 20 seconds."})
        pcm = self.rfile.read(n)
        pcm = pcm[: len(pcm) // 2 * 2]
        if len(pcm) < MIN_BYTES:
            return self._json({"text": "", "error": "That was too short. Try again."})
        for _ in range(2):
            try:
                return self._json({"text": transcribe(pcm)})
            except Exception:
                pass
        self._json({"error": "Transcription failed. Try again."})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), partial(Handler, directory="app"))
    print("Lifeline running at http://localhost:8000  (Ctrl+C to stop)")
    server.serve_forever()