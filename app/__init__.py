"""Flask application factory."""
import logging
import os
import cloudinary
from flask import Flask, jsonify, request
from flask_cors import CORS

from app.config import config, _build_cors_origins, origin_allowed
from app.extensions import init_mongo, jwt


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

    cors_origins = _build_cors_origins()
    app.config["CORS_ORIGINS"] = cors_origins
    logging.info("CORS origins: %s", cors_origins)

    CORS(
        app,
        origins=cors_origins,
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        expose_headers=["Content-Type", "Authorization"],
    )

    @app.after_request
    def ensure_cors_headers(response):
        """Always attach CORS on API responses (incl. errors / worker edge cases)."""
        origin = request.headers.get("Origin")
        if origin and origin_allowed(origin, cors_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers.add("Vary", "Origin")
        return response

    @app.errorhandler(Exception)
    def handle_unhandled_exception(err):
        logging.exception("Unhandled error: %s", err)
        return jsonify({"error": "Internal server error"}), 500

    jwt.init_app(app)
    init_mongo(app)
    _init_cloudinary(app)

    from app.controllers import register_blueprints
    register_blueprints(app)

    @app.route("/api/health")
    def health():
        return {
            "status": "ok",
            "service": "Bright Future English API",
            "db": app.config["MONGODB_DB"],
            "cloudinary_folder": app.config["CLOUDINARY_FOLDER_PREFIX"],
        }, 200

    return app
