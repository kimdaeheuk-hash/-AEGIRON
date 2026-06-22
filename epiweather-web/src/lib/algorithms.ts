// 역병예보 핵심 알고리즘 — 원본 HTML에서 TypeScript로 이식
// 알고리즘 출처: Farrington et al. 1996, SEIR 표준 구획 모델

export function clamp(v: number, a: number, b: number) {
  return Math.max(a, Math.min(b, v));
}

// ── 통계 함수 ─────────────────────────────────────────────────
function erf(x: number) {
  const a1=.254829592,a2=-.284496736,a3=1.421413741,a4=-1.453152027,a5=1.061405429,p=.3275911;
  const s = x < 0 ? -1 : 1;
  x = Math.abs(x);
  const t = 1 / (1 + p * x);
  return s * (1 - (((((a5*t+a4)*t)+a3)*t+a2)*t+a1)*t*Math.exp(-x*x));
}

function pZ(z: number) {
  return Math.max(.0005, 1 - .5 * (1 + erf(z / Math.SQRT2)));
}

function chiCdf(x: number, k: number) {
  if (x <= 0) return 0;
  let s = 0, t = Math.exp(-x / 2);
  for (let i = 0; i < k / 2; i++) { s += t; t *= x / (2 * (i + 1)); }
  return 1 - s;
}

export function combineP(zs: number[]) {
  const ps = zs.map(z => pZ(Math.max(0, z)));
  const chi = -2 * ps.reduce((s, p) => s + Math.log(p), 0);
  return 1 - chiCdf(chi, 2 * ps.length);
}

// ── LCG 랜덤 (seed 기반, 결정론적) ──────────────────────────
let SD = 42;
export function seedRandom(s: number) { SD = s; }
function rnd() { SD = (SD * 1103515245 + 12345) & 0x7fffffff; return SD / 0x7fffffff; }
function gauss() { return Math.sqrt(-2 * Math.log(rnd() + 1e-9)) * Math.cos(2 * Math.PI * rnd()); }

// ── 상수 데이터 ───────────────────────────────────────────────
export const THREAT = {
  flu:    { R0: 2.2, cfr: 0.010, nm: '계절 유행' },
  novel:  { R0: 2.8, cfr: 0.018, nm: '신종 감염병' },
  severe: { R0: 3.4, cfr: 0.028, nm: '고위험 신종' },
} as const;
export type ThreatKey = keyof typeof THREAT;

export const PRESETS = {
  none:   { quar: 0,   dist: 0,   vax: 0,   vaxsp: 0,     anti: 0,   vuln: 0   },
  mild:   { quar: .15, dist: .18, vax: .35, vaxsp: .005,  anti: .3,  vuln: .4  },
  strong: { quar: .30, dist: .32, vax: .55, vaxsp: .008,  anti: .55, vuln: .7  },
} as const;
export type PresetKey = keyof typeof PRESETS;
export type Levers = Record<string, number>;

export const CHANNELS = [
  { nm: '검색·SNS', ic: '🔍', col: '#a78bfa' },
  { nm: 'OTC 판매',  ic: '💊', col: '#fbbf24' },
  { nm: '하수 신호', ic: '🚰', col: '#38bdf8' },
  { nm: '동물 예찰', ic: '🐦', col: '#f472b6' },
  { nm: '이동 변화', ic: '🚇', col: '#34d399' },
  { nm: '1339 통화', ic: '📞', col: '#fb923c' },
];

export const CIVIC = [
  { id: 'citi',  nm: '시민 자가증상', sub: 'CITIZEN',    ic: '🤒', col: '#a78bfa', lead: 14, q: .55, v: .85 },
  { id: 'sewer', nm: '하수 역학',     sub: 'WASTEWATER', ic: '🚰', col: '#38bdf8', lead: 11, q: .92, v: .72 },
  { id: 'otc',   nm: '약국 OTC',      sub: 'PHARMACY',   ic: '💊', col: '#fbbf24', lead: 8,  q: .78, v: .95 },
  { id: 'kit',   nm: '민간 진단키트', sub: 'KIT',        ic: '🧪', col: '#f472b6', lead: 6,  q: .81, v: .60 },
  { id: 'lab',   nm: '민간 검사소',   sub: 'LAB',        ic: '🔬', col: '#34d399', lead: 5,  q: .95, v: .45 },
];

export const CITIES = [
  { id: 'WUH', nm: '우한',       lon: 114.3, lat: 30.6,  er: .85, pax: .55, hrs: 5,  note: '인수공통·고밀도' },
  { id: 'JKT', nm: '자카르타',   lon: 106.8, lat: -6.2,  er: .70, pax: .45, hrs: 7,  note: '가금·열대' },
  { id: 'BKK', nm: '방콕',       lon: 100.5, lat: 13.7,  er: .55, pax: .80, hrs: 6,  note: '관광허브·고여객' },
  { id: 'HAN', nm: '하노이',     lon: 105.8, lat: 21.0,  er: .60, pax: .65, hrs: 5,  note: '가금·접경' },
  { id: 'DAC', nm: '다카',       lon: 90.4,  lat: 23.8,  er: .65, pax: .25, hrs: 7,  note: '니파위험' },
  { id: 'FIH', nm: '킨샤사',     lon: 15.3,  lat: -4.3,  er: .90, pax: .05, hrs: 20, note: '출혈열·취약' },
  { id: 'LOS', nm: '라고스',     lon: 3.4,   lat: 6.5,   er: .80, pax: .08, hrs: 18, note: '인수공통' },
  { id: 'MEX', nm: '멕시코시티', lon: -99.1, lat: 19.4,  er: .60, pax: .12, hrs: 14, note: '신종플루 전례' },
];

export const REGIONS = [
  { id: 'IC', nm: '인천', c: 2, r: 1, x: 120, y: 60,  pop: 3.0,  eld: 16 },
  { id: 'SU', nm: '서울', c: 3, r: 1, x: 175, y: 48,  pop: 9.4,  eld: 18 },
  { id: 'GG', nm: '경기', c: 4, r: 1, x: 205, y: 98,  pop: 13.6, eld: 15 },
  { id: 'GW', nm: '강원', c: 5, r: 1, x: 285, y: 65,  pop: 1.5,  eld: 24 },
  { id: 'CN', nm: '충남', c: 2, r: 2, x: 135, y: 150, pop: 2.1,  eld: 21 },
  { id: 'CB', nm: '충북', c: 4, r: 2, x: 235, y: 135, pop: 1.6,  eld: 20 },
  { id: 'DG', nm: '대구', c: 5, r: 3, x: 295, y: 190, pop: 2.4,  eld: 19 },
  { id: 'JB', nm: '전북', c: 2, r: 3, x: 150, y: 215, pop: 1.8,  eld: 23 },
  { id: 'GN', nm: '경남', c: 4, r: 4, x: 265, y: 245, pop: 3.3,  eld: 19 },
  { id: 'JN', nm: '전남', c: 2, r: 5, x: 155, y: 280, pop: 1.8,  eld: 26 },
  { id: 'BS', nm: '부산', c: 5, r: 5, x: 320, y: 265, pop: 3.3,  eld: 22 },
  { id: 'JJ', nm: '제주', c: 3, r: 7, x: 135, y: 320, pop: .67,  eld: 17 },
];

export const MOBILITY: Record<string, Record<string, number>> = {
  IC: { SU:.9,GG:.8,CN:.4,JJ:.5,BS:.4,DG:.3,CB:.3 },
  SU: { IC:.9,GG:.95,CN:.5,DG:.5,BS:.5,JJ:.4,GW:.5,CB:.5 },
  GG: { SU:.95,IC:.8,CN:.6,DG:.5,BS:.4,JJ:.3,GW:.6,CB:.6 },
  GW: { SU:.5,GG:.6,CB:.4,DG:.3 },
  CN: { GG:.6,SU:.5,IC:.4,JB:.5,CB:.5,DG:.3 },
  CB: { GG:.6,SU:.5,CN:.5,DG:.5,GW:.4 },
  DG: { SU:.5,GG:.5,BS:.7,CB:.5,GN:.6,CN:.3 },
  JB: { CN:.5,GN:.5,JN:.6,GG:.3 },
  GN: { DG:.6,BS:.7,JB:.5,JN:.4,SU:.4 },
  JN: { JB:.6,GN:.4,JJ:.4,SU:.3 },
  BS: { DG:.7,GN:.7,SU:.5,JJ:.45,GG:.4 },
  JJ: { IC:.5,SU:.4,BS:.45,JN:.4,GG:.3 },
};

export const ENTRY_PORTS = [
  { id: 'ICN', nm: '인천국제공항', eng: 'ICN·수도권', base: .82 },
  { id: 'GMP', nm: '김포·기타',    eng: 'GMP',        base: .06 },
  { id: 'PUS', nm: '부산',         eng: 'PUS·영남',   base: .08 },
  { id: 'CJU', nm: '제주',         eng: 'CJU',        base: .04 },
];

export const LEVERS_CONFIG = [
  { k: 'quar',  nm: '입국 검역',  ic: '✈️', sub: '유입 차단', max: .5  },
  { k: 'dist',  nm: '거리두기',   ic: '🧑‍🤝‍🧑', sub: '접촉 감소', max: .6  },
  { k: 'vax',   nm: '백신 목표',  ic: '💉', sub: '커버리지', max: .85 },
  { k: 'vaxsp', nm: '백신 속도',  ic: '⏩', sub: '일일 증가', max: .015 },
  { k: 'anti',  nm: '치료제',     ic: '💊', sub: '치명률↓', max: .8  },
  { k: 'vuln',  nm: '취약보호',   ic: '🛡', sub: '고위험군', max: .9  },
];

// ── Stage 0: 발원지 격자 추론 ─────────────────────────────────
export interface GridCell {
  r: number; c: number;
  zs: number[]; p: number; prob: number;
}
export interface PatientZeroResult {
  oR: number; oC: number;
  cells: GridCell[]; cands: GridCell[]; top: GridCell;
}

export function genPatientZero(seed: number, originId: string): PatientZeroResult {
  SD = seed * 31 + originId.charCodeAt(0);
  const oR = 1 + Math.floor(rnd() * 8);
  const oC = 1 + Math.floor(rnd() * 8);
  const cells: GridCell[] = [];
  for (let r = 0; r < 10; r++) {
    for (let c = 0; c < 10; c++) {
      const d = Math.sqrt((r - oR) ** 2 + (c - oC) ** 2);
      const boost = Math.exp(-d * d / 2);
      const zs: number[] = [];
      for (let i = 0; i < 6; i++) zs.push(boost * (.9 + rnd() * .7) + gauss() * .85);
      cells.push({ r, c, zs, p: combineP(zs), prob: 0 });
    }
  }
  const tot = cells.reduce((s, c) => s + Math.exp(Math.max(0, -Math.log(Math.max(c.p, 1e-9)))), 0);
  cells.forEach(c => { c.prob = Math.exp(Math.max(0, -Math.log(Math.max(c.p, 1e-9)))) / tot; });
  const cands = [...cells].sort((a, b) => b.prob - a.prob).slice(0, 5);
  return { oR, oC, cells, cands, top: cands[0] };
}

// ── Stage 2: 글로벌 유입 ──────────────────────────────────────
export interface GlobalResult {
  city: typeof CITIES[0];
  arrival: number; risk: number; detectLead: number;
  dist: { port: typeof ENTRY_PORTS[0]; w: number }[];
}

function importDay(pax: number, hrs: number, novel: boolean) {
  const r = novel ? .20 : .16, p0 = .00006, cap = .4;
  const dp = pax * 4200, lh = hrs < 10 ? 1 : .68;
  let cum = 0;
  for (let d = 0; d < 150; d++) {
    cum += Math.min(cap, p0 * Math.exp(r * d)) * dp * lh;
    if (cum >= 1) return d;
  }
  return -1;
}

export function computeGlobal(originId: string, threat: ThreatKey): GlobalResult {
  const city = CITIES.find(c => c.id === originId)!;
  const novel = threat !== 'flu';
  const arrival = importDay(city.pax, city.hrs, novel);
  const risk = Math.round(clamp(city.er * 38 + city.pax * 52 + (novel ? 8 : 0), 5, 99));
  const detectLead = Math.round(6 + city.er * 8 + (novel ? 4 : 0));
  const seAsia = ['BKK', 'HAN', 'JKT', 'DAC'].includes(city.id);
  const dist = ENTRY_PORTS.map(port => {
    let w = port.base;
    if (port.id === 'PUS' && seAsia) w += .05;
    if (port.id === 'CJU' && seAsia) w += .03;
    if (port.id === 'ICN' && !seAsia) w += .06;
    return { port, w };
  });
  const sw = dist.reduce((a, x) => a + x.w, 0);
  dist.forEach(x => { x.w /= sw; });
  return { city, arrival, risk, detectLead, dist };
}

// ── Stage 3+4: 국내 확산 ──────────────────────────────────────
export interface DomesticResult {
  I: Record<string, number[]>;
  arr: Record<string, number | null>;
  riskWeek: Record<string, number[]>;
}

export function computeDomestic(threat: ThreatKey): DomesticResult {
  const sp = THREAT[threat];
  const beta = clamp(0.12 + (sp.R0 - 2.2) * 0.07, 0.12, 0.24);
  const origin = 'IC';
  const cur: Record<string, number> = {};
  REGIONS.forEach(x => { cur[x.id] = x.id === origin ? .015 : .0002; });
  const I: Record<string, number[]> = {};
  REGIONS.forEach(x => { I[x.id] = []; });
  const arr: Record<string, number | null> = {};
  REGIONS.forEach(x => { arr[x.id] = null; });
  const seedStart = 104;

  for (let d = 0; d < 160; d++) {
    REGIONS.forEach(x => {
      I[x.id][d] = cur[x.id];
      if (arr[x.id] === null && cur[x.id] >= .25) arr[x.id] = d - seedStart;
    });
    if (d >= seedStart) {
      const nx: Record<string, number> = {};
      REGIONS.forEach(x => {
        let f = beta * cur[x.id] * (1 - cur[x.id]);
        const m = MOBILITY[x.id] || {};
        Object.keys(m).forEach(j => { f += .05 * beta * m[j] * cur[j] * (1 - cur[x.id]); });
        nx[x.id] = clamp(cur[x.id] + f, 0, 1);
      });
      Object.assign(cur, nx);
    }
  }
  const today = 119;
  const riskWeek: Record<string, number[]> = {};
  REGIONS.forEach(x => {
    const a: number[] = [];
    for (let w = 0; w < 5; w++) {
      const dd = Math.min(159, today + w * 7);
      a.push(Math.round(clamp(8 + x.eld * 0.3 + (I[x.id][dd] || 0) * 135, 3, 99)));
    }
    riskWeek[x.id] = a;
  });
  return { I, arr, riskWeek };
}

// ── Stage 5: SEIR 방어 시뮬레이션 ────────────────────────────
export interface SimResult {
  I: number[]; peak: number; pday: number; deaths: number; ofd: number;
}
const N = 5e6, HOSP_CAP = 12000;

export function simulate(lev: Levers, threat: ThreatKey, days = 200): SimResult {
  const sp = THREAT[threat];
  let s = N - 21, e = 20, i = 1, d = 0;
  const sig = 1/4, gam = 1/7, hosp = .08, iv = 21;
  let peak = 0, pday = 0, ofd = 0;
  const I: number[] = [];
  for (let t = 0; t < days; t++) {
    const ramp = clamp((t - iv) / 14, 0, 1);
    const npi = (lev.quar + lev.dist) * ramp;
    const vax = Math.min(lev.vax, Math.max(0, t - iv) * lev.vaxsp);
    const ve = lev.vuln * ramp * .25;
    const Reff = sp.R0 * (1 - clamp(npi, 0, .85)) * (1 - vax * .85) * (1 - ve * .3);
    const bta = Reff * gam;
    const nE = bta * s * i / N, nI = sig * e, nR = gam * i;
    const ecfr = sp.cfr * (1 - lev.anti * .4 * ramp) * (1 - ve);
    s -= nE; e += nE - nI; i += nI - nR; d += nR * ecfr;
    s = Math.max(0, s); e = Math.max(0, e); i = Math.max(0, i);
    I.push(i);
    if (i > peak) { peak = i; pday = t; }
    if (i * hosp > HOSP_CAP) ofd++;
  }
  return { I, peak, pday, deaths: d, ofd };
}

export function currentRt(lev: Levers, threat: ThreatKey) {
  const sp = THREAT[threat];
  return sp.R0 * (1 - clamp(lev.quar + lev.dist, 0, .85)) * (1 - lev.vax * .85) * (1 - lev.vuln * .25 * .3);
}

// ── 색상 유틸 ─────────────────────────────────────────────────
const STOPS: [number, [number, number, number]][] = [
  [0, [30, 58, 95]], [25, [29, 155, 138]], [50, [234, 179, 8]],
  [75, [249, 115, 22]], [100, [214, 40, 40]],
];
function rgbAt(v: number) {
  v = clamp(v, 0, 100);
  for (let i = 0; i < 4; i++) {
    const [a, ca] = STOPS[i], [b, cb] = STOPS[i + 1];
    if (v <= b) {
      const k = (v - a) / (b - a);
      return ca.map((c, j) => Math.round(c + (cb[j] - c) * k)) as [number, number, number];
    }
  }
  return STOPS[4][1];
}
export function riskColor(v: number) {
  const [r, g, b] = rgbAt(v); return `rgb(${r},${g},${b})`;
}
export function statusOf(v: number) {
  return v < 20 ? '안정' : v < 40 ? '관심' : v < 60 ? '주의' : v < 80 ? '경계' : '심각';
}

// SVG 아크 경로
export function arc(x1: number, y1: number, x2: number, y2: number, l: number) {
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2 - l;
  return `M${x1} ${y1} Q${mx} ${my} ${x2} ${y2}`;
}

// 위경도 → SVG 좌표
export function proj(lon: number, lat: number, W = 1000, H = 400) {
  return { x: (lon + 180) / 360 * W, y: (90 - lat) / 180 * (H - 20) + 10 };
}
