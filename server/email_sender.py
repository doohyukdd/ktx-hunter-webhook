# -*- coding: utf-8 -*-
"""구매 확인 이메일 자동 발송 (Resend API)."""

from __future__ import annotations

import os

import httpx


def send_license_email(
    to_email: str,
    *,
    license_key: str,
    tier: str,
    expires_at: str,
    order_id: str,
) -> None:
    api_key = os.environ.get("RESEND_API_KEY", "")
    from_email = os.environ.get("EMAIL_FROM", "KTX Ticket Hunter <onboarding@resend.dev>")
    download_url = os.environ.get("DOWNLOAD_URL", "https://gumroad.com")

    if not api_key:
        raise RuntimeError("RESEND_API_KEY 가 설정되지 않았습니다.")

    tier_label = {"PRO": "프로 (고속조회+자동예약)", "STD": "스탠다드 (알림+모니터링)"}.get(tier, tier)

    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:0 auto">
      <h2>KTX Ticket Hunter 구매 감사합니다</h2>
      <p>주문번호: <b>{order_id}</b></p>
      <p>등급: <b>{tier_label}</b></p>
      <p>만료일: <b>{expires_at}</b></p>
      <hr>
      <h3>라이선스 키</h3>
      <p style="font-size:18px;background:#f4f4f4;padding:12px;font-family:monospace">
        {license_key}
      </p>
      <h3>설치 방법</h3>
      <ol>
        <li><a href="{download_url}">다운로드 페이지</a>에서 ZIP 받기 (Gumroad 구매 내역)</li>
        <li>압축 해제 후 <code>config.example.yaml</code> → <code>config.yaml</code> 로 복사</li>
        <li>코레일 아이디/비밀번호 입력</li>
        <li><code>activate.bat {license_key}</code> 실행</li>
        <li><code>run.bat</code> 실행 (창 닫지 마세요)</li>
      </ol>
      <p style="color:#666;font-size:12px">
        본인 코레일 계정만 사용하세요. 예약 후 앱에서 직접 결제해야 합니다.
      </p>
    </div>
    """

    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": from_email,
            "to": [to_email],
            "subject": f"[KTX Ticket Hunter] 라이선스 키 ({tier_label})",
            "html": html,
        },
        timeout=30.0,
    )
    response.raise_for_status()
