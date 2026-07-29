'use client';
import { useStore } from '@/lib/store';
import { proj, arc } from '@/lib/algorithms';

const VW = 1000, VH = 400;
const KR = { lon: 127, lat: 37 };

// auto 국가명은 World Bank 외부 데이터라 dangerouslySetInnerHTML(SVG 문자열)에
// 넣기 전 이스케이프 — curated 이름은 하드코딩이라 원래 안전하지만 통일 적용.
function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export default function Stage3Global() {
  const { glob, originsCatalog } = useStore();
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

  // 큐레이션 도시(실측 기반)는 항상 이름표와 함께 표시. World Bank 전세계
  // 국가(auto, 210여개)는 점만 작고 흐리게 찍어 "전세계 커버리지"는 보이되
  // 210개 이름표·화살표로 지도가 뒤죽박죽되지 않게 함. 선택된 발원지는
  // auto든 curated든 항상 강조 표시.
  const curated = originsCatalog.filter(c => c.tier === 'curated');
  const auto = originsCatalog.filter(c => c.tier === 'auto' && c.id !== glob.city.id);

  const originArc = (() => {
    const c = glob.city;
    const a = proj(c.lon, c.lat, VW, VH);
    const lift = Math.abs(a.x - kr.x) * 0.18 + 30;
    const w = 0.4 + c.pax * 2.6 + 0.6;
    const path = arc(a.x, a.y, kr.x, kr.y, lift);
    return `<path d="${path}" fill="none" stroke="rgba(244,63,94,.85)" stroke-width="${w}"/>`
      + `<circle r="4" fill="#fff"><animateMotion dur="2.4s" repeatCount="indefinite" path="${path}"/></circle>`;
  })();

  const curatedDots = curated.filter(c => c.id !== glob.city.id).map(c => {
    const a = proj(c.lon, c.lat, VW, VH);
    const col = c.er >= .75 ? '#fbbf24' : '#2a3647';
    return `<circle cx="${a.x}" cy="${a.y}" r="5" fill="${col}" stroke="#0a0e14" stroke-width="1.5"/>`
      + `<text x="${a.x}" y="${a.y - 8}" fill="var(--muted)" font-size="9" text-anchor="middle">${esc(c.nm)}</text>`;
  }).join('');

  const autoDots = auto.map(c => {
    const a = proj(c.lon, c.lat, VW, VH);
    return `<circle cx="${a.x}" cy="${a.y}" r="2.2" fill="rgba(120,140,170,.35)"/>`;
  }).join('');

  const originDot = (() => {
    const c = glob.city;
    const a = proj(c.lon, c.lat, VW, VH);
    return `<circle cx="${a.x}" cy="${a.y}" r="14" fill="none" stroke="#f43f5e" stroke-width="1.5" opacity=".5"><animate attributeName="r" values="8;18;8" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".6;0;.6" dur="2s" repeatCount="indefinite"/></circle>`
      + `<circle cx="${a.x}" cy="${a.y}" r="8" fill="#f43f5e" stroke="#0a0e14" stroke-width="1.5"/>`
      + `<text x="${a.x}" y="${a.y - 11}" fill="#fff" font-size="11" font-weight="700" text-anchor="middle">${esc(c.nm)}</text>`;
  })();

  const arcs = originArc;
  const dots = autoDots + curatedDots + originDot;

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
