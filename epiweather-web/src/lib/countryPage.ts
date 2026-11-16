/**
 * 나라별 페이지 /observations/[iso3] 의 데이터 (2026-11-16).
 *
 * 관측 데이터 활용 계획 ①⑥⑦ 중 비용 없이 할 수 있는 부분: 이미 쌓인 데이터만 쓴다.
 * - 나라 카드: lib/countryCards (백엔드 /api/country-cards, 없으면 같은 공식으로 웹 계산)
 * - 30일 이력: /api/observations/history (2026-11-15 부터 매시 저장 — 기후·무역·재난)
 * - 확인 목록: 받은 관측 종류 → 정해 둔 문장(규칙). 의료·방역 권고가 아님.
 * - 대응 조치: AI 추출이 아직 없어 '판정 안 함'으로 적는다(지어내지 않음).
 *
 * ★ 정직성 ★ 이력 조회 실패는 null(화면: 판정 안 함), 빈 결과는 [] — 둘을 섞지 않는다.
 */
import type { CountryCard } from './countryCards';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';
const REVALIDATE_SECONDS = 900;
const TIMEOUT_MS = 15_000;
const DASH = '—';

export type HistoryLayer = 'climate' | 'trade' | 'disaster';
export const HISTORY_LAYERS: HistoryLayer[] = ['climate', 'trade', 'disaster'];

export type HistoryRow = {
  id: string;
  observed: string;
  confirmed: string;
  measured: string;
  derived: string;
};

type J = Record<string, unknown>;

export function isIso3(v: string): boolean {
  return /^[A-Z]{3}$/.test(v);
}

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

function stamp(v: unknown): string {
  return typeof v === 'string' && v.length >= 16 ? `${v.slice(0, 10)} ${v.slice(11, 16)} UTC` : DASH;
}

/** 측정값·해석값 JSON 을 한 줄로 — 키 이름은 그대로 둔다(번역하면 원자료와 대조가 어려워짐). */
function flat(obj: unknown): string {
  if (!obj || typeof obj !== 'object') return DASH;
  const parts: string[] = [];
  for (const [k, v] of Object.entries(obj as J)) {
    if (v === null || v === undefined) continue;
    if (Array.isArray(v)) {
      if (k === 'events') {
        for (const e of v as J[]) {
          parts.push([e.alert_level, e.disaster_type, e.disaster_date].filter(Boolean).join(' '));
        }
      } else if (k === 'monthly_import_usd') {
        const last = num(v[v.length - 1]);
        parts.push(`${k}(last) ${last === null ? DASH : '$' + last.toLocaleString('en-US')}`);
      } else {
        parts.push(`${k} ${v.join(', ') || DASH}`);
      }
    } else {
      parts.push(`${k} ${typeof v === 'number' ? v.toLocaleString('en-US') : String(v)}`);
    }
  }
  return parts.join(' · ') || DASH;
}

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

/** 층별 30일 이력. 조회 실패면 null(판정 안 함), 저장된 값이 없으면 []. 최신이 위. */
export async function getCountryHistory(
  iso3: string,
  undeterminedLabel: string,
): Promise<Record<HistoryLayer, HistoryRow[] | null>> {
  const entries = await Promise.all(
    HISTORY_LAYERS.map(async (layer) => {
      const body = await getJson(`/api/observations/history?layer=${layer}&target=${iso3}&days=30&limit=500`);
      if (!body || !Array.isArray(body.rows)) return [layer, null] as const;
      const rows = (body.rows as J[])
        .slice()
        .reverse()
        .map((r, i) => ({
          id: `${layer}-${String(r.id ?? i)}`,
          observed: stamp(r.observed_at),
          confirmed: stamp(r.confirmed_at),
          measured:
            r.status === 'undetermined'
              ? `${undeterminedLabel}${typeof r.reason === 'string' ? ` — ${r.reason}` : ''}`
              : `${typeof r.metric === 'string' && r.metric ? `[${r.metric}] ` : ''}${flat(r.measured)}`,
          derived: r.status === 'undetermined' ? DASH : flat(r.derived),
        }));
      return [layer, rows] as const;
    }),
  );
  return Object.fromEntries(entries) as Record<HistoryLayer, HistoryRow[] | null>;
}

export type CheckKey = 'travel' | 'disaster' | 'trade' | 'event' | 'unexplained' | 'korea';

/** 받은 관측 종류 → 확인 항목(규칙). 관측이 없으면 빈 배열 — 화면이 '만들지 않음'으로 적는다. */
export function checklist(card: CountryCard | null): CheckKey[] {
  if (!card) return [];
  const out: CheckKey[] = [];
  if (card.travelLevel !== null) out.push('travel');
  if (card.counts.disaster > 0) out.push('disaster');
  if (card.counts.trade > 0) out.push('trade');
  if (card.counts.event > 0) out.push('event');
  if (card.counts.unexplained > 0) out.push('unexplained');
  if ((card.korea.routes ?? 0) > 0 || (card.korea.passengers ?? 0) > 0) out.push('korea');
  return out;
}

export type ResponseRow = {
  id: string;
  date: string;
  disease: string;
  measure: string;
  evidence: string;
  url: string | null;
  shared: boolean;
};

/**
 * 발병국 대응 조치 — /api/response-measures (WHO DON '대응' 단락 낱말 읽기, 2026-11-16).
 * 조회 실패(머지 전 포함)는 null(판정 안 함), 기록 없음은 []. 조치 이름은 백엔드 labels 의 해당 언어.
 */
export async function getResponseMeasures(iso3: string, locale: 'ko' | 'en' | 'fr'): Promise<ResponseRow[] | null> {
  const body = await getJson(`/api/response-measures?country=${iso3}&days=400&limit=300`);
  if (!body || !Array.isArray(body.rows)) return null;
  const labels = (body.labels ?? {}) as Record<string, Record<string, string>>;
  return (body.rows as J[]).map((r, i) => {
    const key = typeof r.measure === 'string' ? r.measure : '';
    return {
      id: `${String(r.don_id ?? '')}-${key}-${i}`,
      date: typeof r.published === 'string' ? r.published : DASH,
      disease: typeof r.disease === 'string' && r.disease ? r.disease : DASH,
      measure: labels[key]?.[locale] ?? key,
      evidence: typeof r.evidence === 'string' ? r.evidence : DASH,
      url: typeof r.url === 'string' ? r.url : null,
      shared: (num(r.shared_countries) ?? 1) > 1,
    };
  });
}
