'use client';
import { useEffect, useState } from 'react';
import { fetchBiodefenseReadiness, BiodefenseReadiness } from '@/lib/api';
import ClassifiedBadge from './ClassifiedBadge';

// VALHALLA 실측 패널 — 백엔드 대응제 준비태세(biodefense_readiness) 호출·렌더.
// 커버리지·생산주권·단일故障점·비축 물류를 실제 집계로 표시.
export default function ValhallaPanel() {
  const [r, setR] = useState<BiodefenseReadiness | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetchBiodefenseReadiness()
      .then(d => { if (alive) setR(d); })
      .catch(e => { if (alive) setErr(String(e)); });
    return () => { alive = false; };
  }, []);

  return (
    <div className="card" style={{ marginTop: 14 }}>
      <ClassifiedBadge c={r?.classification} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.14em', color: '#34d399' }}>
          VALHALLA · 국가 대응제 준비태세(실측)
        </span>
        {r?.is_illustrative && (
          <span style={{ fontFamily: 'var(--kr)', fontSize: 10, color: 'var(--muted2)',
            border: '1px solid var(--line2)', borderRadius: 5, padding: '2px 7px' }}>예시 데이터</span>
        )}
      </div>

      {err && <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#f43f5e' }}>
        {err.includes('503') ? '인증 필요(API 키 미설정)' : err}
      </div>}

      {r && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 8 }}>
            <Stat label="커버리지" v={`${r.coverage.covered}/${r.threats_assessed}`}
              sub={r.coverage.coverage_rate != null ? `${Math.round(r.coverage.coverage_rate * 100)}%` : '—'} col="#34d399" />
            <Stat label="미커버 위협" v={String(r.coverage.uncovered)}
              sub={r.coverage.uncovered_threats.join(', ') || '없음'} col="#f43f5e" warn={r.coverage.uncovered > 0} />
            <Stat label="생산 주권" v={r.sovereignty.sovereignty_rate != null ? `${Math.round(r.sovereignty.sovereignty_rate * 100)}%` : '—'}
              sub={`수입의존 ${r.sovereignty.import_dependent_covered}`} col="#38bdf8" warn={r.sovereignty.import_dependent_covered > 0} />
            <Stat label="단일故障점" v={String(r.resilience.single_point_count)}
              sub={r.resilience.single_point_of_failure.join(', ') || '없음'} col="#fbbf24" warn={r.resilience.single_point_count > 0} />
          </div>

          {r.logistics.items.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted2)', letterSpacing: '.08em', marginBottom: 6 }}>
                비축 소진 물류
              </div>
              {r.logistics.items.map((it, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
                  padding: '8px 12px', marginTop: 4, borderRadius: 7,
                  background: 'var(--panel2)', border: '1px solid var(--line)',
                }}>
                  <span style={{ fontFamily: 'var(--kr)', fontSize: 12, fontWeight: 700 }}>{it.name}</span>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted)' }}>
                    비축 {it.courses.toLocaleString()}인분
                  </span>
                  {it.coverage_fraction != null && (
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 11,
                      color: it.coverage_fraction < 1 ? '#fb923c' : '#34d399' }}>
                      수요 커버 {Math.round(it.coverage_fraction * 100)}%
                    </span>
                  )}
                  {it.shortfall > 0 && (
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#f43f5e' }}>
                      부족 {it.shortfall.toLocaleString()}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          <div style={{ marginTop: 10, fontFamily: 'var(--kr)', fontSize: 10.5, color: 'var(--muted2)', lineHeight: 1.6 }}>
            {r.disclaimer}
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ label, v, sub, col, warn = false }: { label: string; v: string; sub: string; col: string; warn?: boolean }) {
  return (
    <div style={{
      background: 'var(--panel2)', border: `1px solid ${warn ? col + '66' : 'var(--line)'}`,
      borderRadius: 8, padding: '11px 13px',
    }}>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted2)', letterSpacing: '.04em' }}>{label}</div>
      <div style={{ fontFamily: 'var(--mono)', fontWeight: 800, fontSize: 20, marginTop: 3, color: col }}>{v}</div>
      <div style={{ fontFamily: 'var(--kr)', fontSize: 10.5, color: 'var(--muted2)', marginTop: 3 }}>{sub}</div>
    </div>
  );
}
