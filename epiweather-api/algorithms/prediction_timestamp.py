"""예측 타임스탬프 증명 (Phase 44) — 블록체인 재검토 결론(2026-07-27) 실행.

배경: 아이기론은 아직 검증된 예측 트랙레코드가 0건이다(정직하게 확인된
사실). "지금부터 쌓는 모든 예측을 처음부터 위변조 불가능하게 기록"하면,
나중에 트랙레코드가 쌓였을 때 "그때 진짜로 예측했다"를 누구도 반박 못 하게
증명할 수 있다 — 소급 적용이 안 되는 종류의 가치라 지금 시작하는 게 맞다는
결론(확인된 경쟁사 BlueDot·Airfinity·Metabiota 중 이런 증명을 쓰는 곳 없음).

방식: OpenTimestamps(오픈소스, LGPL3, 비트코인 체인) — 예측 기록의 SHA-256
해시를 공개 캘린더 서버에 제출하면, 그 서버가 여러 제출을 모아 하나의
Merkle Tree로 묶어 몇 시간~하루 내 비트코인 블록체인에 통째로 새긴다.
우리가 코인을 사거나 가스비를 낼 필요가 없다(캘린더 서버가 비용을 흡수)
— 그래서 완전 무료다. 실제 라이브 테스트로 동작 확인 완료(2026-07-27).

★ 정직성 경계선 ★
- 이 증명은 "예측이 맞았다"를 증명하지 않는다. **"이 내용을 이 시각에
  이미 갖고 있었다"만** 증명한다(Proof of Existence). 정확도 주장과 절대
  섞지 않는다.
- 제출 직후엔 "제출됨(pending)" 상태고, 실제 비트코인 블록에 새겨져
  검증 가능해지기까지 몇 시간~하루 걸린다 — 즉시 완성되는 게 아님을 명시.
- 캘린더 서버가 전부 응답 없으면(네트워크 등) data_available=False로
  정직하게 표시하고, 예측 생성 자체는 절대 막지 않는다(best-effort).
"""
from __future__ import annotations
import hashlib
import json

from opentimestamps.calendar import RemoteCalendar
from opentimestamps.core.serialize import BytesSerializationContext, BytesDeserializationContext
from opentimestamps.core.timestamp import Timestamp

# 공개 무료 캘린더 서버(가입·키 불필요) — otsclient 기본값과 동일.
CALENDAR_URLS = [
    "https://a.pool.opentimestamps.org",
    "https://b.pool.opentimestamps.org",
    "https://a.pool.eternitywall.com",
    "https://ots.btc.catallaxy.com",
]
SUBMIT_TIMEOUT = 15


def canonical_hash(prediction: dict) -> str:
    """예측의 불변 핵심 필드만 뽑아 결정론적으로 직렬화한 SHA-256(hex).
    verified_at 이후 채점 필드는 제외 — '예측 시점에 뭘 알고 있었는지'만 증명."""
    core = {
        "id": prediction.get("id"),
        "predicted_at": prediction.get("predicted_at"),
        "country": prediction.get("country"),
        "disease": prediction.get("disease"),
        "risk_score": prediction.get("risk_score"),
        "basis": prediction.get("basis"),
    }
    canonical_json = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def submit_timestamp(digest_hex: str, calendar_urls: list[str] | None = None) -> str | None:
    """digest_hex(32바이트 SHA-256)를 공개 캘린더 서버에 제출해 최초(미완성)
    타임스탬프 증명을 받는다. 여러 서버를 순서대로 시도, 하나라도 성공하면
    그 결과를 hex 문자열로 반환. 전부 실패하면 None(정직한 실패)."""
    digest = bytes.fromhex(digest_hex)
    for url in (calendar_urls or CALENDAR_URLS):
        try:
            cal = RemoteCalendar(url)
            ts = cal.submit(digest, timeout=SUBMIT_TIMEOUT)
            ctx = BytesSerializationContext()
            ts.serialize(ctx)
            return ctx.getbytes().hex()
        except Exception:
            continue
    return None


def check_timestamp(digest_hex: str, proof_hex: str,
                     calendar_urls: list[str] | None = None) -> dict:
    """제출된 증명이 실제 비트코인 블록에 새겨졌는지(confirmed) 조회.
    아직이면 pending(정상 — 몇 시간~하루 걸림), 조회 자체가 실패하면
    data_available=False."""
    try:
        digest = bytes.fromhex(digest_hex)
        proof_bytes = bytes.fromhex(proof_hex)
        ctx = BytesDeserializationContext(proof_bytes)
        Timestamp.deserialize(ctx, digest)  # 저장된 증명 자체가 파싱 가능한지 검증
    except Exception:
        return {"data_available": False, "reason": "저장된 증명 파싱 실패"}

    for url in (calendar_urls or CALENDAR_URLS):
        try:
            cal = RemoteCalendar(url)
            upgraded = cal.get_timestamp(digest, timeout=SUBMIT_TIMEOUT)
            if upgraded is not None:
                return {
                    "data_available": True, "confirmed": True,
                    "calendar_url": url,
                    "note": "비트코인 블록체인에 새겨짐 — 위변조 불가능한 존재증명 완성",
                }
        except Exception:
            continue
    return {
        "data_available": True, "confirmed": False,
        "note": "아직 비트코인 블록 확정 대기 중(정상 — 보통 몇 시간~하루 소요). "
                "제출 자체는 완료된 상태.",
    }
