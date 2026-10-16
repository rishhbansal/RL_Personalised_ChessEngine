import copy
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

IST = ZoneInfo("Asia/Kolkata")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOCAL_DB_FILE = os.path.join(DATA_DIR, "local_db.json")


def _serialize_value(v):
    if isinstance(v, ObjectId):
        return {"$oid": str(v)}
    if isinstance(v, datetime):
        return {"$date": v.isoformat()}
    if isinstance(v, dict):
        return {k: _serialize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_serialize_value(item) for item in v]
    return v


def _deserialize_value(v):
    if isinstance(v, dict):
        if len(v) == 1 and "$oid" in v:
            try:
                return ObjectId(v["$oid"])
            except Exception:
                return v["$oid"]
        if len(v) == 1 and "$date" in v:
            try:
                return datetime.fromisoformat(v["$date"])
            except Exception:
                return datetime.now(IST)
        return {k: _deserialize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_deserialize_value(item) for item in v]
    return v


class _InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class _LocalCursor:
    def __init__(self, docs: list[dict]):
        self._docs = docs

    def sort(self, key: str, direction: int = 1):
        reverse = direction < 0
        self._docs.sort(
            key=lambda d: (d.get(key) is not None, d.get(key)),
            reverse=reverse,
        )
        return self

    def limit(self, count: int):
        self._docs = self._docs[:count]
        return self

    async def to_list(self, length: int | None = None):
        if length is not None:
            return self._docs[:length]
        return list(self._docs)


class _PersistentDiskStore:
    """Thread-safe local JSON disk store that mirrors MongoDB collections when mongod is offline."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self._data: dict[str, list[dict]] = {"users": [], "games": []}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self._data = _deserialize_value(raw)
                if "users" not in self._data:
                    self._data["users"] = []
                if "games" not in self._data:
                    self._data["games"] = []
            except Exception as e:
                print(f"[DB] Warning loading local_db.json ({e}), starting fresh.")

    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        tmp_path = self.filepath + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(_serialize_value(self._data), f, indent=2)
        os.replace(tmp_path, self.filepath)

    def get_collection(self, name: str) -> list[dict]:
        if name not in self._data:
            self._data[name] = []
        return self._data[name]


_disk_store = _PersistentDiskStore(LOCAL_DB_FILE)
_mongo_online: bool | None = None
_motor_client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=600)
_motor_db = _motor_client["rl_chess"]


async def _is_mongo_available() -> bool:
    global _mongo_online
    if _mongo_online is not None:
        return _mongo_online
    try:
        await _motor_client.admin.command("ping")
        _mongo_online = True
    except Exception:
        _mongo_online = False
    return _mongo_online


def _matches_filter(doc: dict, query: dict) -> bool:
    if not query:
        return True
    for k, v in query.items():
        doc_val = doc.get(k)
        if isinstance(v, ObjectId) or isinstance(doc_val, ObjectId):
            if str(doc_val) != str(v):
                return False
        elif doc_val != v:
            return False
    return True


class HybridCollection:
    """Uses MongoDB if running, and automatically falls back to persistent local disk storage."""

    def __init__(self, name: str):
        self.name = name
        self._motor_col = _motor_db[name]

    async def create_index(self, *args, **kwargs):
        if await _is_mongo_available():
            return await self._motor_col.create_index(*args, **kwargs)
        return "local_index_ok"

    async def find_one(self, query: dict):
        if await _is_mongo_available():
            return await self._motor_col.find_one(query)
        col = _disk_store.get_collection(self.name)
        for doc in col:
            if _matches_filter(doc, query):
                return copy.deepcopy(doc)
        return None

    async def insert_one(self, doc: dict):
        if await _is_mongo_available():
            return await self._motor_col.insert_one(doc)
        col = _disk_store.get_collection(self.name)
        new_doc = copy.deepcopy(doc)
        if "_id" not in new_doc or new_doc["_id"] is None:
            new_doc["_id"] = ObjectId()
        col.append(new_doc)
        _disk_store.save()
        return _InsertResult(new_doc["_id"])

    async def update_one(self, query: dict, update: dict):
        if await _is_mongo_available():
            return await self._motor_col.update_one(query, update)
        col = _disk_store.get_collection(self.name)
        for doc in col:
            if _matches_filter(doc, query):
                if "$set" in update:
                    for k, v in update["$set"].items():
                        doc[k] = copy.deepcopy(v)
                if "$push" in update:
                    for k, v in update["$push"].items():
                        if k not in doc or not isinstance(doc[k], list):
                            doc[k] = []
                        doc[k].append(copy.deepcopy(v))
                _disk_store.save()
                return
        return

    def find(self, query: dict | None = None):
        query = query or {}
        if _mongo_online is True:
            return self._motor_col.find(query)
        col = _disk_store.get_collection(self.name)
        matched = [copy.deepcopy(d) for d in col if _matches_filter(d, query)]
        return _LocalCursor(matched)


class HybridDB:
    async def list_collection_names(self):
        if await _is_mongo_available():
            return await _motor_db.list_collection_names()
        return list(_disk_store._data.keys())


db = HybridDB()
users_collection = HybridCollection("users")
games_collection = HybridCollection("games")


async def ensure_indexes():
    if await _is_mongo_available():
        await users_collection.create_index("email", unique=True)
        await games_collection.create_index([("user_id", 1), ("started_at", -1)])
        print("Connected to MongoDB successfully and verified indexes.")
    else:
        print(
            f"[DB] MongoDB daemon not detected — using persistent disk database at {LOCAL_DB_FILE}"
        )