'use client';
import { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { CHANNELS, clamp } from '@/lib/algorithms';

const API = 'http://localhost:8000';

interface WhoSignal { title: string; date?: string; risk: number; source: string; link?: string }
interface LocalSignalTitle { title: string; recent_14d?: number; baseline_14d?: number; ratio?: number; error?: string }
interface LocalSignal {
  available: boolean; reason?: string; lang?: string;
  titles?: LocalSignalTitle[]; max_anomaly_ratio?: number; verdict?: string; source?: string;
}

export default function Stage0PatientZero() {
  const { pz, zsel, setZSel, origin } = useStore();

  const [who, setWho] = useState<WhoSignal[] | null>(null);
  useEffect(() => {
    fetch(`${API}/api/synthetic-threat/who`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(d => setWho(d.items))
      .catch(() => setWho(null));
  }, []);

  const [local, setLocal] = useState<LocalSignal | null>(null);
  useEffect(() => {
    setLocal(null);
    fetch(`${API}/api/patient-zero/local-signal?origin_id=${origin}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setLocal)
      .catch(() => setLocal(null));
  }, [origin]);

  interface EbolaEvidence { best_lead_days: number; best_label: string; who_pheic_date: string; data_source: string; caveat: string }
  const [ebola, setEbola] = useState<EbolaEvidence | null>(null);
  const [ebolaErr, setEbolaErr] = useState(false);
  useEffect(() => {
    fetch(`${API}/api/patient-zero/ebola-backtest-evidence`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setEbola)
      .catch(() => setEbolaErr(true));
  }, []);

  if (!pz) return null;

  const maxP = Math.max(...pz.cells.map(c => c.prob), .01);

  function cellColor(prob: number) {
    const t = Math.min(1, prob / maxP);
    if (t < .2) return `rgba(26,36,51,${.4 + t * 1.5})`;
    if (t < .5) {
      const k = (t - .2) / .3;
      return `rgb(${26 + k * 30 | 0},${36 + k * 153 | 0},${51 + k * 200 | 0})`;
    }
    if (t < .8) {
      const k = (t - .5) / .3;
      return `rgb(${56 + k * 195 | 0},${189 - k * 10 | 0},${251 - k * 214 | 0})`;
    }
    const k = (t - .8) / .2;
    return `rgb(${251 - k * 7 | 0},${179 - k * 116 | 0},${37 + k * 57 | 0})`;
  }

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">최초 발원지 추적</div>
      <div className="psub">
        스컹크웍스가 벽 너머 <em style={{ color: 'var(--violet)', fontStyle: 'normal', fontWeight: 600 }}>심장박동</em>을 잡았듯이,
        진단 0명 시점에 격자 단위 발원지를 추론합니다.
        6채널 약신호를 <em style={{ color: 'var(--violet)', fontStyle: 'normal', fontWeight: 600 }}>피셔 결합</em>으로 증폭.
      </div>

      <div className="grid2">
        {/* 히트맵 */}
        <div className="card">
          <div className="card-h">
            <span className="lbl">격자 후방확률 · 10×10</span>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>
              최고확률 {(pz.top.prob * 100).toFixed(1)}% · 6채널 결합
            </span>
          </div>
          <div style={{
            background: 'linear-gradient(180deg,#070b14,#0a1018)',
            borderRadius: 11, padding: 8, border: '1px solid var(--line)',
          }}>
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(10,1fr)',
              gridTemplateRows: 'repeat(10,1fr)', gap: 2, aspectRatio: '1',
            }}>
              {pz.cells.map((cell, i) => {
                const isCand = pz.cands.includes(cell);
                const isTop = pz.top === cell;
                return (
                  <div key={i}
                    onClick={() => setZSel(cell)}
                    style={{
                      borderRadius: 3,
                      background: cellColor(cell.prob),
                      cursor: 'pointer',
                      transition: 'all .4s',
                      outline: isCand ? '2px solid var(--accent)' : undefined,
                      boxShadow: isCand ? '0 0 10px var(--accent)' : undefined,
                      position: 'relative',
                      display: 'grid', placeItems: 'center',
                    }}
                  >
                    {isTop && (
                      <span style={{
                        color: '#fff', fontSize: 13, fontWeight: 'bold',
                        textShadow: '0 0 6px #000',
                        animation: 'cpulse 1.5s infinite',
                      }}>◎</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)',
            marginTop: 8, alignItems: 'center',
          }}>
            <span>낮음</span>
            <span style={{
              height: 7, flex: 1, margin: '0 12px', borderRadius: 3,
              background: 'linear-gradient(90deg,#1a2433,#38bdf8,#fbbf24,#f43f5e)',
            }} />
            <span>발원 의심</span>
          </div>
        </div>

        {/* 후보 목록 */}
        <div className="card">
          <div className="card-h"><span className="lbl">발원 후보 TOP 5</span></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {pz.cands.map((cell, i) => (
              <div key={i}
                onClick={() => setZSel(cell)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '9px 11px',
                  background: cell === zsel ? 'rgba(244,63,94,.08)' : 'rgba(255,255,255,.025)',
                  border: `1px solid ${cell === zsel ? 'var(--accent)' : 'var(--line)'}`,
                  borderRadius: 10, cursor: 'pointer',
                }}
              >
                <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, width: 22, textAlign: 'center', color: 'var(--accent)' }}>
                  #{i + 1}
                </div>
                <div style={{ flex: 1, fontSize: 12, fontWeight: 600 }}>
                  격자({cell.r},{cell.c})
                  <small style={{ display: 'block', fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', marginTop: 1 }}>
                    {i === 0 ? '최우선 발원 후보' : '대안'}
                  </small>
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 700, color: 'var(--accent)', width: 50, textAlign: 'right' }}>
                  {(cell.prob * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>

          {zsel && (
            <>
              <div style={{
                fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted)',
                textTransform: 'uppercase', letterSpacing: '.16em', margin: '12px 0 8px',
              }}>선택 격자 · 6채널 약신호</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {zsel.zs.map((z, i) => {
                  const ch = CHANNELS[i];
                  const pct = clamp((z + 1) / 4 * 100, 3, 100);
                  const col = z > 2 ? '#ef4444' : z > 1 ? '#fbbf24' : z > 0 ? ch.col : '#566377';
                  return (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', gap: 9,
                      padding: '7px 10px',
                      background: 'rgba(255,255,255,.025)',
                      border: '1px solid var(--line)', borderRadius: 8,
                    }}>
                      <span style={{ fontSize: 14 }}>{ch.ic}</span>
                      <span style={{ fontSize: 11, flex: 1 }}>{ch.nm}</span>
                      <div style={{ width: 60, height: 4, background: 'rgba(255,255,255,.06)', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ width: `${pct}%`, height: '100%', borderRadius: 2, background: col }} />
                      </div>
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, width: 42, textAlign: 'right', color: col }}>
                        {z >= 0 ? '+' : ''}{z.toFixed(2)}σ
                      </span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* 발원지 현지어 위키피디아 신호 — 한국 데이터로는 못 보는 '현지' 실신호 대체재 */}
      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-h">
          <span className="lbl">발원지 현지어 위키피디아 신호 ({origin})</span>
          {local?.lang && <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)' }}>{local.lang}.wikipedia 실시간 · 최근14일 vs 이전14일</span>}
        </div>
        {!local && <div style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 10.5, padding: '8px 0' }}>현지어 신호 불러오는 중...</div>}
        {local && !local.available && <div style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 10.5, padding: '8px 0' }}>{local.reason}</div>}
        {local?.available && (
          <>
            <div style={{ fontFamily: 'var(--disp)', fontWeight: 700, fontSize: 13, marginBottom: 8, color: (local.max_anomaly_ratio ?? 1) > 2 ? '#ef4444' : (local.max_anomaly_ratio ?? 1) > 1.3 ? '#fbbf24' : 'var(--ok)' }}>
              {local.verdict}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {local.titles?.map((t, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '7px 10px', background: 'rgba(255,255,255,.025)', border: '1px solid var(--line)', borderRadius: 8 }}>
                  <span style={{ fontSize: 11, flex: 1 }}>{t.title}</span>
                  {t.error ? (
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)' }}>조회 실패</span>
                  ) : (
                    <>
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)' }}>{t.recent_14d} / {t.baseline_14d}회</span>
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, width: 42, textAlign: 'right', color: (t.ratio ?? 1) > 2 ? '#ef4444' : (t.ratio ?? 1) > 1.3 ? '#fbbf24' : 'var(--ok)' }}>
                        ×{t.ratio}
                      </span>
                    </>
                  )}
                </div>
              ))}
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 8.5, color: 'var(--muted2)', marginTop: 8 }}>{local.source}</div>
          </>
        )}
      </div>

      {/* 실측 검증: 진행중인 2026 에볼라 PHEIC으로 위 방법론을 백테스트 */}
      {ebola && (
        <div className="card" style={{ marginTop: 14, background: 'rgba(52,211,153,.07)', borderColor: 'rgba(52,211,153,.3)' }}>
          <div className="card-h"><span className="lbl">✅ 실측 검증 — 2026 에볼라 PHEIC 백테스트</span></div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10.5, lineHeight: 1.7 }}>
            <b style={{ color: 'var(--ok)' }}>{ebola.best_label}</b>이 WHO PHEIC 선언({ebola.who_pheic_date})보다{' '}
            <b style={{ color: 'var(--ok)' }}>{ebola.best_lead_days}일</b> 먼저 반응 (현재 진행 중인 실제 사건)
          </div>
          <div style={{ color: 'var(--muted2)', fontSize: 9, marginTop: 6, lineHeight: 1.5 }}>
            {ebola.data_source}<br />⚠ {ebola.caveat}
          </div>
        </div>
      )}
      {ebolaErr && (
        <div style={{ marginTop: 12, padding: '9px 13px', borderRadius: 11, background: 'rgba(255,255,255,.025)', border: '1px solid var(--line)', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}>
          에볼라 백테스트 데이터를 불러오지 못했습니다.
        </div>
      )}

      {/* 실제 WHO 발생 동향 — 위 격자는 방법론 시연용 시뮬레이션, 아래는 실데이터 */}
      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-h">
          <span className="lbl">현재 실제 발원지 신호 (WHO)</span>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)' }}>
            ⚠ 위 10×10 격자는 방법론(Fisher 결합) 시연용 시뮬레이션, 위·아래 카드는 실시간 데이터
          </span>
        </div>
        {who === null && (
          <div style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 10.5, padding: '8px 0' }}>실시간 WHO 신호 불러오는 중...</div>
        )}
        {who && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {who.map((w, i) => {
              const wc = w.risk > 60 ? '#ef4444' : w.risk > 35 ? '#fbbf24' : '#34d399';
              return (
                <a key={i} href={w.link} target="_blank" rel="noreferrer"
                  style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '8px 9px', background: 'rgba(255,255,255,.025)', border: '1px solid var(--line)', borderLeft: `3px solid ${wc}`, borderRadius: 4, textDecoration: 'none' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 10.5, fontWeight: 600, color: wc }}>{w.title}</div>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 8, color: 'var(--muted2)' }}>{w.date}</div>
                  </div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 700, color: wc }}>{w.risk}</div>
                </a>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
