"""Flask application factory."""
import logging
import os
import cloudinary
from flask import Flask
from flask_cors import CORS

from app.config import config
from app.extensions import init_mongo, jwt, socketio


def _init_cloudinary(app):
    """Initialize Cloudinary from CLOUDINARY_URL or individual keys."""
    cloudinary_url = app.config.get("CLOUDINARY_URL") or os.getenv("CLOUDINARY_URL")
    if cloudinary_url:
        os.environ.setdefault("CLOUDINARY_URL", cloudinary_url)
        cloudinary.config(secure=True)
    elif app.config.get("CLOUDINARY_CLOUD_NAME"):
        cloudinary.config(
            cloud_name=app.config["CLOUDINARY_CLOUD_NAME"],
            api_key=app.config["CLOUDINARY_API_KEY"],
            api_secret=app.config["CLOUDINARY_API_SECRET"],
            secure=True,
        )


def create_app(config_name=None):
    app = Flask(__name__)
    env = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config.get(env, config["default"]))

    logging.basicConfig(level=logging.INFO)
    logging.info("MongoDB database: %s", app.config["MONGODB_DB"])

    CORS(app, origins=[app.config["FRONTEND_URL"], "http://localhost:5173"], supports_credentials=True)

    jwt.init_app(app)
    init_mongo(app)
    socketio.init_app(app, async_mode="eventlet")
    _init_cloudinary(app)

    from app.controllers import register_blueprints
    register_blueprints(app)

    from app.sockets.chat import register_socket_events
    register_socket_events(socketio)

    @app.route("/api/health")
    def health():
        return {
            "status": "ok",
            "service": "Bright Future English API",
            "db": app.config["MONGODB_DB"],
            "cloudinary_folder": app.config["CLOUDINARY_FOLDER_PREFIX"],
        }, 200

    return app
