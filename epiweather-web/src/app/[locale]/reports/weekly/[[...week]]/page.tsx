import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { Card } from '@astryxdesign/core/Card';
import { HStack } from '@astryxdesign/core/HStack';
import { Link } from '@astryxdesign/core/Link';
import { List, ListItem } from '@astryxdesign/core/List';
import { Heading, Text } from '@astryxdesign/core/Text';
import { Token } from '@astryxdesign/core/Token';
import { VStack } from '@astryxdesign/core/VStack';
import { AstryxProvider } from '@/components/AstryxProvider';
import { alternateLanguages, getDictionary, isLocale, localePath, localeUrl, type Locale } from '@/i18n';
import { getWeeklyReport, isIsoWeek, type WeeklyRow } from '@/lib/weeklyReport';

/**
 * 주간 해외유입 위험 보고서 — 무료 베타 (2026-11-16, 관측 데이터 활용 계획 ④ '데이터로 팔 수 있는 것' 첫 상품).
 *
 * /reports/weekly → 최신 주, /reports/weekly/2026-W46 → 그 주(보관본). 새로 계산하지 않고 운영 서버가
 * 매주 만든 보고서를 그대로 보여 준다. 메일 구독은 만들지 않았고 화면에도 그렇게 적는다.
 */

export const revalidate = 900;

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';

type Params = { params: Promise<{ locale: string; week?: string[] }> };

function parseWeek(seg: string[] | undefined): string | null | false {
  if (!seg || seg.length === 0) return null;
  if (seg.length > 1) return false;
  const w = seg[0].toUpperCase();
  return isIsoWeek(w) ? w : false;
}

export async function generateMetadata(props: Params): Promise<Metadata> {
  const { locale, week: seg } = await props.params;
  const week = parseWeek(seg);
  if (!isLocale(locale) || week === false) return {};
  const t = getDictionary(locale).extra.observations.weekly;
  const path = week ? `reports/weekly/${week}` : 'reports/weekly';
  return {
    title: t.metaTitle
      .replace('{week}', week ?? '')
      .replace(/\s+—/, ' —')
      .trim(),
    description: t.metaDescription,
    alternates: { canonical: localeUrl(locale, path), languages: alternateLanguages(path) },
  };
}

export default async function WeeklyReportPage(props: Params) {
  const { locale: raw, week: seg } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const week = parseWeek(seg);
  if (week === false) notFound();
  const x = getDictionary(locale).extra;
  const t = x.observations.weekly;
  const R = x.record.importReport;
  const W = x.record.weekly;
  const nf = new Intl.NumberFormat(locale === 'ko' ? 'ko-KR' : locale === 'fr' ? 'fr-FR' : 'en-US');
  const res = await getWeeklyReport(week, locale);

  const rows = (list: WeeklyRow[], withIndex: boolean, byPax: boolean) => (
    <List density="compact" hasDividers edge="bleed">
      {list.map((r) => (
        <ListItem
          key={r.iso3}
          href={/^[A-Z]{3}$/.test(r.iso3) ? localePath(locale, `observations/${r.iso3}`) : undefined}
          label={
            <HStack gap={2} vAlign="center" wrap="wrap">
              <Text weight="semibold">{r.name}</Text>
              {withIndex && r.index !== null ? <Token size="sm" label={`${R.colIndex} ${r.index}`} /> : null}
              <Token size="sm" label={`${R.colScore} ${r.score ?? '—'}`} />
            </HStack>
          }
          description={
            <VStack gap={0}>
              <Text type="supporting">
                {[
                  `${R.colDisease}: ${r.disease ?? R.noDisease}`,
                  byPax
                    ? `${R.colPassengers} ${r.passengers !== null ? nf.format(r.passengers) : '—'}`
                    : `${R.colRoutes} ${r.routes ?? '—'}`,
                ].join(' · ')}
              </Text>
              {r.travel.length ? (
                <Text type="supporting">
                  {t.travelLabel}: {r.travel.join(' · ')}
                </Text>
              ) : null}
            </VStack>
          }
        />
      ))}
    </List>
  );

  return (
    <AstryxProvider mode="light">
      <VStack as="main" hAlign="center" paddingInline={4} paddingBlock={8} width="100%">
        <VStack gap={5} maxWidth={1000} width="100%">
          <VStack gap={2}>
            <Text type="label" color="accent">
              {t.eyebrow}
            </Text>
            <Heading level={1}>{t.title}</Heading>
            <Text color="secondary">{t.lead}</Text>
          </VStack>

          <Card padding={4}>
            <VStack gap={2}>
              <Heading level={2}>{t.betaTitle}</Heading>
              <Text>{t.betaBody}</Text>
              <HStack gap={4} wrap="wrap">
                <Link href={localePath(locale, 'contact')}>
                  <Text weight="semibold" color="inherit">
                    {t.subscribe}
                  </Text>
                </Link>
                {res.state === 'ok' ? (
                  <Link href={`${API_BASE}/api/korea-import-report?week=${res.report.week}&format=md`}>
                    <Text weight="semibold" color="inherit">
                      {R.markdown} →
                    </Text>
                  </Link>
                ) : null}
              </HStack>
              <Text type="supporting">{t.printHint}</Text>
            </VStack>
          </Card>

          {res.state === 'unavailable' ? (
            <Card padding={4}>
              <Text color="secondary">{t.unavailable}</Text>
            </Card>
          ) : res.state === 'missing' ? (
            <Card padding={4}>
              <VStack gap={2}>
                <Text color="secondary">{t.missing.replace('{week}', week ?? '—')}</Text>
                {res.weeks.length ? (
                  <HStack gap={3} wrap="wrap">
                    {res.weeks.map((w) => (
                      <Link key={w} href={localePath(locale, `reports/weekly/${w}`)}>
                        <Text color="inherit">{w}</Text>
                      </Link>
                    ))}
                  </HStack>
                ) : null}
              </VStack>
            </Card>
          ) : (
            (() => {
              const r = res.report;
              const period = r.period ?? '—';
              return (
                <>
                  <Card padding={4}>
                    <VStack gap={3}>
                      <HStack gap={2} vAlign="center" wrap="wrap">
                        <Heading level={2}>
                          {R.week} {r.week}
                        </Heading>
                        {r.weeks[0] === r.week ? <Token size="sm" color="blue" label={t.latest} /> : null}
                      </HStack>
                      {r.generatedAt ? (
                        <Text type="supporting">
                          {R.generated}: {r.generatedAt.slice(0, 16).replace('T', ' ')} UTC
                        </Text>
                      ) : null}
                      <HStack gap={2} wrap="wrap">
                        <Token label={`${R.summary.signal} ${r.summary.signal ?? '—'}`} />
                        <Token label={`${R.summary.exposed} ${r.summary.exposed ?? '—'}`} />
                        <Token label={`${R.summary.noRoute} ${r.summary.noRoute ?? '—'}`} />
                        <Token label={`${R.summary.alerts} ${r.summary.alerts ?? '—'}`} />
                      </HStack>
                      {r.weeks.length > 1 ? (
                        <HStack gap={3} wrap="wrap" vAlign="center">
                          <Text type="supporting">{t.weeksLabel}:</Text>
                          {r.weeks.map((w) =>
                            w === r.week ? (
                              <Text key={w} weight="semibold">
                                {w}
                              </Text>
                            ) : (
                              <Link key={w} href={localePath(locale, `reports/weekly/${w}`)}>
                                <Text color="inherit">{w}</Text>
                              </Link>
                            ),
                          )}
                        </HStack>
                      ) : null}
                    </VStack>
                  </Card>

                  <Card padding={4}>
                    <VStack gap={2}>
                      <Heading level={2}>{R.topTitle}</Heading>
                      <Text type="supporting">{t.indexNote}</Text>
                      {r.routesError ? <Text color="secondary">{R.routesError}</Text> : null}
                      {r.top.length ? rows(r.top, true, r.byPassengers) : <Text color="secondary">{R.topEmpty}</Text>}
                    </VStack>
                  </Card>

                  <Card padding={4}>
                    <VStack gap={2}>
                      <Heading level={2}>{R.noRouteTitle}</Heading>
                      {r.noRoute.length ? (
                        rows(r.noRoute, false, r.byPassengers)
                      ) : (
                        <Text color="secondary">{R.noRouteEmpty}</Text>
                      )}
                    </VStack>
                  </Card>

                  {r.trends.length ? (
                    <Card padding={4}>
                      <VStack gap={2}>
                        <Heading level={2}>{R.trendsTitle}</Heading>
                        <List density="compact" hasDividers edge="bleed">
                          {r.trends.map((tr) => (
                            <ListItem
                              key={tr.series}
                              label={<Text weight="semibold">{W.series[tr.series] ?? tr.series}</Text>}
                              description={
                                <Text type="supporting">
                                  {`${tr.baseWeek} ${tr.baseValue !== null ? nf.format(tr.baseValue) : '—'} → ${tr.targetWeek} ${W.probUp} ${tr.probUp !== null ? tr.probUp.toFixed(2) : '—'}`}
                                  {tr.last
                                    ? ` · ${R.lastScored} ${tr.last.week}: ${tr.last.probUp !== null ? tr.last.probUp.toFixed(2) : '—'} → ${tr.last.outcome === 'up' ? W.statusUp : tr.last.outcome === 'down' ? W.statusDown : tr.last.outcome || '—'}`
                                    : ''}
                                </Text>
                              }
                            />
                          ))}
                        </List>
                      </VStack>
                    </Card>
                  ) : null}

                  <Card padding={4}>
                    <VStack gap={2}>
                      {locale === 'ko' && r.caveats.length ? (
                        // 한국어판은 서버 원문 유의사항이 연결 기준·지수·신호 해석을 모두 담고 있다
                        <List density="compact" listStyle="disc">
                          {r.caveats.map((cv) => (
                            <ListItem key={cv} label={<Text type="supporting">{cv}</Text>} />
                          ))}
                        </List>
                      ) : (
                        <List density="compact" listStyle="disc">
                          {[
                            r.byPassengers ? R.basisPassengers.replace('{period}', period) : R.basisRoutes,
                            ...R.caveats,
                          ].map((cv) => (
                            <ListItem key={cv} label={<Text type="supporting">{cv}</Text>} />
                          ))}
                        </List>
                      )}
                      {locale !== 'ko' && r.caveats.length ? (
                        <VStack gap={1}>
                          <Text type="supporting" weight="semibold">
                            {t.serverCaveats}
                          </Text>
                          <List density="compact" listStyle="disc">
                            {r.caveats.map((cv) => (
                              <ListItem key={cv} label={<Text type="supporting">{cv}</Text>} />
                            ))}
                          </List>
                        </VStack>
                      ) : null}
                    </VStack>
                  </Card>
                </>
              );
            })()
          )}
        </VStack>
      </VStack>
    </AstryxProvider>
  );
}
