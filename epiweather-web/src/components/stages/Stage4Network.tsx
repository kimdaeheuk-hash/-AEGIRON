'use client';
import { useStore } from '@/lib/store';
import { REGIONS, MOBILITY, clamp } from '@/lib/algorithms';

export default function Stage4Network() {
  const { dom } = useStore();
  if (!dom) return null;

  const MAX_D = 35;
  const origin = 'IC';

  // 링크 (중복 방지)
  const links: string[] = [];
  const drawn = new Set<string>();
  REGIONS.forEach(a => {
    const m = MOBILITY[a.id] || {};
    Object.keys(m).forEach(bid => {
      const key = [a.id, bid].sort().join('-');
      if (drawn.has(key)) return;
      drawn.add(key);
      const b = REGIONS.find(r => r.id === bid)!;
      const w = m[bid];
      links.push(`<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="rgba(120,140,170,${.05 + w * .14})" stroke-width="${.5 + w * 1.8}"/>`);
    });
  });

  // 노드
  const nodes = REGIONS.map(reg => {
    const isO = reg.id === origin;
    const d = dom.arr[reg.id];
    let col: string, rad = 10, glow = '';
    if (isO) {
      col = '#f43f5e'; rad = 13;
      glow = `<circle cx="${reg.x}" cy="${reg.y}" r="19" fill="none" stroke="#f43f5e" stroke-width="1.5" opacity=".5"><animate attributeName="r" values="13;23;13" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".6;0;.6" dur="2s" repeatCount="indefinite"/></circle>`;
    } else if (d == null || d < 0 || d > MAX_D) {
      col = '#2a3647';
    } else {
      const k = clamp(d / MAX_D, 0, 1);
      col = `rgb(${244 - k * 60 | 0},${63 + k * 100 | 0},${94 + k * 60 | 0})`;
    }
    let svg = glow;
    svg += `<circle cx="${reg.x}" cy="${reg.y}" r="${rad}" fill="${col}" stroke="#0a0e14" stroke-width="2"/>`;
    svg += `<text x="${reg.x}" y="${reg.y + 4}" fill="#fff" font-size="9" font-weight="700" text-anchor="middle">${reg.nm}</text>`;
    if (!isO && d != null && d >= 0 && d <= MAX_D) {
      svg += `<text x="${reg.x}" y="${reg.y + rad + 10}" fill="${col}" font-size="8.5" font-family="var(--mono)" text-anchor="middle">D+${d}</text>`;
    }
    return svg;
  }).join('');

  // 도착 목록
  const arr = REGIONS
    .map(reg => ({ reg, d: dom.arr[reg.id], isO: reg.id === origin }))
    .filter(a => a.isO || (a.d != null && a.d >= 0 && a.d <= MAX_D))
    .sort((a, b) => {
      if (a.isO) return -1; if (b.isO) return 1;
      return (a.d ?? 999) - (b.d ?? 999);
    });
  const maxD = Math.max(...arr.filter(a => !a.isO).map(a => a.d ?? 0), 1);

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">다지역 도착 예측</div>
      <div className="psub">
        이동량 네트워크 위에서 발원지에서 각 지역으로{' '}
        <em style={{ color: 'var(--violet)', fontStyle: 'normal', fontWeight: 600 }}>병원체가 도착·확산할 시점</em>을
        메타개체군 모델로 역추론.
      </div>
      <div className="card">
        <div className="card-h">
          <span className="lbl">확산 도착 네트워크</span>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>
            {origin} 발원 · {arr.length - 1}개 지역
          </span>
        </div>
        <div className="grid2">
          <svg viewBox="0 0 420 340" style={{ width: '100%', height: 'auto', overflow: 'visible' }}
            dangerouslySetInnerHTML={{ __html: links.join('') + nodes }}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {arr.slice(0, 7).map(a => {
              if (a.isO) return (
                <div key="origin" style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '9px 11px',
                  background: 'rgba(244,63,94,.08)', border: '1px solid var(--accent)',
                  borderRadius: 10,
                }}>
                  <div style={{ width: 3, alignSelf: 'stretch', borderRadius: 3, background: '#f43f5e' }} />
                  <div style={{ flex: 1, fontSize: 12, fontWeight: 600 }}>
                    {a.reg.nm} <small style={{ display: 'block', fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted)', fontWeight: 400, marginTop: 1 }}>유입 관문</small>
                  </div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: '#f43f5e', textAlign: 'right' }}>
                    <b style={{ fontSize: 14, display: 'block' }}>D+0</b>발원
                  </div>
                </div>
              );
              const k = (a.d ?? 0) / maxD;
              const col = `rgb(${244 - k * 60 | 0},${63 + k * 100 | 0},${94 + k * 60 | 0})`;
              return (
                <div key={a.reg.id} style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '9px 11px',
                  background: 'rgba(255,255,255,.02)', border: '1px solid var(--line)',
                  borderRadius: 10,
                }}>
                  <div style={{ width: 3, alignSelf: 'stretch', borderRadius: 3, background: col }} />
                  <div style={{ flex: 1, fontSize: 12, fontWeight: 600 }}>
                    {a.reg.nm} <small style={{ display: 'block', fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted)', fontWeight: 400, marginTop: 1 }}>도착 예측</small>
                  </div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: col, textAlign: 'right' }}>
                    <b style={{ fontSize: 14, display: 'block' }}>D+{a.d}</b>도착
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
