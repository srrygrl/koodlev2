import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

# Em produção (Railway), defina a variável de ambiente JWT_SECRET com uma
# string aleatória longa. O valor abaixo é só um fallback pra rodar local.
SECRET_KEY = os.environ.get("JWT_SECRET", "troque-essa-chave-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    # bcrypt tem um limite de 72 bytes por senha — corta com segurança antes
    # de gerar o hash, pra nunca dar erro em senhas mais longas.
    raw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        raw = password.encode("utf-8")[:72]
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
