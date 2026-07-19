import asyncio
import base64
import hashlib
import io
import json
import os
import re
import threading
import webbrowser
from datetime import datetime, timezone

import requests
import syncedlyrics
import webview
from PIL import Image

import oauth_client

from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus,
)
from winrt.windows.storage.streams import DataReader, Buffer, InputStreamOptions

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
UI_DIR = os.path.join(BASE_DIR, "ui")

# Servidor de Amigos (koddle-server)
FRIENDS_API_BASE = "https://valiant-youth-env.up.railway.app"

# Login via Google — Client ID público (sem Client Secret, usa PKCE).
# Crie em console.cloud.google.com, tipo de app "Desktop app".
GOOGLE_CLIENT_ID = "931116092083-hk8bloen2tvp7tif7fp3j7q57gsajs00.apps.googleusercontent.com"
GOOGLE_REDIRECT_URI = "http://127.0.0.1:8898/callback"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPE = "openid email profile"

# Login via Discord — Client ID público (sem Client Secret, usa PKCE).
# Crie em discord.com/developers/applications, aba OAuth2.
# Isso é diferente do token de status usado pra sincronizar a letra da música.
DISCORD_OAUTH_CLIENT_ID = "1528307591137202196"
DISCORD_REDIRECT_URI = "http://127.0.0.1:8899/callback"
DISCORD_AUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_OAUTH_SCOPE = "identify email"

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ------------------------------------------------------------------
# Letras (mesma logica do script original)
# ------------------------------------------------------------------

def clean_lyric(text):
    if not text:
        return None
    text = text.replace("\r", "").strip()
    if "/" in text and len(text) > 40:
        return None
    if re.search(r"[a-z][A-Z][a-z]", text):
        return None
    if len(text) > 80:
        return None
    if len(re.sub(r"[a-zA-Z ]", "", text)) > len(text) * 0.4:
        return None
    return text


def fix_joined_words(text):
    if not text:
        return text
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", text)


def parse_lrc(lrc_string):
    lyrics = []
    if not lrc_string:
        return lyrics
    for line in lrc_string.splitlines():
        match = re.match(r"\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)", line)
        if match:
            m = int(match.group(1))
            s = float(match.group(2))
            text = match.group(3).strip()
            lyrics.append((m * 60 + s, text))
    return sorted(lyrics, key=lambda x: x[0])


# ------------------------------------------------------------------
# Discord
# ------------------------------------------------------------------

def update_discord_status(token, text):
    if not token:
        return
    url = "https://discord.com/api/v9/users/@me/settings"
    headers = {"authorization": token, "content-type": "application/json"}
    data = {"custom_status": {"text": text}} if text else {"custom_status": None}
    try:
        requests.patch(url, headers=headers, json=data, timeout=5)
    except Exception:
        pass


# ------------------------------------------------------------------
# Midia + capa do album
# ------------------------------------------------------------------

async def read_thumbnail_bytes(thumb_ref):
    if not thumb_ref:
        return None
    try:
        stream = await thumb_ref.open_read_async()
        size = stream.size
        if not size:
            return None
        buf = Buffer(size)
        await stream.read_async(buf, size, InputStreamOptions.READ_AHEAD)
        reader = DataReader.from_buffer(buf)
        data = bytearray(size)
        reader.read_bytes(data)
        return bytes(data)
    except Exception:
        return None


def _session_matches_spotify(session):
    try:
        aumid = (session.source_app_user_model_id or "").lower()
    except Exception:
        return False
    return "spotify" in aumid


def _find_spotify_session(manager):
    """Procura, entre todas as sessões de mídia do Windows, a que pertence ao Spotify.
    Cobre tanto a versão instalável (AUMID 'Spotify.exe') quanto a da Microsoft Store
    (AUMID começando com 'SpotifyAB.SpotifyMusic'). Cada sessão é checada isoladamente
    pra uma sessão problemática não derrubar a varredura inteira."""
    try:
        sessions = manager.get_sessions()
        for session in sessions:
            if _session_matches_spotify(session):
                return session
    except Exception:
        pass

    # Fallback: se a sessão "atual" do Windows já for o Spotify, usa ela direto
    try:
        current = manager.get_current_session()
        if current and _session_matches_spotify(current):
            return current
    except Exception:
        pass

    return None


async def get_media_info():
    try:
        manager = await MediaManager.request_async()
        session = _find_spotify_session(manager)

        if session:
            playback = session.get_playback_info()
            props = await session.try_get_media_properties_async()
            timeline = session.get_timeline_properties()

            now = datetime.now(timezone.utc)
            diff = (now - timeline.last_updated_time).total_seconds()

            thumb_bytes = await read_thumbnail_bytes(getattr(props, "thumbnail", None))

            return {
                "title": props.title,
                "artist": props.artist,
                "position": timeline.position.total_seconds() + diff,
                "status": playback.playback_status,
                "thumbnail": thumb_bytes,
            }
    except Exception:
        pass

    return {"status": None}


def image_to_data_uri(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        fmt = "JPEG"
        buf = io.BytesIO()
        img.save(buf, format=fmt, quality=88)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return None


def extract_dominant_color(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((48, 48))
        paletted = img.quantize(colors=6, method=Image.MEDIANCUT)
        palette = paletted.getpalette()
        color_counts = sorted(paletted.getcolors(), reverse=True)

        for count, idx in color_counts:
            r, g, b = palette[idx * 3: idx * 3 + 3]
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if 25 < brightness < 235:
                return [r, g, b]

        count, idx = color_counts[0]
        r, g, b = palette[idx * 3: idx * 3 + 3]
        return [r, g, b]
    except Exception:
        return None


# ------------------------------------------------------------------
# Worker: roda a logica em background e empurra estado pra UI
# ------------------------------------------------------------------

class LyricsWorker(threading.Thread):
    def __init__(self, token, window, stop_event):
        super().__init__(daemon=True)
        self.token = token
        self.window = window
        self.stop_event = stop_event

    def push(self, payload):
        try:
            js = f"window.updateState && window.updateState({json.dumps(payload)})"
            self.window.evaluate_js(js)
        except Exception:
            pass

    def run(self):
        try:
            asyncio.run(self.main_loop())
        except Exception as e:
            self.push({"type": "error", "message": str(e)})

    async def main_loop(self):
        current_song = None
        current_lyrics = []
        current_line = None
        current_art_uri = None
        current_color = None

        update_discord_status(self.token, None)
        self.push({"type": "state", "live": False, "label": "Procurando o Spotify..."})

        try:
            while not self.stop_event.is_set():
                info = await get_media_info()
                status = info.get("status")

                if status != GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                    update_discord_status(self.token, None)
                    label = (
                        "Pausado"
                        if status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED
                        else "Spotify nao detectado (abra e toque algo)"
                    )
                    self.push({"type": "state", "live": False, "label": label})
                    await asyncio.sleep(1)
                    continue

                song_id = f"{info['title']} {info['artist']}"

                if song_id != current_song:
                    current_song = song_id
                    current_line = None

                    thumb = info.get("thumbnail")
                    current_art_uri = image_to_data_uri(thumb) if thumb else None
                    current_color = extract_dominant_color(thumb) if thumb else None

                    self.push({
                        "type": "song",
                        "title": info["title"],
                        "artist": info["artist"],
                        "art": current_art_uri,
                        "color": current_color,
                    })
                    self.push({"type": "state", "live": False, "label": "Buscando letra..."})

                    lrc = await asyncio.to_thread(syncedlyrics.search, song_id)
                    current_lyrics = parse_lrc(lrc) if lrc else []

                    self.push({
                        "type": "state",
                        "live": bool(current_lyrics),
                        "label": "Reproduzindo" if current_lyrics else "Letra nao encontrada",
                    })

                pos = info["position"]
                active = None
                for t, txt in current_lyrics:
                    if t <= pos + 0.5:
                        active = txt
                    else:
                        break

                active = fix_joined_words(clean_lyric(active))

                if active != current_line:
                    current_line = active
                    if current_line:
                        await asyncio.to_thread(
                            update_discord_status, self.token, f"\U0001F3B5 {current_line}"
                        )
                self.push({"type": "lyric", "text": current_line, "position": pos})

                await asyncio.sleep(0.3)
        finally:
            update_discord_status(self.token, None)
            self.push({"type": "state", "live": False, "label": "Parado"})


# ------------------------------------------------------------------
# API exposta ao JavaScript
# ------------------------------------------------------------------

class Api:
    def __init__(self):
        self.cfg = load_config()
        self.stop_event = threading.Event()
        self.worker = None
        self.window = None

    def start(self):
        token = self.cfg.get("discord_token", "")
        if not token:
            return {"error": "Configure o token do Discord na aba Perfil antes de iniciar."}

        if self.worker and self.worker.is_alive():
            return {"ok": True}

        self.stop_event = threading.Event()
        self.worker = LyricsWorker(token, self.window, self.stop_event)
        self.worker.start()
        return {"ok": True}

    def stop(self):
        self.stop_event.set()
        return {"ok": True}

    def save_token(self, token):
        self.cfg["discord_token"] = (token or "").strip()
        save_config(self.cfg)
        return {"ok": True}

    def get_token(self):
        return self.cfg.get("discord_token", "")

    def open_external(self, url):
        """Abre um link no navegador padrão do Windows — nunca dentro da própria janela
        do Koddle, pra ele não parecer um site/navegador."""
        if url:
            webbrowser.open(url)
        return {"ok": True}

    # ---------------- Perfil (avatar, capa, nome, bio) ----------------

    def save_profile(self, data):
        data = data or {}
        self.cfg["profile_avatar"] = data.get("avatar", "")
        self.cfg["profile_cover"] = data.get("cover", "")
        self.cfg["profile_name"] = (data.get("name") or "")[:40]
        self.cfg["profile_handle"] = (data.get("handle") or "")[:30]
        self.cfg["profile_bio"] = (data.get("bio") or "")[:160]
        save_config(self.cfg)
        return {"ok": True}

    def get_profile(self):
        return {
            "avatar": self.cfg.get("profile_avatar", ""),
            "cover": self.cfg.get("profile_cover", ""),
            "name": self.cfg.get("profile_name", ""),
            "handle": self.cfg.get("profile_handle", ""),
            "bio": self.cfg.get("profile_bio", ""),
        }

    # ---------------- Amigos (sessão do koddle-server) ----------------

    def save_friends_session(self, token, username):
        self.cfg["friends_token"] = token or ""
        self.cfg["friends_username"] = username or ""
        save_config(self.cfg)
        return {"ok": True}

    def get_friends_session(self):
        return {
            "token": self.cfg.get("friends_token", ""),
            "username": self.cfg.get("friends_username", ""),
        }

    def clear_friends_session(self):
        self.cfg["friends_token"] = ""
        self.cfg["friends_username"] = ""
        save_config(self.cfg)
        return {"ok": True}

    def _push_auth_event(self, payload):
        try:
            js = f"window.onAuthEvent && window.onAuthEvent({json.dumps(payload)})"
            self.window.evaluate_js(js)
        except Exception:
            pass

    def google_login(self):
        def worker():
            try:
                access_token = oauth_client.run_pkce_login(
                    GOOGLE_AUTH_URL, GOOGLE_TOKEN_URL, GOOGLE_CLIENT_ID,
                    GOOGLE_REDIRECT_URI, 8898, GOOGLE_SCOPE,
                )
                resp = requests.post(
                    f"{FRIENDS_API_BASE}/auth/google",
                    json={"access_token": access_token},
                    timeout=10,
                )
                if resp.status_code != 200:
                    detail = resp.json().get("detail", "Erro ao entrar com Google.")
                    self._push_auth_event({"provider": "google", "error": detail})
                    return

                data = resp.json()
                self.cfg["friends_token"] = data["access_token"]
                self.cfg["friends_username"] = data["username"]
                save_config(self.cfg)
                self._push_auth_event({"provider": "google", "ok": True, "username": data["username"]})
            except oauth_client.OAuthError as e:
                self._push_auth_event({"provider": "google", "error": str(e)})
            except Exception as e:
                self._push_auth_event({"provider": "google", "error": f"Erro inesperado: {e}"})

        threading.Thread(target=worker, daemon=True).start()
        return {"started": True}

    def discord_oauth_login(self):
        def worker():
            try:
                access_token = oauth_client.run_pkce_login(
                    DISCORD_AUTH_URL, DISCORD_TOKEN_URL, DISCORD_OAUTH_CLIENT_ID,
                    DISCORD_REDIRECT_URI, 8899, DISCORD_OAUTH_SCOPE,
                )
                resp = requests.post(
                    f"{FRIENDS_API_BASE}/auth/discord",
                    json={"access_token": access_token},
                    timeout=10,
                )
                if resp.status_code != 200:
                    detail = resp.json().get("detail", "Erro ao entrar com Discord.")
                    self._push_auth_event({"provider": "discord", "error": detail})
                    return

                data = resp.json()
                self.cfg["friends_token"] = data["access_token"]
                self.cfg["friends_username"] = data["username"]
                save_config(self.cfg)
                self._push_auth_event({"provider": "discord", "ok": True, "username": data["username"]})
            except oauth_client.OAuthError as e:
                self._push_auth_event({"provider": "discord", "error": str(e)})
            except Exception as e:
                self._push_auth_event({"provider": "discord", "error": f"Erro inesperado: {e}"})

        threading.Thread(target=worker, daemon=True).start()
        return {"started": True}
        return {"ok": True}



def check_ui_files():
    index_path = os.path.join(UI_DIR, "index.html")
    if not os.path.isdir(UI_DIR):
        raise SystemExit(
            f"\n[ERRO] Pasta 'ui' não encontrada em: {UI_DIR}\n"
            f"Certifique-se de que a pasta 'ui' (com index.html, style.css e app.js)\n"
            f"está no mesmo diretório que o app.py.\n"
        )
    if not os.path.isfile(index_path):
        raise SystemExit(
            f"\n[ERRO] Arquivo não encontrado: {index_path}\n"
            f"Confira se index.html está dentro da pasta 'ui'.\n"
        )


def main():
    check_ui_files()
    api = Api()
    window = webview.create_window(
        "Koddle",
        url=os.path.join(UI_DIR, "index.html"),
        js_api=api,
        width=1180,
        height=760,
        min_size=(900, 600),
        background_color="#0a0a0c",
    )
    api.window = window

    def on_closed():
        api.stop_event.set()

    window.events.closed += on_closed

    try:
        webview.start(gui="edgechromium", debug=False)
    except Exception:
        import traceback
        log_path = os.path.join(BASE_DIR, "crash_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now(timezone.utc).isoformat()} ---\n")
            f.write(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
