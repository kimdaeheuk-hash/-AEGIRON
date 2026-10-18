import type { MetadataRoute } from 'next';
import { locales, SITE_URL, localeUrl, alternateLanguages, defaultLocale } from '@/i18n/config';
import { listBriefings } from '@/lib/briefings';

/**
 * 사이트맵 — 어제까지 404였다. 없으면 검색엔진이 세 언어판을 스스로 찾아야 하는데,
 * 로케일 라우팅은 링크를 따라가기만 해서는 전부 발견되지 않는다.
 *
 * 각 항목에 alternates.languages를 붙여 "같은 내용의 다른 언어판"임을 알린다.
 * 이게 없으면 ko/en/fr가 서로 중복 콘텐츠로 취급돼 색인에서 손해를 본다.
 */

/** 로케일마다 존재하는 정적 경로. 새 페이지를 만들면 여기에 추가한다. */
const ROUTES: { path: string; priority: number; changeFrequency: MetadataRoute.Sitemap[number]['changeFrequency'] }[] = [
  { path: '', priority: 1.0, changeFrequency: 'daily' },
  { path: 'platform', priority: 0.9, changeFrequency: 'monthly' },
  { path: 'technology', priority: 0.9, changeFrequency: 'monthly' },
  { path: 'technology-advanced', priority: 0.8, changeFrequency: 'monthly' },
  { path: 'programs', priority: 0.9, changeFrequency: 'monthly' },
  { path: 'methodology', priority: 0.9, changeFrequency: 'monthly' },
  { path: 'transparency', priority: 0.9, changeFrequency: 'monthly' },
  { path: 'data-sources', priority: 0.8, changeFrequency: 'weekly' },
  { path: 'solutions/reinsurance', priority: 0.8, changeFrequency: 'monthly' },
  { path: 'solutions/government', priority: 0.8, changeFrequency: 'monthly' },
  { path: 'solutions/ngo', priority: 0.8, changeFrequency: 'monthly' },
  { path: 'briefings', priority: 0.7, changeFrequency: 'daily' },
  { path: 'about', priority: 0.6, changeFrequency: 'monthly' },
  { path: 'contact', priority: 0.6, changeFrequency: 'yearly' },
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const entries: MetadataRoute.Sitemap = [];

  for (const route of ROUTES) {
    for (const locale of locales) {
      entries.push({
        url: localeUrl(locale, route.path),
        lastModified: now,
        changeFrequency: route.changeFrequency,
        priority: route.priority,
        alternates: { languages: alternateLanguages(route.path) },
      });
    }
  }

  // 브리핑은 매일 늘어난다 — 목록만 넣으면 개별 브리핑이 색인되지 않는다.
  // 여기가 이 사이트에서 유일하게 계속 자라는 콘텐츠라 SEO상 가장 중요하다.
  // API가 죽어 있으면 브리핑 항목만 빠지고 나머지 사이트맵은 정상 생성된다.
  const briefs = await listBriefings(defaultLocale);
  for (const brief of briefs ?? []) {
    const path = `briefings/${brief.date}`;
    for (const locale of locales) {
      entries.push({
        url: localeUrl(locale, path),
        lastModified: new Date(`${brief.date}T00:00:00Z`),
        changeFrequency: 'yearly',   // 지난 브리핑은 다시 바뀌지 않는다
        priority: 0.5,
        alternates: { languages: alternateLanguages(path) },
      });
    }
  }

  // 대시보드는 언어별 사본이 없다 — 실시간 화면 하나뿐이라 단독으로 넣는다.
  entries.push({
    url: `${SITE_URL}/dashboard`,
    lastModified: now,
    changeFrequency: 'hourly',
    priority: 0.9,
  });

  return entries;
}
