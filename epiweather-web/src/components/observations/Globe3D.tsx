'use client';

/**
 * 3D 관측 지구본(WebGL, globe.gl) — ObservationGlobe 가 next/dynamic(ssr:false)으로만 불러온다.
 *
 * - 국토: 육각 격자(hex). 관측이 있는 나라는 관측 강도에 따라 색·높이가 오른다. 한국은 따로 강조.
 * - 발생 보도·설명 불가 신호가 있는 나라: 맥동하는 링.
 * - 한국과 항공으로 연결된 관측 국가 → 서울: 움직이는 호(유입 경로).
 * - 극지 8곳: 기둥(관찰 점수 높이), 재난 감시창·의료물자 급증: 작은 점.
 *
 * 색은 Astryx 토큰을 런타임에 읽는다(WebGL 은 CSS 변수를 못 읽으므로 계산된 값으로 넘긴다).
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import Globe from 'react-globe.gl';
import type { GlobeMethods } from 'react-globe.gl';
import { MeshPhongMaterial } from 'three';
import type { CountryCard } from '@/lib/countryCards';
import type { GlobePoint } from '@/lib/globeData';

export type Pov = { lat: number; lng: number; altitude: number };

export type HexFeature = GeoJSON.Feature<GeoJSON.Geometry, { name: string }> & { iso3: string | null };

export type PlacedCard = CountryCard & { at: [number, number] };

type Colors = {
  ocean: string;
  oceanGlow: string;
  land: string;
  korea: string;
  high: string;
  elevated: string;
  watch: string;
  ring: string;
  ringAlt: string;
  polar: string;
  disaster: string;
  trade: string;
  atmosphere: string;
  label: string;
};

const SEOUL = { lat: 37.5665, lng: 126.978 };

/** Astryx 토큰 → 실제 색 문자열. 못 읽으면(테마 밖) 무채색 계열로. */
function readColors(el: HTMLElement | null): Colors {
  const cs = el ? getComputedStyle(el) : null;
  const v = (name: string, fallback: string) => cs?.getPropertyValue(name).trim() || fallback;
  return {
    ocean: v('--color-data-blue-5', 'rgb(20,40,80)'),
    oceanGlow: v('--color-background-surface', 'rgb(10,14,24)'),
    land: v('--color-border-emphasized', 'rgb(120,130,150)'),
    korea: v('--color-data-blue-2', 'rgb(120,180,255)'),
    high: v('--color-data-red-3', 'rgb(240,80,80)'),
    elevated: v('--color-data-orange-3', 'rgb(240,150,60)'),
    watch: v('--color-data-yellow-3', 'rgb(230,200,80)'),
    ring: v('--color-data-red-2', 'rgb(255,120,120)'),
    ringAlt: v('--color-data-orange-2', 'rgb(255,170,90)'),
    polar: v('--color-data-teal-2', 'rgb(120,230,230)'),
    disaster: v('--color-data-yellow-2', 'rgb(255,220,110)'),
    trade: v('--color-data-teal-3', 'rgb(60,190,170)'),
    atmosphere: v('--color-data-blue-2', 'rgb(120,180,255)'),
    label: v('--color-text-primary', 'rgb(235,238,245)'),
  };
}

/** 'rgb(1,2,3)' / '#abc' → rgba 문자열 (링 페이드용) */
function withAlpha(color: string, a: number): string {
  const m = color.match(/rgba?\(([^)]+)\)/);
  if (m) {
    const [r, g, b] = m[1].split(',').map((x) => x.trim());
    return `rgba(${r},${g},${b},${a})`;
  }
  if (color.startsWith('#') && (color.length === 7 || color.length === 4)) {
    const hex = color.length === 4 ? color.replace(/^#(.)(.)(.)$/, '#$1$1$2$2$3$3') : color;
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  }
  return color;
}

export default function Globe3D(props: {
  width: number;
  height: number;
  hexes: HexFeature[];
  cards: PlacedCard[];
  points: GlobePoint[];
  showRings: boolean;
  showArcs: boolean;
  koreaLabel: string;
  pov: Pov;
  onCountry: (iso3: string | null, name: string) => void;
  onPoint: (id: string) => void;
}) {
  const { width, height, hexes, cards, points, showRings, showArcs, koreaLabel, pov, onCountry, onPoint } = props;
  const ref = useRef<GlobeMethods | undefined>(undefined);
  const host = useRef<HTMLElement | null>(null);
  const [colors, setColors] = useState<Colors>(() => readColors(null));

  useEffect(() => {
    // 캔버스를 감싼 가장 가까운 Astryx 테마 범위에서 계산된 토큰 색을 읽는다
    const canvas = ref.current?.renderer().domElement;
    host.current = (canvas?.closest('[data-astryx-theme]') as HTMLElement | null) ?? document.documentElement;
    setColors(readColors(host.current));
  }, []);

  const byIso = useMemo(() => new Map(cards.map((c) => [c.iso3, c])), [cards]);

  const material = useMemo(
    () =>
      new MeshPhongMaterial({
        color: colors.ocean,
        emissive: colors.oceanGlow,
        emissiveIntensity: 0.35,
        shininess: 12,
      }),
    [colors.ocean, colors.oceanGlow],
  );

  useEffect(() => {
    const g = ref.current;
    if (!g) return;
    const controls = g.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;
    controls.enableDamping = true;
  }, []);

  useEffect(() => {
    ref.current?.pointOfView(pov, 1200);
  }, [pov]);

  const rings = useMemo(
    () => (showRings ? cards.filter((c) => c.counts.event + c.counts.unexplained > 0) : []),
    [cards, showRings],
  );
  const arcs = useMemo(
    () =>
      showArcs
        ? cards
            .filter((c) => (c.korea.routes ?? 0) > 0 || (c.korea.passengers ?? 0) > 0)
            .filter((c) => c.iso3 !== 'KOR')
            .map((c) => ({ c, startLat: c.at[1], startLng: c.at[0], endLat: SEOUL.lat, endLng: SEOUL.lng }))
        : [],
    [cards, showArcs],
  );
  const labels = useMemo(
    () => [
      { lat: SEOUL.lat, lng: SEOUL.lng, text: koreaLabel, korea: true },
      ...cards.slice(0, 6).map((c) => ({ lat: c.at[1], lng: c.at[0], text: c.name, korea: false })),
    ],
    [cards, koreaLabel],
  );

  const gradeColor = (c: CountryCard) =>
    c.grade === 'high' ? colors.high : c.grade === 'elevated' ? colors.elevated : colors.watch;

  return (
    <Globe
      ref={ref}
      width={width}
      height={height}
      backgroundColor="rgba(0,0,0,0)"
      globeMaterial={material}
      showAtmosphere
      atmosphereColor={colors.atmosphere}
      atmosphereAltitude={0.2}
      hexPolygonsData={hexes}
      hexPolygonResolution={3}
      hexPolygonMargin={0.32}
      hexPolygonUseDots={false}
      hexPolygonAltitude={(d) => {
        const f = d as HexFeature;
        if (f.iso3 === 'KOR') return 0.02;
        const c = f.iso3 ? byIso.get(f.iso3) : undefined;
        return c ? 0.012 + (c.intensity / 100) * 0.05 : 0.006;
      }}
      hexPolygonColor={(d) => {
        const f = d as HexFeature;
        if (f.iso3 === 'KOR') return colors.korea;
        const c = f.iso3 ? byIso.get(f.iso3) : undefined;
        return c ? (c.grade === 'watch' ? withAlpha(colors.watch, 0.6) : gradeColor(c)) : withAlpha(colors.land, 0.55);
      }}
      hexPolygonLabel={(d) => {
        const f = d as HexFeature;
        const c = f.iso3 ? byIso.get(f.iso3) : undefined;
        return c ? `${c.name} · ${c.intensity}` : f.properties.name;
      }}
      onHexPolygonClick={(d) => {
        const f = d as HexFeature;
        if (ref.current) ref.current.controls().autoRotate = false;
        onCountry(f.iso3, f.properties.name);
      }}
      ringsData={rings}
      ringLat={(d) => (d as PlacedCard).at[1]}
      ringLng={(d) => (d as PlacedCard).at[0]}
      ringColor={(d: object) => {
        const c = d as PlacedCard;
        const base = c.counts.event > 0 ? colors.ring : colors.ringAlt;
        return (t: number) => withAlpha(base, 1 - t);
      }}
      ringMaxRadius={(d) => 2 + (d as PlacedCard).intensity / 22}
      ringPropagationSpeed={2.2}
      ringRepeatPeriod={1100}
      arcsData={arcs}
      arcColor={() => [withAlpha(colors.high, 0.9), withAlpha(colors.korea, 0.9)]}
      arcDashLength={0.45}
      arcDashGap={0.25}
      arcDashAnimateTime={2600}
      arcStroke={0.55}
      arcAltitudeAutoScale={0.42}
      pointsData={points}
      pointLat={(d) => (d as GlobePoint & { at: [number, number] }).at[1]}
      pointLng={(d) => (d as GlobePoint & { at: [number, number] }).at[0]}
      pointColor={(d) => {
        const p = d as GlobePoint;
        return p.layer === 'polar' ? colors.polar : p.layer === 'disaster' ? colors.disaster : colors.trade;
      }}
      pointAltitude={(d) => {
        const p = d as GlobePoint;
        return p.layer === 'polar' ? 0.04 + p.count * 0.025 : 0.025;
      }}
      pointRadius={(d) => ((d as GlobePoint).layer === 'polar' ? 0.9 : 0.45)}
      pointLabel={(d) => (d as GlobePoint).title}
      onPointClick={(d) => {
        if (ref.current) ref.current.controls().autoRotate = false;
        onPoint((d as GlobePoint).id);
      }}
      htmlElementsData={labels}
      htmlLat="lat"
      htmlLng="lng"
      htmlAltitude={0.03}
      htmlElement={(d) => {
        // three.js 글꼴에는 한글이 없어 '???' 로 나온다 — 이름표는 HTML 로 그린다(지구본이 그리는 오버레이)
        const l = d as { text: string; korea: boolean };
        const el = document.createElement('span');
        el.textContent = l.text;
        el.style.color = l.korea ? colors.korea : withAlpha(colors.label, 0.9);
        el.style.font = `${l.korea ? 700 : 600} ${l.korea ? 13 : 11}px system-ui, sans-serif`;
        el.style.textShadow = '0 1px 3px rgba(0,0,0,0.9)';
        el.style.pointerEvents = 'none';
        el.style.whiteSpace = 'nowrap';
        el.style.transform = 'translate(-50%, -140%)';
        return el;
      }}
    />
  );
}
