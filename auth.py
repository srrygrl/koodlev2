import os
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

# Em produção (Railway), defina a variável de ambiente JWT_SECRET com uma
# string aleatória longa. O valor abaixo é só um fallback pra rodar local.
SECRET_KEY = os.environ.get("JWT_SECRET", "troque-essa-chave-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


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
