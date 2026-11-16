'use client';

/**
 * 대시보드 각 단계 위의 '지금 실제로 관측된 것' 패널 (2026-11-15).
 *
 * 아래 단계 화면은 모델 시나리오(시뮬레이션)다 — 지우지 않는다. 이 패널은 같은 질문에 대해 운영 서버가
 * 실제로 받은 값을 보여 준다. 측정값과 해석값(추정)은 다른 칸이고, 조회 실패는 '판정 안 함'으로 적는다.
 * 2026-11-16: 대시보드 언어(?lang=en|fr)에 맞춰 3개 언어.
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
import { useDashLang, type DashLang } from '@/lib/dashLang';
import { loadStageLive, STAGE_SOURCES, type LiveRow, type StageLive } from '@/lib/stageLive';

const L: Record<
  DashLang,
  {
    cols: Record<'target' | 'measured' | 'derived' | 'time' | 'source', string>;
    title: string;
    badge: string;
    lead: (sources: string) => string;
    loading: string;
    none: string;
    failed: (names: string) => string;
  }
> = {
  ko: {
    cols: { target: '대상', measured: '측정값(출처)', derived: '해석값(추정)', time: '시각', source: '출처' },
    title: '지금 실제로 관측된 것',
    badge: '운영 서버 실측',
    lead: (s) =>
      `아래 단계 화면은 모델 시나리오임. 이 표는 같은 질문에 대해 운영 서버가 실제로 받은 값임. 측정값(출처가 준 숫자)과 해석값(우리 모델의 추정)은 다른 칸임. 출처: ${s}`,
    loading: '불러오는 중…',
    none: '지금 이 단계에 해당하는 관측이 없음',
    failed: (n) => `판정 안 함(조회 실패): ${n}`,
  },
  en: {
    cols: { target: 'Subject', measured: 'Measured (source)', derived: 'Derived (estimate)', time: 'Time', source: 'Source' },
    title: 'What is actually observed now',
    badge: 'Measured by the production server',
    lead: (s) =>
      `The stage screen below is a model scenario. This table shows what the production server actually received for the same question. Measured values (numbers from the source) and derived values (our model’s estimates) are in separate columns. Sources: ${s}`,
    loading: 'Loading…',
    none: 'No observation for this stage right now',
    failed: (n) => `Undetermined (fetch failed): ${n}`,
  },
  fr: {
    cols: {
      target: 'Objet',
      measured: 'Valeur mesurée (source)',
      derived: 'Valeur dérivée (estimation)',
      time: 'Heure',
      source: 'Source',
    },
    title: 'Ce qui est réellement observé maintenant',
    badge: 'Mesuré par le serveur de production',
    lead: (s) =>
      `L’écran d’étape ci-dessous est un scénario de modèle. Ce tableau montre ce que le serveur de production a réellement reçu pour la même question. Les valeurs mesurées (chiffres de la source) et les valeurs dérivées (estimations de notre modèle) sont dans des colonnes distinctes. Sources : ${s}`,
    loading: 'Chargement…',
    none: 'Aucune observation pour cette étape pour le moment',
    failed: (n) => `Non déterminé (échec de lecture) : ${n}`,
  },
};

export default function LiveObserved({ stage }: { stage: number }) {
  const lang = useDashLang();
  const t = L[lang];
  // 받은 값은 (단계·언어) 열쇠와 함께 둔다 — 단계나 언어가 바뀌면 새 값이 올 때까지 '불러오는 중'
  const key = `${stage}|${lang}`;
  const [got, setGot] = useState<{ key: string; data: StageLive } | null>(null);
  const data = got && got.key === key ? got.data : null;
  const sources = STAGE_SOURCES[stage] ?? [];

  useEffect(() => {
    let alive = true;
    loadStageLive(stage, lang).then((d) => {
      if (alive) setGot({ key: `${stage}|${lang}`, data: d });
    });
    return () => {
      alive = false;
    };
  }, [stage, lang]);

  if (!sources.length) return null;

  const columns: TableColumn<LiveRow>[] = [
    { key: 'target', header: t.cols.target, width: proportional(1.3, { minWidth: 120 }) },
    { key: 'measured', header: t.cols.measured, width: proportional(2, { minWidth: 170 }) },
    { key: 'derived', header: t.cols.derived, width: proportional(1.4, { minWidth: 130 }) },
    { key: 'time', header: t.cols.time, width: proportional(0.9, { minWidth: 90 }) },
    { key: 'source', header: t.cols.source, width: proportional(1, { minWidth: 100 }) },
  ];

  return (
    <AstryxProvider>
      <Card padding={3}>
        <VStack gap={2}>
          <HStack gap={2} vAlign="center" wrap="wrap">
            <Heading level={3}>{t.title}</Heading>
            <Token size="sm" color="green" label={t.badge} />
          </HStack>
          <Text type="supporting">{t.lead(sources.map((s) => s.name[lang]).join(' · '))}</Text>
          {data === null ? (
            <Text type="supporting">{t.loading}</Text>
          ) : data.rows.length === 0 && data.failures.length === 0 ? (
            <Text type="supporting">{t.none}</Text>
          ) : (
            data.rows.length > 0 && (
              <Table<LiveRow>
                data={data.rows}
                columns={columns}
                idKey="id"
                density="compact"
                textOverflow="wrap"
                verticalAlign="top"
              />
            )
          )}
          {data && data.failures.length > 0 && <Text type="supporting">{t.failed(data.failures.join(' · '))}</Text>}
        </VStack>
      </Card>
    </AstryxProvider>
  );
}
