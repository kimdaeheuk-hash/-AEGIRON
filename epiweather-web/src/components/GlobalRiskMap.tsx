'use client';
import { MapContainer, GeoJSON, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { feature } from 'topojson-client';
import type { Topology, GeometryCollection } from 'topojson-specification';
import worldTopo from 'world-atlas/countries-110m.json';
import type { Country } from '@/lib/api';
import { COUNTRY_COORDS } from '@/lib/countryCoords';

// ★ 배경 지도를 우리가 직접 그린다 (2026-10-18) ★
// 예전엔 CARTO 다크 타일(basemaps.cartocdn.com)을 썼는데, CARTO 가 키 없는 호출에
// "API KEY REQUIRED" 워터마크를 박기 시작해 모든 방문자의 지도가 워터마크로 덮였다
// (운영 캡처로 확인). 외부 타일 서버에 기대면 같은 일이 또 난다. 그래서 Natural Earth
// 1:110m 국경(world-atlas, 퍼블릭 도메인)을 번들에 넣어 GeoJSON 으로 그린다 — 키·외부
// 호출·사용 정책이 없다. 위험도 원은 그 위에 그대로 얹는다.
const WORLD = feature(
  worldTopo as unknown as Topology,
  (worldTopo as unknown as Topology).objects.countries as GeometryCollection,
);

function scoreColor(score: number): string {
  if (score >= 80) return '#ef4444';
  if (score >= 60) return '#f97316';
  if (score >= 40) return '#fbbf24';
  return '#34d399';
}

// Leaflet + 자체 국경 레이어(위 WORLD) — 외부 타일 없음.
// 좌표 우선순위: API 응답의 lat/lng(world_countries 캐시, Tier-2 자동발견 국가
// 포함) → 없으면 로컬 COUNTRY_COORDS(Tier-1 하드코딩 폴백). 둘 다 없는 항목은
// 지도에서는 건너뛰고 옆의 막대그래프(Screen1Banner)에서만 보이게 둔다.
function resolveCoord(c: Country): [number, number] | null {
  if (typeof c.lat === 'number' && typeof c.lng === 'number') return [c.lat, c.lng];
  return COUNTRY_COORDS[c.country] ?? null;
}

export default function GlobalRiskMap({ countries }: { countries: Country[] }) {
  return (
    <div className="grm-wrap" style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid var(--line)' }}>
      <MapContainer
        center={[15, 20]}
        zoom={1.4}
        minZoom={1}
        style={{ height: '100%', width: '100%', background: '#0e1623' }}
        scrollWheelZoom={false}
        worldCopyJump
        attributionControl={false}
      >
        <GeoJSON
          data={WORLD}
          interactive={false}
          style={{ color: '#2b3a52', weight: 0.6, fillColor: '#18233a', fillOpacity: 1 }}
        />
        {countries.map(c => {
          const coord = resolveCoord(c);
          if (!coord) return null;
          const score = c.risk_score ?? 0;
          const col = scoreColor(score);
          return (
            <CircleMarker
              key={c.country}
              center={coord}
              radius={6 + Math.min(score, 100) / 6}
              pathOptions={{ color: col, fillColor: col, fillOpacity: 0.55, weight: 1.5 }}
            >
              <Popup>
                <div style={{ fontSize: 12 }}>
                  <strong>{c.name ?? c.country}</strong>{c.coverage_tier === 'auto' ? ' (자동발견)' : ''}<br />
                  위험도: {Math.round(score)}{c.tier ? ` · ${c.tier}` : ''}
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
