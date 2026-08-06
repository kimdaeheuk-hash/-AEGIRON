import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import {
  getDictionary, isLocale, localeUrl, localePath, alternateLanguages, type Locale,
} from '@/i18n';
import { Section, Card } from '@/components/site/Section';
import { LanguageNotice } from '@/components/site/LanguageNotice';
import { getBriefingResult, isBriefDate, briefLangFor, listBriefings } from '@/lib/briefings';

/**
 * 개별 브리핑 — 매일 새로 생기는 색인 대상 페이지.
 *
 * 회사 소개 페이지는 한 번 만들면 안 바뀌지만 여기는 매일 늘어난다. 검색엔진이
 * 다시 찾아올 이유를 만드는 건 이쪽이고, 그래서 브리핑 하나하나가 자기 제목·설명·
 * 정식주소를 갖는 독립 페이지여야 한다(목록 안 아코디언으로 만들면 색인되지 않는다).
 */

/**
 * 미리 만들어 둔 날짜가 아니어도 요청 시 렌더링한다 — 브리핑은 매일 새로 생기므로
 * 이게 꺼져 있으면 내일 것이 재배포 전까지 안 열린다(상위 레이아웃에서 이 설정을
 * 끄고 있었고, 자식에서 켜도 되돌아오지 않아 상위에서 제거했다).
 */
export const dynamicParams = true;

/** 이미 있는 브리핑은 미리 만들어 둔다(빠르고 색인에 유리). 새 날짜는 위 설정으로 처리. */
export async function generateStaticParams() {
  const briefs = await listBriefings('ko');
  return (briefs ?? []).map((b) => ({ date: b.date }));
}

export async function generateMetadata(props: {
  params: Promise<{ locale: string; date: string }>;
}): Promise<Metadata> {
  const { locale, date } = await props.params;
  if (!isLocale(locale) || !isBriefDate(date)) return {};
  const dict = getDictionary(locale);
  const { brief } = await getBriefingResult(locale, date);
  const path = `briefings/${date}`;

  if (!brief) {
    return {
      title: dict.briefings.notFound,
      // 없는 브리핑이 색인되면 검색결과에 빈 페이지가 남는다.
      robots: { index: false, follow: true },
    };
  }

  const title = brief.headline || `${dict.pages.briefings.title} · ${date}`;
  const description = brief.summary || dict.pages.briefings.metaDescription;

  return {
    title,
    description,
    alternates: { canonical: localeUrl(locale, path), languages: alternateLanguages(path) },
    openGraph: {
      type: 'article',
      title,
      description,
      url: localeUrl(locale, path),
      publishedTime: `${date}T00:00:00Z`,
    },
  };
}

export default async function BriefingDetailPage(props: {
  params: Promise<{ locale: string; date: string }>;
}) {
  const { locale: raw, date } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  if (!isBriefDate(date)) notFound();

  const dict = getDictionary(locale);
  const t = dict.briefings;
  const { status, brief } = await getBriefingResult(locale, date);

  // ★ 없는 브리핑과 API 장애를 구분한다 ★
  // 없는 날짜는 **진짜 404**여야 한다 — 200에 "없습니다"를 띄우면 검색엔진이
  // 빈 페이지를 정상 페이지로 색인한다(soft 404).
  // 반대로 API가 잠깐 죽은 것뿐이라면 그 페이지는 실재하므로 404로 지워버리면 안 된다.
  if (status === 'missing') notFound();
  if (!brief) {
    return (
      <Section>
        <Card>
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>{t.error}</p>
          <Link
            href={localePath(locale, 'briefings')}
            style={{
              display: 'inline-block', marginTop: 16,
              fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)', textDecoration: 'none',
            }}
          >
            ← {t.backToList}
          </Link>
        </Card>
      </Section>
    );
  }

  const segments = brief.segments ?? [];

  // 뉴스 기사 구조화 데이터 — 브리핑은 날짜가 있는 발행물이라 이 형식이 맞다.
  const articleJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'NewsArticle',
    headline: brief.headline,
    description: brief.summary,
    datePublished: `${date}T00:00:00Z`,
    inLanguage: brief.lang,
    isAccessibleForFree: true,
    publisher: { '@type': 'Organization', name: dict.common.siteName },
    url: localeUrl(locale, `briefings/${date}`),
  };

  return (
    <>
      <script
        type="application/ld+json"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd) }}
      />

      <Section>
        <Link
          href={localePath(locale, 'briefings')}
          style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--muted)', textDecoration: 'none' }}
        >
          ← {t.backToList}
        </Link>

        <div style={{ display: 'flex', alignItems: 'center', gap: 9, flexWrap: 'wrap', margin: '22px 0 14px' }}>
          <time
            dateTime={date}
            style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)' }}
          >
            {date}
          </time>
          {brief.format?.name && (
            <span
              style={{
                fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--muted2)',
                border: '1px solid var(--line)', borderRadius: 999, padding: '3px 8px',
              }}
            >
              {brief.format.name}
            </span>
          )}
          {brief.quiet_day && (
            <span
              style={{
                fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--ok)',
                border: '1px solid rgba(52,211,153,.3)', borderRadius: 999, padding: '3px 8px',
              }}
            >
              {t.quietDay}
            </span>
          )}
        </div>

        <h1
          style={{
            fontFamily: 'var(--disp)', fontWeight: 800,
            fontSize: 'clamp(24px,3.4vw,42px)', lineHeight: 1.2, letterSpacing: '-.025em',
            maxWidth: 900,
          }}
        >
          {brief.headline}
        </h1>

        {brief.summary && (
          <p style={{ color: 'var(--muted)', fontSize: 'clamp(15px,1.2vw,17px)', lineHeight: 1.75, marginTop: 18, maxWidth: 760 }}>
            {brief.summary}
          </p>
        )}

        <LanguageNotice locale={locale} actualLang={brief.lang || briefLangFor(locale)} dict={t} />
      </Section>

      {brief.ticker && brief.ticker.length > 0 && (
        <Section pad="sm">
          <Card>
            <h2
              style={{
                fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.1em',
                textTransform: 'uppercase', color: 'var(--muted2)', marginBottom: 14,
              }}
            >
              {t.ticker}
            </h2>
            <ul style={{ listStyle: 'none', display: 'grid', gap: 10 }}>
              {brief.ticker.map((line, i) => (
                <li key={i} style={{ display: 'flex', gap: 11, alignItems: 'flex-start' }}>
                  <span aria-hidden="true" style={{ color: 'var(--accent)', fontSize: 13, paddingTop: 1 }}>
                    ·
                  </span>
                  <span style={{ fontSize: 13.5, lineHeight: 1.7 }}>{line}</span>
                </li>
              ))}
            </ul>
          </Card>
        </Section>
      )}

      {segments.length > 0 && (
        <Section pad="sm">
          <h2
            style={{
              fontFamily: 'var(--disp)', fontWeight: 800,
              fontSize: 'clamp(19px,2.1vw,26px)', marginBottom: 18,
            }}
          >
            {t.segments}
          </h2>
          <div style={{ display: 'grid', gap: 14 }}>
            {segments.map((seg, i) => (
              <Card key={seg.segment_id ?? i}>
                {(seg.lower_third || seg.tier) && (
                  <div style={{ display: 'flex', gap: 9, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
                    {seg.lower_third && (
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--accent)' }}>
                        {seg.lower_third}
                      </span>
                    )}
                    {seg.tier && (
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>
                        {seg.tier}
                        {typeof seg.score === 'number' ? ` · ${seg.score}` : ''}
                      </span>
                    )}
                  </div>
                )}
                {seg.anchor_script && (
                  <p style={{ fontSize: 14.5, lineHeight: 1.8 }}>{seg.anchor_script}</p>
                )}
                {((seg.countries && seg.countries.length > 0) ||
                  (seg.sources && seg.sources.length > 0)) && (
                  <p
                    style={{
                      fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)',
                      marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--line)',
                    }}
                  >
                    {[seg.countries?.join(' · '), seg.sources?.join(' · ')]
                      .filter(Boolean)
                      .join('  |  ')}
                  </p>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {(brief.disclosure || brief.closing) && (
        <Section pad="sm">
          <Card>
            <h2
              style={{
                fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.1em',
                textTransform: 'uppercase', color: 'var(--muted2)', marginBottom: 12,
              }}
            >
              {t.disclosure}
            </h2>
            {brief.closing && (
              <p style={{ color: 'var(--muted)', fontSize: 13.5, lineHeight: 1.75, marginBottom: 12 }}>
                {brief.closing}
              </p>
            )}
            {brief.disclosure && (
              <p style={{ color: 'var(--muted2)', fontSize: 12.5, lineHeight: 1.72 }}>
                {brief.disclosure}
              </p>
            )}
          </Card>
        </Section>
      )}
    </>
  );
}
