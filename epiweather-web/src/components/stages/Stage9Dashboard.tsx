'use client';
import { useDashboard } from '@/lib/useDashboard';
import type { Country, StreamEvent, Outbreak, ChainWarning, AlertItem, AlertDashboard, TierSummaryEntry } from '@/lib/api';

// ── 색상 헬퍼 ─────────────────────────────────────────────────
function tierColor(tier: string | undefined): string {
  if (!tier) return 'var(--muted)';
  const t = tier.toUpperCase();
  if (t.includes('CRITICAL') || t.includes('위험')) return '#ef4444';
  if (t.includes('ALERT') || t.includes('경보')) return '#f97316';
  if (t.includes('WATCH') || t.includes('주의')) return '#fbbf24';
  if (t.includes('정상') || t.includes('NORMAL')) return '#34d399';
  return 'var(--muted)';
}

function scoreColor(score: number): string {
  if (score >= 80) return '#ef4444';
  if (score >= 60) return '#f97316';
  if (score >= 40) return '#fbbf24';
  return '#34d399';
}

// ── 화면 1: GAI 배너 ──────────────────────────────────────────
function Screen1Banner({ gai, tier, countries }: { gai: number; tier: string; countries: Country[] }) {
  const col = scoreColor(gai);
  const top5 = countries.slice(0, 8);
  return (
    <div className="card" style={{ background: `linear-gradient(135deg, rgba(14,22,35,.9), rgba(14,22,35,.6))`, border: `1px solid ${col}33` }}>
      <div className="card-h">
        <span className="lbl">🌐 글로벌 이상지수 (GAI)</span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: tierColor(tier), border: `1px solid ${tierColor(tier)}44`, borderRadius: 6, padding: '2px 8px' }}>{tier}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
        {/* 숫자 */}
        <div style={{ textAlign: 'center', minWidth: 90 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 56, fontWeight: 800, color: col, lineHeight: 1 }}>{Math.round(gai)}</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', letterSpacing: '.14em', marginTop: 4 }}>/ 100</div>
        </div>
        {/* 바 차트 */}
        <div style={{ flex: 1, minWidth: 200 }}>
          {top5.map(c => {
            const sc = c.risk_score ?? 0;
            return (
              <div key={c.country} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 10, width: 80, color: 'var(--txt)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.country}</div>
                <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,.06)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(sc, 100)}%`, height: '100%', background: scoreColor(sc), borderRadius: 3, transition: '.4s' }} />
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 10, width: 30, textAlign: 'right', color: scoreColor(sc) }}>{Math.round(sc)}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── 화면 2: 이벤트 스트림 ─────────────────────────────────────
function Screen2Events({ events, total }: { events: StreamEvent[]; total: number }) {
  return (
    <div className="card" style={{ maxHeight: 300, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <div className="card-h">
        <span className="lbl">📡 실시간 이벤트 스트림</span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}>총 {total}건</span>
      </div>
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {events.length === 0 && <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)', padding: 8 }}>수집된 이벤트 없음</div>}
        {events.map((ev, i) => {
          const conf = typeof ev.confidence === 'number' ? ev.confidence : null;
          const confCol = conf != null ? (conf >= 0.7 ? '#34d399' : conf >= 0.4 ? '#fbbf24' : '#f97316') : 'var(--muted2)';
          return (
            <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--line)', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: 'var(--kr)', fontSize: 12, color: 'var(--txt)', lineHeight: 1.4 }}>
                  {ev.title ?? ev.text ?? JSON.stringify(ev).slice(0, 80)}
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)', marginTop: 3 }}>
                  {ev.source ?? ev.layer ?? '—'}
                  {ev.timestamp ? ` · ${String(ev.timestamp).slice(0, 16)}` : ''}
                </div>
              </div>
              {conf != null && (
                <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: confCol, border: `1px solid ${confCol}44`, borderRadius: 4, padding: '2px 5px', flexShrink: 0 }}>
                  {Math.round(conf * 100)}%
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── 화면 3: 발병 타임라인 ─────────────────────────────────────
function Screen3Timeline({ outbreaks }: { outbreaks: Outbreak[] }) {
  return (
    <div className="card" style={{ maxHeight: 300, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <div className="card-h">
        <span className="lbl">🕒 발병 타임라인</span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}>{outbreaks.length}건</span>
      </div>
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {outbreaks.length === 0 && <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)', padding: 8 }}>활성 이벤트 없음</div>}
        {outbreaks.map((ob, i) => (
          <div key={ob.id ?? i} style={{ padding: '7px 0', borderBottom: '1px solid var(--line)', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <div style={{ width: 3, background: 'var(--accent)', borderRadius: 2, alignSelf: 'stretch', flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: 'var(--disp)', fontSize: 12, fontWeight: 700, color: 'var(--txt)' }}>
                {ob.event_name ?? ob.event_id ?? '—'}
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', marginTop: 2 }}>
                {ob.milestone ?? ''}{ob.event_date ? ` · ${String(ob.event_date).slice(0, 10)}` : ''}
              </div>
              {ob.description && (
                <div style={{ fontFamily: 'var(--kr)', fontSize: 11, color: 'var(--muted2)', marginTop: 3, lineHeight: 1.4 }}>
                  {ob.description}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── 화면 4: 국가별 위험 랭킹 ──────────────────────────────────
function Screen4Ranking({ top20 }: { top20: Country[] }) {
  return (
    <div className="card">
      <div className="card-h">
        <span className="lbl">🏴 국가별 위험지수 상위 20</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px 14px' }}>
        {top20.slice(0, 20).map((c, i) => {
          const sc = c.risk_score ?? 0;
          return (
            <div key={c.country} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '4px 0', borderBottom: '1px solid var(--line)' }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)', width: 16, flexShrink: 0 }}>{i + 1}</span>
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--txt)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.country}</div>
                <div style={{ height: 3, background: 'rgba(255,255,255,.06)', borderRadius: 2, marginTop: 2, overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(sc, 100)}%`, height: '100%', background: scoreColor(sc) }} />
                </div>
              </div>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: scoreColor(sc), flexShrink: 0 }}>{Math.round(sc)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── 화면 5: AI 예측 패널 ──────────────────────────────────────
function Screen5Forecast({
  score7, score14, tier7, tier14, warnings, topAlerts,
}: {
  score7: number; score14: number;
  tier7: string; tier14: string;
  warnings: ChainWarning[];
  topAlerts: AlertItem[];
}) {
  return (
    <div className="card">
      <div className="card-h">
        <span className="lbl">🧠 AI 예측 패널</span>
      </div>
      {/* 7일·14일 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
        {([
          { label: '7일 예측', score: score7, tier: tier7 },
          { label: '14일 예측', score: score14, tier: tier14 },
        ] as const).map(item => (
          <div key={item.label} className="oc">
            <div className="ok">{item.label}</div>
            <div className="ov" style={{ color: scoreColor(item.score) }}>{Math.round(item.score)}</div>
            <div className="od" style={{ color: tierColor(item.tier) }}>{item.tier}</div>
          </div>
        ))}
      </div>
      {/* 지식 그래프 경보 */}
      {warnings.length > 0 && (
        <>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', letterSpacing: '.14em', marginBottom: 7 }}>
            활성 체인 경보
          </div>
          {warnings.map((w, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 5 }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: '#f97316', width: 60, flexShrink: 0 }}>{w.disease ?? '—'}</span>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)', flex: 1 }}>{w.trigger_metric ?? ''}</span>
              {w.lead_days != null && (
                <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--ok)' }}>D−{w.lead_days}</span>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}

// ── 화면 6: 경보 센터 ──────────────────────────────────────────
function Screen6Alerts({
  dashboard, tierSummary,
}: {
  dashboard: AlertDashboard | null;
  tierSummary: Record<string, TierSummaryEntry> | null;
}) {
  const topItems: AlertItem[] = dashboard?.top ?? [];

  const tierDefs: { key: string; label: string; col: string }[] = [
    { key: 'critical', label: 'CRITICAL', col: '#ef4444' },
    { key: 'high',     label: 'HIGH',     col: '#f97316' },
    { key: 'medium',   label: 'MEDIUM',   col: '#fbbf24' },
    { key: 'low',      label: 'LOW',      col: '#34d399' },
  ];

  return (
    <div className="card">
      <div className="card-h">
        <span className="lbl">🚨 경보 센터</span>
        {tierSummary && (
          <div style={{ display: 'flex', gap: 10 }}>
            {tierDefs.map(({ key, col }) => {
              const entry = tierSummary[key];
              if (!entry || entry.total === 0) return null;
              return (
                <span key={key} style={{ fontFamily: 'var(--mono)', fontSize: 9, color: col, border: `1px solid ${col}44`, borderRadius: 4, padding: '1px 6px' }}>
                  {key.toUpperCase()} {entry.total}
                </span>
              );
            })}
          </div>
        )}
      </div>

      {/* 활성 경보 목록 */}
      {topItems.length === 0 ? (
        <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ok)', padding: '8px 0' }}>✓ 활성 경보 없음</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {topItems.map((a, i) => {
            const col = tierColor(a.tier);
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', background: `${col}0d`, borderRadius: 8, border: `1px solid ${col}22` }}>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: col, border: `1px solid ${col}44`, borderRadius: 4, padding: '1px 5px', flexShrink: 0 }}>
                  {(a.tier ?? '').toUpperCase()}
                </div>
                <div style={{ flex: 1, fontFamily: 'var(--kr)', fontSize: 12, color: 'var(--txt)', lineHeight: 1.4 }}>
                  {a.label ?? a.metric ?? a.message ?? '—'}
                </div>
                {a.score != null && (
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: col, flexShrink: 0 }}>{Math.round(a.score)}</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────
export default function Stage9Dashboard() {
  const { data, loading, error, lastUpdated } = useDashboard(30_000);

  if (loading) {
    return (
      <div style={{ animation: 'fade .25s' }}>
        <div className="ptitle">실시간 대시보드</div>
        <div className="psub">백엔드 서버에서 실시간 데이터를 가져오는 중...</div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: 20, fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--muted)',
        }}>
          <span style={{ animation: 'sp 1.2s linear infinite', display: 'inline-block' }}>⟳</span>
          서버 연결 중 — localhost:8000
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ animation: 'fade .25s' }}>
        <div className="ptitle">실시간 대시보드</div>
        <div style={{ padding: '16px 0' }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: '#ef4444', marginBottom: 10 }}>
            ⚠ 백엔드 서버에 연결할 수 없습니다
          </div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)', lineHeight: 1.8 }}>
            서버 실행 방법:<br />
            <span style={{ color: 'var(--ok)' }}>cd epiweather-api && uvicorn main:app --reload --port 8000</span>
          </div>
          {error && (
            <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: '#f97316', marginTop: 8, background: 'rgba(249,115,22,.08)', padding: '8px 10px', borderRadius: 8 }}>
              {error}
            </div>
          )}
        </div>
      </div>
    );
  }

  const s1 = data.screen1_global_map;
  const s2 = data.screen2_event_stream;
  const s3 = data.screen3_timeline;
  const s4 = data.screen4_country_ranking;
  const s5 = data.screen5_forecast;
  const s6 = data.screen6_alert_center;

  return (
    <div style={{ animation: 'fade .25s' }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 4, flexWrap: 'wrap', gap: 8 }}>
        <div>
          <div className="ptitle">실시간 대시보드</div>
          <div className="psub">백엔드 실시간 데이터 · 30초 자동 갱신</div>
        </div>
        {lastUpdated && (
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)', textAlign: 'right' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--ok)', boxShadow: '0 0 6px var(--ok)', display: 'inline-block', marginRight: 5, animation: 'blink 1.6s infinite' }} />
            갱신 {lastUpdated.toLocaleTimeString('ko-KR')}
          </div>
        )}
      </div>

      {/* 화면 1: GAI 배너 */}
      <Screen1Banner gai={s1.gai} tier={s1.tier} countries={s1.countries} />

      {/* 화면 2+3: 이벤트 스트림 + 타임라인 */}
      <div className="grid2" style={{ marginTop: 14 }}>
        <Screen2Events events={s2.events} total={s2.total} />
        <Screen3Timeline outbreaks={s3.active_outbreaks} />
      </div>

      {/* 화면 4+5: 랭킹 + 예측 */}
      <div className="grid2" style={{ marginTop: 14 }}>
        <Screen4Ranking top20={s4.top20} />
        <Screen5Forecast
          score7={s5.score_7d}
          score14={s5.score_14d}
          tier7={s5.tier_7d}
          tier14={s5.tier_14d}
          warnings={s5.chain_warnings}
          topAlerts={s5.top_alerts}
        />
      </div>

      {/* 화면 6: 경보 센터 */}
      <div style={{ marginTop: 14 }}>
        <Screen6Alerts dashboard={s6.dashboard} tierSummary={s6.tier_summary} />
      </div>
    </div>
  );
}
