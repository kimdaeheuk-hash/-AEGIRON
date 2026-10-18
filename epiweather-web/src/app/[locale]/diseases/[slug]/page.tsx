import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getDictionary, isLocale, localePath, localeUrl, alternateLanguages, locales, type Locale } from '@/i18n';
import { Section, SectionHeading } from '@/components/site/Section';
import params from '@/data/disease-params.json';

/** 질병별 감시 — 무엇을 보고, 어떤 문헌 파라미터로 시뮬레이션하는지. */
type P = Record<string, { r0: number; cfr: number }>;

export function generateStaticParams() {
  const slugs = getDictionary('ko').extra.diseases.map((d) => d.slug);
  return locales.flatMap((locale) => slugs.map((slug) => ({ locale, slug })));
}

export async function generateMetadata(props: { params: Promise<{ locale: string; slug: string }> }): Promise<Metadata> {
  const { locale, slug } = await props.params;
  if (!isLocale(locale)) return {};
  const d = getDictionary(locale).extra.diseases.find((x) => x.slug === slug);
  if (!d) return {};
  const path = `diseases/${slug}`;
  return {
    title: d.name,
    description: d.summary,
    alternates: { canonical: localeUrl(locale, path), languages: alternateLanguages(path) },
  };
}

export default async function DiseasePage(props: { params: Promise<{ locale: string; slug: string }> }) {
  const { locale: raw, slug } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const x = getDictionary(locale).extra;
  const d = x.diseases.find((e) => e.slug === slug);
  if (!d) notFound();
  const p = (params as P)[d.paramKey];
  const L = x.disease;

  return (
    <div style={{ wordBreak: 'keep-all' }}>
      <Section>
        <Link href={localePath(locale, 'diseases')} style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--muted)', textDecoration: 'none' }}>
          ← {L.back}
        </Link>
        <div style={{ marginTop: 18 }}>
          <SectionHeading as="h1" eyebrow="DISEASE WATCH" title={d.name} lead={d.summary} />
        </div>
        {p && (
          <div style={{ display: 'grid', gap: 1, background: 'var(--line)', border: '1px solid var(--line)', borderRadius: 13, overflow: 'hidden', gridTemplateColumns: 'repeat(auto-fit, minmax(min(220px, 100%), 1fr))', maxWidth: 640 }}>
            {[[L.r0, String(p.r0)], [L.cfr, `${Math.round(p.cfr * 1000) / 10}%`]].map(([k, v]) => (
              <div key={k} style={{ background: 'var(--panel)', padding: '16px 18px' }}>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 28, fontWeight: 700 }}>{v}</div>
                <div style={{ fontSize: 12.5, color: 'var(--muted)', marginTop: 6, fontWeight: 600 }}>{k}</div>
              </div>
            ))}
          </div>
        )}
        <p style={{ color: 'var(--muted2)', fontSize: 12.5, lineHeight: 1.7, marginTop: 12, maxWidth: 760 }}>{L.paramNote}</p>
      </Section>
      <Section pad="sm">
        <div className="toned-card" data-tone="teal" style={{ border: '1px solid var(--line)', borderRadius: 14, padding: 'clamp(18px,2.2vw,28px)', background: 'var(--panel)' }}>
          <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(19px,2vw,24px)' }}>{L.watchTitle}</h2>
          <ul style={{ listStyle: 'none', display: 'grid', gap: 12, marginTop: 18 }}>
            {d.watch.map((w, i) => (
              <li key={i} style={{ display: 'flex', gap: 12, fontSize: 14, lineHeight: 1.7 }}>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--tone)', fontWeight: 700, paddingTop: 3 }}>{String(i + 1).padStart(2, '0')}</span>
                {w}
              </li>
            ))}
          </ul>
          <Link href="/dashboard" style={{ display: 'inline-block', marginTop: 22, fontFamily: 'var(--mono)', fontSize: 12.5, color: 'var(--accent)', textDecoration: 'none', fontWeight: 700 }}>
            {L.openDashboard} →
          </Link>
        </div>
      </Section>
    </div>
  );
}
