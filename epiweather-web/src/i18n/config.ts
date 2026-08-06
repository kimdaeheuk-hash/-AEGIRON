/**
 * 다국어 설정 — 한국어 · 영어 · 프랑스어 (캡틴 확정 2026-08-05)
 *
 * 프랑스어를 고른 이유: 아이기론이 실제로 다루는 지역이 불어권이다
 * (콩고민주공화국·기니·차드·중앙아프리카). WHO AFRO 실무어가 영어/불어이고
 * MSF 본부가 제네바·파리다. 스페인어는 고객 후보에 해당 지역이 없어 기각.
 *
 * ★ 구조 원칙 ★
 * 언어를 나중에 붙이려면 페이지를 다 갈아엎어야 한다. 그래서 처음부터
 * 로케일 라우팅(/[locale]/)으로 짜고, 문구는 컴포넌트에서 분리해 사전에 둔다.
 * 네 번째 언어가 필요해지면 사전 파일 하나만 추가하면 끝이다.
 */

export const locales = ['ko', 'en', 'fr'] as const;
export type Locale = (typeof locales)[number];

/** 기본 로케일 — 캡틴이 읽는 언어이자 현재 사이트 언어. */
export const defaultLocale: Locale = 'ko';

/** <html lang="...">과 hreflang에 쓰는 정식 태그. */
export const htmlLang: Record<Locale, string> = {
  ko: 'ko-KR',
  en: 'en',
  fr: 'fr',
};

/** 언어 전환기에 표시할 이름 — 각 언어의 자국어 표기(그게 국제 관행). */
export const localeNames: Record<Locale, string> = {
  ko: '한국어',
  en: 'English',
  fr: 'Français',
};

export function isLocale(value: string): value is Locale {
  return (locales as readonly string[]).includes(value);
}

/** 사이트 정식 주소 — sitemap·canonical·OG에 쓴다. */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, '') ?? 'https://epiweather-web.vercel.app';

/** 로케일별 정식 경로. canonical과 hreflang이 같은 규칙을 쓰게 한 곳에서 만든다. */
export function localePath(locale: Locale, path = ''): string {
  const clean = path.replace(/^\/+/, '').replace(/\/+$/, '');
  return clean ? `/${locale}/${clean}` : `/${locale}`;
}

export function localeUrl(locale: Locale, path = ''): string {
  return `${SITE_URL}${localePath(locale, path)}`;
}

/**
 * hreflang 지도. 검색엔진에 "같은 내용의 다른 언어판"을 알려준다 —
 * 이게 없으면 세 언어판이 서로 중복 콘텐츠로 취급돼 색인에서 손해를 본다.
 */
export function alternateLanguages(path = ''): Record<string, string> {
  const map: Record<string, string> = {};
  for (const locale of locales) map[htmlLang[locale]] = localeUrl(locale, path);
  map['x-default'] = localeUrl(defaultLocale, path);
  return map;
}
