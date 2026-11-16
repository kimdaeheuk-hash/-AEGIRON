/**
 * 데이터 상품 페이지(/data) 데이터 — 보유량·카탈로그·실적표 (2026-11-16, 캡틴 "판매할 수 있게 전부 셋팅").
 *
 * 운영 서버의 /api/data-inventory · /api/datasets · /api/track-record 를 읽는다. 지어내지 않는다:
 * 조회 실패는 null(화면: 판정 안 함). 상업 상태(allowed/review/blocked)는 서버 카탈로그가 준 그대로.
 */
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';

type J = Record<string, unknown>;

async function getJson(path: string): Promise<J | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: 900 },
      headers: { accept: 'application/json' },
      signal: AbortSignal.timeout(20_000),
    });
    if (!res.ok) return null;
    const body: unknown = await res.json();
    return body && typeof body === 'object' ? (body as J) : null;
  } catch {
    return null;
  }
}

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}
function str(v: unknown): string | null {
  return typeof v === 'string' && v.trim() ? v.trim() : null;
}

export type License = 'allowed' | 'derived' | 'review' | 'blocked' | 'by_layer';

export type Dataset = {
  id: string;
  title: string;
  description: string;
  sources: string;
  license: License;
  licenseNote: string;
  measuredVsDerived: string;
  rows: number | null;
  first: string | null;
  last: string | null;
  days: number | null;
  layers: { layer: string; source: string; license: License; note: string }[];
  sampleJson: string;
  sampleCsv: string;
};

export type Holding = { id: string; label: string; rows: number | null; first: string | null; days: number | null };

export type TrackRecord = {
  predictions: {
    total: number | null;
    resolved: number | null;
    correct: number | null;
    incorrect: number | null;
  } | null;
  ledger: { measured: number | null; ahead: number | null; meanLead: number | null; falseAlarms: number | null } | null;
  weekly: { scored: number | null; enough: boolean | null } | null;
  alertsByMonth: { month: string; total: number; sent: number }[] | null;
};

export type DataShop = {
  datasets: Dataset[] | null;
  holdings: Holding[] | null;
  signalsLog: { lines: number | null; sizeMb: number | null; first: string | null } | null;
  earliest: string | null;
  computedAt: string | null;
  track: TrackRecord | null;
  paidEnabled: boolean;
};

function lic(v: unknown): License {
  return v === 'allowed' || v === 'derived' || v === 'review' || v === 'blocked' || v === 'by_layer' ? v : 'review';
}

export async function getDataShop(): Promise<DataShop> {
  const [cat, inv, tr] = await Promise.all([
    getJson('/api/datasets'),
    getJson('/api/data-inventory'),
    getJson('/api/track-record'),
  ]);

  const datasets: Dataset[] | null =
    cat && Array.isArray(cat.datasets)
      ? (cat.datasets as J[]).map((d) => {
          const cov = (d.coverage ?? null) as J | null;
          const id = str(d.id) ?? '';
          return {
            id,
            title: str(d.title) ?? id,
            description: str(d.description) ?? '',
            sources: str(d.sources) ?? '',
            license: lic(d.license),
            licenseNote: str(d.license_note) ?? '',
            measuredVsDerived: str(d.measured_vs_derived) ?? '',
            rows: cov ? num(cov.rows) : null,
            first: cov ? str(cov.first) : null,
            last: cov ? str(cov.last) : null,
            days: cov ? num(cov.days) : null,
            layers: Array.isArray(d.layers)
              ? (d.layers as J[]).map((l) => ({
                  layer: str(l.layer) ?? '',
                  source: str(l.source) ?? '',
                  license: lic(l.license),
                  note: str(l.note) ?? '',
                }))
              : [],
            sampleJson: `${API_BASE}/api/datasets/${id}/export?format=json`,
            sampleCsv: `${API_BASE}/api/datasets/${id}/export?format=csv`,
          };
        })
      : null;

  const tables = inv && inv.tables && typeof inv.tables === 'object' ? (inv.tables as Record<string, J>) : null;
  const holdings: Holding[] | null = tables
    ? Object.entries(tables)
        .map(([id, t]) => ({
          id,
          label: str(t.label) ?? id,
          rows: num(t.rows),
          first: str(t.first),
          days: num(t.days),
        }))
        .filter((h) => h.rows === null || h.rows > 0)
        .sort((a, b) => (b.rows ?? -1) - (a.rows ?? -1))
    : null;
  const slRaw = inv && inv.files ? ((inv.files as Record<string, J>)['signals_log.jsonl'] ?? null) : null;
  // 파일이 없으면(exists=false) 보유량 칸에 '0줄'로 보이지 않게 아예 뺀다
  const sl = slRaw && slRaw.exists === true ? slRaw : null;

  const pr = tr ? ((tr.predictions_90d ?? null) as J | null) : null;
  const lg = tr ? ((tr.lead_time_ledger ?? null) as J | null) : null;
  const wk = tr ? ((tr.weekly_direction ?? null) as J | null) : null;
  const track: TrackRecord | null = tr
    ? {
        predictions:
          pr && !pr.error
            ? {
                total: num(pr.total),
                resolved: num(pr.resolved),
                correct: num(pr.correct),
                incorrect: num(pr.incorrect),
              }
            : null,
        ledger:
          lg && !lg.error
            ? {
                measured: num(lg.measured_events),
                ahead: num(lg.ahead_of_declaration),
                meanLead: num(lg.mean_lead_days),
                falseAlarms: num(lg.false_alarms),
              }
            : null,
        weekly:
          wk && !wk.error
            ? { scored: num(wk.scored), enough: typeof wk.enough === 'boolean' ? wk.enough : null }
            : null,
        alertsByMonth: Array.isArray(tr.alerts_by_month)
          ? (tr.alerts_by_month as J[]).map((m) => ({
              month: str(m.month) ?? '—',
              total: num(m.total) ?? 0,
              sent: num(m.sent) ?? 0,
            }))
          : null,
      }
    : null;

  return {
    datasets,
    holdings,
    signalsLog: sl
      ? {
          lines: num(sl.lines),
          sizeMb: num(sl.size_bytes) !== null ? Math.round((num(sl.size_bytes) as number) / 1e6) : null,
          first: str(sl.first),
        }
      : null,
    earliest: inv ? str(inv.earliest_record) : null,
    computedAt: inv ? str(inv.computed_at) : null,
    track,
    paidEnabled: Boolean(cat && cat.access && (cat.access as J).paid_enabled),
  };
}
