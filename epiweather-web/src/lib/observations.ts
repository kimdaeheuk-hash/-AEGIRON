/**
 * 관측 데이터 보드(/observations)가 읽는 운영 API 값 (2026-11-15).
 *
 * 분야마다 응답 모양이 다르지만 화면은 다섯 칸 하나로 통일한다:
 *   대상 · 측정값 · 해석값(추정·대리) · 기준 시각 · 비고
 * 측정값과 해석값을 다른 칸에 두는 게 핵심이다 — 같은 칸에 섞으면 추정이 측정처럼 읽힌다.
 *
 * 못 읽으면 rows=null → 화면은 "읽어 오지 못함"을 쓴다(지어낸 0 이 아니라).
 * 값이 없는 칸은 '—' 가 아니라 비워 두지 않고 VALUE_NONE 으로 쓴다.
 */
import type { ObservationSectionKey } from '@/i18n/types';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ??
  'https://epiweather-api-production.up.railway.app';

/** 수집은 매시 돈다. 일부 분야는 요청 때 외부 API 를 부르므로 너무 자주 묻지 않는다. */
const REVALIDATE_SECONDS = 900;
/** 한 분야가 느려도 페이지 전체가 막히지 않게. */
const TIMEOUT_MS = 20_000;
/** 분야별 최대 행 수 — 표가 끝없이 길어지지 않게. 잘랐으면 비고에 남긴다. */
const MAX_ROWS = 25;

export const VALUE_NONE = '값 없음';

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
  /** 전체 몇 건 중 표시했는지 */
  total: number | null;
  source: string | null;
  /** 응답에 실린 주의 문구(disclaimer/caveat) — 화면이 그대로 그린다 */
  caveat: string | null;
  /** 응답 원문 링크 */
  apiPath: string;
};

type J = Record<string, unknown>;

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
/** 붙일 값이 하나도 없으면 VALUE_NONE. */
function join(parts: (string | null | undefined | false)[]): string {
  const kept = parts.filter((p): p is string => typeof p === 'string' && p.length > 0);
  return kept.length ? kept.join(' · ') : VALUE_NONE;
}
function when(v: unknown): string {
  const s = str(v);
  if (!s) return VALUE_NONE;
  // ISO 시각이면 'YYYY-MM-DD HH:MM UTC', 날짜만이면 그대로
  const m = s.match(/^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}))?/);
  if (!m) return s.slice(0, 40);
  return m[2] ? `${m[1]} ${m[2]} UTC` : m[1];
}
function clip(s: string | null, n = 120): string | null {
  if (!s) return null;
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}
function limit(rows: ObservationRow[]): ObservationRow[] {
  return rows.slice(0, MAX_ROWS);
}

function section(
  key: ObservationSectionKey,
  apiPath: string,
  body: J | null,
  build: (b: J) => { rows: ObservationRow[]; total?: number },
): ObservationSection {
  if (!body) return { key, rows: null, total: null, source: null, caveat: null, apiPath };
  let built: { rows: ObservationRow[]; total?: number };
  try {
    built = build(body);
  } catch {
    // 모양이 예상과 다르면 지어내지 않고 '읽지 못함'으로 떨어진다
    return { key, rows: null, total: null, source: str(body.data_source), caveat: null, apiPath };
  }
  return {
    key,
    rows: limit(built.rows),
    total: built.total ?? built.rows.length,
    source: str(body.data_source),
    caveat: clip(str(body.disclaimer) ?? str(body.caveat) ?? str(body.note), 260),
    apiPath,
  };
}

// ── 분야별 변환 ────────────────────────────────────────────────────────

function events(b: J) {
  const rows = arr(b.records).map((r, i) => ({
    id: `ev-${str(r.id) ?? i}`,
    target: join([str(r.country_iso3) ?? str(r.location), str(r.disease)]),
    measured: join([str(r.signal_type), clip(str(r.location), 60)]),
    derived: VALUE_NONE,
    time: when(r.signal_date ?? r.extracted_at),
    note: join([str(r.source), str(r.ai_provider)]),
  }));
  return { rows };
}

function polar(b: J) {
  const rows = arr(b.regions).map((r, i) => {
    const thaw = obj(r.thaw);
    const news = obj(r.news);
    return {
      id: `po-${str(r.region) ?? i}`,
      target: str(r.name) ?? str(r.region) ?? VALUE_NONE,
      measured: join([
        fmt(thaw.thaw_days_30d, 0) && `해빙일 ${fmt(thaw.thaw_days_30d, 0)}일/30일`,
        fmt(thaw.heat_trend_c, 2) && `기온 추세 ${fmt(thaw.heat_trend_c, 2)}℃`,
        fmt(news.item_count, 0) && `관련 보도 ${fmt(news.item_count, 0)}건`,
      ]),
      derived: join([
        fmt(thaw.permafrost_thaw_pressure, 2) && `해빙 압력 ${fmt(thaw.permafrost_thaw_pressure, 2)}`,
        fmt(r.polar_watch_score, 1) && `관찰 점수 ${fmt(r.polar_watch_score, 1)}`,
        str(r.watch_grade),
      ]),
      time: VALUE_NONE,
      note: thaw.data_available === false ? '기상값 받지 못함' : '',
    };
  });
  return { rows };
}

function climate(b: J) {
  const all = arr(b.countries);
  const rows = all.map((c, i) => ({
    id: `cl-${str(c.country) ?? i}`,
    target: str(c.country) ?? VALUE_NONE,
    measured:
      c.data_available === false
        ? VALUE_NONE
        : join([
            fmt(c.mean_recent_temp_c, 1) && `평균 기온 ${fmt(c.mean_recent_temp_c, 1)}℃`,
            fmt(c.precip_recent_14d_mm, 1) && `14일 강수 ${fmt(c.precip_recent_14d_mm, 1)}mm`,
            fmt(c.heat_trend_c, 2) && `추세 ${fmt(c.heat_trend_c, 2)}℃`,
          ]),
    derived: join([
      fmt(c.vector_suitability, 2) && `매개체 적합도 ${fmt(c.vector_suitability, 2)}`,
      fmt(c.spillover_pressure, 2) && `환경 압력 ${fmt(c.spillover_pressure, 2)}`,
    ]),
    time: VALUE_NONE,
    note: c.data_available === false ? clip(str(c.reason), 80) ?? '' : '',
  }));
  return { rows };
}

function trade(b: J) {
  // 키 없는 공개 스캔: top_surges · multi_product_surges / 키 있는 모드: countries
  const surges = arr(b.top_surges);
  const countries = arr(b.countries);
  const src = surges.length ? surges : countries;
  const rows = src.map((s, i) => ({
    id: `tr-${i}`,
    target: join([str(s.country_iso3) ?? str(s.country), str(s.product) ?? str(s.label)]),
    measured: join([
      fmt(s.monthly_import_usd, 0) && `월 수입 $${fmt(s.monthly_import_usd, 0)}`,
      str(s.period) && `기준월 ${str(s.period)}`,
    ]),
    derived: join([
      fmt(s.surge_ratio ?? s.max_surge_ratio, 2) && `평소 대비 ${fmt(s.surge_ratio ?? s.max_surge_ratio, 2)}배`,
    ]),
    time: when(b.scanned_at ?? b.called_at),
    note: '',
  }));
  return { rows };
}

function disaster(b: J) {
  const rows = arr(b.countries).map((c, i) => {
    const wins = arr(c.open_windows);
    const first = wins[0] ?? {};
    return {
      id: `di-${str(c.country_iso3) ?? i}`,
      target: str(c.country) ?? str(c.country_iso3) ?? VALUE_NONE,
      measured: join([
        str(first.event_type) ?? str(first.disaster_type),
        str(first.alert_level) && `GDACS ${str(first.alert_level)}`,
        fmt(first.days_since_disaster, 0) && `${fmt(first.days_since_disaster, 0)}일 경과`,
      ]),
      derived: join([
        Array.isArray(c.diseases) && c.diseases.length
          ? `감시창: ${(c.diseases as unknown[]).map(String).join(', ')}`
          : null,
      ]),
      time: when(first.disaster_date ?? first.started_at ?? b.updated_at),
      note: fmt(c.window_count, 0) ? `열린 창 ${fmt(c.window_count, 0)}개` : '',
    };
  });
  return { rows };
}

function travel(b: J) {
  if (b.data_available === false) return { rows: [] as ObservationRow[] };
  const list = arr(b.all_notices);
  const sorted = [...list].sort((a, z) => (num(z.level) ?? 0) - (num(a.level) ?? 0));
  const rows = sorted.map((n, i) => ({
    id: `tv-${i}`,
    target: str(n.country) ?? clip(str(n.title), 60) ?? VALUE_NONE,
    measured: join([num(n.level) !== null ? `Level ${num(n.level)}` : null, clip(str(n.title), 80)]),
    derived: VALUE_NONE,
    time: when(n.published ?? n.date),
    note: '',
  }));
  return { rows, total: list.length };
}

function landOrForest(prefix: string, countKey: string, pressureKey: string, unit: string) {
  return (b: J) => {
    const rows = arr(b.countries).map((c, i) => ({
      id: `${prefix}-${str(c.country) ?? i}`,
      target: str(c.country) ?? VALUE_NONE,
      measured:
        c.data_available === false
          ? VALUE_NONE
          : join([fmt(c[countKey], 0) && `${fmt(c[countKey], 0)}${unit}`, str(c.day_range) && `${str(c.day_range)}일`]),
      derived: join([fmt(c[pressureKey], 2) && `압력 ${fmt(c[pressureKey], 2)}`]),
      time: VALUE_NONE,
      note: c.data_available === false ? clip(str(c.reason), 80) ?? '' : '',
    }));
    return { rows };
  };
}

function animal(b: J) {
  return {
    rows: [
      {
        id: 'woah',
        target: 'WOAH RSS',
        measured: fmt(b.woah_rss_items, 0) ? `공식 RSS 항목 ${fmt(b.woah_rss_items, 0)}건` : VALUE_NONE,
        derived: VALUE_NONE,
        time: VALUE_NONE,
        note: join([str(b.rss_reason), str(b.api_status) && `WAHIS API: ${str(b.api_status)}`]),
      },
    ],
  };
}

function keyedEntries(b: J): [string, J][] {
  return Object.entries(b).filter(([, v]) => v && typeof v === 'object' && !Array.isArray(v)) as [string, J][];
}

function genomic(b: J) {
  const rows = keyedEntries(b).map(([slug, g]) => ({
    id: `ge-${slug}`,
    target: str(g.label) ?? str(g.pathogen) ?? slug,
    measured:
      g.available === false
        ? VALUE_NONE
        : join([
            Array.isArray(g.new_clades) && g.new_clades.length
              ? `새 계통 ${(g.new_clades as unknown[]).map(String).slice(0, 4).join(', ')}`
              : '새 계통 없음',
            str(g.dominant_clade) && `우세 ${str(g.dominant_clade)}`,
          ]),
    derived: VALUE_NONE,
    time: when(g.build_updated ?? g.updated_at),
    note: g.available === false ? clip(str(g.reason), 80) ?? '' : '',
  }));
  return { rows };
}

function social(b: J) {
  const rows = keyedEntries(b).map(([tag, s]) => ({
    id: `so-${tag}`,
    target: str(s.label) ?? `#${tag}`,
    measured: s.available === false ? VALUE_NONE : join([fmt(s.count_recent, 0) && `7일 ${fmt(s.count_recent, 0)}건`]),
    derived: join([fmt(s.count_change_ratio, 2) && `직전 대비 ${fmt(s.count_change_ratio, 2)}배`]),
    time: VALUE_NONE,
    note: s.available === false ? clip(str(s.reason), 80) ?? '' : s.surge_alert ? '급변' : '',
  }));
  return { rows };
}

function silence(b: J) {
  const rows = arr(b.alerts).map((a, i) => ({
    id: `si-${str(a.metric) ?? i}`,
    target: join([str(a.label), str(a.metric)]),
    measured: join([
      fmt(a.latest, 1) && `최근 ${fmt(a.latest, 1)}`,
      fmt(a.history_avg, 2) && `과거 평균 ${fmt(a.history_avg, 2)}`,
    ]),
    derived: join([fmt(a.drop_ratio, 2) && `평균 대비 ${fmt(a.drop_ratio, 2)}배`]),
    time: VALUE_NONE,
    note: clip(str(a.message), 80) ?? '',
  }));
  return { rows, total: rows.length };
}

function unexplained(b: J) {
  const rows = arr(b.alerts).map((a, i) => ({
    id: `un-${i}`,
    target: str(a.location) ?? VALUE_NONE,
    measured: clip(str(a.raw_disease_text), 80) ?? VALUE_NONE,
    derived: VALUE_NONE,
    time: when(a.signal_date ?? a.extracted_at),
    note: str(a.source) ?? '',
  }));
  return { rows };
}

// ── 한 번에 모으기 ─────────────────────────────────────────────────────

const PLAN: { key: ObservationSectionKey; path: string; build: (b: J) => { rows: ObservationRow[]; total?: number } }[] = [
  { key: 'events', path: '/api/extracted-signals?limit=100', build: events },
  { key: 'polar', path: '/api/polar-watch', build: polar },
  { key: 'climate', path: '/api/climate-signals', build: climate },
  { key: 'trade', path: '/api/trade-signals', build: trade },
  { key: 'disaster', path: '/api/disaster-watch', build: disaster },
  { key: 'travel', path: '/api/travel-notices', build: travel },
  { key: 'land', path: '/api/land-signals', build: landOrForest('la', 'fire_count_recent', 'land_clearing_pressure', '건 화재 탐지') },
  { key: 'forest', path: '/api/deforestation-signals', build: landOrForest('fo', 'deforestation_alerts_recent', 'deforestation_pressure', '건 손실 알림') },
  { key: 'animal', path: '/api/animal-signals', build: animal },
  { key: 'genomic', path: '/api/genomic-variants', build: genomic },
  { key: 'social', path: '/api/social-signal', build: social },
  { key: 'silence', path: '/api/negative-space', build: silence },
  { key: 'unexplained', path: '/api/unexplained-signals', build: unexplained },
];

export async function getObservations(): Promise<ObservationSection[]> {
  const bodies = await Promise.all(PLAN.map((p) => getJson(p.path)));
  return PLAN.map((p, i) => section(p.key, p.path, bodies[i], p.build));
}
