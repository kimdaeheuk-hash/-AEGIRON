"""사용자 정의 관심 영역 — Phase 3. 기업 고객 맞춤 필터 프로파일.

인수인계서:
  대한항공: "동남아·중동 노선 위험도만"
  보험사:   "전세계 여행 위험도"
  학교:     "호흡기 질환만"
  군부대:   "전염성 강한 질환만"

프로파일별로 관심 지역, 질병 유형, 알림 임계값을 다르게 설정.
GET /api/profile/{profile_id}/risk 로 맞춤 위험도 반환.
"""
from __future__ import annotations
from typing import Any

PROFILES: dict[str, dict] = {
    "airline": {
        "name":         "항공사",
        "example":      "대한항공·아시아나",
        "regions":      ["동남아", "중동", "아프리카"],
        "disease_types":["respiratory", "hemorrhagic", "novel"],
        "alert_threshold": 65,
        "key_metrics":  ["mobility_total_flights", "wiki_ebola_daily", "cidrap_mers", "cidrap_avian_flu"],
        "description":  "운항 노선 위험도. 항공편 감소·발병지 확산 징후 감지.",
    },
    "insurance": {
        "name":         "여행 보험사",
        "example":      "삼성화재·현대해상",
        "regions":      ["전세계"],
        "disease_types":["all"],
        "alert_threshold": 60,
        "key_metrics":  ["wiki_ebola_daily", "wiki_flu_daily", "cidrap_mers", "cidrap_avian_flu",
                         "naver_ebola_ratio", "mobility_total_flights"],
        "description":  "전세계 여행 위험도. 보험료 조정 기준으로 활용.",
    },
    "school": {
        "name":         "학교·교육기관",
        "example":      "교육청·대학교",
        "regions":      ["국내", "동아시아"],
        "disease_types":["respiratory"],
        "alert_threshold": 70,
        "key_metrics":  ["naver_flu_ratio", "wiki_flu_daily", "cidrap_mers", "japan_idwr_total",
                         "hk_chp_total", "supply_alert_count"],
        "description":  "호흡기 질환 집중 감시. 휴교 결정 지원.",
    },
    "military": {
        "name":         "군·방위산업",
        "example":      "국방부·방위사업청",
        "regions":      ["전세계"],
        "disease_types":["high_transmission", "hemorrhagic", "novel"],
        "alert_threshold": 55,
        "key_metrics":  ["wiki_ebola_daily", "cidrap_avian_flu", "cidrap_ebola",
                         "local_news_kw_hits", "medrxiv_epi_papers", "wahis_watch_hits"],
        "description":  "전파력 강한 질환 집중. 부대 방역 의사결정 지원.",
    },
    "hospital": {
        "name":         "병원·의료기관",
        "example":      "서울대병원·빅5",
        "regions":      ["국내", "전세계"],
        "disease_types":["all"],
        "alert_threshold": 60,
        "key_metrics":  ["kdca_weekly_total", "naver_flu_ratio", "supply_alert_count",
                         "wiki_ebola_daily", "cidrap_mers", "japan_idwr_total"],
        "description":  "원내 감염 예방 + 응급실 과부하 예측. 선제 격리 지원.",
    },
    "kdca": {
        "name":         "질병관리청 (KDCA)",
        "example":      "질병청·복지부",
        "regions":      ["전세계", "국내"],
        "disease_types":["all"],
        "alert_threshold": 50,
        "key_metrics":  ["all"],
        "description":  "전체 신호 무제한 접근. WHO보다 3~14일 먼저 감지가 목표.",
    },
}


def get_profile(profile_id: str) -> dict | None:
    return PROFILES.get(profile_id)


def filter_risk_for_profile(profile_id: str, anomalies: list[dict], forecast: dict) -> dict:
    """
    이상 탐지 결과 + 예측을 프로파일 필터로 걸러서 맞춤 위험 요약 반환.
    """
    profile = PROFILES.get(profile_id)
    if not profile:
        return {"error": f"프로파일 없음. 지원: {list(PROFILES)}"}

    key_metrics = set(profile["key_metrics"])
    threshold   = profile["alert_threshold"]

    if "all" in key_metrics:
        filtered_anomalies = anomalies
    else:
        filtered_anomalies = [a for a in anomalies if a["metric"] in key_metrics]

    high_risk = [a for a in filtered_anomalies if a["anomaly_score"] >= threshold]
    avg_score = (
        sum(a["anomaly_score"] for a in filtered_anomalies) / len(filtered_anomalies)
        if filtered_anomalies else 0.0
    )

    # 예측 필터링
    forecast_alerts = [
        f for f in forecast.get("top_alerts", [])
        if "all" in key_metrics or f["metric"] in key_metrics
    ]

    return {
        "profile_id":      profile_id,
        "profile_name":    profile["name"],
        "description":     profile["description"],
        "alert_threshold": threshold,
        "current_risk_score": round(avg_score, 1),
        "high_risk_signals":  len(high_risk),
        "high_risk_items":    high_risk[:5],
        "forecast_7d_alerts": forecast_alerts[:5],
        "regions":         profile["regions"],
    }
