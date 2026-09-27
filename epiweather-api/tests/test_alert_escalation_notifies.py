"""등급이 올라가면 사람에게 간다 — 소킹 3일차에 관측된 정반대 방향의 고장.

09-22, `supply_alert_count` 가 **critical 로 23시간** 떠 있었는데 통보가 한 번도
안 나갔다. 매 주기 로그가 `알림: 보낼 신규 경보 없음` 이었다.

원인은 `already_seen_today = {r["source"] …}` 가 **등급을 안 본 것**이다. 오늘
`low` 로 한 번 잡힌 지표는 그 뒤 critical 로 올라가도 '이미 본 것'이라 조용했다.

거짓 경보의 정반대 방향이고, 조기경보 제품에서는 이쪽이 더 나쁘다 — 거짓은
신뢰를 깎지만 이건 **있는 경보를 없는 것으로 만든다.** 그리고 09-22 에는 마침
그 침묵이 거짓 경보를 가려줬다. 서로 상쇄하는 두 고장이 제일 조용하고 제일 위험하다.
"""
from __future__ import annotations

from algorithms.alerts import TIER_RANK, escalated, seen_rank_today


def test_brand_new_critical_is_sent():
    """기존 계약 — 처음 보는 source 의 critical/high 는 나간다."""
    assert escalated("gai:x", "critical", {}) is True
    assert escalated("gai:x", "high", {}) is True


def test_low_to_critical_is_sent():
    """★ 고친 자리 ★ 09-22 supply_alert_count 의 모양이다."""
    seen = seen_rank_today([{"source": "negative_space:behavioral.supply_alert_count",
                             "tier": "low"}])
    assert escalated("negative_space:behavioral.supply_alert_count", "critical", seen) is True


def test_ongoing_critical_is_not_resent():
    """기존 의도 유지 — 매시간 같은 경보를 재통보하지 않는다."""
    seen = seen_rank_today([{"source": "a", "tier": "critical"}])
    assert escalated("a", "critical", seen) is False


def test_de_escalation_is_not_news():
    """critical → high 는 나아진 것이다. 알림으로 깨우지 않는다."""
    seen = seen_rank_today([{"source": "a", "tier": "critical"}])
    assert escalated("a", "high", seen) is False


def test_high_to_critical_is_sent():
    seen = seen_rank_today([{"source": "a", "tier": "high"}])
    assert escalated("a", "critical", seen) is True


def test_medium_to_high_is_sent():
    seen = seen_rank_today([{"source": "a", "tier": "medium"}])
    assert escalated("a", "high", seen) is True


def test_seen_rank_keeps_the_highest_tier_per_source():
    seen = seen_rank_today([
        {"source": "a", "tier": "low"},
        {"source": "a", "tier": "critical"},
        {"source": "b", "tier": "medium"},
    ])
    assert seen == {"a": TIER_RANK["critical"], "b": TIER_RANK["medium"]}


def test_unknown_tier_counts_as_lowest():
    """등급 문자열이 낯설면 0으로 본다 — 모르는 값 때문에 통보가 막히면
    이번엔 반대로 진짜 경보를 죽인다."""
    seen = seen_rank_today([{"source": "a", "tier": "???"}])
    assert escalated("a", "high", seen) is True


def test_refresh_alerts_uses_escalated():
    """배선 고정 — 조건이 source 비교로 되돌아가면 침묵이 돌아온다."""
    import ast
    import inspect

    from algorithms import alerts
    src = inspect.getsource(alerts.refresh_alerts)
    names = {n.id for n in ast.walk(ast.parse(src.strip())) if isinstance(n, ast.Name)}
    assert "escalated" in names and "seen_rank_today" in names
