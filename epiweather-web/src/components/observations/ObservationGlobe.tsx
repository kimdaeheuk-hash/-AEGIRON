'use client';

/**
 * 관측 지구본 + 나라별 위험 카드 (2026-11-15 v2 — 캡틴: "지구본이 너무 질이 떨어져",
 * "이대로 가면 데이터를 활용 못하고 사업화가 안 돼").
 *
 * 3D 지구본(Globe3D, WebGL)은 브라우저에서만 불러온다(next/dynamic ssr:false).
 * 나라를 누르면 그 나라에 모인 모든 관측(보도·설명불가·재난·무역·CDC 경보·위험지수·한국 연결)이
 * 카드 한 장으로 나온다 — 이 카드가 상품(구독·API·기관 브리핑)의 단위다.
 */
import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { geoCentroid } from 'd3-geo';
import type { GeoPermissibleObjects } from 'd3-geo';
import { feature } from 'topojson-client';
import type { GeometryCollection, Topology } from 'topojson-specification';
import worldTopo from 'world-atlas/countries-110m.json';
import { Button } from '@astryxdesign/core/Button';
import { Card } from '@astryxdesign/core/Card';
import { HStack } from '@astryxdesign/core/HStack';
import { Link } from '@astryxdesign/core/Link';
import { Heading, Text } from '@astryxdesign/core/Text';
import { Token } from '@astryxdesign/core/Token';
import { VStack } from '@astryxdesign/core/VStack';
import { AstryxProvider } from '@/components/AstryxProvider';
import type { ObservationsDict } from '@/i18n/types';
import type { CardsData, CountryCard } from '@/lib/countryCards';
import type { GlobeData, GlobePoint } from '@/lib/globeData';
import { ISO3_NUMERIC, SMALL } from '@/lib/isoGeo';
import type { HexFeature, PlacedCard, Pov } from './Globe3D';

const Globe3D = dynamic(() => import('./Globe3D'), { ssr: false });

type Feature = GeoJSON.Feature<GeoJSON.Geometry, { name: string }>;
const topo = worldTopo as unknown as Topology<{ countries: GeometryCollection<{ name: string }> }>;
const COUNTRIES = (
  feature(topo, topo.objects.countries) as unknown as GeoJSON.FeatureCollection<GeoJSON.Geometry, { name: string }>
).features as Feature[];
const NUMERIC_ISO3: Record<string, string> = Object.fromEntries(Object.entries(ISO3_NUMERIC).map(([i, n]) => [n, i]));
const BY_NUMERIC = new Map(COUNTRIES.map((f) => [String(f.id), f]));
/**
 * 육각 격자(h3)는 점 하나가 반복된 퇴화 폴리곤에서 예외를 던진다 — world-atlas 1:110m 의 북한(408) 첫 조각이
 * 그렇다(2026-11-15 로컬 렌더에서 확인). 서로 다른 점이 3개 미만인 조각은 빼고 넘긴다.
 */
function sane(ring: GeoJSON.Position[]): boolean {
  return new Set(ring.map((p) => `${p[0]},${p[1]}`)).size >= 3;
}
function sanitize(f: Feature): Feature {
  const g = f.geometry;
  if (g.type === 'MultiPolygon') {
    return { ...f, geometry: { ...g, coordinates: g.coordinates.filter((poly) => sane(poly[0])) } };
  }
  return f;
}
const HEXES: HexFeature[] = COUNTRIES.map((f) => ({ ...sanitize(f), iso3: NUMERIC_ISO3[String(f.id)] ?? null })).filter(
  (f) => f.geometry.type !== 'Polygon' || sane(f.geometry.coordinates[0]),
);

const START: Pov = { lat: 22, lng: 70, altitude: 2.3 };
const KOREA: Pov = { lat: 36, lng: 127.5, altitude: 1.5 };
const ARCTIC: Pov = { lat: 78, lng: 10, altitude: 2.1 };
const ANTARCTIC: Pov = { lat: -70, lng: -57, altitude: 2.1 };

/** ISO3 → [경도, 위도] : 국경 중심 → 작은 영토 표 → null */
function centroid(iso3: string): [number, number] | null {
  const f = BY_NUMERIC.get(ISO3_NUMERIC[iso3] ?? '');
  if (f) return geoCentroid(f as GeoPermissibleObjects) as [number, number];
  const s = SMALL[iso3];
  return s ? [s[1], s[0]] : null;
}

type Layers = { rings: boolean; arcs: boolean; polar: boolean; disaster: boolean };
type Selected = { kind: 'country'; iso3: string | null; name: string } | { kind: 'point'; id: string } | null;

export default function ObservationGlobe({
  data,
  cards,
  labels,
  countryHref,
  openLabel,
}: {
  data: GlobeData;
  cards: CardsData;
  labels: ObservationsDict['globe'];
  /** 나라 페이지 경로 접두(예: /ko/observations) — 주면 카드에 '나라 페이지 열기' 링크 */
  countryHref?: string;
  openLabel?: string;
}) {
  const t = labels.card;
  // 좁은 화면에서는 지구본이 작아 보이므로 처음 시점을 더 가깝게(시점은 브라우저 전용 지구본에만 쓰여 SSR 마크업과 무관)
  const [pov, setPov] = useState<Pov>(() =>
    typeof window !== 'undefined' && window.innerWidth < 700 ? { ...START, altitude: 1.7 } : START,
  );
  const [layers, setLayers] = useState<Layers>({ rings: true, arcs: true, polar: true, disaster: true });
  const [selected, setSelected] = useState<Selected>(null);
  const [size, setSize] = useState({ w: 640, h: 560 });

  useEffect(() => {
    // 화면 폭에 맞춘 지구본 크기 — 데스크톱은 옆에 카드, 휴대폰은 위아래
    const fit = () => {
      const vw = window.innerWidth;
      const w = vw >= 1100 ? 700 : Math.max(300, Math.min(700, vw - 72));
      setSize({ w, h: Math.round(w * (vw >= 1100 ? 0.86 : 1)) });
    };
    fit();
    window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
  }, []);

  const placedCards: PlacedCard[] = useMemo(
    () =>
      cards.cards
        .map((c) => ({
          ...c,
          at: c.lat !== null && c.lng !== null ? ([c.lng, c.lat] as [number, number]) : centroid(c.iso3),
        }))
        .filter((c): c is PlacedCard => c.at !== null),
    [cards.cards],
  );

  const points = useMemo(
    () =>
      data.points
        .filter((p) => (p.layer === 'polar' && layers.polar) || (p.layer === 'disaster' && layers.disaster))
        .map((p) => ({
          ...p,
          at:
            p.lat !== null && p.lon !== null ? ([p.lon, p.lat] as [number, number]) : p.iso3 ? centroid(p.iso3) : null,
        }))
        .filter((p): p is GlobePoint & { at: [number, number] } => p.at !== null),
    [data.points, layers.polar, layers.disaster],
  );

  const pickedCard: CountryCard | null =
    selected?.kind === 'country' && selected.iso3 ? (cards.cards.find((c) => c.iso3 === selected.iso3) ?? null) : null;
  const pickedPoint: GlobePoint | null =
    selected?.kind === 'point' ? (data.points.find((p) => p.id === selected.id) ?? null) : null;

  const counts: Record<keyof Layers, number> = {
    rings: placedCards.filter((c) => c.counts.event + c.counts.unexplained > 0).length,
    arcs: placedCards.filter((c) => (c.korea.routes ?? 0) > 0 || (c.korea.passengers ?? 0) > 0).length,
    polar: data.points.filter((p) => p.layer === 'polar').length,
    disaster: data.points.filter((p) => p.layer === 'disaster').length,
  };
  const layerLabel: Record<keyof Layers, string> = {
    rings: `${labels.layers.event} · ${labels.layers.unexplained}`,
    arcs: t.korea,
    polar: labels.layers.polar,
    disaster: labels.layers.disaster,
  };
  const layerColor: Record<keyof Layers, 'red' | 'blue' | 'cyan' | 'yellow'> = {
    rings: 'red',
    arcs: 'blue',
    polar: 'cyan',
    disaster: 'yellow',
  };
  const gradeColor = (g: CountryCard['grade']) => (g === 'high' ? 'red' : g === 'elevated' ? 'orange' : 'yellow');

  function focusCard(c: CountryCard) {
    setSelected({ kind: 'country', iso3: c.iso3, name: c.name });
    const at = c.lat !== null && c.lng !== null ? ([c.lng, c.lat] as [number, number]) : centroid(c.iso3);
    if (at) setPov({ lat: at[1], lng: at[0], altitude: 1.6 });
  }

  return (
    <AstryxProvider mode="dark">
      <Card padding={4}>
        <VStack gap={3}>
          <VStack gap={1}>
            <Heading level={2}>{labels.title}</Heading>
            <Text type="supporting">{labels.lead}</Text>
          </VStack>

          <HStack gap={2} wrap="wrap">
            {(Object.keys(layers) as (keyof Layers)[]).map((k) => (
              <Token
                key={k}
                size="sm"
                color={layers[k] ? layerColor[k] : 'gray'}
                label={`${layerLabel[k]} ${counts[k]}`}
                onClick={() => setLayers((l) => ({ ...l, [k]: !l[k] }))}
              />
            ))}
          </HStack>
          <HStack gap={2} wrap="wrap">
            <Button size="sm" label={labels.toKorea} onClick={() => setPov({ ...KOREA })} />
            <Button size="sm" label={labels.toArctic} onClick={() => setPov({ ...ARCTIC })} />
            <Button size="sm" variant="ghost" label={labels.toAntarctic} onClick={() => setPov({ ...ANTARCTIC })} />
            <Button
              size="sm"
              variant="ghost"
              label={`◀ ${labels.rotateWest}`}
              onClick={() => setPov((p) => ({ ...p, lng: p.lng - 40 }))}
            />
            <Button
              size="sm"
              variant="ghost"
              label={`${labels.rotateEast} ▶`}
              onClick={() => setPov((p) => ({ ...p, lng: p.lng + 40 }))}
            />
          </HStack>

          <HStack gap={4} wrap="wrap" vAlign="start">
            <VStack width={size.w}>
              <Globe3D
                width={size.w}
                height={size.h}
                hexes={HEXES}
                cards={placedCards}
                points={points}
                showRings={layers.rings}
                showArcs={layers.arcs && cards.koreaAvailable}
                koreaLabel={labels.korea}
                pov={pov}
                onCountry={(iso3, name) => setSelected({ kind: 'country', iso3, name })}
                onPoint={(id) => setSelected({ kind: 'point', id })}
              />
            </VStack>

            <VStack gap={2} width="100%" maxWidth={380}>
              {pickedCard ? (
                <>
                  <HStack gap={2} vAlign="center" wrap="wrap">
                    <Heading level={3}>{pickedCard.name}</Heading>
                    <Token size="sm" color={gradeColor(pickedCard.grade)} label={t.grade[pickedCard.grade]} />
                  </HStack>
                  {countryHref && openLabel && (
                    <Link href={`${countryHref}/${pickedCard.iso3}`}>
                      <Text type="supporting" color="inherit">
                        {openLabel}
                      </Text>
                    </Link>
                  )}
                  <Text weight="semibold">
                    {t.intensity} {pickedCard.intensity}/100
                  </Text>
                  <Text type="supporting">
                    {t.counts}: {labels.layers.event} {pickedCard.counts.event} · {labels.layers.unexplained}{' '}
                    {pickedCard.counts.unexplained} · {labels.layers.disaster} {pickedCard.counts.disaster} ·{' '}
                    {labels.layers.trade} {pickedCard.counts.trade}
                  </Text>
                  {pickedCard.travelLevel !== null && (
                    <Text type="supporting">
                      {t.travel}: {pickedCard.travelTitles[0]}
                    </Text>
                  )}
                  {pickedCard.riskScore !== null && (
                    <Text type="supporting">
                      {t.riskScore}: {pickedCard.riskScore}
                      {pickedCard.dominantDisease ? ` · ${t.dominant}: ${pickedCard.dominantDisease}` : ''}
                    </Text>
                  )}
                  <Text type="supporting">
                    {t.korea}:{' '}
                    {pickedCard.korea.routes !== null || pickedCard.korea.passengers !== null
                      ? [
                          pickedCard.korea.routes !== null ? `${t.koreaRoutes} ${pickedCard.korea.routes}` : null,
                          pickedCard.korea.passengers !== null
                            ? `${t.koreaPassengers} ${pickedCard.korea.passengers.toLocaleString('en-US')}`
                            : null,
                        ]
                          .filter(Boolean)
                          .join(' · ')
                      : t.koreaNone}
                  </Text>
                  <Text type="label">{t.evidence}</Text>
                  {pickedCard.evidence.slice(0, 8).map((e) => (
                    <Text key={`${e.layer}-${e.line}`} type="supporting" display="block">
                      {e.layer === 'travel' ? t.travel : labels.layers[e.layer]} · {e.line}
                    </Text>
                  ))}
                </>
              ) : pickedPoint ? (
                <>
                  <Text type="label" color="accent">
                    {labels.layers[pickedPoint.layer]}
                  </Text>
                  <Heading level={3}>{pickedPoint.title}</Heading>
                  {pickedPoint.lines.map((line) => (
                    <Text key={line} type="supporting" display="block">
                      {line}
                    </Text>
                  ))}
                </>
              ) : (
                <>
                  {selected?.kind === 'country' && <Heading level={3}>{selected.name}</Heading>}
                  <Text type="label">{t.top}</Text>
                  {cards.cards.slice(0, 8).map((c) => (
                    <HStack key={c.iso3} gap={2} vAlign="center">
                      <Token
                        size="sm"
                        color={gradeColor(c.grade)}
                        label={`${c.intensity}`}
                        onClick={() => focusCard(c)}
                      />
                      <Text>{c.name}</Text>
                    </HStack>
                  ))}
                  <Text type="supporting">{labels.pick}</Text>
                </>
              )}
              <Text type="supporting">{t.intensityNote}</Text>
              <Text type="supporting">{cards.koreaAvailable ? t.arcNote : t.koreaUnavailable}</Text>
              <Text type="supporting">{labels.honesty}</Text>
              {data.unlocated > 0 && (
                <Text type="supporting">
                  {labels.unlocated}: {data.unlocated}
                </Text>
              )}
            </VStack>
          </HStack>
        </VStack>
      </Card>
    </AstryxProvider>
  );
}
