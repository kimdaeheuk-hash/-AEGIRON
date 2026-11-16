/**
 * 한국 관점 묶음 — /korea 아래 '지금 실제로 관측된 것' (2026-11-16, 관측 데이터 활용 계획 ⑨).
 *
 * 캡틴: "특히 우리나라 아노적인 것도". '안보적인 것'(국가 바이오안보)으로 이해하고 만든다 —
 * 캡틴의 "결정해 주실 것 진행해"에 따라 이 해석으로 진행(다른 뜻이면 바꾼다).
 *
 * 모으는 것(전부 이미 운영 서버가 받는 값):
 *  ① 한국과 항공으로 연결된 관측국(나라별 카드의 한국 연결)  ② 이웃 나라 주간 추세(일본 IDWR 예측)
 *  ③ 국내 설명 불가 신호  ④ 한국 의료물자 수입(관측 저장본, 상위 급증 목록 기준)
 *  ⑤ 안보: 국제 비상 비축이 없는 병원체(대응제 격차) · 고위험 병원체 관련 보도
 *
 * ★ 정직성 ★ 조회 실패는 null(화면: 판정 안 함), 빈 결과는 []. 고위험 병원체 보도는 AI 구조화 추출이라
 * 확진이 아니라고 적는다. 무역은 품목별 상위 10개국만 저장하므로 '한국 없음'은 '급증 상위에 없음'이다.
 */
import type { Locale } from '@/i18n';
import type { CountryCard } from './countryCards';
import { getCountryCards } from './countryCards';
import { getGlobeData } from './globeData';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';
const TIMEOUT_MS = 15_000;

type J = Record<string, unknown>;

async function getJson(path: string): Promise<J | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: 900 },
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

const DOMESTIC = /한국|대한민국|서울|부산|인천|대구|광주|대전|제주|경기|korea|seoul|busan/i;
const HIGH_THREAT =
  /페스트|흑사병|탄저|두창|천연두|에볼라|마버그|마르부르크|니파|라사|plague|anthrax|smallpox|ebola|marburg|nipah|lassa/i;

export type Trend = { label: string; base: string; prob: number | null; target: string };
export type Line = { id: string; title: string; detail: string };

export type KoreaWatch = {
  exposed: CountryCard[] | null;
  koreaAvailable: boolean;
  week: string | null;
  trends: Trend[] | null;
  domestic: Line[] | null;
  trade: Line[] | null;
  gaps: { gaps: string[]; covered: string[]; verified: string | null } | null;
  highThreat: Line[] | null;
};

export async function getKoreaWatch(locale: Locale): Promise<KoreaWatch> {
  const globe = await getGlobeData(locale);
  const [cards, report, unexplained, gap, extracted, trade] = await Promise.all([
    getCountryCards(locale, globe),
    getJson('/api/korea-import-report'),
    getJson('/api/unexplained-signals'),
    getJson('/api/countermeasure-gap'),
    getJson('/api/extracted-signals?limit=200'),
    getJson('/api/observations/history?layer=trade&target=KOR&days=90&limit=200'),
  ]);

  const exposed = cards.koreaAvailable
    ? cards.cards
        .filter((c) => (c.korea.routes ?? 0) > 0 || (c.korea.passengers ?? 0) > 0)
        .sort((a, b) => b.intensity - a.intensity)
        .slice(0, 12)
    : null;

  const trends = report
    ? arr(report.neighbor_trends).map((t) => ({
        label: str(t.label_ko) ?? str(t.series) ?? '—',
        base: `${str(t.base_week) ?? '—'} · ${num(t.base_value)?.toLocaleString('en-US') ?? '—'}`,
        prob: num(t.prob_up),
        target: str(t.target_week) ?? '—',
      }))
    : null;

  const domestic = unexplained
    ? arr(unexplained.alerts)
        .filter((a) => DOMESTIC.test(str(a.location) ?? ''))
        .slice(0, 10)
        .map((a, i) => ({
          id: `u${i}`,
          title: str(a.location) ?? '—',
          detail: [str(a.source), str(a.signal_date) ?? str(a.extracted_at)?.slice(0, 10)].filter(Boolean).join(' · '),
        }))
    : null;

  const tradeRows = trade && Array.isArray(trade.rows) ? (trade.rows as J[]) : null;
  const tradeLines = tradeRows
    ? tradeRows
        .slice()
        .reverse()
        .slice(0, 10)
        .map((r, i) => {
          const m = (r.measured ?? {}) as J;
          const d = (r.derived ?? {}) as J;
          const usd = Array.isArray(m.monthly_import_usd)
            ? num(m.monthly_import_usd[m.monthly_import_usd.length - 1])
            : null;
          return {
            id: `t${i}`,
            title: str(r.metric) ?? '—',
            detail: [
              usd !== null ? `$${usd.toLocaleString('en-US')}` : null,
              num(d.surge_ratio) !== null ? `×${num(d.surge_ratio)}` : null,
              str(m.latest_period),
              r.status === 'undetermined' ? 'undetermined' : null,
            ]
              .filter(Boolean)
              .join(' · '),
          };
        })
    : null;

  const gaps = gap
    ? {
        gaps: Array.isArray(gap.gaps) ? (gap.gaps as unknown[]).map(String) : [],
        covered: Array.isArray(gap.covered) ? (gap.covered as unknown[]).map(String) : [],
        verified: str(gap.table_verified_as_of),
      }
    : null;

  const highThreat = extracted
    ? (() => {
        const by = new Map<string, { n: number; places: Set<string>; last: string }>();
        for (const r of arr(extracted.records)) {
          const d = str(r.disease);
          if (!d || !HIGH_THREAT.test(d)) continue;
          const cur = by.get(d) ?? { n: 0, places: new Set<string>(), last: '' };
          cur.n += 1;
          const loc = str(r.location);
          if (loc) cur.places.add(loc);
          const at = str(r.extracted_at) ?? '';
          if (at > cur.last) cur.last = at;
          by.set(d, cur);
        }
        return [...by.entries()]
          .sort((a, b) => b[1].n - a[1].n)
          .map(([d, v], i) => ({
            id: `h${i}`,
            title: d,
            detail: `${v.n} · ${[...v.places].slice(0, 4).join(', ')} · ${v.last.slice(0, 10)}`,
          }));
      })()
    : null;

  return {
    exposed,
    koreaAvailable: cards.koreaAvailable,
    week: report ? str(report.week) : null,
    trends,
    domestic,
    trade: tradeLines,
    gaps,
    highThreat,
  };
}
