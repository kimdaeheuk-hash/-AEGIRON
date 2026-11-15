/**
 * 나라별 위험 카드 — 흩어진 관측 층을 나라 하나로 융합한다 (2026-11-15 캡틴:
 * "이대로 가면 데이터를 활용 못하고 사업화가 안 돼").
 *
 * 한 나라에 대해: 발생 보도 · 설명 불가 신호 · 재난 감시창 · 의료물자 수입 급증 · CDC 여행경보 등급 ·
 * 위험지수(risk-index) · 한국 연결(직항 노선·인천 여객) 을 한 장에 모은다. 이 카드가 지구본의 클릭 화면이자
 * 판매 단위(구독·API·기관 브리핑)의 한 행이다.
 *
 * ★ 정직성 ★
 * - '관측 강도'는 측정값이 아니라 우리가 정한 가중합(추정)이다. 가중치는 실측으로 보정하지 않았다 —
 *   화면에 공식과 '가중치 미보정'을 같이 적는다. 위험(발병 확률)이 아니라 '이번에 받은 관측이 얼마나 많고 무거운가'다.
 * - 한국 연결은 korea-import-report 가 준 값만 쓴다(없으면 '값 없음'). 지어내지 않는다.
 * - 여행경보 나라는 CDC 제목 속 나라 이름을 읽은 것이다(못 읽으면 붙이지 않음).
 */
import type { Locale } from '@/i18n';
import type { GlobeData, GlobeLayer } from './globeData';
import { EN_ISO3, KO_ISO3 } from './isoGeo';
import { placeName } from './observationNames';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';
const REVALIDATE_SECONDS = 900;
const TIMEOUT_MS = 20_000;

type J = Record<string, unknown>;

export type Grade = 'high' | 'elevated' | 'watch';

export type CountryCard = {
  iso3: string;
  name: string;
  /** risk-index 가 준 대표 좌표(없으면 화면이 국경 중심으로 계산) */
  lat: number | null;
  lng: number | null;
  counts: Record<Exclude<GlobeLayer, 'polar'>, number>;
  /** CDC 여행경보 최고 등급(1~4), 없으면 null */
  travelLevel: number | null;
  travelTitles: string[];
  /** 관측 강도 0~100 — 추정(가중합), 가중치 미보정 */
  intensity: number;
  grade: Grade;
  /** risk-index 의 위험 점수(그 자체도 모델 추정) */
  riskScore: number | null;
  dominantDisease: string | null;
  korea: { routes: number | null; passengers: number | null };
  /** 층별 근거 줄(globeData 의 lines 를 층 이름과 함께) */
  evidence: { layer: GlobeLayer | 'travel'; line: string }[];
};

export type CardsData = {
  cards: CountryCard[];
  /** 한국 연결 자료를 못 읽었으면 false — 화면은 유입 경로 호를 그리지 않고 그렇게 적는다 */
  koreaAvailable: boolean;
  koreaBasis: string | null;
};

/** 관측 강도 가중치 — 판단 상수(미보정). 화면에 그대로 공개한다. */
export const INTENSITY_WEIGHTS = { event: 20, unexplained: 15, disaster: 15, trade: 10, travelPerLevel: 8 } as const;
const GRADE_HIGH = 60;
const GRADE_ELEVATED = 30;

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

function arr(v: unknown): J[] {
  return Array.isArray(v) ? v.filter((x) => x && typeof x === 'object').map((x) => x as J) : [];
}
function str(v: unknown): string | null {
  return typeof v === 'string' && v.trim() ? v.trim() : null;
}
function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

const KO_NAME: Record<string, string> = Object.fromEntries(
  Object.entries(KO_ISO3)
    .sort((a, b) => b[0].length - a[0].length)
    .map(([ko, iso]) => [iso, ko]),
);
/** 영어 나라 이름(긴 것부터) — CDC 제목 'Yellow Fever in Burkina Faso, Côte d'Ivoire, and Ghana' 읽기용 */
const EN_NAMES = Object.keys(EN_ISO3)
  .filter((n) => n.length >= 4)
  .sort((a, b) => b.length - a.length);

function travelIsos(headline: string): string[] {
  const m = headline.match(/\bin (?:the )?(.+)$/i);
  if (!m) return [];
  let rest = m[1].toLowerCase();
  const out = new Set<string>();
  for (const n of EN_NAMES) {
    if (rest.includes(n)) {
      out.add(EN_ISO3[n]);
      rest = rest.split(n).join(' ');
    }
  }
  return [...out];
}

export function intensityOf(counts: CountryCard['counts'], travelLevel: number | null): number {
  const w = INTENSITY_WEIGHTS;
  const v =
    w.event * Math.log2(1 + counts.event) +
    w.unexplained * Math.log2(1 + counts.unexplained) +
    w.disaster * Math.log2(1 + counts.disaster) +
    w.trade * Math.log2(1 + counts.trade) +
    w.travelPerLevel * (travelLevel ?? 0);
  return Math.min(100, Math.round(v));
}

function gradeOf(intensity: number): Grade {
  return intensity >= GRADE_HIGH ? 'high' : intensity >= GRADE_ELEVATED ? 'elevated' : 'watch';
}

export async function getCountryCards(locale: Locale, globe: GlobeData): Promise<CardsData> {
  const [risk, korea, travel] = await Promise.all([
    getJson('/api/risk-index'),
    getJson('/api/korea-import-report'),
    getJson('/api/travel-notices'),
  ]);

  const cards = new Map<string, CountryCard>();
  const card = (iso3: string): CountryCard => {
    let c = cards.get(iso3);
    if (!c) {
      const ko = KO_NAME[iso3];
      c = {
        iso3,
        name: (ko && (locale === 'ko' ? ko : placeName(ko, locale))) || iso3,
        lat: null,
        lng: null,
        counts: { event: 0, unexplained: 0, disaster: 0, trade: 0 },
        travelLevel: null,
        travelTitles: [],
        intensity: 0,
        grade: 'watch',
        riskScore: null,
        dominantDisease: null,
        korea: { routes: null, passengers: null },
        evidence: [],
      };
      cards.set(iso3, c);
    }
    return c;
  };

  for (const p of globe.points) {
    if (!p.iso3 || p.layer === 'polar') continue;
    const c = card(p.iso3);
    c.counts[p.layer] += p.count;
    if (c.name === p.iso3 && p.title !== p.iso3) c.name = p.title;
    for (const line of p.lines) if (c.evidence.length < 12) c.evidence.push({ layer: p.layer, line });
  }

  for (const n of arr(travel?.all_notices)) {
    const head = str(n.headline);
    const level = num(n.level);
    if (!head || level === null) continue;
    for (const iso of travelIsos(head)) {
      const c = card(iso);
      c.travelLevel = Math.max(c.travelLevel ?? 0, level);
      if (c.travelTitles.length < 3) c.travelTitles.push(`Level ${level} · ${head}`);
    }
  }

  // 위험지수 — 신호가 있는 나라에만 붙인다(없는 나라를 카드로 새로 만들지 않음)
  for (const r of arr(risk?.countries)) {
    const iso = str(r.country);
    if (!iso || !cards.has(iso)) continue;
    const c = cards.get(iso)!;
    c.lat = num(r.lat);
    c.lng = num(r.lng);
    c.riskScore = num(r.risk_score);
    c.dominantDisease = str(r.dominant_disease);
  }

  // 한국 연결 — 유입 보고서의 노출 국가 목록
  const exposure = [...arr(korea?.top_exposure), ...arr(korea?.no_direct_route_high)];
  for (const e of exposure) {
    const iso = str(e.country);
    if (!iso || !cards.has(iso)) continue;
    const c = cards.get(iso)!;
    c.korea = { routes: num(e.direct_routes_to_kor), passengers: num(e.kor_passengers) };
  }
  const conn = (korea?.connectivity ?? null) as J | null;
  const koreaBasis = conn
    ? [str(conn.basis), str(conn.source), str(conn.period as string)].filter(Boolean).join(' · ') || null
    : null;

  const out = [...cards.values()].map((c) => {
    const intensity = intensityOf(c.counts, c.travelLevel);
    return { ...c, intensity, grade: gradeOf(intensity) };
  });
  out.sort((a, b) => b.intensity - a.intensity);
  return { cards: out, koreaAvailable: !!korea, koreaBasis };
}
