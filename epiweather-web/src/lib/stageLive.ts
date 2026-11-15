/**
 * 대시보드 0~8단계 '지금 실제로 관측된 것' 패널의 데이터 (2026-11-15).
 *
 * 관측 데이터 활용 계획 ③: 2~6단계는 운영 API 를 부르지 않는 순수 시뮬레이션이었다. 시뮬레이션은 지우지 않고,
 * 각 단계 위에 그 단계와 같은 질문에 대한 **운영 서버의 실제 관측**을 붙인다.
 *
 * ★ 정직성 ★
 * - 측정값(출처가 준 숫자·등급)과 해석값(우리 모델의 점수·확률·배수)을 다른 칸에 둔다(관측 보드와 같은 규칙).
 * - 조회가 실패한 출처는 행을 지어내지 않고 failures 에 이름을 남긴다 → 화면이 '판정 안 함'으로 적는다.
 * - 출처가 대체 자료(FALLBACK)를 줬으면 실측으로 보이지 않게 버린다(bioRxiv).
 * - 값이 없으면 '—'. 0 으로 채우지 않는다.
 */
import { API_BASE } from '@/lib/api';
import { KO_ISO3 } from '@/lib/isoGeo';

/** ISO3 → 한국어 나라 이름(가장 짧은 표기), 없으면 코드 그대로 */
const KO_NAME: Record<string, string> = Object.fromEntries(
  Object.entries(KO_ISO3)
    .sort((a, b) => b[0].length - a[0].length)
    .map(([ko, iso]) => [iso, ko]),
);
const PRODUCT_KO: Record<string, string> = {
  masks_breathing: '마스크·호흡보호구',
  surgical_gloves: '수술용 장갑',
  diagnostic_reagents: '진단 시약',
};

export type LiveRow = {
  id: string;
  target: string;
  /** 출처가 준 측정값 */
  measured: string;
  /** 우리가 계산한 해석값(추정) — 없으면 '—' */
  derived: string;
  time: string;
  source: string;
};

export type StageLive = { rows: LiveRow[]; failures: string[] };

type J = Record<string, unknown>;

const TIMEOUT_MS = 12_000;
const DASH = '—';

async function getJson(path: string): Promise<J | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
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
function fmt(n: number | null, digits = 0): string {
  return n === null ? DASH : n.toLocaleString('ko-KR', { maximumFractionDigits: digits });
}
function day(v: unknown): string {
  const s = str(v);
  return s ? s.slice(0, 10) : DASH;
}

type Source = { name: string; path: string; rows: (body: J) => LiveRow[] };

let seq = 0;
function row(r: Omit<LiveRow, 'id'>): LiveRow {
  seq += 1;
  return { id: `r${seq}`, ...r };
}

// ── 단계별 출처 ───────────────────────────────────────────────────────────────

const GENOMIC: Source = {
  name: '유전체 계통(Nextstrain)',
  path: '/api/genomic-variants',
  rows: (b) =>
    Object.values(b)
      .filter((v): v is J => !!v && typeof v === 'object' && !Array.isArray(v) && (v as J).available === true)
      .slice(0, 4)
      .map((v) =>
        row({
          target: str(v.label) ?? DASH,
          measured: `최근 서열 ${fmt(num(v.n_recent_sequences))}건 · 우세 계통 ${str(v.dominant_clade) ?? DASH}`,
          derived: num(v.new_clade_count) === null ? DASH : `새 계통 ${fmt(num(v.new_clade_count))}개`,
          time: `빌드 ${day(v.build_updated)}`,
          source: 'Nextstrain',
        }),
      ),
};

const BIORXIV: Source = {
  name: '합성생물 프리프린트(bioRxiv)',
  path: '/api/synthetic-threat/biorxiv',
  rows: (b) =>
    arr(b.papers)
      .filter((p) => p.source === 'bioRxiv_REAL') // 대체 자료는 실측이 아님
      .slice(0, 3)
      .map((p) =>
        row({
          target: '프리프린트',
          measured: str(p.title) ?? DASH,
          derived: DASH,
          time: day(p.date),
          source: 'bioRxiv(Europe PMC)',
        }),
      ),
};

const UNEXPLAINED: Source = {
  name: '설명 불가 신호',
  path: '/api/unexplained-signals',
  rows: (b) =>
    arr(b.alerts)
      .slice(0, 4)
      .map((a) =>
        row({
          target: str(a.location) ?? '위치 미상',
          measured: `${str(a.source) ?? DASH} 보도`,
          derived: '기존 질병 패턴과 불일치(모델 판정)',
          time: day(a.signal_date ?? a.extracted_at),
          source: str(a.source) ?? DASH,
        }),
      ),
};

const EXTRACTED: Source = {
  name: '발생 보도 추출',
  path: '/api/extracted-signals?limit=30',
  rows: (b) => {
    const seen = new Set<string>();
    return arr(b.records)
      .filter((r) => {
        const k = `${r.disease}|${r.location}`;
        if (seen.has(k)) return false;
        seen.add(k);
        return true;
      })
      .slice(0, 4)
      .map((r) =>
        row({
          target: `${str(r.disease) ?? DASH} · ${str(r.location) ?? '위치 미상'}`,
          measured: `${str(r.signal_type) ?? DASH} · ${str(r.source) ?? DASH}`,
          derived: 'AI 구조화 추출(원문 확인 필요)',
          time: day(r.extracted_at),
          source: str(r.source) ?? DASH,
        }),
      );
  },
};

const SOCIAL: Source = {
  name: 'SNS 게시량(Mastodon)',
  path: '/api/social-signal',
  rows: (b) =>
    Object.values(b)
      .filter((v): v is J => !!v && typeof v === 'object' && !Array.isArray(v) && (v as J).available === true)
      .sort((x, y) => (num(y.count_recent) ?? 0) - (num(x.count_recent) ?? 0))
      .slice(0, 5)
      .map((v) =>
        row({
          target: str(v.label) ?? DASH,
          measured: `최근 7일 게시자 ${fmt(num(v.count_recent))}명${v.sample_capped === true ? '+(표본 상한)' : ''}`,
          derived: v.surge_alert === true ? '급증 판정' : '급증 아님',
          time: '최근 7일',
          source: 'Mastodon',
        }),
      ),
};

const TRAVEL: Source = {
  name: 'CDC 여행경보',
  path: '/api/travel-notices',
  rows: (b) =>
    arr(b.high_severity_notices)
      .slice(0, 3)
      .map((n) =>
        row({
          target: str(n.headline) ?? DASH,
          measured: `CDC Level ${fmt(num(n.level))}`,
          derived: DASH,
          time: str(n.pub_date)?.slice(5, 16) ?? DASH,
          source: 'CDC Travelers’ Health',
        }),
      ),
};

const TRADE: Source = {
  name: '의료물자 수입(UN Comtrade)',
  path: '/api/trade-signals',
  rows: (b) =>
    Object.entries((b.products ?? {}) as Record<string, unknown>)
      .flatMap(([product, p]) =>
        arr((p as J | null)?.top_surges).map((s) => ({ product, s, ratio: num(s.surge_ratio) ?? 0 })),
      )
      .sort((x, y) => y.ratio - x.ratio)
      .slice(0, 3)
      .map(({ product, s }) => {
        const usd = Array.isArray(s.monthly_import_usd) ? (s.monthly_import_usd as unknown[]).map(num) : [];
        const last = usd.length ? usd[usd.length - 1] : null;
        return row({
          target: `${KO_NAME[str(s.country_iso3) ?? ''] ?? str(s.country_iso3) ?? DASH} · ${PRODUCT_KO[product] ?? product}`,
          measured: `최근 월 수입 $${fmt(last)}`,
          derived: `평소 대비 ×${fmt(num(s.surge_ratio), 2)}`,
          time: '신고 지연 약 2개월',
          source: 'UN Comtrade',
        });
      }),
};

const RISK: Source = {
  name: '나라별 위험지수',
  path: '/api/risk-index',
  rows: (b) =>
    arr(b.countries)
      .filter((c) => c.has_signal === true)
      .slice(0, 3)
      .map((c) =>
        row({
          target: str(c.name) ?? str(c.country) ?? DASH,
          measured: `대표 질병 ${str(c.dominant_disease) ?? DASH}`,
          derived: `위험 점수 ${fmt(num(c.risk_score), 1)}(모델 추정)`,
          time: '매시',
          source: '보도 추출 + 취약성 지수',
        }),
      ),
};

const KOREA_TRENDS: Source = {
  name: '이웃 나라 주간 추세',
  path: '/api/korea-import-report',
  rows: (b) =>
    arr(b.neighbor_trends)
      .slice(0, 3)
      .map((t) => {
        const p = num(t.prob_up);
        return row({
          target: str(t.label_ko) ?? DASH,
          measured: `${str(t.base_week) ?? DASH} 값 ${fmt(num(t.base_value))}`,
          derived: p === null ? DASH : `${str(t.target_week) ?? '다음 주'} 증가 확률 ${Math.round(p * 100)}%(예측)`,
          time: str(b.week) ?? DASH,
          source: '일본 IDWR 표본감시',
        });
      }),
};

const KOREA_ROUTES: Source = {
  name: '한국 유입 경로',
  path: '/api/korea-import-report',
  rows: (b) => {
    const conn = (b.connectivity ?? {}) as J;
    return arr(b.top_exposure)
      .slice(0, 4)
      .map((e) =>
        row({
          target: str(e.name) ?? str(e.country) ?? DASH,
          measured: `한국 직항 노선 ${fmt(num(e.direct_routes_to_kor))}(${str(b.routes_source)?.includes('2014') ? 'OpenFlights 2014 기준' : '노선 자료'}) · 인천 여객 ${fmt(num(e.kor_passengers))}명`,
          derived: `노출 지수 ${fmt(num(e.exposure_index), 1)}(추정)`,
          time: str(b.week) ?? DASH,
          source: str(conn.source) ? '인천공항 운송실적 · OpenFlights' : 'OpenFlights',
        }),
      );
  },
};

const DISASTER: Source = {
  name: '재난 감시창(GDACS)',
  path: '/api/disaster-watch',
  rows: (b) =>
    arr(b.countries)
      .slice(0, 4)
      .map((c) => {
        const w = arr(c.open_windows)[0] ?? {};
        return row({
          target: str(c.country) ?? str(c.country_iso3) ?? DASH,
          measured: `${str(w.alert_level) ?? DASH} 경보 · ${(str(w.title) ?? DASH).slice(0, 70)}`,
          derived: `감시창 ${fmt(num(c.window_count))}개(문헌 잠복기 추정)`,
          time: day(w.disaster_date),
          source: 'GDACS',
        });
      }),
};

const AI_PIPELINE: Source = {
  name: '추출 모델 실적',
  path: '/api/extracted-signals?limit=100',
  rows: (b) => {
    const recs = arr(b.records);
    const by = new Map<string, { n: number; last: string }>();
    for (const r of recs) {
      const k = str(r.ai_provider) ?? '기록 없음';
      const cur = by.get(k) ?? { n: 0, last: '' };
      cur.n += 1;
      const t = str(r.extracted_at) ?? '';
      if (t > cur.last) cur.last = t;
      by.set(k, cur);
    }
    return [...by.entries()]
      .sort((a, b2) => b2[1].n - a[1].n)
      .map(([k, v]) =>
        row({
          target: k,
          measured: `최근 ${recs.length}건 중 ${v.n}건 추출`,
          derived: DASH,
          time: day(v.last),
          source: '운영 추출 기록',
        }),
      );
  },
};

const COUNTERMEASURE: Source = {
  name: '대응제 비축 격차',
  path: '/api/countermeasure-gap',
  rows: (b) => {
    const gaps = Array.isArray(b.gaps) ? (b.gaps as unknown[]).map(String) : [];
    const covered = Array.isArray(b.covered) ? (b.covered as unknown[]).map(String) : [];
    return [
      row({
        target: '국제 비상 비축(WHO ICG) 없음',
        measured: gaps.length ? gaps.join(', ') : '없음',
        derived: DASH,
        time: str(b.table_verified_as_of) ? `표 확인 ${str(b.table_verified_as_of)}` : DASH,
        source: 'WHO ICG 목록 × 운영 추출 질병',
      }),
      row({
        target: '국제 비상 비축 있음',
        measured: covered.length ? covered.join(', ') : '없음',
        derived: DASH,
        time: DASH,
        source: 'WHO ICG',
      }),
    ];
  },
};

/** 단계 번호 → 그 단계와 같은 질문을 보는 운영 출처 */
export const STAGE_SOURCES: Record<number, Source[]> = {
  0: [GENOMIC, BIORXIV],
  1: [UNEXPLAINED, EXTRACTED],
  2: [SOCIAL],
  3: [TRAVEL, TRADE, RISK],
  4: [KOREA_TRENDS],
  5: [KOREA_ROUTES],
  6: [DISASTER],
  7: [AI_PIPELINE],
  8: [COUNTERMEASURE],
};

export async function loadStageLive(stage: number): Promise<StageLive> {
  const sources = STAGE_SOURCES[stage] ?? [];
  const bodies = new Map<string, Promise<J | null>>();
  const results = await Promise.all(
    sources.map(async (s) => {
      // 같은 경로는 한 번만 부른다(4·5단계가 같은 유입 보고서를 읽음)
      if (!bodies.has(s.path)) bodies.set(s.path, getJson(s.path));
      const body = await bodies.get(s.path)!;
      if (!body) return { name: s.name, rows: null as LiveRow[] | null };
      try {
        return { name: s.name, rows: s.rows(body) };
      } catch {
        return { name: s.name, rows: null };
      }
    }),
  );
  return {
    rows: results.flatMap((r) => r.rows ?? []),
    failures: results.filter((r) => r.rows === null).map((r) => r.name),
  };
}
