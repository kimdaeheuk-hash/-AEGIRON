import { Card } from '@astryxdesign/core/Card';
import { HStack } from '@astryxdesign/core/HStack';
import { Link } from '@astryxdesign/core/Link';
import { List, ListItem } from '@astryxdesign/core/List';
import { Heading, Text } from '@astryxdesign/core/Text';
import { Token } from '@astryxdesign/core/Token';
import { VStack } from '@astryxdesign/core/VStack';
import { AstryxProvider } from '@/components/AstryxProvider';
import { dashboardHref, getDictionary, isLocale, localePath, type Locale } from '@/i18n';
import type { StageDict } from '@/i18n/types';
import { getSourceHealth } from '@/lib/status';

/**
 * 홈 — 2026-11-22 개편. "전부 수정해! 끊을건 끊고 단순함에 집중하자"(캡틴).
 *
 * 한 줄기만 보여 준다: 극지(감지) → 헤임달(식별) → 발할라(대응 판정).
 * 각 고리 아래에는 지금 실제로 도는 것만 적는다. 수집 상태는 고정 문구가 아니라
 * `/api/status` 실측값이고, 못 읽으면 '판정 안 함'으로 쓴다.
 *
 * ★ 절대 규칙 ★ 정확도·선행일수 주장 금지.
 */

export const revalidate = 300;

function stageHref(locale: Locale, s: StageDict): string {
  // 극지는 사이트 페이지, 헤임달·발할라는 운영 화면 안의 구획이다.
  return s.code === 'POLAR' ? localePath(locale, s.href) : `${dashboardHref(locale)}#${s.href}`;
}

export default async function HomePage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const t = getDictionary(locale).home;
  const health = await getSourceHealth();
  const [titleTop, titleBottom] = t.title.split('\n');

  return (
    <AstryxProvider mode="light">
      <VStack as="main" hAlign="center" paddingInline={4} paddingBlock={8} width="100%">
        <VStack gap={8} maxWidth={1100} width="100%">
          {/* ── 머리말 ── */}
          <VStack gap={3}>
            <Text type="label" color="accent">
              {t.eyebrow}
            </Text>
            <Heading level={1}>
              {titleTop}
              {titleBottom && (
                <>
                  <br />
                  {titleBottom}
                </>
              )}
            </Heading>
            <Text type="large" color="secondary">
              {t.lead}
            </Text>
            <HStack gap={4} wrap="wrap" vAlign="center">
              <Link href={dashboardHref(locale)}>
                <Text weight="semibold" color="inherit">
                  {t.primaryCta} →
                </Text>
              </Link>
              <Link href={localePath(locale, 'solutions/government')}>
                <Text color="inherit">{t.secondaryCta}</Text>
              </Link>
            </HStack>
            <Text type="supporting">
              {t.healthTitle}: {health ? t.healthOk.replace('{ok}', String(health.ok)).replace('{total}', String(health.total)) : t.healthUnknown}
            </Text>
          </VStack>

          {/* ── 세 고리 ── */}
          <VStack gap={4}>
            <VStack gap={1}>
              <Heading level={2}>{t.chainTitle}</Heading>
              <Text type="supporting">{t.chainLead}</Text>
            </VStack>
            {t.stages.map((s, i) => (
              <Card key={s.code} padding={4}>
                <VStack gap={2}>
                  <HStack gap={2} vAlign="center" wrap="wrap">
                    <Token size="sm" label={`${i + 1} · ${s.role}`} />
                    <Text type="label" color="accent">
                      {s.code}
                    </Text>
                  </HStack>
                  <Heading level={3}>{s.name}</Heading>
                  <Text>{s.body}</Text>
                  <List density="compact" hasDividers edge="bleed">
                    {s.facts.map((f) => (
                      <ListItem key={f} label={<Text type="supporting">{f}</Text>} />
                    ))}
                  </List>
                  <Link href={stageHref(locale, s)}>
                    <Text weight="semibold" color="inherit">
                      {s.linkLabel} →
                    </Text>
                  </Link>
                </VStack>
              </Card>
            ))}
          </VStack>

          {/* ── 하지 않는 것 ── */}
          <Card padding={4}>
            <VStack gap={2}>
              <Heading level={2}>{t.notTitle}</Heading>
              <List density="compact" hasDividers edge="bleed">
                {t.notPoints.map((p) => (
                  <ListItem key={p} label={<Text type="supporting">{p}</Text>} />
                ))}
              </List>
            </VStack>
          </Card>
        </VStack>
      </VStack>
    </AstryxProvider>
  );
}
