'use client';
import { useState } from 'react';
import ValhallaPanel from './ValhallaPanel';

type Strategy = 'stockpile' | 'platform' | 'hybrid';

const BASE_EFF = 0.85;
const SUSC = 0.6;
const MATCHED_EFF = 0.92;

function variantEscape(days: number, rate: number) {
  const months = days / 30;
  return 1 - Math.exp(-rate * months);
}
function stockpileEff(days: number, mutRate: number) {
  return BASE_EFF * (1 - SUSC * variantEscape(days, mutRate));
}
function platformEff(days: number, platDays: number) {
  return days >= platDays ? MATCHED_EFF : 0;
}
function hybridEff(days: number, mutRate: number, platDays: number) {
  return Math.max(stockpileEff(days, mutRate), platformEff(days, platDays));
}
function effOf(strat: Strategy, days: number, mutRate: number, platDays: number) {
  return strat === 'stockpile' ? stockpileEff(days, mutRate)
    : strat === 'platform' ? platformEff(days, platDays)
    : hybridEff(days, mutRate, platDays);
}
function avgEff(strat: Strategy, mutRate: number, platDays: number, horizon: number) {
  let s = 0, n = 0;
  for (let d = 0; d < horizon; d += 5) { s += effOf(strat, d, mutRate, platDays); n++; }
  return s / n;
}

function StratChart({ mutRate, platDays, horizon, strategy }: { mutRate: number; platDays: number; horizon: number; strategy: Strategy }) {
  const W = 700, H = 280, padL = 36, padR = 12, padT = 14, padB = 26;
  const x = (d: number) => padL + (d / horizon) * (W - padL - padR);
  const y = (e: number) => H - padB - e * (H - padT - padB);

  function curve(strat: Strategy, col: string, width: number, dash: boolean) {
    let p = '';
    for (let d = 0; d <= horizon; d += 5) p += (d === 0 ? 'M' : 'L') + x(d).toFixed(1) + ' ' + y(effOf(strat, d, mutRate, platDays)).toFixed(1) + ' ';
    return <path d={p} fill="none" stroke={col} strokeWidth={width} strokeDasharray={dash ? '4 3' : undefined} />;
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}>
      {[0, 0.25, 0.5, 0.75, 1.0].map((e, i) => (
        <g key={i}>
          <line x1={padL} y1={y(e)} x2={W - padR} y2={y(e)} stroke="rgba(255,255,255,.05)" />
          <text x={padL - 6} y={y(e) + 3} fill="var(--muted2)" fontSize={9} fontFamily="var(--mono)" textAnchor="end">{(e * 100).toFixed(0)}%</text>
        </g>
      ))}
      <line x1={x(platDays)} y1={padT} x2={x(platDays)} y2={H - padB} stroke="rgba(118,185,0,.4)" strokeDasharray="3 3" />
      <text x={x(platDays)} y={padT + 10} fill="#76b900" fontSize={9} fontFamily="var(--mono)" textAnchor="middle">플랫폼 준비 D+{platDays}</text>
      {curve('stockpile', '#eab308', strategy === 'stockpile' ? 3 : 1.5, strategy !== 'stockpile')}
      {curve('platform', '#38bdf8', strategy === 'platform' ? 3 : 1.5, strategy !== 'platform')}
      {curve('hybrid', '#76b900', strategy === 'hybrid' ? 3.2 : 1.5, strategy !== 'hybrid')}
      {[0, Math.round(horizon / 3), Math.round(horizon * 2 / 3), horizon].map((d, i) => (
        <text key={i} x={x(d)} y={H - 8} fill="var(--muted2)" fontSize={9} fontFamily="var(--mono)" textAnchor="middle">D+{d}</text>
      ))}
    </svg>
  );
}

function VariantChart({ mutRate, horizon }: { mutRate: number; horizon: number }) {
  const W = 700, H = 160, padL = 36, padR = 12, padT = 12, padB = 24;
  const x = (d: number) => padL + (d / horizon) * (W - padL - padR);
  const y = (e: number) => H - padB - e * (H - padT - padB);
  let p = '';
  for (let d = 0; d <= horizon; d += 5) p += (d === 0 ? 'M' : 'L') + x(d).toFixed(1) + ' ' + y(variantEscape(d, mutRate)).toFixed(1) + ' ';
  const finalEscape = variantEscape(horizon, mutRate);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      {[0, 0.5, 1.0].map((e, i) => (
        <g key={i}>
          <line x1={padL} y1={y(e)} x2={W - padR} y2={y(e)} stroke="rgba(255,255,255,.05)" />
          <text x={padL - 6} y={y(e) + 3} fill="var(--muted2)" fontSize={9} fontFamily="var(--mono)" textAnchor="end">{(e * 100).toFixed(0)}%</text>
        </g>
      ))}
      <path d={p} fill="none" stroke="#f43f5e" strokeWidth={2.4} />
      <path d={`${p} L${x(horizon)} ${y(0)} L${x(0)} ${y(0)} Z`} fill="rgba(244,63,94,.08)" />
      {[0, Math.round(horizon / 3), Math.round(horizon * 2 / 3), horizon].map((d, i) => (
        <text key={i} x={x(d)} y={H - 7} fill="var(--muted2)" fontSize={9} fontFamily="var(--mono)" textAnchor="middle">D+{d}</text>
      ))}
      <text x={W - padR} y={y(finalEscape) - 6} fill="#f43f5e" fontSize={10} fontFamily="var(--mono)" textAnchor="end">항원 회피 {(finalEscape * 100).toFixed(0)}%</text>
    </svg>
  );
}

export default function Stage8Biodefense() {
  const [mutRate, setMutRate] = useState(0.28);
  const [platDays, setPlatDays] = useState(100);
  const [horizon, setHorizon] = useState(365);
  const [strategy, setStrategy] = useState<Strategy>('hybrid');

  const strats: { id: Strategy; nm: string; ic: string; d: string; col: string }[] = [
    { id: 'stockpile', nm: '순수 비축', ic: '📦', d: '즉시 가용, 변이로 약화', col: '#eab308' },
    { id: 'platform', nm: '플랫폼만', ic: '🏭', d: '초기 공백, 항상 맞춤', col: '#38bdf8' },
    { id: 'hybrid', nm: '혼합 전략', ic: '🛡', d: '비축+플랫폼, 가장 견고', col: '#76b900' },
  ];

  const escape = variantEscape(horizon, mutRate);
  const platReady = Math.max(0, Math.min(1, 1 - (platDays - 60) / 240));
  const hybridAvg = avgEff('hybrid', mutRate, platDays, horizon);
  const sovereignty = 0.55;

  const pillars = [
    { ic: '🧬', nm: '변이 예측', v: (escape * 100).toFixed(0) + '%', d: '1년 항원 회피율', bar: escape, col: '#f43f5e' },
    { ic: '🏭', nm: '플랫폼 준비', v: 'D+' + platDays, d: '맞춤 대응 소요', bar: platReady, col: '#76b900' },
    { ic: '🛡', nm: '방어 견고성', v: (hybridAvg * 100).toFixed(0) + '%', d: '혼합전략 효과', bar: hybridAvg, col: '#34d399' },
    { ic: '🇰🇷', nm: '생산 주권', v: (sovereignty * 100).toFixed(0) + '%', d: '국내 자립도', bar: sovereignty, col: '#eab308' },
  ];

  const checkDay = Math.round(horizon * 0.5);
  const checkEscape = variantEscape(checkDay, mutRate);
  const matching = [
    { ic: '💉', nm: '기존 비축 백신', sub: 'STOCKPILED VACCINE', susc: 0.6, platform: false },
    { ic: '💉', nm: '광범위 백신', sub: 'BROAD-SPECTRUM', susc: 0.25, platform: false },
    { ic: '💊', nm: '기존 치료제', sub: 'EXISTING ANTIVIRAL', susc: 0.45, platform: false },
    { ic: '🏭', nm: '플랫폼 맞춤 백신', sub: 'PLATFORM-MATCHED', susc: 0.05, platform: true },
  ].map(it => {
    const eff = it.platform ? (checkDay >= platDays ? MATCHED_EFF : 0) : BASE_EFF * (1 - it.susc * checkEscape);
    const col = eff >= 0.7 ? '#34d399' : eff >= 0.5 ? '#eab308' : eff >= 0.3 ? '#f97316' : '#ef4444';
    return { ...it, eff, col };
  });

  const sov = [
    { nm: 'mRNA 백신 플랫폼', sub: '국내 생산 가능', level: '국내자립', col: '#34d399' },
    { nm: '원료의약품(API)', sub: '대부분 수입', level: '수입의존', col: '#ef4444' },
    { nm: '진단키트', sub: '국내 생산 강점', level: '국내자립', col: '#34d399' },
    { nm: '필러·바이알(충전)', sub: '일부 수입', level: '부분의존', col: '#f97316' },
    { nm: '인공호흡기', sub: '수입 의존', level: '수입의존', col: '#ef4444' },
  ];

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">바이오 방어 설계 엔진</div>
      <div className="psub">
        비축만으로는 부족하다. <em style={{ color: 'var(--violet)', fontStyle: 'normal', fontWeight: 600 }}>병원체는 진화한다.</em>{' '}
        변이를 예측하고 비축·플랫폼을 최적 혼합해 100일 안에 맞춤 대응하는 능력.
      </div>

      {/* VALHALLA 실측 준비태세 — 백엔드 biodefense_readiness 실집계 */}
      <ValhallaPanel />

      {/* 컨트롤 */}
      <div className="card" style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.1em', color: 'var(--muted)' }}>위협 변이 속도</span>
          <div style={{ display: 'flex', background: 'var(--bg2)', border: '1px solid var(--line)', borderRadius: 9, overflow: 'hidden' }}>
            {[{ v: 0.15, nm: '느린 변이' }, { v: 0.28, nm: '중간' }, { v: 0.42, nm: '빠른 변이(코로나급)' }].map(m => (
              <button key={m.v} onClick={() => setMutRate(m.v)}
                style={{ fontFamily: 'var(--kr)', fontSize: 12, fontWeight: 600, color: mutRate === m.v ? 'var(--txt)' : 'var(--muted)', background: mutRate === m.v ? 'rgba(118,185,0,.16)' : 'none', border: 'none', padding: '8px 12px', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                {m.nm}
              </button>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.1em', color: 'var(--muted)' }}>플랫폼 준비태세 (대응 소요일)</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <input type="range" min={60} max={300} step={10} value={platDays} onChange={e => setPlatDays(+e.target.value)} style={{ width: 150, accentColor: '#76b900', cursor: 'pointer' }} />
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#76b900', minWidth: 44, textAlign: 'right' }}>{platDays}일</span>
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.1em', color: 'var(--muted)' }}>분석 기간</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <input type="range" min={180} max={730} step={30} value={horizon} onChange={e => setHorizon(+e.target.value)} style={{ width: 150, accentColor: '#76b900', cursor: 'pointer' }} />
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#76b900', minWidth: 44, textAlign: 'right' }}>{horizon}일</span>
          </div>
        </div>
      </div>

      <div className="grid2" style={{ marginTop: 14 }}>
        {/* 좌: 전략 차트 + 변이 차트 */}
        <div>
          <div className="card">
            <div className="card-h">
              <span className="lbl">전략별 방어 효과 · 시간축 시뮬레이션</span>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>혼합 1년평균 {(avgEff('hybrid', mutRate, platDays, horizon) * 100).toFixed(0)}%</span>
            </div>
            <StratChart mutRate={mutRate} platDays={platDays} horizon={horizon} strategy={strategy} />
            <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 10, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)' }}>
              <span>━ <span style={{ color: '#eab308' }}>순수 비축</span> (진화에 취약)</span>
              <span>━ <span style={{ color: '#38bdf8' }}>플랫폼만</span> (초기 공백)</span>
              <span>━ <span style={{ color: '#76b900' }}>혼합 전략</span> (최적)</span>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', lineHeight: 1.6, marginTop: 10 }}>
              비축 대응제는 병원체 변이로 효과가 감소하고, 플랫폼은 준비기간 후 맞춤 대응합니다.{' '}
              <b style={{ color: '#76b900' }}>둘을 혼합하면 초기 비축으로 버티고 플랫폼으로 장기 대응</b> — CEPI 100일 미션의 핵심.
            </div>
          </div>

          <div className="card">
            <div className="card-h"><span className="lbl">변이 회피 예측 · 항원 드리프트</span><span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)' }}>BioNeMo 연동 지점</span></div>
            <VariantChart mutRate={mutRate} horizon={horizon} />
            <div style={{ marginTop: 12, borderRadius: 12, padding: '14px 16px', background: 'linear-gradient(135deg,rgba(118,185,0,.08),rgba(14,22,35,.4))', border: '1px solid rgba(118,185,0,.3)' }}>
              <div style={{ display: 'flex', gap: 10 }}>
                <span style={{ fontSize: 20 }}>🧬</span>
                <div>
                  <b style={{ fontFamily: 'var(--disp)', fontSize: 13, color: '#76b900' }}>여기가 엔비디아 BioNeMo와 만나는 지점</b>
                  <p style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.6, marginTop: 5 }}>
                    지금은 결정론적 수식(위 항원 회피 곡선)이지만, 실제 운영 시 BioNeMo NIM 4단계 파이프라인으로 교체합니다 — 젠슨 황이
                    "디지털 바이올로지"를 반도체·컴퓨팅에 버금가는 다음 혁명으로 꼽는 지점이 바로 이 계산 파이프라인입니다.
                  </p>
                </div>
              </div>
              <ol style={{ margin: '10px 0 0', paddingLeft: 20, fontSize: 10.5, color: 'var(--muted)', lineHeight: 1.9 }}>
                <li>
                  <b style={{ color: 'var(--txt)' }}>Evo2</b>(유전체 파운데이션 모델)로 유전체의 자연스러움 이탈·국소 이상 탐지
                  <b style={{ color: '#76b900' }}> — 세균 위협(탄저·페스트·야토병) 연동 완료</b>
                </li>
                <li><b style={{ color: 'var(--txt)' }}>AlphaFold2-Multimer / OpenFold2</b> NIM으로 변이체 항원 단백질의 3D 구조 재계산</li>
                <li>비축 항체·백신은 구조 기반 결합력 재평가, 소분자 치료제는 <b style={{ color: 'var(--txt)' }}>DiffDock</b>으로 결합 도킹 재시뮬레이션 → 중화 여부 판정</li>
                <li>중화 실패 예측 시 <b style={{ color: 'var(--txt)' }}>RFDiffusion·ProteinMPNN</b>으로 차세대 대응제 후보 설계까지 자동 제안</li>
              </ol>
              <div style={{ marginTop: 10, borderRadius: 8, padding: '10px 12px', background: 'rgba(244,63,94,.07)', border: '1px solid rgba(244,63,94,.28)' }}>
                <b style={{ fontFamily: 'var(--disp)', fontSize: 11, color: '#f43f5e' }}>실측으로 확인한 적용범위 한계</b>
                <p style={{ fontSize: 10, color: 'var(--muted)', lineHeight: 1.65, marginTop: 4 }}>
                  Evo2는 <b style={{ color: 'var(--txt)' }}>진핵숙주 감염 바이러스를 학습에서 제외</b>했습니다(Arc의 바이오안보 조치).
                  실제로 NIM에 자연서열을 넣어 측정한 결과, 세균·진핵·파지는 87~100%인데 코로나·독감·에볼라는 25~33%로
                  <b style={{ color: 'var(--txt)' }}> 자연서열조차 판정이 안 됩니다</b>. 따라서 1단계는 바이러스 위협에 적용하지 않고,
                  세균 위협에만 적용합니다 — 위 곡선은 여전히 결정론적 근사식입니다.
                </p>
                <p style={{ fontSize: 10, color: 'var(--muted)', lineHeight: 1.65, marginTop: 6 }}>
                  &quot;바이러스끼리 상대비교하면 되지 않나&quot;도 성공기준을 미리 정해놓고 검증했고, 실패했습니다 —
                  자연 vs 조성동일 셔플 차이 <b style={{ color: 'var(--txt)' }}>+3.2%</b>(기준 15%p),
                  뎅기는 셔플이 오히려 높았고 키메라 접합부도 부호가 반대였습니다.
                  자연 바이러스 평균 33.3%는 <b style={{ color: 'var(--txt)' }}>무작위로 찍는 25%</b>보다 8.3%p 위에 불과합니다.
                </p>
                <p style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)', lineHeight: 1.6, marginTop: 6 }}>
                  측정 2026-07-30~31 · evo2-40b NIM · NCBI 레퍼런스 자연서열 4kb ·
                  람다파지 100% / 인간 mtDNA 91.7% / 효모 90.3% / 대장균 87.5% ·
                  SARS-CoV-2 33.3% / 인플루엔자A 31.9% / 에볼라 25.0% ·
                  재현: scripts/validate_evo2_applicability.py
                </p>
              </div>
              <p style={{ fontSize: 9.5, color: 'var(--muted2)', marginTop: 8, lineHeight: 1.5 }}>
                전부 NVIDIA BioNeMo 플랫폼에 실제 배포된 NIM 마이크로서비스(2025~2026 기준) — 지어낸 파이프라인이 아니라
                실제 존재하는 도구를 연결하는 설계도입니다. 2~4단계는 미연동(Phase 2), 연동 전까지는 위 결정론적 근사식으로 대체.
              </p>
            </div>
          </div>
        </div>

        {/* 우: 전략 선택 + 4대 기둥 */}
        <div>
          <div className="card">
            <div className="card-h"><span className="lbl">전략 선택</span></div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
              {strats.map(s => {
                const avg = avgEff(s.id, mutRate, platDays, horizon);
                const on = strategy === s.id;
                return (
                  <div key={s.id} onClick={() => setStrategy(s.id)}
                    style={{ padding: '12px 14px', borderRadius: 12, background: on ? 'linear-gradient(135deg,rgba(118,185,0,.10),rgba(255,255,255,.02))' : 'rgba(255,255,255,.025)', border: `1px solid ${on ? '#76b900' : 'var(--line)'}`, cursor: 'pointer' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontFamily: 'var(--disp)', fontWeight: 700, fontSize: 14, display: 'flex', alignItems: 'center', gap: 8 }}>{s.ic} {s.nm}</div>
                      <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 18, color: s.col }}>{(avg * 100).toFixed(0)}%</div>
                    </div>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted)', marginTop: 5 }}>{s.d} · 1년 평균 방어효과</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="card">
            <div className="card-h"><span className="lbl">국가 바이오 안보 4대 기둥</span></div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 10 }}>
              {pillars.map((p, i) => (
                <div key={i} className="oc">
                  <div style={{ fontSize: 18 }}>{p.ic}</div>
                  <div style={{ fontSize: 12, fontWeight: 700, marginTop: 5 }}>{p.nm}</div>
                  <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 16, color: p.col, marginTop: 5 }}>{p.v}</div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 8.5, color: 'var(--muted2)', marginTop: 3 }}>{p.d}</div>
                  <div style={{ marginTop: 6, height: 5, background: 'rgba(255,255,255,.06)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${p.bar * 100}%`, height: '100%', background: p.col }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid2" style={{ marginTop: 14 }}>
        <div className="card">
          <div className="card-h"><span className="lbl">대응제-병원체 매칭 · 변이 시점별 유효성</span><span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>D+{checkDay} 시점 평가</span></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {matching.map((it, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '10px 12px', background: 'rgba(255,255,255,.025)', border: '1px solid var(--line)', borderRadius: 10 }}>
                <span style={{ fontSize: 18 }}>{it.ic}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 700 }}>{it.nm}</div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', marginTop: 2 }}>{it.sub} · 회피민감도 {it.susc}</div>
                  <div style={{ marginTop: 5, height: 5, background: 'rgba(255,255,255,.06)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${Math.max(2, it.eff * 100)}%`, height: '100%', background: it.col }} />
                  </div>
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 700, color: it.col, width: 48, textAlign: 'right' }}>{(it.eff * 100).toFixed(0)}%</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-h"><span className="lbl">생산 주권 · 공급망 자립도</span></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sov.map((it, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 11px', background: 'rgba(255,255,255,.025)', border: '1px solid var(--line)', borderRadius: 9 }}>
                <div style={{ flex: 1, fontSize: 12 }}>{it.nm}<small style={{ display: 'block', fontFamily: 'var(--mono)', fontSize: 8.5, color: 'var(--muted2)', marginTop: 1 }}>{it.sub}</small></div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, fontWeight: 700, padding: '3px 8px', borderRadius: 5, background: `${it.col}22`, color: it.col }}>{it.level}</div>
              </div>
            ))}
          </div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted2)', marginTop: 10, lineHeight: 1.6 }}>
            비축은 reactive, 생산능력은 proactive. 긴급 시 직접 만들 수 있는가가 진짜 안보. 빨강=수입의존(취약), 초록=국내자립.
          </div>
        </div>
      </div>

      <div style={{ marginTop: 16, fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)', lineHeight: 1.7, borderTop: '1px solid var(--line)', paddingTop: 12 }}>
        <b style={{ color: 'var(--muted)' }}>※ 8단계 — 비축에서 바이오 방어 설계로</b>: ①변이 회피 예측 ②비축 vs 플랫폼 혼합 최적화 ③대응제-병원체 분자 매칭 ④생산 주권. 모든 수치는 결정론적 모델로 직접 계산하며, 실제 운영 시 BioNeMo NIM(Evo2·AlphaFold2-Multimer·DiffDock·RFDiffusion 등)·유전체 데이터·CEPI 표준을 연동합니다. Evo2는 세균 위협에 한해 연동 완료 — 진핵숙주 감염 바이러스는 모델 학습 제외로 판정 불가(실측 근거는 위 카드).
      </div>
    </div>
  );
}
