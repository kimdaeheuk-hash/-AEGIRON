import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { Card } from '@astryxdesign/core/Card';
import { Link } from '@astryxdesign/core/Link';
import { List, ListItem } from '@astryxdesign/core/List';
import { Heading, Text } from '@astryxdesign/core/Text';
import { VStack } from '@astryxdesign/core/VStack';
import { AstryxProvider } from '@/components/AstryxProvider';
import { getDictionary, isLocale, localePath, type Locale } from '@/i18n';
import { getGlobeData } from '@/lib/globeData';
import { getCountryCards } from '@/lib/countryCards';
import { getCountryHistory, getResponseMeasures, HISTORY_LAYERS, isIso3 } from '@/lib/countryPage';

/**
 * 질병청 통보용 관측 브리핑(초안) — 2026-11-16, 관측 데이터 활용 계획 ⑧.
 *
 * 캡틴: "각 나라 질병청에 알릴 수 있게 해야 해". 자동 발송은 하지 않는다(요청받지 않은 외국 기관 경보는
 * 신뢰·법적 문제 — 계획 문서 ⑧). 사람이 검토하고 직접 보낼 수 있도록 국제보건규칙(IHR) 보고와 비슷한 틀로
 * 무엇을·언제·출처, 측정/추정 구분, 판정 못 한 것을 한 장에 모은다. 인쇄(PDF)·복사용.
 */

export const revalidate = 900;

type Params = { params: Promise<{ locale: string; iso3: string }> };

export async function generateMetadata(props: Params): Promise<Metadata> {
  const { locale, iso3 } = await props.params;
  if (!isLocale(locale) || !isIso3(iso3.toUpperCase())) return {};
  const b = getDictionary(locale).extra.observations.country.briefing;
  // 초안 문서 — 검색 색인에 올리지 않는다
  return { title: b.metaTitle.replace('{name}', iso3.toUpperCase()), robots: { index: false, follow: false } };
}

export default async function BriefingPage(props: Params) {
  const { locale: raw, iso3: iso3raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const iso3 = iso3raw.toUpperCase();
  if (!isIso3(iso3)) notFound();
  const o = getDictionary(locale).extra.observations;
  const t = o.country;
  const b = t.briefing;
  const c = o.globe.card;
  const layers = o.globe.layers;

  const globe = await getGlobeData(locale);
  const [cards, history, responses] = await Promise.all([
    getCountryCards(locale, globe),
    getCountryHistory(iso3, '—'),
    getResponseMeasures(iso3, locale),
  ]);
  const card = cards.cards.find((x) => x.iso3 === iso3) ?? null;
  const name = card?.name ?? iso3;
  const generated = new Date().toISOString().slice(0, 16).replace('T', ' ') + ' UTC';

  const observed = card
    ? [
        `${c.counts}: ${layers.event} ${card.counts.event} · ${layers.unexplained} ${card.counts.unexplained} · ${layers.disaster} ${card.counts.disaster} · ${layers.trade} ${card.counts.trade}`,
        ...card.evidence.map((e) => `${e.layer === 'travel' ? t.travelTitle : layers[e.layer]} — ${e.line}`),
      ]
    : [t.noCard];
  const official = [
    ...(card?.travelTitles ?? []).map((x) => `CDC — ${x}`),
    ...(responses ?? []).slice(0, 20).map((r) => `WHO DON ${r.date} — ${r.disease} — ${r.measure}: “${r.evidence}”`),
  ];
  const measured = [
    ...(card ? [b.estimateLine.replace('{n}', String(card.intensity))] : []),
    ...(card?.riskScore !== null && card?.riskScore !== undefined
      ? [b.riskLine.replace('{n}', String(card.riskScore))]
      : []),
  ];
  const unreadLayers = HISTORY_LAYERS.filter((l) => history[l] === null).map((l) => t.historyLayers[l]);
  const undetermined = [
    ...(unreadLayers.length ? [b.undeterminedHistory.replace('{layers}', unreadLayers.join(', '))] : []),
    ...(responses === null ? [b.undeterminedResponse] : []),
    ...(!cards.koreaAvailable ? [b.undeterminedKorea] : []),
  ];
  const korea = !cards.koreaAvailable
    ? c.koreaUnavailable
    : card && (card.korea.routes !== null || card.korea.passengers !== null)
      ? [
          card.korea.routes !== null ? `${c.koreaRoutes} ${card.korea.routes}` : null,
          card.korea.passengers !== null
            ? `${c.koreaPassengers} ${card.korea.passengers.toLocaleString('en-US')}`
            : null,
        ]
          .filter(Boolean)
          .join(' · ')
      : c.koreaNone;

  const section = (title: string, lines: string[]) => (
    <VStack gap={1}>
      <Heading level={2}>{title}</Heading>
      {lines.length ? (
        <List density="compact" listStyle="disc">
          {lines.map((line, i) => (
            <ListItem key={`${i}-${line.slice(0, 40)}`} label={<Text>{line}</Text>} />
          ))}
        </List>
      ) : (
        <Text color="secondary">{b.nothing}</Text>
      )}
    </VStack>
  );

  return (
    <AstryxProvider mode="light">
      <VStack as="main" hAlign="center" paddingInline={4} paddingBlock={8} width="100%">
        <VStack gap={5} maxWidth={900} width="100%">
          <Link href={localePath(locale, `observations/${iso3}`)}>
            <Text type="supporting" color="inherit">
              {b.back}
            </Text>
          </Link>
          <Card padding={5}>
            <VStack gap={4}>
              <VStack gap={1}>
                <Text type="label" color="accent">
                  {b.eyebrow}
                </Text>
                <Heading level={1}>{b.title.replace('{name}', name)}</Heading>
                <Text weight="semibold">{b.draftNotice}</Text>
              </VStack>
              <VStack gap={1}>
                <Text>
                  {b.toLabel}: {b.toBlank}
                </Text>
                <Text>{b.fromLabel}: AEGIRON</Text>
                <Text>
                  {b.countryLabel}: {name} ({iso3})
                </Text>
                <Text>
                  {b.generatedLabel}: {generated}
                </Text>
              </VStack>
              {section(b.s1, observed)}
              {section(b.s2, official)}
              {section(b.s3, measured)}
              {section(b.s4, undetermined.length ? undetermined : [b.noUndetermined])}
              {section(b.s5, [korea])}
              {section(b.s6, [b.disclaimer])}
              <Text type="supporting">{b.printHint}</Text>
            </VStack>
          </Card>
        </VStack>
      </VStack>
    </AstryxProvider>
  );
}
