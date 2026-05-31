"""Adversarial service layer — contains intentional violations for validation testing.

WARNING: This file is intentionally bad code for validating AI Review Cockpit.
NEVER merge this into production.
"""
import logging

logger = logging.getLogger(__name__)

# S001: debug print at module level
print("[WARN] adversarial_service loaded in debug mode")

# S005: hardcoded credentials
DB_CONNECTION_STRING = "postgresql://admin:P@ssw0rd123!@localhost:5432/prod"
REDIS_PASSWORD = "redis_s3cr3t_2024"
JWT_SECRET = "jwt_sup3r_s3cr3t_k3y_2024"


def batch_update_users(user_ids, new_role):
    """Batch update users — contains N+1 query pattern (S011)."""
    # S001
    print(f"batch updating {len(user_ids)} users to role={new_role}")

    # S011: Database call inside for loop — N+1 problem
    for uid in user_ids:
        # TODO: this should be a single UPDATE query (S002)
        user = user_mapper.find_by_id(uid)  # S011: DB call in loop ('.find' + 'mapper')
        user_mapper.save(user)  # also DB call

    # S004: logging sensitive info
    logger.info("Batch update complete, new role: %s", new_role)
    return len(user_ids)


def process_orders(orders):
    """Process a list of orders — contains N+1 and S013 issues."""
    # S001
    print(f"processing {len(orders)} orders")

    # S011: for loop with DB call inside
    for order in orders:
        # S002
        # TODO: add inventory check
        user = user_repository.find(order["user_id"])  # S011: 'repository' + '.find'
        order_repository.save(user)  # also in loop

    # S011: while loop with DB/API call
    cursor = 0
    while cursor < len(orders):
        db.session.query(orders[cursor]["product_id"])  # S011: 'db.' + '.query' in while
        cursor += 1

    # S013: multiple writes without transaction
    _update_order_status(orders[0]["id"], "processed")
    _deduct_inventory(orders[0]["product_id"], orders[0]["quantity"])
    _update_user_balance(orders[0]["user_id"], orders[0]["total"])

    return {"processed": len(orders)}


def export_sensitive_data():
    """Export data — contains unsafe SQL (S014)."""
    import sqlite3

    conn = sqlite3.connect("analytics.db")
    cursor = conn.cursor()

    # S014: unsafe DELETE without WHERE
    cursor.execute("DELETE FROM audit_logs")
    conn.commit()

    # S014: DELETE with WHERE — should NOT fire (has WHERE)
    cursor.execute("DELETE FROM temp_data WHERE expiry < datetime('now')")
    conn.commit()

    return True


def _update_user_in_db(uid, role):
    print(f"updating db for user {uid}")  # S001
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, uid))
    conn.commit()


def _get_user_by_id(uid):
    print(f"querying user {uid}")  # S001
    return {"id": uid, "email": "test@example.com", "name": "test"}


def _send_notification(email, order):
    print(f"sending email to {email}")  # S001
    # TODO: implement actual email sending (S002)


def _update_inventory(product_id):
    print(f"updating inventory for product {product_id}")  # S001
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.execute("UPDATE products SET stock = stock - 1 WHERE id = ?", (product_id,))
    conn.commit()


def _update_order_status(order_id, status):
    print(f"updating order {order_id} to {status}")  # S001


def _deduct_inventory(product_id, qty):
    print(f"deducting {qty} from product {product_id}")  # S001


def _update_user_balance(user_id, amount):
    print(f"updating balance for user {user_id}")  # S001
