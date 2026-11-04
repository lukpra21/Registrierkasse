"""Start der Kassenoberfläche.

Standard: eigenes Programmfenster über pywebview (unter Windows Edge WebView2).
Alternativ (``--browser``): lokaler Server nur auf 127.0.0.1, Bedienung im Browser.
"""

from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .. import sicherung
from .api import KassenApi, oeffentliche_methoden, standard_api

WEB = Path(__file__).parent / "web"
TYPEN = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml"}


def _sicherungs_waechter(api: KassenApi, intervall_s: int = 1800) -> None:
    """Prüft beim Start und danach alle 30 Minuten, ob eine Sicherung fällig ist."""

    def lauf():
        with api._lock:
            try:
                sicherung.sichern_wenn_faellig(api.con)
            except Exception as e:  # Sicherung darf die Kasse nie blockieren
                print(f"Sicherung fehlgeschlagen: {e}")
        t = threading.Timer(intervall_s, lauf)
        t.daemon = True
        t.start()

    lauf()


def http_server(api: KassenApi, port: int = 8765) -> ThreadingHTTPServer:
    methoden = oeffentliche_methoden(api)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _senden(self, code: int, body: bytes, typ: str):
            self.send_response(code)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            pfad = self.path.split("?")[0].lstrip("/") or "index.html"
            datei = (WEB / pfad).resolve()
            if not str(datei).startswith(str(WEB.resolve())) or not datei.is_file():
                return self._senden(404, b"nicht gefunden", "text/plain")
            self._senden(200, datei.read_bytes(), TYPEN.get(datei.suffix, "application/octet-stream"))

        def do_POST(self):
            name = self.path.removeprefix("/api/")
            if name not in methoden:
                return self._senden(404, b"{}", "application/json")
            laenge = int(self.headers.get("Content-Length", 0))
            args = json.loads(self.rfile.read(laenge) or b"{}").get("args", [])
            res = methoden[name](*args)
            self._senden(200, json.dumps(res, ensure_ascii=False).encode(), "application/json")

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kasse-ui")
    ap.add_argument("--browser", action="store_true", help="im Browser statt eigenem Fenster")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--datenbank")
    args = ap.parse_args(argv)

    api = standard_api(args.datenbank)
    _sicherungs_waechter(api)
    api.update_im_hintergrund()

    if not args.browser:
        try:
            import webview  # pywebview
        except ImportError:
            print("pywebview nicht installiert – starte im Browser")
            args.browser = True

    if args.browser:
        server = http_server(api, args.port)
        api._beenden = lambda: threading.Thread(target=server.shutdown, daemon=True).start()
        url = f"http://127.0.0.1:{args.port}/"
        print(f"Kasse läuft auf {url}  (Beenden mit Strg+C)")
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        return

    class Bruecke:
        """Nur die freigegebenen Methoden an JavaScript weiterreichen."""

    bruecke = Bruecke()
    for name, f in oeffentliche_methoden(api).items():
        setattr(bruecke, name, f)
    fenster = webview.create_window("Registrierkasse", str(WEB / "index.html"), js_api=bruecke,
                                    width=1366, height=820, min_size=(1024, 680))
    api._beenden = fenster.destroy
    api._fenster = fenster
    webview.start()


if __name__ == "__main__":
    main()
