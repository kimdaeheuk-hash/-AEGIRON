/**
 * 관측 데이터 보드(/observations)가 읽는 운영 API 값 (2026-11-15).
 *
 * 분야마다 응답 모양이 다르지만 화면은 다섯 칸 하나로 통일한다:
 *   대상 · 측정값 · 해석값(추정·대리) · 기준 시각 · 비고
 * 측정값과 해석값을 다른 칸에 두는 게 핵심이다 — 같은 칸에 섞으면 추정이 측정처럼 읽힌다.
 *
 * 필드 이름은 2026-11-15 운영 스냅숏(media-capture/results, 12개 엔드포인트 모두 200)으로 맞췄다.
 * 못 읽으면 rows=null → 화면은 "읽어 오지 못함"을 쓴다(지어낸 0 이 아니라).
 * 값이 없는 칸은 비워 두지 않고 '값 없음'으로 쓴다.
 *
 * 번역: 질병명·지명·극지 지역·유전체/SNS 라벨·사건 유형은 observationNames 사전으로 en/fr 표기를 바꾼다
 * (사전에 없으면 원문). 보도 요약(raw_text)은 자유 문장이라 번역하지 않고 비고에 '한국어 원문'을 표시한다.
 */
import type { Locale } from '@/i18n';
import type { ObservationSectionKey } from '@/i18n/types';
import { diseaseName, hasHangul, labelName, placeName } from './observationNames';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';

/** 수집은 매시 돈다. 일부 분야는 요청 때 외부 API 를 부르므로 너무 자주 묻지 않는다. */
const REVALIDATE_SECONDS = 900;
/** 한 분야가 느려도 페이지 전체가 막히지 않게. */
const TIMEOUT_MS = 20_000;
/** 분야별 최대 행 수 — 표가 끝없이 길어지지 않게. 전체 건수는 따로 표시한다. */
const MAX_ROWS = 25;

export type ObservationRow = {
  id: string;
  target: string;
  measured: string;
  derived: string;
  time: string;
  note: string;
} & Record<string, unknown>;

export type ObservationSection = {
  key: ObservationSectionKey;
  /** null = 운영 서버에서 읽지 못함 */
  rows: ObservationRow[] | null;
  /** 응답에 있던 전체 건수(표에는 MAX_ROWS 까지만) */
  total: number | null;
  source: string | null;
  /** 응답에 실린 주의 문구(disclaimer/caveat/note) — 화면이 그대로 그린다 */
  caveat: string | null;
  apiPath: string;
};

type J = Record<string, unknown>;

// ── 값 문구(3개 언어) ──────────────────────────────────────────────────

type V = {
  locale: Locale;
  /** en/fr 화면에서 한국어 원문 그대로인 보도 요약에 붙이는 표시 */
  koSource: string;
  none: string;
  thawDays: (n: string) => string;
  anomaly: (n: string) => string;
  news: (n: string) => string;
  thawPressure: (n: string) => string;
  watchScore: (n: string) => string;
  weatherMissing: string;
  meanTemp: (n: string) => string;
  precip14: (n: string) => string;
  trend: (n: string) => string;
  vectorSuit: (n: string) => string;
  envPressure: (n: string) => string;
  monthlyImport: (n: string, period: string) => string;
  vsUsual: (n: string) => string;
  multiProduct: (n: string) => string;
  daysSince: (n: string) => string;
  windows: (list: string) => string;
  openWindows: (n: string) => string;
  level: (n: string) => string;
  rssItems: (n: string) => string;
  newClades: (list: string) => string;
  noNewClades: string;
  dominant: (c: string, share: string) => string;
  sequences: (n: string) => string;
  posts7d: (n: string) => string;
  vsPrev: (n: string) => string;
  capped: string;
  surge: string;
  recent: (n: string) => string;
  pastAvg: (n: string) => string;
  vsAvg: (n: string) => string;
  apiRetired: string;
  silenceChecked: (n: string) => string;
};

const VALUES: Record<Locale, V> = {
  ko: {
    locale: 'ko',
    koSource: '',
    none: '값 없음',
    thawDays: (n) => `최근 30일 중 영상 ${n}일`,
    anomaly: (n) => `10년 같은 달 평균 대비 ${n}℃`,
    news: (n) => `관련 보도 ${n}건`,
    thawPressure: (n) => `해빙 압력 ${n}`,
    watchScore: (n) => `관찰 점수 ${n}`,
    weatherMissing: '기상값 받지 못함',
    meanTemp: (n) => `평균 기온 ${n}℃`,
    precip14: (n) => `14일 강수 ${n}mm`,
    trend: (n) => `추세 ${n}℃`,
    vectorSuit: (n) => `매개체 적합도 ${n}`,
    envPressure: (n) => `환경 압력 ${n}`,
    monthlyImport: (n, p) => `${p} 수입 $${n}`,
    vsUsual: (n) => `평소 대비 ${n}배`,
    multiProduct: (n) => `${n}개 품목 동시 급증`,
    daysSince: (n) => `${n}일 경과`,
    windows: (l) => `감시창: ${l}`,
    openWindows: (n) => `열린 감시창 ${n}개`,
    level: (n) => `Level ${n}`,
    rssItems: (n) => `공식 RSS 항목 ${n}건`,
    newClades: (l) => `새 계통 ${l}`,
    noNewClades: '새 계통 없음',
    dominant: (c, s) => `우세 ${c}${s ? ` (${s})` : ''}`,
    sequences: (n) => `최근 60일 시퀀스 ${n}건`,
    posts7d: (n) => `7일 게시 ${n}건`,
    vsPrev: (n) => `직전 대비 ${n}배`,
    capped: '표본 상한에 닿음',
    surge: '급변',
    recent: (n) => `최근 ${n}`,
    pastAvg: (n) => `과거 평균 ${n}`,
    vsAvg: (n) => `평균 대비 ${n}배`,
    apiRetired: 'WAHIS API 은퇴 — 발생 건수는 판정 안 함',
    silenceChecked: (n) => `채널 ${n}개 점검 · 급감 없음`,
  },
  en: {
    locale: 'en',
    koSource: 'summary in Korean (source language)',
    none: 'No value',
    thawDays: (n) => `${n} above-zero days in last 30`,
    anomaly: (n) => `${n}℃ vs same-month 10-yr mean`,
    news: (n) => `${n} related reports`,
    thawPressure: (n) => `Thaw pressure ${n}`,
    watchScore: (n) => `Watch score ${n}`,
    weatherMissing: 'Weather values not received',
    meanTemp: (n) => `Mean temp ${n}℃`,
    precip14: (n) => `14-day rain ${n}mm`,
    trend: (n) => `Trend ${n}℃`,
    vectorSuit: (n) => `Vector suitability ${n}`,
    envPressure: (n) => `Env. pressure ${n}`,
    monthlyImport: (n, p) => `${p} imports $${n}`,
    vsUsual: (n) => `${n}× usual`,
    multiProduct: (n) => `${n} products surging together`,
    daysSince: (n) => `${n} days ago`,
    windows: (l) => `Watch windows: ${l}`,
    openWindows: (n) => `${n} open windows`,
    level: (n) => `Level ${n}`,
    rssItems: (n) => `${n} official RSS items`,
    newClades: (l) => `New lineages ${l}`,
    noNewClades: 'No new lineage',
    dominant: (c, s) => `Dominant ${c}${s ? ` (${s})` : ''}`,
    sequences: (n) => `${n} sequences, last 60 days`,
    posts7d: (n) => `${n} posts in 7 days`,
    vsPrev: (n) => `${n}× previous`,
    capped: 'Hit sample cap',
    surge: 'Sudden change',
    recent: (n) => `Latest ${n}`,
    pastAvg: (n) => `Past mean ${n}`,
    vsAvg: (n) => `${n}× mean`,
    apiRetired: 'WAHIS API retired — outbreak count not determined',
    silenceChecked: (n) => `${n} channels checked · no drop`,
  },
  fr: {
    locale: 'fr',
    koSource: 'résumé en coréen (langue source)',
    none: 'Pas de valeur',
    thawDays: (n) => `${n} jours au-dessus de zéro sur 30`,
    anomaly: (n) => `${n}℃ vs moyenne du même mois sur 10 ans`,
    news: (n) => `${n} articles liés`,
    thawPressure: (n) => `Pression de dégel ${n}`,
    watchScore: (n) => `Score de veille ${n}`,
    weatherMissing: 'Valeurs météo non reçues',
    meanTemp: (n) => `Temp. moyenne ${n}℃`,
    precip14: (n) => `Pluie 14 j ${n} mm`,
    trend: (n) => `Tendance ${n}℃`,
    vectorSuit: (n) => `Aptitude vectorielle ${n}`,
    envPressure: (n) => `Pression env. ${n}`,
    monthlyImport: (n, p) => `Importations ${p} ${n} $`,
    vsUsual: (n) => `${n}× l'habitude`,
    multiProduct: (n) => `${n} produits en hausse simultanée`,
    daysSince: (n) => `il y a ${n} jours`,
    windows: (l) => `Fenêtres : ${l}`,
    openWindows: (n) => `${n} fenêtres ouvertes`,
    level: (n) => `Niveau ${n}`,
    rssItems: (n) => `${n} éléments RSS officiels`,
    newClades: (l) => `Nouvelles lignées ${l}`,
    noNewClades: 'Aucune nouvelle lignée',
    dominant: (c, s) => `Dominante ${c}${s ? ` (${s})` : ''}`,
    sequences: (n) => `${n} séquences sur 60 jours`,
    posts7d: (n) => `${n} publications sur 7 jours`,
    vsPrev: (n) => `${n}× la précédente`,
    capped: "Plafond d'échantillon atteint",
    surge: 'Variation brusque',
    recent: (n) => `Dernière ${n}`,
    pastAvg: (n) => `Moyenne passée ${n}`,
    vsAvg: (n) => `${n}× la moyenne`,
    apiRetired: 'API WAHIS retirée — nombre de foyers non déterminé',
    silenceChecked: (n) => `${n} canaux vérifiés · aucune baisse`,
  },
};

// ── 가져오기 ───────────────────────────────────────────────────────────

async function getJson(path: string): Promise<J | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: REVALIDATE_SECONDS },
      headers: { accept: 'application/json' },
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!res.ok) return null;
    const body: unknown = await res.json();
    return body && typeof body === 'object' ? (body as J) : null;
  } catch {
    return null;
  }
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

// ── 값 다듬기 ──────────────────────────────────────────────────────────

function obj(v: unknown): J {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as J) : {};
}
function arr(v: unknown): J[] {
  return Array.isArray(v) ? v.filter((x) => x && typeof x === 'object').map((x) => x as J) : [];
}
function str(v: unknown): string | null {
  if (typeof v === 'string' && v.trim()) return v.trim();
  if (typeof v === 'number' && Number.isFinite(v)) return String(v);
  return null;
}
function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}
function fmt(v: unknown, digits = 1): string | null {
  const n = num(v);
  if (n === null) return null;
  return Number.isInteger(n) ? n.toLocaleString('en-US') : n.toFixed(digits);
}
function signed(v: unknown, digits = 1): string | null {
  const n = num(v);
  if (n === null) return null;
  return `${n > 0 ? '+' : ''}${n.toFixed(digits)}`;
}
function pct(v: unknown): string | null {
  const n = num(v);
  return n === null ? null : `${Math.round(n * 100)}%`;
}
function clip(s: string | null, n = 120): string | null {
  if (!s) return null;
  const flat = s.replace(/\s+/g, ' ').replace(/\*\*/g, '').trim();
  return flat.length > n ? `${flat.slice(0, n - 1)}…` : flat;
}
function list(v: unknown, max = 4): string | null {
  if (!Array.isArray(v) || v.length === 0) return null;
  const items = v.map(String);
  return items.length > max ? `${items.slice(0, max).join(', ')} +${items.length - max}` : items.join(', ');
}
/** 'YYYY-MM-DD HH:MM UTC' · 'YYYY-MM-DD' · RFC 1123('Tue, 10 Nov 2026 …') · 'YYYYMM' */
function when(v: unknown, none: string): string {
  const s = str(v);
  if (!s) return none;
  const iso = s.match(/^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}))?/);
  if (iso) return iso[2] ? `${iso[1]} ${iso[2]} UTC` : iso[1];
  if (/^\d{6}$/.test(s)) return `${s.slice(0, 4)}-${s.slice(4)}`;
  const t = Date.parse(s);
  if (!Number.isNaN(t)) return new Date(t).toISOString().slice(0, 10);
  return s.slice(0, 40);
}

// ── 백엔드 한국어 고정 문구(사유·출처 괄호) — en/fr 표기 ─────────────────
// 운영 스냅숏(2026-11-15)에 실제로 나온 문구만. 모르는 한국어 사유는 원문을 두고 '한국어 원문' 표시를 붙인다.
const REASON: { re: RegExp; en: string; fr: string }[] = [
  {
    re: /^FIRMS 조회 실패/,
    en: 'FIRMS query failed (network, policy block or invalid key) — no value',
    fr: 'Échec de la requête FIRMS (réseau, blocage ou clé invalide) — pas de valeur',
  },
  {
    re: /^GFW_API_KEY 미설정/,
    en: 'GFW_API_KEY not set (free key required) — no value',
    fr: 'GFW_API_KEY non défini (clé gratuite requise) — pas de valeur',
  },
  {
    re: /^FIRMS_MAP_KEY 미설정/,
    en: 'FIRMS_MAP_KEY not set (free key required) — no value',
    fr: 'FIRMS_MAP_KEY non défini (clé gratuite requise) — pas de valeur',
  },
  {
    re: /^최근 구간 시퀀스 없음/,
    en: 'No sequences in the recent window (submission may lag)',
    fr: 'Aucune séquence dans la période récente (dépôt possiblement en retard)',
  },
];

function localNote(raw: string | null, v: V): string | null {
  if (!raw || v.locale === 'ko' || !hasHangul(raw)) return raw;
  const hit = REASON.find((r) => r.re.test(raw));
  if (hit) return hit[v.locale];
  return `${raw} (${v.koSource})`;
}

/** 출처 문자열의 한국어 괄호 설명('(무료·키 불필요)')은 en/fr 에서 뺀다 — 출처 이름은 그대로. */
function localSource(raw: string | null, locale: Locale): string | null {
  if (!raw || locale === 'ko') return raw;
  return raw.replace(/\s*\([^)]*[\uac00-\ud7a3][^)]*\)/g, '').trim() || raw;
}

type Built = { rows: ObservationRow[]; total?: number };
type Builder = (b: J, v: V) => Built;

/** 붙일 값이 하나도 없으면 '값 없음'. */
function joiner(v: V) {
  return (parts: (string | null | undefined | false)[]): string => {
    const kept = parts.filter((p): p is string => typeof p === 'string' && p.length > 0);
    return kept.length ? kept.join(' · ') : v.none;
  };
}

// ── 분야별 변환 ────────────────────────────────────────────────────────

/**
 * 나라별 발생 보도 — AI 구조화 추출. 보도 요약(raw_text)은 출처가 전한 수치를 그대로 담는다.
 * 같은 사건을 같은 출처가 매일 다시 전하므로(질병·장소·출처가 같음) 최신 한 건만 남긴다 —
 * 응답은 최신순이라 처음 만난 것이 최신이다. 시각은 보도 속 사건 날짜(signal_date — PHEIC 선포일처럼
 * 몇 달 전일 수 있음)가 아니라 아이기론이 기록한 시각(extracted_at)이다.
 */
const events: Builder = (b, v) => {
  const j = joiner(v);
  const seen = new Set<string>();
  const latest = arr(b.records).filter((r) => {
    const k = [str(r.disease), str(r.location), str(r.source)].join('|');
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  const rows = latest.map((r, i) => ({
    id: `ev-${str(r.id) ?? i}`,
    target: j([
      diseaseName(str(r.disease), v.locale),
      clip(placeName(str(r.location), v.locale), 50) ?? str(r.country_iso3),
    ]),
    measured: j([clip(str(r.raw_text), 160)]),
    derived: j([labelName(str(r.signal_type), v.locale)]),
    time: when(r.extracted_at ?? r.signal_date, v.none),
    note: j([str(r.source), str(r.ai_provider), v.locale !== 'ko' && hasHangul(str(r.raw_text)) && v.koSource]),
  }));
  return { rows, total: latest.length };
};

const polar: Builder = (b, v) => {
  const j = joiner(v);
  const rows = arr(b.regions).map((r, i) => {
    const thaw = obj(r.thaw);
    const news = obj(r.news);
    const base = obj(r.baseline);
    const anomalyBasis = str(thaw.heat_basis) === 'baseline_anomaly';
    return {
      id: `po-${str(r.region) ?? i}`,
      target: labelName(str(r.name), v.locale) ?? str(r.region) ?? v.none,
      measured:
        thaw.data_available === false
          ? v.weatherMissing
          : j([
              fmt(thaw.thaw_days_30d, 0) !== null && v.thawDays(fmt(thaw.thaw_days_30d, 0)!),
              anomalyBasis && signed(thaw.heat_trend_c) !== null && v.anomaly(signed(thaw.heat_trend_c)!),
              news.status === 'ok' && fmt(news.item_count, 0) !== null && v.news(fmt(news.item_count, 0)!),
            ]),
      derived: j([
        fmt(thaw.permafrost_thaw_pressure, 1) !== null && v.thawPressure(fmt(thaw.permafrost_thaw_pressure, 1)!),
        fmt(r.polar_watch_score, 1) !== null && v.watchScore(fmt(r.polar_watch_score, 1)!),
      ]),
      time: when(base.reference_period, v.none),
      note: '',
    };
  });
  return { rows };
};

const climate: Builder = (b, v) => {
  const j = joiner(v);
  const rows = arr(b.countries).map((c, i) => ({
    id: `cl-${str(c.country) ?? i}`,
    target: str(c.country) ?? v.none,
    measured:
      c.data_available === false
        ? v.none
        : j([
            fmt(c.mean_recent_temp_c) !== null && v.meanTemp(fmt(c.mean_recent_temp_c)!),
            fmt(c.precip_recent_14d_mm) !== null && v.precip14(fmt(c.precip_recent_14d_mm)!),
            signed(c.heat_trend_c) !== null && v.trend(signed(c.heat_trend_c)!),
          ]),
    derived: j([
      fmt(c.vector_suitability, 2) !== null && v.vectorSuit(fmt(c.vector_suitability, 2)!),
      fmt(c.spillover_pressure) !== null && v.envPressure(fmt(c.spillover_pressure)!),
    ]),
    time: v.none,
    note: c.data_available === false ? (clip(localNote(str(c.reason), v), 110) ?? '') : '',
  }));
  return { rows };
};

/** 키 없는 공개 스캔(top_surges) — 월 수입액은 품목별 top_surges 의 마지막 값(=latest_period). */
const trade: Builder = (b, v) => {
  const j = joiner(v);
  const products = obj(b.products);
  const period = when(b.latest_period, v.none);
  const multi = new Map(arr(b.multi_product_surges).map((m) => [str(m.country_iso3), num(m.product_count)]));
  const surges = arr(b.top_surges);
  const rows = surges.map((s, i) => {
    const iso = str(s.country_iso3);
    const prod = str(s.product);
    const detail = arr(obj(products[prod ?? '']).top_surges).find((x) => str(x.country_iso3) === iso);
    const series = Array.isArray(detail?.monthly_import_usd) ? (detail!.monthly_import_usd as unknown[]) : [];
    const latest = num(series[series.length - 1]);
    const count = multi.get(iso);
    return {
      id: `tr-${iso ?? i}-${prod ?? i}`,
      target: j([iso, prod]),
      measured: j([latest !== null && v.monthlyImport(Math.round(latest).toLocaleString('en-US'), period)]),
      derived: j([fmt(s.surge_ratio, 2) !== null && v.vsUsual(fmt(s.surge_ratio, 2)!)]),
      time: period,
      note: count && count > 1 ? v.multiProduct(String(count)) : '',
    };
  });
  return { rows, total: surges.length };
};

const disaster: Builder = (b, v) => {
  const j = joiner(v);
  const rows = arr(b.countries).map((c, i) => {
    const first = arr(c.open_windows)[0] ?? {};
    return {
      id: `di-${str(c.country_iso3) ?? i}`,
      target: str(c.country) ?? str(c.country_iso3) ?? v.none,
      measured: j([
        clip(str(first.title), 110),
        str(first.alert_level) && `GDACS ${str(first.alert_level)}`,
        fmt(first.days_since_disaster, 0) !== null && v.daysSince(fmt(first.days_since_disaster, 0)!),
      ]),
      derived: j([
        list(c.diseases) &&
          v.windows(list((c.diseases as unknown[]).map((x) => diseaseName(String(x), v.locale) ?? String(x)))!),
      ]),
      time: when(first.disaster_date, v.none),
      note: fmt(c.window_count, 0) ? v.openWindows(fmt(c.window_count, 0)!) : '',
    };
  });
  return { rows };
};

const travel: Builder = (b, v) => {
  if (b.data_available === false) return { rows: [] };
  const j = joiner(v);
  const all = arr(b.all_notices);
  const sorted = [...all].sort(
    (a, z) =>
      (num(z.level) ?? 0) - (num(a.level) ?? 0) ||
      Date.parse(str(z.pub_date) ?? '') - Date.parse(str(a.pub_date) ?? ''),
  );
  const rows = sorted.map((n, i) => ({
    id: `tv-${i}`,
    target: clip(str(n.headline), 90) ?? v.none,
    measured: j([num(n.level) !== null && v.level(String(num(n.level)))]),
    derived: v.none,
    time: when(n.pub_date, v.none),
    note: '',
  }));
  return { rows, total: all.length };
};

function satellite(
  prefix: string,
  countKey: string,
  pressureKey: string,
  unit: Record<Locale, string>,
  locale: Locale,
): Builder {
  return (b, v) => {
    const j = joiner(v);
    const rows = arr(b.countries).map((c, i) => ({
      id: `${prefix}-${str(c.country) ?? i}`,
      target: str(c.country) ?? v.none,
      measured:
        c.data_available === false
          ? v.none
          : j([fmt(c[countKey], 0) !== null && `${fmt(c[countKey], 0)} ${unit[locale]}`, str(c.day_range)]),
      derived: j([fmt(c[pressureKey], 1)]),
      time: v.none,
      note: c.data_available === false ? (clip(localNote(str(c.reason), v), 110) ?? '') : '',
    }));
    return { rows };
  };
}

const animal: Builder = (b, v) => {
  const j = joiner(v);
  return {
    rows: [
      {
        id: 'woah',
        target: 'WOAH RSS',
        measured: j([fmt(b.woah_rss_items, 0) !== null && v.rssItems(fmt(b.woah_rss_items, 0)!)]),
        derived: v.none,
        time: v.none,
        note: j([localNote(str(b.rss_reason), v), str(b.api_status) === 'retired' && v.apiRetired]),
      },
    ],
  };
};

function keyed(b: J): [string, J][] {
  return Object.entries(b).filter(([, x]) => x && typeof x === 'object' && !Array.isArray(x)) as [string, J][];
}

const genomic: Builder = (b, v) => {
  const j = joiner(v);
  const rows = keyed(b).map(([slug, g]) => ({
    id: `ge-${slug}`,
    target: labelName(str(g.label), v.locale) ?? slug,
    measured:
      g.available === false
        ? v.none
        : j([
            fmt(g.n_recent_sequences, 0) !== null && v.sequences(fmt(g.n_recent_sequences, 0)!),
            list(g.new_clades) ? v.newClades(list(g.new_clades)!) : v.noNewClades,
            str(g.dominant_clade) && v.dominant(str(g.dominant_clade)!, pct(g.dominant_share) ?? ''),
          ]),
    derived: v.none,
    time: when(g.build_updated, v.none),
    note: clip(localNote(str(g.note) ?? (g.available === false ? str(g.reason) : null), v), 110) ?? '',
  }));
  return { rows };
};

const social: Builder = (b, v) => {
  const j = joiner(v);
  const rows = keyed(b).map(([tag, s]) => ({
    id: `so-${tag}`,
    target: labelName(str(s.label), v.locale) ?? `#${tag}`,
    measured:
      s.available === false ? v.none : j([fmt(s.count_recent, 0) !== null && v.posts7d(fmt(s.count_recent, 0)!)]),
    derived: j([fmt(s.count_change_ratio, 2) !== null && v.vsPrev(fmt(s.count_change_ratio, 2)!)]),
    time: v.none,
    note: j([
      s.available === false && clip(localNote(str(s.reason), v), 110),
      s.sample_capped === true && v.capped,
      s.surge_alert === true && v.surge,
    ]).replace(v.none, ''),
  }));
  return { rows };
};

/** 급감이 없으면 행이 0 — 그 자체가 답이라 '점검 N개 · 급감 없음' 한 줄을 남긴다. */
const silence: Builder = (b, v) => {
  const j = joiner(v);
  const alerts = arr(b.alerts);
  if (alerts.length === 0 && fmt(b.metrics_checked, 0) !== null) {
    return {
      rows: [
        {
          id: 'si-none',
          target: v.silenceChecked(fmt(b.metrics_checked, 0)!),
          measured: v.none,
          derived: v.none,
          time: v.none,
          note: '',
        },
      ],
      total: 0,
    };
  }
  const rows = alerts.map((a, i) => ({
    id: `si-${str(a.metric) ?? i}`,
    target: j([str(a.label), str(a.metric)]),
    measured: j([
      fmt(a.latest) !== null && v.recent(fmt(a.latest)!),
      fmt(a.history_avg, 2) !== null && v.pastAvg(fmt(a.history_avg, 2)!),
    ]),
    derived: j([fmt(a.drop_ratio, 2) !== null && v.vsAvg(fmt(a.drop_ratio, 2)!)]),
    time: v.none,
    note: clip(str(a.message), 90) ?? '',
  }));
  return { rows, total: alerts.length };
};

const unexplained: Builder = (b, v) => {
  const j = joiner(v);
  const alerts = arr(b.alerts);
  const rows = alerts.map((a, i) => ({
    id: `un-${i}`,
    target: clip(placeName(str(a.location), v.locale), 50) ?? v.none,
    measured: j([clip(str(a.raw_disease_text) ?? str(a.raw_text), 160)]),
    derived: v.none,
    time: when(a.signal_date ?? a.extracted_at, v.none),
    note: j([str(a.source), v.locale !== 'ko' && hasHangul(str(a.raw_disease_text) ?? str(a.raw_text)) && v.koSource]),
  }));
  return { rows, total: alerts.length };
};

// ── 한 번에 모으기 ─────────────────────────────────────────────────────

function plan(locale: Locale): { key: ObservationSectionKey; path: string; build: Builder }[] {
  return [
    { key: 'events', path: '/api/extracted-signals?limit=100', build: events },
    { key: 'polar', path: '/api/polar-watch', build: polar },
    { key: 'climate', path: '/api/climate-signals', build: climate },
    { key: 'trade', path: '/api/trade-signals', build: trade },
    { key: 'disaster', path: '/api/disaster-watch', build: disaster },
    { key: 'travel', path: '/api/travel-notices', build: travel },
    {
      key: 'land',
      path: '/api/land-signals',
      build: satellite(
        'la',
        'fire_count_recent',
        'land_clearing_pressure',
        { ko: '건 화재 탐지', en: 'fire detections', fr: 'détections de feux' },
        locale,
      ),
    },
    {
      key: 'forest',
      path: '/api/deforestation-signals',
      build: satellite(
        'fo',
        'deforestation_alerts_recent',
        'deforestation_pressure',
        { ko: '건 손실 알림', en: 'loss alerts', fr: 'alertes de perte' },
        locale,
      ),
    },
    { key: 'animal', path: '/api/animal-signals', build: animal },
    { key: 'genomic', path: '/api/genomic-variants', build: genomic },
    { key: 'social', path: '/api/social-signal', build: social },
    { key: 'silence', path: '/api/negative-space', build: silence },
    {
      key: 'unexplained',
      path: '/api/unexplained-signals',
      build: unexplained,
    },
  ];
}

export async function getObservations(locale: Locale): Promise<ObservationSection[]> {
  const v = VALUES[locale];
  const steps = plan(locale);
  const bodies = await Promise.all(steps.map((p) => getJson(p.path)));
  return steps.map((p, i) => {
    const body = bodies[i];
    if (!body)
      return {
        key: p.key,
        rows: null,
        total: null,
        source: null,
        caveat: null,
        apiPath: p.path,
      };
    let built: Built;
    try {
      built = p.build(body, v);
    } catch {
      // 모양이 예상과 다르면 지어내지 않고 '읽지 못함'으로 떨어진다
      return {
        key: p.key,
        rows: null,
        total: null,
        source: localSource(str(body.data_source), locale),
        caveat: null,
        apiPath: p.path,
      };
    }
    return {
      key: p.key,
      rows: built.rows.slice(0, MAX_ROWS),
      total: built.total ?? built.rows.length,
      source: localSource(str(body.data_source), locale),
      caveat: clip(str(body.disclaimer) ?? str(body.caveat) ?? str(body.note), 280),
      apiPath: p.path,
    };
  });
}
