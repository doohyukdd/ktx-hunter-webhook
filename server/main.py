# -*- coding: utf-8 -*-
"""
결제 웹훅 → 라이선스 자동 발급 → 이메일 자동 발송

Gumroad Ping URL: POST /webhook/gumroad
Lemon Squeezy URL: POST /webhook/lemonsqueezy
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Header, HTTPException, Request

from database import count_sales, init_db, sale_exists, save_sale
from email_sender import send_license_email
from license_gen import generate_license, generate_order_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kth-webhook")

app = FastAPI(title="KTX Ticket Hunter Automation", version="1.0.0")

PRODUCTS_FILE = Path(__file__).parent / "products.json"


def _load_products() -> dict:
    if PRODUCTS_FILE.exists():
        return json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))
    return {"products": [], "default": {"tier": "PRO", "days": 30}}


def _resolve_product(*, permalink: str = "", product_name: str = "", product_id: str = "") -> tuple[str, int]:
    catalog = _load_products()
    permalink = (permalink or "").lower()
    product_name = product_name or ""
    product_id = product_id or ""

    for item in catalog.get("products", []):
        if item.get("permalink") and item["permalink"].lower() in permalink:
            return item["tier"], int(item["days"])
        if item.get("product_id") and item["product_id"] == product_id:
            return item["tier"], int(item["days"])
        contains = item.get("product_name_contains", "")
        if contains and contains in product_name:
            return item["tier"], int(item["days"])

    default = catalog.get("default", {"tier": "PRO", "days": 30})
    return default["tier"], int(default["days"])


def _process_sale(
    *,
    order_id: str,
    email: str,
    product_name: str,
    permalink: str,
    product_id: str,
    source: str,
    refunded: bool = False,
) -> dict:
    if refunded:
        logger.info("Refund ignored order_id=%s", order_id)
        return {"status": "ignored", "reason": "refund"}

    if sale_exists(order_id):
        logger.info("Duplicate order_id=%s", order_id)
        return {"status": "duplicate", "order_id": order_id}

    tier, days = _resolve_product(permalink=permalink, product_name=product_name, product_id=product_id)
    license_key, expires_at = generate_license(tier, days)

    save_sale(
        order_id=order_id,
        email=email,
        tier=tier,
        license_key=license_key,
        expires_at=expires_at,
        source=source,
        product_name=product_name,
    )

    send_license_email(
        email,
        license_key=license_key,
        tier=tier,
        expires_at=expires_at.strftime("%Y-%m-%d"),
        order_id=order_id,
    )

    logger.info("Sale processed order_id=%s email=%s tier=%s", order_id, email, tier)
    return {
        "status": "ok",
        "order_id": order_id,
        "tier": tier,
        "expires_at": expires_at.strftime("%Y-%m-%d"),
    }


@app.on_event("startup")
def startup() -> None:
    init_db()
    logger.info("Automation server started. Total sales: %s", count_sales())


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "sales": count_sales(), "time": datetime.now().isoformat()}


@app.get("/")
def root() -> dict:
    return {
        "service": "KTX Ticket Hunter Automation",
        "webhooks": ["/webhook/gumroad", "/webhook/lemonsqueezy"],
        "health": "/health",
    }


@app.post("/webhook/gumroad")
async def webhook_gumroad(
    seller_id: str = Form(default=""),
    sale_id: str = Form(default=""),
    email: str = Form(default=""),
    product_id: str = Form(default=""),
    product_name: str = Form(default=""),
    permalink: str = Form(default=""),
    refunded: str = Form(default="false"),
    test: str = Form(default="false"),
):
    expected_seller = os.environ.get("GUMROAD_SELLER_ID", "")
    if expected_seller and seller_id != expected_seller:
        raise HTTPException(status_code=403, detail="Invalid seller_id")

    if not email or not sale_id:
        raise HTTPException(status_code=400, detail="Missing email or sale_id")

    # Gumroad "Send test ping" (no sale) — skip only when sale_id is empty
    order_id = f"GM-{sale_id}"
    return _process_sale(
        order_id=order_id,
        email=email,
        product_name=product_name,
        permalink=permalink,
        product_id=product_id,
        source="gumroad",
        refunded=refunded.lower() == "true",
    )


@app.post("/webhook/lemonsqueezy")
async def webhook_lemonsqueezy(
    request: Request,
    x_signature: str = Header(default=""),
):
    secret = os.environ.get("LEMONSQUEEZY_WEBHOOK_SECRET", "")
    body = await request.body()

    if secret:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_signature):
            raise HTTPException(status_code=403, detail="Invalid signature")

    payload = json.loads(body)
    event_name = payload.get("meta", {}).get("event_name", "")
    if event_name != "order_created":
        return {"status": "ignored", "event": event_name}

    attrs = payload.get("data", {}).get("attributes", {})
    email = attrs.get("user_email", "")
    order_number = str(attrs.get("order_number", generate_order_id()))
    product_name = attrs.get("first_order_item", {}).get("product_name", "")
    variant_name = attrs.get("first_order_item", {}).get("variant_name", "")
    full_name = f"{product_name} {variant_name}".strip()

    order_id = f"LS-{order_number}"
    return _process_sale(
        order_id=order_id,
        email=email,
        product_name=full_name,
        permalink="",
        product_id="",
        source="lemonsqueezy",
    )


@app.get("/admin/stats")
def admin_stats(x_admin_key: str = Header(default="")) -> dict:
    admin_key = os.environ.get("ADMIN_API_KEY", "")
    if not admin_key or not hmac.compare_digest(x_admin_key, admin_key):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"sales": count_sales()}
