import base64
import hashlib
import http.server
import secrets
import socketserver
import time
import urllib.parse
import webbrowser

import requests


class OAuthError(Exception):
    pass


def _generate_pkce_pair():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode("ascii").rstrip("=")
    challenge_digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(challenge_digest).decode("ascii").rstrip("=")
    return verifier, challenge


class _CallbackServer(socketserver.TCPServer):
    allow_reuse_address = True


SUCCESS_PAGE = """<html><body style="font-family:Segoe UI,sans-serif;background:#0a0a0c;
color:#f3f2ef;text-align:center;padding-top:90px;">
<h2>Pode fechar essa aba</h2>
<p style="color:#a3a1ab;">Volte pro Koddle — o login já foi concluído.</p>
</body></html>"""

ERROR_PAGE = """<html><body style="font-family:Segoe UI,sans-serif;background:#0a0a0c;
color:#f3f2ef;text-align:center;padding-top:90px;">
<h2>Falha no login</h2>
<p style="color:#a3a1ab;">Volte pro Koddle e tente de novo.</p>
</body></html>"""


def _make_handler():
    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            self.server.auth_code = params.get("code", [None])[0]
            self.server.auth_error = params.get("error", [None])[0]

            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            page = SUCCESS_PAGE if self.server.auth_code else ERROR_PAGE
            self.wfile.write(page.encode("utf-8"))

        def log_message(self, format, *args):
            pass

    return _Handler


def run_pkce_login(auth_url, token_url, client_id, redirect_uri, port, scope, timeout=120, client_secret=None):
    """Fluxo genérico de login OAuth2 com PKCE — usado tanto pro Google quanto
    pro Discord. O client_secret é opcional: o Discord dispensa ele de verdade,
    mas o Google (mesmo usando PKCE) ainda exige esse valor no passo de troca
    do código pelo token — é uma peculiaridade da implementação deles."""
    verifier, challenge = _generate_pkce_pair()

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    url = f"{auth_url}?{urllib.parse.urlencode(params)}"

    httpd = _CallbackServer(("127.0.0.1", port), _make_handler())
    httpd.auth_code = None
    httpd.auth_error = None
    httpd.timeout = 5

    webbrowser.open(url)

    start = time.time()
    while httpd.auth_code is None and httpd.auth_error is None:
        httpd.handle_request()
        if time.time() - start > timeout:
            break

    httpd.server_close()

    if httpd.auth_error:
        raise OAuthError(f"Login recusado: {httpd.auth_error}")
    if not httpd.auth_code:
        raise OAuthError("Tempo esgotado esperando o login no navegador.")

    token_data = {
        "grant_type": "authorization_code",
        "code": httpd.auth_code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": verifier,
    }
    if client_secret:
        token_data["client_secret"] = client_secret

    resp = requests.post(
        token_url,
        data=token_data,
        headers={"Accept": "application/json"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise OAuthError(f"Falha ao trocar código por token ({resp.status_code}): {resp.text[:200]}")

    data = resp.json()
    access_token = data.get("access_token")
    if not access_token:
        raise OAuthError("O provedor não devolveu um access_token.")
    return access_token
