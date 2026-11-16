"""데이터 보유량 집계 — 무엇을 언제부터 얼마나 쌓았나 (2026-11-16).

캡틴: "관측은 몇 달 전부터 한 거 아냐?" → "보고해서 데이터로 집계해 판매할 수 있게 전부 셋팅해야 해".
판매 이야기를 하려면 먼저 **실제 보유량**을 숫자로 말할 수 있어야 한다. 추정으로 말하지 않으려고
운영 DB 와 누적 기록 파일을 직접 센다.

## 무엇을 세나

- DB 테이블마다: 행 수, 첫·마지막 시각(그 테이블의 시각 칸 기준), 기록이 있는 날 수.
- 누적 파일(signals_log.jsonl 매시 수집 기록, baseline_signals.jsonl 기준선): 줄 수, 첫·마지막 기록 시각, 크기.
  큰 파일(수백 MB)이라 줄 수 세기는 무겁다 — 결과를 TTL 동안 캐시하고, 매일 한 번 로그에 남긴다.

## 정직성

- 못 센 테이블·파일은 0 이 아니라 error 를 적는다(판정 안 함).
- 시각 칸의 형식이 섞여 있을 수 있어 첫·마지막은 문자열 최소·최대다(ISO 형식이면 시간순과 같다). 날 수는 앞 10자(YYYY-MM-DD).
- api_key_usage(고객 호출 기록)처럼 내부·개인 정보 성격의 테이블은 세지 않는다.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

# 테이블 → (시각 칸, 설명). 설명은 카탈로그·화면에서 쓴다.
TABLES: dict[str, tuple[str, str]] = {
    "alerts": ("alert_date", "경보(등급·근거·전송 기록)"),
    "extracted_signals": ("extracted_at", "발생 보도 AI 구조화 추출"),
    "predictions": ("predicted_at", "질병 지목 예측 원장"),
    "lead_time_ledger": ("crossed_at", "선행성 원장(문턱 통과 → 공식 선언)"),
    "outbreak_timeline": ("created_at", "발병 타임라인"),
    "sentinel_queue": ("detected_at", "센티넬 검증 대기열"),
    "daily_briefs": ("brief_date", "일일 브리핑 보관본"),
    "weekly_reports": ("generated_at", "한국 해외유입 주간 보고서"),
    "weekly_forecasts": ("created_at", "이웃 나라 주간 예측(일본 IDWR)"),
    "weekly_observations": ("observed_at", "이웃 나라 주간 관측값"),
    "baikal_snapshots": ("observed_at", "BAIKAL 7개 시스템 상태 스냅숏"),
    "baikal_transitions": ("observed_at", "BAIKAL 상태 전이"),
    "variant_ledger": ("observed_at", "변이 원장"),
    "match_ledger": ("verdict_date", "대응제-병원체 매칭 원장"),
    "countermeasure_stockpile": ("created_at", "대응제 비축 표"),
    "ground_truth_coverage": ("recorded_at", "정답 통로 수집 범위"),
    "kdca_vintages": ("seen_at", "질병청 수치 판본"),
    "observations": ("observed_at", "관측값 시계열(극지·기후·토지·삼림·무역·재난·여행경보)"),
    "don_response_measures": ("seen_at", "WHO DON 대응 조치"),
}

CORE_TABLES = ("alerts", "extracted_signals", "predictions", "lead_time_ledger", "daily_briefs", "weekly_reports")

FILES: dict[str, str] = {
    "signals_log.jsonl": "매시 수집 기록(모든 무료·AI 소스 원값)",
    "baseline_signals.jsonl": "이상 탐지 기준선",
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_TTL_S = int(os.environ.get("EPIWEATHER_INVENTORY_TTL_S", "3600"))

_lock = threading.Lock()
_cache: tuple[float, dict] | None = None


def _table_stats(conn, table: str, col: str) -> dict:
    try:
        row = conn.execute(
            f"SELECT COUNT(*) AS n, MIN({col}) AS first, MAX({col}) AS last, "
            f"COUNT(DISTINCT substr({col}, 1, 10)) AS days FROM {table}"
        ).fetchone()
        return {"rows": int(row["n"]), "first": row["first"], "last": row["last"], "days": int(row["days"] or 0)}
    except Exception as e:  # noqa: BLE001 — 표가 없거나 칸 이름이 다르면 판정 안 함
        return {"rows": None, "error": f"{type(e).__name__}: {e}"[:200]}


def _ts_of(line: str) -> str | None:
    try:
        rec = json.loads(line)
    except (ValueError, TypeError):
        return None
    if not isinstance(rec, dict):
        return None
    for k in ("timestamp", "_logged_at", "collected_at", "date"):
        v = rec.get(k)
        if isinstance(v, str) and v:
            return v
    return None


def _last_line(path: Path, chunk: int = 65536) -> str | None:
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        if end == 0:
            return None
        pos = max(0, end - chunk)
        f.seek(pos)
        tail = f.read().decode("utf-8", errors="replace").rstrip("\n")
    return tail.rsplit("\n", 1)[-1] if tail else None


def _file_stats(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "lines": 0}
    try:
        size = path.stat().st_size
        lines = 0
        first: str | None = None
        with open(path, "rb") as f:
            first_raw = f.readline()
            if first_raw:
                lines = 1
                first = _ts_of(first_raw.decode("utf-8", errors="replace"))
            for buf in iter(lambda: f.read(1 << 20), b""):
                lines += buf.count(b"\n")
        last_line = _last_line(path)
        return {
            "exists": True,
            "size_bytes": size,
            "lines": lines,
            "first": first,
            "last": _ts_of(last_line) if last_line else None,
        }
    except Exception as e:  # noqa: BLE001
        return {"exists": True, "lines": None, "error": f"{type(e).__name__}: {e}"[:200]}


def compute() -> dict:
    """지금 센다(무겁다 — 큰 파일 줄 수). 보통은 inventory() 로 캐시본을 쓴다."""
    import db

    t0 = time.monotonic()
    tables: dict[str, dict] = {}
    with db.get_connection() as conn:
        for name, (col, label) in TABLES.items():
            tables[name] = {"label": label, "time_column": col, **_table_stats(conn, name, col)}
    files = {name: {"label": label, **_file_stats(DATA_DIR / name)} for name, label in FILES.items()}
    # '가장 이른 기록'은 수집이 실제로 남긴 기록만 본다(참고표·기준 시드의 옛 날짜는 수집 시작이 아니다)
    core = [tables.get(t, {}) for t in CORE_TABLES] + [files.get("signals_log.jsonl", {})]
    firsts = [v.get("first") for v in core if v.get("first")]
    return {
        "computed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "earliest_record": min(firsts) if firsts else None,
        "tables": tables,
        "files": files,
        "elapsed_s": round(time.monotonic() - t0, 2),
        "basis": "운영 DB·누적 파일을 직접 센 값(추정 아님). 못 센 항목은 error. 내부 호출 기록(api_key_usage)은 제외.",
    }


def inventory(max_age_s: int | None = None) -> dict:
    """캐시본(기본 TTL 1시간). 없거나 낡으면 다시 센다."""
    global _cache
    ttl = CACHE_TTL_S if max_age_s is None else max_age_s
    with _lock:
        if _cache and time.monotonic() - _cache[0] < ttl:
            return _cache[1]
    data = compute()
    with _lock:
        _cache = (time.monotonic(), data)
    return data


def summary_line(inv: dict) -> str:
    """로그 한 줄 — '📦 데이터 보유량: …'. 숫자만, 해석 없이."""
    parts = []
    for name in ("alerts", "extracted_signals", "predictions", "lead_time_ledger", "weekly_reports", "observations"):
        t = inv["tables"].get(name, {})
        if t.get("rows") is None:
            parts.append(f"{name} 판정 안 함")
        else:
            parts.append(f"{name} {t['rows']}행({str(t.get('first') or '—')[:10]}~, {t.get('days', 0)}일)")
    f = inv["files"].get("signals_log.jsonl", {})
    if f.get("lines") is None:
        parts.append("signals_log 판정 안 함")
    elif f.get("exists"):
        parts.append(
            f"signals_log {f['lines']}줄·{round((f.get('size_bytes') or 0) / 1e6)}MB({str(f.get('first') or '—')[:10]}~)"
        )
    return f"📦 데이터 보유량(가장 이른 기록 {str(inv.get('earliest_record') or '—')[:10]}): " + " · ".join(parts)
