"""매시 수집 한 주기 전체 — 극지 → 헤임달 → 발할라 → 소스 건강 (2026-11-22 개편 2차).

개편 뒤 collector.py 는 세 층만 돈다. 층마다 따로 떼어 시험은 있었지만 **한 주기를 끝까지
돌리는** 시험이 없었다(커버리지 22%). 고정하는 것:
① 세 층이 다 성공하면 결과 키 셋이 채워지고 소스 건강이 3/3 으로 기록된다.
② 한 층이 터져도 나머지 층은 돈다 — 터진 층만 None(판정 안 함)이 되고 실패로 세어진다.
③ 극지 8곳 모두 기상 자료가 없으면 자료를 None 으로 두고 그 사실을 로그에 남긴다.
외부 호출은 전부 스텁이다(conftest 가 실제 HTTP 를 막는다).
"""
from __future__ import annotations

import json

import pytest

import collector
from algorithms import source_health


def _region(ok: bool) -> dict:
    return {"region": "greenland", "name": "그린란드", "polar_watch_score": 40.0 if ok else None,
            "thaw": {"data_available": ok}, "news": {"signal": None}}


def _polar(ok: bool = True) -> dict:
    return {"regions": [_region(ok), dict(_region(ok), region="svalbard", name="스발바르")],
            "grade": "watch"}


GENOMES = {"ncov_open_global_6m": {"available": True, "label": "SARS-CoV-2", "dominant_clade": "25C",
                                   "dominant_share": 0.56, "n_recent_sequences": 1275}}
VALHALLA = {"readiness": {"countermeasure_count": 5}, "vaccine_chokepoints": {"single_source_count": 17},
            "pipeline": {"value": None, "refreshed": False, "age_hours": 1.0, "reason": "갱신 주기 전"}}


@pytest.fixture
def cycle(tmp_path, monkeypatch, isolated_db):
    monkeypatch.setattr(collector, "DATA_DIR", tmp_path)
    monkeypatch.setattr(collector, "LOG_FILE", tmp_path / "signals_log.jsonl")
    monkeypatch.setattr(collector, "ERR_FILE", tmp_path / "error_log.txt")
    monkeypatch.setattr(source_health, "HEALTH_FILE", tmp_path / "source_health.json")
    import algorithms.genomic_variants as gv
    import algorithms.polar_signals as ps
    import algorithms.valhalla_watch as vw
    monkeypatch.setattr(ps, "polar_watch_all", lambda: _polar(True))
    monkeypatch.setattr(gv, "get_genomic_variant_signals", lambda: GENOMES)
    monkeypatch.setattr(vw, "valhalla_snapshot", lambda: VALHALLA)
    lines: list[str] = []
    monkeypatch.setattr(collector, "log", lines.append)
    return {"lines": lines, "ps": ps, "gv": gv, "vw": vw, "tmp": tmp_path}


def _health(tmp) -> dict:
    return json.loads((tmp / "source_health.json").read_text(encoding="utf-8"))


def test_full_cycle_fills_all_three_layers_and_health(cycle):
    result = collector.collect_free_sources()

    assert result["polar_watch"]["grade"] == "watch"
    assert result["genomic_variants"] is GENOMES
    assert result["valhalla"] is VALHALLA
    health = _health(cycle["tmp"])
    assert set(health) == {"PolarWatch", "GenomicVariants", "Valhalla"}
    assert all(e.get("consecutive_failures", 0) == 0 for e in health.values())
    text = "\n".join(cycle["lines"])
    assert "Nextstrain SARS-CoV-2: 우세계통 25C(56%, n=1275)" in text
    assert "📊 소스 건강: 정상 3/3" in text
    assert (cycle["tmp"] / "signals_log.jsonl").exists()


def test_one_layer_crashing_does_not_stop_the_others(cycle, monkeypatch):
    def boom():
        raise ConnectionError("Nextstrain down")
    monkeypatch.setattr(cycle["gv"], "get_genomic_variant_signals", boom)

    result = collector.collect_free_sources()

    assert result["genomic_variants"] is None                 # 판정 안 함 — 0 이 아니다
    assert result["polar_watch"] is not None and result["valhalla"] is VALHALLA
    health = _health(cycle["tmp"])
    assert health["GenomicVariants"]["consecutive_failures"] == 1
    assert health["PolarWatch"].get("consecutive_failures", 0) == 0


def test_no_weather_anywhere_drops_polar_data_and_says_so(cycle, monkeypatch):
    monkeypatch.setattr(cycle["ps"], "polar_watch_all", lambda: _polar(False))

    result = collector.collect_free_sources()

    assert result["polar_watch"] is None
    assert any("모든 관측지 기상 자료 없음" in line for line in cycle["lines"])
    assert _health(cycle["tmp"])["PolarWatch"]["consecutive_failures"] == 1


def test_old_sources_in_the_health_file_are_pruned(cycle):
    (cycle["tmp"] / "source_health.json").write_text(
        json.dumps({"KDCA": {"consecutive_failures": 90}}), encoding="utf-8")

    collector.collect_free_sources()

    assert "KDCA" not in _health(cycle["tmp"])
