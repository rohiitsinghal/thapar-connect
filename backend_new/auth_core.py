"""Shared JWT + bcrypt + DynamoDB helpers used by the student and faculty auth routers."""

from __future__ import annotations

import os
import time
from typing import Any

import bcrypt
import jwt
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException

JWT_ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 60 * 60 * 12  # 12 hours


def jwt_secret() -> str:
    secret = os.environ.get("AUTH_JWT_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="Server misconfigured: AUTH_JWT_SECRET is not set")
    return secret


def issue_token(subject: str, role: str) -> str:
    payload = {"sub": subject, "role": role, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALGORITHM)


def claims_from_token(authorization: str) -> dict[str, Any]:
    """Decode a bearer token without enforcing a specific role, for endpoints
    that accept multiple roles (e.g. student/faculty/admin)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = jwt.decode(token, jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc

    if not claims.get("role") or not claims.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid session")

    return claims


def subject_from_token(authorization: str, expected_role: str) -> str:
    claims = claims_from_token(authorization)
    if claims.get("role") != expected_role:
        raise HTTPException(status_code=401, detail="Invalid session")

    return claims["sub"]


def get_item_or_404(table: Any, key_name: str, key_value: str, not_found_message: str) -> dict[str, Any]:
    try:
        response = table.get_item(Key={key_name: key_value})
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=f"DynamoDB error: {exc}") from exc

    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail=not_found_message)
    return item


def check_password(item: dict[str, Any], password: str) -> bool:
    password_hash = item.get("password_hash")
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), str(password_hash).encode("utf-8"))


def set_password(table: Any, key_name: str, key_value: str, new_password: str) -> None:
    new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    try:
        table.update_item(
            Key={key_name: key_value},
            UpdateExpression="SET password_hash = :hash, password_is_default = :is_default",
            ExpressionAttributeValues={":hash": new_hash, ":is_default": False},
        )
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=f"DynamoDB error: {exc}") from exc
