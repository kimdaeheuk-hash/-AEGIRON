"""자동 예측 봉인 — 매시 수집 주기가 미봉인 예측을 따라잡는다 (2026-10-18).

배경(사고): 존재증명 봉인은 수동 API(POST /api/predictions)에만 붙어 있었다. 운영에서
예측을 실제로 만드는 것은 매시 주기의 country_risk 자동 기록인데, 그 경로는
db.create_prediction 을 바로 불러 봉인을 건너뛰었다. 2026-10-18 운영 스냅숏에서 예측
36건 중 content_hash·ots_proof_hex 가 채워진 건이 **0건**이었다 — 사이트는 "모든 예측을
봉인한다"고 적고 있었다. (boundary-audit 계열 2: 만들어만 두고 아무도 안 부른다)
"""
from __future__ import annotations

import ast
from pathlib import Path

from algorithms import prediction_timestamp as pt

ROOT = Path(__file__).resolve().parents[1]


def _make(db, n: int) -> list[dict]:
    return [
        db.create_prediction(f"Country{i}", "콜레라", 40.0 + i, [f"근거 {i}"])
        for i in range(n)
    ]


def test_auto_created_predictions_start_unsealed(isolated_db):
    """사고 재현: 자동 경로(db.create_prediction 직접 호출)는 봉인 필드를 비워 둔다."""
    preds = _make(isolated_db, 3)
    assert all(p["ots_proof_hex"] is None and p["content_hash"] is None for p in preds)
    assert isolated_db.count_unsealed_predictions() == 3


def test_sweep_seals_every_unsealed_prediction_with_its_canonical_hash(isolated_db, monkeypatch):
    preds = _make(isolated_db, 3)
    submitted: list[str] = []
    monkeypatch.setattr(pt, "submit_timestamp", lambda digest: submitted.append(digest) or "ab12")

    result = pt.seal_pending_predictions()

    assert result == {"sealed": 3, "failed": 0, "remaining": 0}
    for p in preds:
        stored = isolated_db.get_prediction(p["id"])
        # 해시는 예측 시점의 불변 필드로 계산한 그 값이어야 한다 — 봉인이 늦어도 내용 증명은 같다.
        assert stored["content_hash"] == pt.canonical_hash(p)
        assert stored["ots_proof_hex"] == "ab12"
        assert stored["ots_submitted_at"]
    assert submitted == [pt.canonical_hash(p) for p in preds]  # 오래된 순


def test_sealed_predictions_are_not_submitted_again(isolated_db, monkeypatch):
    _make(isolated_db, 2)
    monkeypatch.setattr(pt, "submit_timestamp", lambda digest: "ab12")
    pt.seal_pending_predictions()

    calls: list[str] = []
    monkeypatch.setattr(pt, "submit_timestamp", lambda digest: calls.append(digest) or "cd34")
    result = pt.seal_pending_predictions()

    assert calls == []
    assert result == {"sealed": 0, "failed": 0, "remaining": 0}


def test_sweep_stops_at_first_failure_and_writes_nothing(isolated_db, monkeypatch):
    """캘린더 서버가 전부 무응답이면 첫 건에서 멈춘다 — 건마다 기다리면 수집 주기가 밀린다.
    실패한 건은 봉인된 것처럼 적지 않는다."""
    _make(isolated_db, 3)
    calls: list[str] = []
    monkeypatch.setattr(pt, "submit_timestamp", lambda digest: calls.append(digest) and None)

    result = pt.seal_pending_predictions()

    assert len(calls) == 1
    assert result == {"sealed": 0, "failed": 1, "remaining": 3}
    assert isolated_db.count_unsealed_predictions() == 3


def test_sweep_respects_the_batch_limit(isolated_db, monkeypatch):
    _make(isolated_db, 5)
    monkeypatch.setattr(pt, "submit_timestamp", lambda digest: "ab12")
    result = pt.seal_pending_predictions(limit=2)
    assert result == {"sealed": 2, "failed": 0, "remaining": 3}


def test_seal_line_always_reports_what_is_left():
    assert pt.seal_line({"sealed": 0, "failed": 0, "remaining": 0}) == "예측 봉인: 미봉인 예측 없음"
    assert "남은 미봉인 3건" in pt.seal_line({"sealed": 2, "failed": 0, "remaining": 3})
    line = pt.seal_line({"sealed": 0, "failed": 1, "remaining": 36})
    assert "남은 미봉인 36건" in line and "다음 주기 재시도" in line


def _find_func(tree: ast.Module, name: str):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"{name} 없음")


def _called(func: ast.AST) -> set[str]:
    out = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                out.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                out.add(fn.attr)
    return out


def test_hourly_collection_cycle_runs_the_seal_sweep_and_logs_it():
    """배선 고정: 예측을 남기는 바로 그 주기(collect_free_sources)가 봉인 단계를 부르고,
    그 결과 줄이 수집 로그로 나가야 한다. 함수만 있고 아무도 안 부르면 사고가 되풀이된다."""
    tree = ast.parse((ROOT / "collector.py").read_text(encoding="utf-8"))
    cycle = _find_func(tree, "collect_free_sources")
    called = _called(cycle)
    assert "log_notable_predictions" in called
    assert "seal_pending_predictions" in called
    # seal_line(seal_pending_predictions()) 가 log(...) 의 인자 안에 있어야 한다.
    logged = False
    for node in ast.walk(cycle):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "log":
            inner = {n.func.id for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            if {"seal_line", "seal_pending_predictions"} <= inner:
                logged = True
    assert logged, "봉인 결과가 수집 로그로 나가지 않는다"
