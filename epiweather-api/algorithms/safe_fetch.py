"""외부 URL 내려받기 안전 래퍼(SSRF·용량 방어).

두 불리틴 엔드포인트가 임의 http(s) URL을 120초·무제한으로 받아왔다.
API 키 소지자만 호출하지만 키는 공유될 수 있고, 응답 크기 DoS는 키와 무관하다.
여기서 한 번에 막는다:

1) 스킴은 http/https만. userinfo·비표준 포트 거부.
2) 호스트가 사설·루프백·링크로컬·예약 대역이면 거부(DNS로 풀린 전 주소 검사).
   ★ 잔여 위험: 검사와 연결 사이 DNS가 바뀌는 재바인딩(TOCTOU)은 못 막는다.
   완전 차단은 허용목록 전환뿐 — 고위험 배포는 BULLETIN_URL_ALLOWLIST를 쓸 것.
3) 스트리밍 수신 + 상한(기본 20MB) 초과 즉시 중단.
4) PDF 매직(%PDF) 확인.

반환은 (바이트 | None, 사유 | None, HTTP상태) — 실패 사유까지 들고 나온다.
422는 '네 URL이 나쁨', 502는 '가져오다 실패'다.

## ★ 적용 범위 감사(갭 #2, 2026-11-02) ★

임의 URL을 받는 진입점은 두 불리틴 엔드포인트뿐이고 둘 다 여기를 쓴다.
main.py에 requests 직접 호출은 없고, 수집기는 고정 URL만 본다(구성상 SSRF
불가). 새 엔드포인트에 URL 파라미터를 달면 여기를 거치게 할 것.
"""
from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlsplit

import requests

USER_AGENT = {"User-Agent": "Mozilla/5.0 (EpiWeather/1.0)"}

# 한 번에 받는 상한 — WHO 주간보고서 PDF는 수 MB라 20MB면 넉넉하다.
MAX_PDF_BYTES = 20 * 1024 * 1024
# 연결 10초·읽기 110초 — 예전 timeout=120과 총량은 같고, 붙는 데만 오래
# 걸리는 좀비 호스트는 10초에 끊는다.
CONNECT_TIMEOUT_SEC = 10
READ_TIMEOUT_SEC = 110

# 쉼표 구분 호스트 접미사. 비어 있으면 꺼짐(기본). 예: "who.int,afro.who.int"
ALLOWLIST_ENV = "BULLETIN_URL_ALLOWLIST"


def _allowlist() -> list[str]:
    raw = os.environ.get(ALLOWLIST_ENV, "")
    return [h.strip().lower().lstrip(".") for h in raw.split(",") if h.strip()]


def _is_global_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_global


def assert_fetchable_url(url: str) -> str:
    """URL이 내려받아도 되면 호스트명을, 안 되면 ValueError(사유 한글)를."""
    try:
        parts = urlsplit(url)
    except Exception:
        raise ValueError("URL 해석 불가")
    if parts.scheme.lower() not in ("http", "https"):
        raise ValueError("http(s) 주소만 허용")
    if parts.username or parts.password:
        raise ValueError("userinfo 포함 주소 거부")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("호스트 없음")
    port = parts.port
    if port is not None and port not in (80, 443):
        raise ValueError("80/443 외 포트 거부")

    allowed = _allowlist()
    if allowed and not any(host == a or host.endswith("." + a) for a in allowed):
        raise ValueError("허용목록 밖 호스트")

    # 리터럴 IP면 DNS 없이 바로 판정.
    try:
        ipaddress.ip_address(host)
        is_literal = True
    except ValueError:
        is_literal = False
    if is_literal:
        if not _is_global_ip(host):
            raise ValueError("사설·특수 대역 거부")
        return host

    # 호스트명 — 풀리는 주소가 하나라도 비공용이면 거부(fail-closed).
    try:
        infos = socket.getaddrinfo(host, port or 443, type=socket.SOCK_STREAM)
    except Exception:
        raise ValueError("DNS 해석 실패")
    ips = {info[4][0] for info in infos}
    if not ips:
        raise ValueError("DNS 해석 결과 없음")
    if not all(_is_global_ip(ip) for ip in ips):
        raise ValueError("사설·특수 대역으로 풀림")
    return host


def fetch_pdf_bytes_detailed(url: str, *, max_bytes: int = MAX_PDF_BYTES,
                             timeout: tuple[int, int] = (CONNECT_TIMEOUT_SEC,
                                                         READ_TIMEOUT_SEC)
                             ) -> tuple[bytes | None, str | None, int]:
    """(PDF 바이트 | None, 실패 사유 | None, HTTP 상태).
    422는 요청 URL 문제, 502는 내려받기 실패다."""
    try:
        assert_fetchable_url(url)
    except ValueError as e:
        return None, str(e), 422
    try:
        resp = requests.get(url, headers=USER_AGENT, timeout=timeout, stream=True)
        resp.raise_for_status()
        declared = resp.headers.get("Content-Length")
        if declared is not None:
            try:
                if int(declared) > max_bytes:
                    return None, f"선언 크기 초과({declared}B)", 422
            except (TypeError, ValueError):
                pass  # 이상한 선언값은 무시하고 실측으로 자른다
        chunks: list[bytes] = []
        total = 0
        for piece in resp.iter_content(chunk_size=65536):
            if not piece:
                continue
            total += len(piece)
            if total > max_bytes:
                return None, f"수신 크기 초과({max_bytes}B 상한)", 422
            chunks.append(piece)
    except Exception as e:
        return None, f"PDF 내려받기 실패: {e}", 502
    content = b"".join(chunks)
    if not content[:5].startswith(b"%PDF"):
        return None, "PDF 파일이 아님", 422
    return content, None, 200
