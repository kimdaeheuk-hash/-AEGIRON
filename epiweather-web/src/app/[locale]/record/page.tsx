import type { Metadata } from 'next';
import { getDictionary, isLocale, type Locale } from '@/i18n';
import { Section, SectionHeading } from '@/components/site/Section';
import { CtaBand } from '@/components/site/ContentPageView';
import {
  ScoreBoard, PredictionTable, LedgerList, AlertAnatomy, WeeklyBoard, WeeklyList, ImportReportView,
} from '@/components/live/RecordWidgets';
import {
  getPredictions, getScorecard, getLedger, getTopAlerts, getWeeklyForecasts, getKoreaImportReport,
} from '@/lib/live';
import { pageMetadata } from '@/lib/meta';

/**
 * 공개 예측 원장 — 봉인된 예측·채점표·선행성 원장·경보 한 건 해부.
 * 판정 대기·실패를 지우지 않는다. 숫자는 전부 운영 API 실측(5분 캐시).
 * 2026-10-19: 주간 추세 예측 채점표(90일 예측과 따로)·대한민국 유입 주간 보고서 추가.
 */
const PATH = 'record';

export async function generateMetadata(props: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  return pageMetadata(getDictionary(locale).extra.pages.record, locale, PATH);
}

export default async function RecordPage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const x = getDictionary(locale).extra;
  const page = x.pages.record;
  const R = x.record;
  const na = x.live.unavailable;
  const [score, predictions, ledger, alerts, weekly, importReport] = await Promise.all([
    getScorecard(), getPredictions(), getLedger(), getTopAlerts(), getWeeklyForecasts(), getKoreaImportReport(),
  ]);

  return (
    <div style={{ wordBreak: 'keep-all' }}>
      <Section>
        <SectionHeading as="h1" eyebrow={page.eyebrow} title={page.title} lead={page.lead} />
        <h2 style={h2}>{R.scoreTitle}</h2>
        <p style={lead}>{R.scoreLead}</p>
        <ScoreBoard score={score} labels={R} unavailable={na} />
      </Section>

      <div className="band-deep">
        <Section>
          <SectionHeading eyebrow="ALERT ANATOMY" title={R.anatomyTitle} lead={R.anatomyLead} />
          <AlertAnatomy alert={alerts?.items[0] ?? null} labels={R} date={alerts?.date} />
        </Section>
      </div>

      <Section>
        <h2 style={h2}>{R.listTitle}</h2>
        <p style={lead}>{R.listLead}</p>
        <PredictionTable predictions={predictions} labels={R} unavailable={na} showCriteria={locale === 'ko'} />
      </Section>

      <Section pad="sm">
        <h2 style={h2}>{R.ledgerTitle}</h2>
        <p style={lead}>{R.ledgerLead}</p>
        <LedgerList ledger={ledger} labels={R} unavailable={na} />
      </Section>

      <div className="band-deep">
        <Section>
          <SectionHeading eyebrow="WEEKLY FORECASTS" title={R.weekly.title} lead={R.weekly.lead} />
          <WeeklyBoard data={weekly} labels={R} unavailable={na} />
          <h3 style={{ ...h2, fontSize: 17, marginTop: 26, marginBottom: 12 }}>{R.weekly.listTitle}</h3>
          <WeeklyList data={weekly} labels={R} />
        </Section>
      </div>

      <Section>
        <SectionHeading eyebrow="KOREA IMPORT REPORT" title={R.importReport.title} lead={R.importReport.lead} />
        <ImportReportView report={importReport} labels={R.importReport} weeklyLabels={R.weekly} />
      </Section>

      {page.cta && <CtaBand cta={page.cta} locale={locale} />}
    </div>
  );
}

const h2 = { fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(19px,2.1vw,25px)', letterSpacing: '-.02em', marginTop: 8 } as const;
const lead = { color: 'var(--muted)', fontSize: 14, lineHeight: 1.7, margin: '8px 0 18px', maxWidth: 780 } as const;
