/**
 * 주간 해외유입 위험 보고서 — 무료 베타 페이지 데이터 (2026-11-16, 관측 데이터 활용 계획 ④).
 *
 * 캡틴: "데이터로 판매할 수 있는 것". 계획 문서에서 '지금 바로 무료 베타 가능'으로 고른 첫 상품.
 * 새로 계산하지 않는다 — 운영 서버가 매주 첫 수집 주기에 만들어 보관하는 /api/korea-import-report 를
 * 주 단위로 읽어 한 장으로 보여 주고, 같은 나라의 CDC 여행경보(나라 카드)를 옆에 붙인다.
 *
 * ★ 정직성 ★
 * - 조회 실패(네트워크·5xx)는 'unavailable'(화면: 판정 안 함), 그 주 보고서가 없음(404)은 'missing' — 섞지 않는다.
 * - 유입 노출 지수는 순위용이지 확률이 아니다(서버 is_probability=false 를 그대로 싣는다).
 */
import type { Locale } from '@/i18n';
import { getCountryCards } from './countryCards';
import { countryLabel } from './countryNames';
import { getGlobeData } from './globeData';
import { diseaseName, placeName } from './observationNames';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';
const TIMEOUT_MS = 15_000;

type J = Record<string, unknown>;

export function isIsoWeek(v: string): boolean {
  return /^\d{4}-W(0[1-9]|[1-4]\d|5[0-3])$/.test(v);
}

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}
function str(v: unknown): string | null {
  return typeof v === 'string' && v.trim() ? v.trim() : null;
}
function arr(v: unknown): J[] {
  return Array.isArray(v) ? v.filter((x) => x && typeof x === 'object').map((x) => x as J) : [];
}

export type WeeklyRow = {
  iso3: string;
  name: string;
  score: number | null;
  index: number | null;
  disease: string | null;
  routes: number | null;
  passengers: number | null;
  travel: string[];
};

export type WeeklyTrend = {
  series: string;
  baseWeek: string;
  baseValue: number | null;
  targetWeek: string;
  probUp: number | null;
  last: { week: string; probUp: number | null; outcome: string } | null;
};

export type WeeklyReport = {
  week: string;
  generatedAt: string | null;
  summary: { signal: number | null; exposed: number | null; noRoute: number | null; alerts: number | null };
  top: WeeklyRow[];
  noRoute: WeeklyRow[];
  trends: WeeklyTrend[];
  byPassengers: boolean;
  period: string | null;
  routesError: boolean;
  caveats: string[];
  weeks: string[];
};

export type WeeklyResult =
  | { state: 'ok'; report: WeeklyReport }
  | { state: 'missing'; weeks: string[] }
  | { state: 'unavailable' };

async function fetchReport(week: string | null): Promise<{ status: number; body: J | null }> {
  try {
    const q = week ? `?week=${encodeURIComponent(week)}` : '';
    const res = await fetch(`${API_BASE}/api/korea-import-report${q}`, {
      next: { revalidate: 900 },
      headers: { accept: 'application/json' },
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!res.ok) return { status: res.status, body: null };
    const body: unknown = await res.json();
    return { status: res.status, body: body && typeof body === 'object' ? (body as J) : null };
  } catch {
    return { status: 0, body: null };
  }
}

export async function getWeeklyReport(week: string | null, locale: Locale): Promise<WeeklyResult> {
  const [{ status, body }, globe] = await Promise.all([fetchReport(week), getGlobeData(locale)]);
  if (status === 404) {
    // 그 주가 없을 때 보관된 주 목록은 최신 보고서에서 얻는다
    const latest = week ? await fetchReport(null) : { status: 0, body: null };
    const weeks =
      latest.body && Array.isArray(latest.body.available_weeks) ? latest.body.available_weeks.map(String) : [];
    return { state: 'missing', weeks };
  }
  if (!body || !str(body.week) || !Array.isArray(body.top_exposure)) return { state: 'unavailable' };

  const cards = await getCountryCards(locale, globe);
  const travelOf = new Map(cards.cards.map((c) => [c.iso3, c.travelTitles]));
  const row = (r: J): WeeklyRow => {
    const iso3 = str(r.country) ?? '';
    const ko = str(r.name);
    const d = str(r.dominant_disease);
    return {
      iso3,
      // 백엔드 name 은 일부만 한국어 — ISO3 로 화면 언어 이름을 먼저 (2026-11-16)
      name: countryLabel(iso3, locale) ?? ((ko && (locale === 'ko' ? ko : placeName(ko, locale))) || iso3),
      score: num(r.raw_score),
      index: num(r.exposure_index),
      disease: d ? (locale === 'ko' ? d : (diseaseName(d, locale) ?? d)) : null,
      routes: num(r.direct_routes_to_kor),
      passengers: num(r.kor_passengers),
      travel: travelOf.get(iso3) ?? [],
    };
  };
  const s = (body.summary ?? {}) as J;
  const conn = (body.connectivity ?? null) as J | null;
  const period =
    conn && Array.isArray(conn.period)
      ? conn.period
          .map((x) =>
            locale === 'ko'
              ? String(x)
              : String(x).replace(/(\d{4})년\s*(\d{1,2})월/, (_, y: string, m: string) => `${y}-${m.padStart(2, '0')}`),
          )
          .join(' ~ ')
      : null;

  return {
    state: 'ok',
    report: {
      week: str(body.week) as string,
      generatedAt: str(body.generated_at),
      summary: {
        signal: num(s.countries_with_signal),
        exposed: num(s.exposed_countries),
        noRoute: num(s.no_direct_route_high),
        alerts: num(s.active_alerts),
      },
      top: arr(body.top_exposure).map(row),
      noRoute: arr(body.no_direct_route_high).map(row),
      trends: arr(body.neighbor_trends).map((t) => {
        const ls = (t.last_scored ?? null) as J | null;
        return {
          series: str(t.series) ?? '—',
          baseWeek: str(t.base_week) ?? '—',
          baseValue: num(t.base_value),
          targetWeek: str(t.target_week) ?? '—',
          probUp: num(t.prob_up),
          last: ls
            ? { week: str(ls.target_week) ?? '—', probUp: num(ls.prob_up), outcome: str(ls.outcome) ?? '' }
            : null,
        };
      }),
      byPassengers: conn?.basis === 'passengers',
      period,
      routesError: Boolean(body.routes_error),
      caveats: Array.isArray(body.caveats) ? body.caveats.map(String) : [],
      weeks: Array.isArray(body.available_weeks) ? body.available_weeks.map(String) : [],
    },
  };
}
