"""일일 브리핑 특수 섹션 — 이미 계산하고 있는데 브리핑이 안 쓰던 것들.

★ 왜 이 파일이 생겼나 (2026-08-26) ★
`algorithms/` 에 모듈이 84개인데 `daily_brief.py` 가 import 하는 건 4개뿐이었다
(`name_i18n`·`event_dedup`·`country_risk`·`anthropic`). 나머지 80개가 계산한 것을
브리핑이 **하나도 쓰지 않았다.** 그 결과 7일 연속으로 헤드라인이 똑같았다:

    8/24 현장 리포트  : 한국 오즈 바이러스 신호 주시
    8/23 심층 분석    : 한국 오즈 바이러스 신호 주시   (연속 유사도 88~89%)
    ...

바뀌는 건 포맷 이름뿐이었다. 캡틴의 말: *"나라도 텔레그램 이거 안 보게 되는데."*

여기 붙인 층들은 **매일 값이 달라진다** — 해빙 압력도, 조용해진 채널도,
7일 예보도, 설명 불가 신호 수도. 그리고 무엇보다 **다른 곳이 안 하는 이야기다.**

★ 지키는 선 ★
1. **없으면 안 만든다.** 각 빌더는 할 말이 없으면 `None` 을 돌려주고, 그 칸은
   브리핑에서 통째로 빠진다. 빈 칸을 그럴듯한 문장으로 채우지 않는다.
2. **정직성 경계선을 함께 싣는다.** 각 모듈이 자기 주석에 적어둔 한계
   (관찰 vs 경보, 측정 vs 추정)를 `honesty` 필드로 그대로 가져온다.
   이게 빠지면 "AI가 예측했다"고 말하는 흔한 대시보드와 같아진다.
3. **한 층이 죽어도 브리핑은 나간다.** 각 빌더를 개별로 감싸서, 하나가 터져도
   나머지 칸과 기존 브리핑은 그대로 만들어진다.
"""
from __future__ import annotations

import datetime as dt

# ─── 언어 ────────────────────────────────────────────────────────────────────

SUPPORTED = ("ko", "en", "fr")


def _pick(bundle: dict, lang: str) -> str:
    return bundle.get(lang) or bundle.get("en") or bundle["ko"]


# 극지 지역명 — polar_signals 는 한국어 이름만 준다. 영어/프랑스어 브리핑에
# 한국어가 섞이지 않게 여기서 갈아끼운다(지역 집합이 고정 6개라 표로 충분하다).
_REGION_NAME = {
    "siberia_yamal": {"ko": "시베리아 야말(러시아)", "en": "Yamal, Siberia (Russia)",
                      "fr": "Yamal, Sibérie (Russie)"},
    "alaska_north": {"ko": "알래스카 노스슬로프(미국)", "en": "North Slope, Alaska (USA)",
                     "fr": "North Slope, Alaska (É.-U.)"},
    "canada_arctic": {"ko": "캐나다 북극권", "en": "Canadian Arctic", "fr": "Arctique canadien"},
    "greenland": {"ko": "그린란드", "en": "Greenland", "fr": "Groenland"},
    "antarctic_peninsula": {"ko": "남극 반도", "en": "Antarctic Peninsula",
                            "fr": "Péninsule Antarctique"},
    "svalbard": {"ko": "스발바르(노르웨이)", "en": "Svalbard (Norway)", "fr": "Svalbard (Norvège)"},
}


# ─── 뉴스 제목 청소 ──────────────────────────────────────────────────────────

def clean_news_titles(titles: list | None) -> list[str]:
    """Google News RSS 가 돌려주는 쓰레기 제목을 걸러낸다.

    실측(2026-08-26) 응답:
        [0] '"сибирская язва OR падёж оленей OR вечная мерзлота OR ..." - Google Новости'
        [1] 'Google Новости'
        [2] 'Ancient viruses are being awakened by melting permafrost - BBC Science Focus'

    앞 두 개는 **우리가 던진 검색어와 피드 이름**이 제목 자리에 돌아온 것이다.
    그대로 브리핑에 실으면 고장난 것처럼 보인다. 진짜 기사는 [2]부터다.
    """
    out: list[str] = []
    for raw in titles or []:
        if not isinstance(raw, str):
            continue
        t = raw.strip()
        if not t:
            continue
        # 검색어가 그대로 돌아온 것 — OR 로 이어붙인 키워드 나열
        if " OR " in t:
            continue
        # 피드 이름만 있는 껍데기
        if t.lower().startswith("google ") or t.lower() in {"google news", "google новости"}:
            continue
        out.append(t)
    return out


# ─── 🧊 극지·영구동토 ────────────────────────────────────────────────────────

_POLAR_TITLE = {
    "ko": "극지 감시", "en": "Polar watch", "fr": "Veille polaire",
}
_POLAR_LEAD = {
    "ko": "{name}의 지난 30일 중 {thaw}일이 해빙일이었습니다. "
          "기온 추세 {heat:+.1f}℃, 영구동토 해빙 압력 {pressure:.1f}로 관측 {n}개 지역 중 가장 높습니다.",
    "en": "{thaw} of the last 30 days were thaw days in {name}. "
          "Heat trend {heat:+.1f}℃, permafrost thaw pressure {pressure:.1f} — highest of {n} monitored regions.",
    "fr": "{thaw} des 30 derniers jours ont été des jours de dégel à {name}. "
          "Tendance thermique {heat:+.1f}℃, pression de dégel {pressure:.1f} — la plus élevée des {n} régions.",
}
_POLAR_WHY = {
    "ko": "2016년 이 지역에서 탄저가 재출현했습니다. 75년 전 죽은 순록 사체가 녹으면서 "
          "포자가 다시 노출된 것으로 조사됐습니다.",
    "en": "Anthrax re-emerged here in 2016 — spores from reindeer carcasses buried 75 years "
          "earlier were exposed as the ground thawed.",
    "fr": "L’anthrax a resurgi ici en 2016 — des spores de carcasses de rennes enfouies 75 ans "
          "plus tôt ont été exposées par le dégel.",
}


def build_polar_section(lang: str = "ko") -> dict | None:
    """극지 관찰 층. 해빙 압력이 0 인 날(전부 얼어 있음)엔 할 말이 없으므로 None."""
    from .polar_signals import polar_watch_all

    data = polar_watch_all() or {}
    regions = [r for r in (data.get("regions") or []) if isinstance(r, dict)]
    if not regions:
        return None

    def pressure(r):
        return float((r.get("thaw") or {}).get("permafrost_thaw_pressure") or 0.0)

    ranked = sorted(regions, key=pressure, reverse=True)
    top = ranked[0]
    if pressure(top) <= 0:
        # 전 지역이 얼어 있다 — 관찰할 해빙이 없다. 억지로 쓰지 않는다.
        return None

    thaw = top.get("thaw") or {}
    rid = top.get("region")
    name = _pick(_REGION_NAME.get(rid, {"ko": top.get("name") or "?"}), lang)

    lead = _pick(_POLAR_LEAD, lang).format(
        name=name,
        thaw=int(thaw.get("thaw_days_30d") or 0),
        heat=float(thaw.get("heat_trend_c") or 0.0),
        pressure=pressure(top),
        n=len(regions),
    )

    rows = []
    for r in ranked:
        t = r.get("thaw") or {}
        rows.append({
            "name": _pick(_REGION_NAME.get(r.get("region"), {"ko": r.get("name") or "?"}), lang),
            "pressure": round(float(t.get("permafrost_thaw_pressure") or 0.0), 1),
            "thaw_days_30d": int(t.get("thaw_days_30d") or 0),
            "heat_trend_c": round(float(t.get("heat_trend_c") or 0.0), 1),
        })

    # 실제 기사 제목만. 검색어·피드이름은 clean_news_titles 가 걸러낸다.
    citations: list[str] = []
    for r in ranked:
        citations.extend(clean_news_titles((r.get("news") or {}).get("sample_titles")))
    seen, uniq = set(), []
    for c in citations:
        if c not in seen:
            seen.add(c)
            uniq.append(c)

    honesty = " ".join(x for x in (data.get("note"), data.get("disclaimer")) if x)
    return {
        "id": "polar",
        "icon": "🧊",
        "title": _pick(_POLAR_TITLE, lang),
        "lead": lead,
        "why": _pick(_POLAR_WHY, lang) if rid == "siberia_yamal" else None,
        "rows": rows,
        "citations": uniq[:4],
        "grade": data.get("grade"),
        "honesty": honesty or None,
        "data_source": data.get("data_source"),
    }


# ─── 🔇 조용해진 곳 ──────────────────────────────────────────────────────────

_SILENCE_TITLE = {
    "ko": "조용해진 곳", "en": "Gone quiet", "fr": "Devenu silencieux",
}
_SILENCE_LEAD = {
    "ko": "{n}개 지표 중 {k}개가 과거 평균의 절반 아래로 떨어졌습니다.",
    "en": "{k} of {n} tracked metrics fell below half their historical average.",
    "fr": "{k} des {n} indicateurs suivis sont tombés sous la moitié de leur moyenne.",
}
_SILENCE_WHY = {
    "ko": "신호가 늘어나는 것만 위험한 게 아닙니다. 2014년 기니에서는 보건부 보고가 "
          "줄어든 것을 '조용하다'고 읽었고, 실제로는 의료체계가 무너지는 중이었습니다. "
          "몇 주 뒤 에볼라가 폭발했습니다.",
    "en": "Rising signals are not the only danger. In Guinea in 2014 a drop in ministry "
          "reporting was read as calm; the health system was in fact collapsing. Ebola "
          "exploded weeks later.",
    "fr": "Une hausse des signaux n’est pas le seul danger. En Guinée en 2014, la baisse des "
          "rapports du ministère fut prise pour du calme ; le système s’effondrait. "
          "Ebola a explosé des semaines plus tard.",
}


def build_silence_section(lang: str = "ko") -> dict | None:
    """급감한 신호원. 하나도 없으면 None — '조용한 곳이 없습니다'는 뉴스가 아니다."""
    from .negative_space import scan_negative_space

    data = scan_negative_space() or {}
    alerts = [a for a in (data.get("alerts") or []) if isinstance(a, dict)]
    if not alerts:
        return None

    rows = []
    for a in alerts:
        rows.append({
            "metric": a.get("metric"),
            "label": metric_label(a.get("metric"), lang),
            "layer": a.get("label") or a.get("layer"),
            "latest": a.get("latest"),
            "history_avg": a.get("history_avg"),
            "drop_ratio": a.get("drop_ratio"),
            "message": a.get("message"),
        })

    return {
        "id": "silence",
        "icon": "🔇",
        "title": _pick(_SILENCE_TITLE, lang),
        "lead": _pick(_SILENCE_LEAD, lang).format(
            n=data.get("metrics_checked") or 0, k=len(alerts)),
        "why": _pick(_SILENCE_WHY, lang),
        "rows": rows,
        "honesty": None,   # 이 층은 값 자체가 실측(과거평균 대비 비율)이라 별도 단서가 없다
    }


# 지표 식별자를 사람이 읽는 말로. **모르는 지표는 원래 이름 그대로 둔다** —
# 억지로 번역해서 뜻이 틀어지는 것보다 영어 식별자가 낫다.
_METRIC_LABEL = {
    "africa_cdc_confirmed": {"ko": "아프리카 CDC 확진", "en": "Africa CDC confirmed",
                             "fr": "Afrique CDC confirmés"},
    "africa_cdc_deaths": {"ko": "아프리카 CDC 사망", "en": "Africa CDC deaths",
                          "fr": "Afrique CDC décès"},
    "who_afro_items": {"ko": "WHO 아프리카 보고", "en": "WHO AFRO items", "fr": "OMS AFRO"},
    "infodengue_casos_total": {"ko": "브라질 뎅기 환자", "en": "Brazil dengue cases",
                               "fr": "Dengue Brésil"},
    "kdca_weekly": {"ko": "국내 법정감염병 주간", "en": "KDCA weekly", "fr": "KDCA hebdo"},
    "naver_ebola_ratio": {"ko": "네이버 에볼라 검색", "en": "Naver ebola searches",
                          "fr": "Recherches ebola Naver"},
    "social_mpox": {"ko": "SNS 엠폭스 언급", "en": "Social mpox mentions",
                    "fr": "Mentions mpox"},
    "social_birdflu": {"ko": "SNS 조류독감 언급", "en": "Social bird flu mentions",
                       "fr": "Mentions grippe aviaire"},
}


def metric_label(metric: str | None, lang: str = "ko") -> str:
    """지표 식별자 → 사람이 읽는 이름. 모르면 원래 이름 그대로."""
    if not metric:
        return "?"
    entry = _METRIC_LABEL.get(metric)
    return _pick(entry, lang) if entry else metric


# ─── 🔮 7·14일 예보 ─────────────────────────────────────────────────────────

_FORECAST_TITLE = {
    "ko": "7·14일 예보", "en": "7- and 14-day outlook", "fr": "Prévision à 7 et 14 jours",
}
_FORECAST_LEAD = {
    "ko": "7일 후 위험도 {s7}({t7}), 14일 후 {s14}({t14}). 신뢰도 {conf}.",
    "en": "Risk {s7} ({t7}) in 7 days, {s14} ({t14}) in 14. Confidence {conf}.",
    "fr": "Risque {s7} ({t7}) à 7 jours, {s14} ({t14}) à 14. Confiance {conf}.",
}
_FORECAST_HONESTY = {
    "ko": "선형회귀와 지수평활의 앙상블 추정입니다. 측정된 발병 수가 아니라 "
          "신호 시계열의 외삽이며, 아직 적중률 트랙레코드가 쌓이는 중입니다.",
    "en": "An ensemble of linear regression and exponential smoothing. This extrapolates "
          "signal time series — it is not a measured case count, and the accuracy track "
          "record is still accumulating.",
    "fr": "Un ensemble de régression linéaire et de lissage exponentiel. Il s’agit d’une "
          "extrapolation de séries de signaux, non d’un comptage mesuré ; l’historique de "
          "précision est encore en constitution.",
}


def build_forecast_section(lang: str = "ko") -> dict | None:
    """7·14일 예보 + **사람 수가 실린 지표**를 앞세운다.

    지금 브리핑에는 사람 숫자가 하나도 없다("오즈 바이러스 · 한국 · 관찰").
    `africa_cdc_confirmed`·`africa_cdc_deaths` 처럼 사람을 세는 지표가 있으면
    그것부터 보여준다 — 우리 순위표가 아니라 사람 이야기여야 한다.
    """
    from .forecast_engine import forecast_summary

    data = forecast_summary() or {}
    s7, s14 = data.get("score_7d"), data.get("score_14d")
    if s7 is None and s14 is None:
        return None

    # 사람 수를 세는 지표를 앞으로
    human_first = ("confirmed", "deaths", "cases")
    alerts = [a for a in (data.get("top_alerts") or []) if isinstance(a, dict)]
    alerts.sort(key=lambda a: (
        0 if any(w in str(a.get("metric", "")) for w in human_first) else 1))

    rows = []
    for a in alerts[:5]:
        f7 = a.get("forecast_7d") or {}
        f14 = a.get("forecast_14d") or {}
        rows.append({
            "metric": a.get("metric"),
            "label": metric_label(a.get("metric"), lang),
            "layer": a.get("layer"),
            "current": a.get("current_val"),
            "in_7d": f7.get("val"),
            "in_14d": f14.get("val"),
            "counts_people": any(w in str(a.get("metric", "")) for w in human_first),
        })

    return {
        "id": "forecast",
        "icon": "🔮",
        "title": _pick(_FORECAST_TITLE, lang),
        "lead": _pick(_FORECAST_LEAD, lang).format(
            s7=s7, t7=data.get("tier_7d"), s14=s14, t14=data.get("tier_14d"),
            conf=data.get("confidence")),
        "why": None,
        "rows": rows,
        "honesty": _pick(_FORECAST_HONESTY, lang),
        "score_model": data.get("score_model"),
    }


# ─── ❓ 설명 불가 신호 ───────────────────────────────────────────────────────

_UNEXPLAINED_TITLE = {
    "ko": "설명 불가 신호", "en": "Unexplained signals", "fr": "Signaux inexpliqués",
}
_UNEXPLAINED_LEAD = {
    "ko": "알려진 질병 어느 것과도 맞지 않는 신호 {k}건이 추적 중입니다.",
    "en": "{k} signals under watch match no known disease pattern.",
    "fr": "{k} signaux suivis ne correspondent à aucune maladie connue.",
}


def build_unexplained_section(lang: str = "ko", limit: int = 4) -> dict | None:
    """알려진 질병에 안 걸리는 신호. 감시에서 가장 뉴스 가치가 높은 부류다."""
    from .unexplained import scan_unexplained

    data = scan_unexplained() or {}
    alerts = [a for a in (data.get("alerts") or []) if isinstance(a, dict)]
    if not alerts:
        return None

    def when(a):
        return str(a.get("signal_date") or a.get("extracted_at") or "")

    alerts.sort(key=when, reverse=True)

    rows = []
    for a in alerts[:limit]:
        rows.append({
            "source": a.get("source"),
            "location": a.get("location"),
            "signal_date": a.get("signal_date"),
            "tier": a.get("tier"),
            "message": (a.get("message") or "")[:160] or None,
        })

    return {
        "id": "unexplained",
        "icon": "❓",
        "title": _pick(_UNEXPLAINED_TITLE, lang),
        "lead": _pick(_UNEXPLAINED_LEAD, lang).format(k=len(alerts)),
        "why": None,
        "rows": rows,
        "honesty": data.get("caveat"),
    }


# ─── 조립 ────────────────────────────────────────────────────────────────────

_BUILDERS = (
    ("silence", build_silence_section),          # 조용해진 곳이 제일 앞 — 아무도 안 보는 각도
    ("polar", build_polar_section),
    ("forecast", build_forecast_section),
    ("unexplained", build_unexplained_section),
)


def build_special_sections(lang: str = "ko", on_error=None) -> list[dict]:
    """특수 섹션을 모아 온다. **한 층이 죽어도 나머지는 나간다.**

    브리핑은 매일 나가야 하는 것이라, 층 하나가 외부 API 때문에 터졌다고
    브리핑 전체가 빠지면 안 된다. 대신 조용히 삼키지 않고 on_error 로 넘긴다.
    """
    lang = lang if lang in SUPPORTED else "ko"
    out = []
    for name, builder in _BUILDERS:
        try:
            section = builder(lang)
        except Exception as e:            # noqa: BLE001 — 한 층의 실패가 브리핑을 막지 않는다
            if on_error:
                on_error(name, e)
            continue
        if section:
            out.append(section)
    return out
