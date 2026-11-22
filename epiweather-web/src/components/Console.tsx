import { Card } from '@astryxdesign/core/Card';
import { HStack } from '@astryxdesign/core/HStack';
import { Link } from '@astryxdesign/core/Link';
import { Table, proportional } from '@astryxdesign/core/Table';
import type { TableColumn } from '@astryxdesign/core/Table';
import { Heading, Text } from '@astryxdesign/core/Text';
import { VStack } from '@astryxdesign/core/VStack';
import { AstryxProvider } from '@/components/AstryxProvider';
import HeimdallPanel from '@/components/stages/HeimdallPanel';
import ValhallaPanel from '@/components/stages/ValhallaPanel';
import { getDictionary, localePath, type Locale } from '@/i18n';
import type { PolarTrendRow } from '@/lib/polarTrend';

/**
 * 운영 화면(/dashboard) — 2026-11-22 개편. 예전 10단계 시뮬레이션(Command)을 지우고
 * 세 고리만 위에서 아래로 둔다: 극지(감지) → 헤임달(식별) → 발할라(대응 판정).
 *
 * 헤임달·발할라 패널은 운영 API 를 브라우저에서 직접 부르는 기존 클라이언트 컴포넌트다
 * (문구는 아직 한국어 — en/fr 에서는 그 사실을 머리말에 밝힌다).
 */
type Polar = { rows: PolarTrendRow[]; days: number; undetermined: number } | null;

const KO_ONLY: Record<Locale, string | null> = {
  ko: null,
  en: 'The Heimdall and Valhalla panels below are still in Korean.',
  fr: 'Les panneaux Heimdall et Valhalla ci-dessous sont encore en coréen.',
};

export default function Console({ locale, polar }: { locale: Locale; polar: Polar }) {
  const dict = getDictionary(locale);
  // 순서가 아니라 코드로 찾는다 — 홈 사전에서 고리 순서를 바꿔도 이 화면이 안 깨진다.
  const byCode = Object.fromEntries(dict.home.stages.map((s) => [s.code, s]));
  const heimdall = byCode.HEIMDALL;
  const valhalla = byCode.VALHALLA;
  const polarStage = byCode.POLAR;
  const pt = dict.polar;
  const columns: TableColumn<PolarTrendRow>[] = [
    { key: 'region', header: pt.cols.region, width: proportional(1.2, { minWidth: 130 }) },
    { key: 'first', header: pt.cols.first, width: proportional(1.6, { minWidth: 170 }) },
    { key: 'latest', header: pt.cols.latest, width: proportional(1.6, { minWidth: 170 }) },
    { key: 'change', header: pt.cols.change, width: proportional(1, { minWidth: 110 }) },
    { key: 'span', header: pt.cols.records, width: proportional(0.5, { minWidth: 70 }) },
  ];
  const head = (n: number, s: typeof polarStage) => (
    <VStack gap={1}>
      <Text type="label" color="accent">
        {n} · {s.code} · {s.role}
      </Text>
      <Heading level={2}>{s.name}</Heading>
      <Text type="supporting">{s.body}</Text>
    </VStack>
  );

  return (
    <AstryxProvider mode="dark">
      <VStack as="main" hAlign="center" paddingInline={4} paddingBlock={6} width="100%">
        <VStack gap={6} maxWidth={1200} width="100%">
          <HStack gap={3} vAlign="center" wrap="wrap">
            <Link href={localePath(locale)}>
              <Text weight="semibold" color="inherit">
                {dict.common.siteName}
              </Text>
            </Link>
            <Text type="supporting">{dict.home.title.replace('\n', ' · ')}</Text>
          </HStack>
          {KO_ONLY[locale] && <Text type="supporting">{KO_ONLY[locale]}</Text>}

          <VStack gap={2} id="heimdall">
            {head(1, heimdall)}
            <HeimdallPanel />
          </VStack>

          <VStack gap={2} id="valhalla">
            {head(2, valhalla)}
            <ValhallaPanel />
          </VStack>

          <Card padding={4}>
            <VStack gap={3}>
              {head(3, polarStage)}
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
              <Link href={localePath(locale, 'polar')}>
                <Text type="supporting" color="inherit">
                  {polarStage.linkLabel} →
                </Text>
              </Link>
            </VStack>
          </Card>

          <Text type="supporting">{dict.footer.disclaimer}</Text>
        </VStack>
      </VStack>
    </AstryxProvider>
  );
}
