"""아이기론 · 무인 신호 수집기 (스케줄러 전용)
==========================================
개편(2026-11-22) 뒤 남은 층은 셋이다 — 극지(감지) → 헤임달(식별) → 발할라(대응).
나머지 소스(국내외 감염병 통계·뉴스·위키·SNS·무역·재난 등)는 지웠다.
복원이 필요하면 커밋 83406e4 에서 `git checkout 83406e4 -- <경로>`.

실행: python collector.py   (매시 스케줄러가 부른다)
키는 환경변수로만 주입한다. 하드코딩된 키 없음.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
LOG_FILE = DATA_DIR / "signals_log.jsonl"
ERR_FILE = DATA_DIR / "error_log.txt"


def log(msg: str) -> None:
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}")


def log_error(context: str, e: Exception) -> None:
    """에러를 파일에 남기고 **stdout에도 반드시 찍는다**.

    예전엔 파일에만 썼다. 그래서 KDCA가 나흘·93회 연속으로 죽는 동안 Railway 배포
    로그는 완벽하게 깨끗했고, 로그를 아무리 들여다봐도 원인이 안 보였다(2026-08-13~17).
    에러가 파일 안에만 있으면 서버에 들어갈 수 있는 사람만 볼 수 있는데, 그건
    '조용한 실패'를 막겠다는 이 시스템의 설계 목적과 정면으로 어긋난다.
    """
    line = f"{dt.datetime.now().isoformat()} | {context} | {str(e)[:200]}"
    print(f"  ❌ [{context}] {type(e).__name__}: {str(e)[:200]}", flush=True)
    DATA_DIR.mkdir(exist_ok=True)
    with open(ERR_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def append_signal(record: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    record["_logged_at"] = dt.datetime.now().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# 소스 헬스가 매 주기 보는 키 — 값이 None 이면 그 주기 수집 실패로 센다.
# 맵에 없는 옛 항목은 source_health.record_cycle 이 상태 파일에서 지운다.
FREE_SOURCE_HEALTH_KEYS = {
    "PolarWatch": "polar_watch",
    "GenomicVariants": "genomic_variants",
    "Valhalla": "valhalla",
}


def polar_weather_ok(pw: dict | None) -> bool:
    """이 주기에 기상 자료가 **한 곳이라도** 있나. 자료를 살릴지 버릴지의 판정.

    ★ 왜 서식에서 떼어냈나 (2026-11-16) ★
    이 판정은 **자료의 성질**이고, 로그 줄을 만드는 일은 사람에게 보이는 일이다.
    둘이 한 함수·한 try 에 묶여 있으면 **서식 버그 하나가 다시 층 전체를 버린다** —
    11-14~15 사고가 정확히 그 모양이었다(`%.0f` ← None 이 터지자 `except` 가
    이미 받아온 8개 관측지 자료를 None 으로 덮었고, `record_cycle` 이 수집 실패로 셌다).
    그래서 호출부는 이 함수로 먼저 **정하고**, 줄을 찍는 건 그 뒤에 따로 한다.
    """
    regions = (pw or {}).get("regions") or []
    no_weather = [r for r in regions if not (r.get("thaw") or {}).get("data_available")]
    return bool(regions) and len(no_weather) < len(regions)


def polar_summary_line(pw: dict) -> tuple[str, bool]:
    """극지 관찰 요약 로그 줄과 '기상 자료가 한 곳이라도 있나'(`polar_weather_ok`).

    점수가 없는 관측지(기상·뉴스 모두 없음)는 '점수 없음'으로 적는다 — 예전엔 `%.0f` 에 None 이 들어가
    로그 줄이 TypeError 로 죽었다(2026-11-15 10:00~익일 00:00, 소스 헬스 '중단').
    """
    regions = pw.get("regions") or []
    no_weather = [r for r in regions if not (r.get("thaw") or {}).get("data_available")]
    top = sorted(regions, key=lambda r: -(r.get("polar_watch_score") or 0))[:3]

    def fmt(r: dict) -> str:
        s = r.get("polar_watch_score")
        name = str(r.get("name") or r.get("region") or "?")[:10]
        return f"{name}({'점수 없음' if s is None else f'{s:.0f}'})"

    tops = ", ".join(fmt(r) for r in top) or "없음"
    line = f"  극지 관찰: {len(regions)}개 관측지 · 등급 {pw.get('grade')} · 상위 {tops}"
    if no_weather:
        line += f" · 기상 자료 없음 {len(no_weather)}/{len(regions)}(판정 안 함)"
    return line, polar_weather_ok(pw)


def collect_free_sources() -> dict:
    log("=== 수집 시작 (극지 · 헤임달 · 발할라) ===")
    result = {"type": "free_sources", "timestamp": dt.datetime.now().isoformat()}

    # ── 극지 관찰층 (2026-09-01 수집 편입) ─────────────────────────────
    # ★ 경보가 아니라 관찰이다 ★ watch_grade=True 로 경보 파이프라인과 분리돼
    # 있다. 여기서 수집하는 이유는 울리기 위해서가 아니라 **쌓기 위해서**다 —
    # 동토 해빙은 추세가 핵심인데, 부를 때만 계산하면 매번 그 순간만 보게 된다.
    #
    # ★ 요약 줄은 수집 try 밖이다 (2026-11-16) ★
    # 2026-11-14 21시 ~ 11-15 23시에 이 층이 14주기 연속 `중단` 으로 잡혔다.
    # 에러는 `TypeError: must be real number, not NoneType` 하나였고, 터진 자리는
    # 수집이 아니라 **수집 결과를 찍는 요약 줄**이었다(`%.0f` ← score=None).
    # 그런데 `except` 가 `result["polar_watch"] = None` 으로 덮어써서,
    # **이미 성공적으로 받아온 8개 관측지 자료가 매 주기 버려졌다.**
    # `record_cycle` 은 이 키가 None 이면 수집 실패로 세므로 소스까지 죽었다.
    #
    # 자료를 받아왔는가와 그걸 사람이 읽게 찍는 데 성공했는가는 **다른 사건**이다.
    # 그래서 수집만 try 에 두고, 요약은 else 에서 따로 감싼다. 요약이 실패해도
    # 자료는 남고 `log_error` 도 부르지 않는다 — 소스 헬스는 수집의 성패를
    # 말하는 자리이지 서식 버그를 말하는 자리가 아니다.
    try:
        from algorithms.polar_signals import polar_watch_all
        pw = polar_watch_all()
    except Exception as e:
        result["polar_watch"] = None
        log(f"  ❌ 극지 관찰 실패: {type(e).__name__}: {e}")
        log_error("PolarWatch", e)
    else:
        # ⓪ 계산한 값을 응답 캐시에 넣는다(2026-11-18) — 관측값 저장·API 가 같은 자료를
        #    Open-Meteo 에서 또 받지 않게. 기상 자료가 빈 결과도 넣는다: 방문자가 다시
        #    두드려 남은 한도를 쓰게 하지 않고, 화면은 '판정 안 함'을 그대로 보여 준다.
        try:
            from algorithms import response_cache
            from algorithms.polar_signals import POLAR_CACHE_KEY
            response_cache.put(POLAR_CACHE_KEY, pw)
        except Exception as e:
            log(f"  ⚠ 극지 관찰 응답 캐시 저장 실패(수집은 유지): {type(e).__name__}: {e}")
        # ① 먼저 **자료로** 정한다. 8곳 모두 기상 자료가 없으면 이 주기엔 측정이
        #    없는 것이라 소스 헬스가 보게 None 으로 둔다(#124). 일부만 없으면 살린다.
        weather_ok = polar_weather_ok(pw)
        result["polar_watch"] = pw if weather_ok else None
        # ② 그 다음에 찍는다. 찍다가 터져도 ①의 판정은 이미 끝났으므로 자료가
        #    안 날아간다. `log_error` 도 부르지 않는다 — 소스 헬스는 수집의 성패를
        #    말하는 자리이지 서식 버그를 말하는 자리가 아니다.
        try:
            log(polar_summary_line(pw)[0])
        except Exception as e:
            # else 블록의 예외는 위 except 가 못 잡는다 — 여기서 막지 않으면
            # 주기 전체가 죽는다(수집은 이미 끝났는데).
            log(f"  ⚠ 극지 관찰 요약 줄 생성 실패(자료는 보존): {type(e).__name__}: {e}")
        if not weather_ok:
            log("  ❌ 극지 관찰: 모든 관측지 기상 자료 없음 — 이 주기 측정 없음(소스 헬스 실패로 셈)")
    # Open-Meteo 실패 사유(2026-11-18) — 한도(429)인지 장애인지 로그로 갈리게.
    try:
        from algorithms.climate_signals import failure_reasons_line, pop_failure_reasons
        reasons_line = failure_reasons_line(pop_failure_reasons())
        if reasons_line:
            log(reasons_line)
    except Exception as e:
        log(f"  ⚠ Open-Meteo 실패 사유 집계 실패: {type(e).__name__}: {e}")

    # ── 헤임달: 공개 시퀀스 계통 추적 ─────────────────────────────────
    try:
        from algorithms.genomic_variants import get_genomic_variant_signals
        result["genomic_variants"] = get_genomic_variant_signals()
        for slug, v in result["genomic_variants"].items():
            if not v.get("available"):
                log(f"  ⏭ Nextstrain {v['label']}: {v.get('reason')}")
                continue
            if v.get("dominant_share") is None:
                log(f"  ⏭ Nextstrain {v['label']}: {v.get('note') or '최근 구간 데이터 없음'}")
                continue
            new_tag = f" 🆕신규계통{v['new_clade_count']}건" if v.get("new_clade_count") else ""
            log(f"  Nextstrain {v['label']}: 우세계통 {v['dominant_clade']}"
                f"({v['dominant_share']*100:.0f}%, n={v['n_recent_sequences']}){new_tag}")
    except Exception as e:
        result["genomic_variants"] = None
        log_error("GenomicVariants", e)

    # ★ 변이원장 (2026-11-03) ★ 이번 주기 변이 스냅샷을 원장에 적고 전이만
    # 로그에 남긴다. 원장 실패가 수집을 깨면 안 되므로 별도 try.
    if result.get("genomic_variants"):
        try:
            from algorithms.variant_ledger import record_cycle
            for _entry in record_cycle(result["genomic_variants"]):
                if _entry["transition"] == "dominant_changed":
                    log(f"  🧬 변이원장 {_entry['label']}: 우세 "
                        f"{_entry['prev_dominant']}→{_entry['dominant_clade']}")
                elif _entry["transition"] == "new_clade":
                    log(f"  🧬 변이원장 {_entry['label']}: "
                        f"신규계통 {','.join(_entry['new_clades'])}")
        except Exception as e:
            log_error("VariantLedger", e)

    # ★ 매칭원장 (2026-11-03) ★ 오늘의 위협×비축×변이 판정 1행/위협.
    # 실데이터(등록 비축)만 기록 — 예시로 원장을 채우지 않는다.
    try:
        import db
        from algorithms.biodefense_readiness import DEFAULT_THREATS
        from algorithms.match_ledger import record_daily_verdict
        _stored = db.list_countermeasures()
        if _stored:
            _vers = record_daily_verdict(_stored, DEFAULT_THREATS)
            for _v in _vers:
                if _v["verdict"] in ("gap", "recheck"):
                    log(f"  🛡 매칭원장 {_v['pathogen']}: {_v['verdict']}"
                        + (f" ({_v['note']})" if _v.get("note") else ""))
    except Exception as e:
        log_error("MatchLedger", e)

    # ── 발할라 관찰층 (2026-09-03 수집 편입) ───────────────────────────
    # ★ 점검에서 드러난 것 ★ 발할라는 **부를 때만** 계산됐다. 극지층이
    # 2026-09-01 에 겪은 것과 똑같다 — 기능은 있는데 감시는 안 하고 있었다.
    # 어제 백신 공급이 어땠는지 오늘 비교할 수가 없었다.
    #
    # ★ 조각마다 주기가 다르다 ★ 준비태세·백신 공급은 로컬이라 매 주기 채우고,
    # 임상 파이프라인은 24시간마다 새로 받는다(조달은 개편 2차에서 뺐다 — 무결과 병목).
    # 그래도 `valhalla` 키는 매 주기 채워지므로 소스 헬스가 정상으로 돈다 —
    # 무거운 걸 하루 한 번만 돌리면 나머지 23주기가 값없음으로 쌓여 거짓 경보가
    # 된다(극지층 주석의 그 함정).
    try:
        from algorithms.valhalla_watch import valhalla_snapshot
        result["valhalla"] = valhalla_snapshot()
        v = result["valhalla"]
        ready = v.get("readiness") or {}
        log("  발할라: 백신 단일공급원 %s종 · 대응제 %s건%s"
            % ((v.get("vaccine_chokepoints") or {}).get("single_source_count", "?"),
               ready.get("countermeasure_count", "?"),
               " · 판정불가 %s" % ready["unrated"] if ready.get("unrated") else ""))

        # 무거운 조각이 오래 굳어 있으면 조용히 지나가지 않는다.
        # ★ 판정은 valhalla_watch.stale_parts 가 한다 ★ 여기서 직접 짜다가
        # `part.get("reason", "")` 로 터졌다(2026-09-03) — 키가 있는데 값이 None
        # 이면 .get 의 기본값이 안 먹는다.
        # ★ 준비태세를 범위별로 찍는다 (2026-09-04) ★ 예전엔 수기 등록 5건만
        # 보고 "대응제 5건" 이라고 찍었다. 국제 비축과 임상 파이프라인을 이미
        # 매일 받아오면서도 준비태세 판정에는 안 넣고 있었다.
        from algorithms.readiness_scopes import scope_summary
        scopes = scope_summary(v.get("readiness_by_scope"))
        if scopes:
            log("  발할라 준비태세: %s" % scopes)
        # 승인은 끝났는데 비축이 없는 칸을 이름까지 찍는다 — 그게 곧 '개발이
        # 아니라 조달부터 하면 되는' 목록이라 대비 우선순위를 바꾼다.
        from algorithms.approved_products import approved_summary
        appr = approved_summary(
            ((v.get("readiness_by_scope") or {}).get("scopes") or {}).get("approved_products"))
        if appr:
            log("  발할라 승인제품: %s" % appr)

        # ★ 파이프라인 결과를 찍는다 ★ 24시간마다 17개 병원체를 조회해놓고
        # 로그에 아무 값도 안 실려서, 돌고는 있는데 뭐가 나오는지 모르는
        # 층이었다(2026-09-04 점검). 굳은 값이면 나이도 같이 밝힌다.
        from algorithms.valhalla_watch import pipeline_summary
        pipe = v.get("pipeline") or {}
        summary = pipeline_summary(pipe.get("value"))
        if summary:
            age = ("갱신" if pipe.get("refreshed")
                   else "%s시간 전 값" % pipe.get("age_hours"))
            log("  발할라 파이프라인(%s): %s" % (age, summary))
            failed = (pipe.get("value") or {}).get("failed_pathogens") or []
            if failed:
                # 일부만 실패하면 예전엔 조용히 '판정불가'로 섞였다.
                log("    ⚠ 임상 조회 실패 %d종: %s — '등록 연구 없음'과 다른 상태다"
                    % (len(failed), "·".join(failed)))

        from algorithms.valhalla_watch import stale_parts
        _KO = {"pipeline": "파이프라인"}
        for key, part in stale_parts(v):
            log("  ⚠ 발할라 %s %s (%s시간 전 값 사용)"
                % (_KO.get(key, key), part["reason"], part.get("age_hours")))
        # 정적 축(백신 공급·국가 역량)이 묵었으면 매 주기 보이게 한다.
        # /api/status 에만 있으면 아무도 매시간 들여다보지 않는다.
        from algorithms.reference_snapshots import stale_lines
        for line in stale_lines(v.get("reference_snapshots")):
            log("  ⚠ 발할라 %s. 주간작업이 갱신 시도" % line)
    except Exception as e:
        result["valhalla"] = None
        log(f"  ❌ 발할라 관찰 실패: {type(e).__name__}: {e}")
        log_error("Valhalla", e)

    # 소스별 헬스 기록 — result 의 각 키가 None 이면 이번 주기 수집 실패로 판정.
    try:
        from algorithms.source_health import record_cycle, source_health_report
        record_cycle(result, FREE_SOURCE_HEALTH_KEYS)
        rep = source_health_report()
        bad = [f"{s['source']}({s['status']})" for s in rep["sources"] if s["status"] != "ok"]
        log(f"  📊 소스 건강: 정상 {len(rep['sources']) - len(bad)}/{len(rep['sources'])}"
            + (f" · {', '.join(bad)}" if bad else ""))
    except Exception as e:
        log_error("SourceHealth", e)

    append_signal(result)
    log("=== 수집 끝 ===")
    return result


def main() -> None:
    log("아이기론 수집 시작")
    try:
        collect_free_sources()
    except Exception as e:
        log_error("main", e)
        log(f"치명적 오류: {e}")
    log("아이기론 수집 종료")


if __name__ == "__main__":
    main()
