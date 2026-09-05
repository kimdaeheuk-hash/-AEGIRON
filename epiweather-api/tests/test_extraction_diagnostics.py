"""추출 실패가 사유를 달고 나오는가 (2026-09-04).

## 무엇을 고친 것인가

운영 로그 실측:

    09-02 21:01   NLP 구조화 추출: 0건 저장
    09-03 21:01   NLP 구조화 추출: 0건 저장
    09-04 21:01   NLP 구조화 추출: 0건 저장 · 추출실패 5

추출층은 하루 한 번만 도는데 사흘 내리 0건이었다. 앞의 두 줄은 실패인지
중복건너뜀인지조차 구분이 안 됐고(그때는 계수기가 없었다), 마지막 줄은 5번
실패했다는 것만 말하고 **왜인지는 말하지 않았다.**

계수기만으로는 못 고친다. 5를 보고도 할 수 있는 게 없었다 — 키가 죽었는지,
모델명이 틀렸는지, 크레딧이 떨어졌는지, 모델이 JSON을 못 지켰는지가 전부 같은
None으로 접혔기 때문이다. 하마터면 "8B가 스키마를 못 지키니 모델을 올려라"라는
처방이 나갈 뻔했는데, 사실 그 사이클엔 폴백(Claude)도 같이 죽어 있었고 NIM 이전
이틀도 0건이었다.

## 이 파일이 지키는 것

**실패는 사유와 경로를 달고 나온다.** '몇 번' 다음엔 반드시 '왜'가 온다.
그리고 성공했더라도 도중에 죽은 경로는 숨기지 않는다 — 폴백이 매번 구해주는
중이라면 NIM은 사실상 꺼져 있는 것이다.
"""
from __future__ import annotations

from unittest.mock import patch

import algorithms.aegiron_model as am
from algorithms import nlp_extract as nx


def _record(source: str = "who_emro", raw_text: str = "원문") -> dict:
    return {
        "source": source, "disease": "에볼라", "location": "DRC",
        "country_iso3": "COD", "signal_type": "신규발생", "severity": [],
        "symptom": None, "transmission": None, "source_trust": 0.65,
        "signal_date": None, "known_disease": True, "raw_text": raw_text,
    }


def _nim_env(monkeypatch, base=None):
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.delenv("AEGIRON_NIM_API_KEY", raising=False)
    monkeypatch.delenv("AEGIRON_REQUIRE_LOCAL", raising=False)
    monkeypatch.delenv("AEGIRON_NVIDIA_ONPREM_BASE", raising=False)
    monkeypatch.delenv("AEGIRON_LOCAL_MODEL", raising=False)
    if base:
        monkeypatch.setenv("AEGIRON_NIM_BASE_URL", base)
    else:
        monkeypatch.delenv("AEGIRON_NIM_BASE_URL", raising=False)


class _Resp:
    def __init__(self, status):
        self.status_code = status


class _HTTPish(Exception):
    """requests.HTTPError처럼 response.status_code를 들고 다니는 예외."""

    def __init__(self, status):
        super().__init__(f"{status} Client Error: for url https://x/v1/chat/completions")
        self.response = _Resp(status)


# ── 사유가 실제로 붙는가 ─────────────────────────────────────────
def test_failed_extraction_names_the_path_and_the_reason(monkeypatch):
    """★핵심★ 두 경로가 다 죽으면 자취에 둘 다, 각자의 사유와 함께 남는다.
    이게 없어서 '추출실패 5'를 보고도 어디를 고칠지 알 수 없었다."""
    _nim_env(monkeypatch)
    with patch.object(am, "nim_raw_detailed", return_value=(None, "HTTPError 404")), \
         patch.object(nx, "llm_raw", return_value=(None, "AuthenticationError 401")):
        record, prov = am.extract_record("원문", source="who_emro")

    assert record is None
    assert prov["attempts"] == ["nvidia_nim_hosted: HTTPError 404",
                                "external_llm_fallback: AuthenticationError 401"]


def test_call_failure_and_schema_failure_are_different_reasons(monkeypatch):
    """호출이 안 된 것과 모델이 스키마를 못 지킨 것은 손댈 곳이 다르다.
    앞은 키·모델명·URL, 뒤는 모델 상향 — 섞으면 엉뚱한 데를 고친다."""
    _nim_env(monkeypatch)
    # 응답은 왔는데 JSON이 아님 → 파싱실패
    with patch.object(am, "nim_raw_detailed", return_value=("죄송합니다, 못 하겠어요", None)), \
         patch.object(nx, "llm_raw", return_value=(None, "Timeout")):
        _, prov = am.extract_record("원문", source="who_emro")

    assert prov["attempts"][0] == f"nvidia_nim_hosted: {nx.PARSE_FAILED}"
    assert prov["attempts"][1] == "external_llm_fallback: Timeout"


def test_status_code_survives_into_the_reason(monkeypatch):
    """401(키)·404(모델명)·402/429(한도)는 서로 다른 처방이다. 숫자가 살아야 한다."""
    _nim_env(monkeypatch)
    with patch("requests.post", side_effect=_HTTPish(404)):
        content, reason = am.nim_raw_detailed("원문", am._nim_config())
    assert content is None
    assert reason == "_HTTPish 404"


def test_reason_never_carries_the_response_body():
    """★유출 방지★ 사유는 로그·/api/status로 나간다. 본문에 요청 URL·헤더 조각이
    섞여 나올 수 있으므로 종류와 상태코드까지만 담는다."""
    brief = nx.brief_reason(_HTTPish(401))
    assert "chat/completions" not in brief
    assert "Client Error" not in brief
    assert brief == "_HTTPish 401"


def test_reason_without_status_code_is_still_named():
    assert nx.brief_reason(TimeoutError("느림")) == "TimeoutError"


# ── 성공했어도 죽은 경로를 숨기지 않는다 ─────────────────────────
def test_fallback_rescue_is_reported_not_hidden(monkeypatch):
    """★핵심★ 폴백이 살리면 겉보기엔 성공이라 예전엔 아무 흔적도 안 남았다.
    그런데 그게 바로 'NIM 켰는데 계속 Claude가 돌고 있음'의 정확한 모습이다."""
    _nim_env(monkeypatch)
    with patch.object(am, "nim_raw_detailed", return_value=(None, "ConnectionError")), \
         patch.object(nx, "extract_signal_detailed", return_value=(_record(), None)):
        record, prov = am.extract_record("원문", source="who_emro")

    assert record is not None
    assert prov["ai_provider"] == "external_llm_fallback"
    assert prov["attempts"] == ["nvidia_nim_hosted: ConnectionError"]


def test_clean_nim_success_leaves_no_trail(monkeypatch):
    """죽은 게 없으면 자취도 없다 — 잡음을 만들지 않는다."""
    _nim_env(monkeypatch)
    with patch.object(am, "_nim_extract_detailed", return_value=(_record(), None)):
        record, prov = am.extract_record("원문", source="who_emro")
    assert record is not None
    assert prov["attempts"] == []


def test_sovereign_block_is_not_counted_as_a_failed_path(monkeypatch):
    """차단은 고장이 아니라 정책이 동작한 것이다. 실패 사유에 섞으면 '고쳐야 할
    것'과 '의도한 것'이 같은 목록에 들어간다."""
    _nim_env(monkeypatch)
    monkeypatch.setenv("AEGIRON_REQUIRE_LOCAL", "on")
    record, prov = am.extract_record("민감 원문", source="who_emro")
    assert record is None
    assert prov["blocked"] is True
    assert prov["attempts"] == []


def test_missing_fallback_key_says_so(monkeypatch):
    _nim_env(monkeypatch)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _, prov = am.extract_record("원문", source="who_emro", api_key=None)
    assert prov["attempts"] == ["external_llm_fallback: 키없음"]


# ── 사이클 집계 ──────────────────────────────────────────────────
def test_cycle_aggregates_reasons_by_path(isolated_db, monkeypatch):
    """수집기가 한 줄로 찍을 수 있게 경로별로 센다."""
    _nim_env(monkeypatch)
    watch = {"signals": [{"id": "who_emro", "text": "가"},
                         {"id": "africa_cdc", "text": "나"}]}
    with patch.object(am, "nim_raw_detailed", return_value=(None, "HTTPError 404")), \
         patch.object(nx, "llm_raw", return_value=(None, "HTTPError 401")):
        out = nx.extract_from_global_watch_detailed(watch, api_key="k")

    assert out["failed"] == 2
    assert out["failure_reasons"] == {"nvidia_nim_hosted: HTTPError 404": 2,
                                      "external_llm_fallback: HTTPError 401": 2}


def test_cycle_counts_fallback_rescues(isolated_db, monkeypatch):
    _nim_env(monkeypatch)
    watch = {"signals": [{"id": "who_emro", "text": "가"}]}
    with patch.object(am, "nim_raw_detailed", return_value=(None, "Timeout")), \
         patch.object(nx, "extract_signal_detailed",
                      return_value=(_record("who_emro", "가"), None)):
        out = nx.extract_from_global_watch_detailed(watch, api_key="k")

    assert len(out["records"]) == 1
    assert out["rescued_by_fallback"] == 1
    assert out["failure_reasons"] == {"nvidia_nim_hosted: Timeout": 1}


# ── 로그 한 줄 ───────────────────────────────────────────────────
def test_log_line_says_why_not_just_how_many():
    """★이게 09-04에 없던 것★ '추출실패 5' 뒤에 경로별 사유가 붙는다."""
    line = nx.extraction_summary({
        "records": [], "providers": {}, "failed": 5, "blocked": 0,
        "skipped_duplicate": 0,
        "failure_reasons": {"nvidia_nim_hosted: HTTPError 404": 5,
                            "external_llm_fallback: HTTPError 401": 5}})
    assert "추출실패 5" in line
    assert "nvidia_nim_hosted: HTTPError 404×5" in line
    assert "external_llm_fallback: HTTPError 401×5" in line


def test_log_line_surfaces_a_silently_rescued_nim():
    line = nx.extraction_summary({
        "records": [_record()], "providers": {"external_llm_fallback": 1},
        "failed": 0, "blocked": 0, "skipped_duplicate": 0,
        "failure_reasons": {"nvidia_nim_hosted: Timeout": 1},
        "rescued_by_fallback": 1})
    assert "1건 저장" in line
    assert "폴백이 구제 1" in line
    assert "nvidia_nim_hosted: Timeout×1" in line


def test_log_line_tolerates_the_old_shape():
    """★배포 직후★ 지난 주기가 만든 값엔 새 키가 없다. 줄이 통째로 사라지면
    '조용해진 층'이 하나 더 생긴다 — 파이프라인에서 이미 겪었다."""
    line = nx.extraction_summary({"records": [], "providers": {}, "failed": 5,
                                  "blocked": 0, "skipped_duplicate": 0})
    assert line == "0건 저장 · 추출실패 5"


def test_log_line_stays_quiet_on_a_clean_cycle():
    line = nx.extraction_summary({
        "records": [_record()], "providers": {"nvidia_nim_hosted": 1},
        "failed": 0, "blocked": 0, "skipped_duplicate": 0,
        "failure_reasons": {}, "rescued_by_fallback": 0})
    assert line == "1건 저장 · nvidia_nim_hosted=1"


# ── 능력 장부: 폴백도 관측한다 ───────────────────────────────────
def test_external_llm_failure_is_recorded_in_the_ledger(monkeypatch):
    """★NIM 층만 장부에 있었다★ 그래서 '둘 다 죽었다'를 /api/status에서 볼 수
    없었다. 폴백은 마지막 방어선이라 그게 서 있는지가 특히 중요하다."""
    from algorithms.capability_ledger import status

    class _Boom:
        def __init__(self, **kw): pass

        @property
        def messages(self): raise AssertionError("여기까지 오면 안 됨")

    with patch("anthropic.Anthropic") as client:
        client.return_value.messages.create.side_effect = _HTTPish(401)
        raw, reason = nx.llm_raw("원문", "key")

    assert raw is None and reason == "_HTTPish 401"
    st = status(nx.EXTERNAL_LLM_CAPABILITY, configured=True)
    assert st["verified"] is False
    assert st["claim_basis"] == "observed_failure"
    assert "_HTTPish" in (st["last_error"] or "")


def test_external_llm_success_is_recorded_in_the_ledger():
    from algorithms.capability_ledger import status

    class _Block:
        type = "text"
        text = "{}"

    with patch("anthropic.Anthropic") as client:
        client.return_value.messages.create.return_value.content = [_Block()]
        raw, reason = nx.llm_raw("원문", "key")

    assert raw == "{}" and reason is None
    st = status(nx.EXTERNAL_LLM_CAPABILITY, configured=True)
    assert st["verified"] is True
    assert st["last_sovereign"] is False        # 외부 API — 주권 경로가 아니다


# ── 설명불가 감시: 다섯 사유를 한 문장으로 뭉치지 않는다 ─────────
# 예전 로그는 이랬다:
#
#     ⏭ 설명불가 신호 감시: 새 신호 없음(검색/추출 실패, 배경정보 노이즈,
#       또는 최근 21일 내 동일 사건 재탐지 중 하나)
#
# '검색이 죽었다'와 '오늘은 새 사건이 없다'는 정반대 상태다. 앞은 고쳐야 할
# 고장이고 뒤는 정상 동작인데, 같은 문장으로 나가니 몇 주째 고장이 나 있어도
# 알 수가 없었다 — NLP 추출이 사흘간 0건이었는데 아무도 몰랐던 것과 같은 모양.
def test_unexplained_search_failure_is_not_no_news(monkeypatch):
    """★핵심★ 검색이 죽은 것을 '새 신호 없음'으로 접지 않는다."""
    from algorithms import unexplained as ux
    monkeypatch.setattr(ux, "perplexity_search",
                        lambda *a, **k: (_ for _ in ()).throw(TimeoutError()))
    _, why = ux.run_unexplained_watch_detailed(perplexity_key="p")
    assert "검색 실패" in why and "TimeoutError" in why


def test_unexplained_rediscovery_is_marked_normal(isolated_db, monkeypatch):
    """재탐지는 고장이 아니다 — 그 사실을 문장에 담는다."""
    from algorithms import unexplained as ux
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(ux, "perplexity_search", lambda *a, **k: "원인불명 폐렴 집단")
    monkeypatch.setattr(ux, "extract_record",
                        lambda *a, **k: (_record("unexplained_cluster", "원문"), {}))
    monkeypatch.setattr(ux, "_is_duplicate_event", lambda *a, **k: True)
    record, why = ux.run_unexplained_watch_detailed(perplexity_key="p", anthropic_key="k")
    assert record is None
    assert "재탐지" in why and "정상" in why


def test_unexplained_extraction_failure_carries_the_trail(isolated_db, monkeypatch):
    """추출이 죽었으면 어느 경로에서 죽었는지까지 나온다."""
    from algorithms import unexplained as ux
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(ux, "perplexity_search", lambda *a, **k: "원인불명 폐렴 집단")
    monkeypatch.setattr(ux, "extract_record", lambda *a, **k: (
        None, {"attempts": ["nvidia_nim_hosted: HTTPError 404",
                            "external_llm_fallback: HTTPError 401"]}))
    _, why = ux.run_unexplained_watch_detailed(perplexity_key="p", anthropic_key="k")
    assert "추출 실패" in why
    assert "HTTPError 404" in why and "HTTPError 401" in why


def test_unexplained_background_noise_says_what_it_dropped(isolated_db, monkeypatch):
    from algorithms import unexplained as ux
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(ux, "perplexity_search", lambda *a, **k: "여론조사 결과 발표")
    bare = {**_record("unexplained_cluster", "원문"), "disease": None, "symptom": None}
    monkeypatch.setattr(ux, "extract_record", lambda *a, **k: (bare, {}))
    _, why = ux.run_unexplained_watch_detailed(perplexity_key="p", anthropic_key="k")
    assert "배경정보" in why


def test_unexplained_no_search_key_is_distinguished():
    from algorithms import unexplained as ux
    _, why = ux.run_unexplained_watch_detailed()
    assert "검색 키 없음" in why


# ── 기준 스냅샷: "(None일 전)" 을 없앤다 ─────────────────────────
def test_absent_snapshot_says_absent_not_none_days():
    """★실측 결함★ 파일이 없으면 age_days가 None이라 운영 로그에
    "묵음 (None일 전)"으로 나갔다. 한 번도 안 떠진 것과 오래된 것은 다른 상태다."""
    from algorithms.reference_snapshots import stale_lines
    lines = stale_lines({"stale": ["approved_products"],
                         "ages_days": {"approved_products": None},
                         "reasons": {"approved_products": "기준 파일이 없다"}})
    assert lines == ["기준 스냅샷 'approved_products' — 기준 파일이 없다"]
    assert "None" not in lines[0]


def test_stale_snapshot_reports_its_age():
    from algorithms.reference_snapshots import stale_lines
    lines = stale_lines({"stale": ["vaccine_supply"],
                         "ages_days": {"vaccine_supply": 120.0},
                         "reasons": {"vaccine_supply": "120일 묵음(기준 90일)"}})
    assert lines == ["기준 스냅샷 'vaccine_supply' — 120일 묵음(기준 90일)"]


def test_stale_lines_tolerate_the_old_shape_without_reasons():
    """★배포 직후★ reasons 키가 없던 시절 값에도 안 터지고, 나이로라도 말한다."""
    from algorithms.reference_snapshots import stale_lines
    assert stale_lines({"stale": ["ihr_capacity"],
                        "ages_days": {"ihr_capacity": 200.4}}) == [
        "기준 스냅샷 'ihr_capacity' — 200일 묵음"]
    # 나이조차 없으면 조용해지지 않고 '모른다'고 말한다.
    assert stale_lines({"stale": ["ihr_capacity"]}) == [
        "기준 스냅샷 'ihr_capacity' — 사유 미상(갱신 대기)"]


def test_stale_lines_survive_a_broken_layer():
    from algorithms.reference_snapshots import stale_lines
    assert stale_lines(None) == []
    assert stale_lines({"error": "TypeError"}) == []


# ── 사유 문자열을 만드는 자리는 한 곳이다 (2026-09-05) ───────────
# brief_reason 을 nlp_extract 에만 뒀더니, 몇 시간 뒤 조달(TED) 층이 똑같은
# 실수를 되풀이했다 — 예외 이름만 찍고 상태코드를 버렸다. 공용 자리로 옮긴다.
def test_brief_reason_lives_in_one_place():
    from algorithms.common import brief_reason as canonical
    assert nx.brief_reason is canonical


def test_ted_layer_uses_the_same_reason_builder():
    from algorithms import procurement_ted as ted
    from algorithms.common import brief_reason as canonical
    assert ted.brief_reason is canonical


def test_tally_keeps_attempt_order_and_counts():
    from algorithms.common import tally
    assert tally(["HTTPError 404"] * 3 + ["Timeout"]) == "HTTPError 404×3 · Timeout×1"
    assert tally([]) == ""
