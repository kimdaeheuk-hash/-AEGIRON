'use client';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import type { Country } from '@/lib/api';
import { COUNTRY_COORDS } from '@/lib/countryCoords';

function scoreColor(score: number): string {
  if (score >= 80) return '#ef4444';
  if (score >= 60) return '#f97316';
  if (score >= 40) return '#fbbf24';
  return '#34d399';
}

// Leaflet + OpenStreetMap(CARTO 다크 타일) — 무료, API 토큰 불필요.
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
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
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
