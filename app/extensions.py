"""Flask extensions initialization."""
from flask_jwt_extended import JWTManager
from pymongo import MongoClient

jwt = JWTManager()
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
