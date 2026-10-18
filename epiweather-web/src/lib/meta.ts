import type { Metadata } from 'next';
import type { ContentPage } from '@/i18n/types';
import { localeUrl, alternateLanguages, type Locale } from '@/i18n';

/** 콘텐츠 페이지 공통 메타데이터 — 페이지마다 같은 모양을 되풀이하지 않게. */
export function pageMetadata(page: ContentPage, locale: Locale, path: string): Metadata {
  return {
    title: page.metaTitle,
    description: page.metaDescription,
    alternates: { canonical: localeUrl(locale, path), languages: alternateLanguages(path) },
    openGraph: { type: 'article', title: page.metaTitle, description: page.metaDescription, url: localeUrl(locale, path) },
  };
}
