"""보고서 자동 수집 — 스케줄러가 부르는 한 칸짜리 진입점.

수집→표추출→신호→적재를 한 번에 돌리되, **이미 적재한 회차는 PDF를 아예 안
건드린다.** 비용이 여기 걸려 있기 때문이다: 표 추출은 회차당 VLM 4회 호출인데
보고서는 주 1회만 나온다. 매일 확인하되 새 회차가 있을 때만 파싱해야, 같은 PDF를
일주일에 일곱 번 재파싱하는 낭비를 피한다.

중복 판정은 두 겹이다:
  ① DB에 (source, signal_date) 신호가 있으면 처리 완료 — 재시작해도 DB가 남으면 유지.
  ② **시도 기록 파일**(data/bulletin_processed.json). ①만으로는 부족하다: 표를 못
     찾아 신호가 0건인 회차는 DB에 흔적이 없어 **매일 다시 파싱된다**(실측에서
     7/19 회차가 그랬다 — 결과 없이 하루 VLM 4회씩 영원히). 파싱을 시도했다는
     사실 자체를 남겨야 그 누수가 막힌다.

max_new로 한 번에 파싱할 회차 수를 묶는다. 첫 실행이 과거 회차를 전부 긁어
호출량이 튀는 걸 막는 안전장치다(과거분이 필요하면 그만큼 여러 번 돌리면 된다).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

# 시도 기록 — 신호가 0건이어도 '이미 해봤다'를 남겨 재파싱 낭비를 막는다.
STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "bulletin_processed.json"
# 오래된 기록은 정리한다(파일이 무한히 자라지 않게). 보고서는 주간이라 넉넉한 값.
STATE_KEEP_DAYS = 400


def _state_key(source: str, report: dict) -> str:
    return f"{source}|{report.get('issued') or report.get('uuid')}"


def load_processed() -> dict:
    """시도 기록 읽기. 파일이 없거나 깨져도 빈 기록으로 계속 간다."""
    try:
        with STATE_FILE.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_processed(state: dict) -> None:
    """시도 기록 쓰기. 실패해도 수집 자체를 막지 않는다(다음 회차에 재시도될 뿐)."""
    cutoff = (dt.datetime.now(dt.timezone.utc)
              - dt.timedelta(days=STATE_KEEP_DAYS)).isoformat()
    pruned = {k: v for k, v in state.items() if str(v) >= cutoff}
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(pruned, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def collect_new_reports(dbmod=None, source: str = "who_sitrep_bundibugyo",
                        topic: str | None = "Bundibugyo", limit: int = 6,
                        max_new: int = 2, max_pages: int = 4,
                        lookback_days: int = 180) -> dict:
    """새로 올라온 상황보고서만 적재. 예외를 던지지 않는다(스케줄러가 죽으면 안 됨)."""
    from .bulletin_ingest import ingest
    from .bulletin_signals import extract_signals
    from .pdf_table_extract import extract_tables
    from .who_iris import fetch_bytes, latest_situation_reports

    if dbmod is None:
        import db as dbmod                                       # noqa: PLC0415

    try:
        reports = latest_situation_reports(limit=limit, topic=topic)
    except Exception as e:
        return {"ok": False, "reason": f"IRIS 조회 실패({type(e).__name__})",
                "parsed": 0, "inserted": 0}
    if not reports:
        return {"ok": True, "reason": "새 보고서 없음", "reports_seen": 0,
                "parsed": 0, "inserted": 0, "skipped_existing": 0}

    try:
        known = dbmod.list_recent_signals_by_source(source, days=lookback_days, limit=2000)
    except Exception:
        known = []
    done_dates = {r.get("signal_date") for r in known if r.get("signal_date")}
    state = load_processed()
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()

    parsed = inserted = skipped = failed = 0
    processed: list[dict] = []
    for report in reports:
        issued = report.get("issued")
        key = _state_key(source, report)
        if (issued and issued in done_dates) or key in state:
            skipped += 1
            continue                                  # 이미 처리됨 — PDF를 열지도 않는다
        if parsed >= max_new:
            break                                     # 한 번에 파싱할 양을 묶는다

        pdf = fetch_bytes(report["pdf"]["url"])
        if not pdf:
            failed += 1
            continue
        table_result = extract_tables(pdf, max_pages=max_pages)
        if not table_result.get("ok"):
            failed += 1
            continue
        found = extract_signals(table_result, source=source, signal_date=issued)

        # ★ VLM은 같은 페이지를 같은 조건으로 보내도 매번 같은 표를 주지 않는다.
        # 실측(2026-07-26 상황보고서): 국가 요약표가 어떤 회차 실행에선 통째로
        # 빠져 신호 0건이 났는데, 그 페이지만 세 번 다시 보내니 세 번 다 정상
        # 3건이 나왔다. 페이지 선택도 파싱도 옳은데 응답이 흔들린 것이다.
        # 회차 전체가 0건이면 한 번만 다시 시도한다 — 실패했을 때만 드는 비용이라
        # 상한이 분명하고, 안 하면 그 주 보고서를 통째로 잃는다.
        retried = False
        if found["signal_count"] == 0:
            retried = True
            again = extract_tables(pdf, max_pages=max_pages)
            if again.get("ok"):
                found_again = extract_signals(again, source=source, signal_date=issued)
                if found_again["signal_count"] > 0:
                    table_result, found = again, found_again

        # 여기까지 왔으면 파싱은 실제로 해봤다 — 신호가 0건이어도 기록한다.
        # 안 그러면 표를 못 찾는 회차를 매일 다시 파싱하게 된다(실측 확인).
        state[key] = now_iso
        result = ingest(found["signals"], source=source, dbmod=dbmod)
        parsed += 1
        inserted += result["inserted"]
        processed.append({
            "report_number": report.get("report_number"),
            "issued": issued,
            "signals_found": found["signal_count"],
            "inserted": result["inserted"],
            "pages_selected": table_result.get("pages_selected"),
            # 재시도가 실제로 얼마나 일어나는지 보이게 남긴다 — 조용히 두 번씩
            # 부르면 비용이 어디서 나는지 모른다.
            "retried_empty": retried,
        })

    if parsed:
        save_processed(state)

    return {
        "ok": True,
        "source": source,
        "reports_seen": len(reports),
        "skipped_existing": skipped,
        "parsed": parsed,
        "inserted": inserted,
        "failed": failed,
        "processed": processed,
        "note": (
            "이미 처리한 회차는 PDF를 열지 않는다 — 표 추출이 회차당 VLM 4회 호출이라 "
            "매일 확인해도 새 회차가 없으면 비용이 0이다. 신호가 0건으로 끝난 회차도 "
            "'시도했다'로 기록해 매일 재파싱하는 낭비를 막는다. max_new로 한 번에 "
            "파싱할 회차 수를 묶어 첫 실행 때 호출량이 튀는 걸 막는다."
        ),
    }
