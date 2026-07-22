"""DynamoDB access shared by the auth router and the student import script."""

from __future__ import annotations

import os
from functools import lru_cache

import boto3

AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
STUDENTS_TABLE_NAME = os.environ.get("DYNAMODB_STUDENTS_TABLE", "students")
FACULTY_TABLE_NAME = os.environ.get("DYNAMODB_FACULTY_TABLE", "faculty")
COURSES_TABLE_NAME = os.environ.get("DYNAMODB_COURSES_TABLE", "courses")


@lru_cache(maxsize=1)
def get_students_table():
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(STUDENTS_TABLE_NAME)


@lru_cache(maxsize=1)
def get_faculty_table():
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(FACULTY_TABLE_NAME)


@lru_cache(maxsize=1)
def get_courses_table():
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(COURSES_TABLE_NAME)
