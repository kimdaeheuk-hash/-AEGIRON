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
