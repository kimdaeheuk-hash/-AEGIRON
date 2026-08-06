import type { Locale } from '@/i18n/config';

/**
 * 브리핑 아카이브 조회 계층.
 *
 * 언어(2026-08-06 백엔드 개편 후): ko·en·fr 모두 정식 생성된다. 병명·국가명 같은
 * 고유명사까지 지역화된다(그 전에는 문장만 번역되고 "watching 오즈 바이러스
 * signal in 한국"처럼 나왔다).
 *
 * 그래도 응답의 `lang`을 확인하는 코드는 남겨둔다 — 백엔드가 어떤 이유로든 다른
 * 언어를 돌려주면 그 사실을 화면에 표시해야지, 조용히 넘기면 안 된다.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ??
  'https://epiweather-api-production.up.railway.app';

/** 브리핑은 하루 한 번 생성된다 — 매 요청마다 API를 두드릴 이유가 없다. */
const REVALIDATE_SECONDS = 1800;

/** 백엔드가 실제로 생성하는 언어(daily_brief.SUPPORTED_LANGS와 맞춰 둔다). */
const SUPPORTED_BRIEF_LANGS = ['ko', 'en', 'fr'] as const;

export type BriefLang = (typeof SUPPORTED_BRIEF_LANGS)[number];

export function briefLangFor(locale: Locale): BriefLang {
  return (SUPPORTED_BRIEF_LANGS as readonly string[]).includes(locale)
    ? (locale as BriefLang)
    : 'en'; // 백엔드 폴백과 같은 규칙 — 모르는 언어는 영어로.
}

export type BriefSummary = {
  date: string;
  lang: string;
  headline: string;
  format: string;
  quiet_day: boolean;
  created_at?: string;
};

export type BriefSegment = {
  segment_id?: string;
  kind?: string;
  anchor_script?: string;
  lower_third?: string;
  tier?: string | null;
  score?: number | null;
  sources?: string[];
  countries?: string[];
};

export type BriefDetail = {
  date: string;
  lang: string;
  program_name?: string;
  format?: { id?: string; name?: string; description?: string };
  headline?: string;
  summary?: string;
  quiet_day?: boolean;
  is_official_alert?: boolean;
  segments?: BriefSegment[];
  ticker?: string[];
  disclosure?: string;
  closing?: string;
  generation_method?: string;
};

/**
 * 조회 결과 — '없다'와 '못 가져왔다'를 구분한다.
 *
 * 이걸 뭉뚱그리면 API가 30초 잠깐 죽은 사이에 **실재하는 브리핑 페이지가 404로
 * 색인**되거나, 반대로 없는 날짜가 200으로 색인된다(soft 404). 둘 다 검색 품질에
 * 직접 손해라 호출부가 구분할 수 있어야 한다.
 */
export type FetchStatus = 'ok' | 'missing' | 'error';

async function getJson<T>(path: string): Promise<{ status: FetchStatus; data: T | null }> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: REVALIDATE_SECONDS },
      headers: { accept: 'application/json' },
    });
    if (res.status === 404) return { status: 'missing', data: null };
    if (!res.ok) return { status: 'error', data: null };
    return { status: 'ok', data: (await res.json()) as T };
  } catch {
    // API가 잠깐 죽어도 페이지는 떠야 한다 — 사전의 error 문구로 대체된다.
    return { status: 'error', data: null };
  }
}

export async function listBriefings(locale: Locale): Promise<BriefSummary[] | null> {
  const lang = briefLangFor(locale);
  const { data } = await getJson<{ briefs?: BriefSummary[] }>(
    `/api/daily-brief/archive?lang=${lang}`,
  );
  if (!data?.briefs) return null;
  // 최신순 — 백엔드 정렬을 믿지 않고 여기서 한 번 더 맞춘다.
  return [...data.briefs].sort((a, b) => b.date.localeCompare(a.date));
}

export async function getBriefingResult(
  locale: Locale,
  date: string,
): Promise<{ status: FetchStatus; brief: BriefDetail | null }> {
  const lang = briefLangFor(locale);
  const { status, data } = await getJson<BriefDetail>(
    `/api/daily-brief/archive/${encodeURIComponent(date)}?lang=${lang}`,
  );
  return { status, brief: data };
}

/**
 * 요청한 로케일과 실제로 받은 브리핑 언어가 어긋났는가.
 * 어긋났으면 화면에 그 사실을 적어야 한다(조용히 넘기면 오해를 만든다).
 */
export function languageMismatch(locale: Locale, actualLang: string | undefined): boolean {
  if (!actualLang) return false;
  return actualLang !== locale;
}

/** YYYY-MM-DD가 맞는지 — 경로 파라미터를 그대로 API에 넘기기 전에 거른다. */
export function isBriefDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}
