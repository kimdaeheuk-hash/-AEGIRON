const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
export const API_BASE = BASE;

// 백엔드 쓰기(POST) 엔드포인트는 X-API-Key 인증이 걸려있음.
// 빌드타임에 공개되는 값이라 진짜 민감한 관리자 키가 아니라, 신뢰 클라이언트인
// 이 프론트엔드가 봇/스크래퍼와 구분되기 위한 최소한의 게이트임을 유의.
export function apiWriteHeaders(json = true): HeadersInit {
  const headers: Record<string, string> = {};
  if (json) headers['Content-Type'] = 'application/json';
  const key = process.env.NEXT_PUBLIC_API_KEY;
  if (key) headers['X-API-Key'] = key;
  return headers;
}

// ── 공통 타입 ────────────────────────────────────────────────
export interface Country {
  country: string;
  name?: string;
  risk_score: number;
  tier?: string;
  layer_scores?: Record<string, number>;
  // coverage_tier: "curated"(Tier-1, 손으로 다듬은 14개국) | "auto"(Tier-2, country_iso3로
  // 자동발견된 국가). lat/lng: world_countries 캐시 좌표 — Tier-2 지도 표시에 씀.
  coverage_tier?: 'curated' | 'auto';
  lat?: number | null;
  lng?: number | null;
}

export interface StreamEvent {
  id?: string;
  title?: string;
  text?: string;
  source?: string;
  confidence?: number;
  layer?: string;
  timestamp?: string;
  [key: string]: unknown;
}

export interface Outbreak {
  id?: number;
  event_id?: string;
  event_name?: string;
  event_date?: string;
  milestone?: string;
  description?: string;
  source?: string;
  source_type?: string;
  created_at?: string;
}

export interface ChainWarning {
  disease?: string;
  trigger_metric?: string;
  chain?: string[];
  lead_days?: number;
  korea_pathway?: string;
}

export interface AlertItem {
  label?: string;
  metric?: string;
  layer?: string;
  score?: number;
  tier?: string;
  message?: string;
  source?: string;
  evidence?: string[];
}

export interface TierSummaryEntry {
  cap: number | null;
  total: number;
  suppressed: number;
}

export interface AlertDashboard {
  top?: AlertItem[];
  hidden_count?: number;
}

export interface PredictionAccuracy {
  total_verified: number;
  correct: number;
  accuracy: number | null;
  mean_lead_days: number | null;
}

export interface VerifiedPrediction {
  id: number;
  predicted_at: string;
  country: string;
  disease: string;
  risk_score: number;
  basis: string[];
  verified_at: string | null;
  actual_result: string | null;
  lead_days: number | null;
  correct: boolean | null;
}

export interface DashboardData {
  generated_at: string;
  screen1_global_map: {
    gai: number;
    tier: string;
    countries: Country[];
  };
  screen2_event_stream: {
    events: StreamEvent[];
    total: number;
  };
  screen3_timeline: {
    active_outbreaks: Outbreak[];
  };
  screen4_country_ranking: {
    top20: Country[];
  };
  screen5_forecast: {
    score_7d: number;
    score_14d: number;
    tier_7d: string;
    tier_14d: string;
    chain_warnings: ChainWarning[];
    top_alerts: AlertItem[];
    prediction_track_record: {
      accuracy: PredictionAccuracy;
      recent_verified: VerifiedPrediction[];
    };
  };
  screen6_alert_center: {
    dashboard: AlertDashboard | null;
    tier_summary: Record<string, TierSummaryEntry> | null;
  };
}

export async function fetchDashboard(): Promise<DashboardData> {
  const res = await fetch(`${BASE}/api/dashboard`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<DashboardData>;
}

// ── 발원지 카탈로그 — 큐레이션 8개 도시 + World Bank 실제 전세계 국가 ──
// tier="auto" 국가는 위험도(er)·여객량(pax)이 중립 기본값이고 실측이 아님
// (note 참고). curated만 실제 발병사례 기반 값.
export interface OriginCity {
  id: string; nm: string; iso2: string | null; region: string | null;
  lon: number; lat: number; er: number; pax: number; hrs: number;
  note: string; tier: 'curated' | 'auto';
}

export async function fetchOrigins(): Promise<OriginCity[]> {
  const res = await fetch(`${BASE}/api/patient-zero/origins`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return (await res.json() as { origins: OriginCity[] }).origins;
}

// ── 팬데믹 리스크 계량화(㉓) ──────────────────────────────────
// BlueDot의 '탐지'와 Metabiota의 '계량화' 사이 빈 시장. 노출 지수는 절대
// 확률이 아니라 상대 비교용 모델 지표임(is_probability=false)을 UI에서도
// 반드시 그대로 표기해야 함 — 보험·금융이 확률로 오해하면 안 됨.
export interface CountryExposure {
  country: string;
  name: string;
  coverage_tier: 'curated' | 'auto';
  exposure_index: number;
  components: {
    signal_pressure: number;
    vulnerability: number;
    spread_potential: number;
  };
  has_active_signal: boolean;
  is_probability: false;
  weights_calibrated: false;
  vulnerability_source: 'real_data' | 'seed_fallback';
  percentile?: number;
}

export interface RiskQuantification {
  countries: CountryExposure[];
  empirical_basis: {
    verified_lead_time_cases: number;
    mean_observed_lead_days: number | null;
    note: string;
  };
  disclaimer: string;
}

export async function fetchRiskQuantification(): Promise<RiskQuantification> {
  const res = await fetch(`${BASE}/api/risk-quantification`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<RiskQuantification>;
}

// ── 일일 브리핑(㊱) — 홈페이지 뉴스·팟캐스트·유튜브 공통 방송 러시트 ──────
// 포맷은 '표현 방식'만 바꾸고 숫자·등급·출처 같은 사실은 불변. is_official_alert은
// 항상 false — UI에서도 '공식 경보 아님'을 반드시 그대로 노출해야 함.
export interface BriefSegment {
  segment_id: string;
  kind: 'threat' | 'quiet' | 'promo';
  anchor_script: string;
  lower_third: string;
  visual_cue: string;
  tier: string | null;
  score: number | null;
  sources: string[];
  countries: string[];
  dialogue?: { speaker: string; text: string }[];
  is_future?: boolean;
}

export interface DailyBrief {
  date: string;
  lang: 'ko' | 'en';
  program_name: string;
  format: { id: string; name: string; host_mode: 'single' | 'duo'; description: string };
  available_formats: { id: string; name: string; description: string }[];
  presenter: { name: string; appearance: { outfit: string } };
  presenters: { presenter_id: string; role: string; name: string; gender: 'female' | 'male' }[];
  is_official_alert: false;
  quiet_day: boolean;
  headline: string;
  summary: string;
  segments: BriefSegment[];
  ticker: string[];
  disclosure: string;
  closing: string;
  generation_method: 'template_fallback' | 'llm_polished';
  podcast?: {
    title: string;
    description: string;
    author: string;
    language: string;
    cadence: string;
    audio_timeline: { speaker: string; presenter_id: string; name: string;
      voice: { gender: string; style: string; pace: string }; text: string }[];
    note: string;
  };
}

export async function fetchDailyBrief(lang: 'ko' | 'en' = 'ko', format?: string): Promise<DailyBrief> {
  const qs = new URLSearchParams({ lang });
  if (format) qs.set('format', format);
  const res = await fetch(`${BASE}/api/daily-brief?${qs.toString()}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<DailyBrief>;
}

// ── 기밀 프로그램(HEIMDALL / VALHALLA) — 실측 결과 ──────────────────
// 두 엔드포인트 모두 인증 필수(apiWriteHeaders가 X-API-Key 부착). 응답에
// classification(program_code·담당센터·보안등급)이 붙는다.
export interface Classification {
  program_code: string; program_name_ko: string; stage: number;
  owning_center_ko: string; designation_ko: string;
  classification_ko: string; is_classified: boolean;
  access_control: string; audit_logged: boolean; access_note: string;
}

export interface ReferenceComparisonMetric {
  value: number; reference_mean: number; reference_stdev: number;
  z_score: number; percentile: number;
}

export interface ReferenceComparison {
  n_reference_sequences: number;
  gc_content: ReferenceComparisonMetric | null;
  shannon_entropy_bits: ReferenceComparisonMetric | null;
  cpg_observed_expected: ReferenceComparisonMetric | null;
  note: string;
}

export interface GenomeScreen {
  ok: boolean; reason?: string; clean_length?: number;
  segments_found?: number; analyzed_segment_length?: number;
  ambiguous_bases_removed?: number; ambiguous_fraction?: number; segments_note?: string;
  gc_content?: number; shannon_entropy_bits?: number; cpg_observed_expected?: number;
  max_dinucleotide_deviation?: { dinucleotide: string; oe: number; deviation: number } | null;
  cai_human?: {
    cai: number; codons_scored: number;
    orf_used?: { strand: '+' | '-'; frame: number; start: number; end: number; length: number } | null;
  } | null;
  window_composition_anomaly?: { assessed: boolean; anomaly_count?: number; median_gc?: number };
  restriction_even_spacing?: { even_spacing_flagged: string[]; by_enzyme: Record<string, { sites: number; gap_cv: number | null; even_spacing_signature: boolean }> };
  flags?: { metric: string; note: string }[];
  flag_count?: number; is_screening_only?: boolean; disclaimer?: string;
  reference_comparison?: ReferenceComparison | null;
  classification?: Classification;
}

export async function fetchGenomeScreen(sequence: string, referenceSequences?: string[]): Promise<GenomeScreen> {
  const res = await fetch(`${BASE}/api/synthetic-threat/genome-screen`, {
    method: 'POST', headers: apiWriteHeaders(),
    body: JSON.stringify({ sequence, reference_sequences: referenceSequences?.length ? referenceSequences : undefined }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json() as Promise<GenomeScreen>;
}

export interface BiodefenseReadiness {
  threats_assessed: number;
  coverage: {
    covered: number; uncovered: number; coverage_rate: number | null; uncovered_threats: string[];
    severity_weighted_rate?: number | null;
    priority_uncovered_threats?: { pathogen: string; severity: number | null }[];
  };
  sovereignty: {
    domestically_covered: number; import_dependent_covered: number; sovereignty_rate: number | null; import_dependent_threats: string[];
    severity_weighted_sovereignty_rate?: number | null;
    priority_import_dependent_threats?: { pathogen: string; severity: number | null }[];
  };
  resilience: { single_point_of_failure: string[]; single_point_count: number; import_only_covered: string[] };
  logistics: { assessed: number; items: { name: string; courses: number; projected_demand: number | null; coverage_fraction: number | null; shortfall: number }[] };
  matrix: { pathogen: string; covered: boolean; best_declared_efficacy: number | null; domestic_production: boolean }[];
  threat_category_coverage?: {
    framework: string;
    categories: { category: string; name_ko: string; tracked: boolean; threats_assessed: number }[];
  };
  international_benchmark?: {
    assessed: boolean; reason?: string;
    population?: number; population_source?: string;
    total_antiviral_courses?: number; population_coverage_pct?: number;
    international_target_pct?: number; meets_target?: boolean; note?: string;
  };
  international_reference_systems?: {
    region: string; name: string; established: number | null; summary: string; source: string;
  }[];
  is_illustrative?: boolean; note?: string; disclaimer: string; classification?: Classification;
}

export async function fetchBiodefenseReadiness(): Promise<BiodefenseReadiness> {
  const res = await fetch(`${BASE}/api/biodefense/readiness`, {
    method: 'POST', headers: apiWriteHeaders(), body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json() as Promise<BiodefenseReadiness>;
}

// ── Stage 8 실제 대응제 비축 목록(영속 저장) ────────────────────────
export interface CountermeasureItem {
  id: number; name: string; type: string | null; targets: string[];
  declared_efficacy: number | null; domestic_producible: boolean;
  courses: number | null; population: number | null; attack_rate: number | null;
  created_at: string; updated_at: string;
}

export interface CountermeasureCreateInput {
  name: string; type?: string; targets: string[];
  declared_efficacy?: number; domestic_producible: boolean;
  courses?: number; population?: number; attack_rate?: number;
}

export async function fetchStockpile(): Promise<CountermeasureItem[]> {
  const res = await fetch(`${BASE}/api/biodefense/stockpile`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return (await res.json() as { items: CountermeasureItem[] }).items;
}

export async function createStockpileItem(item: CountermeasureCreateInput): Promise<CountermeasureItem> {
  const res = await fetch(`${BASE}/api/biodefense/stockpile`, {
    method: 'POST', headers: apiWriteHeaders(), body: JSON.stringify(item),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json() as Promise<CountermeasureItem>;
}

export async function deleteStockpileItem(id: number): Promise<void> {
  const res = await fetch(`${BASE}/api/biodefense/stockpile/${id}`, {
    method: 'DELETE', headers: apiWriteHeaders(),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
}

// http(s):// 베이스를 ws(s):// 대시보드 엔드포인트로 변환.
export function dashboardWsUrl(): string | null {
  try {
    const u = new URL(`${BASE}/ws/dashboard`);
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
    return u.toString();
  } catch {
    return null;
  }
}
