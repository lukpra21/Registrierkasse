"""Lokaler PC-Server (Browser-Modus): Schutz gegen fremde Webseiten (CSRF) und DNS-Rebinding."""

import http.client
import json
import socket
import threading

from kasse.ui.app import http_server
from test_erweiterungen import api  # noqa: F401


def _port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _post(port, pfad, body, kopf):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request("POST", pfad, body=body, headers=kopf)
    r = c.getresponse()
    return r.status, r.read()


def test_lokaler_server_csrf_und_rebinding(api):  # noqa: F811
    port = _port()
    srv = http_server(api, port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        gut = {"Host": f"127.0.0.1:{port}", "Content-Type": "application/json"}
        assert _post(port, "/api/status", '{"args":[]}', gut)[0] == 200
        assert _post(port, "/api/status", '{"args":[]}', {**gut, "Origin": f"http://localhost:{port}"})[0] == 200
        # Formular/„simple request“ einer fremden Seite (text/plain, ohne CORS-Vorabprüfung)
        assert _post(port, "/api/status", '{"args":[]}', {**gut, "Content-Type": "text/plain"})[0] == 403
        # fremde Seite per fetch
        assert _post(port, "/api/status", '{"args":[]}', {**gut, "Origin": "https://boese.example"})[0] == 403
        # DNS-Rebinding: fremder Hostname zeigt auf 127.0.0.1
        assert _post(port, "/api/status", '{"args":[]}', {**gut, "Host": f"boese.example:{port}"})[0] == 403
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("GET", "/", headers={"Host": f"boese.example:{port}"})
        assert c.getresponse().status == 403
        assert _post(port, "/api/status", "kaputt", gut)[0] == 400
        assert json.loads(_post(port, "/api/status", '{"args":[1,2,3,4,5]}', gut)[1])["fehler"] == "Ungültiger Aufruf"
    finally:
        srv.shutdown()
        srv.server_close()
