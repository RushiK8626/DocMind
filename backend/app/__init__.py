"""Module __init__.py."""
import os
import logging
import colorlog


os.environ.setdefault("LITELLM_CACHE", "false")

import litellm
from flask import Flask
from flask_cors import CORS
from app.api import register_blueprints
from app.config import Config
from app.extensions import db, jwt, init_chroma, init_redis, init_s3
from app.services.jwt_service import is_blacklisted
from app.tasks.celery_utils import celery_init_app



_original_completion = litellm.completion


def _patched_completion(*args, **kwargs):
    """_patched_completion function."""
    messages = kwargs.get("messages", [])
    if messages:
        for msg in messages:
            if isinstance(msg, dict) and "cache_breakpoint" in msg:
                del msg["cache_breakpoint"]
    return _original_completion(*args, **kwargs)


litellm.completion = _patched_completion


def create_app():
    """create_app function."""
    app = Flask(__name__)
    CORS(app, origins=["http://localhost:5173"])

    app.config.from_object(Config)
    
    
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            }
        )
    )

    app.logger.handlers.clear()  
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    

    db.init_app(app)
    jwt.init_app(app)
    init_redis(app)
    init_chroma(app)
    init_s3(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """check_if_token_revoked function."""
        return is_blacklisted(jwt_payload["jti"])

    @jwt.revoked_token_loader
    def revoked_token_response(jwt_header, jwt_payload):
        """revoked_token_response function."""
        return {
            "status": "error",
            "message": "Token has been revoked. Please log in again.",
        }, 401

    with app.app_context():
        db.create_all()

    celery_app = celery_init_app(app)

    register_blueprints(app)

    return app
