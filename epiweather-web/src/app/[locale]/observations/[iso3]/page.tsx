import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { Card } from '@astryxdesign/core/Card';
import { HStack } from '@astryxdesign/core/HStack';
import { Link } from '@astryxdesign/core/Link';
import { List, ListItem } from '@astryxdesign/core/List';
import { Table, proportional } from '@astryxdesign/core/Table';
import type { TableColumn } from '@astryxdesign/core/Table';
import { Heading, Text } from '@astryxdesign/core/Text';
import { Token } from '@astryxdesign/core/Token';
import { VStack } from '@astryxdesign/core/VStack';
import { AstryxProvider } from '@/components/AstryxProvider';
import { getDictionary, isLocale, localePath, localeUrl, alternateLanguages, type Locale } from '@/i18n';
import { getGlobeData } from '@/lib/globeData';
import { getCountryCards, type Grade } from '@/lib/countryCards';
import {
  checklist,
  getCountryHistory,
  getResponseMeasures,
  HISTORY_LAYERS,
  isIso3,
  type HistoryRow,
} from '@/lib/countryPage';

/**
 * 나라별 관측 페이지 (2026-11-16, 관측 데이터 활용 계획 ①⑥⑦ — 비용 없이 할 수 있는 부분).
 *
 * 지구본 카드를 한 나라 한 화면으로 펼친다: 관측 강도(추정)·근거·CDC 여행경보·한국 연결,
 * 30일 관측 이력(매시 저장분), 받은 관측 종류로 만든 확인 목록(규칙 — 권고가 아님).
 * 발병국의 대응 조치는 AI 추출이 아직 없어 '판정 안 함'으로 적는다.
 */

export const revalidate = 900;

const UNDETERMINED: Record<Locale, string> = { ko: '판정 안 함', en: 'Undetermined', fr: 'Non déterminé' };

function gradeColor(g: Grade): 'red' | 'orange' | 'gray' {
  return g === 'high' ? 'red' : g === 'elevated' ? 'orange' : 'gray';
}

type Params = { params: Promise<{ locale: string; iso3: string }> };

async function load(raw: string, iso3raw: string) {
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const iso3 = iso3raw.toUpperCase();
  if (!isIso3(iso3)) notFound();
  const globe = await getGlobeData(locale);
  const cards = await getCountryCards(locale, globe);
  const card = cards.cards.find((c) => c.iso3 === iso3) ?? null;
  return { locale, iso3, cards, card };
}

export async function generateMetadata(props: Params): Promise<Metadata> {
  const { locale: raw, iso3: iso3raw } = await props.params;
  if (!isLocale(raw) || !isIso3(iso3raw.toUpperCase())) return {};
  const iso3 = iso3raw.toUpperCase();
  const t = getDictionary(raw).extra.observations.country;
  const path = `observations/${iso3}`;
  // 메타데이터에서는 무거운 카드 조회를 하지 않는다 — 이름은 ISO3 코드로(본문 제목은 카드의 나라 이름)
  return {
    title: t.metaTitle.replace('{name}', iso3),
    description: t.metaDescription.replace('{name}', iso3),
    alternates: { canonical: localeUrl(raw, path), languages: alternateLanguages(path) },
  };
}

export default async function CountryObservationsPage(props: Params) {
  const { locale: raw, iso3: iso3raw } = await props.params;
  const { locale, iso3, cards, card } = await load(raw, iso3raw);
  const o = getDictionary(locale).extra.observations;
  const t = o.country;
  const c = o.globe.card;
  const layers = o.globe.layers;
  const [history, responses] = await Promise.all([
    getCountryHistory(iso3, UNDETERMINED[locale]),
    getResponseMeasures(iso3, locale),
  ]);
  const checks = checklist(card);
  const name = card?.name ?? iso3;

  const historyColumns: TableColumn<HistoryRow>[] = [
    { key: 'observed', header: t.historyCols.observed, width: proportional(0.9, { minWidth: 120 }) },
    { key: 'confirmed', header: t.historyCols.confirmed, width: proportional(0.9, { minWidth: 120 }) },
    { key: 'measured', header: t.historyCols.measured, width: proportional(2, { minWidth: 200 }) },
    { key: 'derived', header: t.historyCols.derived, width: proportional(1.3, { minWidth: 140 }) },
  ];

  return (
    <AstryxProvider mode="light">
      <VStack as="main" hAlign="center" paddingInline={4} paddingBlock={8} width="100%">
        <VStack gap={6} maxWidth={1100} width="100%">
          <Link href={localePath(locale, 'observations')}>
            <Text type="supporting" color="inherit">
              {t.back}
            </Text>
          </Link>

          <VStack gap={2}>
            <Text type="label" color="accent">
              {t.eyebrow} · {iso3}
            </Text>
            <HStack gap={2} vAlign="center" wrap="wrap">
              <Heading level={1}>{name}</Heading>
              {card && <Token color={gradeColor(card.grade)} label={c.grade[card.grade]} />}
            </HStack>
            {card ? (
              <>
                <Text type="large" weight="semibold">
                  {c.intensity} {card.intensity}/100
                </Text>
                <Text type="supporting">{c.intensityNote}</Text>
              </>
            ) : (
              <Text type="large" color="secondary">
                {t.noCard}
              </Text>
            )}
          </VStack>

          {card && (
            <Card padding={4}>
              <VStack gap={3}>
                <Heading level={2}>{t.summaryTitle}</Heading>
                <Text>
                  {c.counts}: {layers.event} {card.counts.event} · {layers.unexplained} {card.counts.unexplained} ·{' '}
                  {layers.disaster} {card.counts.disaster} · {layers.trade} {card.counts.trade}
                </Text>
                {card.riskScore !== null && (
                  <Text type="supporting">
                    {c.riskScore}: {card.riskScore}
                    {card.dominantDisease ? ` · ${c.dominant}: ${card.dominantDisease}` : ''}
                  </Text>
                )}
                <VStack gap={1}>
                  <Heading level={3}>{t.travelTitle}</Heading>
                  {card.travelTitles.length ? (
                    card.travelTitles.map((title) => (
                      <Text key={title} type="supporting" display="block">
                        {title}
                      </Text>
                    ))
                  ) : (
                    <Text type="supporting">{t.travelNone}</Text>
                  )}
                </VStack>
                <VStack gap={1}>
                  <Heading level={3}>{t.koreaTitle}</Heading>
                  <Text type="supporting">
                    {!cards.koreaAvailable
                      ? c.koreaUnavailable
                      : card.korea.routes !== null || card.korea.passengers !== null
                        ? [
                            card.korea.routes !== null ? `${c.koreaRoutes} ${card.korea.routes}` : null,
                            card.korea.passengers !== null
                              ? `${c.koreaPassengers} ${card.korea.passengers.toLocaleString('en-US')}`
                              : null,
                          ]
                            .filter(Boolean)
                            .join(' · ')
                        : c.koreaNone}
                  </Text>
                </VStack>
                {card.evidence.length > 0 && (
                  <List
                    header={<Heading level={3}>{t.evidenceTitle}</Heading>}
                    density="compact"
                    hasDividers
                    edge="bleed"
                  >
                    {card.evidence.map((e) => (
                      <ListItem
                        key={`${e.layer}-${e.line}`}
                        label={<Text>{e.line}</Text>}
                        startContent={
                          <Token size="sm" label={e.layer === 'travel' ? t.travelTitle : layers[e.layer]} />
                        }
                      />
                    ))}
                  </List>
                )}
              </VStack>
            </Card>
          )}

          <Card padding={4}>
            <VStack gap={3}>
              <VStack gap={1}>
                <Heading level={2}>{t.checklistTitle}</Heading>
                <Text type="supporting">{t.checklistLead}</Text>
              </VStack>
              {checks.length ? (
                <List density="compact" hasDividers edge="bleed" listStyle="decimal">
                  {checks.map((k) => (
                    <ListItem key={k} label={<Text>{t.checks[k]}</Text>} />
                  ))}
                </List>
              ) : (
                <Text color="secondary">{t.checks.none}</Text>
              )}
            </VStack>
          </Card>

          <Card padding={4}>
            <VStack gap={2}>
              <Heading level={2}>{t.responseTitle}</Heading>
              <Text type="supporting">{t.responseNote}</Text>
              {responses === null ? (
                <Text color="secondary">{t.responseUnavailable}</Text>
              ) : responses.length === 0 ? (
                <Text color="secondary">{t.responseEmpty}</Text>
              ) : (
                <>
                  {/* 서버 컴포넌트라 표 셀에 함수(renderCell)를 못 넘긴다 — 링크가 필요한 행은 List(href)로 */}
                  <List density="compact" hasDividers edge="bleed">
                    {responses.slice(0, 80).map((r) => (
                      <ListItem
                        key={r.id}
                        href={r.url ?? undefined}
                        target={r.url ? '_blank' : undefined}
                        label={
                          <Text weight="semibold">
                            {r.measure}
                            {r.shared ? ' *' : ''}
                          </Text>
                        }
                        description={
                          <Text type="supporting">
                            {r.date} · {r.disease} · {t.responseCols.evidence}: {r.evidence}
                          </Text>
                        }
                      />
                    ))}
                  </List>
                  {responses.some((r) => r.shared) && <Text type="supporting">* {t.responseShared}</Text>}
                </>
              )}
            </VStack>
          </Card>

          <Card padding={4}>
            <VStack gap={4}>
              <VStack gap={1}>
                <Heading level={2}>{t.historyTitle}</Heading>
                <Text type="supporting">{t.historyLead}</Text>
              </VStack>
              {HISTORY_LAYERS.map((layer) => {
                const rows = history[layer];
                return (
                  <VStack key={layer} gap={2}>
                    <Heading level={3}>{t.historyLayers[layer]}</Heading>
                    {rows === null ? (
                      <Text color="secondary">{t.historyUnavailable}</Text>
                    ) : rows.length === 0 ? (
                      <Text color="secondary">{t.historyEmpty}</Text>
                    ) : (
                      <Table<HistoryRow>
                        data={rows.slice(0, 60)}
                        columns={historyColumns}
                        idKey="id"
                        density="compact"
                        textOverflow="wrap"
                        verticalAlign="top"
                      />
                    )}
                  </VStack>
                );
              })}
            </VStack>
          </Card>
        </VStack>
      </VStack>
    </AstryxProvider>
  );
}
