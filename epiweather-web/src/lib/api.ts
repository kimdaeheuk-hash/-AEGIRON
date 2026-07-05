const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ── 공통 타입 ────────────────────────────────────────────────
export interface Country {
  country: string;
  risk_score: number;
  tier?: string;
  layer_scores?: Record<string, number>;
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
