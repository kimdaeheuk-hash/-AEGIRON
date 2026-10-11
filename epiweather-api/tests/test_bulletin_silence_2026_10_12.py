"""WHO 상황보고서 층이 **조용히 끝나지 않는다** — 네 가지 침묵을 가른다.

## 배경 (2026-10-12 아침 점검에서 발견)

문서 층(NVIDIA `nemotron-parse`)은 스케줄러에 **이미 배선돼 있었고 실제로 돌았다** —
2026-10-08 21:05 UTC 프로덕션 로그:

    WHO 상황보고서: 새 회차 1건 파싱, 신호 2건 적재 (기존 5건은 건너뜀)

그런데 10-09·10·11 사흘은 이 층의 로그가 **0줄**이었고, 아침 점검이 그 0줄의
뜻을 가릴 방법이 없었다. `_run_bulletin_collection` 이 `if result["parsed"]`
일 때만 로그를 남기고 키 없음은 조용히 return 했기 때문이다. 네 가지가 전부
같은 침묵이었다:

  ① 확인했고 새 회차가 없다 (정상 — 보고서는 주 1회 나온다)
  ② IRIS 조회가 죽었다 — `{"ok": False, "reason": …}` 반환값이 통째로 버려졌다
  ③ `NVIDIA_API_KEY` 가 빠졌다 — 조용히 return
  ④ 스케줄러가 이 줄에 닿지도 못했다

**①과 ②를 가릴 수 없다는 게 핵심이다.** 게다가 이 층은 소스 건강에 없다 —
주 1회 원천을 `FLAKY_WINDOW = 24`(최근 24주기 성공률) 틀에 넣으면 성공률이
영구히 문턱 아래라 `flaky` 거짓 경보가 된다. 그래서 **로그가 유일한 관측
경로**다.

같은 결함을 이 저장소가 이미 세 번 겪었다: GroqWatch 의 삼켜진 `except`
(2026-08-25 — 실패는 세는데 사유가 어디에도 없었다), Mobility 가 공항별 사유를
계산해놓고 버린 것(2026-08-28), 일일 브리핑이 성공 시 로그를 안 남겨 침묵과
구별되지 않은 것(10-10·10-11 점검이 '못 본 것'으로 적었다).

이 시험이 고정하는 것: (1) 어떤 경로로 끝나도 문장이 나온다, (2) 실패 사유가
조치 단위로 갈린다(IRIS 쪽이냐 NVIDIA 쪽이냐), (3) 그 줄이 실제 스케줄러
경로에서 불린다. 셋째가 빠지면 '만들어만 두고 아무도 안 부르는 층'이 된다.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from algorithms import bulletin_collect as bc
from algorithms.bulletin_collect import collection_summary

MAIN_PY = Path(__file__).resolve().parent.parent / "main.py"


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch, tmp_path):
    """시도 기록 파일을 시험마다 격리한다(운영 data/ 를 건드리지 않는다)."""
    monkeypatch.setattr(bc, "STATE_FILE", tmp_path / "processed.json")


class FakeDB:
    def __init__(self, existing_dates=()):
        self.existing = [{"signal_date": d} for d in existing_dates]
        self.rows = []

    def list_recent_signals_by_source(self, source, days=21, limit=50):
        return self.existing

    def create_extracted_signal(self, **kwargs):
        self.rows.append(dict(kwargs))
        return dict(kwargs)


def _report(number: int, issued: str) -> dict:
    return {"uuid": f"u{number}", "report_number": number, "issued": issued,
            "title": f"Weekly External Situation Report {number}",
            "pdf": {"name": f"sitrep{number}.pdf", "size_bytes": 100,
                    "url": f"https://iris.who.int/x/{number}"}}


def _patch(monkeypatch, reports, *, fetched=b"%PDF", table_result=None, signals=None):
    """수집 경로를 스텁으로 대체한다. table_result 를 직접 주어 실패 모양을 고른다."""
    import algorithms.bulletin_signals as bs
    import algorithms.pdf_table_extract as pt
    import algorithms.who_iris as wi

    monkeypatch.setattr(wi, "latest_situation_reports",
                        lambda limit=6, topic=None, search_size=30: reports)
    monkeypatch.setattr(wi, "fetch_bytes", lambda url, max_bytes=None: fetched)
    monkeypatch.setattr(
        pt, "extract_tables",
        lambda pdf, max_pages=4, **kw: dict(
            table_result if table_result is not None
            else {"ok": True, "pages": [], "pages_selected": [1, 2]}))
    monkeypatch.setattr(bs, "extract_signals",
                        lambda parsed, source=None, signal_date=None: {
                            "ok": True, "signal_count": len(signals or []),
                            "signals": [dict(s, signal_date=signal_date)
                                        for s in (signals or [])]})


_SIGNAL = {"source": "who_sitrep_bundibugyo", "disease": "Bundibugyo", "location": "DRC",
           "grade": None, "layout": None, "metrics": {"confirmed": 3262, "deaths": 1437},
           "raw_text": "DRC row", "cross_check": {"checked": True, "numbers_unverified": 0}}


# ── ① '새 회차 없음' 이 문장으로 나온다 ──────────────────────────────

def test_no_new_report_still_produces_a_line():
    """★ 이게 이 수리의 핵심 ★ 예전엔 parsed=0 이면 호출측이 아무 줄도 남기지
    않아서 '확인했고 없다' 와 'IRIS 가 죽었다' 가 같은 침묵이었다."""
    line = collection_summary({"ok": True, "reports_seen": 6, "parsed": 0,
                               "inserted": 0, "skipped_existing": 6})
    assert "새 회차 없음" in line
    # '없음' 과 '못 봤음' 을 가르려면 확인 건수가 같은 줄에 있어야 한다.
    assert "확인 6건" in line
    assert line.startswith("WHO 상황보고서:")


def test_no_new_report_line_is_never_empty_even_with_a_bare_result():
    """옛 형태 결과(키가 빠진 dict)가 와도 줄이 사라지지 않는다 — 배포 직후
    지난 주기가 만든 값에 새 키가 없을 수 있다."""
    line = collection_summary({"ok": True})
    assert line.strip()
    assert "새 회차 없음" in line
    assert "확인 0건" in line


# ── ② IRIS 실패가 침묵하지 않는다 ────────────────────────────────────

def test_iris_failure_is_not_silent_and_carries_its_reason():
    """`ok: False` 반환값이 통째로 버려지던 자리."""
    line = collection_summary({"ok": False, "reason": "IRIS 조회 실패(ConnectionError)",
                               "parsed": 0, "inserted": 0})
    assert line.startswith("❌")
    assert "IRIS 조회 실패(ConnectionError)" in line


def test_failure_without_reason_does_not_claim_success():
    """사유가 비어도 성공으로 읽히면 안 된다."""
    line = collection_summary({"ok": False})
    assert line.startswith("❌")
    assert "사유 미상" in line


# ── ③ 실패 사유가 조치 단위로 갈린다 ────────────────────────────────

def test_pdf_download_failure_is_counted_with_its_own_reason(monkeypatch):
    """PDF 를 못 받은 것은 IRIS 쪽 문제다 — NVIDIA 쪽과 섞이면 안 된다."""
    _patch(monkeypatch, [_report(11, "2026-10-04")], fetched=None)
    result = bc.collect_new_reports(FakeDB(), max_new=2)

    assert result["failed"] == 1
    assert result["failure_reasons"] == {"PDF 못 받음": 1}
    assert "PDF 못 받음×1" in collection_summary(result)


def test_table_extraction_failure_keeps_the_extractors_own_reason(monkeypatch):
    """표 추출이 준 사유를 그대로 들고 온다 — 키 문제와 네트워크 문제는 조치가 다르다."""
    _patch(monkeypatch, [_report(11, "2026-10-04")],
           table_result={"ok": False, "reason": "NVIDIA_API_KEY 없음 — 표 추출 생략"})
    result = bc.collect_new_reports(FakeDB(), max_new=2)

    assert result["failed"] == 1
    assert result["failure_reasons"] == {"NVIDIA_API_KEY 없음 — 표 추출 생략": 1}


def test_total_page_failure_without_reason_says_how_many_pages_died(monkeypatch):
    """extract_tables 는 페이지가 전부 실패하면 ok=False 에 reason 을 안 준다
    (ok 가 bool(parsed) 다). 그 경우를 '사유 미상' 으로 흘리지 않는다."""
    _patch(monkeypatch, [_report(11, "2026-10-04")],
           table_result={"ok": False, "pages_failed": 3})
    result = bc.collect_new_reports(FakeDB(), max_new=2)

    assert result["failure_reasons"] == {"표 추출 전멸(페이지 3장 실패)": 1}


def test_two_different_failures_are_not_merged_into_one_count(monkeypatch):
    """★ Mobility 가 401·403·5xx 를 `http_error` 하나로 묶어 원인을 못 찾게
    만든 전례 ★ 서로 다른 실패는 따로 세어야 한다."""
    reports = [_report(11, "2026-10-04"), _report(12, "2026-10-11")]
    calls = {"n": 0}

    import algorithms.pdf_table_extract as pt
    import algorithms.who_iris as wi
    import algorithms.bulletin_signals as bs

    monkeypatch.setattr(wi, "latest_situation_reports",
                        lambda limit=6, topic=None, search_size=30: reports)

    def fetch(url, max_bytes=None):
        calls["n"] += 1
        return None if calls["n"] == 1 else b"%PDF"      # 첫 건만 PDF 실패

    monkeypatch.setattr(wi, "fetch_bytes", fetch)
    monkeypatch.setattr(pt, "extract_tables",
                        lambda pdf, max_pages=4, **kw: {"ok": False, "pages_failed": 2})
    monkeypatch.setattr(bs, "extract_signals",
                        lambda parsed, source=None, signal_date=None: {
                            "ok": True, "signal_count": 0, "signals": []})

    result = bc.collect_new_reports(FakeDB(), max_new=3)

    assert result["failed"] == 2
    assert result["failure_reasons"] == {
        "PDF 못 받음": 1, "표 추출 전멸(페이지 2장 실패)": 1}


def test_counted_failure_with_no_reason_is_named_as_a_silent_path():
    """실패를 셌는데 사유가 하나도 없으면 '사유 없음' 이라고 말한다 — 그 자체가
    '실패 경로가 아직 조용하다' 는 정보다(collector._fmt_failure_reasons 와 같은 규약)."""
    line = collection_summary({"ok": True, "reports_seen": 2, "parsed": 0,
                               "failed": 2, "failure_reasons": {}})
    assert "사유 없음(실패 경로가 아직 조용하다)" in line


# ── ④ 성공 경로는 숫자를 그대로 싣는다 ──────────────────────────────

def test_parsed_summary_carries_every_number(monkeypatch):
    """10-08 에 실제로 찍힌 모양을 유지한다."""
    _patch(monkeypatch, [_report(12, "2026-10-11")], signals=[_SIGNAL])
    db = FakeDB()
    result = bc.collect_new_reports(db, max_new=2)
    line = collection_summary(result)

    assert result["parsed"] == 1
    assert "새 회차 1건 파싱" in line
    assert f"신호 {result['inserted']}건 적재" in line
    assert "실패" not in line                 # 실패가 0이면 그 조각을 안 붙인다


def test_success_does_not_invent_a_failure_segment():
    line = collection_summary({"ok": True, "reports_seen": 6, "parsed": 1,
                               "inserted": 2, "skipped_existing": 5, "failed": 0,
                               "failure_reasons": {}})
    assert "실패" not in line
    assert "기존 5건 건너뜀" in line


# ── 배선 — 이 줄이 실제 스케줄러 경로에서 불리는가 ──────────────────

def _scheduler_fn() -> ast.AsyncFunctionDef:
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))
    return next(n for n in ast.walk(tree)
                if isinstance(n, ast.AsyncFunctionDef)
                and n.name == "_run_bulletin_collection")


def test_scheduler_sends_the_summary_to_the_log():
    """★ 만들어만 두고 아무도 안 부르는 층 ★ `collection_summary` 의 결과가
    `collector.log` 의 인자 안에 실제로 들어가는지 AST 로 고정한다. 문자열
    grep 이 아니라 호출 트리를 본다."""
    fn = _scheduler_fn()

    logged = [
        call for call in ast.walk(fn)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
        and call.func.attr == "log"
        and any(isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                and inner.func.id == "collection_summary"
                for arg in call.args for inner in ast.walk(arg))
    ]
    assert logged, "collection_summary 의 결과가 collector.log 로 나가지 않는다"


def test_summary_log_is_not_guarded_by_parsed():
    """★ 이 수리의 본질 ★ 요약 줄은 `if result["parsed"]` 안에 있으면 안 된다 —
    그러면 '새 회차 없음' 이 다시 침묵이 된다."""
    fn = _scheduler_fn()

    def logs_summary(node) -> bool:
        return any(
            isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            and call.func.attr == "log"
            and any(isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                    and inner.func.id == "collection_summary"
                    for arg in call.args for inner in ast.walk(arg))
            for call in ast.walk(node))

    guarded = [n for n in ast.walk(fn)
               if isinstance(n, ast.If)
               and any(isinstance(c, ast.Constant) and c.value == "parsed"
                       for c in ast.walk(n.test))
               and logs_summary(n)]
    assert not guarded, "요약 줄이 parsed 분기 안에 갇혀 있다(옛 결함 재발)"


def test_missing_key_path_logs_before_it_returns():
    """키 없음도 한 줄 남긴다 — 조용히 return 하면 '키가 빠졌다' 와 '층이
    죽었다' 를 가릴 수 없다(Tavily 의 `대체 공급자 없음` 과 같은 규칙)."""
    fn = _scheduler_fn()

    key_branches = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.If)
        and any(isinstance(c, ast.Constant) and c.value == "NVIDIA_API_KEY"
                for c in ast.walk(n.test))
    ]
    assert key_branches, "NVIDIA_API_KEY 분기를 못 찾았다"

    for branch in key_branches:
        assert any(isinstance(n, ast.Return) for n in ast.walk(branch)), \
            "키 없음 분기가 return 하지 않는다"
        assert any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "log" for n in ast.walk(branch)), \
            "키 없음 분기가 로그를 남기지 않고 조용히 돌아간다"


def test_algorithms_import_and_awaits_stay_inside_try():
    """★ 이 수리를 하다가 실제로 만든 회귀를 고정한다 (2026-10-12) ★

    `_scheduler_loop` 는 `await _run_bulletin_collection()` 을 try 로 감싸지
    않는다. 그래서 이 함수에서 예외가 올라가면 **매시간 수집 루프가 통째로
    죽는다** — 에러 한 줄 없이 멈추는 사고 ②(2026-08-22)와 같은 모양이다.
    요약 줄을 넣으면서 `from algorithms.bulletin_collect import …` 를 함수
    최상단(try 밖)으로 옮겼다가 이걸 알아차렸다. import 한 줄로도 충분하다.

    `import collector` 는 예외다 — 로그를 남기는 수단 자체라 try 안에 둘 수
    없고, 기존에도 밖이었다.
    """
    fn = _scheduler_fn()

    inside: set[int] = set()
    for node in (n for n in ast.walk(fn) if isinstance(n, ast.Try)):
        inside.update(id(n) for n in ast.walk(node))

    risky = [
        n for n in ast.walk(fn)
        if (isinstance(n, ast.ImportFrom) and (n.module or "").startswith("algorithms"))
        or isinstance(n, ast.Await)
    ]
    assert risky, "검사 대상(algorithms import·await)을 못 찾았다"
    for node in risky:
        assert id(node) in inside, (
            f"{type(node).__name__} 이 try 밖에 있다 — 실패가 스케줄러 루프를 "
            "죽인다(사고 ②와 같은 모양)")


def test_failed_result_also_goes_to_the_error_ledger():
    """로그 한 줄로 끝내지 않는다 — `/api/status` 의 recent_errors 에 안 들어가면
    '실패는 아는데 왜 실패했는지 어디에도 없는' 상태가 된다(2026-08-25 교훈)."""
    fn = _scheduler_fn()

    ledger_calls = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "log_error"
    ]
    # 둘 이상이어야 한다: 예외 경로 + ok=False 경로.
    assert len(ledger_calls) >= 2, \
        "ok=False 경로가 장부(log_error)에 안 들어간다 — 예외 경로만 있다"
