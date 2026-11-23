/**
 * 발할라 대응제 공백 지도 — /api/valhalla/gap-map 을 서버에서 읽는다 (2026-11-23).
 *
 * 캡틴: "치료제나 백신 같은 게 없는 항목들이 많을 거야" → 빈칸이 한눈에 보이게.
 * 칸 상태는 백엔드 판정 그대로: approved · clinical · none · undetermined · unsearchable.
 * '없음'은 그 등록부에 없다는 뜻이고, '판정 안 함'은 못 봤다는 뜻이다 — 화면도 둘을 다른 표시로 그린다.
 * 조회 실패는 null(판정 안 함).
 */
import type { Locale } from '@/i18n';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';

type J = Record<string, unknown>;
const str = (v: unknown): string | null => (typeof v === 'string' && v.trim() ? v : null);
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

export type GapStatus = 'approved' | 'clinical' | 'none' | 'undetermined' | 'unsearchable';
const STATUSES: GapStatus[] = ['approved', 'clinical', 'none', 'undetermined', 'unsearchable'];
const asStatus = (v: unknown): GapStatus =>
  typeof v === 'string' && (STATUSES as string[]).includes(v) ? (v as GapStatus) : 'undetermined';

export type GapCell = { status: GapStatus; label: string };
export type GapRow = {
  id: string;
  name: string;
  family: string;
  basis: string;
  gap: boolean;
  vaccine: GapCell;
  therapeutic: GapCell;
  fda: GapCell;
  diagnostic: GapCell;
  domestic: GapCell;
};
export type GapMap = {
  rows: GapRow[];
  pathogenCount: number;
  gapCount: number;
  gapNames: string[];
  gapRule: string;
  trialsAgeHours: number | null;
} | null;

function cell(v: unknown): GapCell {
  const c = (v && typeof v === 'object' ? v : {}) as J;
  return { status: asStatus(c.status), label: str(c.label) ?? '—' };
}

export async function getGapMap(locale: Locale): Promise<GapMap> {
  let body: J;
  try {
    const res = await fetch(`${API_BASE}/api/valhalla/gap-map`, {
      next: { revalidate: 900 },
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
  const rows: GapRow[] = (Array.isArray(body.rows) ? (body.rows as J[]) : []).map((r, i) => {
    const cells = (r.cells && typeof r.cells === 'object' ? r.cells : {}) as J;
    return {
      id: str(r.key) ?? String(i),
      name: (locale === 'ko' ? str(r.ko) : str(r.en)) ?? str(r.ko) ?? '—',
      family: str(r.family) ?? '—',
      basis: str(r.basis_ko) ?? '',
      gap: r.countermeasure_gap === true,
      vaccine: cell(cells.vaccine),
      therapeutic: cell(cells.therapeutic),
      fda: cell(cells.fda),
      diagnostic: cell(cells.diagnostic),
      domestic: cell(cells.domestic),
    };
  });
  return {
    rows,
    pathogenCount: num(body.pathogen_count) ?? rows.length,
    gapCount: num(body.gap_count) ?? rows.filter((r) => r.gap).length,
    gapNames: Array.isArray(body.gap_pathogens)
      ? (body.gap_pathogens as unknown[]).filter((x): x is string => typeof x === 'string')
      : [],
    gapRule: str(body.gap_rule_ko) ?? '',
    trialsAgeHours: num(body.trials_age_hours),
  };
}
