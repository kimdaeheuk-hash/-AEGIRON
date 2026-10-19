import type { Metadata } from 'next';
import { getDictionary, isLocale, type Locale } from '@/i18n';
import { ContentPageView, CtaBand } from '@/components/site/ContentPageView';
import { Section, SectionHeading } from '@/components/site/Section';
import { pageMetadata } from '@/lib/meta';
import endpoints from '@/data/api-endpoints.json';

/**
 * 개발자 · API. 엔드포인트 표는 epiweather-api/main.py 의 라우트 데코레이터에서 뽑은
 * src/data/api-endpoints.json(126개 · 인증 37개, 2026-10-19)을 그대로 그린다.
 */
const PATH = 'developers';

type Endpoint = { method: string; path: string; tag: string; auth: boolean };

export async function generateMetadata(props: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  return pageMetadata(getDictionary(locale).extra.pages.developers, locale, PATH);
}

export default async function DevelopersPage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const x = getDictionary(locale).extra;
  const { cta, ...pageNoCta } = x.pages.developers;

  const groups = new Map<string, Endpoint[]>();
  for (const e of endpoints as Endpoint[]) {
    groups.set(e.tag, [...(groups.get(e.tag) ?? []), e]);
  }
  const ordered = [...groups.entries()].sort((a, b) => b[1].length - a[1].length);

  return (
    <>
      <ContentPageView page={pageNoCta} locale={locale} />
      <Section>
        <SectionHeading eyebrow="ENDPOINTS" title={x.api.tableTitle} lead={x.api.tableLead} />
        <div style={{ display: 'grid', gap: 22 }}>
          {ordered.map(([tag, list]) => (
            <div key={tag} style={{ border: '1px solid var(--line)', borderRadius: 13, background: 'var(--panel)', overflow: 'hidden' }}>
              <h3 style={{ fontSize: 14.5, fontWeight: 800, padding: '12px 16px', borderBottom: '1px solid var(--line)', background: 'var(--panel2)' }}>
                {x.apiTags[tag] ?? tag} <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)', fontWeight: 500 }}>· {list.length}</span>
              </h3>
              <ul style={{ listStyle: 'none' }}>
                {list.map((e) => (
                  <li key={e.method + e.path} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '8px 16px', borderTop: '1px solid var(--line)', fontFamily: 'var(--mono)', fontSize: 12.5 }}>
                    <span style={{ width: 48, flexShrink: 0, fontWeight: 700, color: e.method === 'GET' ? 'var(--cyan)' : 'var(--amber)' }}>{e.method}</span>
                    <span style={{ flex: 1, minWidth: 0, wordBreak: 'break-all' }}>{e.path}</span>
                    <span style={{ fontSize: 11, color: e.auth ? 'var(--accent)' : 'var(--muted2)', whiteSpace: 'nowrap' }}>
                      {e.auth ? `🔒 ${x.api.authYes}` : x.api.authNo}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>
      {cta && <CtaBand cta={cta} locale={locale} />}
    </>
  );
}
