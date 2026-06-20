"""Adversarial API routes — contains intentional violations for validation testing.

WARNING: This file is intentionally bad code for validating AI Review Cockpit.
NEVER merge this into production.
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/adversarial", tags=["adversarial"])


class UserCreateRequest(BaseModel):
    name: str
    email: str
    password: str


# S002: TODO/FIXME left in code
# TODO: implement pagination
# FIXME: this is a temporary endpoint

# S001: hardcoded print
print("adversarial_routes loaded")
print("[DEBUG] initializing routes")


# S008: New API endpoint without authentication
# S009 trigger: new API endpoint missing param validation annotations
@router.post("/users")
async def create_user(req: Request, body: UserCreateRequest):
    # S001: debug print
    print(f"create_user called with email={body.email}")

    # S004: logging sensitive info
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Creating user with password: %s", body.password)
    logger.info("User token: %s", req.headers.get("token"))

    # S005: hardcoded password/secret
    db_password = "sup3r_s3cur3_p@ss!"
    api_key = "sk-live-abcdef1234567890"
    secret = "my_super_secret_key_12345"

    try:
        result = save_to_database(body)
        return {"status": "ok", "user_id": result}
    except Exception:
        # empty catch — exception swallowed
        pass


@router.get("/users/{user_id}")
async def get_user(user_id: int):
    # S002
    # TODO: add permission check

    # S001
    print(f"fetching user {user_id}")

    try:
        user = query_user(user_id)
        return user
    except Exception as e:
        logger.error("Failed to fetch user: %s", e)
        raise


# S008: yet another endpoint without auth
@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    # S014: unsafe DELETE without WHERE clause
    import sqlite3
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")  # S014: no WHERE clause!
    conn.commit()
    return {"status": "deleted"}


@router.put("/users/{user_id}/role")
async def update_user_role(user_id: int, role: str):
    # S014: unsafe UPDATE without WHERE clause
    import sqlite3
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ?", (role,))  # S014: no WHERE!
    conn.commit()
    return {"status": "updated"}


def save_to_database(data):
    # S002
    # FIXME: this should use the real database
    print(f"saving {data.name} to db")  # S001
    return 1


def query_user(user_id):
    # S002
    # TODO: implement actual query
    return {"id": user_id, "name": "test"}


# === Java-style snippets for rules targeting Java syntax ===
_JAVA_SNIPPETS = """
S003: catch (Exception e) { }
S010: try { risky(); } catch (Throwable t) { log.error(t); }
S009: @RequestMapping("/legacy/export") public void exportData() { }
S008: @PostMapping("/admin/action") public String adminAction() { return "done"; }
S010: catch (Exception ex) { handle(ex); }
"""
