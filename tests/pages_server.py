#!/usr/bin/env python3
"""Serveur local qui imite GitHub Pages pour les mesures Lighthouse : compression gzip des fichiers texte,
cache de 10 minutes (max-age=600) et page 404.html pour les adresses inconnues.

    python3 tests/pages_server.py 8766        # sert _site/ sur http://localhost:8766
"""
import gzip
import http.server
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_site")
TEXT = (".html", ".css", ".js", ".json", ".xml", ".txt", ".svg")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            if not self.path.split("?")[0].endswith("/"):
                return super().send_head()
            path = os.path.join(path, "index.html")
        status = 200
        if not os.path.isfile(path):
            path, status = os.path.join(ROOT, "404.html"), 404
        with open(path, "rb") as f:
            data = f.read()
        gz = path.endswith(TEXT) and "gzip" in self.headers.get("Accept-Encoding", "")
        if gz:
            data = gzip.compress(data, 6)
        self.send_response(status)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Cache-Control", "max-age=600")
        if gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        import io
        return io.BytesIO(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    http.server.ThreadingHTTPServer(("", port), Handler).serve_forever()
