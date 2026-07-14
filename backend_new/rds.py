"""MySQL (RDS) access for course material — file bytes + metadata live in one
table here since the AWS account this runs under only has RDS + DynamoDB
permissions (no S3). DynamoDB items cap out at 400KB, too small for uploaded
PDFs/slides, so course material uses RDS instead.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator

import pymysql
import pymysql.cursors

RDS_HOST = os.environ.get("RDS_HOST", "")
RDS_PORT = int(os.environ.get("RDS_PORT", "3306"))
RDS_DB_NAME = os.environ.get("RDS_DB_NAME", "thapar_connect")
RDS_USER = os.environ.get("RDS_USER", "")
RDS_PASSWORD = os.environ.get("RDS_PASSWORD", "")

CREATE_COURSE_MATERIALS_TABLE = """
CREATE TABLE IF NOT EXISTS course_materials (
    material_id CHAR(36) PRIMARY KEY,
    course_code VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    content_type VARCHAR(128) NOT NULL,
    size_bytes INT NOT NULL,
    file_data LONGBLOB NOT NULL,
    uploaded_by VARCHAR(64) NOT NULL,
    uploaded_by_name VARCHAR(255) NOT NULL,
    uploaded_at VARCHAR(64) NOT NULL,
    INDEX idx_course_code (course_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def _require_config() -> None:
    missing = [name for name, value in (("RDS_HOST", RDS_HOST), ("RDS_USER", RDS_USER)) if not value]
    if missing:
        raise RuntimeError(f"Server misconfigured: missing env var(s): {', '.join(missing)}")


@lru_cache(maxsize=1)
def get_connection_pool_config() -> dict[str, Any]:
    _require_config()
    return {
        "host": RDS_HOST,
        "port": RDS_PORT,
        "user": RDS_USER,
        "password": RDS_PASSWORD,
        "database": RDS_DB_NAME,
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }


@contextmanager
def get_connection() -> Iterator[pymysql.connections.Connection]:
    connection = pymysql.connect(**get_connection_pool_config())
    try:
        yield connection
    finally:
        connection.close()


def _ensure_database_exists() -> None:
    """The RDS instance only ships with MySQL's built-in system schemas until
    someone creates RDS_DB_NAME, so connect without selecting a database first
    and create it if missing."""
    _require_config()
    config = dict(get_connection_pool_config())
    config.pop("database")
    connection = pymysql.connect(**config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{RDS_DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        connection.close()


def ensure_schema() -> None:
    _ensure_database_exists()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_COURSE_MATERIALS_TABLE)
