import type { Metadata } from 'next';
import Link from 'next/link';
import { getDictionary, isLocale, localePath, type Locale } from '@/i18n';
import { Section, SectionHeading } from '@/components/site/Section';
import { CtaBand } from '@/components/site/ContentPageView';
import { pageMetadata } from '@/lib/meta';
import params from '@/data/disease-params.json';

const PATH = 'diseases';
type P = Record<string, { r0: number; cfr: number }>;

export async function generateMetadata(props: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  return pageMetadata(getDictionary(locale).extra.pages.diseases, locale, PATH);
}

export default async function DiseasesPage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const x = getDictionary(locale).extra;
  const page = x.pages.diseases;
  return (
    <div style={{ wordBreak: 'keep-all' }}>
      <Section>
        <SectionHeading as="h1" eyebrow={page.eyebrow} title={page.title} lead={page.lead} />
        <div style={{ display: 'grid', gap: 14, gridTemplateColumns: 'repeat(auto-fit, minmax(min(270px, 100%), 1fr))' }}>
          {x.diseases.map((d) => {
            const p = (params as P)[d.paramKey];
            return (
              <Link
                key={d.slug}
                href={localePath(locale, `diseases/${d.slug}`)}
                className="toned-card"
                data-tone="crimson"
                style={{ display: 'block', textDecoration: 'none', color: 'var(--txt)', border: '1px solid var(--line)', borderRadius: 13, padding: 18, background: 'var(--panel)' }}
              >
                <strong style={{ fontSize: 16.5, display: 'block', marginBottom: 8 }}>{d.name}</strong>
                <span style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.65, display: 'block' }}>{d.summary}</span>
                {p && (
                  <span style={{ display: 'block', fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--muted2)', marginTop: 12 }}>
                    R0 {p.r0} · CFR {Math.round(p.cfr * 1000) / 10}%
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </Section>
      {page.cta && <CtaBand cta={page.cta} locale={locale} />}
    </div>
  );
}
