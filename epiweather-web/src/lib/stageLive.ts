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
 *
 * 언어(2026-11-16, ⑪): 문구는 P[lang] 에서, 서버가 한국어로 준 이름(나라·질병·지명)은 observationNames 로
 * 아는 것만 옮기고 모르는 것은 원문 그대로 둔다(지어내지 않음).
 */
import { API_BASE } from '@/lib/api';
import type { DashLang } from '@/lib/dashLang';
import { KO_ISO3 } from '@/lib/isoGeo';
import { cdcHeadline, countryText, gdacsTitle } from '@/lib/backendText';
import { countryLabel } from '@/lib/countryNames';
import { diseaseName, labelName, placeName } from '@/lib/observationNames';

/** ISO3 → 한국어 나라 이름(가장 짧은 표기), 없으면 코드 그대로 */
const KO_NAME: Record<string, string> = Object.fromEntries(
  Object.entries(KO_ISO3)
    .sort((a, b) => b[0].length - a[0].length)
    .map(([ko, iso]) => [iso, ko]),
);
const PRODUCT: Record<string, Record<DashLang, string>> = {
  masks_breathing: { ko: '마스크·호흡보호구', en: 'Masks & respirators', fr: 'Masques et appareils respiratoires' },
  surgical_gloves: { ko: '수술용 장갑', en: 'Surgical gloves', fr: 'Gants chirurgicaux' },
  diagnostic_reagents: { ko: '진단 시약', en: 'Diagnostic reagents', fr: 'Réactifs de diagnostic' },
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
const NUM_LOCALE: Record<DashLang, string> = { ko: 'ko-KR', en: 'en-US', fr: 'fr-FR' };

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
function day(v: unknown): string {
  const s = str(v);
  return s ? s.slice(0, 10) : DASH;
}

/** 패널 행 문구 — 3개 언어 */
type Phr = {
  recentSeq: (n: string, c: string) => string;
  newClades: (n: string) => string;
  build: (d: string) => string;
  preprint: string;
  unknownPlace: string;
  reported: (s: string) => string;
  mismatch: string;
  aiExtract: string;
  posters: (n: string, capped: boolean) => string;
  surge: string;
  noSurge: string;
  last7: string;
  monthImport: (v: string) => string;
  vsUsual: (v: string) => string;
  lag: string;
  mainDisease: (d: string) => string;
  riskScore: (v: string) => string;
  hourly: string;
  riskSource: string;
  weekValue: (w: string, v: string) => string;
  nextWeek: string;
  probUp: (w: string, p: number) => string;
  idwr: string;
  routes: (n: string, basis2014: boolean, pax: string) => string;
  exposure: (v: string) => string;
  paxSource: string;
  alertLevel: (l: string, title: string) => string;
  windows: (n: string) => string;
  noRecord: string;
  extractedOf: (total: number, n: number) => string;
  opsRecord: string;
  noStockpile: string;
  stockpile: string;
  none: string;
  tableChecked: (d: string) => string;
  icgSource: string;
};

const P: Record<DashLang, Phr> = {
  ko: {
    recentSeq: (n, c) => `최근 서열 ${n}건 · 우세 계통 ${c}`,
    newClades: (n) => `새 계통 ${n}개`,
    build: (d) => `빌드 ${d}`,
    preprint: '프리프린트',
    unknownPlace: '위치 미상',
    reported: (s) => `${s} 보도`,
    mismatch: '기존 질병 패턴과 불일치(모델 판정)',
    aiExtract: 'AI 구조화 추출(원문 확인 필요)',
    posters: (n, capped) => `최근 7일 게시자 ${n}명${capped ? '+(표본 상한)' : ''}`,
    surge: '급증 판정',
    noSurge: '급증 아님',
    last7: '최근 7일',
    monthImport: (v) => `최근 월 수입 $${v}`,
    vsUsual: (v) => `평소 대비 ×${v}`,
    lag: '신고 지연 약 2개월',
    mainDisease: (d) => `대표 질병 ${d}`,
    riskScore: (v) => `위험 점수 ${v}(모델 추정)`,
    hourly: '매시',
    riskSource: '보도 추출 + 취약성 지수',
    weekValue: (w, v) => `${w} 값 ${v}`,
    nextWeek: '다음 주',
    probUp: (w, p) => `${w} 증가 확률 ${p}%(예측)`,
    idwr: '일본 IDWR 표본감시',
    routes: (n, basis2014, pax) =>
      `한국 직항 노선 ${n}(${basis2014 ? 'OpenFlights 2014 기준' : '노선 자료'}) · 인천 여객 ${pax}명`,
    exposure: (v) => `노출 지수 ${v}(추정)`,
    paxSource: '인천공항 운송실적 · OpenFlights',
    alertLevel: (l, title) => `${l} 경보 · ${title}`,
    windows: (n) => `감시창 ${n}개(문헌 잠복기 추정)`,
    noRecord: '기록 없음',
    extractedOf: (total, n) => `최근 ${total}건 중 ${n}건 추출`,
    opsRecord: '운영 추출 기록',
    noStockpile: '국제 비상 비축(WHO ICG) 없음',
    stockpile: '국제 비상 비축 있음',
    none: '없음',
    tableChecked: (d) => `표 확인 ${d}`,
    icgSource: 'WHO ICG 목록 × 운영 추출 질병',
  },
  en: {
    recentSeq: (n, c) => `${n} recent sequences · dominant clade ${c}`,
    newClades: (n) => `${n} new clades`,
    build: (d) => `build ${d}`,
    preprint: 'Preprint',
    unknownPlace: 'Location unknown',
    reported: (s) => `reported by ${s}`,
    mismatch: 'Does not match known disease patterns (model judgement)',
    aiExtract: 'AI structured extraction (check the original)',
    posters: (n, capped) => `${n} posters in the last 7 days${capped ? '+ (sample cap)' : ''}`,
    surge: 'Surge flagged',
    noSurge: 'No surge',
    last7: 'Last 7 days',
    monthImport: (v) => `Latest month imports $${v}`,
    vsUsual: (v) => `×${v} vs usual`,
    lag: 'Reporting lag about 2 months',
    mainDisease: (d) => `Main disease ${d}`,
    riskScore: (v) => `Risk score ${v} (model estimate)`,
    hourly: 'Hourly',
    riskSource: 'Report extraction + vulnerability index',
    weekValue: (w, v) => `${w} value ${v}`,
    nextWeek: 'next week',
    probUp: (w, p) => `P(increase) ${w} ${p}% (forecast)`,
    idwr: 'Japan IDWR sentinel surveillance',
    routes: (n, basis2014, pax) =>
      `${n} direct routes to Korea (${basis2014 ? 'OpenFlights 2014' : 'route data'}) · ${pax} Incheon passengers`,
    exposure: (v) => `Exposure index ${v} (estimate)`,
    paxSource: 'Incheon Airport traffic · OpenFlights',
    alertLevel: (l, title) => `${l} alert · ${title}`,
    windows: (n) => `${n} watch windows (incubation from literature, estimate)`,
    noRecord: 'Not recorded',
    extractedOf: (total, n) => `${n} of the latest ${total} extractions`,
    opsRecord: 'Production extraction log',
    noStockpile: 'No international emergency stockpile (WHO ICG)',
    stockpile: 'International emergency stockpile exists',
    none: 'None',
    tableChecked: (d) => `table checked ${d}`,
    icgSource: 'WHO ICG list × diseases extracted in production',
  },
  fr: {
    recentSeq: (n, c) => `${n} séquences récentes · clade dominant ${c}`,
    newClades: (n) => `${n} nouveaux clades`,
    build: (d) => `version ${d}`,
    preprint: 'Prépublication',
    unknownPlace: 'Lieu inconnu',
    reported: (s) => `signalé par ${s}`,
    mismatch: 'Ne correspond à aucun schéma connu (jugement du modèle)',
    aiExtract: 'Extraction structurée par IA (vérifier la source)',
    posters: (n, capped) => `${n} auteurs sur 7 jours${capped ? '+ (plafond d’échantillon)' : ''}`,
    surge: 'Hausse signalée',
    noSurge: 'Pas de hausse',
    last7: '7 derniers jours',
    monthImport: (v) => `Importations du dernier mois ${v} $`,
    vsUsual: (v) => `×${v} par rapport à l’habitude`,
    lag: 'Délai de déclaration d’environ 2 mois',
    mainDisease: (d) => `Maladie principale ${d}`,
    riskScore: (v) => `Score de risque ${v} (estimation du modèle)`,
    hourly: 'Toutes les heures',
    riskSource: 'Extraction de rapports + indice de vulnérabilité',
    weekValue: (w, v) => `${w} valeur ${v}`,
    nextWeek: 'semaine suivante',
    probUp: (w, p) => `P(hausse) ${w} ${p} % (prévision)`,
    idwr: 'Surveillance sentinelle IDWR (Japon)',
    routes: (n, basis2014, pax) =>
      `${n} liaisons directes vers la Corée (${basis2014 ? 'OpenFlights 2014' : 'données de liaisons'}) · ${pax} passagers à Incheon`,
    exposure: (v) => `Indice d’exposition ${v} (estimation)`,
    paxSource: 'Trafic de l’aéroport d’Incheon · OpenFlights',
    alertLevel: (l, title) => `Alerte ${l} · ${title}`,
    windows: (n) => `${n} fenêtres de veille (incubation d’après la littérature, estimation)`,
    noRecord: 'Non enregistré',
    extractedOf: (total, n) => `${n} des ${total} dernières extractions`,
    opsRecord: 'Journal d’extraction en production',
    noStockpile: 'Pas de stock d’urgence international (ICG de l’OMS)',
    stockpile: 'Stock d’urgence international disponible',
    none: 'Aucun',
    tableChecked: (d) => `tableau vérifié le ${d}`,
    icgSource: 'Liste ICG de l’OMS × maladies extraites en production',
  },
};

/** 행을 만들 때 쓰는 언어 묶음 — 문구·숫자 표기·서버 한국어 이름 옮기기 */
type Ctx = {
  t: Phr;
  fmt: (n: number | null, digits?: number) => string;
  /** 고정 라벨(극지 지역·계통 등) → 질병 → 지명 순으로 아는 것만 옮김 */
  nm: (v: string | null) => string | null;
  dz: (v: string | null) => string | null;
  pl: (v: string | null) => string | null;
};

function ctxOf(lang: DashLang): Ctx {
  const loc = NUM_LOCALE[lang];
  const keep = (f: (v: string) => string | null) => (v: string | null) =>
    !v || lang === 'ko' ? v : (f(v) ?? v);
  return {
    t: P[lang],
    fmt: (n, digits = 0) => (n === null ? DASH : n.toLocaleString(loc, { maximumFractionDigits: digits })),
    nm: keep((v) => labelName(v, lang)),
    dz: keep((v) => diseaseName(v, lang)),
    pl: keep((v) => placeName(v, lang)),
  };
}

type Source = { name: Record<DashLang, string>; path: string; rows: (body: J, c: Ctx, lang: DashLang) => LiveRow[] };

let seq = 0;
function row(r: Omit<LiveRow, 'id'>): LiveRow {
  seq += 1;
  return { id: `r${seq}`, ...r };
}

// ── 단계별 출처 ───────────────────────────────────────────────────────────────

const GENOMIC: Source = {
  name: { ko: '유전체 계통(Nextstrain)', en: 'Genomic lineages (Nextstrain)', fr: 'Lignées génomiques (Nextstrain)' },
  path: '/api/genomic-variants',
  rows: (b, { t, fmt, nm }) =>
    Object.values(b)
      .filter((v): v is J => !!v && typeof v === 'object' && !Array.isArray(v) && (v as J).available === true)
      .slice(0, 4)
      .map((v) =>
        row({
          target: nm(str(v.label)) ?? DASH,
          measured: t.recentSeq(fmt(num(v.n_recent_sequences)), str(v.dominant_clade) ?? DASH),
          derived: num(v.new_clade_count) === null ? DASH : t.newClades(fmt(num(v.new_clade_count))),
          time: t.build(day(v.build_updated)),
          source: 'Nextstrain',
        }),
      ),
};

const BIORXIV: Source = {
  name: {
    ko: '합성생물 프리프린트(bioRxiv)',
    en: 'Synthetic-biology preprints (bioRxiv)',
    fr: 'Prépublications en biologie de synthèse (bioRxiv)',
  },
  path: '/api/synthetic-threat/biorxiv',
  rows: (b, { t }) =>
    arr(b.papers)
      .filter((p) => p.source === 'bioRxiv_REAL') // 대체 자료는 실측이 아님
      .slice(0, 3)
      .map((p) =>
        row({
          target: t.preprint,
          measured: str(p.title) ?? DASH,
          derived: DASH,
          time: day(p.date),
          source: 'bioRxiv(Europe PMC)',
        }),
      ),
};

const UNEXPLAINED: Source = {
  name: { ko: '설명 불가 신호', en: 'Unexplained signals', fr: 'Signaux inexpliqués' },
  path: '/api/unexplained-signals',
  rows: (b, { t, pl }) =>
    arr(b.alerts)
      .slice(0, 4)
      .map((a) =>
        row({
          target: pl(str(a.location)) ?? t.unknownPlace,
          measured: t.reported(str(a.source) ?? DASH),
          derived: t.mismatch,
          time: day(a.signal_date ?? a.extracted_at),
          source: str(a.source) ?? DASH,
        }),
      ),
};

const EXTRACTED: Source = {
  name: { ko: '발생 보도 추출', en: 'Outbreak report extraction', fr: 'Extraction des rapports d’épidémie' },
  path: '/api/extracted-signals?limit=30',
  rows: (b, { t, dz, pl, nm }) => {
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
          target: `${dz(str(r.disease)) ?? DASH} · ${pl(str(r.location)) ?? t.unknownPlace}`,
          measured: `${nm(str(r.signal_type)) ?? DASH} · ${str(r.source) ?? DASH}`,
          derived: t.aiExtract,
          time: day(r.extracted_at),
          source: str(r.source) ?? DASH,
        }),
      );
  },
};

const SOCIAL: Source = {
  name: { ko: 'SNS 게시량(Mastodon)', en: 'Social posts (Mastodon)', fr: 'Publications sociales (Mastodon)' },
  path: '/api/social-signal',
  rows: (b, { t, fmt, nm }) =>
    Object.values(b)
      .filter((v): v is J => !!v && typeof v === 'object' && !Array.isArray(v) && (v as J).available === true)
      .sort((x, y) => (num(y.count_recent) ?? 0) - (num(x.count_recent) ?? 0))
      .slice(0, 5)
      .map((v) =>
        row({
          target: nm(str(v.label)) ?? DASH,
          measured: t.posters(fmt(num(v.count_recent)), v.sample_capped === true),
          derived: v.surge_alert === true ? t.surge : t.noSurge,
          time: t.last7,
          source: 'Mastodon',
        }),
      ),
};

const TRAVEL: Source = {
  name: { ko: 'CDC 여행경보', en: 'CDC travel notices', fr: 'Avis de voyage du CDC' },
  path: '/api/travel-notices',
  rows: (b, { fmt }, lang) =>
    arr(b.high_severity_notices)
      .slice(0, 3)
      .map((n) =>
        row({
          target: cdcHeadline(str(n.headline), lang) ?? DASH,
          measured: `CDC Level ${fmt(num(n.level))}`,
          derived: DASH,
          time: str(n.pub_date)?.slice(5, 16) ?? DASH,
          source: 'CDC Travelers’ Health',
        }),
      ),
};

const TRADE: Source = {
  name: {
    ko: '의료물자 수입(UN Comtrade)',
    en: 'Medical-supply imports (UN Comtrade)',
    fr: 'Importations de fournitures médicales (UN Comtrade)',
  },
  path: '/api/trade-signals',
  rows: (b, { t, fmt, pl }, lang) =>
    Object.entries((b.products ?? {}) as Record<string, unknown>)
      .flatMap(([product, p]) =>
        arr((p as J | null)?.top_surges).map((s) => ({ product, s, ratio: num(s.surge_ratio) ?? 0 })),
      )
      .sort((x, y) => y.ratio - x.ratio)
      .slice(0, 3)
      .map(({ product, s }) => {
        const usd = Array.isArray(s.monthly_import_usd) ? (s.monthly_import_usd as unknown[]).map(num) : [];
        const last = usd.length ? usd[usd.length - 1] : null;
        const iso = str(s.country_iso3) ?? '';
        return row({
          target: `${pl(KO_NAME[iso] ?? null) ?? (iso || DASH)} · ${PRODUCT[product]?.[lang] ?? product}`,
          measured: t.monthImport(fmt(last)),
          derived: t.vsUsual(fmt(num(s.surge_ratio), 2)),
          time: t.lag,
          source: 'UN Comtrade',
        });
      }),
};

const RISK: Source = {
  name: { ko: '나라별 위험지수', en: 'Country risk index', fr: 'Indice de risque par pays' },
  path: '/api/risk-index',
  rows: (b, { t, fmt, dz, pl }, lang) =>
    arr(b.countries)
      .filter((c) => c.has_signal === true)
      .slice(0, 3)
      .map((c) =>
        row({
          // 백엔드 name 은 일부만 한국어('Sudan · 사우디아라비아' 혼용) — ISO3 로 화면 언어 이름을 먼저 (2026-11-16)
          target: countryLabel(str(c.country), lang) ?? pl(str(c.name)) ?? str(c.country) ?? DASH,
          measured: t.mainDisease(dz(str(c.dominant_disease)) ?? DASH),
          derived: t.riskScore(fmt(num(c.risk_score), 1)),
          time: t.hourly,
          source: t.riskSource,
        }),
      ),
};

const IDWR_LABEL: Record<string, Record<'en' | 'fr', string>> = {
  jp_covid: { en: 'Japan COVID-19 sentinel (national, weekly)', fr: 'Japon COVID-19, sentinelle (national, hebdo)' },
  jp_influenza: { en: 'Japan influenza sentinel (national, weekly)', fr: 'Japon grippe, sentinelle (national, hebdo)' },
  jp_rsv: { en: 'Japan RSV sentinel (national, weekly)', fr: 'Japon VRS, sentinelle (national, hebdo)' },
};

const KOREA_TRENDS: Source = {
  name: { ko: '이웃 나라 주간 추세', en: 'Neighbouring-country weekly trends', fr: 'Tendances hebdomadaires d’un pays voisin' },
  path: '/api/korea-import-report',
  rows: (b, { t, fmt }, lang) =>
    arr(b.neighbor_trends)
      .slice(0, 3)
      .map((tr) => {
        const p = num(tr.prob_up);
        const series = str(tr.series) ?? '';
        return row({
          target: (lang === 'ko' ? null : IDWR_LABEL[series]?.[lang]) ?? str(tr.label_ko) ?? DASH,
          measured: t.weekValue(str(tr.base_week) ?? DASH, fmt(num(tr.base_value))),
          derived: p === null ? DASH : t.probUp(str(tr.target_week) ?? t.nextWeek, Math.round(p * 100)),
          time: str(b.week) ?? DASH,
          source: t.idwr,
        });
      }),
};

const KOREA_ROUTES: Source = {
  name: { ko: '한국 유입 경로', en: 'Import routes into Korea', fr: 'Voies d’importation vers la Corée' },
  path: '/api/korea-import-report',
  rows: (b, { t, fmt, pl }) => {
    const conn = (b.connectivity ?? {}) as J;
    return arr(b.top_exposure)
      .slice(0, 4)
      .map((e) =>
        row({
          target: pl(str(e.name)) ?? str(e.country) ?? DASH,
          measured: t.routes(
            fmt(num(e.direct_routes_to_kor)),
            !!str(b.routes_source)?.includes('2014'),
            fmt(num(e.kor_passengers)),
          ),
          derived: t.exposure(fmt(num(e.exposure_index), 1)),
          time: str(b.week) ?? DASH,
          source: str(conn.source) ? t.paxSource : 'OpenFlights',
        }),
      );
  },
};

const DISASTER: Source = {
  name: { ko: '재난 감시창(GDACS)', en: 'Disaster watch windows (GDACS)', fr: 'Fenêtres de veille catastrophes (GDACS)' },
  path: '/api/disaster-watch',
  rows: (b, { t, fmt, pl }, lang) =>
    arr(b.countries)
      .slice(0, 4)
      .map((c) => {
        const w = arr(c.open_windows)[0] ?? {};
        return row({
          target: countryText(str(c.country), str(c.country_iso3), lang) ?? pl(str(c.country)) ?? DASH,
          measured: t.alertLevel(str(w.alert_level) ?? DASH, (gdacsTitle(str(w.title), lang) ?? DASH).slice(0, 70)),
          derived: t.windows(fmt(num(c.window_count))),
          time: day(w.disaster_date),
          source: 'GDACS',
        });
      }),
};

const AI_PIPELINE: Source = {
  name: { ko: '추출 모델 실적', en: 'Extraction model record', fr: 'Bilan des modèles d’extraction' },
  path: '/api/extracted-signals?limit=100',
  rows: (b, { t }) => {
    const recs = arr(b.records);
    const by = new Map<string, { n: number; last: string }>();
    for (const r of recs) {
      const k = str(r.ai_provider) ?? t.noRecord;
      const cur = by.get(k) ?? { n: 0, last: '' };
      cur.n += 1;
      const at = str(r.extracted_at) ?? '';
      if (at > cur.last) cur.last = at;
      by.set(k, cur);
    }
    return [...by.entries()]
      .sort((a, b2) => b2[1].n - a[1].n)
      .map(([k, v]) =>
        row({
          target: k,
          measured: t.extractedOf(recs.length, v.n),
          derived: DASH,
          time: day(v.last),
          source: t.opsRecord,
        }),
      );
  },
};

const COUNTERMEASURE: Source = {
  name: { ko: '대응제 비축 격차', en: 'Countermeasure stockpile gaps', fr: 'Lacunes des stocks de contre-mesures' },
  path: '/api/countermeasure-gap',
  rows: (b, { t, dz }) => {
    const gaps = Array.isArray(b.gaps) ? (b.gaps as unknown[]).map((x) => dz(String(x)) ?? String(x)) : [];
    const covered = Array.isArray(b.covered) ? (b.covered as unknown[]).map((x) => dz(String(x)) ?? String(x)) : [];
    return [
      row({
        target: t.noStockpile,
        measured: gaps.length ? gaps.join(', ') : t.none,
        derived: DASH,
        time: str(b.table_verified_as_of) ? t.tableChecked(str(b.table_verified_as_of) as string) : DASH,
        source: t.icgSource,
      }),
      row({
        target: t.stockpile,
        measured: covered.length ? covered.join(', ') : t.none,
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

export async function loadStageLive(stage: number, lang: DashLang = 'ko'): Promise<StageLive> {
  const sources = STAGE_SOURCES[stage] ?? [];
  const c = ctxOf(lang);
  const bodies = new Map<string, Promise<J | null>>();
  const results = await Promise.all(
    sources.map(async (s) => {
      // 같은 경로는 한 번만 부른다(4·5단계가 같은 유입 보고서를 읽음)
      if (!bodies.has(s.path)) bodies.set(s.path, getJson(s.path));
      const body = await bodies.get(s.path)!;
      if (!body) return { name: s.name[lang], rows: null as LiveRow[] | null };
      try {
        return { name: s.name[lang], rows: s.rows(body, c, lang) };
      } catch {
        return { name: s.name[lang], rows: null };
      }
    }),
  );
  return {
    rows: results.flatMap((r) => r.rows ?? []),
    failures: results.filter((r) => r.rows === null).map((r) => r.name),
  };
}
