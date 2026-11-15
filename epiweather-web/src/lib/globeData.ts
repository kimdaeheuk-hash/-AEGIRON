/**
 * 관측 지구본의 점 데이터 (2026-11-15 캡틴: "발병지도를 시각화해 — 지구본에 표시하는 것처럼 · 극지방도 같이").
 *
 * 관측 데이터 보드와 같은 운영 API 를 읽는다(같은 경로·같은 캐시라 fetch 가 한 번으로 합쳐진다).
 * 점은 '보도·관측이 있었던 곳'이지 확진 환자 위치가 아니다. 나라 단위 값은 나라 중앙에 찍는다.
 * 위치를 못 읽은 기록은 찍지 않고 unlocated 로 센다 — 아무 데나 찍지 않는다.
 */
import type { Locale } from '@/i18n';
import { EN_ISO3, KO_ISO3 } from './isoGeo';
import { diseaseName, labelName, placeName } from './observationNames';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';
const REVALIDATE_SECONDS = 900;
const TIMEOUT_MS = 20_000;

export type GlobeLayer = 'event' | 'unexplained' | 'disaster' | 'trade' | 'polar';

export type GlobePoint = {
  id: string;
  layer: GlobeLayer;
  /** 나라 단위 점이면 ISO3 (좌표는 화면이 국경 데이터에서 계산) */
  iso3: string | null;
  /** 지역 단위 점(극지)이면 직접 좌표 */
  lat: number | null;
  lon: number | null;
  title: string;
  /** 이 점에 모인 기록 수 — 점 크기 */
  count: number;
  /** 상세 패널 줄(최대 6) */
  lines: string[];
};

export type GlobeData = {
  points: GlobePoint[];
  unlocated: number;
  /** 하나라도 못 읽은 엔드포인트가 있으면 그 경로 */
  failed: string[];
};

type J = Record<string, unknown>;

async function getJson(path: string): Promise<J | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: REVALIDATE_SECONDS },
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
function clip(s: string | null, n: number): string | null {
  if (!s) return null;
  const flat = s.replace(/\s+/g, ' ').replace(/\*\*/g, '').trim();
  return flat.length > n ? `${flat.slice(0, n - 1)}…` : flat;
}

/** 긴 이름부터 — '남수단'이 '수단'으로, '콩고민주공화국'이 '콩고'로 잘리지 않게. */
const KO_NAMES = Object.keys(KO_ISO3).sort((a, b) => b.length - a.length);

/**
 * 지역 문자열 → ISO3 목록. '콩고민주공화국, 우간다' · 'DRC·우간다' · 'Irkutsk, Russia' · '러시아 이르쿠츠크'.
 * 못 읽으면 빈 배열(찍지 않음).
 */
export function locationIsos(raw: string | null, isoHint: string | null): string[] {
  if (isoHint && /^[A-Z]{3}$/.test(isoHint)) return [isoHint];
  if (!raw) return [];
  const found = new Set<string>();
  let rest = raw;
  for (const name of KO_NAMES) {
    if (rest.includes(name)) {
      found.add(KO_ISO3[name]);
      rest = rest.split(name).join(' ');
    }
  }
  for (const part of rest.split(/[,·/()]|\s+and\s+|\s+및\s+/)) {
    const key = part.trim().toLowerCase();
    if (key && EN_ISO3[key]) found.add(EN_ISO3[key]);
  }
  return [...found];
}

/** ISO3 → 한국어 이름(name_i18n 표를 거꾸로). en/fr 은 그 한국어 이름을 지명 사전으로 옮긴다. */
const KO_NAME: Record<string, string> = Object.fromEntries(
  Object.entries(KO_ISO3)
    .sort((a, b) => a[0].length - b[0].length)
    .reverse()
    .map(([ko, iso]) => [iso, ko]),
);

/** 나라 표시 이름 — 화면 언어로. 사전에 없으면 null(화면이 지도 데이터의 영문명을 쓴다). */
function countryLabel(iso3: string, locale: Locale): string | null {
  const ko = KO_NAME[iso3];
  if (!ko) return null;
  return locale === 'ko' ? ko : placeName(ko, locale);
}

/** 같은 (레이어, 나라)는 한 점으로 합친다. */
class Bucket {
  private map = new Map<string, GlobePoint>();
  add(layer: GlobeLayer, iso3: string, title: string, line: string | null) {
    const id = `${layer}-${iso3}`;
    const p = this.map.get(id) ?? { id, layer, iso3, lat: null, lon: null, title, count: 0, lines: [] };
    p.count += 1;
    if (line && p.lines.length < 6 && !p.lines.includes(line)) p.lines.push(line);
    this.map.set(id, p);
  }
  values(): GlobePoint[] {
    return [...this.map.values()];
  }
}

export async function getGlobeData(locale: Locale): Promise<GlobeData> {
  const paths = {
    events: '/api/extracted-signals?limit=100',
    unexplained: '/api/unexplained-signals',
    disaster: '/api/disaster-watch',
    trade: '/api/trade-signals',
    polar: '/api/polar-watch',
  };
  const [events, unexplained, disaster, trade, polar] = await Promise.all(Object.values(paths).map(getJson));
  const failed = Object.entries({ events, unexplained, disaster, trade, polar })
    .filter(([, b]) => !b)
    .map(([k]) => paths[k as keyof typeof paths]);

  const bucket = new Bucket();
  const name = (iso: string, fallback: string) => countryLabel(iso, locale) ?? fallback;
  let unlocated = 0;

  // 발생 보도 — 같은 질병·장소·출처의 반복 보도는 보드와 같이 최신 1건만
  const seen = new Set<string>();
  for (const r of arr(events?.records)) {
    const k = [str(r.disease), str(r.location), str(r.source)].join('|');
    if (seen.has(k)) continue;
    seen.add(k);
    const isos = locationIsos(str(r.location), str(r.country_iso3));
    if (!isos.length) {
      unlocated += 1;
      continue;
    }
    const disease = diseaseName(str(r.disease), locale) ?? '?';
    const line = [disease, labelName(str(r.signal_type), locale), str(r.source), str(r.extracted_at)?.slice(0, 10)]
      .filter(Boolean)
      .join(' · ');
    for (const iso of isos) bucket.add('event', iso, name(iso, iso), line);
  }

  for (const a of arr(unexplained?.alerts)) {
    const isos = locationIsos(str(a.location), null);
    if (!isos.length) {
      unlocated += 1;
      continue;
    }
    const line = [clip(placeName(str(a.location), locale), 40), str(a.source), str(a.signal_date)]
      .filter(Boolean)
      .join(' · ');
    for (const iso of isos) bucket.add('unexplained', iso, name(iso, iso), line);
  }

  for (const c of arr(disaster?.countries)) {
    const iso = str(c.country_iso3);
    if (!iso) {
      unlocated += 1;
      continue;
    }
    const first = arr(c.open_windows)[0] ?? {};
    const diseases = Array.isArray(c.diseases)
      ? (c.diseases as unknown[]).map((d) => diseaseName(String(d), locale) ?? String(d)).join(', ')
      : null;
    bucket.add('disaster', iso, name(iso, str(c.country) ?? iso), clip(str(first.title), 90));
    if (diseases) bucket.add('disaster', iso, name(iso, str(c.country) ?? iso), diseases);
  }

  for (const s of arr(trade?.top_surges)) {
    const iso = str(s.country_iso3);
    if (!iso) continue;
    const ratio = num(s.surge_ratio);
    bucket.add(
      'trade',
      iso,
      iso,
      [str(s.product), ratio !== null ? `×${ratio.toFixed(2)}` : null].filter(Boolean).join(' '),
    );
  }

  const points = bucket.values();

  // 극지 — 지역 좌표(polar_signals.POLAR_REGIONS 와 같은 값)
  for (const r of arr(polar?.regions)) {
    const region = str(r.region);
    const at = region ? POLAR_COORDS[region] : undefined;
    if (!at) {
      unlocated += 1;
      continue;
    }
    const thaw = (r.thaw ?? {}) as J;
    const score = num(r.polar_watch_score);
    points.push({
      id: `polar-${region}`,
      layer: 'polar',
      iso3: null,
      lat: at[0],
      lon: at[1],
      title: labelName(str(r.name), locale) ?? region ?? '',
      count: Math.max(1, Math.round((score ?? 0) / 20)),
      lines: [
        num(thaw.thaw_days_30d) !== null ? POLAR_TEXT[locale].thaw(String(num(thaw.thaw_days_30d))) : null,
        num(thaw.heat_trend_c) !== null
          ? POLAR_TEXT[locale].anomaly(`${(num(thaw.heat_trend_c) as number) > 0 ? '+' : ''}${num(thaw.heat_trend_c)}`)
          : null,
        score !== null ? POLAR_TEXT[locale].score(String(score)) : null,
      ].filter((x): x is string => !!x),
    });
  }

  return { points, unlocated, failed };
}

const POLAR_TEXT: Record<
  Locale,
  { thaw: (n: string) => string; anomaly: (n: string) => string; score: (n: string) => string }
> = {
  ko: {
    thaw: (n) => `최근 30일 중 영상 ${n}일`,
    anomaly: (n) => `10년 같은 달 평균 대비 ${n}℃`,
    score: (n) => `관찰 점수 ${n} (추정)`,
  },
  en: {
    thaw: (n) => `${n} above-zero days in last 30`,
    anomaly: (n) => `${n}℃ vs same-month 10-yr mean`,
    score: (n) => `watch score ${n} (estimate)`,
  },
  fr: {
    thaw: (n) => `${n} jours au-dessus de zéro sur 30`,
    anomaly: (n) => `${n}℃ vs moyenne du mois sur 10 ans`,
    score: (n) => `score de veille ${n} (estimation)`,
  },
};

/** epiweather-api/algorithms/polar_signals.py POLAR_REGIONS 의 좌표(2026-11-15 복사). */
const POLAR_COORDS: Record<string, [number, number]> = {
  siberia_yamal: [66.5, 68.0],
  alaska_north: [70.2, -148.5],
  canada_arctic: [68.5, -133.5],
  greenland: [72.0, -40.0],
  svalbard: [78.2, 15.6],
  antarctic_peninsula: [-63.0, -57.0],
  arctic_archipelago: [74.7, -94.8],
  iceland: [65.0, -19.0],
};
