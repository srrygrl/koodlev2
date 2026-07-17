import os

import motor.motor_asyncio

# motor é a versão assíncrona oficial do pymongo, feita pelo mesmo time da
# MongoDB — usamos ela em vez do pymongo puro porque o servidor inteiro é
# assíncrono (FastAPI + WebSocket), e o pymongo normal bloquearia o loop de
# eventos a cada consulta.
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb+srv://koddle:j4WeCZY7Bsb1jXyo@cluster0.9ozxmq6.mongodb.net/?appName=Cluster0")
DB_NAME = os.environ.get("DB_NAME", "koddle")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]

users_collection = db["users"]
friendships_collection = db["friendships"]
messages_collection = db["messages"]


async def ensure_indexes():
    """Cria os índices necessários — roda uma vez quando o servidor inicia."""
    await users_collection.create_index("username", unique=True)
    await friendships_collection.create_index("pair")
    await messages_collection.create_index("pair")
    await messages_collection.create_index("timestamp")
