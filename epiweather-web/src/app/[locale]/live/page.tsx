import type { Metadata } from 'next';
import { getDictionary, isLocale, type Locale } from '@/i18n';
import { Section, SectionHeading } from '@/components/site/Section';
import { CtaBand } from '@/components/site/ContentPageView';
import { OpsCounters, RiskTop, ScreenGallery, SourceGrid, AlertList } from '@/components/live/LiveWidgets';
import { getOpsStatus, getRiskTop, getTopAlerts } from '@/lib/live';
import { pageMetadata } from '@/lib/meta';

/**
 * 실가동 — "진짜 아이기론이 뭘 하고 있는지 실가동되는 걸 보여줘야 해"(캡틴, 2026-10-18).
 * 운영 화면 캡처 + 운영 API 실측(5분 캐시). 실데이터와 모델 시나리오 화면을 구분해 표시한다.
 */
const PATH = 'live';

export async function generateMetadata(props: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  return pageMetadata(getDictionary(locale).extra.pages.live, locale, PATH);
}

export default async function LivePage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const x = getDictionary(locale).extra;
  const page = x.pages.live;
  const L = x.live;
  const [ops, risk, alerts] = await Promise.all([getOpsStatus(), getRiskTop(10), getTopAlerts()]);

  return (
    <div style={{ wordBreak: 'keep-all' }}>
      <Section>
        <SectionHeading as="h1" eyebrow={page.eyebrow} title={page.title} lead={page.lead} />
        <h2 style={h2}>{L.countersTitle}</h2>
        <p style={lead}>{L.countersLead}</p>
        <OpsCounters ops={ops} labels={L} />
      </Section>

      <div className="band-deep">
        <Section>
          <SectionHeading eyebrow="SCREENS" title={L.screensTitle} lead={L.screensLead} />
          <ScreenGallery labels={L} />
        </Section>
      </div>

      <Section>
        <div style={{ display: 'grid', gap: 40, gridTemplateColumns: 'repeat(auto-fit, minmax(min(420px, 100%), 1fr))' }}>
          <div>
            <h2 style={h2}>{L.riskTitle}</h2>
            <p style={lead}>{L.riskLead}</p>
            <RiskTop rows={risk} labels={L} />
          </div>
          <div>
            <h2 style={h2}>{L.alertsTitle}</h2>
            <p style={lead}>{L.alertsLead}</p>
            <AlertList alerts={alerts} labels={L} />
          </div>
        </div>
      </Section>

      <Section pad="sm">
        <h2 style={h2}>{L.sourcesTitle}</h2>
        <p style={lead}>{L.sourcesLead}</p>
        <SourceGrid ops={ops} labels={L} />
      </Section>

      {page.cta && <CtaBand cta={page.cta} locale={locale} />}
    </div>
  );
}

const h2 = { fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(19px,2.1vw,25px)', letterSpacing: '-.02em', marginTop: 8 } as const;
const lead = { color: 'var(--muted)', fontSize: 14, lineHeight: 1.7, margin: '8px 0 18px', maxWidth: 760 } as const;
