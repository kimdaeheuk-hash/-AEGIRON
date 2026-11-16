/**
 * 관측 데이터 보드의 이름 번역 (2026-11-15 캡틴: "영문하고 프랑스어로도 번역 시켜야 해").
 *
 * 백엔드가 질병명·지역명·라벨을 한국어로 내려주므로, en/fr 화면에서는 이 사전으로 표기만 바꾼다.
 * 질병·나라 표는 epiweather-api/algorithms/name_i18n.py 를 옮긴 것이고(생성 시점 2026-11-15),
 * 거기 없는 표기는 그날 운영 스냅숏에 실제로 나온 것만 추가했다.
 *
 * ★ 정직성(name_i18n 과 같은 원칙) ★ 사전에 없는 이름은 원문 그대로 둔다 — 어설프게 옮기면
 * 다른 병·다른 곳으로 읽힌다. 원문이 남아 있으면 번역이 빠졌다는 사실이 눈에 보인다.
 * 보도 요약(raw_text) 같은 자유 문장은 여기서 번역하지 않는다(사전 번역이 불가능).
 */
import type { Locale } from '@/i18n';

type T = { en: string; fr: string };

const DISEASE: Record<string, T> = {
  에볼라: {
    en: 'Ebola',
    fr: 'Ebola',
  },
  이볼라: {
    en: 'Ebola',
    fr: 'Ebola',
  },
  ebola: {
    en: 'Ebola',
    fr: 'Ebola',
  },
  '에볼라 출혈열': {
    en: 'Ebola haemorrhagic fever',
    fr: 'fièvre hémorragique Ebola',
  },
  마르부르크: {
    en: 'Marburg',
    fr: 'Marburg',
  },
  marburg: {
    en: 'Marburg',
    fr: 'Marburg',
  },
  니파바이러스: {
    en: 'Nipah virus',
    fr: 'virus Nipah',
  },
  니파: {
    en: 'Nipah virus',
    fr: 'virus Nipah',
  },
  nipah: {
    en: 'Nipah virus',
    fr: 'virus Nipah',
  },
  라싸열: {
    en: 'Lassa fever',
    fr: 'fièvre de Lassa',
  },
  'lassa fever': {
    en: 'Lassa fever',
    fr: 'fièvre de Lassa',
  },
  엠폭스: {
    en: 'mpox',
    fr: 'mpox',
  },
  mpox: {
    en: 'mpox',
    fr: 'mpox',
  },
  monkeypox: {
    en: 'mpox',
    fr: 'mpox',
  },
  홍역: {
    en: 'measles',
    fr: 'rougeole',
  },
  measles: {
    en: 'measles',
    fr: 'rougeole',
  },
  콜레라: {
    en: 'cholera',
    fr: 'choléra',
  },
  cholera: {
    en: 'cholera',
    fr: 'choléra',
  },
  뎅기열: {
    en: 'dengue',
    fr: 'dengue',
  },
  뎅기: {
    en: 'dengue',
    fr: 'dengue',
  },
  dengue: {
    en: 'dengue',
    fr: 'dengue',
  },
  말라리아: {
    en: 'malaria',
    fr: 'paludisme',
  },
  malaria: {
    en: 'malaria',
    fr: 'paludisme',
  },
  mers: {
    en: 'MERS',
    fr: 'MERS',
  },
  메르스: {
    en: 'MERS',
    fr: 'MERS',
  },
  'covid-19': {
    en: 'COVID-19',
    fr: 'COVID-19',
  },
  코로나19: {
    en: 'COVID-19',
    fr: 'COVID-19',
  },
  한타바이러스: {
    en: 'hantavirus',
    fr: 'hantavirus',
  },
  hantavirus: {
    en: 'hantavirus',
    fr: 'hantavirus',
  },
  안데스바이러스: {
    en: 'Andes virus',
    fr: 'virus Andes',
  },
  '오즈 바이러스': {
    en: 'Oz virus',
    fr: 'virus Oz',
  },
  황열: {
    en: 'yellow fever',
    fr: 'fièvre jaune',
  },
  'yellow fever': {
    en: 'yellow fever',
    fr: 'fièvre jaune',
  },
  디프테리아: {
    en: 'diphtheria',
    fr: 'diphtérie',
  },
  수막염: {
    en: 'meningitis',
    fr: 'méningite',
  },
  소아마비: {
    en: 'polio',
    fr: 'poliomyélite',
  },
  결핵: {
    en: 'tuberculosis',
    fr: 'tuberculose',
  },
  조류인플루엔자: {
    en: 'avian influenza',
    fr: 'grippe aviaire',
  },
  h5n1: {
    en: 'H5N1',
    fr: 'H5N1',
  },
  치쿤구니야: {
    en: 'chikungunya',
    fr: 'chikungunya',
  },
  지카: {
    en: 'Zika',
    fr: 'Zika',
  },
  폐렴: {
    en: 'pneumonia',
    fr: 'pneumonie',
  },
  백일해: {
    en: 'pertussis',
    fr: 'coqueluche',
  },
  마버그열: {
    en: 'Marburg virus disease',
    fr: 'maladie à virus Marburg',
  },
  a형간염: {
    en: 'hepatitis A',
    fr: 'hépatite A',
  },
  렙토스피라증: {
    en: 'leptospirosis',
    fr: 'leptospirose',
  },
  장티푸스: {
    en: 'typhoid',
    fr: 'typhoïde',
  },
};

/** 에볼라 하위 계통 — 표기가 제각각(분디부교·분두비기요·붕디부고·Bundibugyo)이라 패턴으로 잡는다. */
const BUNDIBUGYO = /bundibugyo|분디부교|분두비기요|붕디부[고교]/i;
const BUNDIBUGYO_NAME: T = { en: 'Ebola (Bundibugyo)', fr: 'Ebola (Bundibugyo)' };

const PLACE: Record<string, T> = {
  콩고민주공화국: {
    en: 'DR Congo',
    fr: 'RD Congo',
  },
  콩고공화국: {
    en: 'Republic of the Congo',
    fr: 'République du Congo',
  },
  우간다: {
    en: 'Uganda',
    fr: 'Ouganda',
  },
  케냐: {
    en: 'Kenya',
    fr: 'Kenya',
  },
  탄자니아: {
    en: 'Tanzania',
    fr: 'Tanzanie',
  },
  르완다: {
    en: 'Rwanda',
    fr: 'Rwanda',
  },
  부룬디: {
    en: 'Burundi',
    fr: 'Burundi',
  },
  에티오피아: {
    en: 'Ethiopia',
    fr: 'Éthiopie',
  },
  소말리아: {
    en: 'Somalia',
    fr: 'Somalie',
  },
  남수단: {
    en: 'South Sudan',
    fr: 'Soudan du Sud',
  },
  수단: {
    en: 'Sudan',
    fr: 'Soudan',
  },
  차드: {
    en: 'Chad',
    fr: 'Tchad',
  },
  니제르: {
    en: 'Niger',
    fr: 'Niger',
  },
  나이지리아: {
    en: 'Nigeria',
    fr: 'Nigéria',
  },
  가나: {
    en: 'Ghana',
    fr: 'Ghana',
  },
  기니: {
    en: 'Guinea',
    fr: 'Guinée',
  },
  기니비사우: {
    en: 'Guinea-Bissau',
    fr: 'Guinée-Bissau',
  },
  적도기니: {
    en: 'Equatorial Guinea',
    fr: 'Guinée équatoriale',
  },
  라이베리아: {
    en: 'Liberia',
    fr: 'Liberia',
  },
  시에라리온: {
    en: 'Sierra Leone',
    fr: 'Sierra Leone',
  },
  세네갈: {
    en: 'Senegal',
    fr: 'Sénégal',
  },
  말리: {
    en: 'Mali',
    fr: 'Mali',
  },
  부르키나파소: {
    en: 'Burkina Faso',
    fr: 'Burkina Faso',
  },
  코트디부아르: {
    en: 'Côte d’Ivoire',
    fr: 'Côte d’Ivoire',
  },
  토고: {
    en: 'Togo',
    fr: 'Togo',
  },
  베냉: {
    en: 'Benin',
    fr: 'Bénin',
  },
  카메룬: {
    en: 'Cameroon',
    fr: 'Cameroun',
  },
  중앙아프리카공화국: {
    en: 'Central African Republic',
    fr: 'République centrafricaine',
  },
  가봉: {
    en: 'Gabon',
    fr: 'Gabon',
  },
  앙골라: {
    en: 'Angola',
    fr: 'Angola',
  },
  잠비아: {
    en: 'Zambia',
    fr: 'Zambie',
  },
  짐바브웨: {
    en: 'Zimbabwe',
    fr: 'Zimbabwe',
  },
  말라위: {
    en: 'Malawi',
    fr: 'Malawi',
  },
  모잠비크: {
    en: 'Mozambique',
    fr: 'Mozambique',
  },
  남아프리카공화국: {
    en: 'South Africa',
    fr: 'Afrique du Sud',
  },
  마다가스카르: {
    en: 'Madagascar',
    fr: 'Madagascar',
  },
  이집트: {
    en: 'Egypt',
    fr: 'Égypte',
  },
  모로코: {
    en: 'Morocco',
    fr: 'Maroc',
  },
  알제리: {
    en: 'Algeria',
    fr: 'Algérie',
  },
  튀니지: {
    en: 'Tunisia',
    fr: 'Tunisie',
  },
  리비아: {
    en: 'Libya',
    fr: 'Libye',
  },
  한국: {
    en: 'South Korea',
    fr: 'Corée du Sud',
  },
  북한: {
    en: 'North Korea',
    fr: 'Corée du Nord',
  },
  일본: {
    en: 'Japan',
    fr: 'Japon',
  },
  홍콩: {
    en: 'Hong Kong',
    fr: 'Hong Kong',
  },
  대만: {
    en: 'Taiwan',
    fr: 'Taïwan',
  },
  싱가포르: {
    en: 'Singapore',
    fr: 'Singapour',
  },
  말레이시아: {
    en: 'Malaysia',
    fr: 'Malaisie',
  },
  미얀마: {
    en: 'Myanmar',
    fr: 'Birmanie',
  },
  라오스: {
    en: 'Laos',
    fr: 'Laos',
  },
  네팔: {
    en: 'Nepal',
    fr: 'Népal',
  },
  스리랑카: {
    en: 'Sri Lanka',
    fr: 'Sri Lanka',
  },
  아프가니스탄: {
    en: 'Afghanistan',
    fr: 'Afghanistan',
  },
  아랍에미리트: {
    en: 'United Arab Emirates',
    fr: 'Émirats arabes unis',
  },
  페루: {
    en: 'Peru',
    fr: 'Pérou',
  },
  콜롬비아: {
    en: 'Colombia',
    fr: 'Colombie',
  },
  멕시코: {
    en: 'Mexico',
    fr: 'Mexique',
  },
  에리트레아: {
    en: 'Eritrea',
    fr: 'Érythrée',
  },
  지부티: {
    en: 'Djibouti',
    fr: 'Djibouti',
  },
  모리타니: {
    en: 'Mauritania',
    fr: 'Mauritanie',
  },
  나미비아: {
    en: 'Namibia',
    fr: 'Namibie',
  },
  보츠와나: {
    en: 'Botswana',
    fr: 'Botswana',
  },
  감비아: {
    en: 'Gambia',
    fr: 'Gambie',
  },
  중국: {
    en: 'China',
    fr: 'Chine',
  },
  인도: {
    en: 'India',
    fr: 'Inde',
  },
  파키스탄: {
    en: 'Pakistan',
    fr: 'Pakistan',
  },
  방글라데시: {
    en: 'Bangladesh',
    fr: 'Bangladesh',
  },
  베트남: {
    en: 'Vietnam',
    fr: 'Viêt Nam',
  },
  캄보디아: {
    en: 'Cambodia',
    fr: 'Cambodge',
  },
  필리핀: {
    en: 'Philippines',
    fr: 'Philippines',
  },
  인도네시아: {
    en: 'Indonesia',
    fr: 'Indonésie',
  },
  태국: {
    en: 'Thailand',
    fr: 'Thaïlande',
  },
  사우디아라비아: {
    en: 'Saudi Arabia',
    fr: 'Arabie saoudite',
  },
  예멘: {
    en: 'Yemen',
    fr: 'Yémen',
  },
  이라크: {
    en: 'Iraq',
    fr: 'Irak',
  },
  이란: {
    en: 'Iran',
    fr: 'Iran',
  },
  브라질: {
    en: 'Brazil',
    fr: 'Brésil',
  },
  아르헨티나: {
    en: 'Argentina',
    fr: 'Argentine',
  },
  아이티: {
    en: 'Haiti',
    fr: 'Haïti',
  },
  미국: {
    en: 'United States',
    fr: 'États-Unis',
  },
  영국: {
    en: 'United Kingdom',
    fr: 'Royaume-Uni',
  },
  프랑스: {
    en: 'France',
    fr: 'France',
  },
  독일: {
    en: 'Germany',
    fr: 'Allemagne',
  },
  사모아: {
    en: 'Samoa',
    fr: 'Samoa',
  },
  파푸아뉴기니: {
    en: 'Papua New Guinea',
    fr: 'Papouasie-Nouvelle-Guinée',
  },
  '중국 북부': {
    en: 'northern China',
    fr: 'nord de la Chine',
  },
  '러시아 시베리아': {
    en: 'Siberia, Russia',
    fr: 'Sibérie, Russie',
  },
  '러시아 이르쿠츠크': {
    en: 'Irkutsk, Russia',
    fr: 'Irkoutsk, Russie',
  },
  이르쿠츠크: {
    en: 'Irkutsk',
    fr: 'Irkoutsk',
  },
  러시아: {
    en: 'Russia',
    fr: 'Russie',
  },
  '수단 다르푸르': {
    en: 'Darfur, Sudan',
    fr: 'Darfour, Soudan',
  },
  'WHO 서태평양지역': {
    en: 'WHO Western Pacific Region',
    fr: 'Région OMS du Pacifique occidental',
  },
  '서태평양 지역': {
    en: 'Western Pacific',
    fr: 'Pacifique occidental',
  },
  서태평양지역: {
    en: 'Western Pacific',
    fr: 'Pacifique occidental',
  },
  서태평양: {
    en: 'Western Pacific',
    fr: 'Pacifique occidental',
  },
  아프리카: {
    en: 'Africa',
    fr: 'Afrique',
  },
  '방글라데시 로힝야 난민캠프': {
    en: 'Rohingya refugee camps, Bangladesh',
    fr: 'camps de réfugiés rohingyas, Bangladesh',
  },
  시리아: {
    en: 'Syria',
    fr: 'Syrie',
  },
};

const LABEL: Record<string, T> = {
  '시베리아 야말(러시아)': {
    en: 'Yamal, Siberia (Russia)',
    fr: 'Iamal, Sibérie (Russie)',
  },
  아이슬란드: {
    en: 'Iceland',
    fr: 'Islande',
  },
  '알래스카 노스슬로프(미국)': {
    en: 'North Slope, Alaska (US)',
    fr: 'North Slope, Alaska (États-Unis)',
  },
  '캐나다 북극권': {
    en: 'Canadian Arctic',
    fr: 'Arctique canadien',
  },
  그린란드: {
    en: 'Greenland',
    fr: 'Groenland',
  },
  '북극군도(레졸루트, 캐나다)': {
    en: 'Arctic Archipelago (Resolute, Canada)',
    fr: 'Archipel arctique (Resolute, Canada)',
  },
  '스발바르(노르웨이)': {
    en: 'Svalbard (Norway)',
    fr: 'Svalbard (Norvège)',
  },
  '남극 반도(H5N1 야생동물)': {
    en: 'Antarctic Peninsula (H5N1 in wildlife)',
    fr: 'Péninsule Antarctique (H5N1 chez la faune)',
  },
  'SARS-CoV-2(공개시퀀스)': {
    en: 'SARS-CoV-2 (open sequences)',
    fr: 'SARS-CoV-2 (séquences ouvertes)',
  },
  급증: {
    en: 'surge',
    fr: 'hausse',
  },
  감소: {
    en: 'decline',
    fr: 'baisse',
  },
  신규발생: {
    en: 'new outbreak',
    fr: 'nouveau foyer',
  },
  진행중: {
    en: 'ongoing',
    fr: 'en cours',
  },
  종료: {
    en: 'ended',
    fr: 'terminé',
  },
  불명: {
    en: 'unclear',
    fr: 'indéterminé',
  },
};

/** 긴 이름부터 바꿔야 '콩고민주공화국'이 '콩고'로 먼저 잘리지 않는다. */
const PLACE_KEYS = Object.keys(PLACE).sort((a, b) => b.length - a.length);

const HANGUL = /[\uac00-\ud7a3]/;

export function hasHangul(s: string | null | undefined): boolean {
  return !!s && HANGUL.test(s);
}

function norm(s: string): string {
  return s.trim().toLowerCase().replace(/\s+/g, ' ');
}

/** 질병명 하나. 모르면 원문. */
function oneDisease(raw: string, locale: 'en' | 'fr'): string {
  if (BUNDIBUGYO.test(raw)) return BUNDIBUGYO_NAME[locale];
  const hit = DISEASE[norm(raw)];
  if (hit) return hit[locale];
  for (const [k, v] of Object.entries(DISEASE)) {
    if (k.length >= 3 && norm(raw).includes(k)) return v[locale];
  }
  return raw;
}

/** 질병명. '홍역, 백일해'·'콜레라·장티푸스'처럼 묶인 표기는 나눠서 옮긴다. */
export function diseaseName(raw: string | null, locale: Locale): string | null {
  if (!raw || locale === 'ko') return raw;
  const lab = LABEL[raw.trim()];
  if (lab) return lab[locale];
  return raw
    .split(/(\s*[,·]\s*)/)
    .map((part) => (/^\s*[,·]\s*$/.test(part) || !part ? part : oneDisease(part, locale)))
    .join('');
}

/** 지역 문자열 — 아는 지명만 바꾸고 나머지는 둔다. '및'은 접속어로 옮긴다. */
export function placeName(raw: string | null, locale: Locale): string | null {
  if (!raw || locale === 'ko' || !hasHangul(raw)) return raw;
  const lab = LABEL[raw.trim()];
  if (lab) return lab[locale];
  let out = raw;
  for (const k of PLACE_KEYS) {
    if (out.includes(k)) out = out.split(k).join(PLACE[k][locale]);
  }
  return out.replace(/\s*및\s*/g, locale === 'en' ? ' and ' : ' et ');
}

/** 고정 라벨(극지 지역·유전체 빌드·사건 유형). 없으면 질병명 → 지명 순으로 시도. */
export function labelName(raw: string | null, locale: Locale): string | null {
  if (!raw || locale === 'ko') return raw;
  const lab = LABEL[raw.trim()];
  if (lab) return lab[locale];
  const d = diseaseName(raw, locale);
  return d !== raw ? d : placeName(raw, locale);
}

/**
 * 문장 안의 질병명 → 화면 언어 (2026-11-16, 캡틴 '번역들이 꼬인 거 같은데').
 * CDC 여행경보·WHO DON 제목처럼 출처가 영문만 주거나, 추출 원문이 한·영으로 섞인 문장에 쓴다.
 * 사전의 한국어 키와 그 영문 표기를 함께 찾아 가장 긴 일치를 고른다. 조류인플루엔자 아형(H9N2 등)은 붙여 둔다.
 * 못 찾으면 null(지어내지 않음).
 */
function wordIn(hay: string, needle: string): boolean {
  let i = hay.indexOf(needle);
  while (i >= 0) {
    const before = hay[i - 1] ?? ' ';
    const after = hay[i + needle.length] ?? ' ';
    if (!/[a-z]/.test(before) && !/[a-z]/.test(after)) return true;
    i = hay.indexOf(needle, i + 1);
  }
  return false;
}

export function diseaseIn(text: string | null | undefined, locale: Locale): string | null {
  if (!text) return null;
  const sub = /\b(H\d{1,2}N\d{1,2})\b/i.exec(text)?.[1]?.toUpperCase();
  if (BUNDIBUGYO.test(text)) return locale === 'ko' ? '에볼라(분디부교)' : BUNDIBUGYO_NAME[locale];
  const low = text.toLowerCase();
  let best: { ko: string; v: T; len: number } | null = null;
  for (const [ko, v] of Object.entries(DISEASE)) {
    if (!HANGUL.test(ko)) continue;
    const en = v.en.toLowerCase();
    // 영문은 낱말 경계로(‘summers’ 안의 ‘mers’ 를 메르스로 읽지 않게), 한국어는 부분 일치(조사가 붙는다)
    const hits = [low.includes(ko) ? ko.length : 0, en.length >= 4 && wordIn(low, en) ? en.length : 0];
    const len = Math.max(...hits);
    if (len && (!best || len > best.len)) best = { ko, v, len };
  }
  if (!best) return null;
  const name = locale === 'ko' ? best.ko : best.v[locale];
  return sub && !name.includes(sub) ? `${name} ${sub}` : name;
}

/**
 * 한국어가 섞인 짧은 제목을 en/fr 로 (2026-11-16). 아는 질병명·지명만 바꾸고 나머지는 둔다.
 * 예: '에볼라 DRC 2026' → 'Ebola DRC 2026'. ko 이거나 한글이 없으면 그대로.
 */
export function koTitleTo(raw: string | null, locale: Locale): string | null {
  if (!raw || locale === 'ko' || !hasHangul(raw)) return raw;
  let out = raw;
  const keys = Object.keys(DISEASE)
    .filter((k) => HANGUL.test(k))
    .sort((a, b) => b.length - a.length);
  for (const k of keys) if (out.includes(k)) out = out.split(k).join(DISEASE[k][locale]);
  for (const [k, v] of Object.entries(TITLE_WORDS)) if (out.includes(k)) out = out.split(k).join(v[locale]);
  out = out.replace(/(\d+)차/g, (_, n) => (locale === 'en' ? `#${n}` : `n°${n}`));
  const placed = placeName(out, locale) ?? out;
  return placed.charAt(0).toUpperCase() + placed.slice(1);
}

/** 옛 시드 제목(발병 타임라인 백필)에만 나오는 지명·낱말. */
const TITLE_WORDS: Record<string, T> = {
  글로벌: { en: 'global', fr: 'mondial' },
  케랄라: { en: 'Kerala', fr: 'Kerala' },
  에콰퇴르: { en: 'Équateur', fr: 'Équateur' },
  북키부: { en: 'North Kivu', fr: 'Nord-Kivu' },
  '우한 초기': { en: 'Wuhan early cluster', fr: 'Wuhan, premier foyer' },
};
