"""pytest 설정 — main.py와 동일하게 epiweather-api 루트를 sys.path에 올려서
`import db`, `from algorithms.xxx import yyy` 스타일 임포트가 테스트에서도 되게 함.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import db as dbmod  # noqa: E402


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """테스트마다 독립된 임시 SQLite를 쓰게 해서 실제 운영 DB를 건드리지 않음."""
    monkeypatch.setattr(dbmod, "DB_PATH", tmp_path / "test_epiweather.db")
    dbmod.init_db()
    yield dbmod
