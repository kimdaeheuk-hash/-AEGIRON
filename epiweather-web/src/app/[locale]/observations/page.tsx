import type { Metadata } from 'next';
import { Card } from '@astryxdesign/core/Card';
import { HStack } from '@astryxdesign/core/HStack';
import { Link } from '@astryxdesign/core/Link';
import { Table, proportional } from '@astryxdesign/core/Table';
import type { TableColumn } from '@astryxdesign/core/Table';
import { Heading, Text } from '@astryxdesign/core/Text';
import { Token } from '@astryxdesign/core/Token';
import { VStack } from '@astryxdesign/core/VStack';
import { AstryxProvider } from '@/components/AstryxProvider';
import { getDictionary, isLocale, type Locale } from '@/i18n';
import { apiUrl, getObservations, type ObservationRow } from '@/lib/observations';
import { hasHangul } from '@/lib/observationNames';
import { pageMetadata } from '@/lib/meta';

/**
 * 관측 데이터 보드 — "아이기론에서 받은 모든 정보도 실측이야 — 홈페이지나 대시보드에서
 * 볼 수 있게 해야 해"(캡틴, 2026-11-15).
 *
 * 백엔드가 측정하고 있는데 웹에 안 보이던 분야(극지·기후·무역·재난·여행경보·산림·
 * 동물·유전체·SNS·보고공백·설명불가·나라별 발생 보도)를 분야별 표로 공개한다.
 * Astryx table-collapsible 템플릿의 뼈대(분야마다 카드 + 자기 표)를 따르되, 그 템플릿의
 * StyleX·차트 의존은 이 프로젝트에 컴파일러가 없어 쓰지 않았다.
 */

const PATH = 'observations';

/** 운영 API 를 15분 간격으로 다시 읽는다(lib/observations 의 fetch 캐시와 같은 값). */
export const revalidate = 900;

export async function generateMetadata(props: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await props.params;
  if (!isLocale(locale)) return {};
  return pageMetadata(getDictionary(locale).extra.pages.observations, locale, PATH);
}

export default async function ObservationsPage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const x = getDictionary(locale).extra;
  const page = x.pages.observations;
  const t = x.observations;
  const sections = await getObservations(locale);

  // 측정값과 해석값은 다른 칸 — 같은 모양으로 섞어 그리지 않는다.
  const columns: TableColumn<ObservationRow>[] = [
    {
      key: 'target',
      header: t.columns.target,
      width: proportional(1.2, { minWidth: 120 }),
    },
    {
      key: 'measured',
      header: t.columns.measured,
      width: proportional(2, { minWidth: 180 }),
    },
    {
      key: 'derived',
      header: t.columns.derived,
      width: proportional(1.4, { minWidth: 140 }),
    },
    {
      key: 'time',
      header: t.columns.time,
      width: proportional(1, { minWidth: 110 }),
    },
    {
      key: 'note',
      header: t.columns.note,
      width: proportional(1.2, { minWidth: 120 }),
    },
  ];

  return (
    // 사이트가 밝은 배경이라 light — 기본값(dark)이면 제목이 배경에 묻힌다(2026-11-15 로컬 렌더 확인).
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
            <Text type="supporting">{t.columnsNote}</Text>
          </VStack>

          {sections.map((s) => {
            const label = t.sections[s.key];
            return (
              <Card key={s.key} padding={4}>
                <VStack gap={3}>
                  <VStack gap={1}>
                    <HStack gap={2} vAlign="center" wrap="wrap">
                      <Heading level={2}>{label.title}</Heading>
                      {s.rows !== null && s.total !== null && (
                        <Token size="sm" label={`${s.total.toLocaleString('en-US')} ${t.countLabel}`} />
                      )}
                    </HStack>
                    <Text type="supporting">{label.lead}</Text>
                  </VStack>

                  {s.rows === null ? (
                    <Text color="secondary">{t.unavailable}</Text>
                  ) : s.rows.length === 0 ? (
                    <Text color="secondary">{t.empty}</Text>
                  ) : (
                    <Table<ObservationRow>
                      data={s.rows}
                      columns={columns}
                      idKey="id"
                      density="compact"
                      textOverflow="wrap"
                      verticalAlign="top"
                    />
                  )}

                  {s.caveat && (
                    <Text type="supporting">
                      {/* 백엔드 주의 문구는 한국어 원문 — en/fr 에서도 지우지 않고(정직 표시) 원문임을 밝힌다 */}
                      {locale !== 'ko' && hasHangul(s.caveat) ? `${t.caveatKoLabel}: ${s.caveat}` : s.caveat}
                    </Text>
                  )}
                  <HStack gap={3} wrap="wrap">
                    {s.source && (
                      <Text type="supporting">
                        {t.sourceLabel}: {s.source}
                      </Text>
                    )}
                    <Link href={apiUrl(s.apiPath)} target="_blank">
                      <Text type="supporting" color="inherit">
                        {s.apiPath}
                      </Text>
                    </Link>
                  </HStack>
                </VStack>
              </Card>
            );
          })}
        </VStack>
      </VStack>
    </AstryxProvider>
  );
}
