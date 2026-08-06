import { ImageResponse } from 'next/og';
import { getDictionary, isLocale, type Locale } from '@/i18n';
import { OgFrame, OG_SIZE, OG_CONTENT_TYPE, clampTitle } from '@/components/og/OgFrame';
import { ogFonts } from '@/components/og/font';
import { getBriefingResult, isBriefDate } from '@/lib/briefings';

/**
 * 브리핑별 공유 카드 — 그날의 실제 헤드라인이 이미지에 들어간다.
 *
 * 여기가 공유될 가능성이 가장 높은 페이지다(매일 새로 생기고 내용이 구체적이라).
 * 모든 브리핑이 같은 이미지를 쓰면 어느 날 것인지 구분이 안 된다.
 */
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = 'AEGIRON';

export default async function Image({
  params,
}: {
  params: Promise<{ locale: string; date: string }>;
}) {
  const { locale: raw, date } = await params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const dict = getDictionary(locale);

  // 브리핑을 못 가져와도 이미지는 나가야 한다 — 없으면 페이지 제목만이라도.
  const brief = isBriefDate(date) ? (await getBriefingResult(locale, date)).brief : null;
  const title = clampTitle(brief?.headline || dict.pages.briefings.title);
  const eyebrow = `${dict.pages.briefings.eyebrow} · ${date}`;
  const footnote = clampTitle(brief?.summary || dict.pages.briefings.lead, 96);

  return new ImageResponse(<OgFrame eyebrow={eyebrow} title={title} footnote={footnote} />, {
    ...size,
    fonts: await ogFonts(title, eyebrow, footnote),
  });
}
