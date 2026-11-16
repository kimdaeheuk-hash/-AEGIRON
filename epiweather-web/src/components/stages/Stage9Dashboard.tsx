'use client';
import dynamic from 'next/dynamic';
import { useDashboard } from '@/lib/useDashboard';
import type { Country, StreamEvent, Outbreak, ChainWarning, AlertItem, AlertDashboard, TierSummaryEntry, PredictionAccuracy, VerifiedPrediction } from '@/lib/api';
import { API_BASE } from '@/lib/api';
import { countryLabel } from '@/lib/countryNames';
import { numLocale, useDashLang, useT, type DashLang, type Tr } from '@/lib/dashLang';
import { alertLabel, evidenceLine, isUntranslated, tierName } from '@/lib/backendText';
import { diseaseIn, diseaseName, koTitleTo, placeName } from '@/lib/observationNames';

// 로딩 문구에 '실제로' 부르는 호스트를 쓴다(예전엔 localhost:8000 이 박혀 있어 운영에서도 그렇게 보였다).
const API_HOST = API_BASE.replace(/^https?:\/\//, '');

// Leaflet은 window에 의존해 SSR에서 깨지므로 클라이언트에서만 로드.
const GlobalRiskMap = dynamic(() => import('@/components/GlobalRiskMap'), {
  ssr: false,
  loading: () => (
    <div className="grm-wrap" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted2)', fontFamily: 'var(--mono)', fontSize: 11 }}>
      …
    </div>
  ),
});

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
  const tr = useT();
  const lang = useDashLang();
  const col = scoreColor(gai);
  const top5 = countries.slice(0, 8);
  return (
    <div className="card" style={{ background: `linear-gradient(135deg, rgba(14,22,35,.9), rgba(14,22,35,.6))`, border: `1px solid ${col}33` }}>
      <div className="card-h">
        <span className="lbl">🌐 {tr('글로벌 이상지수 (GAI)', 'Global Anomaly Index (GAI)', 'Indice mondial d’anomalie (GAI)')}</span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: tierColor(tier), border: `1px solid ${tierColor(tier)}44`, borderRadius: 6, padding: '2px 8px' }}>{tierName(tier, lang)}</span>
      </div>
      {/* 실제 지도 (Leaflet + OpenStreetMap) */}
      <GlobalRiskMap countries={countries} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap', marginTop: 14 }}>
        {/* 숫자 */}
        <div style={{ textAlign: 'center', minWidth: 90 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 56, fontWeight: 800, color: col, lineHeight: 1 }}>{Math.round(gai)}</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', letterSpacing: '.14em', marginTop: 4 }}>/ 100</div>
        </div>
        {/* 바 차트 — 지도 마커로는 순위 비교가 어려워서 보조 지표로 유지 */}
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

/**
 * 이벤트 한 건을 사람이 읽는 두 줄로.
 *
 * 백엔드 스트림이 사건 묶음(cluster) 형식으로 바뀌었는데 화면은 옛 title/text 만 알아서,
 * 묶음이 오면 `{"disease":null,"countries":[],...}` 같은 JSON 원문을 그대로 찍었다.
 * 값이 없는 칸은 비워 두지 않고 '질병 미상'·'위치 미상'으로 쓴다 — 모른다는 것도 정보다.
 * 어느 형식에도 안 맞으면 원문 대신 '형식을 알 수 없는 이벤트'라고만 쓴다.
 */
function describeEvent(ev: StreamEvent, tr: Tr, lang: DashLang): { title: string; meta: string } {
  if (ev.title || ev.text) {
    return {
      title: String(ev.title ?? ev.text),
      meta: `${ev.source ?? ev.layer ?? '—'}${ev.timestamp ? ` · ${String(ev.timestamp).slice(0, 16)}` : ''}`,
    };
  }
  if (ev.tier !== undefined || ev.representative || ev.sources) {
    // 서버가 준 질병·장소·등급은 한국어 — 화면 언어로 (2026-11-16)
    const rawDisease = ev.disease ?? ev.representative?.disease;
    const disease = rawDisease ? (diseaseName(rawDisease, lang) ?? rawDisease) : tr('질병 미상', 'disease unknown', 'maladie inconnue');
    const rawWhere = ev.representative?.location || (ev.countries?.length ? ev.countries.join(', ') : null);
    const where = rawWhere ? (placeName(rawWhere, lang) ?? rawWhere) : tr('위치 미상', 'location unknown', 'lieu inconnu');
    const srcs = ev.sources?.length ? ev.sources.join(', ') : (ev.representative?.source ?? '—');
    const parts = [
      srcs,
      typeof ev.source_count === 'number' ? tr(`출처 ${ev.source_count}곳`, `${ev.source_count} sources`, `${ev.source_count} sources`) : null,
      typeof ev.merged_score === 'number' ? tr(`점수 ${Math.round(ev.merged_score)}`, `score ${Math.round(ev.merged_score)}`, `score ${Math.round(ev.merged_score)}`) : null,
      ev.latest_signal_date ? String(ev.latest_signal_date).slice(0, 10) : null,
    ].filter(Boolean);
    return { title: `${ev.tier ? `${tierName(String(ev.tier), lang)} · ` : ''}${disease} · ${where}`, meta: parts.join(' · ') };
  }
  return { title: tr('형식을 알 수 없는 이벤트', 'Event in an unknown format', 'Événement au format inconnu'), meta: ev.source ?? ev.layer ?? '—' };
}

// ── 화면 2: 이벤트 스트림 ─────────────────────────────────────
function Screen2Events({ events, total }: { events: StreamEvent[]; total: number }) {
  const tr = useT();
  const lang = useDashLang();
  return (
    <div className="card" style={{ maxHeight: 300, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <div className="card-h">
        <span className="lbl">📡 {tr('실시간 이벤트 스트림', 'Live event stream', 'Flux d’événements en direct')}</span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}>{tr(`총 ${total}건`, `${total} total`, `${total} au total`)}</span>
      </div>
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {events.length === 0 && <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)', padding: 8 }}>{tr('수집된 이벤트 없음', 'No events collected', 'Aucun événement collecté')}</div>}
        {events.map((ev, i) => {
          const conf = typeof ev.confidence === 'number' ? ev.confidence : null;
          const confCol = conf != null ? (conf >= 0.7 ? '#34d399' : conf >= 0.4 ? '#fbbf24' : '#f97316') : 'var(--muted2)';
          return (
            <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--line)', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: 'var(--kr)', fontSize: 12, color: 'var(--txt)', lineHeight: 1.4 }}>
                  {describeEvent(ev, tr, lang).title}
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)', marginTop: 3 }}>
                  {describeEvent(ev, tr, lang).meta}
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
/**
 * 타임라인 제목을 화면 언어로 (2026-11-16, 캡틴 '번역들이 꼬인 거 같은데').
 * event_name 은 예측 채점 대조 키라 추출 원문이 이어 붙어 언어가 섞인다
 * ('Ebola disease … 에볼라 Kenya and Nigeria 2026'). 질병(웹 사전 → 백엔드 정규 키)·ISO3·연도가
 * 다 읽힐 때만 '질병 · 나라 · 연도'로 다시 쓰고, 원문은 아래 작은 줄에 남긴다. 하나라도 없으면 null(원문 그대로).
 */
function outbreakTitle(ob: Outbreak, lang: DashLang): string | null {
  if (!ob.iso3 || !ob.year) return null;
  const country = countryLabel(ob.iso3, lang);
  const fromKey =
    ob.disease_key &&
    (lang === 'ko' ? (ob.disease_key === 'MERS' ? '메르스' : ob.disease_key) : diseaseName(ob.disease_key, lang));
  const disease = diseaseIn(ob.event_name, lang) ?? fromKey;
  if (!country || !disease) return null;
  return `${disease.charAt(0).toUpperCase()}${disease.slice(1)} · ${country} · ${ob.year}`;
}

function Screen3Timeline({ outbreaks }: { outbreaks: Outbreak[] }) {
  const tr = useT();
  const lang = useDashLang();
  return (
    <div className="card" style={{ maxHeight: 300, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <div className="card-h">
        <span className="lbl">🕒 {tr('발병 타임라인', 'Outbreak timeline', 'Chronologie des épidémies')}</span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}>{outbreaks.length}{tr('건', '', '')}</span>
      </div>
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {outbreaks.length === 0 && <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)', padding: 8 }}>{tr('활성 이벤트 없음', 'No active events', 'Aucun événement actif')}</div>}
        {outbreaks.map((ob, i) => (
          <div key={ob.id ?? i} style={{ padding: '7px 0', borderBottom: '1px solid var(--line)', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <div style={{ width: 3, background: 'var(--accent)', borderRadius: 2, alignSelf: 'stretch', flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              {/* 원문(채점 대조 키)은 언어가 섞여 있어 본문 대신 마우스를 올리면 보이게 둔다 (2026-11-16) */}
              <div
                style={{ fontFamily: 'var(--disp)', fontSize: 12, fontWeight: 700, color: 'var(--txt)' }}
                title={outbreakTitle(ob, lang) && ob.event_name ? `${tr('원문', 'Source text', 'Texte source')}: ${ob.event_name}` : undefined}
              >
                {outbreakTitle(ob, lang) ?? koTitleTo(ob.event_name ?? null, lang) ?? ob.event_id ?? '—'}
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
  const tr = useT();
  return (
    <div className="card">
      <div className="card-h">
        <span className="lbl">🏴 {tr('국가별 위험지수 상위 20', 'Top 20 countries by risk index', '20 premiers pays par indice de risque')}</span>
      </div>
      <div className="rank-grid">
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
  score7, score14, tier7, tier14, warnings, topAlerts, trackRecord,
}: {
  score7: number; score14: number;
  tier7: string; tier14: string;
  warnings: ChainWarning[];
  topAlerts: AlertItem[];
  trackRecord: { accuracy: PredictionAccuracy; recent_verified: VerifiedPrediction[] };
}) {
  const acc = trackRecord.accuracy;
  const tr = useT();
  const lang = useDashLang();
  return (
    <div className="card">
      <div className="card-h">
        <span className="lbl">🧠 {tr('AI 예측 패널', 'AI forecast panel', 'Panneau de prévision IA')}</span>
      </div>
      {/* 7일·14일 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
        {([
          { label: tr('7일 예측', '7-day forecast', 'Prévision 7 j'), score: score7, tier: tier7 },
          { label: tr('14일 예측', '14-day forecast', 'Prévision 14 j'), score: score14, tier: tier14 },
        ] as const).map(item => (
          <div key={item.label} className="oc">
            <div className="ok">{item.label}</div>
            <div className="ov" style={{ color: scoreColor(item.score) }}>{Math.round(item.score)}</div>
            <div className="od" style={{ color: tierColor(item.tier) }}>{tierName(item.tier, lang)}</div>
          </div>
        ))}
      </div>
      {/* 지식 그래프 경보 */}
      {warnings.length > 0 && (
        <>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', letterSpacing: '.14em', marginBottom: 7 }}>
            {tr('활성 체인 경보', 'Active chain warnings', 'Alertes de chaîne actives')}
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
      {/* 예측 트랙레코드 — "우리가 X% 맞췄다"의 실측 근거 */}
      <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--line)' }}>
        <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', letterSpacing: '.14em', marginBottom: 7 }}>
          {tr('예측 트랙레코드', 'Forecast track record', 'Historique des prévisions')}
        </div>
        {acc.total_verified === 0 ? (
          <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>
            {tr('아직 검증된 예측 없음 — 표본이 쌓이면 적중률이 계산됨', 'No verified forecasts yet; accuracy is computed once samples accumulate', 'Aucune prévision vérifiée pour l’instant ; la précision sera calculée quand l’échantillon grandira')}
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 10 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 22, fontWeight: 800, color: 'var(--ok)' }}>
                {acc.accuracy != null ? `${Math.round(acc.accuracy * 100)}%` : '—'}
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 8, color: 'var(--muted2)' }}>{tr('적중률', 'accuracy', 'précision')}</div>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)', lineHeight: 1.7 }}>
              {tr(`검증 ${acc.total_verified}건 중 ${acc.correct}건 적중`, `${acc.correct} of ${acc.total_verified} verified forecasts correct`, `${acc.correct} sur ${acc.total_verified} prévisions vérifiées justes`)}
              {acc.mean_lead_days != null && <><br />{tr('평균 선행일수', 'Mean lead time', 'Avance moyenne')} D−{Math.round(acc.mean_lead_days)}</>}
            </div>
          </div>
        )}
        {trackRecord.recent_verified.map(p => (
          <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontFamily: 'var(--mono)', fontSize: 10 }}>
            <span style={{ color: p.correct ? 'var(--ok)' : '#ef4444', flexShrink: 0 }}>{p.correct ? '✓' : '✗'}</span>
            <span style={{ color: 'var(--txt)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {p.country} · {p.disease}
            </span>
            {p.lead_days != null && <span style={{ color: 'var(--muted2)', flexShrink: 0 }}>D−{p.lead_days}</span>}
          </div>
        ))}
      </div>
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
  const tr = useT();
  const lang = useDashLang();

  const tierDefs: { key: string; label: string; col: string }[] = [
    { key: 'critical', label: 'CRITICAL', col: '#ef4444' },
    { key: 'high',     label: 'HIGH',     col: '#f97316' },
    { key: 'medium',   label: 'MEDIUM',   col: '#fbbf24' },
    { key: 'low',      label: 'LOW',      col: '#34d399' },
  ];

  return (
    <div className="card">
      <div className="card-h">
        <span className="lbl">🚨 {tr('경보 센터', 'Alert centre', 'Centre d’alertes')}</span>
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
        <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ok)', padding: '8px 0' }}>✓ {tr('활성 경보 없음', 'No active alerts', 'Aucune alerte active')}</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {topItems.map((a, i) => {
            const col = tierColor(a.tier);
            return (
              <div key={i} style={{ padding: '8px 10px', background: `${col}0d`, borderRadius: 8, border: `1px solid ${col}22` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: col, border: `1px solid ${col}44`, borderRadius: 4, padding: '1px 5px', flexShrink: 0 }}>
                    {tierName(a.tier ?? '', lang).toUpperCase()}
                  </div>
                  <div style={{ flex: 1, fontFamily: 'var(--kr)', fontSize: 12, color: 'var(--txt)', lineHeight: 1.4 }}>
                    {a.label ? alertLabel(a.label, lang) : (a.metric ?? a.message ?? '—')}
                  </div>
                  {a.score != null && (
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: col, flexShrink: 0 }}>{Math.round(a.score)}</div>
                  )}
                </div>
                {/* 경보 근거 — "근거 없는 숫자는 기관이 사용 못 함" */}
                {a.evidence && a.evidence.length > 0 && (
                  <div style={{ marginTop: 6, paddingLeft: 8, borderLeft: `2px solid ${col}33` }}>
                    {a.evidence.map((e, ei) => (
                      <div key={ei} style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted2)', lineHeight: 1.6 }}>
                        · {evidenceLine(String(e), lang)}
                        {isUntranslated(evidenceLine(String(e), lang), lang) ? ` ${tr('', '(original in Korean)', '(original en coréen)')}` : ''}
                      </div>
                    ))}
                  </div>
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
  const { data, loading, error, lastUpdated, live } = useDashboard(30_000);
  const tr = useT();
  const lang = useDashLang();
  const title = tr('실시간 대시보드', 'Live dashboard', 'Tableau de bord en direct');

  if (loading) {
    return (
      <div style={{ animation: 'fade .25s' }}>
        <div className="ptitle">{title}</div>
        <div className="psub">{tr('백엔드 서버에서 실시간 데이터를 가져오는 중...', 'Fetching live data from the backend server…', 'Récupération des données en direct depuis le serveur…')}</div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: 20, fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--muted)',
        }}>
          <span style={{ animation: 'sp 1.2s linear infinite', display: 'inline-block' }}>⟳</span>
          {tr('서버 연결 중', 'Connecting to server', 'Connexion au serveur')} — {API_HOST}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ animation: 'fade .25s' }}>
        <div className="ptitle">{title}</div>
        <div style={{ padding: '16px 0' }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: '#ef4444', marginBottom: 10 }}>
            ⚠ {tr('백엔드 서버에 연결할 수 없습니다', 'Cannot connect to the backend server', 'Impossible de joindre le serveur')}
          </div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)', lineHeight: 1.8 }}>
            {tr('연결 대상', 'Target', 'Cible')}: {API_HOST}<br />
            <span style={{ color: 'var(--ok)' }}>{tr('위 주소가 맞는데도 안 되면 CORS·방화벽·확장프로그램 확인', 'If the address is right and it still fails, check CORS, firewall and browser extensions', 'Si l’adresse est correcte et que cela échoue, vérifiez CORS, pare-feu et extensions')}</span>
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
          <div className="ptitle">{title}</div>
          <div className="psub">{tr('백엔드 실시간 데이터', 'Live backend data', 'Données du serveur en direct')} · {live ? tr('WebSocket 실시간 푸시', 'WebSocket live push', 'push WebSocket en direct') : tr('30초 폴링(WebSocket 미연결)', '30 s polling (WebSocket not connected)', 'interrogation toutes les 30 s (WebSocket non connecté)')}</div>
        </div>
        {lastUpdated && (
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)', textAlign: 'right' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--ok)', boxShadow: '0 0 6px var(--ok)', display: 'inline-block', marginRight: 5, animation: 'blink 1.6s infinite' }} />
            {tr('갱신', 'Updated', 'Mis à jour')} {lastUpdated.toLocaleTimeString(numLocale(lang))}
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
          trackRecord={s5.prediction_track_record}
        />
      </div>

      {/* 화면 6: 경보 센터 */}
      <div style={{ marginTop: 14 }}>
        <Screen6Alerts dashboard={s6.dashboard} tierSummary={s6.tier_summary} />
      </div>
    </div>
  );
}
