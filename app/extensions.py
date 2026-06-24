"""Flask extensions initialization."""
import logging
import os
import sys

from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from pymongo import MongoClient

jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*")


def resolve_socketio_async_mode() -> str:
    """Pick a Socket.IO async driver compatible with the current Python runtime."""
    explicit = os.getenv("SOCKETIO_ASYNC_MODE", "").strip().lower()
    if explicit:
        return explicit
    # eventlet breaks on Python 3.13+ (threading.start_joinable_thread missing in green.thread)
    if sys.version_info >= (3, 13):
        logging.warning(
            "Python %s is incompatible with eventlet; using threading for Socket.IO",
            sys.version.split()[0],
        )
        return "threading"
    return "eventlet"
mongo_client = None
db = None


def init_mongo(app):
    global mongo_client, db
    mongo_client = MongoClient(app.config["MONGODB_URI"])
    db = mongo_client[app.config["MONGODB_DB"]]
    try:
        from app.models.collections import create_indexes
        create_indexes(db)
    except Exception:
        pass
    return db


def get_db():
    return db
