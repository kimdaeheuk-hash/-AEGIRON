import type { Metadata } from 'next';
import '../globals.css';
import { SITE_URL } from '@/i18n/config';

/**
 * 라이브 대시보드용 루트 레이아웃.
 *
 * 사이트(`/[locale]/...`)와 **별개의 루트 레이아웃**이다. 대시보드는 언어별 사본이
 * 없는 실시간 화면 하나이고, 이미 공유된 `/dashboard` 링크를 깨지 않아야 해서
 * 로케일 경로 밖에 둔다(다중 루트 레이아웃 규약 — 최상위 layout.tsx를 두지 않고
 * 각 구획이 자기 <html>·<body>를 갖는다).
 *
 * 화면 문구가 아직 한국어라 lang="ko"로 둔다. 대시보드를 다국어화하면 그때
 * 로케일 경로로 옮기면 된다.
 */
export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: 'AEGIRON · 라이브 대시보드',
  description:
    '아이기론이 지금 이 순간 받고 있는 감염병 신호를 그대로 보여주는 실시간 화면입니다. 로그인 없이 열립니다.',
  alternates: { canonical: `${SITE_URL}/dashboard` },
  openGraph: {
    type: 'website',
    siteName: 'AEGIRON',
    title: 'AEGIRON · 라이브 대시보드',
    description: '로그인 없이 열리는 실시간 감염병 신호 화면.',
    url: `${SITE_URL}/dashboard`,
  },
  robots: { index: true, follow: true },
};

export default function LiveLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko-KR">
      <head>
        <link rel="preconnect" href="https://cdn.jsdelivr.net" />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css"
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=JetBrains+Mono:wght@400;500;700&display=swap"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
