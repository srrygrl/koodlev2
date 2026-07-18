import json
import traceback
from datetime import datetime, timezone
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer

from auth import create_access_token, decode_access_token, hash_password, verify_password
from database import ensure_indexes, friendships_collection, messages_collection, users_collection
from models import FriendRequestCreate, UserLogin, UserRegister

app = FastAPI(title="Koddle Friends Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# TEMPORÁRIO — mostra o erro de verdade na resposta em vez do genérico
# "Internal Server Error". Depois que resolvermos o problema, dá pra remover
# esse bloco (ou deixar, só não é ideal expor tracebacks pra sempre).
@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        },
    )


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# username -> WebSocket, só de quem está online agora (fica só na memória,
# reseta se o servidor reiniciar — o normal pra presença online/offline)
active_connections: Dict[str, WebSocket] = {}


@app.on_event("startup")
async def on_startup():
    await ensure_indexes()


@app.get("/")
async def root():
    return {"status": "ok", "service": "koddle-server"}


# ---------------- Autenticação ----------------

async def get_current_username(token: str = Depends(oauth2_scheme)) -> str:
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return payload["sub"]


@app.post("/register")
async def register(data: UserRegister):
    username = data.username.strip().lower()
    email = data.email.strip().lower()

    if await users_collection.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Esse nome de usuário já existe.")
    if await users_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Esse e-mail já está cadastrado.")

    await users_collection.insert_one({
        "username": username,
        "email": email,
        "display_name": data.username.strip(),
        "password_hash": hash_password(data.password),
        "created_at": datetime.now(timezone.utc),
    })

    token = create_access_token({"sub": username})
    return {"access_token": token, "username": username}


@app.post("/login")
async def login(data: UserLogin):
    identifier = data.username.strip().lower()
    user = await users_collection.find_one(
        {"$or": [{"username": identifier}, {"email": identifier}]}
    )
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Usuário/e-mail ou senha incorretos.")

    token = create_access_token({"sub": user["username"]})
    return {"access_token": token, "username": user["username"]}


@app.get("/me")
async def me(username: str = Depends(get_current_username)):
    user = await users_collection.find_one({"username": username})
    return {"username": user["username"], "display_name": user.get("display_name", username)}


# ---------------- Amigos ----------------

@app.post("/friends/request")
async def send_friend_request(data: FriendRequestCreate, username: str = Depends(get_current_username)):
    target = data.username.strip().lower()
    if target == username:
        raise HTTPException(status_code=400, detail="Você não pode adicionar a si mesmo.")

    target_user = await users_collection.find_one({"username": target})
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    pair = sorted([username, target])
    existing = await friendships_collection.find_one({"pair": pair})
    if existing:
        raise HTTPException(status_code=400, detail="Já existe um pedido ou amizade com esse usuário.")

    await friendships_collection.insert_one({
        "pair": pair,
        "requested_by": username,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })
    return {"ok": True}


@app.post("/friends/accept")
async def accept_friend_request(data: FriendRequestCreate, username: str = Depends(get_current_username)):
    requester = data.username.strip().lower()
    pair = sorted([username, requester])
    result = await friendships_collection.update_one(
        {"pair": pair, "status": "pending", "requested_by": requester},
        {"$set": {"status": "accepted", "accepted_at": datetime.now(timezone.utc)}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Pedido de amizade não encontrado.")
    return {"ok": True}


@app.post("/friends/decline")
async def decline_friend_request(data: FriendRequestCreate, username: str = Depends(get_current_username)):
    requester = data.username.strip().lower()
    pair = sorted([username, requester])
    result = await friendships_collection.delete_one(
        {"pair": pair, "status": "pending", "requested_by": requester}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pedido de amizade não encontrado.")
    return {"ok": True}


@app.get("/friends")
async def list_friends(username: str = Depends(get_current_username)):
    cursor = friendships_collection.find({"pair": username, "status": "accepted"})
    friends = []
    async for doc in cursor:
        other = [u for u in doc["pair"] if u != username][0]
        friends.append({"username": other, "online": other in active_connections})
    return {"friends": friends}


@app.get("/friends/requests")
async def list_pending_requests(username: str = Depends(get_current_username)):
    cursor = friendships_collection.find({"pair": username, "status": "pending"})
    incoming, outgoing = [], []
    async for doc in cursor:
        other = [u for u in doc["pair"] if u != username][0]
        (outgoing if doc["requested_by"] == username else incoming).append(other)
    return {"incoming": incoming, "outgoing": outgoing}


# ---------------- Histórico de mensagens ----------------

@app.get("/messages/{friend_username}")
async def get_messages(friend_username: str, username: str = Depends(get_current_username), limit: int = 50):
    friend_username = friend_username.strip().lower()
    pair = sorted([username, friend_username])
    cursor = messages_collection.find({"pair": pair}).sort("timestamp", -1).limit(limit)

    messages = []
    async for doc in cursor:
        messages.append({
            "from": doc["from"],
            "text": doc["text"],
            "timestamp": doc["timestamp"].isoformat(),
        })
    messages.reverse()
    return {"messages": messages}


# ---------------- WebSocket: chat + presença + "ouvindo junto" ----------------

async def _authenticate_ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        return None
    payload = decode_access_token(token)
    return payload.get("sub") if payload else None


async def _are_friends(user_a: str, user_b: str) -> bool:
    pair = sorted([user_a, user_b])
    doc = await friendships_collection.find_one({"pair": pair, "status": "accepted"})
    return doc is not None


async def _broadcast_presence(username: str, online: bool):
    cursor = friendships_collection.find({"pair": username, "status": "accepted"})
    async for doc in cursor:
        other = [u for u in doc["pair"] if u != username][0]
        conn = active_connections.get(other)
        if conn:
            await conn.send_text(json.dumps({
                "type": "presence", "username": username, "online": online,
            }))


async def _handle_chat(sender: str, data: dict):
    to = (data.get("to") or "").strip().lower()
    text = (data.get("text") or "").strip()[:1000]
    if not to or not text or not await _are_friends(sender, to):
        return

    pair = sorted([sender, to])
    doc = {"pair": pair, "from": sender, "text": text, "timestamp": datetime.now(timezone.utc)}
    await messages_collection.insert_one(doc)

    payload = json.dumps({
        "type": "chat", "from": sender, "text": text, "timestamp": doc["timestamp"].isoformat(),
    })

    for recipient in (to, sender):
        conn = active_connections.get(recipient)
        if conn:
            await conn.send_text(payload)


async def _handle_now_playing(sender: str, data: dict):
    to = (data.get("to") or "").strip().lower()
    if not to or not await _are_friends(sender, to):
        return

    conn = active_connections.get(to)
    if conn:
        await conn.send_text(json.dumps({
            "type": "now_playing",
            "from": sender,
            "title": data.get("title"),
            "artist": data.get("artist"),
            "position": data.get("position"),
            "is_playing": bool(data.get("is_playing", False)),
        }))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    username = await _authenticate_ws(websocket)
    if not username:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    active_connections[username] = websocket
    await _broadcast_presence(username, online=True)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")
            if msg_type == "chat":
                await _handle_chat(username, data)
            elif msg_type == "now_playing":
                await _handle_now_playing(username, data)
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        if active_connections.get(username) is websocket:
            active_connections.pop(username, None)
        await _broadcast_presence(username, online=False)
