import type { Metadata } from 'next';
import { getDictionary, isLocale, type Locale } from '@/i18n';
import { ContentPageView } from '@/components/site/ContentPageView';
import { pageMetadata } from '@/lib/meta';

const KEY = 'pilot' as const;
const PATH = 'pilot';

export async function generateMetadata(props: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  return pageMetadata(getDictionary(locale).extra.pages[KEY], locale, PATH);
}

export default async function Page(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  return <ContentPageView page={getDictionary(locale).extra.pages[KEY]} locale={locale} />;
}
