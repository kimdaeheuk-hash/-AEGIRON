/**
 * 실가동·예측 원장 페이지가 읽는 운영 API 값 (2026-10-18).
 *
 * 응답 모양은 수집 워크플로가 받아 둔 운영 스냅숏으로 확인했다(media-capture/results).
 * 못 읽으면 null — 화면은 지어낸 값 대신 "지금 읽어 오지 못했다"를 쓴다.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ??
  'https://epiweather-api-production.up.railway.app';

/** 수집이 매시 돈다 — 5분이면 충분히 새롭다. */
const REVALIDATE_SECONDS = 300;

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: REVALIDATE_SECONDS },
      headers: { accept: 'application/json' },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export type SourceRow = {
  source: string;
  status: string;
  last_success_at?: string | null;
};

export type OpsStatus = {
  counts: { predictions: number; alerts: number; extracted: number; sentinel: number; declarations: number };
  healthy: number;
  total: number;
  sources: SourceRow[];
};

export async function getOpsStatus(): Promise<OpsStatus | null> {
  const d = await getJson<{
    db_table_counts?: Record<string, number>;
    source_health?: { healthy_count?: number; total_tracked?: number; sources?: SourceRow[] };
  }>('/api/status');
  const c = d?.db_table_counts;
  const sh = d?.source_health;
  if (!c || typeof sh?.healthy_count !== 'number' || typeof sh?.total_tracked !== 'number') return null;
  return {
    counts: {
      predictions: c.predictions ?? 0,
      alerts: c.alerts ?? 0,
      extracted: c.extracted_signals ?? 0,
      sentinel: c.sentinel_queue ?? 0,
      declarations: c.outbreak_timeline ?? 0,
    },
    healthy: sh.healthy_count,
    total: sh.total_tracked,
    sources: sh.sources ?? [],
  };
}

export type RiskRow = {
  country: string;
  name: string;
  risk_score: number;
  raw_score?: number;
  dominant_disease?: string | null;
};

export async function getRiskTop(n = 8): Promise<RiskRow[] | null> {
  const d = await getJson<{ countries?: RiskRow[] }>('/api/risk-index');
  if (!d?.countries) return null;
  return [...d.countries]
    .filter((c) => typeof c.risk_score === 'number')
    .sort((a, b) => b.risk_score - a.risk_score)
    .slice(0, n);
}

export type AlertItem = {
  label: string;
  tier: string;
  score: number;
  source: string;
  evidence?: string[];
};

export async function getTopAlerts(): Promise<{ date?: string; items: AlertItem[] } | null> {
  const d = await getJson<{ date?: string; dashboard?: { top?: AlertItem[] } }>('/api/alerts');
  if (!d?.dashboard) return null;
  return { date: d.date, items: d.dashboard.top ?? [] };
}

export type Prediction = {
  id: number;
  predicted_at: string;
  country: string;
  disease: string;
  risk_score: number;
  confidence?: number | null;
  resolves_by?: string | null;
  resolution_criteria?: string | null;
  outcome?: string | null;
  correct?: number | null;
  verified_at?: string | null;
  content_hash?: string | null;
  ots_submitted_at?: string | null;
};

export async function getPredictions(): Promise<Prediction[] | null> {
  const d = await getJson<{ predictions?: Prediction[] }>('/api/predictions');
  return d?.predictions ?? null;
}

export type Scorecard = {
  total: number;
  resolved: number;
  correct: number;
  incorrect: number;
  unresolved: number;
  unscoreable_legacy: number;
  brier: number | null;
  overdue: unknown[];
};

export async function getScorecard(): Promise<Scorecard | null> {
  const d = await getJson<Scorecard>('/api/predictions/scorecard');
  return d && typeof d.total === 'number' ? d : null;
}

export type LedgerEntry = {
  id: number;
  disease: string;
  country_iso3: string | null;
  crossed_at: string;
  severity: number;
  threshold: number;
  outcome: string;
  declared_on?: string | null;
  lead_days?: number | null;
};

export type Ledger = {
  summary: { measured_events: number; open_crossings: number; false_alarms: number; horizon_days: number };
  entries: LedgerEntry[];
};

export async function getLedger(): Promise<Ledger | null> {
  const d = await getJson<Ledger>('/api/lead-time-ledger?limit=50');
  return d?.summary && Array.isArray(d.entries) ? d : null;
}

/** 예측 판정 상태 — 백엔드 outcome·correct 를 화면 네 갈래로. */
export function predictionStatus(p: Prediction): 'hit' | 'miss' | 'open' | 'other' {
  if (p.outcome === 'correct' || p.correct === 1) return 'hit';
  if (p.outcome === 'incorrect' || p.correct === 0) return 'miss';
  if (p.outcome === 'ambiguous' || p.outcome === 'cancelled') return 'other';
  return 'open';
}

// ── BAIKAL MOB (2026-10-19) ─────────────────────────────────
// 응답 모양은 백엔드 algorithms/baikal.py · main.baikal_current 와 같다.
// 못 읽으면 null — 화면은 지어낸 상태 대신 "읽지 못함"을 쓴다.

export type BaikalSystem = {
  key: string;
  name_ko?: string;
  role_ko?: string;
  order?: number;
  status: 'ok' | 'degraded' | 'down' | 'undetermined';
  status_ko?: string;
  reason: string;
  scope_ko?: string;
  evidence_class: 'measured' | 'estimated' | 'proxy';
  readings?: Record<string, unknown>;
  on_request?: string[];
};

export type BaikalLoopLink = Record<string, string | number | null | undefined> & { key: string };

export type BaikalTransition = {
  id: number;
  observed_at: string;
  subject: string;
  from_status: string | null;
  to_status: string;
  reason: string | null;
};

export type BaikalSnapshot = {
  available: true;
  observed_at: string;
  systems: BaikalSystem[];
  summary: { counts: Record<string, number>; total: number };
  loop: {
    state: 'measuring' | 'awaiting' | 'empty' | 'undetermined';
    text: string;
    links: BaikalLoopLink[];
    earliest_due: string | null;
  };
  transitions: BaikalTransition[];
  snapshot_age_minutes: number | null;
  stale: boolean;
};

export type BaikalResult =
  | BaikalSnapshot
  | { available: false; transitions: BaikalTransition[] };

export async function getBaikal(): Promise<BaikalResult | null> {
  const d = await getJson<Record<string, unknown>>('/api/baikal?transitions=30');
  if (!d || typeof d.available !== 'boolean') return null;
  if (!d.available) {
    return { available: false, transitions: Array.isArray(d.transitions) ? (d.transitions as BaikalTransition[]) : [] };
  }
  if (!Array.isArray(d.systems) || !d.loop) return null;
  return d as unknown as BaikalSnapshot;
}
