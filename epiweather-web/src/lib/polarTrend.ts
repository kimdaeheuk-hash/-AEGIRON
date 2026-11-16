/**
 * 극지 추이 — 관측값 시계열(/api/observations/history?layer=polar)에서 지역별 처음 값 → 최근 값 (2026-11-16, ⑩).
 *
 * 캡틴: "극지지방도 같이 보여줘야 해". 저장은 2026-11-15 부터라 30일이 다 차지 않았다 — 며칠치인지 같이 적는다.
 * 기온·해빙일수는 기상 관측값(Open-Meteo), 이상도는 우리가 계산한 값(같은 달 10년 평균 대비).
 * 조회 실패는 null(판정 안 함). 그 시각에 못 읽은 행(undetermined)은 추이 계산에서 빼고 수를 센다.
 */
import type { Locale } from '@/i18n';
import { placeName } from './observationNames';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';

type J = Record<string, unknown>;

async function getJson(path: string): Promise<J | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: 900 },
      headers: { accept: 'application/json' },
      signal: AbortSignal.timeout(15_000),
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

export type PolarTrendRow = {
  id: string;
  region: string;
  first: string;
  latest: string;
  change: string;
  span: string;
};

const THAW: Record<Locale, (n: string) => string> = {
  ko: (n) => `해빙 ${n}일`,
  en: (n) => `thaw ${n}d`,
  fr: (n) => `dégel ${n} j`,
};

function point(r: J, locale: Locale): string {
  const m = (r.measured ?? {}) as J;
  const d = (r.derived ?? {}) as J;
  const t = num(m.mean_max_c_current);
  const th = num(m.thaw_days_30d);
  const an = num(d.anomaly_c);
  return [
    String(r.observed_at ?? '').slice(0, 10),
    t !== null ? `${t}℃` : null,
    th !== null ? THAW[locale](String(th)) : null,
    an !== null ? `Δ${an > 0 ? '+' : ''}${an}℃` : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

export async function getPolarTrend(
  locale: Locale,
): Promise<{ rows: PolarTrendRow[]; days: number; undetermined: number } | null> {
  const [hist, watch] = await Promise.all([
    getJson('/api/observations/history?layer=polar&days=30&limit=5000'),
    getJson('/api/polar-watch'),
  ]);
  if (!hist || !Array.isArray(hist.rows)) return null;
  const names = new Map<string, string>();
  for (const r of Array.isArray(watch?.regions) ? (watch!.regions as J[]) : []) {
    if (typeof r.region === 'string' && typeof r.name === 'string') {
      names.set(r.region, locale === 'ko' ? r.name : (placeName(r.name, locale) ?? r.name));
    }
  }
  const by = new Map<string, J[]>();
  let undetermined = 0;
  let minAt = '';
  let maxAt = '';
  for (const r of hist.rows as J[]) {
    if (r.status === 'undetermined') {
      undetermined += 1;
      continue;
    }
    const target = String(r.target ?? '');
    if (!target || target === '*') continue;
    (by.get(target) ?? by.set(target, []).get(target)!).push(r);
    const at = String(r.observed_at ?? '');
    if (!minAt || at < minAt) minAt = at;
    const conf = String(r.confirmed_at ?? '');
    if (conf > maxAt) maxAt = conf;
  }
  const rows: PolarTrendRow[] = [...by.entries()].map(([target, rs]) => {
    const first = rs[0];
    const last = rs[rs.length - 1];
    const t0 = num(((first.measured ?? {}) as J).mean_max_c_current);
    const t1 = num(((last.measured ?? {}) as J).mean_max_c_current);
    const h0 = num(((first.measured ?? {}) as J).thaw_days_30d);
    const h1 = num(((last.measured ?? {}) as J).thaw_days_30d);
    const change = [
      t0 !== null && t1 !== null ? `${t1 - t0 >= 0 ? '+' : ''}${Math.round((t1 - t0) * 10) / 10}℃` : null,
      h0 !== null && h1 !== null ? THAW[locale](`${h1 - h0 >= 0 ? '+' : ''}${h1 - h0}`) : null,
    ]
      .filter(Boolean)
      .join(' · ');
    return {
      id: target,
      region: names.get(target) ?? target,
      first: point(first, locale),
      latest: rs.length > 1 ? point(last, locale) : '—',
      change: rs.length > 1 ? change || '—' : '—',
      span: String(rs.length),
    };
  });
  const days = minAt && maxAt ? Math.max(1, Math.round((Date.parse(maxAt) - Date.parse(minAt)) / 86_400_000)) : 0;
  return { rows, days, undetermined };
}
