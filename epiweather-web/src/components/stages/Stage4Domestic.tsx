'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useStore } from '@/lib/store';
import { REGIONS, riskColor, statusOf } from '@/lib/algorithms';

export default function Stage4Domestic() {
  const { dom, week, reg, setWeek, setReg } = useStore();
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    setPlaying(false);
  }, []);

  const play = useCallback(() => {
    setPlaying(true);
    let w = week >= 4 ? 0 : week;
    setWeek(w);
    timerRef.current = setInterval(() => {
      w++;
      if (w > 4) { setWeek(4); stop(); return; }
      setWeek(w);
    }, 900);
  }, [week, setWeek, stop]);

  useEffect(() => () => stop(), [stop]);

  if (!dom) return null;
  const selReg = REGIONS.find(r => r.id === reg)!;
  const v = dom.riskWeek[reg][week];
  const base = Math.round(8 + selReg.eld * 0.3);

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">국내 확산 예보</div>
      <div className="psub">
        유입 관문(인천)에서 시작된 확산을 전국 지도로.{' '}
        <em style={{ color: 'var(--violet)', fontStyle: 'normal', fontWeight: 600 }}>▶ 재생</em>하면 수도권→전국 파동.
      </div>
      <div className="grid2">
        {/* 지도 */}
        <div className="card">
          <div className="card-h">
            <span className="lbl">전국 위험도</span>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>
              {week === 0 ? '현재' : `+${week}주`}
            </span>
          </div>

          {/* 한국 지도 (그리드 카토그램) */}
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(6,1fr)',
            gap: 6, aspectRatio: '6/7.4',
          }}>
            {REGIONS.map(r => {
              const rv = dom.riskWeek[r.id][week];
              return (
                <div key={r.id}
                  onClick={() => setReg(r.id)}
                  style={{
                    gridColumn: r.c, gridRow: r.r,
                    position: 'relative', borderRadius: 9,
                    border: `1px solid ${r.id === reg ? 'rgba(255,255,255,.8)' : 'rgba(255,255,255,.06)'}`,
                    boxShadow: r.id === reg ? '0 0 0 2px var(--txt) inset' : undefined,
                    display: 'flex', flexDirection: 'column',
                    justifyContent: 'space-between', padding: '6px 7px',
                    cursor: 'pointer',
                    background: riskColor(rv),
                    transition: 'background-color .55s',
                    overflow: 'hidden',
                  }}
                >
                  {r.id === 'IC' && (
                    <span style={{ position: 'absolute', top: 4, left: 5, fontSize: 10 }}>◎</span>
                  )}
                  <span style={{ fontSize: 11, fontWeight: 700, color: '#fff', textShadow: '0 1px 4px rgba(0,0,0,.6)' }}>
                    {r.nm}
                  </span>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 700, color: '#fff', alignSelf: 'flex-end', textShadow: '0 1px 4px rgba(0,0,0,.55)' }}>
                    {rv}
                  </span>
                </div>
              );
            })}
          </div>

          {/* 타임라인 */}
          <div style={{ marginTop: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 11.5 }}>
                {week === 0 ? <><b>현재</b></> : <><b>+{week}주</b></>}
              </div>
              <button
                onClick={playing ? stop : play}
                style={{
                  display: 'flex', alignItems: 'center', gap: 7,
                  fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--txt)',
                  background: 'rgba(244,63,94,.12)', border: '1px solid var(--accent)',
                  borderRadius: 7, padding: '6px 11px', cursor: 'pointer',
                }}
              >
                {playing ? '⏸' : '▶'} 재생
              </button>
            </div>
            <div style={{ position: 'relative', height: 28, display: 'flex', alignItems: 'center' }}>
              <div style={{ position: 'absolute', left: 0, right: 0, height: 3, background: 'var(--line2)', borderRadius: 3 }} />
              <div style={{ position: 'absolute', left: 0, height: 3, width: `${week / 4 * 100}%`, borderRadius: 3, background: 'linear-gradient(90deg,#1d9b8a,#eab308,var(--accent))', transition: 'width .4s' }} />
              {[0, 1, 2, 3, 4].map(t => (
                <div key={t}
                  onClick={() => { stop(); setWeek(t); }}
                  style={{
                    position: 'absolute', top: '50%', left: `${t / 4 * 100}%`,
                    transform: 'translate(-50%,-50%)',
                    display: 'flex', flexDirection: 'column', alignItems: 'center', cursor: 'pointer',
                  }}
                >
                  <div style={{
                    width: 11, height: 11, borderRadius: '50%',
                    background: t === week ? 'var(--accent)' : 'var(--bg2)',
                    border: `2px solid ${t === week ? 'var(--txt)' : 'var(--muted2)'}`,
                  }} />
                  <div style={{
                    fontFamily: 'var(--mono)', fontSize: 8.5, marginTop: 6,
                    color: t === week ? 'var(--txt)' : 'var(--muted)', whiteSpace: 'nowrap',
                  }}>
                    {t === 0 ? '현재' : `+${t}주`}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 지역 상세 */}
        <div className="card">
          <div className="card-h">
            <span className="lbl">지역 추론</span>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>{selReg.nm}</span>
          </div>
          <div className="outcomes">
            <div className="oc">
              <div className="ok">📍 {selReg.nm}</div>
              <div className="ov" style={{ color: riskColor(v) }}>{v}<small style={{ fontSize: 10, fontWeight: 400, color: 'var(--muted)' }}>/100</small></div>
              <div className="od">{statusOf(v)} · 베이스라인 +{v - base}</div>
            </div>
            <div className="oc">
              <div className="ok">🛡 65세+</div>
              <div className="ov">{selReg.eld}<small style={{ fontSize: 10, fontWeight: 400, color: 'var(--muted)' }}>%</small></div>
              <div className="od">취약가중</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
