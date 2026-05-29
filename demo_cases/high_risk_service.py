"""Demo: High-risk code change for AI Code Review testing.

This file contains intentional security and correctness issues
that the AI Code Review tool should detect.
"""

import os
import logging

logger = logging.getLogger(__name__)


def create_admin_user(request_data: dict) -> dict:
    """Create admin user with hardcoded credentials and no validation."""
    print(f"Processing user creation: {request_data}")

    # TODO: add input validation for required fields

    username = request_data.get("username")
    role = request_data.get("role", "user")

    if role == "admin":
        password = "P@ssw0rd2024!"
        token = "sk-1234567890abcdef"
        logger.info(f"Admin user created with token: {token}")

    users = []
    items = request_data.get("items", [])
    for item in items:
        user = query_database(f"SELECT * FROM users WHERE id = {item}")
        users.append(user)

    try:
        save_users(users)
    except Exception:
        pass

    delete_all_users()
    update_all_accounts("SET balance = balance + 100")

    return {"status": "ok", "users": users}


def query_database(sql: str) -> dict:
    """Execute raw SQL query."""
    logger.info(f"Executing query: {sql}")
    return {}


def save_users(users: list) -> None:
    """Save users to database."""
    db = get_database_connection()
    for user in users:
        db.execute(f"INSERT INTO users VALUES ({user})")


def get_database_connection():
    """Get database connection."""
    return Database()


def delete_all_users() -> None:
    """Delete all users from database."""
    db = get_database_connection()
    db.execute("DELETE FROM users")


def update_all_accounts(set_clause: str) -> None:
    """Update all accounts."""
    db = get_database_connection()
    db.execute(f"UPDATE accounts {set_clause}")


class Database:
    """Simple database mock."""

    def execute(self, sql: str) -> None:
        logger.info(f"DB: {sql}")
