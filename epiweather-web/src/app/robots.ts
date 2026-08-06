import type { MetadataRoute } from 'next';
import { SITE_URL } from '@/i18n/config';

/**
 * robots.txt — 어제까지 404였다.
 *
 * 전면 허용이 맞다. 이 사이트의 전략 자체가 '완전 공개'이고, 감출 계약도 고객도
 * 없다. 다만 `/api/`는 막는다 — 색인돼 봐야 사람이 읽을 페이지가 아니고,
 * 크롤러가 실시간 엔드포인트를 반복 호출하면 수집 스케줄러와 자원을 다툰다.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/'],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
