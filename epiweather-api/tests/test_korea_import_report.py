"""대한민국 해외 유입 위험 주간 보고서 (2026-10-19, 캡틴 승인 ③).

배경: 기능은 많은데 기관이 손에 쥘 결과물이 없었다. 이상도 × 한국 직항 연결 + 이웃 나라
주간 추세 + 이번 주 경보를 ISO 주마다 한 장으로 묶는다. 이 시험은 정직성 경계선을 고정한다 —
지수는 확률이 아님, 신호 없는 나라는 순위에 넣지 않음, 직항 없는 고이상도 나라를 빠뜨리지 않음,
정규화 기준이 주마다 흔들리지 않음, 주당 1건.
"""
from __future__ import annotations

import ast
import datetime as dt
import pathlib

import pytest

from algorithms import korea_import_report as kr

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 19, 6, tzinfo=UTC)          # 2026-W43
COLLECTOR_PY = pathlib.Path(__file__).resolve().parents[1] / "collector.py"

ROUTES = {("CHN", "KOR"): 303, ("JPN", "KOR"): 213, ("KOR", "USA"): 78, ("KOR", "PHL"): 53,
          ("COD", "UGA"): 4}


def _c(cid, raw, name=None, disease=None, tier="medium"):
    return {"country": cid, "name": name or cid, "raw_score": raw, "tier": tier,
            "dominant_disease": disease, "dominant_disease_share": 0.6 if disease else None}


def _build(ranked, routes=ROUTES, alerts=(), weekly=(), err=None):
    return kr.build_report(list(ranked), routes, list(alerts), list(weekly), NOW, routes_error=err)


def test_countries_without_signal_are_not_ranked():
    # 취약성만으로 만든 기준선 점수를 위험처럼 보이게 하지 않는다.
    rep = _build([_c("CHN", None), _c("JPN", 40)])
    assert [r["country"] for r in rep["top_exposure"]] == ["JPN"]
    assert rep["summary"]["countries_with_signal"] == 1


def test_exposure_ranks_by_signal_times_connectivity_and_is_not_probability():
    rep = _build([_c("PHL", 90, disease="뎅기열"), _c("CHN", 30), _c("USA", 60)])
    # PHL 90×ln54/ln304 ≈ 62.8 · USA 60×ln79/ln304 ≈ 45.9 · CHN 30×1 = 30.0
    assert [(r["country"], r["exposure_index"]) for r in rep["top_exposure"]] == [
        ("PHL", 62.8), ("USA", 45.9), ("CHN", 30.0)]
    phl = rep["top_exposure"][0]
    assert phl["direct_routes_to_kor"] == 53 and phl["dominant_disease"] == "뎅기열"
    assert phl["exposure_index"] < phl["raw_score"]          # 연결이 최대가 아니면 줄어든다
    assert rep["is_probability"] is False
    assert any("확률이 아님" in c for c in rep["caveats"])


def test_normalisation_is_stable_regardless_of_who_is_ranked():
    """정규화 기준을 '순위에 든 나라 중 최대'로 잡으면 중국이 빠진 주에 일본 지수가 말없이
    커진다. 한국 노선 전체 최대(303)로 고정한다."""
    with_chn = _build([_c("CHN", 50), _c("JPN", 50)])
    without_chn = _build([_c("JPN", 50)])
    jpn = lambda rep: next(r for r in rep["top_exposure"] if r["country"] == "JPN")["exposure_index"]
    assert jpn(with_chn) == jpn(without_chn) < 50


def test_high_signal_country_without_direct_route_is_listed_separately():
    rep = _build([_c("COD", 85, disease="에볼라"), _c("UGA", 40)])
    assert rep["top_exposure"] == []
    assert [r["country"] for r in rep["no_direct_route_high"]] == ["COD"]   # UGA 는 문턱 미만


def test_korea_itself_goes_to_domestic_not_import_ranking():
    rep = _build([_c("KOR", 72, disease="레지오넬라증"), _c("JPN", 40)])
    assert rep["domestic"]["raw_score"] == 72
    assert all(r["country"] != "KOR" for r in rep["top_exposure"])


def test_suppressed_alerts_are_not_reported_as_active():
    alerts = [{"tier": "medium", "label": "하수 농도", "score": 79, "suppressed": 0},
              {"tier": "low", "label": "내려간 경보", "score": 40, "suppressed": 1}]
    rep = _build([], alerts=alerts)
    assert [a["label"] for a in rep["alerts"]] == ["하수 농도"]


def _wf(i, series, tw, p, outcome=None):
    return {"id": i, "series": series, "base_year": 2026, "base_week": tw - 1, "base_value": 1000.0,
            "target_year": 2026, "target_week": tw, "prob_up": p, "outcome": outcome}


def test_neighbor_trends_show_latest_forecast_and_last_scored_one():
    weekly = [_wf(1, "jp_influenza", 41, 0.6, "up"), _wf(2, "jp_influenza", 42, 0.7),
              _wf(3, "jp_covid", 42, 0.4)]
    rep = _build([], weekly=weekly)
    flu = next(t for t in rep["neighbor_trends"] if t["series"] == "jp_influenza")
    assert flu["target_week"] == "2026-W42" and flu["prob_up"] == 0.7
    assert flu["last_scored"] == {"target_week": "2026-W41", "prob_up": 0.6, "outcome": "up"}
    covid = next(t for t in rep["neighbor_trends"] if t["series"] == "jp_covid")
    assert covid["last_scored"] is None


def test_markdown_has_all_sections_and_handles_empty_report():
    md = kr.to_markdown(_build([]))
    for heading in ("유입 노출 상위 국가", "직항 없는 고이상도", "이웃 나라 주간 추세", "활성 경보", "고지"):
        assert heading in md
    assert "이상 신호 국가 없음" in md and "확률이 아님" in md


def test_markdown_warns_when_route_cache_is_missing():
    md = kr.to_markdown(_build([_c("JPN", 50)], routes={}, err="항공 노선 캐시가 없다."))
    assert "노출 지수 산출 불가" in md


def test_generate_once_per_iso_week(isolated_db, monkeypatch):
    from algorithms import country_risk, digital_twin
    monkeypatch.setattr(country_risk, "rank_countries",
                        lambda: {"countries": [_c("PHL", 80, disease="뎅기열")]})
    monkeypatch.setattr(digital_twin, "load_flight_routes", lambda: (ROUTES, None))
    first = kr.generate_if_due(NOW)
    assert first["week"] == "2026-W43" and first["top_exposure"][0]["country"] == "PHL"
    assert kr.generate_if_due(NOW + dt.timedelta(days=3)) is None            # 같은 주
    nxt = kr.generate_if_due(NOW + dt.timedelta(days=7))
    assert nxt["week"] == "2026-W44"
    assert kr.list_weeks() == ["2026-W44", "2026-W43"]
    assert kr.get_report("2026-W43")["generated_at"] == first["generated_at"]   # 지우지 않는다


def test_api_returns_404_without_report_and_markdown_with_one(isolated_db, monkeypatch):
    import main
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        main.korea_import_report()
    assert exc.value.status_code == 404
    kr.save_report(_build([_c("JPN", 50)]))
    body = main.korea_import_report(format="md").body.decode("utf-8")
    assert body.startswith("# 대한민국 해외 유입 위험 주간 보고서 — 2026-W43")
    assert main.korea_import_report()["available_weeks"] == ["2026-W43"]


def test_collector_cycle_generates_report_and_logs_its_line():
    """만들어만 두고 아무도 안 부르는 층이 되지 않게 배선을 AST 로 고정한다."""
    tree = ast.parse(COLLECTOR_PY.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "collect_free_sources")
    assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id == "generate_if_due" for n in ast.walk(fn))
    assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "log"
               and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                       and c.func.id == "report_line" for a in n.args for c in ast.walk(a))
               for n in ast.walk(fn))


def test_report_names_are_korean_not_mixed_with_english():
    """2026-W43 첫 운영 보고서가 '일본(62.8), Russian Federation(25.3), Cambodia(14.9)' 로
    한글·영문을 섞어 썼다(Tier-2 국가는 영문 캐시 이름). 표시명은 한글로 통일한다."""
    ranked = [_c("JPN", 66, name="일본"), _c("RUS", 40, name="Russian Federation"),
              _c("KHM", 30, name="Cambodia")]
    routes = {**ROUTES, ("KHM", "KOR"): 6, ("KOR", "RUS"): 27}
    rep = _build(ranked, routes=routes)
    assert [r["name"] for r in rep["top_exposure"]] == ["일본", "러시아", "캄보디아"]
    assert "Russian Federation" not in kr.report_line(rep)


def test_name_not_in_korean_table_falls_back_to_original_not_invented():
    rep = _build([_c("PHL", 60, name="Philippines"), _c("XXA", 90, name="Atlantis")],
                 routes={**ROUTES, ("KOR", "XXA"): 5})
    names = {r["country"]: r["name"] for r in rep["top_exposure"]}
    assert names == {"PHL": "필리핀", "XXA": "Atlantis"}


def test_korean_name_uses_canonical_first_spelling():
    from algorithms.country_resolve import korean_name
    assert korean_name("KOR") == "대한민국"          # '한국' 이 아니라 표준형
    assert korean_name("TUR") == "튀르키예"           # '터키' 가 아니라 표준형
    assert korean_name("COD") == "콩고민주공화국"
    assert korean_name("ZZZ") is None and korean_name(None) is None


# ── 텔레그램 발송 (2026-10-19 — 만들어만 두고 받는 사람이 없던 결과물) ─────────

def test_telegram_text_summarises_with_caveat_and_link():
    rep = _build([_c("PHL", 90, disease="뎅기열"), _c("COD", 85), _c("XXA", 80, name="<b>A&B</b>")],
                 routes={**ROUTES, ("KOR", "XXA"): 5})
    text = kr.telegram_text(rep, site_url="https://example.test/")
    assert text.startswith("🇰🇷 <b>대한민국 해외 유입 위험 주간 보고서 2026-W43</b>")
    assert "노출 상위: 필리핀 62.8" in text
    assert "직항 없는 고이상도: 콩고민주공화국" in text
    assert "확률이 아님" in text and "https://example.test/ko/record" in text
    assert "<b>A&B</b>" not in text and "&lt;b&gt;A&amp;B&lt;/b&gt;" in text, "값은 이스케이프"


def test_notify_states(monkeypatch):
    from algorithms import notifier
    rep = _build([_c("JPN", 50)])
    sent = []
    monkeypatch.setattr(notifier, "telegram_configured", lambda: True)
    monkeypatch.setattr(notifier, "send_telegram_message", lambda t: sent.append(t) or True)
    assert kr.notify_new_report(rep) == "전송됨" and len(sent) == 1
    monkeypatch.setattr(notifier, "send_telegram_message", lambda t: False)
    assert kr.notify_new_report(rep).startswith("전송 실패(재시도 없음")
    monkeypatch.setenv("EPIWEATHER_WEEKLY_REPORT_NOTIFY", "off")
    assert kr.notify_new_report(rep) == "꺼 둠"
    monkeypatch.delenv("EPIWEATHER_WEEKLY_REPORT_NOTIFY")
    monkeypatch.setattr(notifier, "telegram_configured", lambda: False)
    assert kr.notify_new_report(rep) == "채널 미설정"


def test_collector_sends_only_when_a_new_report_was_made():
    """generate_if_due 가 None(이번 주 이미 있음)이면 보내지 않는다 — 같은 if 블록 안에 있어야 한다."""
    tree = ast.parse(COLLECTOR_PY.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "collect_free_sources")
    ifs = [n for n in ast.walk(fn) if isinstance(n, ast.If)
           and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "report_line"
                   for c in ast.walk(n))]
    assert ifs and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                       and c.func.id == "notify_new_report" for c in ast.walk(ifs[0]))
