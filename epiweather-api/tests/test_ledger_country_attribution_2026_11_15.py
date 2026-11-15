"""선행성 원장 — 나라를 맞춰서만 채점한다 (소킹 11-05~11-13, 2026-11-15).

관측: `홍역/국가미상`(11-05) → `홍역/SDN`(11-06), `pneumonia/국가미상`(11-07) → `폐렴/CHN`(11-13).
같은 사건이 나라를 읽기 전·뒤로 두 번 열렸다. 코드를 보니 더 큰 구멍이 있었다 — 선언과 맞출 때
나라를 안 봐서, 어느 나라에서든 같은 병이 선언되면 '실측'이 됐다. 홍역·폐렴은 90일 안에
어딘가에서 거의 반드시 선언된다. 그대로 두면 첫 실측이 우리가 지어낸 숫자가 된다.
"""
import datetime as dt

from algorithms.event_dedup import normalize_disease
from algorithms.lead_time_ledger import (
    OUTCOME_DECLARED, OUTCOME_DUPLICATE, OUTCOME_UNATTRIBUTABLE,
    ledger_record, list_entries, open_crossing, resolve_ledger,
)

UTC = dt.timezone.utc


def _at(y, m, d):
    return dt.datetime(y, m, d, tzinfo=UTC)


def _declare(dbmod, event_id, name, date):
    dbmod.upsert_timeline_event(event_id, name, date,
                                "who_pheic", "WHO 선언", "WHO DON", "who")


def test_other_country_declaration_does_not_credit_a_known_country(isolated_db):
    # 폐렴/CHN 이 다른 나라의 폐렴 선언으로 '실측'이 되면 안 된다.
    open_crossing("폐렴", "CHN", 80.0, 80.0, [1], now=_at(2026, 11, 13))
    _declare(isolated_db, "폐렴_ind_2026", "폐렴 IND", "2026-11-20")
    out = resolve_ledger(now=_at(2026, 11, 25))
    assert out["closed_declared"] == []
    assert out["still_open"] == 1
    assert ledger_record()["measured_events"] == 0


def test_same_country_declaration_still_credits(isolated_db):
    open_crossing("폐렴", "CHN", 80.0, 80.0, [1], now=_at(2026, 11, 13))
    _declare(isolated_db, "폐렴_chn_2026", "폐렴 CHN", "2026-11-20")
    (hit,) = resolve_ledger(now=_at(2026, 11, 25))["closed_declared"]
    assert hit["country_iso3"] == "CHN" and hit["lead_days"] == 7


def test_country_less_crossing_alone_is_never_measured(isolated_db):
    # 나라 모르는 통과 혼자서는 어느 나라의 선행인지 말할 수 없다 — 실측도 오경보도 아니다.
    open_crossing("홍역", None, 80.0, 80.0, [1], now=_at(2026, 11, 5))
    _declare(isolated_db, "홍역_sdn_2026", "홍역 SDN", "2026-11-20")
    out = resolve_ledger(now=_at(2026, 11, 25))
    assert out["closed_declared"] == []
    assert out["closed_unattributable"] == 1
    (row,) = list_entries()
    assert row["outcome"] == OUTCOME_UNATTRIBUTABLE
    rec = ledger_record()
    assert rec["measured_events"] == 0 and rec["false_alarms"] == 0
    assert rec["unattributable"] == 1


def test_soak_pattern_country_less_first_then_known_counts_once_from_known(isolated_db):
    # 11-05 홍역/국가미상 → 11-06 홍역/SDN. 나라 아는 쪽이 채점되고, 앞선 국가미상은 중복이다.
    open_crossing("홍역", None, 80.0, 80.0, [1], now=_at(2026, 11, 5))
    open_crossing("홍역", "SDN", 80.0, 80.0, [2], now=_at(2026, 11, 6))
    _declare(isolated_db, "홍역_sdn_2026", "홍역 SDN", "2026-11-20")
    out = resolve_ledger(now=_at(2026, 11, 25))
    (hit,) = out["closed_declared"]
    assert hit["country_iso3"] == "SDN"
    assert hit["lead_days"] == 14        # 나라를 안 날부터 — 국가미상(15일)으로 부풀리지 않는다
    assert out["closed_duplicate"] == 1
    outcomes = {r["country_iso3"]: r["outcome"] for r in list_entries()}
    assert outcomes == {"SDN": OUTCOME_DECLARED, None: OUTCOME_DUPLICATE}


def test_english_disease_names_are_normalized():
    assert normalize_disease("pneumonia") == "폐렴"
    assert normalize_disease("unknown pneumonia cluster") == "폐렴"
    assert normalize_disease("Measles outbreak") == "홍역"
    assert normalize_disease("pneumonic plague") != "폐렴"
