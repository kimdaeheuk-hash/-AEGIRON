import type { Metadata } from 'next';
import { getDictionary, isLocale, type Locale } from '@/i18n';
import { ContentPageView } from '@/components/site/ContentPageView';
import { pageMetadata } from '@/lib/meta';
import KoreaWatchSection from '@/components/observations/KoreaWatchSection';

/** 소개 글 아래에 실측 묶음을 붙인다(2026-11-16) — 15분마다 다시 읽음 */
export const revalidate = 900;

const KEY = 'korea' as const;
const PATH = 'korea';

export async function generateMetadata(props: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  return pageMetadata(getDictionary(locale).extra.pages[KEY], locale, PATH);
}

export default async function Page(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  return (
    <>
      <ContentPageView page={getDictionary(locale).extra.pages[KEY]} locale={locale} />
      <KoreaWatchSection locale={locale} />
    </>
  );
}
