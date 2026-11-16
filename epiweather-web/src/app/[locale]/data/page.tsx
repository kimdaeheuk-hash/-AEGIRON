import type { Metadata } from 'next';
import { Card } from '@astryxdesign/core/Card';
import { HStack } from '@astryxdesign/core/HStack';
import { Link } from '@astryxdesign/core/Link';
import { List, ListItem } from '@astryxdesign/core/List';
import { Heading, Text } from '@astryxdesign/core/Text';
import { Token } from '@astryxdesign/core/Token';
import { VStack } from '@astryxdesign/core/VStack';
import { AstryxProvider } from '@/components/AstryxProvider';
import { alternateLanguages, getDictionary, isLocale, localePath, localeUrl, type Locale } from '@/i18n';
import { getDataShop, type License } from '@/lib/dataShop';

/**
 * 데이터 상품 페이지 (2026-11-16) — 캡틴 "보고해서 데이터로 집계해 판매할 수 있게 전부 셋팅해야 해".
 *
 * 보유량(운영 DB 직접 집계) · 공개 실적표 · 데이터셋 카탈로그(원천·상업 이용 상태) · 무료 표본 · 파일럿 문의.
 * 가격은 정하지 않았다(캡틴 결정) — 그대로 적는다. 원천 약관이 막는 데이터는 팔지 않는다고 적는다.
 */

export const revalidate = 900;

const PATH = 'data';

function licColor(l: License): 'green' | 'orange' | 'red' | 'gray' {
  return l === 'allowed' ? 'green' : l === 'review' ? 'orange' : l === 'blocked' ? 'red' : 'gray';
}

export async function generateMetadata(props: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  const t = getDictionary(locale).extra.observations.dataShop;
  return {
    title: t.metaTitle,
    description: t.metaDescription,
    alternates: { canonical: localeUrl(locale, PATH), languages: alternateLanguages(PATH) },
  };
}

export default async function DataShopPage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const t = getDictionary(locale).extra.observations.dataShop;
  const nf = new Intl.NumberFormat(locale === 'ko' ? 'ko-KR' : locale === 'fr' ? 'fr-FR' : 'en-US');
  const n = (v: number | null) => (v === null ? '—' : nf.format(v));
  const shop = await getDataShop();
  const tr = shop.track;

  return (
    <AstryxProvider mode="light">
      <VStack as="main" hAlign="center" paddingInline={4} paddingBlock={8} width="100%">
        <VStack gap={5} maxWidth={1100} width="100%">
          <VStack gap={2}>
            <Text type="label" color="accent">
              {t.eyebrow}
            </Text>
            <Heading level={1}>{t.title}</Heading>
            <Text color="secondary">{t.lead}</Text>
            <Link href={localePath(locale, 'contact')}>
              <Text weight="semibold" color="inherit">
                {t.contact}
              </Text>
            </Link>
          </VStack>

          <Card padding={4}>
            <VStack gap={2}>
              <Heading level={2}>{t.holdingsTitle}</Heading>
              <Text type="supporting">
                {t.holdingsLead}
                {shop.computedAt ? ` · ${shop.computedAt.slice(0, 16).replace('T', ' ')} UTC` : ''}
              </Text>
              {shop.holdings === null ? (
                <Text color="secondary">{t.unavailable}</Text>
              ) : (
                <>
                  <HStack gap={2} wrap="wrap">
                    {shop.earliest ? <Token label={`${t.earliest} ${shop.earliest.slice(0, 10)}`} /> : null}
                    {shop.signalsLog && shop.signalsLog.lines !== null ? (
                      <Token
                        label={`${t.signalsLog} ${n(shop.signalsLog.lines)} · ${n(shop.signalsLog.sizeMb)}MB${
                          shop.signalsLog.first ? ` · ${shop.signalsLog.first.slice(0, 10)}~` : ''
                        }`}
                      />
                    ) : null}
                  </HStack>
                  <List density="compact" hasDividers edge="bleed">
                    {shop.holdings.map((h) => (
                      <ListItem
                        key={h.id}
                        label={<Text weight="semibold">{(locale !== 'ko' && t.tableLabels[h.id]) || h.label}</Text>}
                        description={
                          <Text type="supporting">
                            {h.rows === null
                              ? t.unavailable
                              : `${n(h.rows)} ${t.rows} · ${h.first ? h.first.slice(0, 10) : '—'}~ · ${n(h.days)} ${t.days}`}
                          </Text>
                        }
                      />
                    ))}
                  </List>
                </>
              )}
            </VStack>
          </Card>

          <Card padding={4}>
            <VStack gap={2}>
              <Heading level={2}>{t.trackTitle}</Heading>
              <Text type="supporting">{t.trackLead}</Text>
              {tr === null ? (
                <Text color="secondary">{t.unavailable}</Text>
              ) : (
                <List density="compact" hasDividers edge="bleed">
                  <ListItem
                    label={<Text weight="semibold">{t.predictions}</Text>}
                    description={
                      <Text type="supporting">
                        {tr.predictions
                          ? `total ${n(tr.predictions.total)} · resolved ${n(tr.predictions.resolved)} · ✓ ${n(tr.predictions.correct)} · ✗ ${n(tr.predictions.incorrect)}`
                          : t.unavailable}
                      </Text>
                    }
                  />
                  <ListItem
                    label={<Text weight="semibold">{t.ledger}</Text>}
                    description={
                      <Text type="supporting">
                        {tr.ledger
                          ? `measured ${n(tr.ledger.measured)} · ahead ${n(tr.ledger.ahead)} · mean ${tr.ledger.meanLead ?? '—'}d · false alarms ${n(tr.ledger.falseAlarms)}`
                          : t.unavailable}
                      </Text>
                    }
                  />
                  <ListItem
                    label={<Text weight="semibold">{t.weekly}</Text>}
                    description={
                      <Text type="supporting">
                        {tr.weekly
                          ? `scored ${n(tr.weekly.scored)}${tr.weekly.enough === false ? ` · ${t.notEnough}` : ''}`
                          : t.unavailable}
                      </Text>
                    }
                  />
                  <ListItem
                    label={<Text weight="semibold">{t.alertsMonthly}</Text>}
                    description={
                      <Text type="supporting">
                        {tr.alertsByMonth === null
                          ? t.unavailable
                          : tr.alertsByMonth.length === 0
                            ? '—'
                            : tr.alertsByMonth.map((m) => `${m.month} ${n(m.total)}/${n(m.sent)}`).join(' · ')}
                      </Text>
                    }
                  />
                </List>
              )}
            </VStack>
          </Card>

          <Card padding={4}>
            <VStack gap={3}>
              <VStack gap={1}>
                <Heading level={2}>{t.catalogTitle}</Heading>
                <Text type="supporting">{t.catalogLead}</Text>
                <Text type="supporting">{t.licenseHelp}</Text>
              </VStack>
              {shop.datasets === null ? (
                <Text color="secondary">{t.unavailable}</Text>
              ) : (
                <List density="compact" hasDividers edge="bleed">
                  {shop.datasets.map((d) => {
                    const local = locale === 'ko' ? null : t.datasets[d.id];
                    return (
                      <ListItem
                        key={d.id}
                        label={
                          <HStack gap={2} vAlign="center" wrap="wrap">
                            <Text weight="semibold">{local?.title ?? d.title}</Text>
                            <Token size="sm" color={licColor(d.license)} label={t.license[d.license]} />
                            {d.rows !== null ? <Token size="sm" label={`${n(d.rows)} ${t.rows}`} /> : null}
                          </HStack>
                        }
                        description={
                          <VStack gap={1}>
                            <Text type="supporting">{local?.description ?? d.description}</Text>
                            {locale === 'ko' && d.licenseNote ? <Text type="supporting">{d.licenseNote}</Text> : null}
                            {d.layers.length ? (
                              <HStack gap={1} wrap="wrap">
                                {d.layers.map((l) => (
                                  <Token
                                    key={l.layer}
                                    size="sm"
                                    color={licColor(l.license)}
                                    label={`${t.layers[l.layer] ?? l.layer} · ${t.license[l.license]}`}
                                  />
                                ))}
                              </HStack>
                            ) : null}
                            {d.license !== 'blocked' ? (
                              <HStack gap={3} wrap="wrap">
                                <Link href={d.sampleJson}>
                                  <Text type="supporting" color="inherit">
                                    {t.sample} JSON
                                  </Text>
                                </Link>
                                <Link href={d.sampleCsv}>
                                  <Text type="supporting" color="inherit">
                                    {t.sample} CSV
                                  </Text>
                                </Link>
                              </HStack>
                            ) : null}
                          </VStack>
                        }
                      />
                    );
                  })}
                </List>
              )}
            </VStack>
          </Card>

          <Card padding={4}>
            <VStack gap={2}>
              <Heading level={2}>{t.accessTitle}</Heading>
              <List density="compact" listStyle="disc">
                <ListItem label={<Text>{t.accessSample}</Text>} />
                <ListItem label={<Text>{t.accessPaid}</Text>} />
                {!shop.paidEnabled ? <ListItem label={<Text type="supporting">{t.paidOff}</Text>} /> : null}
                <ListItem label={<Text weight="semibold">{t.pricing}</Text>} />
              </List>
              <Link href={localePath(locale, 'contact')}>
                <Text weight="semibold" color="inherit">
                  {t.contact}
                </Text>
              </Link>
              <Text type="supporting">{t.disclaimer}</Text>
            </VStack>
          </Card>
        </VStack>
      </VStack>
    </AstryxProvider>
  );
}
