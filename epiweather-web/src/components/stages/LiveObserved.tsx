'use client';

/**
 * 대시보드 각 단계 위의 '지금 실제로 관측된 것' 패널 (2026-11-15).
 *
 * 아래 단계 화면은 모델 시나리오(시뮬레이션)다 — 지우지 않는다. 이 패널은 같은 질문에 대해 운영 서버가
 * 실제로 받은 값을 보여 준다. 측정값과 해석값(추정)은 다른 칸이고, 조회 실패는 '판정 안 함'으로 적는다.
 */
import { useEffect, useState } from 'react';
import { Card } from '@astryxdesign/core/Card';
import { HStack } from '@astryxdesign/core/HStack';
import { Table, proportional } from '@astryxdesign/core/Table';
import type { TableColumn } from '@astryxdesign/core/Table';
import { Heading, Text } from '@astryxdesign/core/Text';
import { Token } from '@astryxdesign/core/Token';
import { VStack } from '@astryxdesign/core/VStack';
import { AstryxProvider } from '@/components/AstryxProvider';
import { loadStageLive, STAGE_SOURCES, type LiveRow, type StageLive } from '@/lib/stageLive';

const COLUMNS: TableColumn<LiveRow>[] = [
  { key: 'target', header: '대상', width: proportional(1.3, { minWidth: 120 }) },
  { key: 'measured', header: '측정값(출처)', width: proportional(2, { minWidth: 170 }) },
  { key: 'derived', header: '해석값(추정)', width: proportional(1.4, { minWidth: 130 }) },
  { key: 'time', header: '시각', width: proportional(0.9, { minWidth: 90 }) },
  { key: 'source', header: '출처', width: proportional(1, { minWidth: 100 }) },
];

export default function LiveObserved({ stage }: { stage: number }) {
  const [data, setData] = useState<StageLive | null>(null);
  const sources = STAGE_SOURCES[stage] ?? [];

  useEffect(() => {
    let alive = true;
    loadStageLive(stage).then((d) => {
      if (alive) setData(d);
    });
    return () => {
      alive = false;
    };
  }, [stage]);

  if (!sources.length) return null;

  return (
    <AstryxProvider>
      <Card padding={3}>
        <VStack gap={2}>
          <HStack gap={2} vAlign="center" wrap="wrap">
            <Heading level={3}>지금 실제로 관측된 것</Heading>
            <Token size="sm" color="green" label="운영 서버 실측" />
          </HStack>
          <Text type="supporting">
            아래 단계 화면은 모델 시나리오임. 이 표는 같은 질문에 대해 운영 서버가 실제로 받은 값임. 측정값(출처가 준
            숫자)과 해석값(우리 모델의 추정)은 다른 칸임. 출처: {sources.map((s) => s.name).join(' · ')}
          </Text>
          {data === null ? (
            <Text type="supporting">불러오는 중…</Text>
          ) : data.rows.length === 0 && data.failures.length === 0 ? (
            <Text type="supporting">지금 이 단계에 해당하는 관측이 없음</Text>
          ) : (
            data.rows.length > 0 && (
              <Table<LiveRow>
                data={data.rows}
                columns={COLUMNS}
                idKey="id"
                density="compact"
                textOverflow="wrap"
                verticalAlign="top"
              />
            )
          )}
          {data && data.failures.length > 0 && (
            <Text type="supporting">판정 안 함(조회 실패): {data.failures.join(' · ')}</Text>
          )}
        </VStack>
      </Card>
    </AstryxProvider>
  );
}
