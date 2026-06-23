"""Module __init__.py."""
from .auth import auth_bp
from .chats import chats_bp
from .documents import documents_bp
from .conversations import conversations_bp
from .projects import projects_bp


def register_blueprints(app):
    """register_blueprints function."""
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(documents_bp, url_prefix="/api/documents")
    app.register_blueprint(chats_bp, url_prefix="/api/chats")
    app.register_blueprint(conversations_bp, url_prefix="/api/conversations")
    app.register_blueprint(projects_bp, url_prefix="/api/projects")
