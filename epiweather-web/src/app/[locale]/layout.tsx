import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import '../globals.css';
import {
  locales,
  isLocale,
  htmlLang,
  SITE_URL,
  localeUrl,
  alternateLanguages,
  getDictionary,
  type Locale,
} from '@/i18n';
import { SiteNav } from '@/components/site/SiteNav';
import { SiteFooter } from '@/components/site/SiteFooter';

/**
 * 사이트 루트 레이아웃(로케일별).
 *
 * Next.js 16에서 루트 레이아웃은 반드시 <html>·<body>를 포함해야 한다. 그런데
 * lang 속성은 로케일마다 달라야 하므로, 최상위에 layout.tsx를 두는 대신
 * **[locale] 자체를 루트로** 삼는다(다중 루트 레이아웃 규약). 최상위에 layout을
 * 두고 lang을 고정하면 영어·프랑스어 페이지에도 lang="ko"가 붙어 검색엔진과
 * 화면낭독기가 잘못 읽는다.
 */

/** 세 로케일만 정적 생성한다. */
export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

/**
 * ★ 중요 ★ 등록되지 않은 로케일은 404로 보낸다.
 * 이게 없으면 `/anything`이 전부 한국어 홈으로 렌더링돼, 검색엔진 눈에는
 * **같은 내용의 URL이 무한히 있는 사이트**로 보인다(색인 품질에 직접 손해).
 */
export const dynamicParams = false;

export async function generateMetadata(props: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  const dict = getDictionary(locale);

  return {
    metadataBase: new URL(SITE_URL),
    title: {
      default: dict.home.metaTitle,
      // 하위 페이지는 자기 제목만 쓰면 여기 붙는다 — 매 페이지에 반복해 적지 않게.
      template: `%s · ${dict.common.siteName}`,
    },
    description: dict.home.metaDescription,
    applicationName: dict.common.siteName,
    alternates: {
      canonical: localeUrl(locale),
      languages: alternateLanguages(),
    },
    openGraph: {
      type: 'website',
      siteName: dict.common.siteName,
      title: dict.home.metaTitle,
      description: dict.home.metaDescription,
      url: localeUrl(locale),
      locale: htmlLang[locale].replace('-', '_'),
    },
    twitter: {
      card: 'summary_large_image',
      title: dict.home.metaTitle,
      description: dict.home.metaDescription,
    },
    robots: { index: true, follow: true },
  };
}

export default async function LocaleLayout(props: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await props.params;
  if (!isLocale(locale)) notFound();
  const dict = getDictionary(locale);

  // 구조화 데이터 — 검색엔진에 "이건 어떤 조직인가"를 기계가 읽는 형식으로 준다.
  // 회사 정보가 검색결과에 제대로 뜨려면 이게 있어야 한다.
  const organizationJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: dict.common.siteName,
    url: localeUrl(locale as Locale),
    description: dict.home.metaDescription,
    address: {
      '@type': 'PostalAddress',
      addressLocality: 'Busan',
      addressCountry: 'KR',
    },
    // 정직성: 아직 검증된 실적이 없다는 사실을 구조화 데이터에도 남긴다.
    disambiguatingDescription: dict.footer.disclaimer,
  };

  return (
    <html lang={htmlLang[locale as Locale]}>
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
        <script
          type="application/ld+json"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
        />
      </head>
      <body>
        <SiteNav locale={locale as Locale} dict={dict} />
        <main>{props.children}</main>
        <SiteFooter locale={locale as Locale} dict={dict} />
      </body>
    </html>
  );
}
