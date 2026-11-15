"""나라별 위험 카드 — 관측 층 융합·관측 강도(추정)·한국 연결·텔레그램 요약 (2026-11-15)."""
from __future__ import annotations

import ast
from pathlib import Path

from algorithms import country_cards as cc

MAIN = Path(__file__).resolve().parents[1] / "main.py"


def _inputs(**over):
    base = {
        "extracted": [
            {"disease": "에볼라", "location": "콩고민주공화국, 우간다", "country_iso3": "COD",
             "signal_type": "진행중", "source": "who", "extracted_at": "2026-11-14T21:00:00+00:00"},
            # 같은 질병·장소·출처 반복 → 1건으로
            {"disease": "에볼라", "location": "콩고민주공화국, 우간다", "country_iso3": "COD",
             "signal_type": "진행중", "source": "who", "extracted_at": "2026-11-13T21:00:00+00:00"},
            {"disease": "폐렴", "location": "어딘지 모름", "country_iso3": None, "source": "x"},
        ],
        "unexplained": {"alerts": [{"location": "러시아 이르쿠츠크", "source": "news", "signal_date": "2026-11-10"}]},
        "disaster": {"countries": [{"country_iso3": "IND", "open_windows": [{"title": "Red notification for cyclone"}]}]},
        "trade": {"top_surges": [{"country_iso3": "KAZ", "product": "masks_breathing", "surge_ratio": 2.2}]},
        "travel": {"all_notices": [{"level": 3, "headline": "Ebola Bundibugyo Virus Disease in Haut-Uélé Provinces of the Democratic Republic of the Congo"}]},
        "risk": {"countries": [{"country": "COD", "risk_score": 19.8, "dominant_disease": "에볼라", "lat": -4.4, "lng": 15.3}]},
        "korea": {"week": "2026-W46", "top_exposure": [{"country": "COD", "direct_routes_to_kor": 0, "kor_passengers": None}]},
    }
    base.update(over)
    return base


def test_fuses_layers_per_country_and_dedupes_repeats():
    r = cc.build_cards(**_inputs())
    by = {c["iso3"]: c for c in r["cards"]}
    cod = by["COD"]
    assert cod["counts"]["event"] == 1  # 반복 보도 1건
    assert cod["travel_level"] == 3
    assert cod["risk_score"] == 19.8 and cod["lat"] == -4.4
    assert cod["korea"] == {"routes": 0, "passengers": None}
    assert by["UGA"]["counts"]["event"] == 1  # 위치에서 함께 읽힌 나라
    assert by["RUS"]["counts"]["unexplained"] == 1
    assert by["IND"]["counts"]["disaster"] == 1
    assert by["KAZ"]["counts"]["trade"] == 1
    assert r["unlocated"] == 1  # 위치 못 읽은 폐렴은 카드에 안 넣고 센다
    assert r["korea_available"] is True and r["korea_week"] == "2026-W46"


def test_intensity_is_labelled_estimate_not_probability():
    r = cc.build_cards(**_inputs())
    assert r["weights_calibrated"] is False and r["is_probability"] is False
    assert "추정" in r["note"] and "확률" in r["note"]
    # 공식 그대로: 보도 1건 → 20·log2(2)=20, CDC L3 → 24 → 44
    cod = next(c for c in r["cards"] if c["iso3"] == "COD")
    assert cod["intensity"] == 44 and cod["grade"] == "elevated"
    assert r["cards"] == sorted(r["cards"], key=lambda c: -c["intensity"])


def test_intensity_caps_at_100_and_grades():
    assert cc.intensity_of({"event": 1000, "unexplained": 1000, "disaster": 10, "trade": 10}, 4) == 100
    assert cc.grade_of(60) == "high" and cc.grade_of(30) == "elevated" and cc.grade_of(29) == "watch"


def test_missing_korea_report_is_said_not_invented():
    r = cc.build_cards(**_inputs(korea=None))
    assert r["korea_available"] is False
    assert all(c["korea"] == {"routes": None, "passengers": None} for c in r["cards"])


def test_risk_index_does_not_create_cards_for_quiet_countries():
    r = cc.build_cards(**_inputs(risk={"countries": [{"country": "BRA", "risk_score": 50}]}))
    assert "BRA" not in {c["iso3"] for c in r["cards"]}


def test_telegram_text_escapes_and_states_estimate():
    r = cc.build_cards(**_inputs())
    r["cards"][0]["name"] = "<b>X</b>"
    text = cc.telegram_text(r, site_url="https://example.org")
    assert "&lt;b&gt;X&lt;/b&gt;" in text
    assert "발병 확률 아님" in text and "가중치 미보정" in text
    assert text.endswith("https://example.org/ko/observations")


def test_telegram_text_quiet_day():
    text = cc.telegram_text({"cards": []})
    assert "카드로 묶일 관측이 없음" in text


def test_weights_match_the_web():
    """웹(lib/countryCards.ts)과 백엔드가 같은 가중치를 써야 화면과 API·텔레그램 숫자가 같다."""
    ts = (Path(__file__).resolve().parents[2] / "epiweather-web/src/lib/countryCards.ts").read_text(encoding="utf-8")
    assert "INTENSITY_WEIGHTS = { event: 20, unexplained: 15, disaster: 15, trade: 10, travelPerLevel: 8 }" in ts
    assert cc.INTENSITY_WEIGHTS == {"event": 20, "unexplained": 15, "disaster": 15, "trade": 10, "travel_per_level": 8}
    assert "GRADE_HIGH = 60" in ts and "GRADE_ELEVATED = 30" in ts


def test_wiring_endpoint_daily_telegram_and_prewarm():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    names = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "response_cache.swr(f'country-cards:{lang}'" in ast.unparse(names["country_cards_endpoint"])
    daily = next(ast.unparse(n) for n in names.values() if "notify_daily_brief" in ast.unparse(n)
                 and isinstance(n, ast.AsyncFunctionDef))
    assert "notify_country_cards" in daily
    assert "_after_cycle_bg" in ast.unparse(names["_prewarm_after_cycle"])
    assert "_prewarm_heavy()" in ast.unparse(names["_after_cycle_bg"])
    assert "country-cards:ko" in ast.unparse(names["_prewarm_heavy"])
    assert "_prewarm_heavy()" in ast.unparse(names["_dashboard_warmup_bg"])  # 기동 직후에도


def test_endpoint_returns_cards(monkeypatch):
    from fastapi.testclient import TestClient

    import main

    monkeypatch.setattr(cc, "collect_inputs", lambda: _inputs())
    r = TestClient(main.app).get("/api/country-cards?lang=en&limit=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body["cards"]) == 2
    assert body["cards"][0]["name"]  # 영어 이름
    assert body["response_cache"]["stale"] is False
