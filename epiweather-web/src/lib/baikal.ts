/**
 * BAIKAL MOB — 상태변화 엔진(/api/baikal)을 서버에서 읽는다 (2026-11-22).
 *
 * 캡틴: "상태변화 엔진으로서 아이기론의 핵심 엔진 · 온톨로지보다 상위계층". 운영 화면 맨 위에 둔다.
 * 엔진별 상태·언제부터·근거는 백엔드가 매시 판정한 값을 그대로 옮긴다(근거 문구는 한국어).
 * 조회 실패는 null(판정 안 함). 스냅숏이 없거나 낡았으면 그 사실을 그대로 넘긴다 — 화면이 '정상'으로 읽지 않게.
 */
import type { Locale } from '@/i18n';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';

type J = Record<string, unknown>;

const str = (v: unknown): string | null => (typeof v === 'string' && v.trim() ? v : null);
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

const LOCALE_TAG: Record<Locale, string> = { ko: 'ko-KR', en: 'en-GB', fr: 'fr-FR' };

function when(iso: unknown, locale: Locale): string {
  const s = str(iso);
  if (!s) return '—';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return `${d.toLocaleString(LOCALE_TAG[locale], {
    timeZone: 'UTC', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })} UTC`;
}

export type BaikalStatus = 'ok' | 'degraded' | 'down' | 'undetermined';

export type BaikalNodeRow = {
  id: string;
  engine: string;
  status: BaikalStatus;
  since: string;
  reason: string;
};

export type BaikalTransitionRow = {
  id: string;
  observed: string;
  engine: string;
  from: BaikalStatus | null;
  to: BaikalStatus;
  reason: string;
};

export type Baikal = {
  observedAt: string | null;
  /** 화면용 시각(UTC) */
  observedLabel: string;
  fresh: boolean;
  ageMinutes: number | null;
  nodes: BaikalNodeRow[];
  impacts: string[];
  transitions: BaikalTransitionRow[];
} | null;

const STATUSES: BaikalStatus[] = ['ok', 'degraded', 'down', 'undetermined'];
const asStatus = (v: unknown): BaikalStatus | null =>
  typeof v === 'string' && (STATUSES as string[]).includes(v) ? (v as BaikalStatus) : null;

const NAME_KEY: Record<Locale, string> = { ko: 'name_ko', en: 'name_en', fr: 'name_fr' };

export async function getBaikal(locale: Locale): Promise<Baikal> {
  let body: J;
  try {
    const res = await fetch(`${API_BASE}/api/baikal`, {
      next: { revalidate: 300 },
      headers: { accept: 'application/json' },
      signal: AbortSignal.timeout(15_000),
    });
    if (!res.ok) return null;
    const parsed: unknown = await res.json();
    if (!parsed || typeof parsed !== 'object') return null;
    body = parsed as J;
  } catch {
    return null;
  }

  const rawNodes = Array.isArray(body.nodes) ? (body.nodes as J[]) : [];
  const names: Record<string, string> = {};
  const ontologyNodes = ((body.ontology as J | undefined)?.nodes ?? []) as J[];
  for (const n of Array.isArray(ontologyNodes) ? ontologyNodes : []) {
    const key = str(n.key);
    if (key) names[key] = str(n[NAME_KEY[locale]]) ?? str(n.name_ko) ?? key;
  }

  const nodes: BaikalNodeRow[] = rawNodes.flatMap((n) => {
    const key = str(n.key);
    // 상태가 없거나 낯선 값이면 '판정 안 함'으로 둔다 — 모르는 값을 정상으로 그리지 않는다.
    if (!key) return [];
    return [{
      id: key,
      engine: names[key] ?? str(n[NAME_KEY[locale]]) ?? key,
      status: asStatus(n.status) ?? 'undetermined',
      since: when(n.since, locale),
      reason: [str(n.reason), str(n.note)].filter(Boolean).join(' · ') || '—',
    }];
  });

  const impacts = (Array.isArray(body.impacts) ? (body.impacts as J[]) : [])
    .map((i) => str(i.note_ko))
    .filter((s): s is string => Boolean(s));

  const transitions: BaikalTransitionRow[] = (Array.isArray(body.transitions) ? (body.transitions as J[]) : [])
    .flatMap((t, i) => {
      const to = asStatus(t.to_status);
      const key = str(t.node);
      if (!to || !key) return [];
      return [{
        id: `${str(t.observed_at) ?? i}-${key}-${i}`,
        observed: when(t.observed_at, locale),
        engine: names[key] ?? key,
        from: asStatus(t.from_status),
        to,
        reason: str(t.reason) ?? '—',
      }];
    });

  return {
    observedAt: str(body.observed_at),
    observedLabel: when(body.observed_at, locale),
    fresh: body.fresh === true,
    ageMinutes: num(body.age_minutes),
    nodes,
    impacts,
    transitions,
  };
}
