import { Card } from '@astryxdesign/core/Card';
import { HStack } from '@astryxdesign/core/HStack';
import { Link } from '@astryxdesign/core/Link';
import { List, ListItem } from '@astryxdesign/core/List';
import { Heading, Text } from '@astryxdesign/core/Text';
import { Token } from '@astryxdesign/core/Token';
import { VStack } from '@astryxdesign/core/VStack';
import { AstryxProvider } from '@/components/AstryxProvider';
import { getDictionary, localePath, type Locale } from '@/i18n';
import { getKoreaWatch, type Line } from '@/lib/koreaWatch';

/** /korea 아래 '지금 한국과 연결된 관측' — 서버 컴포넌트, 이미 운영 서버가 받는 값만 (2026-11-16). */
export default async function KoreaWatchSection({ locale }: { locale: Locale }) {
  const o = getDictionary(locale).extra.observations;
  const t = o.korea;
  const c = o.globe.card;
  const w = await getKoreaWatch(locale);

  const lines = (rows: Line[] | null) =>
    rows === null ? (
      <Text color="secondary">{t.unavailable}</Text>
    ) : rows.length === 0 ? (
      <Text color="secondary">{t.empty}</Text>
    ) : (
      <List density="compact" hasDividers edge="bleed">
        {rows.map((r) => (
          <ListItem
            key={r.id}
            label={<Text weight="semibold">{r.title}</Text>}
            description={<Text type="supporting">{r.detail}</Text>}
          />
        ))}
      </List>
    );

  return (
    <AstryxProvider mode="light">
      <VStack hAlign="center" paddingInline={4} paddingBlock={8} width="100%">
        <VStack gap={5} maxWidth={1100} width="100%">
          <VStack gap={2}>
            <Text type="label" color="accent">
              {t.eyebrow}
            </Text>
            <Heading level={2}>{t.title}</Heading>
            <Text color="secondary">{t.lead}</Text>
            <Text type="supporting">{t.interpretation}</Text>
            <Link href={localePath(locale, 'reports/weekly')}>
              <Text weight="semibold" color="inherit">
                {o.weekly.eyebrow} →
              </Text>
            </Link>
          </VStack>

          <Card padding={4}>
            <VStack gap={2}>
              <Heading level={3}>{t.exposedTitle}</Heading>
              <Text type="supporting">
                {t.exposedLead}
                {w.week ? ` · ${w.week}` : ''}
              </Text>
              {w.exposed === null ? (
                <Text color="secondary">{t.koreaUnavailable}</Text>
              ) : w.exposed.length === 0 ? (
                <Text color="secondary">{t.empty}</Text>
              ) : (
                <List density="compact" hasDividers edge="bleed">
                  {w.exposed.map((x) => (
                    <ListItem
                      key={x.iso3}
                      href={localePath(locale, `observations/${x.iso3}`)}
                      label={
                        <HStack gap={2} vAlign="center" wrap="wrap">
                          <Text weight="semibold">{x.name}</Text>
                          <Token size="sm" label={`${c.intensity} ${x.intensity}/100`} />
                        </HStack>
                      }
                      description={
                        <Text type="supporting">
                          {[
                            x.korea.routes !== null ? `${c.koreaRoutes} ${x.korea.routes}` : null,
                            x.korea.passengers !== null
                              ? `${c.koreaPassengers} ${x.korea.passengers.toLocaleString('en-US')}`
                              : null,
                            x.dominantDisease ? `${c.dominant}: ${x.dominantDisease}` : null,
                          ]
                            .filter(Boolean)
                            .join(' · ')}
                        </Text>
                      }
                    />
                  ))}
                </List>
              )}
            </VStack>
          </Card>

          <Card padding={4}>
            <VStack gap={2}>
              <Heading level={3}>{t.trendsTitle}</Heading>
              <Text type="supporting">{t.trendsLead}</Text>
              {lines(
                w.trends === null
                  ? null
                  : w.trends.map((x, i) => ({
                      id: `tr${i}`,
                      title: x.label,
                      detail: `${x.base} · ${t.trendProb} ${x.target}: ${x.prob === null ? '—' : `${Math.round(x.prob * 100)}%`}`,
                    })),
              )}
            </VStack>
          </Card>

          <Card padding={4}>
            <VStack gap={2}>
              <Heading level={3}>{t.domesticTitle}</Heading>
              <Text type="supporting">{t.domesticLead}</Text>
              {lines(w.domestic)}
            </VStack>
          </Card>

          <Card padding={4}>
            <VStack gap={2}>
              <Heading level={3}>{t.tradeTitle}</Heading>
              <Text type="supporting">{t.tradeLead}</Text>
              {w.trade !== null && w.trade.length === 0 ? <Text color="secondary">{t.tradeNone}</Text> : lines(w.trade)}
            </VStack>
          </Card>

          <Card padding={4}>
            <VStack gap={3}>
              <Heading level={3}>{t.securityTitle}</Heading>
              <VStack gap={1}>
                <Text weight="semibold">{t.gapsLabel}</Text>
                {w.gaps === null ? (
                  <Text color="secondary">{t.unavailable}</Text>
                ) : (
                  <>
                    <Text>{w.gaps.gaps.length ? w.gaps.gaps.join(', ') : t.empty}</Text>
                    <Text type="supporting">
                      {t.coveredLabel}: {w.gaps.covered.length ? w.gaps.covered.join(', ') : t.empty}
                    </Text>
                    <Text type="supporting">
                      {t.gapsNote}
                      {w.gaps.verified ? ` · WHO ICG ${w.gaps.verified}` : ''}
                    </Text>
                  </>
                )}
              </VStack>
              <VStack gap={1}>
                <Text weight="semibold">{t.highThreatLabel}</Text>
                <Text type="supporting">{t.highThreatNote}</Text>
                {lines(w.highThreat)}
              </VStack>
            </VStack>
          </Card>
        </VStack>
      </VStack>
    </AstryxProvider>
  );
}
