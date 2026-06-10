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
