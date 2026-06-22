'use client';
import { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { CIVIC } from '@/lib/algorithms';

const API = 'http://localhost:8000';

interface BacktestEvidence {
  best_lead_days: number;
  best_keyword_group: string;
  benchmark: string;
  case_data_source: string;
  search_data_source: string;
}

export default function Stage1Civic() {
  const { civicOn, toggleCivic } = useStore();
  const active = CIVIC.filter(s => civicOn[s.id]);
  const lead = active.length ? Math.max(...active.map(s => s.lead)) : 0;

  const [evidence, setEvidence] = useState<BacktestEvidence | null>(null);
  const [evidenceErr, setEvidenceErr] = useState(false);
  useEffect(() => {
    fetch(`${API}/api/civic-fusion/backtest-evidence`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setEvidence)
      .catch(() => setEvidenceErr(true));
  }, []);

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">민간 우선 신호망</div>
      <div className="psub">
        코로나의 교훈 — 정부 발표는 너무 늦었다. 검색 신호 1종은{' '}
        <em style={{ color: 'var(--violet)', fontStyle: 'normal', fontWeight: 600 }}>2020년 실제 데이터로 검증</em>됨(아래 박스).
        나머지 4종(하수·OTC·키트·검사소)은 데이터 파트너십 전까지 모델 가정값입니다.
      </div>
      <div className="card">
        {/* 히어로 배너 */}
        <div style={{
          padding: 16, borderRadius: 13,
          background: 'linear-gradient(135deg,rgba(167,139,250,.10),rgba(18,25,37,.5))',
          border: '1px solid var(--line2)',
          display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap',
        }}>
          <div style={{ flex: 1, minWidth: 260, fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 16, lineHeight: 1.3 }}>
            시민·민간 신호 융합 —{' '}
            <b style={{ color: 'var(--violet)' }}>정부 D-0보다 먼저</b>
          </div>
          <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 34, color: 'var(--violet)', textAlign: 'right' }}>
            +{lead}일
            <small style={{ display: 'block', fontSize: 9.5, color: 'var(--muted)', letterSpacing: '.14em', marginTop: 2 }}>정부 대비 선행</small>
          </div>
        </div>

        {/* 실측 검증 근거 */}
        {evidence && (
          <div style={{
            marginTop: 12, padding: '11px 13px', borderRadius: 11,
            background: 'rgba(52,211,153,.07)', border: '1px solid rgba(52,211,153,.3)',
            fontFamily: 'var(--mono)', fontSize: 10.5, lineHeight: 1.7,
          }}>
            <b style={{ color: 'var(--ok)' }}>✅ 실측 검증</b> — &apos;{evidence.best_keyword_group}&apos; 검색 관심이{' '}
            {evidence.benchmark}보다 <b style={{ color: 'var(--ok)' }}>{evidence.best_lead_days}일</b> 먼저 반응 (2020 COVID-19 백테스트)
            <div style={{ color: 'var(--muted2)', fontSize: 9, marginTop: 3 }}>
              검색: {evidence.search_data_source} · 확진자: {evidence.case_data_source}
            </div>
          </div>
        )}
        {evidenceErr && (
          <div style={{ marginTop: 12, padding: '9px 13px', borderRadius: 11, background: 'rgba(255,255,255,.025)', border: '1px solid var(--line)', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}>
            실측 백테스트 데이터를 불러오지 못했습니다 (백엔드 서버 확인 필요) — 아래는 가정 기반 시뮬레이션 값입니다.
          </div>
        )}

        {/* 신호 목록 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 14 }}>
          {CIVIC.map(s => {
            const off = !civicOn[s.id];
            return (
              <div key={s.id}
                onClick={() => toggleCivic(s.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 11,
                  padding: '10px 12px',
                  background: 'rgba(255,255,255,.025)',
                  border: '1px solid var(--line)',
                  borderRadius: 10, cursor: 'pointer',
                  opacity: off ? .35 : 1,
                }}
              >
                <div style={{
                  width: 30, height: 30, borderRadius: 8,
                  background: `${s.col}22`, color: s.col,
                  display: 'grid', placeItems: 'center', fontSize: 15,
                }}>
                  {s.ic}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 700 }}>{s.nm}</div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', marginTop: 1 }}>
                    {s.sub} · 품질 {Math.round(s.q * 100)} · 볼륨 {Math.round(s.v * 100)}
                  </div>
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, textAlign: 'right' }}>
                  <div style={{ fontSize: 16, color: 'var(--violet)' }}>D−{s.lead}</div>
                  <div style={{ fontSize: 8.5, color: 'var(--muted)' }}>선행</div>
                </div>
              </div>
            );
          })}

          {/* 정부 기준선 */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 11,
            padding: '10px 12px',
            background: 'rgba(255,255,255,.025)',
            border: '1px solid rgba(239,68,68,.4)',
            borderRadius: 10, opacity: .7,
          }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8,
              background: 'rgba(239,68,68,.15)', color: '#ef4444',
              display: 'grid', placeItems: 'center', fontSize: 15,
            }}>
              🏛
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12.5, fontWeight: 700 }}>정부 공식 발표</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', marginTop: 1 }}>GOV · 기준선</div>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, textAlign: 'right' }}>
              <div style={{ fontSize: 16, color: '#ef4444' }}>D-0</div>
              <div style={{ fontSize: 8.5, color: 'var(--muted)' }}>기준</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
