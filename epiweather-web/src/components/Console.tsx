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
import type { Baikal, BaikalNodeRow, BaikalTransitionRow } from '@/lib/baikal';
import type { PolarTrendRow } from '@/lib/polarTrend';
import type { GrowthRow, VariantGrowth, VariantLedger, VariantStateRow, VariantTransitionRow } from '@/lib/variantLedger';

/**
 * 운영 화면(/dashboard) — 2026-11-22 개편. 예전 10단계 시뮬레이션(Command)을 지우고
 * 세 고리만 위에서 아래로 둔다: 헤임달(변이 추적) → 발할라(대응 판정) → 극지(감지).
 * 그 위에 BAIKAL MOB(상태변화 엔진 · 온톨로지 위층)이 세 고리와 수집 주기의 상태를 한 장으로 보여 준다.
 *
 * 캡틴 "변이추적으로 발할라를 앞세워"(2026-11-22): 헤임달 구획은 변이 원장(실제로 매시 도는 기록)을
 * 앞에 두고, 서열 스크리너는 그 아래에 '개발 중(검증 진행)'으로 표시한다 — 민감도를 아직 재지 않았다.
 *
 * 헤임달·발할라 패널은 운영 API 를 브라우저에서 직접 부르는 기존 클라이언트 컴포넌트다
 * (문구는 아직 한국어 — en/fr 에서는 그 사실을 머리말에 밝힌다).
 */
type Polar = { rows: PolarTrendRow[]; days: number; undetermined: number } | null;

const KO_ONLY: Record<Locale, string | null> = {
  ko: null,
  en: 'The Heimdall and Valhalla panels and the BAIKAL evidence lines below are still in Korean.',
  fr: 'Les panneaux Heimdall et Valhalla et les éléments BAIKAL ci-dessous sont encore en coréen.',
};

export default function Console({
  locale,
  polar,
  variants,
  growth,
  baikal,
}: {
  locale: Locale;
  polar: Polar;
  variants: VariantLedger;
  growth: VariantGrowth;
  baikal: Baikal;
}) {
  const dict = getDictionary(locale);
  // 순서가 아니라 코드로 찾는다 — 홈 사전에서 고리 순서를 바꿔도 이 화면이 안 깨진다.
  const byCode = Object.fromEntries(dict.home.stages.map((s) => [s.code, s]));
  const heimdall = byCode.HEIMDALL;
  const valhalla = byCode.VALHALLA;
  const polarStage = byCode.POLAR;
  const pt = dict.polar;
  const vt = dict.variant;
  const bk = dict.baikal;
  type NodeView = Omit<BaikalNodeRow, 'status'> & { status: string };
  type TransitionView = { id: string; observed: string; engine: string; change: string; reason: string };
  const nodeColumns: TableColumn<NodeView>[] = [
    { key: 'engine', header: bk.cols.engine, width: proportional(1.2, { minWidth: 150 }) },
    { key: 'status', header: bk.cols.status, width: proportional(0.8, { minWidth: 120 }) },
    { key: 'since', header: bk.cols.since, width: proportional(0.9, { minWidth: 130 }) },
    { key: 'reason', header: bk.cols.reason, width: proportional(2.4, { minWidth: 220 }) },
  ];
  const baikalTransitionColumns: TableColumn<TransitionView>[] = [
    { key: 'observed', header: bk.cols.observed, width: proportional(0.9, { minWidth: 130 }) },
    { key: 'engine', header: bk.cols.engine, width: proportional(1.1, { minWidth: 140 }) },
    { key: 'change', header: bk.cols.change, width: proportional(1.1, { minWidth: 160 }) },
    { key: 'reason', header: bk.cols.reason, width: proportional(2, { minWidth: 200 }) },
  ];
  const statusLabel = (s: string | null) => (s ? (bk.statuses[s] ?? s) : bk.observationStart);
  const nodeRows: NodeView[] = (baikal?.nodes ?? []).map((n) => ({ ...n, status: statusLabel(n.status) }));
  const baikalTransitionRows: TransitionView[] = (baikal?.transitions ?? []).map((t: BaikalTransitionRow) => ({
    id: t.id,
    observed: t.observed,
    engine: t.engine,
    change: `${statusLabel(t.from)} → ${statusLabel(t.to)}`,
    reason: t.reason,
  }));
  const stateColumns: TableColumn<VariantStateRow>[] = [
    { key: 'build', header: vt.cols.build, width: proportional(1.4, { minWidth: 150 }) },
    { key: 'dominant', header: vt.cols.dominant, width: proportional(1.2, { minWidth: 120 }) },
    { key: 'share', header: vt.cols.share, width: proportional(0.6, { minWidth: 80 }) },
    { key: 'sequences', header: vt.cols.sequences, width: proportional(0.7, { minWidth: 100 }) },
    { key: 'observed', header: vt.cols.observed, width: proportional(1.2, { minWidth: 150 }) },
  ];
  const growthColumns: TableColumn<GrowthRow>[] = [
    { key: 'clade', header: vt.growthCols.clade, width: proportional(1, { minWidth: 120 }) },
    { key: 'share', header: vt.growthCols.share, width: proportional(1, { minWidth: 130 }) },
    { key: 'weekly', header: vt.growthCols.weekly, width: proportional(0.7, { minWidth: 100 }) },
    { key: 'doubling', header: vt.growthCols.doubling, width: proportional(0.8, { minWidth: 110 }) },
    { key: 'count', header: vt.growthCols.count, width: proportional(1, { minWidth: 130 }) },
  ];
  const transitionColumns: TableColumn<VariantTransitionRow>[] = [
    { key: 'observed', header: vt.cols.observed, width: proportional(1.2, { minWidth: 150 }) },
    { key: 'build', header: vt.cols.build, width: proportional(1.2, { minWidth: 140 }) },
    { key: 'kind', header: vt.cols.kind, width: proportional(0.8, { minWidth: 110 }) },
    { key: 'change', header: vt.cols.change, width: proportional(1.6, { minWidth: 160 }) },
  ];
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

          <Card padding={4}>
            <VStack gap={3} id="baikal">
              <VStack gap={1}>
                <Text type="label" color="accent">
                  0 · {bk.title} · {bk.layer}
                </Text>
                <Heading level={2}>{bk.title}</Heading>
                <Text type="supporting">{bk.lead}</Text>
              </VStack>
              {baikal === null ? (
                <Text color="secondary">{bk.unavailable}</Text>
              ) : baikal.nodes.length === 0 ? (
                <Text color="secondary">{bk.empty}</Text>
              ) : (
                <VStack gap={3}>
                  {baikal.fresh ? (
                    <Text type="supporting">{bk.observedAt.replace('{t}', baikal.observedLabel)}</Text>
                  ) : (
                    <Text weight="semibold">{bk.stale.replace('{m}', String(baikal.ageMinutes ?? '?'))}</Text>
                  )}
                  <Table<NodeView>
                    data={nodeRows}
                    columns={nodeColumns}
                    idKey="id"
                    density="compact"
                    textOverflow="wrap"
                    verticalAlign="top"
                  />
                  <Text type="label">{bk.impactsTitle}</Text>
                  {baikal.impacts.length === 0 ? (
                    <Text type="supporting">{bk.noImpacts}</Text>
                  ) : (
                    <VStack gap={1}>
                      {baikal.impacts.map((line) => (
                        <Text key={line} type="supporting">
                          {line}
                        </Text>
                      ))}
                    </VStack>
                  )}
                  <Text type="label">{bk.transitionsTitle}</Text>
                  {baikalTransitionRows.length === 0 ? (
                    <Text type="supporting">{bk.noTransitions}</Text>
                  ) : (
                    <Table<TransitionView>
                      data={baikalTransitionRows}
                      columns={baikalTransitionColumns}
                      idKey="id"
                      density="compact"
                      textOverflow="wrap"
                      verticalAlign="top"
                    />
                  )}
                </VStack>
              )}
            </VStack>
          </Card>

          <VStack gap={2} id="heimdall">
            {head(1, heimdall)}
            <Card padding={4}>
              <VStack gap={3}>
                <VStack gap={1}>
                  <Heading level={3}>{vt.title}</Heading>
                  <Text type="supporting">{vt.lead}</Text>
                </VStack>
                {variants === null ? (
                  <Text color="secondary">{vt.unavailable}</Text>
                ) : variants.state.length === 0 ? (
                  <Text color="secondary">{vt.empty}</Text>
                ) : (
                  <VStack gap={3}>
                    <Text type="label">{vt.stateTitle}</Text>
                    <Table<VariantStateRow>
                      data={variants.state}
                      columns={stateColumns}
                      idKey="id"
                      density="compact"
                      textOverflow="wrap"
                      verticalAlign="top"
                    />
                    <Text type="label">{vt.transitionsTitle}</Text>
                    {variants.transitions.length === 0 ? (
                      <Text color="secondary">{vt.noTransitions}</Text>
                    ) : (
                      <Table<VariantTransitionRow>
                        data={variants.transitions}
                        columns={transitionColumns}
                        idKey="id"
                        density="compact"
                        textOverflow="wrap"
                        verticalAlign="top"
                      />
                    )}
                  </VStack>
                )}
              </VStack>
            </Card>
            <Card padding={4}>
              <VStack gap={3}>
                <VStack gap={1}>
                  <Heading level={3}>{vt.growthTitle}</Heading>
                  <Text type="supporting">{vt.growthLead}</Text>
                </VStack>
                {growth === null ? (
                  <Text color="secondary">{vt.growthUnavailable}</Text>
                ) : !growth.determined ? (
                  <Text color="secondary">{growth.reason ?? vt.growthUnavailable}</Text>
                ) : (
                  growth.builds.map((b) => (
                    <VStack gap={2} key={b.label}>
                      <Text type="label">{b.label}</Text>
                      {!b.determined ? (
                        <Text color="secondary">{b.reason ?? vt.growthUnavailable}</Text>
                      ) : b.rows.length === 0 ? (
                        <Text type="supporting">{vt.growthNone}</Text>
                      ) : (
                        <Table<GrowthRow>
                          data={b.rows}
                          columns={growthColumns}
                          idKey="id"
                          density="compact"
                          textOverflow="wrap"
                          verticalAlign="top"
                        />
                      )}
                    </VStack>
                  ))
                )}
              </VStack>
            </Card>
            <VStack gap={1}>
              <Heading level={3}>{vt.screenerTitle}</Heading>
              <Text type="supporting">{vt.screenerNote}</Text>
            </VStack>
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
