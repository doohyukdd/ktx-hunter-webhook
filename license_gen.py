# -*- coding: utf-8 -*-
"""서버용 라이선스 키 발급 (클라이언트 license.py 와 동일 알고리즘)."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta


def _secret() -> bytes:
    value = os.environ.get("KTH_LICENSE_SECRET", "")
    if not value or value == "CHANGE-THIS-SECRET-BEFORE-SELLING-kth-2026":
        raise RuntimeError("KTH_LICENSE_SECRET 환경변수가 설정되지 않았습니다.")
    return value.encode("utf-8")


def sign_license(tier: str, expiry_yyyymmdd: str) -> str:
    payload = f"{tier.upper()}:{expiry_yyyymmdd}"
    digest = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:8].upper()


def format_license_key(tier: str, expiry_yyyymmdd: str) -> str:
    tier = tier.upper()
    return f"KTH-{tier}-{expiry_yyyymmdd}-{sign_license(tier, expiry_yyyymmdd)}"


def generate_license(tier: str, days: int, *, from_date: datetime | None = None) -> tuple[str, datetime]:
    start = from_date or datetime.now()
    expires = start + timedelta(days=days)
    expiry_str = expires.strftime("%Y%m%d")
    key = format_license_key(tier, expiry_str)
    return key, expires.replace(hour=23, minute=59, second=59)


def generate_order_id() -> str:
    return secrets.token_hex(4).upper()
