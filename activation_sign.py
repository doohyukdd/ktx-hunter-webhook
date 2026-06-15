# -*- coding: utf-8 -*-
"""1PC 바인딩 서명 (서버)."""

from __future__ import annotations

import hashlib
import hmac
import os


def _secret() -> bytes:
    value = os.environ.get("KTH_LICENSE_SECRET", "")
    if not value:
        raise RuntimeError("KTH_LICENSE_SECRET not set")
    return value.encode("utf-8")


def sign_activation_token(license_key: str, machine_id: str) -> str:
    payload = f"ACT:{license_key.strip().upper()}:{machine_id.strip().upper()}"
    return hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16].upper()
