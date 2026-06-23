"""Module config.py."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class Config:
    """Config class."""

    try:
        BASE_DIR = Path(__file__).resolve().parent.parent

        SQLALCHEMY_DATABASE_URI: str = os.environ["SQLALCHEMY_DATABASE_URI"]
        SQLALCHEMY_TRACK_MODIFICATIONS: str = False

        JWT_SECRET_KEY: str = os.environ["JWT_SECRET_KEY"]

        SERPAPI_KEY: str = os.environ["SERPAPI_KEY"]

        LLAMA_CLOUD_API_KEY: str = os.environ["LLAMA_CLOUD_API_KEY"]

        CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
        CHROMA_PORT = int(os.environ.get("CHROMA_PORT", 8000))
        CHROMA_PERSIST_DIR: str = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
        CHROMA_COLLECTION_NAME: str = os.environ.get(
            "CHROMA_COLLECTION_NAME", "collection"
        )
        TOP_K_RESULTS: int = int(os.environ.get("TOK_K_RESULTS", 15))

        LLM_API_KEY = os.environ["LLM_API_KEY"]
        LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", 2048))
        LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.2))

        WEB_SEARCH_MAX_RESULTS = int(os.environ.get("WEB_SEARCH_MAX_RESULTS", 5))
        CODE_EXEC_TIMEOUT = int(os.environ.get("CODE_EXEC_TIMEOUT", 10))

        REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
        REDIS_DB = int(os.environ.get("REDIS_DB", 0))
        REDIS_CACHE_TIMEOUT = int(os.environ.get("REDIS_CACHE_TIMEOUT"))

        AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
        AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
        AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

        FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
        FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))
        FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    except KeyError as e:
        print(f"Error: The key '{e.args[0]}' does not exist.")
