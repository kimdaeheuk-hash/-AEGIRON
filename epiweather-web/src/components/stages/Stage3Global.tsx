'use client';
import { useStore } from '@/lib/store';
import { CITIES, proj, arc } from '@/lib/algorithms';

const VW = 1000, VH = 400;
const KR = { lon: 127, lat: 37 };

export default function Stage3Global() {
  const { glob } = useStore();
  if (!glob) return null;

  const kr = proj(KR.lon, KR.lat, VW, VH);
  const riskCol = glob.risk < 40 ? '#34d399' : glob.risk < 60 ? '#eab308' : glob.risk < 80 ? '#f97316' : '#ef4444';

  // SVG 내용
  const gridLines: string[] = [];
  for (let lon = -150; lon <= 150; lon += 30) {
    const p = proj(lon, 0, VW, VH);
    gridLines.push(`<line x1="${p.x}" y1="0" x2="${p.x}" y2="${VH}" stroke="rgba(120,140,170,.05)"/>`);
  }
  for (let lat = -60; lat <= 60; lat += 30) {
    const p = proj(0, lat, VW, VH);
    gridLines.push(`<line x1="0" y1="${p.y}" x2="${VW}" y2="${p.y}" stroke="rgba(120,140,170,.05)"/>`);
  }

  const arcs = CITIES.map(c => {
    const a = proj(c.lon, c.lat, VW, VH);
    const lift = Math.abs(a.x - kr.x) * 0.18 + 30;
    const w = 0.4 + c.pax * 2.6;
    const isOrigin = c.id === glob.city.id;
    const col = isOrigin ? 'rgba(244,63,94,.85)' : 'rgba(120,140,170,.18)';
    let svg = `<path d="${arc(a.x, a.y, kr.x, kr.y, lift)}" fill="none" stroke="${col}" stroke-width="${isOrigin ? w + 0.6 : w}"/>`;
    if (isOrigin) {
      svg += `<circle r="4" fill="#fff"><animateMotion dur="2.4s" repeatCount="indefinite" path="${arc(a.x, a.y, kr.x, kr.y, lift)}"/></circle>`;
    }
    return svg;
  }).join('');

  const dots = CITIES.map(c => {
    const a = proj(c.lon, c.lat, VW, VH);
    const isOrigin = c.id === glob.city.id;
    let svg = '';
    if (isOrigin) {
      svg += `<circle cx="${a.x}" cy="${a.y}" r="14" fill="none" stroke="#f43f5e" stroke-width="1.5" opacity=".5"><animate attributeName="r" values="8;18;8" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".6;0;.6" dur="2s" repeatCount="indefinite"/></circle>`;
    }
    const col = isOrigin ? '#f43f5e' : c.er >= .75 ? '#fbbf24' : '#2a3647';
    const rad = isOrigin ? 8 : 5;
    svg += `<circle cx="${a.x}" cy="${a.y}" r="${rad}" fill="${col}" stroke="#0a0e14" stroke-width="1.5"/>`;
    svg += `<text x="${a.x}" y="${a.y - rad - 3}" fill="${isOrigin ? '#fff' : 'var(--muted)'}" font-size="${isOrigin ? 11 : 9}" font-weight="${isOrigin ? 700 : 400}" text-anchor="middle">${c.nm}</text>`;
    return svg;
  }).join('');

  const krDot = `<circle cx="${kr.x}" cy="${kr.y}" r="9" fill="#38bdf8" stroke="#0a0e14" stroke-width="2"/><text x="${kr.x}" y="${kr.y + 20}" fill="#38bdf8" font-size="11" font-weight="700" text-anchor="middle">한국 ◎</text>`;

  const sorted = [...glob.dist].sort((a, b) => b.w - a.w);

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">글로벌 유입 감지</div>
      <div className="psub">
        한국은 발생국이 아니라{' '}
        <em style={{ color: 'var(--violet)', fontStyle: 'normal', fontWeight: 600 }}>유입 대비국</em>.
        해외 발원지에서 항공망 타고 한국 도착 시점·관문을 예측.
      </div>

      <div className="card">
        <div className="card-h">
          <span className="lbl">글로벌 항공망 지도</span>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>{glob.city.nm} 발원</span>
        </div>
        <svg
          viewBox={`0 0 ${VW} ${VH}`}
          style={{ width: '100%', height: 'auto', display: 'block', background: 'linear-gradient(180deg,#0a1018,#0b1220)', borderRadius: 10 }}
          dangerouslySetInnerHTML={{ __html: gridLines.join('') + arcs + dots + krDot }}
        />
      </div>

      <div className="grid2">
        <div className="card">
          <div className="card-h"><span className="lbl">유입 위험 추론</span></div>
          <div className="outcomes">
            <div className="oc">
              <div className="ok">✈ 한국 첫 유입</div>
              <div className="ov" style={{ color: riskCol }}>D+{glob.arrival}</div>
              <div className="od">발원지 기준</div>
            </div>
            <div className="oc">
              <div className="ok">🌐 유입 위험지수</div>
              <div className="ov" style={{ color: riskCol }}>{glob.risk}</div>
              <div className="od">출현×여객</div>
            </div>
            <div className="oc">
              <div className="ok">🟢 WHO 선행</div>
              <div className="ov" style={{ color: 'var(--ok)' }}>D−{glob.detectLead}</div>
              <div className="od">조기탐지</div>
            </div>
            <div className="oc">
              <div className="ok">🏷 발원 특성</div>
              <div className="ov" style={{ fontSize: 12 }}>{glob.city.note}</div>
              <div className="od">출현 {Math.round(glob.city.er * 100)}</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-h"><span className="lbl">입국 관문별 도착</span></div>
          {sorted.map((x, i) => {
            const day = glob.arrival + Math.round(i * 1.5);
            const pct = Math.round(x.w * 100);
            const col = i === 0 ? '#f43f5e' : i === 1 ? '#fb923c' : '#38bdf8';
            return (
              <div key={x.port.id} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <div style={{ fontSize: 12, width: 100 }}>
                  {x.port.nm}
                  <small style={{ display: 'block', fontFamily: 'var(--mono)', fontSize: 8.5, color: 'var(--muted2)' }}>{x.port.eng}</small>
                </div>
                <div style={{ flex: 1, height: 7, background: 'rgba(255,255,255,.06)', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{ width: `${pct}%`, height: '100%', borderRadius: 4, background: col }} />
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 11, width: 70, textAlign: 'right', color: col }}>
                  <b style={{ fontSize: 14 }}>{pct}%</b>D+{day}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
