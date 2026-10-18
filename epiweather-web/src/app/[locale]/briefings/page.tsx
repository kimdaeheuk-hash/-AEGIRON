import type { Metadata } from 'next';
import Link from 'next/link';
import {
  getDictionary, isLocale, localeUrl, localePath, alternateLanguages, type Locale,
} from '@/i18n';
import { Section, SectionHeading, Card, Grid } from '@/components/site/Section';
import { LanguageNotice } from '@/components/site/LanguageNotice';
import { listBriefings, briefLangFor } from '@/lib/briefings';

/**
 * 일일 브리핑 아카이브.
 *
 * SEO 관점에서 이 페이지가 중요한 이유: 회사 소개 페이지들은 한 번 만들면 안 바뀌지만
 * 브리핑은 **매일 새 페이지가 생긴다.** 검색엔진이 재방문할 이유를 만드는 건 이쪽이다.
 */
const PATH = 'briefings';

export async function generateMetadata(props: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  const page = getDictionary(locale).pages.briefings;
  return {
    title: page.metaTitle,
    description: page.metaDescription,
    alternates: { canonical: localeUrl(locale, PATH), languages: alternateLanguages(PATH) },
    openGraph: {
      type: 'website',
      title: page.metaTitle,
      description: page.metaDescription,
      url: localeUrl(locale, PATH),
    },
  };
}

export default async function BriefingsPage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const dict = getDictionary(locale);
  const page = dict.pages.briefings;
  const t = dict.briefings;

  const briefs = await listBriefings(locale);

  return (
    <>
      <Section>
        <SectionHeading as="h1" eyebrow={page.eyebrow} title={page.title} lead={page.lead} />
        <LanguageNotice locale={locale} actualLang={briefLangFor(locale)} dict={t} />
      </Section>

      {page.blocks.map((block, i) => (
        <Section key={i} pad="sm">
          <Card>
            <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(19px,2.1vw,26px)' }}>
              {block.title}
            </h2>
            {block.body && (
              <p style={{ color: 'var(--muted)', fontSize: 14.5, lineHeight: 1.78, marginTop: 14, maxWidth: 820 }}>
                {block.body}
              </p>
            )}
            {block.note && (
              <p
                style={{
                  color: 'var(--muted2)', fontSize: 12.5, lineHeight: 1.7,
                  marginTop: 18, paddingTop: 15, borderTop: '1px solid var(--line)', maxWidth: 820,
                }}
              >
                {block.note}
              </p>
            )}
          </Card>
        </Section>
      ))}

      <Section pad="sm">
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
          <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(19px,2.1vw,26px)' }}>
            {t.archiveTitle}
          </h2>
          {briefs && briefs.length > 0 && (
            <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--muted2)' }}>
              {t.count.replace('{n}', String(briefs.length))}
            </span>
          )}
        </div>

        {briefs === null ? (
          <Card>
            <p style={{ color: 'var(--muted)', fontSize: 14 }}>{t.error}</p>
          </Card>
        ) : briefs.length === 0 ? (
          <Card>
            <p style={{ color: 'var(--muted)', fontSize: 14 }}>{t.empty}</p>
          </Card>
        ) : (
          <Grid min={300}>
            {briefs.map((b) => (
              <Link
                key={b.date}
                href={localePath(locale, `${PATH}/${b.date}`)}
                style={{ textDecoration: 'none', color: 'inherit', display: 'block', height: '100%' }}
              >
                <Card>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 9, flexWrap: 'wrap', marginBottom: 12 }}>
                    <time
                      dateTime={b.date}
                      style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)' }}
                    >
                      {b.date}
                    </time>
                    {b.format && (
                      <span
                        style={{
                          fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--muted2)',
                          border: '1px solid var(--line)', borderRadius: 999, padding: '3px 8px',
                        }}
                      >
                        {b.format}
                      </span>
                    )}
                    {b.quiet_day && (
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
                  <h3 style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.5 }}>{b.headline}</h3>
                  <p style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--accent)', marginTop: 14 }}>
                    {t.openBrief} →
                  </p>
                </Card>
              </Link>
            ))}
          </Grid>
        )}
      </Section>

      {page.cta && (
        <Section pad="sm">
          <Card>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ maxWidth: 560 }}>
                <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(19px,2.1vw,25px)' }}>
                  {page.cta.title}
                </h2>
                <p style={{ color: 'var(--muted)', fontSize: 14, lineHeight: 1.7, marginTop: 11 }}>
                  {page.cta.body}
                </p>
              </div>
              <Link
                href={page.cta.href}
                style={{
                  fontFamily: 'var(--mono)', fontSize: 13, textDecoration: 'none',
                  background: 'var(--accent)', color: 'var(--on-accent)', borderRadius: 10, padding: '13px 22px',
                }}
              >
                {page.cta.label} →
              </Link>
            </div>
          </Card>
        </Section>
      )}
    </>
  );
}
