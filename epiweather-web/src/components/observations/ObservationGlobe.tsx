'use client';

/**
 * 관측 지구본 — 운영 API 에서 받은 발생 보도·설명불가 신호·재난 감시창·의료물자 수입 급증·극지 관찰을
 * 정사영(orthographic) 지구본에 찍는다. 드래그로 돌리고, 점을 누르면 그곳의 기록이 옆에 나온다.
 *
 * 국경은 world-atlas 1:110m(퍼블릭 도메인, 번들 포함 — 외부 타일·키 없음). WebGL 없이 SVG 라서
 * 서버에서 먼저 그려지고 저사양 기기에서도 돈다. 색은 Astryx 데이터 색 토큰만 쓴다.
 */
import { useMemo, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { geoCentroid, geoDistance, geoGraticule10, geoOrthographic, geoPath } from 'd3-geo';
import type { GeoPermissibleObjects } from 'd3-geo';
import { feature } from 'topojson-client';
import type { GeometryCollection, Topology } from 'topojson-specification';
import worldTopo from 'world-atlas/countries-110m.json';
import { Button } from '@astryxdesign/core/Button';
import { Card } from '@astryxdesign/core/Card';
import { HStack } from '@astryxdesign/core/HStack';
import { Heading, Text } from '@astryxdesign/core/Text';
import { Token } from '@astryxdesign/core/Token';
import { VStack } from '@astryxdesign/core/VStack';
import type { ObservationsDict } from '@/i18n/types';
import type { GlobeData, GlobeLayer, GlobePoint } from '@/lib/globeData';
import { ISO3_NUMERIC, SMALL } from '@/lib/isoGeo';

const SIZE = 560;
const KOREA_NUMERIC = '410';

/** 레이어 색 — Astryx 데이터 범주 토큰. 극지는 차갑게, 재난·보도는 뜨겁게. */
const LAYER_COLOR: Record<GlobeLayer, string> = {
  event: 'var(--color-data-categorical-red)',
  unexplained: 'var(--color-data-categorical-orange)',
  disaster: 'var(--color-data-yellow-4)',
  trade: 'var(--color-data-categorical-teal)',
  polar: 'var(--color-data-categorical-cyan)',
};
const TOKEN_COLOR: Record<GlobeLayer, 'red' | 'orange' | 'yellow' | 'teal' | 'cyan'> = {
  event: 'red',
  unexplained: 'orange',
  disaster: 'yellow',
  trade: 'teal',
  polar: 'cyan',
};
const LAYERS: GlobeLayer[] = ['event', 'unexplained', 'disaster', 'trade', 'polar'];

type Feature = GeoJSON.Feature<GeoJSON.Geometry, { name: string }>;

const topo = worldTopo as unknown as Topology<{ countries: GeometryCollection<{ name: string }> }>;
const COUNTRIES = (
  feature(topo, topo.objects.countries) as unknown as GeoJSON.FeatureCollection<GeoJSON.Geometry, { name: string }>
).features as Feature[];
const BY_NUMERIC = new Map(COUNTRIES.map((f) => [String(f.id), f]));
const GRATICULE = geoGraticule10();

/** ISO3 → [경도, 위도]. 국경 폴리곤 중심, 없으면 작은 영토 표, 그래도 없으면 null. */
function locate(p: GlobePoint): [number, number] | null {
  if (p.lat !== null && p.lon !== null) return [p.lon, p.lat];
  if (!p.iso3) return null;
  const f = BY_NUMERIC.get(ISO3_NUMERIC[p.iso3] ?? '');
  if (f) return geoCentroid(f as GeoPermissibleObjects) as [number, number];
  const s = SMALL[p.iso3];
  return s ? [s[1], s[0]] : null;
}

/** 점 이름 — 서버가 화면 언어로 붙인 이름(title)이 ISO3 그대로면 지도 데이터의 영문명으로 대신한다. */
function pointName(p: GlobePoint): string {
  if (!p.iso3 || p.title !== p.iso3) return p.title;
  return BY_NUMERIC.get(ISO3_NUMERIC[p.iso3] ?? '')?.properties.name ?? p.iso3;
}

export default function ObservationGlobe({ data, labels }: { data: GlobeData; labels: ObservationsDict['globe'] }) {
  // 처음엔 아프리카·유럽·아시아·한국이 한 화면에 들어오게(경도 70°E, 위도 25°N 을 정면으로)
  const [rotate, setRotate] = useState<[number, number]>([-70, -25]);
  const [on, setOn] = useState<Record<GlobeLayer, boolean>>({
    event: true,
    unexplained: true,
    disaster: true,
    trade: true,
    polar: true,
  });
  const [selected, setSelected] = useState<string | null>(null);
  const drag = useRef<{ x: number; y: number; r: [number, number] } | null>(null);
  // 드래그로 돌린 뒤 손을 뗀 자리의 점이 선택되지 않게 — 4px 넘게 움직였으면 클릭으로 보지 않는다
  const moved = useRef(false);

  const projection = useMemo(
    () =>
      geoOrthographic()
        .scale(SIZE / 2 - 8)
        .translate([SIZE / 2, SIZE / 2])
        .rotate([rotate[0], rotate[1]])
        .clipAngle(90),
    [rotate],
  );
  // 소수 2자리로 고정 — 서버(Node)와 브라우저의 부동소수 끝자리가 달라 생기는 hydration 경고를 없앤다
  const path = useMemo(() => geoPath(projection).digits(2), [projection]);
  const center: [number, number] = [-rotate[0], -rotate[1]];

  const placed = useMemo(
    () =>
      data.points
        .map((p) => ({ p, at: locate(p) }))
        .filter((x): x is { p: GlobePoint; at: [number, number] } => x.at !== null),
    [data.points],
  );
  const notPlaced = data.points.length - placed.length;

  const counts = useMemo(() => {
    const c: Record<GlobeLayer, number> = { event: 0, unexplained: 0, disaster: 0, trade: 0, polar: 0 };
    for (const { p } of placed) c[p.layer] += 1;
    return c;
  }, [placed]);

  const korea = BY_NUMERIC.get(KOREA_NUMERIC);
  const pick = placed.find((x) => x.p.id === selected)?.p ?? null;

  function onDown(e: ReactPointerEvent<SVGSVGElement>) {
    drag.current = { x: e.clientX, y: e.clientY, r: rotate };
    moved.current = false;
  }
  function onMove(e: ReactPointerEvent<SVGSVGElement>) {
    const d = drag.current;
    if (!d) return;
    if (Math.abs(e.clientX - d.x) + Math.abs(e.clientY - d.y) > 4) moved.current = true;
    const k = 0.35;
    const lat = Math.max(-80, Math.min(80, d.r[1] - (e.clientY - d.y) * k));
    setRotate([d.r[0] + (e.clientX - d.x) * k, lat]);
  }
  function onUp() {
    drag.current = null;
  }

  return (
    <Card padding={4}>
      <VStack gap={3}>
        <VStack gap={1}>
          <Heading level={2}>{labels.title}</Heading>
          <Text type="supporting">{labels.lead}</Text>
        </VStack>

        <HStack gap={2} wrap="wrap">
          {LAYERS.map((layer) => (
            <Token
              key={layer}
              size="sm"
              color={on[layer] ? TOKEN_COLOR[layer] : 'gray'}
              label={`${labels.layers[layer]} ${counts[layer]}`}
              onClick={() => setOn((o) => ({ ...o, [layer]: !o[layer] }))}
              description={labels.dragHint}
            />
          ))}
          <Token size="sm" color="blue" label={labels.korea} />
        </HStack>
        {/* 휴대폰에서는 드래그가 페이지 스크롤과 겹치므로 버튼으로도 돌린다 */}
        <HStack gap={2} wrap="wrap">
          <Button size="sm" label={`◀ ${labels.rotateWest}`} onClick={() => setRotate(([l, p]) => [l + 30, p])} />
          <Button size="sm" label={`${labels.rotateEast} ▶`} onClick={() => setRotate(([l, p]) => [l - 30, p])} />
          <Button size="sm" variant="ghost" label={labels.toKorea} onClick={() => setRotate([-127.5, -36])} />
          <Button size="sm" variant="ghost" label={labels.toArctic} onClick={() => setRotate([-20, -75])} />
        </HStack>

        <HStack gap={4} wrap="wrap" vAlign="start">
          <VStack width="100%" maxWidth={SIZE}>
            {/* 아이콘이 아니라 지도 그림이라 SVG 가 그 자체로 필요하다 — astryx doctor 의 '아이콘 svg' 경고는 해당 없음 */}
            <svg
              viewBox={`0 0 ${SIZE} ${SIZE}`}
              width="100%"
              role="img"
              aria-label={labels.title}
              onPointerDown={onDown}
              onPointerMove={onMove}
              onPointerUp={onUp}
              onPointerCancel={onUp}
              onPointerLeave={onUp}
            >
              <path
                d={path({ type: 'Sphere' }) ?? ''}
                fill="var(--color-background-blue)"
                stroke="var(--color-border)"
              />
              <path d={path(GRATICULE) ?? ''} fill="none" stroke="var(--color-border)" strokeOpacity={0.5} />
              {COUNTRIES.map((f) => (
                <path
                  key={String(f.id ?? f.properties.name)}
                  d={path(f as GeoPermissibleObjects) ?? ''}
                  fill="var(--color-background-card)"
                  stroke="var(--color-border-emphasized)"
                  strokeWidth={0.4}
                />
              ))}
              {korea && (
                <path
                  d={path(korea as GeoPermissibleObjects) ?? ''}
                  fill="var(--color-data-blue-3)"
                  stroke="var(--color-data-blue-5)"
                  strokeWidth={1.2}
                >
                  <title>{labels.korea}</title>
                </path>
              )}
              {placed
                .filter(({ p, at }) => on[p.layer] && geoDistance(at, center) < Math.PI / 2 - 0.02)
                .sort((a, b) => b.p.count - a.p.count)
                .map(({ p, at }) => {
                  const xy = projection(at);
                  if (!xy) return null;
                  const r = Math.min(18, 4 + Math.sqrt(p.count) * 3);
                  const isPicked = p.id === selected;
                  return (
                    <g
                      key={p.id}
                      onClick={() => {
                        if (!moved.current) setSelected(p.id);
                      }}
                      cursor="pointer"
                    >
                      <circle
                        cx={Math.round(xy[0] * 100) / 100}
                        cy={Math.round(xy[1] * 100) / 100}
                        r={r}
                        fill={LAYER_COLOR[p.layer]}
                        fillOpacity={p.layer === 'polar' ? 0.75 : 0.6}
                        stroke={isPicked ? 'var(--color-border-emphasized)' : LAYER_COLOR[p.layer]}
                        strokeWidth={isPicked ? 2.5 : 1}
                      />
                      <title>{`${labels.layers[p.layer]} · ${pointName(p)} · ${p.count}`}</title>
                    </g>
                  );
                })}
            </svg>
          </VStack>

          <VStack gap={2} width="100%" maxWidth={360}>
            {pick ? (
              <>
                <Text type="label" color="accent">
                  {labels.layers[pick.layer]}
                </Text>
                <Heading level={3}>{pointName(pick)}</Heading>
                {pick.lines.map((line) => (
                  <Text key={line} type="supporting" display="block">
                    {line}
                  </Text>
                ))}
              </>
            ) : (
              <Text type="supporting">{labels.pick}</Text>
            )}
            <Text type="supporting">{labels.dragHint}</Text>
            <Text type="supporting">{labels.honesty}</Text>
            {data.unlocated + notPlaced > 0 && (
              <Text type="supporting">
                {labels.unlocated}: {data.unlocated + notPlaced}
              </Text>
            )}
          </VStack>
        </HStack>
      </VStack>
    </Card>
  );
}
