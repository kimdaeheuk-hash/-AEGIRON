import { ImageResponse } from 'next/og';
import { OgFrame, OG_SIZE, OG_CONTENT_TYPE } from '@/components/og/OgFrame';
import { ogFonts, OG_FONT_FAMILY } from '@/components/og/font';

/** 운영 화면 전용 카드 — 세 고리를 한 화면에서 본다는 것과 '로그인 없음'을 앞세운다. */
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = 'AEGIRON 운영 화면';

const TITLE = '극지 감지 → 헤임달 식별 → 발할라 대응 판정';
const EYEBROW = '운영 화면 · 로그인 없음';
const FOOT = '세 고리의 실측 값을 그대로. 가입 없이 바로 열림.';

export default async function Image() {
  return new ImageResponse(<OgFrame eyebrow={EYEBROW} title={TITLE} footnote={FOOT} palette="dark" />, {
    ...size,
    fonts: await ogFonts(TITLE, EYEBROW, FOOT),
  });
}
