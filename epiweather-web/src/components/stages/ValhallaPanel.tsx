'use client';
import { useEffect, useState, type CSSProperties } from 'react';
import {
  fetchBiodefenseReadiness, BiodefenseReadiness,
  fetchStockpile, createStockpileItem, deleteStockpileItem, CountermeasureItem,
} from '@/lib/api';
import ClassifiedBadge from './ClassifiedBadge';

// VALHALLA 실측 패널 — 백엔드 대응제 준비태세(biodefense_readiness) 호출·렌더.
// 커버리지·생산주권·단일故障점·비축 물류를 실제 집계로 표시.
// 실제 비축 항목을 등록해두면(아래 폼) 예시 데이터 대신 그 데이터로 계산됨.
export default function ValhallaPanel() {
  const [r, setR] = useState<BiodefenseReadiness | null>(null);
  const [stockpile, setStockpile] = useState<CountermeasureItem[]>([]);
  const [err, setErr] = useState<string | null>(null);

  async function reload() {
    try {
      const [readiness, items] = await Promise.all([fetchBiodefenseReadiness(), fetchStockpile()]);
      setR(readiness); setStockpile(items);
    } catch (e) { setErr(String(e)); }
  }

  useEffect(() => { reload(); }, []);

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

      {r?.note && (
        <div style={{ fontFamily: 'var(--kr)', fontSize: 10.5, color: 'var(--muted2)', marginBottom: 8 }}>
          ⓘ {r.note}
        </div>
      )}

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

          {(r.coverage.severity_weighted_rate != null || r.sovereignty.severity_weighted_sovereignty_rate != null) && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 8, marginTop: 8 }}>
              <Stat label="심각도 가중 커버리지" v={r.coverage.severity_weighted_rate != null ? `${Math.round(r.coverage.severity_weighted_rate * 100)}%` : '—'}
                sub="위협별 severity로 가중" col="#a78bfa" />
              <Stat label="심각도 가중 생산주권" v={r.sovereignty.severity_weighted_sovereignty_rate != null ? `${Math.round(r.sovereignty.severity_weighted_sovereignty_rate * 100)}%` : '—'}
                sub="커버된 위협 중 국산 비중" col="#f472b6" />
            </div>
          )}

          {!!r.coverage.priority_uncovered_threats?.length && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted2)', letterSpacing: '.08em', marginBottom: 6 }}>
                우선순위 미커버 위협(심각도순)
              </div>
              {r.coverage.priority_uncovered_threats.map((t, i) => (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between', padding: '6px 10px', marginTop: 4,
                  borderRadius: 7, background: 'rgba(244,63,94,.06)', border: '1px solid rgba(244,63,94,.2)',
                }}>
                  <span style={{ fontFamily: 'var(--kr)', fontSize: 12, fontWeight: 700 }}>{t.pathogen}</span>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted)' }}>
                    severity {t.severity ?? '—'}
                  </span>
                </div>
              ))}
            </div>
          )}

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

          <InternationalBenchmark r={r} />

          <div style={{ marginTop: 10, fontFamily: 'var(--kr)', fontSize: 10.5, color: 'var(--muted2)', lineHeight: 1.6 }}>
            {r.disclaimer}
          </div>
        </>
      )}

      <StockpileManager items={stockpile} onChanged={reload} />
    </div>
  );
}

function InternationalBenchmark({ r }: { r: BiodefenseReadiness }) {
  const bm = r.international_benchmark;
  const cats = r.threat_category_coverage?.categories;
  const refs = r.international_reference_systems;
  if (!bm && !cats && !refs) return null;

  return (
    <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--line)' }}>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted2)', letterSpacing: '.08em', marginBottom: 8 }}>
        국제 벤치마크
      </div>

      {bm && (
        bm.assessed ? (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
            padding: '10px 12px', borderRadius: 8, background: 'var(--panel2)',
            border: `1px solid ${bm.meets_target ? 'rgba(52,211,153,.4)' : 'rgba(251,146,60,.4)'}`,
          }}>
            <span style={{ fontFamily: 'var(--kr)', fontSize: 12, fontWeight: 700 }}>
              항바이러스제 인구 비축률
            </span>
            <span style={{ fontFamily: 'var(--mono)', fontWeight: 800, fontSize: 18, color: bm.meets_target ? '#34d399' : '#fb923c' }}>
              {((bm.population_coverage_pct ?? 0) * 100).toFixed(1)}%
            </span>
            <span style={{ fontFamily: 'var(--kr)', fontSize: 10.5, color: 'var(--muted2)' }}>
              국제권고 {((bm.international_target_pct ?? 0) * 100).toFixed(0)}% 대비
            </span>
            <span style={{
              marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, fontWeight: 700,
              color: bm.meets_target ? '#34d399' : '#fb923c',
              border: `1px solid ${bm.meets_target ? 'rgba(52,211,153,.4)' : 'rgba(251,146,60,.4)'}`,
              borderRadius: 5, padding: '2px 8px',
            }}>
              {bm.meets_target ? '충족' : '미충족'}
            </span>
          </div>
        ) : (
          <div style={{ fontFamily: 'var(--kr)', fontSize: 11, color: 'var(--muted2)' }}>
            ⓘ {bm.reason ?? '항바이러스제 비축 데이터 없음'} — 국제기준 비교 불가
          </div>
        )
      )}

      {cats && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
          {cats.map(c => (
            <span key={c.category} style={{
              fontFamily: 'var(--kr)', fontSize: 11, padding: '4px 10px', borderRadius: 6,
              background: 'var(--panel2)', border: `1px solid ${c.tracked ? 'var(--line)' : 'rgba(244,63,94,.3)'}`,
              color: c.tracked ? 'var(--txt)' : 'var(--muted2)',
            }}>
              {c.name_ko} {c.tracked ? `(${c.threats_assessed}개 추적 중)` : '— 미추적'}
            </span>
          ))}
        </div>
      )}

      {refs && (
        <div style={{ marginTop: 10 }}>
          {refs.map(s => (
            <div key={s.region} style={{
              padding: '7px 10px', marginTop: 4, borderRadius: 7,
              background: 'var(--panel2)', border: '1px solid var(--line)',
            }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, fontWeight: 700, color: '#a78bfa' }}>
                {s.region}
              </span>{' '}
              <span style={{ fontFamily: 'var(--kr)', fontSize: 11.5, fontWeight: 700 }}>{s.name}</span>
              {s.established && (
                <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}> · {s.established}~</span>
              )}
              <div style={{ fontFamily: 'var(--kr)', fontSize: 10.5, color: 'var(--muted2)', marginTop: 2 }}>
                {s.summary}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StockpileManager({ items, onChanged }: { items: CountermeasureItem[]; onChanged: () => void }) {
  const [name, setName] = useState('');
  const [targets, setTargets] = useState('');
  const [efficacy, setEfficacy] = useState('');
  const [domestic, setDomestic] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function add() {
    if (!name.trim() || !targets.trim()) return;
    setBusy(true); setErr(null);
    try {
      await createStockpileItem({
        name: name.trim(),
        targets: targets.split(',').map(t => t.trim()).filter(Boolean),
        declared_efficacy: efficacy ? Number(efficacy) : undefined,
        domestic_producible: domestic,
      });
      setName(''); setTargets(''); setEfficacy('');
      onChanged();
    } catch (e) { setErr(String(e)); }
    finally { setBusy(false); }
  }

  async function remove(id: number) {
    setBusy(true); setErr(null);
    try { await deleteStockpileItem(id); onChanged(); }
    catch (e) { setErr(String(e)); }
    finally { setBusy(false); }
  }

  return (
    <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--line)' }}>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted2)', letterSpacing: '.08em', marginBottom: 8 }}>
        실제 비축 항목 등록 — 등록하면 위 계산에 예시 데이터 대신 실데이터가 쓰임
      </div>

      {items.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          {items.map(it => (
            <div key={it.id} style={{
              display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
              padding: '6px 10px', marginBottom: 4, borderRadius: 7,
              background: 'var(--panel2)', border: '1px solid var(--line)',
            }}>
              <span style={{ fontFamily: 'var(--kr)', fontSize: 12, fontWeight: 700 }}>{it.name}</span>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--muted)' }}>{it.targets.join(', ')}</span>
              {it.declared_efficacy != null && (
                <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--muted)' }}>효능 {it.declared_efficacy}</span>
              )}
              <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: it.domestic_producible ? '#34d399' : '#fb923c' }}>
                {it.domestic_producible ? '국산' : '수입'}
              </span>
              <button onClick={() => remove(it.id)} disabled={busy} style={{
                marginLeft: 'auto', cursor: 'pointer', fontFamily: 'var(--mono)', fontSize: 10.5,
                color: '#f43f5e', background: 'transparent', border: '1px solid rgba(244,63,94,.3)',
                borderRadius: 6, padding: '3px 8px',
              }}>삭제</button>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="대응제 이름"
          style={inputStyle} />
        <input value={targets} onChange={e => setTargets(e.target.value)} placeholder="대상 병원체(쉼표구분, 예: H5N1,MERS)"
          style={{ ...inputStyle, minWidth: 200 }} />
        <input value={efficacy} onChange={e => setEfficacy(e.target.value)} placeholder="효능(0~1)" type="number" step="0.05" min="0" max="1"
          style={{ ...inputStyle, width: 90 }} />
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'var(--kr)', fontSize: 11.5 }}>
          <input type="checkbox" checked={domestic} onChange={e => setDomestic(e.target.checked)} />
          국내 생산 가능
        </label>
        <button onClick={add} disabled={busy || !name.trim() || !targets.trim()} style={{
          cursor: busy ? 'default' : 'pointer', fontFamily: 'var(--kr)', fontWeight: 700, fontSize: 11.5,
          color: '#fff', background: busy ? 'var(--muted2)' : 'linear-gradient(135deg,#34d399,#059669)',
          border: 'none', borderRadius: 7, padding: '7px 14px',
        }}>등록</button>
      </div>
      {err && <div style={{ marginTop: 6, fontFamily: 'var(--mono)', fontSize: 11, color: '#f43f5e' }}>{err}</div>}
    </div>
  );
}

const inputStyle: CSSProperties = {
  fontFamily: 'var(--kr)', fontSize: 11.5, background: 'var(--panel2)', color: 'var(--txt)',
  border: '1px solid var(--line2)', borderRadius: 7, padding: '6px 10px',
};

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
