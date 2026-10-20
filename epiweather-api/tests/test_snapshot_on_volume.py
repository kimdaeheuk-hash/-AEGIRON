"""실행 중에 받은 기준 스냅샷은 볼륨에 쓴다 (2026-10-20, 소킹 10-19 — 배포마다 approved_products 가 사라짐).

고정하는 것: ① 갱신은 볼륨(RUNTIME_DIR)에 쓰고 저장소 사본은 건드리지 않는다 ② 읽을 때는 볼륨 사본과
저장소 사본 중 snapshot_date 가 늦은 쪽 ③ 커밋으로 더 새 값을 넣으면 저장소 쪽이 이긴다
④ 볼륨 디렉터리는 Railway 볼륨 마운트(epiweather-api/data) 아래다 ⑤ 백신·IHR 소비자도 같은 규칙으로 읽는다.
"""
from __future__ import annotations

import json
from unittest.mock import patch

from algorithms import reference_snapshots as rs


def _payload(date: str, n: int = 5) -> dict:
    return {"snapshot_date": date, "source": "시험", "by_threat": {f"T{i}": [] for i in range(n)}}


def test_refresh_writes_to_the_volume_not_the_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "REFERENCE_DIR", tmp_path / "repo")
    with patch("algorithms.reference_fetch.fetch_approved_products", return_value=_payload("2026-10-20")):
        out = rs.refresh("approved_products")
    assert out["refreshed"] is True
    assert (rs.RUNTIME_DIR / "approved_products.json").exists()
    assert not (tmp_path / "repo" / "approved_products.json").exists()
    assert rs.snapshot_status("approved_products")["present"] is True


def test_reads_the_newer_of_volume_and_repo_copies(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(rs, "REFERENCE_DIR", repo)
    rs.RUNTIME_DIR.mkdir(parents=True)
    (repo / "approved_products.json").write_text(json.dumps(_payload("2026-07-01", 3)))
    (rs.RUNTIME_DIR / "approved_products.json").write_text(json.dumps(_payload("2026-10-20", 7)))
    assert rs.path_for("approved_products").parent == rs.RUNTIME_DIR
    # 커밋으로 더 새 값을 넣으면 저장소 쪽이 이긴다.
    (repo / "approved_products.json").write_text(json.dumps(_payload("2026-11-01", 4)))
    assert rs.path_for("approved_products").parent == repo


def test_runtime_dir_is_under_the_volume_mount():
    import importlib
    fresh = importlib.reload(rs)        # autouse 픽스처가 바꾼 값이 아니라 모듈의 원래 값
    try:
        assert fresh.RUNTIME_DIR.parts[-3:] == ("epiweather-api", "data", "reference")
    finally:
        importlib.reload(rs)


def test_vaccine_consumer_reads_the_refreshed_volume_copy(tmp_path, monkeypatch):
    from algorithms import vaccine_supply
    seed = tmp_path / "who_prequalified_vaccines.json"
    seed.write_text(json.dumps({"snapshot_date": "2026-09-02", "records": [{"v": 1}]}))
    monkeypatch.setattr(vaccine_supply, "REFERENCE", seed)
    rs.RUNTIME_DIR.mkdir(parents=True)
    (rs.RUNTIME_DIR / seed.name).write_text(json.dumps({"snapshot_date": "2026-10-20", "records": [{"v": 1}, {"v": 2}]}))
    vaccine_supply._snapshot.cache_clear()
    try:
        assert len(vaccine_supply._snapshot()["records"]) == 2
    finally:
        vaccine_supply._snapshot.cache_clear()
