# -*- coding: utf-8 -*-
"""판매 기록 (SQLite)."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "sales.db"


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                tier TEXT NOT NULL,
                license_key TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                source TEXT NOT NULL,
                product_name TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activations (
                license_key TEXT PRIMARY KEY,
                machine_id TEXT NOT NULL,
                machine_label TEXT,
                bound_at TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
            """
        )


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def sale_exists(order_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT 1 FROM sales WHERE order_id = ?", (order_id,)).fetchone()
        return row is not None


def save_sale(
    *,
    order_id: str,
    email: str,
    tier: str,
    license_key: str,
    expires_at: datetime,
    source: str,
    product_name: str = "",
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO sales (order_id, email, tier, license_key, expires_at, source, product_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                email,
                tier,
                license_key,
                expires_at.isoformat(),
                source,
                product_name,
                datetime.now().isoformat(),
            ),
        )


def count_sales() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) FROM sales").fetchone()
        return int(row[0]) if row else 0


def get_activation(license_key: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT license_key, machine_id, machine_label, bound_at, last_seen FROM activations WHERE license_key = ?",
            (license_key.upper(),),
        ).fetchone()
    if not row:
        return None
    return {
        "license_key": row[0],
        "machine_id": row[1],
        "machine_label": row[2],
        "bound_at": row[3],
        "last_seen": row[4],
    }


def bind_activation(*, license_key: str, machine_id: str, machine_label: str = "") -> dict:
    license_key = license_key.upper()
    machine_id = machine_id.upper()
    now = datetime.now().isoformat()
    existing = get_activation(license_key)

    if existing and existing["machine_id"] != machine_id:
        return {"ok": False, "reason": "already_bound", "bound_machine": existing["machine_id"]}

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO activations (license_key, machine_id, machine_label, bound_at, last_seen)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(license_key) DO UPDATE SET
                machine_id = excluded.machine_id,
                machine_label = excluded.machine_label,
                last_seen = excluded.last_seen
            """,
            (
                license_key,
                machine_id,
                machine_label,
                existing["bound_at"] if existing else now,
                now,
            ),
        )

    return {
        "ok": True,
        "license_key": license_key,
        "machine_id": machine_id,
        "bound_at": existing["bound_at"] if existing else now,
    }


def unbind_activation(license_key: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM activations WHERE license_key = ?", (license_key.upper(),))
        return cur.rowcount > 0


def count_activations() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) FROM activations").fetchone()
        return int(row[0]) if row else 0
