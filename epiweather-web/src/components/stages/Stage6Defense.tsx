'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useStore } from '@/lib/store';
import { LEVERS_CONFIG, clamp, currentRt } from '@/lib/algorithms';

const HOSP_CAP = 12000;
const HOSP_FRAC = 0.08;

export default function Stage6Defense() {
  const { def, def0, lev, threat, setLev, savedLives } = useStore();
  const [animDay, setAnimDay] = useState(200);
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    setPlaying(false);
    setAnimDay(200);
  }, []);

  const play = useCallback(() => {
    setAnimDay(0);
    setPlaying(true);
    let d = 0;
    timerRef.current = setInterval(() => {
      d += 4;
      if (d >= 200) { setAnimDay(200); stop(); return; }
      setAnimDay(d);
    }, 55);
  }, [stop]);

  useEffect(() => () => stop(), [stop]);

  if (!def || !def0) return null;

  const rt = currentRt(lev, threat);
  const suppressed = rt < 1;

  // SVG 차트 그리기
  const W = 720, H = 280, padL = 8, padR = 8, padT = 12, padB = 22;
  const days = def.I.length;
  const xFn = (t: number) => padL + t / (days - 1) * (W - padL - padR);
  const maxV = Math.max(def0.peak, ...def.I) * 1.06;
  const yFn = (v: number) => H - padB - (v / maxV) * (H - padT - padB);
  const upTo = Math.min(animDay, days - 1);
  const line = (arr: number[], n: number) =>
    arr.slice(0, n + 1).map((v, i) => `${i ? 'L' : 'M'}${xFn(i).toFixed(1)} ${yFn(v).toFixed(1)}`).join(' ');

  let chartSvg = `<line x1="${padL}" y1="${yFn(0)}" x2="${W - padR}" y2="${yFn(0)}" stroke="rgba(255,255,255,.06)"/>`;
  chartSvg += `<line x1="${padL}" y1="${yFn(HOSP_CAP / HOSP_FRAC)}" x2="${W - padR}" y2="${yFn(HOSP_CAP / HOSP_FRAC)}" stroke="#fbbf24" stroke-width="1.2" stroke-dasharray="2 3" opacity=".7"/><text x="${W - padR}" y="${yFn(HOSP_CAP / HOSP_FRAC) - 4}" fill="#fbbf24" font-size="8.5" font-family="var(--mono)" text-anchor="end">의료 한계</text>`;
  chartSvg += `<path d="${line(def0.I, days - 1)} L${xFn(days - 1)} ${yFn(0)} L${xFn(0)} ${yFn(0)} Z" fill="rgba(239,68,68,.07)"/><path d="${line(def0.I, days - 1)}" fill="none" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="5 4" opacity=".8"/>`;
  chartSvg += `<path d="${line(def.I, upTo)} L${xFn(upTo)} ${yFn(0)} L${xFn(0)} ${yFn(0)} Z" fill="rgba(52,211,153,.12)"/><path d="${line(def.I, upTo)}" fill="none" stroke="#34d399" stroke-width="2.4"/>`;
  if (animDay >= days - 1) {
    chartSvg += `<circle cx="${xFn(def0.pday)}" cy="${yFn(def0.peak)}" r="4" fill="#ef4444"/><text x="${xFn(def0.pday)}" y="${yFn(def0.peak) - 7}" fill="#ef4444" font-size="9" font-family="var(--mono)" text-anchor="middle">무대응 정점</text>`;
  }
  chartSvg += `<line x1="${xFn(upTo)}" y1="${padT}" x2="${xFn(upTo)}" y2="${H - padB}" stroke="rgba(255,255,255,.2)" stroke-dasharray="2 2"/><text x="${xFn(upTo)}" y="${H - 7}" fill="var(--muted)" font-size="9" font-family="var(--mono)" text-anchor="middle">D+${upTo}</text>`;

  const savedPct = def0.deaths > 0 ? Math.round(savedLives / def0.deaths * 100) : 0;

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">방어 시뮬레이션</div>
      <div className="psub">
        개입 6개 레버를 조절하면 SEIR 엔진이 무대응 대비{' '}
        <em style={{ color: 'var(--violet)', fontStyle: 'normal', fontWeight: 600 }}>몇 명을 살리는지</em> 실시간 계산.
      </div>

      <div className="grid2">
        {/* 감염 곡선 */}
        <div className="card">
          <div className="card-h">
            <span className="lbl">감염 곡선</span>
            <button
              onClick={playing ? stop : play}
              style={{
                display: 'flex', alignItems: 'center', gap: 7,
                fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--txt)',
                background: 'rgba(244,63,94,.12)', border: '1px solid var(--accent)',
                borderRadius: 7, padding: '6px 11px', cursor: 'pointer',
              }}
            >
              {playing ? '⏸' : '▶'} 200일 재생
            </button>
          </div>
          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}
            dangerouslySetInnerHTML={{ __html: chartSvg }}
          />
        </div>

        {/* 레버 */}
        <div className="card">
          <div className="card-h"><span className="lbl">방역 개입 레버</span></div>
          {LEVERS_CONFIG.map(L => {
            const v = lev[L.k] ?? 0;
            const disp = L.k === 'vaxsp' ? (v * 1000).toFixed(1) + '‰' : Math.round(v * 100) + '%';
            return (
              <div key={L.k} style={{ marginBottom: 13 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                  <span style={{ fontSize: 12.5, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 7 }}>
                    {L.ic} {L.nm} <small style={{ fontFamily: 'var(--mono)', fontSize: 8.5, color: 'var(--muted2)', fontWeight: 400 }}>{L.sub}</small>
                  </span>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ok)' }}>{disp}</span>
                </div>
                <input type="range" min={0} max={L.max} step={L.max / 100} value={v}
                  onChange={e => setLev(L.k, parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--ok)', cursor: 'pointer' }}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* 성과 */}
      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-h">
          <span className="lbl">방어 성과</span>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>200일</span>
        </div>
        <div className="outcomes">
          <div style={{
            gridColumn: '1/-1', borderRadius: 13, padding: '14px 16px',
            background: 'linear-gradient(135deg,rgba(52,211,153,.14),rgba(18,25,37,.4))',
            border: '1px solid var(--ok)',
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            <span style={{ fontSize: 26 }}>🛡️</span>
            <div>
              <div style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 23, color: 'var(--ok)', lineHeight: 1 }}>
                {savedLives.toLocaleString()}명
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 4, lineHeight: 1.5 }}>
                무대응 대비 구한 생명 (사망 {savedPct}%↓) ·{' '}
                {suppressed ? <b style={{ color: 'var(--ok)' }}>Rt&lt;1 차단</b> : '억제 중'}
              </div>
            </div>
          </div>

          <div className="oc">
            <div className="ok">📉 정점 감염</div>
            <div className="ov" style={{ color: '#34d399' }}>{Math.round(def.peak).toLocaleString()}<small>명</small></div>
            <div className="od">무대응 {Math.round(def0.peak).toLocaleString()}</div>
          </div>
          <div className="oc">
            <div className="ok">⚰️ 누적 사망</div>
            <div className="ov" style={{ color: def.deaths < def0.deaths * 0.3 ? '#34d399' : '#fb923c' }}>
              {Math.round(def.deaths).toLocaleString()}
            </div>
            <div className="od">무대응 {Math.round(def0.deaths).toLocaleString()}</div>
          </div>
          <div className="oc">
            <div className="ok">🏥 병상 초과</div>
            <div className="ov" style={{ color: def.ofd === 0 ? '#34d399' : def.ofd < 20 ? '#fb923c' : '#ef4444' }}>
              {def.ofd}<small>일</small>
            </div>
            <div className="od">무대응 {def0.ofd}일</div>
          </div>
          <div className="oc">
            <div className="ok">📈 실효 Rt</div>
            <div className="ov" style={{ color: rt < 1 ? '#34d399' : rt < 1.5 ? '#fbbf24' : '#ef4444' }}>
              {rt.toFixed(2)}
            </div>
            <div className="od">{rt < 1 ? '차단' : '>1 확대'}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
