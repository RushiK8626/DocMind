"""Module Auth"""

from datetime import timedelta
from sqlalchemy import select
from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    jwt_required,
    get_jwt_identity,
)

from app.extensions import db
from app.models.user import User
from app.services.jwt_service import blacklist_token

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """register function."""
    data = request.get_json()

    email = data.get("email")
    username = data.get("username")
    password = data.get("password")

    if not email or not username or not password:
        return jsonify({"error": "Email, username and password required"}), 400

    existing_user = db.session.scalar(
        select(User).where(or_(User.email == email, User.username == username))
    )

    if existing_user:
        return jsonify({"error": "Email already exists"}), 409

    user = User(email=email, username=username)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """login function."""
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = db.session.scalar(
        select(User).where(or_(User.email == email, User.username == email))
    )

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(
        identity=user.id, expires_delta=timedelta(hours=1)
    )

    return jsonify({"access_token": access_token})


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """me function."""
    user_id = get_jwt_identity()

    user = db.session.get(User, user_id)

    return jsonify({"id": user.id, "username": user.username, "email": user.email})


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """logout function."""
    claims = get_jwt()
    jti = claims["jti"]
    exp = claims["exp"]

    blacklist_token(jti=jti, exp=exp)
    return jsonify({"status": "success", "message": "Logged out successfully"}), 200
