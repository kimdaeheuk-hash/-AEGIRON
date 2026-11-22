const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
export const API_BASE = BASE;

// ✅ 2026-11-02 해결: 인증 필요 호출은 서버 라우트 프록시로 전환됐다.
// 예전엔 X-API-Key를 NEXT_PUBLIC_API_KEY로 브라우저 번들에 박았는데, 그 값이
// 전 세계에 공개돼 유료 엔드포인트가 무한 호출될 수 있었다(2026-08-19 발견).
// 이제 브라우저는 동일 출처 /api/* 만 부르고, 키는 서버 환경변수
// EPIWEATHER_API_KEY에만 둔다. 프록시 본체는 src/lib/server-api.ts + 각
// src/app/api/**/route.ts. 클라이언트 코드에서 X-API-Key를 직접 다루지 말 것.

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
  evo2_naturalness?: Evo2Naturalness | null;
  msa_homology?: MsaHomology | null;
  classification?: Classification;
}

// Evo2(유전체 파운데이션 모델) 순서 자연스러움. 진핵숙주 감염 바이러스는 학습에서
// 제외돼 판정 불가라 applicable=false로 오고, 그때는 플래그를 올리지 않는다.
export interface Evo2Naturalness {
  ok: boolean; reason?: string;
  match_rate?: number; mean_confidence?: number; bases_compared?: number;
  windows_scored?: number; windows_failed?: number;
  local_anomaly_positions?: number[];
  organism_domain?: string; applicable?: boolean;
  applicability_note?: string; domain_natural_baseline?: number | null;
  suppressed_flags?: string | null;
  flags?: { metric: string; note: string }[];
  flag_count?: number; disclaimer?: string;
}

// 상동성 커버리지 — "자연계에 이 서열 전체를 설명하는 단백질이 있는가".
// DB 검색이라 Evo2와 달리 바이러스에도 유효하다.
export interface MsaHomology {
  ok: boolean; reason?: string;
  best_coverage?: number; total_hits?: number;
  query_length_aa?: number; protein_length_aa?: number;
  hits_by_database?: Record<string, number>;
  top_hits?: { id: string; database: string; coverage: number; identity: number; e_value: number }[];
  translated_region?: { strand: '+' | '-'; frame: number; start: number; end: number; length_bp: number };
  applies_to_viruses?: boolean;
  flags?: { metric: string; note: string }[];
  flag_count?: number; disclaimer?: string;
}

export interface GenomeScreenOptions {
  referenceSequences?: string[];
  useEvo2?: boolean;
  useMsa?: boolean;
  organismDomain?: string;
}

export async function fetchGenomeScreen(sequence: string, opts: GenomeScreenOptions = {}): Promise<GenomeScreen> {
  const { referenceSequences, useEvo2, useMsa, organismDomain } = opts;
  const res = await fetch('/api/synthetic-threat/genome-screen', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sequence,
      reference_sequences: referenceSequences?.length ? referenceSequences : undefined,
      use_evo2: useEvo2 || undefined,
      use_msa: useMsa || undefined,
      organism_domain: organismDomain || undefined,
    }),
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
  amr_watch?: { tracked: boolean; reason: string; entry_criteria: string[]; sentinel_note: string } | null;
  cbrn_sentinel?: { tracked: boolean; layer: string; covers: string[]; method: string; limits: string } | null;
  novel_playbook?: { trigger: string; steps: string[]; basis: string } | null;
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
  const res = await fetch('/api/biodefense/readiness', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}),
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

// ── 매칭원장: 오늘의 판정 ────────────────────────
export interface MatchVerdict {
  id: number; verdict_date: string; pathogen: string;
  coverage_status: string; best_efficacy: number | null;
  covering: string; variant_build: string | null;
  variant_flag: string | null; verdict: string; note: string | null;
}

export async function fetchMatchLedger(): Promise<MatchVerdict[]> {
  const res = await fetch(`${BASE}/api/valhalla/match-ledger?latest_only=true`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return (await res.json() as { entries: MatchVerdict[] }).entries;
}

// ── 국가별 대비 현황판(목연결) ────────────────────────
export interface CountryPosture {
  iso3: string;
  capacity: {
    available: boolean; reason?: string; iso3?: string; year?: number;
    behind_world_count?: number; behind_world?: string[];
    is_self_assessed?: boolean;
  };
  match_verdicts: MatchVerdict[];
  verdict_counts: Record<string, number>;
  note: string;
}

export async function fetchCountryPosture(iso3: string): Promise<CountryPosture> {
  const res = await fetch(`${BASE}/api/valhalla/country-posture?iso3=${encodeURIComponent(iso3)}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json() as Promise<CountryPosture>;
}

export async function createStockpileItem(item: CountermeasureCreateInput): Promise<CountermeasureItem> {
  const res = await fetch('/api/biodefense/stockpile', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(item),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json() as Promise<CountermeasureItem>;
}

export async function deleteStockpileItem(id: number): Promise<void> {
  const res = await fetch(`/api/biodefense/stockpile/${id}`, {
    method: 'DELETE', headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
}
