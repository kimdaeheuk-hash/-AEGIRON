'use client';
import { useEffect } from 'react';
import { useStore } from '@/lib/store';
import { CITIES, THREAT, PRESETS, CIVIC, currentRt } from '@/lib/algorithms';
import Stage0Synthetic from './stages/Stage0Synthetic';
import Stage0PatientZero from './stages/Stage0PatientZero';
import Stage1Civic from './stages/Stage1Civic';
import Stage2Global from './stages/Stage2Global';
import Stage3Domestic from './stages/Stage3Domestic';
import Stage4Network from './stages/Stage4Network';
import Stage5Defense from './stages/Stage5Defense';
import Stage6AI from './stages/Stage6AI';
import Stage8Biodefense from './stages/Stage8Biodefense';

const STAGES = [
  { id: 0, nm: '합성위협 탐지', sub: 'SYNTHETIC',    ic: '🧬' },
  { id: 1, nm: '발원지 추적', sub: 'PATIENT ZERO', ic: '🎯' },
  { id: 2, nm: '민간 신호',   sub: 'CIVIC FIRST',  ic: '🧑‍🤝‍🧑' },
  { id: 3, nm: '글로벌 유입', sub: 'GLOBAL',        ic: '🌐' },
  { id: 4, nm: '국내 확산',   sub: 'DOMESTIC',      ic: '🗺' },
  { id: 5, nm: '도착 예측',   sub: 'NETWORK',       ic: '🕸' },
  { id: 6, nm: '방어 대응',   sub: 'DEFENSE',       ic: '🛡' },
  { id: 7, nm: 'AI 추론',    sub: 'AI POLICY',     ic: '🧠' },
  { id: 8, nm: '전략 비축',  sub: 'BIODEFENSE',    ic: '🦠' },
];

export default function Command() {
  const {
    origin, threat, lev, stage, civicOn,
    pz, glob, savedLives, rt,
    setOrigin, setThreat, setPreset, setStage, recompute,
  } = useStore();

  // 앱 시작 시 초기 계산
  useEffect(() => { recompute(); }, []);

  const civicLead = Math.max(...CIVIC.filter(s => civicOn[s.id]).map(s => s.lead), 0);
  const stageStats: Record<number, string> = {
    0: '스캔',
    1: pz ? (pz.top.prob * 100).toFixed(0) + '%' : '—',
    2: 'D−' + civicLead,
    3: glob ? 'D+' + glob.arrival : 'D+—',
    4: '+4주',
    5: '전국',
    6: savedLives >= 1000 ? (savedLives / 1000).toFixed(0) + 'k' : savedLives.toLocaleString(),
    7: '9단계',
    8: '시뮬',
  };
  const rtSafe = currentRt(lev, threat);
  const estateText = rtSafe < 1 ? '✓ 방어 우세' : rtSafe < 1.5 ? '⚠ 억제' : '⚠ 확산 위험';
  const estateCol = rtSafe < 1 ? 'var(--ok)' : rtSafe < 1.5 ? '#fbbf24' : '#ef4444';
  const city = CITIES.find(c => c.id === origin)!;

  const stageComponents = [
    <Stage0Synthetic key={0} />,
    <Stage0PatientZero key={1} />,
    <Stage1Civic key={2} />,
    <Stage2Global key={3} />,
    <Stage3Domestic key={4} />,
    <Stage4Network key={5} />,
    <Stage5Defense key={6} />,
    <Stage6AI key={7} />,
    <Stage8Biodefense key={8} />,
  ];

  return (
    <div style={{ position: 'relative', zIndex: 1, maxWidth: 1320, margin: '0 auto', padding: 'clamp(14px,2.4vw,26px)' }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', borderBottom: '1px solid var(--line)', paddingBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            width: 42, height: 42, borderRadius: 11,
            background: 'radial-gradient(circle at 30% 30%,#1a2433,#0d1320)',
            border: '1px solid var(--line2)', display: 'grid', placeItems: 'center',
            position: 'relative', overflow: 'hidden',
          }}>
            <div style={{
              position: 'absolute', inset: 0,
              background: 'conic-gradient(from 0deg,transparent 0deg,var(--accent) 30deg,transparent 60deg)',
              animation: 'radar 3s linear infinite', opacity: .55,
            }} />
            <svg viewBox="0 0 24 24" fill="none" stroke="#f43f5e" strokeWidth="1.8" style={{ width: 22, height: 22, position: 'relative', zIndex: 2 }}>
              <circle cx="12" cy="12" r="2" />
              <circle cx="12" cy="12" r="6" opacity=".5" />
              <circle cx="12" cy="12" r="10" opacity=".25" />
            </svg>
          </div>
          <div>
            <h1 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(20px,2.6vw,26px)', letterSpacing: '-.02em', lineHeight: 1 }}>
              역병예보 <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--accent)', verticalAlign: 'middle' }}>COMMAND</span>
            </h1>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', letterSpacing: '.18em', marginTop: 5 }}>
              9단계 통합 관제센터 · 합성위협 탐지 → 생명 살리기까지
            </div>
          </div>
        </div>
        <div style={{ textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 10 }}>
          <div style={{ fontSize: 13, color: estateCol }}>{estateText}</div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 9, letterSpacing: '.14em', marginTop: 4, color: 'var(--ok)' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--ok)', boxShadow: '0 0 8px var(--ok)', animation: 'blink 1.6s infinite' }} />
            9단계 동시 추론
          </div>
        </div>
      </div>

      {/* 시나리오 바 */}
      <div style={{
        display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end',
        margin: '16px 0 18px', padding: '14px 16px',
        background: 'var(--panel)', border: '1px solid var(--line)',
        borderRadius: 14, backdropFilter: 'blur(14px)',
      }}>
        {/* 발원지 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.16em', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 6 }}>해외 발원지</span>
          <select
            value={origin}
            onChange={e => setOrigin(e.target.value)}
            style={{ fontFamily: 'var(--kr)', fontSize: 12.5, color: 'var(--txt)', background: 'var(--bg2)', border: '1px solid var(--line)', borderRadius: 9, padding: '8px 11px', cursor: 'pointer' }}
          >
            {CITIES.map(c => <option key={c.id} value={c.id}>{c.nm}</option>)}
          </select>
        </div>

        {/* 위협 강도 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.16em', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 6 }}>위협 강도</span>
          <div style={{ display: 'flex', background: 'var(--bg2)', border: '1px solid var(--line)', borderRadius: 9, overflow: 'hidden' }}>
            {(['flu', 'novel', 'severe'] as const).map(k => (
              <button key={k}
                onClick={() => setThreat(k)}
                style={{
                  fontFamily: 'var(--kr)', fontSize: 12, fontWeight: 600,
                  color: threat === k ? 'var(--txt)' : 'var(--muted)',
                  background: threat === k ? 'rgba(244,63,94,.16)' : 'none',
                  border: 'none', padding: '8px 12px', cursor: 'pointer',
                  transition: '.18s', whiteSpace: 'nowrap',
                }}
              >
                {k === 'flu' ? '계절 R₀2.2' : k === 'novel' ? '신종 R₀2.8' : '고위험 R₀3.4'}
              </button>
            ))}
          </div>
        </div>

        {/* 대응 수준 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.16em', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 6 }}>대응 수준</span>
          <div style={{ display: 'flex', gap: 5 }}>
            {(['none', 'mild', 'strong'] as const).map(p => {
              const isActive = JSON.stringify(lev) === JSON.stringify(PRESETS[p]);
              return (
                <button key={p}
                  onClick={() => setPreset(p)}
                  style={{
                    fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--txt)',
                    background: isActive ? 'rgba(52,211,153,.16)' : 'rgba(255,255,255,.05)',
                    border: `1px solid ${isActive ? 'var(--ok)' : 'var(--line2)'}`,
                    borderRadius: 9, padding: '9px 12px', cursor: 'pointer',
                  }}
                >
                  {p === 'none' ? '무대응' : p === 'mild' ? '중간' : '강력'}
                </button>
              );
            })}
          </div>
        </div>

        <div style={{ marginLeft: 'auto', textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted)' }}>
          <b style={{ color: 'var(--ok)', fontSize: 14, display: 'block' }}>{savedLives.toLocaleString()}명</b>
          구한 생명
        </div>
      </div>

      {/* 메인 레이아웃 */}
      <div className="shell">
        {/* 사이드바 */}
        <div className="sidenav" style={{ display: 'flex', flexDirection: 'column', gap: 6, position: 'sticky', top: 14, alignSelf: 'start', maxHeight: 'calc(100vh - 30px)', overflowY: 'auto', paddingRight: 4 }}>
          {STAGES.map(s => (
            <button key={s.id}
              onClick={() => setStage(s.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 11,
                padding: '12px 13px',
                background: s.id === stage ? 'linear-gradient(135deg,rgba(244,63,94,.14),rgba(14,22,35,.6))' : 'var(--panel)',
                border: `1px solid ${s.id === stage ? 'var(--accent)' : 'var(--line)'}`,
                borderRadius: 12, cursor: 'pointer', textAlign: 'left',
                width: '100%', color: s.id === stage ? 'var(--txt)' : 'var(--muted)',
                transition: '.22s', position: 'relative',
              }}
            >
              <div style={{
                position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)',
                width: 3, height: s.id === stage ? '60%' : 0,
                background: 'var(--accent)', borderRadius: '0 2px 2px 0', transition: '.25s',
              }} />
              <div style={{
                width: 28, height: 28, borderRadius: 8,
                background: s.id === stage ? 'var(--accent)' : 'var(--bg2)',
                border: `1px solid ${s.id === stage ? 'var(--accent)' : 'var(--line2)'}`,
                display: 'grid', placeItems: 'center',
                fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 12,
                color: s.id === stage ? '#fff' : 'var(--muted)', flexShrink: 0,
              }}>
                {s.id}
              </div>
              <div>
                <div style={{ fontFamily: 'var(--disp)', fontWeight: 700, fontSize: 13, color: 'var(--txt)', lineHeight: 1.15 }}>
                  {s.ic} {s.nm}
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 8.5, color: 'var(--muted)', marginTop: 2, letterSpacing: '.06em' }}>{s.sub}</div>
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, marginLeft: 'auto', flexShrink: 0, textAlign: 'right', whiteSpace: 'nowrap' }}>
                <b style={{ display: 'block', fontSize: 12, color: 'var(--ok)' }}>{stageStats[s.id]}</b>
                {s.id === 1 ? '확률' : s.id === 2 ? '선행' : s.id === 3 ? '유입' : s.id === 6 ? '살림' : ''}
              </div>
            </button>
          ))}

          <div style={{ marginTop: 6, padding: 12, background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 12, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)', lineHeight: 1.6 }}>
            <b style={{ color: 'var(--ok)' }}>통합 시나리오</b><br />
            {city.nm}발 {THREAT[threat].nm}<br />
            구한 생명 <b style={{ color: 'var(--ok)' }}>{savedLives.toLocaleString()}명</b>
          </div>
        </div>

        {/* 컨텐츠 */}
        <div style={{ minWidth: 0 }}>
          {stageComponents[stage]}
        </div>
      </div>

      <style>{`
        .ptitle { font-family: var(--disp); font-weight: 800; font-size: clamp(18px,2.3vw,24px); letter-spacing: -.02em; line-height: 1.15; margin-bottom: 4px; }
        .psub { font-family: var(--mono); font-size: 11px; color: var(--muted); letter-spacing: .04em; margin-bottom: 18px; line-height: 1.6; }
        .card { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: clamp(14px,2vw,20px); backdrop-filter: blur(14px); }
        .card + .card { margin-top: 14px; }
        .card-h { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 10px; flex-wrap: wrap; }
        .lbl { font-family: var(--mono); font-size: 10px; letter-spacing: .18em; color: var(--muted); text-transform: uppercase; }
        .grid2 { display: grid; grid-template-columns: 1.4fr 1fr; gap: 14px; }
        .shell { display: grid; grid-template-columns: 240px 1fr; gap: 18px; }
        @media(max-width:760px) {
          .shell { grid-template-columns: 1fr; }
          .sidenav { position: static !important; max-height: none !important; overflow-y: visible !important; }
        }
        .oc { border-radius: 12px; padding: 11px; border: 1px solid var(--line); background: rgba(255,255,255,.025); }
        .ok { font-size: 10.5px; color: var(--muted); display: flex; align-items: center; gap: 5px; }
        .ov { font-family: var(--mono); font-weight: 700; font-size: 19px; margin-top: 5px; }
        .od { font-family: var(--mono); font-size: 9px; margin-top: 2px; color: var(--muted2); }
        .outcomes { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 4px; }
        @media(max-width:760px) { .grid2 { grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
}
