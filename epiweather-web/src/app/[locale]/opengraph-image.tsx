import { ImageResponse } from 'next/og';
import { getDictionary, isLocale } from '@/i18n';
import { OgFrame, OG_SIZE, OG_CONTENT_TYPE, clampTitle } from '@/components/og/OgFrame';
import { ogFonts, OG_FONT_FAMILY } from '@/components/og/font';

/**
 * 로케일 홈의 공유 카드. 하위 페이지도 더 구체적인 이미지가 없으면 이걸 물려받는다.
 * 어제까지는 이미지가 아예 없어 링크를 공유하면 밋밋한 텍스트만 떴다.
 */
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = 'AEGIRON';

export default async function Image({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const dict = getDictionary(isLocale(locale) ? locale : 'ko');

  // 히어로 제목은 줄바꿈이 들어 있어 한 줄로 편다.
  const title = clampTitle(dict.home.heroTitle.replace(/\n/g, ' '));
  const eyebrow = dict.common.siteTagline;
  // 공유 카드에도 정직성 문구를 남긴다 — 링크만 보고 판단하는 사람이 있다.
  const footnote = clampTitle(dict.footer.disclaimer, 96);

  return new ImageResponse(<OgFrame eyebrow={eyebrow} title={title} footnote={footnote} />, {
    ...size,
    fonts: await ogFonts(title, eyebrow, footnote),
  });
}
