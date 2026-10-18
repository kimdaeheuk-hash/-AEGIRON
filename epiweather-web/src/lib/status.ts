/**
 * 홈 히어로의 가동 배지가 읽는 값 — `/api/status` 의 소스 헬스.
 *
 * 예전 배지는 "21개 소스 실시간 가동 중"이라는 **고정 문구**였다. 소스가 죽어도,
 * 수가 바뀌어도 그대로 떠 있었다. 이제는 운영 백엔드가 실제로 센 값을 그린다.
 * 못 읽으면 null — 화면은 초록 불 대신 '확인하지 못했다'고 쓴다.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ??
  'https://epiweather-api-production.up.railway.app';

/** 수집이 매시 돈다 — 5분이면 충분히 새롭고, 방문마다 백엔드를 두드리지 않는다. */
const REVALIDATE_SECONDS = 300;

export type SourceHealthSummary = {
  /** '진짜 값이 온' 소스만 센다(백엔드 healthy_count — 값없음은 빠진다). */
  ok: number;
  total: number;
};

export async function getSourceHealth(): Promise<SourceHealthSummary | null> {
  try {
    const res = await fetch(`${API_BASE}/api/status`, {
      next: { revalidate: REVALIDATE_SECONDS },
      headers: { accept: 'application/json' },
    });
    if (!res.ok) return null;
    const data = (await res.json()) as {
      source_health?: { healthy_count?: unknown; total_tracked?: unknown };
    };
    const ok = data.source_health?.healthy_count;
    const total = data.source_health?.total_tracked;
    if (typeof ok !== 'number' || typeof total !== 'number' || total <= 0) return null;
    return { ok, total };
  } catch {
    return null;
  }
}
