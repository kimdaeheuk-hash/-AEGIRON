/**
 * 헤임달 변이 원장 — /api/variant-ledger 에서 빌드별 최신 상태와 최근 계통 전이를 읽는다 (2026-11-22).
 *
 * 캡틴: "변이추적으로 발할라를 앞세워". 운영 화면 맨 위에 둔다.
 * 우세 계통·구성비·시퀀스 수는 Nextstrain 공개 빌드에서 읽은 값을 그대로 옮긴 것이고(측정이 아니라 인용),
 * 전이(우세 교체·신규 계통)는 우리 원장이 직전 주기와 비교해 적은 기록이다.
 * 조회 실패는 null(판정 안 함). 빈 원장은 빈 배열 — '전이 없음'과 '못 읽음'을 섞지 않는다.
 */
import type { Locale } from '@/i18n';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';

type J = Record<string, unknown>;

async function getEntries(query: string): Promise<J[] | null> {
  try {
    const res = await fetch(`${API_BASE}/api/variant-ledger?${query}`, {
      next: { revalidate: 900 },
      headers: { accept: 'application/json' },
      signal: AbortSignal.timeout(15_000),
    });
    if (!res.ok) return null;
    const body: unknown = await res.json();
    if (!body || typeof body !== 'object') return null;
    const entries = (body as J).entries;
    return Array.isArray(entries) ? (entries.filter((e) => e && typeof e === 'object') as J[]) : null;
  } catch {
    return null;
  }
}

const str = (v: unknown): string | null => (typeof v === 'string' && v.trim() ? v : null);
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

/** new_clades 는 목록 조회에선 JSON 문자열, 전이 조회에선 목록일 수 있다 — 둘 다 받는다. */
function clades(v: unknown): string[] {
  if (Array.isArray(v)) return v.filter((x): x is string => typeof x === 'string');
  if (typeof v === 'string') {
    try {
      const parsed: unknown = JSON.parse(v);
      return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === 'string') : [];
    } catch {
      return [];
    }
  }
  return [];
}

const LOCALE_TAG: Record<Locale, string> = { ko: 'ko-KR', en: 'en-GB', fr: 'fr-FR' };

function when(iso: unknown, locale: Locale): string {
  const s = str(iso);
  if (!s) return '—';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return `${d.toLocaleString(LOCALE_TAG[locale], {
    timeZone: 'UTC', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })} UTC`;
}

export type VariantStateRow = {
  id: string;
  build: string;
  dominant: string;
  share: string;
  sequences: string;
  observed: string;
};

export type VariantTransitionRow = {
  id: string;
  observed: string;
  build: string;
  kind: string;
  change: string;
};

export type VariantLedger = { state: VariantStateRow[]; transitions: VariantTransitionRow[] } | null;

export async function getVariantLedger(
  locale: Locale,
  transitionNames: Record<string, string>,
): Promise<VariantLedger> {
  const [recent, transitions] = await Promise.all([
    getEntries('limit=50'),
    getEntries('transitions_only=true&limit=10'),
  ]);
  if (recent === null || transitions === null) return null;

  // 최신순으로 오므로 빌드별 첫 행이 최신 상태다.
  const seen = new Set<string>();
  const state: VariantStateRow[] = [];
  for (const e of recent) {
    const build = str(e.build);
    if (!build || seen.has(build)) continue;
    seen.add(build);
    const share = num(e.dominant_share);
    const n = num(e.n_recent);
    state.push({
      id: build,
      build: str(e.label) ?? build,
      dominant: str(e.dominant_clade) ?? '—',
      share: share === null ? '—' : `${(share * 100).toFixed(1)}%`,
      sequences: n === null ? '—' : n.toLocaleString(LOCALE_TAG[locale]),
      observed: when(e.observed_at, locale),
    });
  }

  const rows: VariantTransitionRow[] = transitions.map((e, i) => {
    const kind = str(e.transition) ?? 'none';
    const prev = str(e.prev_dominant);
    const dom = str(e.dominant_clade) ?? '—';
    const added = clades(e.new_clades);
    const change =
      kind === 'dominant_changed' && prev
        ? `${prev} → ${dom}`
        : kind === 'new_clade' && added.length
          ? `+ ${added.join(', ')}`
          : dom;
    return {
      id: `${str(e.id) ?? num(e.id) ?? i}`,
      observed: when(e.observed_at, locale),
      build: str(e.label) ?? str(e.build) ?? '—',
      kind: transitionNames[kind] ?? kind,
      change,
    };
  });

  return { state, transitions: rows };
}
