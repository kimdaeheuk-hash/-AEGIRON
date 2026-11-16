/**
 * 서버가 한국어로 조립해 보내는 문구를 화면 언어로 (2026-11-16, 캡틴 '번역들이 꼬인 거 같은데' · '다른 곳도 살펴봐').
 *
 * 서버는 경보 라벨·근거 문장·위험 단계·유의사항을 한국어로 만들고 DB 에도 그대로 저장한다(원본은 바꾸지 않는다).
 * 화면이 표시할 때만 옮긴다. 원칙:
 * - 아는 틀(고정 문구·숫자 자리)만 옮긴다. 숫자·식별자는 그대로 싣는다.
 * - 모르는 문장은 지어서 옮기지 않는다 — 부르는 쪽이 '원문(한국어)' 표시와 함께 원문을 둔다(isUntranslated).
 * 경보 라벨 조각 표는 백엔드 algorithms/name_i18n.py 의 _LAYER·_LABEL_PHRASE 와 같은 내용이다.
 */
import type { Locale } from '@/i18n';
import { countryLabel, isoInEnglish, isosInEnglish } from './countryNames';
import { diseaseIn, diseaseName, hasHangul, placeName } from './observationNames';

type T = { en: string; fr: string };

/** 위험 단계 — gai._tier('🔴 위험'·'🟠 경보'·'🟡 주의'·'🟢 정상')와 대시보드 단계어. */
const TIER: Record<string, T> = {
  위험: { en: 'Critical', fr: 'Critique' },
  경보: { en: 'Alert', fr: 'Alerte' },
  주의: { en: 'Watch', fr: 'Vigilance' },
  정상: { en: 'Normal', fr: 'Normal' },
};

export function tierName(raw: string | null | undefined, locale: Locale): string {
  if (!raw) return '';
  if (locale === 'ko') return raw;
  let out = raw;
  for (const [ko, v] of Object.entries(TIER)) out = out.split(ko).join(v[locale]);
  return out;
}

const LAYER: Record<string, T> = {
  '설명불가 신호': { en: 'Unexplained signal', fr: 'Signal inexpliqué' },
  공식신호: { en: 'Official signal', fr: 'Signal officiel' },
  비공식신호: { en: 'Unofficial signal', fr: 'Signal non officiel' },
  행동신호: { en: 'Behavioural signal', fr: 'Signal comportemental' },
  환경신호: { en: 'Environmental signal', fr: 'Signal environnemental' },
  동물신호: { en: 'Animal signal', fr: 'Signal animal' },
  설명불가: { en: 'Unexplained', fr: 'Inexpliqué' },
};

const LABEL_PHRASE: Record<string, T> = {
  '의료물자 수입 동시 급증': {
    en: 'Medical-supply imports surging together',
    fr: 'Importations de matériel médical en hausse simultanée',
  },
  '고위험 병원체 보도': { en: 'High-risk pathogen reports', fr: 'Signalements de pathogènes à haut risque' },
  '종합 위험도(GAI 기반)': { en: 'Composite risk (GAI-based)', fr: 'Risque composite (basé sur le GAI)' },
  '보고 급감': { en: 'reporting drop', fr: 'chute des déclarations' },
  '개 매체': { en: ' outlets', fr: ' médias' },
  종합: { en: 'composite', fr: 'composite' },
  지역불명: { en: 'location unknown', fr: 'localisation inconnue' },
  질병불명: { en: 'disease unknown', fr: 'maladie inconnue' },
  품목: { en: 'products', fr: 'produits' },
};

const byLength = (o: Record<string, T>) => Object.entries(o).sort((a, b) => b[0].length - a[0].length);

/**
 * 경보 라벨. '설명불가 신호 · 이르쿠츠크, 러시아 (원인불명 폐렴)' 의 지명·질병명은 사전으로, 나머지 조각은 표로.
 * 'KAZ' 같은 ISO3 는 나라 이름으로 바꾸지 않는다(라벨의 식별자다).
 */
export function alertLabel(raw: string | null | undefined, locale: Locale): string {
  if (!raw) return '';
  if (locale === 'ko' || !hasHangul(raw)) return raw;
  let out = raw;
  const m = /^(설명불가 신호) · (.+?) \((.+)\)$/.exec(out);
  if (m) {
    const where = m[2] === '지역불명' ? m[2] : (placeName(m[2], locale) ?? m[2]);
    const what = m[3] === '질병불명' ? m[3] : (diseaseName(m[3], locale) ?? m[3]);
    out = `${m[1]} · ${where} (${what})`;
  }
  for (const [ko, v] of [...byLength(LAYER), ...byLength(LABEL_PHRASE)]) {
    if (out.includes(ko)) out = out.split(ko).join(v[locale]);
  }
  if (hasHangul(out)) out = placeName(out, locale) ?? out;
  if (hasHangul(out)) out = diseaseName(out, locale) ?? out;
  return out;
}

/** 근거 문장 틀 — 숫자 자리는 그대로 옮겨 싣는다. */
const EVIDENCE: { re: RegExp; en: (m: RegExpExecArray) => string; fr: (m: RegExpExecArray) => string }[] = [
  {
    re: /^(.+?) 가 동시에 평소 대비 급증\(최대 ([\d.]+)배\)$/,
    en: (m) => `${m[1]} surged together versus their usual level (up to ×${m[2]})`,
    fr: (m) => `${m[1]} en hausse simultanée par rapport à l’habitude (jusqu’à ×${m[2]})`,
  },
  {
    re: /^수입액은 관세청 신고 실측치이나, '발병 대비'라는 해석은 추론\(프록시\)이다/,
    en: () =>
      'Import values are measured customs declarations, but reading them as “outbreak preparation” is an inference (proxy) — routine restocking, price swings and seasonal demand produce the same pattern',
    fr: () =>
      'Les montants importés sont des déclarations douanières mesurées, mais y voir une « préparation à une épidémie » est une inférence (indicateur indirect) — réassort courant, variations de prix et demande saisonnière produisent le même motif',
  },
  {
    re: /^무역통계는 신고·집계 지연이 약 (\d+)개월이라 실시간 신호가 아니다/,
    en: (m) =>
      `Trade statistics lag about ${m[1]} months in reporting, so this is not a real-time signal — it confirms preparation months ago, not what is happening now`,
    fr: (m) =>
      `Les statistiques commerciales ont environ ${m[1]} mois de retard de déclaration : ce n’est pas un signal en temps réel, mais la confirmation a posteriori d’une préparation datant de plusieurs mois`,
  },
  {
    re: /^단일 품목 급증은 후보로 올리지 않는다/,
    en: () => 'A surge in a single product is not raised as a candidate — only two or more surging together',
    fr: () => 'La hausse d’un seul produit n’est pas retenue — seulement deux produits ou plus en hausse simultanée',
  },
  {
    re: /^최신 달\((.+?)\)은 신고국이 적어 제외하고 (.+?)까지 반영했다/,
    en: (m) =>
      `The latest month (${m[1]}) had too few reporting countries and was excluded; data up to ${m[2]} is used — more recent values are not in this alert`,
    fr: (m) =>
      `Le dernier mois (${m[1]}) comptait trop peu de pays déclarants et a été exclu ; les données jusqu’à ${m[2]} sont utilisées — les valeurs plus récentes ne figurent pas dans cette alerte`,
  },
  {
    re: /^품목마다 반영한 최신 달이 달라/,
    en: () => 'Products use different latest months, so the joint surge may compare different months',
    fr: () =>
      'Les produits n’utilisent pas le même dernier mois : la hausse conjointe peut comparer des mois différents',
  },
  {
    re: /^원시 이상도 ([\d.]+)점 × 출처신뢰도 ([\d.]+) = ([\d.]+)점(?: → 경보 점수 ([\d.]+)점으로 제한)?/,
    en: (m) => `Raw anomaly ${m[1]} × source trust ${m[2]} = ${m[3]}${m[4] ? ` → alert score capped at ${m[4]}` : ''}`,
    fr: (m) =>
      `Anomalie brute ${m[1]} × fiabilité de la source ${m[2]} = ${m[3]}${m[4] ? ` → score d’alerte plafonné à ${m[4]}` : ''}`,
  },
];

/** 근거 한 줄. 모르는 틀이면 원문 그대로 — isUntranslated 로 부르는 쪽이 표시를 붙인다. */
export function evidenceLine(raw: string, locale: Locale): string {
  if (locale === 'ko' || !hasHangul(raw)) return raw;
  for (const e of EVIDENCE) {
    const m = e.re.exec(raw);
    if (m) return e[locale](m);
  }
  return raw;
}

export function isUntranslated(text: string, locale: Locale): boolean {
  return locale !== 'ko' && hasHangul(text);
}

/** 주간 유입 보고서 서버 유의사항 중 화면 사전(R.caveats·basis)이 이미 옮겨 싣는 것. */
const KNOWN_CAVEATS = [
  /^연결 = /,
  /^유입 노출 지수는 순위용 지수이며 확률이 아님/,
  /^이상 신호 = 확인이 필요한 신호/,
  /^경유 유입은 지수에 반영되지 않음/,
  /^이웃 나라 주간 추세의 확률은 표본/,
];

/** 화면 사전이 다루지 않는 새 유의사항만 — en/fr 에서 원문으로 덧붙일 것. */
export function extraCaveats(caveats: string[]): string[] {
  return caveats.filter((c) => !KNOWN_CAVEATS.some((re) => re.test(c)));
}

/** '2026년 01월' → '2026-01' (en/fr). */
export function isoMonth(raw: string, locale: Locale): string {
  if (locale === 'ko') return raw;
  return raw.replace(/(\d{4})년\s*(\d{1,2})월/g, (_, y: string, m: string) => `${y}-${m.padStart(2, '0')}`);
}

/** 나라 이름 한 칸 — ISO3 가 있으면 그것으로, 없으면 받은 이름을 지명 사전으로. */
export function countryCell(iso3: string | null | undefined, name: string | null | undefined, locale: Locale): string {
  return (
    countryLabel(iso3, locale) ?? (name ? (locale === 'ko' ? name : (placeName(name, locale) ?? name)) : (iso3 ?? '—'))
  );
}

/**
 * CDC 여행경보 제목 → 화면 언어 (2026-11-16, 캡틴 '번역들이 꼬인 거 같은데').
 * CDC 는 영문 제목만 준다('Ebola Bundibugyo Virus Disease in Ituri and Nord-Kivu Provinces of the
 * Democratic Republic of the Congo'). ko/fr 은 '질병 · 나라 (지역)'으로 짧게 쓴다. 지역 이름은 고유명사라
 * 원문 표기를 둔다. 나라가 여럿이면 모두 싣는다. 질병이나 나라를 못 읽으면 원문 그대로(지어내지 않음). en 은 원문.
 */
export function cdcHeadline(headline: string | null, locale: Locale): string | null {
  if (!headline || locale === 'en') return headline;
  const disease = diseaseIn(headline, locale);
  const countries = isosInEnglish(headline)
    .map((iso) => countryLabel(iso, locale))
    .filter((c): c is string => !!c);
  if (!disease || !countries.length) return headline;
  const m = /\bin (.+?) (?:provinces?|regions?|states?|districts?|departments?|counties) of\b/i.exec(headline);
  const regions = m ? m[1].replace(/,? and /g, '·').replace(/, /g, '·') : null;
  const where = countries.join('·');
  return regions ? `${disease} · ${where} (${regions})` : `${disease} · ${where}`;
}

/**
 * GDACS 재난 경보 제목 → ko/fr. 'Red notification for tropical cyclone MURASU-26. Population affected by …'
 * → '열대저기압 MURASU-26 · GDACS 적색'. 틀이 안 맞으면 원문.
 */
const GDACS_TYPE: Record<string, { ko: string; fr: string }> = {
  'tropical cyclone': { ko: '열대저기압', fr: 'cyclone tropical' },
  earthquake: { ko: '지진', fr: 'séisme' },
  flood: { ko: '홍수', fr: 'inondation' },
  drought: { ko: '가뭄', fr: 'sécheresse' },
  volcano: { ko: '화산', fr: 'volcan' },
  'forest fire': { ko: '산불', fr: 'feu de forêt' },
  wildfire: { ko: '산불', fr: 'feu de forêt' },
};
const GDACS_LEVEL: Record<string, { ko: string; fr: string }> = {
  red: { ko: '적색', fr: 'rouge' },
  orange: { ko: '주황', fr: 'orange' },
  green: { ko: '녹색', fr: 'vert' },
};

export function gdacsTitle(title: string | null, locale: Locale): string | null {
  if (!title || locale === 'en') return title;
  const m =
    /^(Red|Orange|Green) (?:notification|alert) for (tropical cyclone|earthquake|flood|drought|volcano|forest fire|wildfire)\s+([^.]*?)(?:\.|$)/i.exec(
      title,
    );
  if (!m) return title;
  const type = GDACS_TYPE[m[2].toLowerCase()][locale];
  const level = GDACS_LEVEL[m[1].toLowerCase()][locale];
  const name = m[3].trim();
  return locale === 'ko' ? `${type} ${name} · GDACS ${level}` : `${type} ${name} · GDACS ${level}`;
}

/**
 * 나라 이름 문자열(영문 'Democratic Republic of the Congo, Uganda' 또는 한국어 '콩고민주공화국, 우간다') → 화면 언어.
 * 쉼표로 나눈 조각이 **전부** 나라로 읽힐 때만 바꾼다(도시·지역이 섞이면 원문 — 지어내지 않음).
 */
export function countryText(
  raw: string | null | undefined,
  iso3: string | null | undefined,
  locale: Locale,
): string | null {
  if (iso3 && /^[A-Z]{3}$/.test(iso3) && raw && !raw.includes(',')) return countryLabel(iso3, locale) ?? raw;
  if (!raw) return iso3 ? (countryLabel(iso3, locale) ?? iso3) : null;
  if (hasHangul(raw)) return locale === 'ko' ? raw : (placeName(raw, locale) ?? raw);
  const parts = raw.split(/\s*,\s*(?:and\s+)?|\s+and\s+/).filter(Boolean);
  const names = parts.map((p) => {
    const iso = isoInEnglish(p);
    return iso && p.trim().length > 1 ? countryLabel(iso, locale) : null;
  });
  return names.every(Boolean) ? (names as string[]).join(locale === 'ko' ? ', ' : ', ') : raw;
}
