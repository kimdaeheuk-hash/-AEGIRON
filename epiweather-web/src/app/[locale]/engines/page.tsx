import type { Metadata } from 'next';
import { getDictionary, isLocale, localeUrl, alternateLanguages, type Locale } from '@/i18n';
import { ContentPageView } from '@/components/site/ContentPageView';

const KEY = 'engines' as const;
const PATH = 'engines';

export async function generateMetadata(props: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  const page = getDictionary(locale).pages[KEY];
  return {
    title: page.metaTitle,
    description: page.metaDescription,
    alternates: {
      canonical: localeUrl(locale, PATH),
      languages: alternateLanguages(PATH),
    },
    openGraph: {
      type: 'article',
      title: page.metaTitle,
      description: page.metaDescription,
      url: localeUrl(locale, PATH),
    },
  };
}

export default async function Page(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  return <ContentPageView page={getDictionary(locale).pages[KEY]} locale={locale} />;
}
