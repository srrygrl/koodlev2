import os

import motor.motor_asyncio

# motor é a versão assíncrona oficial do pymongo, feita pelo mesmo time da
# MongoDB — usamos ela em vez do pymongo puro porque o servidor inteiro é
# assíncrono (FastAPI + WebSocket), e o pymongo normal bloquearia o loop de
# eventos a cada consulta.
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "koddle")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]

users_collection = db["users"]
friendships_collection = db["friendships"]
messages_collection = db["messages"]


async def ensure_indexes():
    """Cria os índices necessários — roda uma vez quando o servidor inicia."""
    await users_collection.create_index("username", unique=True)
    # sparse=True: ignora documentos sem o campo "email" na hora de checar
    # unicidade — isso evita quebrar por causa de contas antigas criadas
    # antes desse campo existir.
    await users_collection.create_index("email", unique=True, sparse=True)
    await friendships_collection.create_index("pair")
    await messages_collection.create_index("pair")
    await messages_collection.create_index("timestamp")
