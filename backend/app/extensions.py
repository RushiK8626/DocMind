"""Module extensions.py."""
import uuid
import boto3
import chromadb
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from redis import Redis
from flask_caching import Cache

chroma_client = None
redis_client: Redis = None
s3_client = None

db = SQLAlchemy()
jwt = JWTManager()
cache = Cache()


def init_redis(app):
    """init_redis function."""
    global redis_client
    redis_client = Redis(
        host=app.config["REDIS_HOST"],
        port=app.config["REDIS_PORT"],
        db=app.config["REDIS_DB"],
        password=app.config.get("REDIS_PASSWORD"),
        decode_responses=True,
    )
    redis_client.ping()
    app.logger.info("Redis connected successfully")


def init_chroma(app):
    """init_chroma function."""
    global chroma_client
    chroma_client = chromadb.PersistentClient(path=app.config["CHROMA_PERSIST_DIR"])
    app.logger.info("ChromaDB connected successfully")


def init_s3(app):
    """init_s3 function."""
    global s3_client
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=app.config["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=app.config["AWS_SECRET_ACCESS_KEY"],
        region_name=app.config["AWS_REGION"],
    )
    app.logger.info("AWS S3 connected successfully")
