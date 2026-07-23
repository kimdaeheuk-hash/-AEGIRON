"""외부 벤치마크 기준선 — 인수인계서 확장(㉕, BlueDot 대비 비교).

TIPS·투자 심사에서 "블루닷보다 빠르다"를 주장하려면, 같은 과거 발병에 대해
블루닷이 실제로 며칠 앞섰는지를 근거와 함께 제시하고 아이기론의 실측
선행일수(historical_backtest.py ㉑)와 나란히 놓아야 설득력이 생긴다.

★ 정직성 경계선(가장 중요) ★
1) 아래 BLUEDOT_RECORDS의 날짜·선행일수는 전부 공개 문헌에서 인용한 값이며
   출처 URL을 함께 저장한다 — 지어낸 숫자가 아니다.
2) 아이기론은 2019년 코로나 초기에 실제로 존재하지 않았다. 따라서 코로나
   사건에 대해 "아이기론이 블루닷을 이겼다"고 절대 주장하지 않는다.
   historical_backtest는 그 시점 extracted_signals가 없으므로 정직하게
   "aegiron_lead_days=None(당시 시스템 부재로 데이터 없음)"으로 보고하고,
   이 모듈은 '블루닷이 세운 기준(넘어야 할 목표선)'을 명시할 뿐이다.
3) 실제 head-to-head 숫자는 아이기론이 실제로 신호를 수집한 이후의 발병에서만
   나온다 — 그 전까지는 "목표 기준선 대비 아직 실측 없음"으로 표기한다.
"""
from __future__ import annotations

# 공개 문헌 인용. lead_days_vs_official = 공식 인지시점(주로 WHO 공개성명)보다
# 블루닷이 앞선 일수. 출처를 반드시 함께 남긴다(검증 가능성).
BLUEDOT_RECORDS = {
    "covid19_wuhan_2019": {
        "event_name": "COVID-19 우한 초기 클러스터",
        "bluedot_alert_date": "2019-12-31",
        "official_reference_date": "2020-01-09",   # WHO 신종코로나 첫 공개성명
        "official_reference_label": "WHO 신종 코로나바이러스 첫 공개 성명",
        "lead_days_vs_official": 9,
        "also_ahead_of": "미국 CDC 대비 6일 선행(CDC 경보 2020-01-06)",
        "sources": [
            "https://www.cbsnews.com/news/coronavirus-outbreak-computer-algorithm-artificial-intelligence/",
            "https://diginomica.com/how-canadian-ai-start-bluedot-spotted-coronavirus-anyone-else-had-clue",
        ],
        "citation_note": "블루닷은 2019-12-31 우한의 '비정상 폐렴' 클러스터를 고객에게 경보 — "
                         "WHO 공개 성명(2020-01-09)보다 9일, 미 CDC보다 6일 앞선 것으로 공개 보도됨.",
    },
}

# 아이기론 outbreak_timeline의 event_id ↔ 위 벤치마크 레코드 키 매핑.
# (코로나 시드 event_id는 main.py._seed_known_timelines에 추가됨 ㉕)
EVENT_TO_BENCHMARK = {
    "covid19_wuhan_2019": "covid19_wuhan_2019",
}


def bluedot_record_for(event_id: str) -> dict | None:
    key = EVENT_TO_BENCHMARK.get(event_id)
    if key is None:
        return None
    return BLUEDOT_RECORDS.get(key)


def compare_to_bluedot(event_id: str, aegiron_lead_days: int | None) -> dict | None:
    """아이기론 실측 선행일수 vs 블루닷 인용 선행일수. 벤치마크가 없는 이벤트는 None.
    aegiron_lead_days가 None이면(그 시점 데이터 없음) 정직하게 '실측 없음'으로 표기."""
    rec = bluedot_record_for(event_id)
    if rec is None:
        return None

    bluedot_lead = rec["lead_days_vs_official"]
    if aegiron_lead_days is None:
        verdict = "아이기론 실측 없음(해당 시점 신호 데이터 부재) — 블루닷이 세운 목표 기준선만 표기"
        delta = None
    else:
        delta = aegiron_lead_days - bluedot_lead
        if delta > 0:
            verdict = f"아이기론이 블루닷보다 {delta}일 더 빠름(실측)"
        elif delta == 0:
            verdict = "아이기론과 블루닷 선행일수 동일(실측)"
        else:
            verdict = f"블루닷이 아이기론보다 {-delta}일 빠름(실측)"

    return {
        "event_id": event_id,
        "event_name": rec["event_name"],
        "bluedot_lead_days": bluedot_lead,
        "bluedot_alert_date": rec["bluedot_alert_date"],
        "official_reference_date": rec["official_reference_date"],
        "official_reference_label": rec["official_reference_label"],
        "aegiron_lead_days": aegiron_lead_days,
        "difference_days": delta,   # 양수 = 아이기론이 더 빠름
        "verdict": verdict,
        "bluedot_sources": rec["sources"],
        "citation_note": rec["citation_note"],
    }
