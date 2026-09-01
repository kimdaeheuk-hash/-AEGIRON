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
_POLAR_TREND = {
    "ko": "{phrase}.", "en": "It is {phrase}.", "fr": "Il est {phrase}.",
}
_POLAR_BASE = {
    "ko": "{period} 기준 {phrase}.",
    "en": "For {period}, {phrase}.",
    "fr": "Pour {period}, {phrase}.",
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
    # ★ 평년 대비를 붙인다 (2026-09-01) ★ "해빙 30일" 만으로는 많은 건지 적은
    # 건지 알 수 없다. 그리고 이건 **우리가 잰 값**이지 인용이 아니다.
    # 자료가 모자라면 아무 말도 붙이지 않는다 — 억지로 채우지 않는다.
    from .polar_baseline import describe as _describe
    from .polar_trend import describe as _describe_trend
    base = top.get("baseline") or {}
    if base.get("available"):
        phrase = _describe(base.get("anomaly_c"), lang)
        if phrase:
            lead += " " + _pick(_POLAR_BASE, lang).format(
                period=base.get("reference_period"), phrase=phrase)
    # ★ 추세는 기준선과 다른 말이다 ★ 한 해가 튄 것과 몇 년째 오르는 것은
    # 다르고, 실제로 여섯 곳 중 둘은 평년보다 더웠지만 추세는 평평했다.
    trend_phrase = _describe_trend(top.get("trend"), lang)
    if trend_phrase:
        lead += " " + _pick(_POLAR_TREND, lang).format(phrase=trend_phrase)

    rows = []
    for r in ranked:
        t = r.get("thaw") or {}
        rows.append({
            "name": _pick(_REGION_NAME.get(r.get("region"), {"ko": r.get("name") or "?"}), lang),
            "pressure": round(float(t.get("permafrost_thaw_pressure") or 0.0), 1),
            "thaw_days_30d": int(t.get("thaw_days_30d") or 0),
            "heat_trend_c": round(float(t.get("heat_trend_c") or 0.0), 1),
            # 자료가 없으면 None 이다 — 0 으로 채우면 '평년과 같음' 으로 읽힌다.
            "anomaly_c": (r.get("baseline") or {}).get("anomaly_c")
                         if (r.get("baseline") or {}).get("available") else None,
            # 판정 못 했으면 None. 0 으로 채우면 '변화 없음' 으로 읽힌다.
            "trend_c_per_decade": (r.get("trend") or {}).get("slope_c_per_decade")
                                  if (r.get("trend") or {}).get("available") else None,
            "trend_direction": (r.get("trend") or {}).get("direction")
                               if (r.get("trend") or {}).get("available") else None,
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


_SILENCE_HONESTY = {
    "ko": "‘과거 평균의 50% 미만’은 경험 규칙이지 검증된 임계값이 아닙니다. 급감이 곧 "
          "보고 체계 붕괴는 아니며 계절성·휴일·소스 개편으로도 생깁니다. 실제로 계절성 "
          "질환(브라질 뎅기)·희소 표본(OpenSky 항공)·평균이 2 미만인 SNS 지표는 오탐이 "
          "잦아 이 스캔에서 제외했습니다. 여기 뜬 항목은 ‘확인해볼 것’이지 ‘무너졌다’가 "
          "아닙니다.",
    "en": "The ‘below 50% of the historical average’ line is a rule of thumb, not a validated "
          "threshold. A drop is not proof of reporting collapse — seasonality, holidays and "
          "source changes cause it too. Seasonal series (Brazil dengue), sparse samples "
          "(OpenSky flights) and social metrics averaging under 2 were excluded because they "
          "produced frequent false positives. Items here are worth checking, not conclusions.",
    "fr": "Le seuil « sous 50 % de la moyenne » est une règle empirique, non un seuil validé. "
          "Une baisse ne prouve pas l’effondrement du signalement — saisonnalité, jours fériés "
          "et changements de source la provoquent aussi. Les séries saisonnières (dengue au "
          "Brésil), les échantillons rares (vols OpenSky) et les indicateurs sociaux de moyenne "
          "inférieure à 2 ont été exclus pour cause de faux positifs fréquents.",
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
        "honesty": _pick(_SILENCE_HONESTY, lang),
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

# ─── 🌊 재난 뒤 감시창 ───────────────────────────────────────────────────────
#
# 이 층이 브리핑에 없던 것이 이상했다(2026-09-01). 지금 네팔·인도·중국에 창이
# 13개 열려 있고 전부 빙하 산맥 지역인데, 브리핑을 보는 사람은 그걸 몰랐다.
#
# ★ 이건 예측이 아니다 ★ "재난이 났으니 이 병이 온다" 가 아니라 "이 기간에
# 이 병 보도가 뜨면 우연으로 넘기지 말라" 는 뜻이다. 문구가 그렇게 읽히게 쓴다.

_DW_TITLE = {
    "ko": "재난 뒤 감시창", "en": "Post-disaster watch", "fr": "Veille post-catastrophe",
}
_DW_LEAD = {
    "ko": "{n}개국에 감시창 {w}개가 열려 있습니다. "
          "가장 오래된 것은 {top_country} — {top_disaster} 발생 {top_days}일째입니다.",
    "en": "{w} watch windows are open across {n} countries. "
          "The oldest is {top_country} — day {top_days} after {top_disaster}.",
    "fr": "{w} fenêtres de veille sont ouvertes dans {n} pays. "
          "La plus ancienne : {top_country}, {top_days}e jour après {top_disaster}.",
}
_DW_GLACIER = {
    "ko": "이 가운데 {g}개국이 빙하 산맥 지역입니다. 빙하 기원 홍수는 비 없이 "
          "갑자기 오고 고산 오지를 쳐서, 발병 보고가 느립니다.",
    "en": "{g} of these are glaciated mountain regions. Glacier-origin floods arrive "
          "suddenly without rain and strike remote high-altitude areas, so outbreak "
          "reporting is slower.",
    "fr": "{g} d'entre eux sont des régions de montagne englacée. Les crues d'origine "
          "glaciaire surviennent sans pluie et frappent des zones reculées : "
          "le signalement des épidémies y est plus lent.",
}
_DW_OFF = {
    "ko": "창 밖 신호 {o}건 — 감시창이 열린 나라인데 창 안 질병이 아닌 것이 잡혔습니다.",
    "en": "{o} off-window signals — in watched countries, but not the diseases the window expects.",
    "fr": "{o} signaux hors fenêtre — dans des pays surveillés, mais pas les maladies attendues.",
}
_DW_HONESTY = {
    "ko": "감시창은 예측이 아닙니다. '이 기간에 이 질병 보도가 뜨면 우연으로 넘기지 "
          "말라'는 뜻이며, 잠복 구간은 문헌 기반 추정이고 이 시스템 데이터로 보정하지 "
          "않았습니다. 빙하 표시는 그 나라에 빙하 산맥이 있다는 지리적 사실이지 "
          "'빙하 때문'이라는 원인 규명이 아닙니다.",
    "en": "A watch window is not a forecast. It means 'if this disease is reported in this "
          "period, do not dismiss it as coincidence.' Incubation ranges are from literature, "
          "not calibrated on our own data. The glacier tag is a geographic fact about the "
          "country, not a finding that the flood was glacier-caused.",
    "fr": "Une fenêtre de veille n'est pas une prévision. Les plages d'incubation viennent "
          "de la littérature et ne sont pas calibrées sur nos données. Le marqueur glaciaire "
          "est un fait géographique, non une attribution de cause.",
}
# GDACS 재해코드 → 사람이 읽는 말. 영어판에 "day 32 after FL" 이 나가면
# 읽는 사람이 FL 을 모른다 — 코드는 우리 내부 표기지 독자의 말이 아니다.
_DISASTER_NAME = {
    "FL": {"ko": "홍수", "en": "flooding", "fr": "inondation"},
    "EQ": {"ko": "지진", "en": "an earthquake", "fr": "un séisme"},
    "TC": {"ko": "열대저기압", "en": "a tropical cyclone", "fr": "un cyclone tropical"},
    "TS": {"ko": "쓰나미", "en": "a tsunami", "fr": "un tsunami"},
    "VO": {"ko": "화산 분화", "en": "a volcanic eruption", "fr": "une éruption volcanique"},
    "DR": {"ko": "가뭄", "en": "drought", "fr": "la sécheresse"},
}


def _disaster_name(code: str | None, lang: str) -> str:
    """모르는 코드는 그대로 둔다 — 지어내지 않는다."""
    return _pick(_DISASTER_NAME.get(code or "", {"ko": code or "?"}), lang)


def build_disaster_watch_section(lang: str = "ko") -> dict | None:
    """재난 뒤 감시창. 열린 창이 없으면 할 말이 없으므로 None."""
    from .disaster_watch import disaster_watch_report

    data = disaster_watch_report() or {}
    countries = [c for c in (data.get("countries") or []) if isinstance(c, dict)]
    if not countries:
        return None

    total_windows = sum(c.get("window_count") or 0 for c in countries)
    if total_windows == 0:
        return None

    # 가장 오래된 창 = 재난 후 가장 많은 날이 지난 것. 시간이 갈수록 창이 닫히므로
    # "아직 열려 있는데 오래됐다" 가 가장 주의를 끄는 항목이다.
    oldest = max(
        (w for c in countries for w in (c.get("open_windows") or [])),
        key=lambda w: w.get("days_since_disaster") or 0,
        default=None,
    )
    if not oldest:
        return None

    glacier_countries = [c for c in countries if c.get("glacier")]
    lead = _pick(_DW_LEAD, lang).format(
        n=len(countries), w=total_windows,
        top_country=oldest.get("country") or "?",
        top_disaster=_disaster_name(oldest.get("disaster_type"), lang),
        top_days=oldest.get("days_since_disaster") or 0,
    )
    if glacier_countries:
        lead += " " + _pick(_DW_GLACIER, lang).format(g=len(glacier_countries))

    rows = []
    for c in sorted(countries, key=lambda x: -(x.get("window_count") or 0)):
        g = c.get("glacier")
        rows.append({
            "country": c.get("country") or c.get("country_iso3"),
            "country_iso3": c.get("country_iso3"),
            "window_count": c.get("window_count"),
            "diseases": c.get("diseases") or [],
            # 빙하 산맥이 없는 나라는 None 이다 — 빈 값으로 채우지 않는다.
            "glacier_ranges": g["ranges"] if g else None,
            "glacier_tier": g["exposure_tier"] if g else None,
        })

    citations = [
        w.get("title") for c in countries for w in (c.get("open_windows") or [])
        if w.get("title")
    ]
    seen, uniq = set(), []
    for t in citations:
        if t not in seen:
            seen.add(t)
            uniq.append(t)

    return {
        "id": "disaster_watch",
        "icon": "🌊",
        "title": _pick(_DW_TITLE, lang),
        "lead": lead,
        "why": None,
        "rows": rows,
        "citations": uniq[:4],
        "grade": "watch",
        "honesty": _pick(_DW_HONESTY, lang),
        "data_source": data.get("data_source"),
    }


_BUILDERS = (
    ("silence", build_silence_section),          # 조용해진 곳이 제일 앞 — 아무도 안 보는 각도
    ("disaster_watch", build_disaster_watch_section),   # 지금 열려 있는 창 — 가장 현재형이다
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
