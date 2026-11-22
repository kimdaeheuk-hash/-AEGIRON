import type { Metadata } from 'next';
import { Card } from '@astryxdesign/core/Card';
import { Link } from '@astryxdesign/core/Link';
import { Table, proportional } from '@astryxdesign/core/Table';
import type { TableColumn } from '@astryxdesign/core/Table';
import { Heading, Text } from '@astryxdesign/core/Text';
import { VStack } from '@astryxdesign/core/VStack';
import { AstryxProvider } from '@/components/AstryxProvider';
import { getDictionary, isLocale, type Locale } from '@/i18n';
import { getPolarTrend, type PolarTrendRow } from '@/lib/polarTrend';
import { pageMetadata } from '@/lib/meta';

/**
 * 극지 감시 — 사슬의 첫 고리(감지). 8개 극지 지역의 매시 저장분을 지역별 처음 값 → 최근 값으로 보여 준다.
 * 기온·해빙일수는 기상 관측값, Δ 는 계산값 — 표 머리말이 그 구분을 말한다. 못 읽으면 '판정 안 함'.
 */

const PATH = 'polar';
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://epiweather-api-production.up.railway.app';
const HISTORY_PATH = '/api/observations/history?layer=polar&days=30';

/** 운영 API 를 15분 간격으로 다시 읽는다(lib/polarTrend 의 fetch 캐시와 같은 값). */
export const revalidate = 900;

export async function generateMetadata(props: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  return pageMetadata(getDictionary(locale).pages.polar, locale, PATH);
}

export default async function PolarPage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const dict = getDictionary(locale);
  const page = dict.pages.polar;
  const pt = dict.polar;
  const polar = await getPolarTrend(locale);
  const columns: TableColumn<PolarTrendRow>[] = [
    { key: 'region', header: pt.cols.region, width: proportional(1.2, { minWidth: 130 }) },
    { key: 'first', header: pt.cols.first, width: proportional(1.6, { minWidth: 170 }) },
    { key: 'latest', header: pt.cols.latest, width: proportional(1.6, { minWidth: 170 }) },
    { key: 'change', header: pt.cols.change, width: proportional(1, { minWidth: 110 }) },
    { key: 'span', header: pt.cols.records, width: proportional(0.5, { minWidth: 70 }) },
  ];

  return (
    // 사이트가 밝은 배경이라 light — 기본값(dark)이면 제목이 배경에 묻힌다.
    <AstryxProvider mode="light">
      <VStack as="main" hAlign="center" paddingInline={4} paddingBlock={8} width="100%">
        <VStack gap={6} maxWidth={1200} width="100%">
          <VStack gap={2}>
            <Text type="label" color="accent">
              {page.eyebrow}
            </Text>
            <Heading level={1}>{page.title}</Heading>
            <Text type="large" color="secondary">
              {page.lead}
            </Text>
          </VStack>

          <Card padding={4}>
            <VStack gap={3}>
              <VStack gap={1}>
                <Heading level={2}>{pt.title}</Heading>
                <Text type="supporting">{pt.lead}</Text>
                {polar && polar.rows.length > 0 && (
                  <Text type="supporting">{pt.span.replace('{days}', String(polar.days))}</Text>
                )}
              </VStack>
              {polar === null ? (
                <Text color="secondary">{pt.unavailable}</Text>
              ) : polar.rows.length === 0 ? (
                <Text color="secondary">{pt.empty}</Text>
              ) : (
                <Table<PolarTrendRow>
                  data={polar.rows}
                  columns={columns}
                  idKey="id"
                  density="compact"
                  textOverflow="wrap"
                  verticalAlign="top"
                />
              )}
              {polar && polar.undetermined > 0 && (
                <Text type="supporting">{pt.undetermined.replace('{n}', String(polar.undetermined))}</Text>
              )}
              <Link href={`${API_BASE}${HISTORY_PATH}`} target="_blank">
                <Text type="supporting" color="inherit">
                  {pt.apiLabel}: {HISTORY_PATH}
                </Text>
              </Link>
            </VStack>
          </Card>
        </VStack>
      </VStack>
    </AstryxProvider>
  );
}
