import type { Metadata } from 'next';
import { getDictionary, isLocale, type Locale } from '@/i18n';
import { Section, SectionHeading, Card } from '@/components/site/Section';
import { CtaBand } from '@/components/site/ContentPageView';
import {
  LayerDiagram, SystemStatusGrid, LoopPanel, TransitionList, FlowList, SystemsTable,
} from '@/components/live/BaikalWidgets';
import { Unavailable } from '@/components/live/LiveWidgets';
import { getBaikal } from '@/lib/live';
import { pageMetadata } from '@/lib/meta';

/**
 * BAIKAL MOB — 아이기론 대표 시스템 (2026-10-19).
 * 캡틴: "엔진=>온톨로지=>바이칼몹 시스템을 아이기론을 대표하는 시스템으로 명명하고 기록해."
 *
 * 3층 구조(엔진 → YGGDRASIL → BAIKAL MOB)와, 운영 서버가 매시간 기록한 7개 시스템 상태·
 * 피드백 루프·상태 변화 기록을 보여 준다. 운영 API(/api/baikal)를 5분 캐시로 읽는다 —
 * 못 읽으면 지어낸 상태 대신 "읽지 못함"을 쓰고, 낡은 스냅숏은 낡았다고 쓴다.
 */
const PATH = 'baikal';

export async function generateMetadata(props: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  return pageMetadata(getDictionary(locale).extra.pages.baikal, locale, PATH);
}

export default async function BaikalPage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const dict = getDictionary(locale);
  const x = dict.extra;
  const page = x.pages.baikal;
  const B = x.baikal;
  const data = await getBaikal();

  return (
    // overflowWrap: keep-all 은 공백 없는 긴 나열('A·B·C·…')을 한 낱말로 봐 휴대폰 화면 밖으로
    // 밀어낸다(2026-10-19 캡틴 휴대폰 캡처). 화면보다 긴 낱말만 예외로 끊게 한다.
    <div style={{ wordBreak: 'keep-all', overflowWrap: 'anywhere' }}>
      <Section>
        <SectionHeading as="h1" eyebrow={page.eyebrow} title={page.title} lead={page.lead} />
        <LayerDiagram labels={B} />
      </Section>

      <div className="band-deep">
        <Section>
          <SectionHeading eyebrow="LIVE STATE · BAIKAL MOB" title={B.statusTitle} lead={B.statusLead} />
          <SystemStatusGrid data={data} systems={x.systems} labels={B} />
        </Section>
      </div>

      <Section>
        <SectionHeading eyebrow="FEEDBACK LOOP" title={B.loopTitle} lead={B.loopLead} />
        <LoopPanel data={data} labels={B} />
      </Section>

      <Section>
        <SectionHeading eyebrow="ENGINE SYSTEMS" title={B.systemsTitle} lead={B.systemsLead} />
        <SystemsTable systems={x.systems} engineGroups={dict.home.engineGroups} labels={B} />
      </Section>

      <div className="band-deep">
        <Section>
          <SectionHeading eyebrow="ONTOLOGY · YGGDRASIL" title={B.flowsTitle} lead={B.flowsLead} />
          <FlowList systems={x.systems} labels={B} />
        </Section>
      </div>

      <Section>
        <SectionHeading eyebrow="STATE CHANGES" title={B.transitionsTitle} lead={B.transitionsLead} />
        {/* 못 읽음과 '변화 없음'을 같은 말로 쓰지 않는다. */}
        {data
          ? <TransitionList transitions={data.transitions} systems={x.systems} labels={B} />
          : <Unavailable text={B.unavailable} />}
      </Section>

      <Section pad="sm">
        <Card accent>
          <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(19px,2.1vw,24px)' }}>{B.honestyTitle}</h2>
          <ul style={{ margin: '14px 0 0', paddingLeft: 20, display: 'grid', gap: 8 }}>
            {B.honestyPoints.map((p) => (
              <li key={p} style={{ fontSize: 14, lineHeight: 1.7 }}>{p}</li>
            ))}
          </ul>
        </Card>
      </Section>

      {page.cta && <CtaBand cta={page.cta} locale={locale} />}
    </div>
  );
}
