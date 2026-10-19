"""WOAH 동물질병 신호 — Phase 2 ⑯ (2026-10-19 부터 RSS 만).

세계동물보건기구(WOAH) 공식 RSS 의 최신 항목 수를 읽는다. 신종 감염병의 다수가
동물에서 시작하므로 동물 쪽 공식 채널을 하나는 보고 있어야 한다.

★ WAHIS API 는 은퇴했다 (2026-10-19 캡틴 결정: "RSS만 써라") ★
예전엔 WAHIS API(`/api/v1/reports/immediate`)로 30일 발병 목록을 받으려 했다.
그런데 키(WAHIS_API_KEY)가 설정된 적이 없었고, 호출은 실패했는데 실패가 조용히
'30일 발병 0건'으로 기록됐다(#94 에서 고침). 고친 뒤 운영 로그가 처음으로 실제 사유를
보여 줬다 — `HTTP 400, 키 없음`. 400 은 인증 문제가 아니라 요청 형식 문제라, 키를 받아도
바로 살아난다는 보장이 없었다. 그래서 API 호출을 걷어 내고 RSS 만 쓴다.

그 결과 outbreaks_30d·watch_hits 는 **늘 None(판정 안 함)** 이다. 키는 하위 호환으로
남긴다 — 지표 추출기(signal_metrics)와 부정적 공간은 None 을 '값 없음'으로 다루므로
지수에도 판정에도 들어가지 않는다. 0 으로 바꿔 넣지 않는다.

RSS 를 못 읽으면 woah_rss_items 가 None 이고 사유가 rss_reason 에 남는다. 수집기는 그때
이 소스를 실패로 기록한다(소스 건강) — RSS 가 이 소스의 전부이기 때문이다.
"""
from __future__ import annotations

import requests

from .common import brief_reason

USER_AGENT = {"User-Agent": "EpiWeather-WAHIS/1.0 (epiweather.kr)"}
TIMEOUT = 20

# WOAH 공개 RSS — 계정 없이 사용 가능 (공식 발병 보고 요약).
# "/en/home/feed/"는 항상 403(WordPress comments-closed 오류)이라 죽어있던
# URL — 실제 유효한 경로는 "/en/feed/"(실측 확인, 200·항목 10개).
WOAH_RSS_URL = "https://www.woah.org/en/feed/"

API_RETIRED_NOTE = ("WAHIS API 은퇴(2026-10-19 캡틴 결정) — 키 없이 HTTP 400, "
                    "WOAH RSS 만 사용 · 30일 발병 건수는 판정 안 함")


def fetch_woah_rss_count() -> tuple[int | None, str | None]:
    """WOAH 공식 RSS 최신 항목 수. 반환: (항목 수, 못 읽은 사유).

    예전엔 실패를 None 하나로만 돌려줘 왜 실패했는지가 사라졌다 — 사유를 함께 준다."""
    try:
        resp = requests.get(WOAH_RSS_URL, headers=USER_AGENT, timeout=TIMEOUT)
    except Exception as e:
        return None, brief_reason(e)
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}"
    if "<rss" not in resp.text and "<feed" not in resp.text:
        # 200 인데 RSS 가 아닌 페이지(차단·점검 안내 등)를 '항목 0건'으로 읽지 않는다.
        return None, "RSS 형식 아님"
    return resp.text.count("<item>"), None


def get_animal_signal() -> dict:
    """동물신호 층 요약값.

    - woah_rss_items: WOAH RSS 최신 항목 수 — 못 읽었으면 None
    - rss_reason: 못 읽은 사유(읽었으면 None)
    - outbreaks_30d · watch_hits: WAHIS API 은퇴로 늘 None(판정 안 함) — 하위 호환 키
    """
    count, reason = fetch_woah_rss_count()
    return {
        "woah_rss_items": count,
        "rss_reason": reason,
        "outbreaks_30d": None,
        "watch_hits": None,
        "api_status": "retired",
        "api_note": API_RETIRED_NOTE,
        "outbreaks": [],
    }
