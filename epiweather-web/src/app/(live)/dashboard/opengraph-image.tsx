import { ImageResponse } from 'next/og';
import { OgFrame, OG_SIZE, OG_CONTENT_TYPE } from '@/components/og/OgFrame';
import { ogFonts, OG_FONT_FAMILY } from '@/components/og/font';

/** 대시보드 전용 카드 — '로그인 없이 열린다'가 이 링크의 핵심이라 그걸 앞세운다. */
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = 'AEGIRON 라이브 대시보드';

const TITLE = '지금 이 순간 받고 있는 신호를 그대로';
const EYEBROW = '라이브 대시보드 · 로그인 없음';
const FOOT = '실시간 감염병 신호 화면. 가입 없이 바로 열립니다.';

export default async function Image() {
  return new ImageResponse(<OgFrame eyebrow={EYEBROW} title={TITLE} footnote={FOOT} palette="dark" />, {
    ...size,
    fonts: await ogFonts(TITLE, EYEBROW, FOOT),
  });
}
