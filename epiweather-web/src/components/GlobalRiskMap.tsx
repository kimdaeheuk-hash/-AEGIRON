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
// 국가 좌표가 없는 항목(COUNTRY_COORDS 미등록)은 지도에서는 건너뛰고
// 옆의 막대그래프(Screen1Banner)에서만 보이게 둔다.
export default function GlobalRiskMap({ countries }: { countries: Country[] }) {
  return (
    <div style={{ height: 260, borderRadius: 10, overflow: 'hidden', border: '1px solid var(--line)' }}>
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
          const coord = COUNTRY_COORDS[c.country];
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
                  <strong>{c.country}</strong><br />
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
