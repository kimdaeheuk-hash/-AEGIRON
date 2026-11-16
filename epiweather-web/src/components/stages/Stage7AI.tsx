'use client';
import { useState } from 'react';
import { useStore } from '@/lib/store';
import { THREAT, CIVIC, currentRt } from '@/lib/algorithms';
import LiveObserved from './LiveObserved';
import { numLocale, useDashLang, useT, type Tr } from '@/lib/dashLang';
import { nameOf } from '@/lib/dashNames';

interface PriorityAction {
  priority: number;
  category: string;
  action: string;
  rationale: string;
  urgency: string;
}

interface DecisionTree {
  alert_level: string;
  rt: number;
  summary: string;
  priority_actions: PriorityAction[];
  medical_warning: string | null;
  reasoning: string[];
}

interface InferResponse {
  mode: string;
  alert_level: string;
  decision_tree: DecisionTree;
  llm_analysis: string | null;
  /** 누가 썼는지 — meta_model_api | anthropic. 없으면(옛 서버) Claude로 본다. */
  llm_provider?: string;
  llm_model?: string;
  meta_error?: string | null;
  /** 성공 캐시(2026-11-03) — 없으면(옛 서버) 시간 표시를 생략한다. */
  cached?: boolean;
  cached_at?: string | null;
  situation_hash?: string;
  note?: string;
  error?: string;
  cache_hit?: boolean;
  /** fast=true 1단계 응답 — LLM 분석은 이어서 받는다(2026-11-15) */
  llm_pending?: boolean;
  usage?: { input_tokens: number; output_tokens: number; cache_creation_tokens: number; cache_read_tokens: number };
}

/** 분석 시점 표시 — 캐시 적중이면 몇 분 전 것인지 밝힌다. */
function ageLabel(r: InferResponse, tr: Tr): string {
  if (!r.cached_at) return '';
  const m = Math.max(0, Math.round((Date.now() - new Date(r.cached_at).getTime()) / 60000));
  const when = m <= 0 ? tr('방금 분석', 'analysed just now', 'analysé à l’instant') : tr(`${m}분 전 분석`, `analysed ${m} min ago`, `analysé il y a ${m} min`);
  return ` · ${when}${r.cached ? tr('(캐시)', ' (cached)', ' (cache)') : ''}`;
}

/** 제공자 표시 — 폴백이면 그 사실도 숨기지 않는다. */
function providerLabel(r: InferResponse, tr: Tr): string {
  if (r.llm_provider === 'meta_model_api') return `Meta ${r.llm_model ?? ''}`.trim();
  if (r.llm_provider === 'anthropic') {
    return r.meta_error ? tr('Claude (Meta 실패 후 폴백)', 'Claude (fallback after Meta failed)', 'Claude (secours après échec de Meta)') : 'Claude';
  }
  return 'Claude';
}

const ALERT_COLOR: Record<string, string> = {
  '관심(Blue)': '#3b82f6',
  '주의(Yellow)': '#eab308',
  '경계(Orange)': '#f97316',
  '심각(Red)': '#ef4444',
};

const URGENCY_COLOR: Record<string, string> = {
  '즉시(24시간 내)': '#ef4444',
  '즉시': '#f97316',
  '48시간 내': '#fb923c',
  '3일 내': '#eab308',
  '2주 내': '#22c55e',
  '주간 점검': '#3b82f6',
};

export default function Stage7AI() {
  const { pz, glob, def, def0, lev, threat, origin, civicOn, savedLives } = useStore();
  const tr = useT();
  const lang = useDashLang();
  const nf = (n: number) => n.toLocaleString(numLocale(lang));
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [result, setResult] = useState<InferResponse | null>(null);
  // 2단계(LLM) 진행 중 — 1단계 결과는 이미 화면에 있다
  const [llmLoading, setLlmLoading] = useState(false);
  const [llmError, setLlmError] = useState('');
  const [errMsg, setErrMsg] = useState('');

  if (!pz || !glob || !def || !def0) return null;

  const sp = THREAT[threat];
  const civicLead = Math.max(...CIVIC.filter(s => civicOn[s.id]).map(s => s.lead), 0);
  const rt = currentRt(lev, threat);

  const summaryItems = [
    { label: tr('발원지 추적', 'Origin tracing', 'Traçage de l’origine'), val: `${tr('격자', 'Cell', 'Cellule')}(${pz.top.r},${pz.top.c})`, sub: tr(`${(pz.top.prob * 100).toFixed(1)}% 확률`, `${(pz.top.prob * 100).toFixed(1)}% probability`, `probabilité ${(pz.top.prob * 100).toFixed(1)} %`) },
    { label: tr('민간 선행', 'Civic lead', 'Avance citoyenne'), val: `D−${civicLead}${tr('일', 'd', ' j')}`, sub: tr('정부 대비', 'vs government', 'vs officiel'), color: 'var(--violet)' },
    { label: tr('한국 유입', 'Arrival in Korea', 'Arrivée en Corée'), val: `D+${glob.arrival}`, sub: tr(`${glob.city.nm}발`, `from ${nameOf(glob.city.nm, lang)}`, `depuis ${nameOf(glob.city.nm, lang)}`) },
    { label: tr('위협', 'Threat', 'Menace'), val: nameOf(sp.nm, lang), sub: `R₀ ${sp.R0}` },
    { label: tr('방어 효과', 'Defence effect', 'Effet de la défense'), val: `${nf(savedLives)}${tr('명', '', '')}`, sub: tr('구한 생명', 'lives saved', 'vies sauvées'), color: 'var(--ok)' },
    { label: 'Rt', val: rt.toFixed(2), sub: rt < 1 ? tr('차단', 'stopped', 'stoppé') : tr('억제', 'suppressing', 'freinage'), color: rt < 1 ? 'var(--ok)' : '#fb923c' },
  ];

  async function runAI() {
    setStatus('loading');
    setResult(null);

    const body = {
      origin_id: origin,
      threat,
      rt: Number(rt.toFixed(3)),
      arrival_day: glob!.arrival,
      detect_lead: glob!.detectLead,
      civic_lead: civicLead,
      pz_top_prob: Number(pz!.top.prob.toFixed(4)),
      pz_top_cell: `${pz!.top.r}${pz!.top.c}`,
      saved_lives: savedLives,
      deaths: Math.round(def!.deaths),
      peak_infected: Math.round(def!.peak),
      hosp_overflow_days: def!.ofd,
      levers: {
        quar: lev.quar, dist: lev.dist, vax: lev.vax,
        anti: lev.anti, vuln: lev.vuln,
      },
    };

    // ★ 두 단계(2026-11-15) ★ 캡틴: "추론도 엄청 늦게 떠". LLM 은 60~120초라, 먼저 fast=true 로
    // 의사결정 트리를 즉시 받아 그리고, LLM 분석은 두 번째 요청으로 이어 받아 채운다.
    async function post(payload: object): Promise<InferResponse> {
      const res = await fetch('/api/ai/infer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        let detail = '';
        try {
          const t = await res.clone().text();
          try { detail = (JSON.parse(t) as { detail?: string }).detail || ''; }
          catch { detail = t.startsWith('<') ? '' : t; }
        } catch { /* 본문 없음 */ }
        throw new Error(`${tr('서버 오류', 'Server error', 'Erreur serveur')} (${res.status})${detail ? ' — ' + String(detail).slice(0, 140) : ''}`);
      }
      return (await res.json()) as InferResponse;
    }

    setLlmError('');
    let first: InferResponse;
    try {
      first = await post({ ...body, fast: true });
      setResult(first);
      setStatus('done');
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : String(e));
      setStatus('error');
      return;
    }
    if (!first.llm_pending) return; // 캐시된 완성본이거나 키가 없어 트리만 있는 경우
    setLlmLoading(true);
    try {
      const full = await post(body);
      setResult(full);
    } catch (e) {
      setLlmError(e instanceof Error ? e.message : String(e));
    } finally {
      setLlmLoading(false);
    }
  }

  const alertColor = result ? (ALERT_COLOR[result.alert_level] ?? '#64748b') : undefined;

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">{tr('AI 통합 역학 추론', 'AI integrated epidemiological reasoning', 'Raisonnement épidémiologique intégré par IA')}</div>
      <div className="psub">
        {tr('7단계 전체 상황을 FastAPI 추론 엔진(의사결정 트리 + RAG + Meta Model API 우선)으로 종합 분석.', 'Analyses the whole situation across the stages with the FastAPI reasoning engine (decision tree + RAG + Meta Model API first).', 'Analyse l’ensemble de la situation avec le moteur de raisonnement FastAPI (arbre de décision + RAG + Meta Model API en priorité).')}
      </div>
      <LiveObserved stage={7} />

      {/* 요약 카드 */}
      <div className="card">
        <div className="card-h"><span className="lbl">{tr('통합 상황 요약', 'Integrated situation summary', 'Synthèse de la situation')}</span></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 10 }}>
          {summaryItems.map((item, i) => (
            <div key={i} className="oc">
              <div className="ok">{item.label}</div>
              <div className="ov" style={{ fontSize: 14, color: item.color }}>{item.val}</div>
              <div className="od">{item.sub}</div>
            </div>
          ))}
        </div>
      </div>

      {/* AI 추론 */}
      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-h">
          <span className="lbl">{tr('AI 정책 추론', 'AI policy reasoning', 'Raisonnement politique par IA')}</span>
          <button
            onClick={runAI}
            disabled={status === 'loading'}
            style={{
              fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--txt)',
              background: 'rgba(244,63,94,.14)', border: '1px solid var(--accent)',
              borderRadius: 9, padding: '9px 12px', cursor: 'pointer',
            }}
          >
            {status === 'loading' ? tr('추론 중…', 'Reasoning…', 'Raisonnement…') : tr('AI 추론 실행', 'Run AI reasoning', 'Lancer le raisonnement IA')}
          </button>
        </div>

        {status === 'idle' && (
          <div style={{ color: 'var(--muted2)', fontFamily: 'var(--mono)', fontSize: 11.5, textAlign: 'center', padding: '18px 0', lineHeight: 1.6 }}>
            {tr('7단계 전체 신호·예측·대응 효과를 근거로 의사결정 트리 + RAG + LLM(Meta 우선·Claude 폴백)이 통합 정책 권고를 추론합니다.', 'From the signals, forecasts and response effects of all stages, a decision tree + RAG + LLM (Meta first, Claude fallback) reasons out integrated policy recommendations.', 'À partir des signaux, prévisions et effets de réponse de toutes les étapes, un arbre de décision + RAG + LLM (Meta d’abord, Claude en secours) formule des recommandations intégrées.')}
          </div>
        )}

        {status === 'loading' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11.5, padding: '10px 0' }}>
            <div style={{ width: 14, height: 14, border: '2px solid var(--line2)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'sp .8s linear infinite' }} />
            {tr('추론 엔진 분석 중…', 'Reasoning engine analysing…', 'Analyse du moteur en cours…')}
          </div>
        )}

        {status === 'done' && result && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

            {/* 위기경보 배지 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                background: alertColor + '22', border: `1px solid ${alertColor}`,
                borderRadius: 8, padding: '6px 14px', fontFamily: 'var(--mono)', fontSize: 12,
                color: alertColor, fontWeight: 700,
              }}>
                {result.alert_level}
              </div>
              <div style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11 }}>
                {result.mode === 'full_rag_llm' ? `✓ RAG + ${providerLabel(result, tr)} ${tr('분석 완료', 'analysis done', 'analyse terminée')}` :
                  result.mode === 'decision_tree_fast' ? tr('의사결정 트리 즉시 결과 · LLM 분석은 이어서 계산 중', 'Instant decision-tree result · LLM analysis still computing', 'Résultat immédiat de l’arbre · analyse LLM en cours') :
                  result.mode === 'decision_tree_only' ? tr('의사결정 트리 (API 키 없음)', 'Decision tree (no API key)', 'Arbre de décision (pas de clé API)') :
                  tr('의사결정 트리 (LLM 오류 시 대체)', 'Decision tree (fallback after LLM error)', 'Arbre de décision (secours après erreur LLM)')}
              </div>
              {result.cache_hit && (
                <div style={{ color: 'var(--ok)', fontFamily: 'var(--mono)', fontSize: 10, marginLeft: 'auto' }}>
                  ⚡ {tr('캐시 히트', 'cache hit', 'cache utilisé')}
                </div>
              )}
            </div>

            {/* 의사결정 트리 — 우선순위 행동 */}
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--mono)', marginBottom: 8 }}>{tr('우선순위 대응', 'Priority actions', 'Actions prioritaires')}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {result.decision_tree.priority_actions.map((a) => {
                  const uc = URGENCY_COLOR[a.urgency] ?? '#64748b';
                  return (
                    <div key={a.priority} style={{
                      background: 'var(--bg2)', border: '1px solid var(--line2)',
                      borderRadius: 10, padding: '10px 13px',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
                        <span style={{
                          background: 'var(--accent)', color: '#fff', borderRadius: 6,
                          padding: '1px 7px', fontSize: 10, fontFamily: 'var(--mono)',
                        }}>{a.priority}</span>
                        <span style={{ fontSize: 11.5, fontWeight: 600 }}>{a.category}</span>
                        <span style={{
                          marginLeft: 'auto', fontSize: 9.5, fontFamily: 'var(--mono)',
                          color: uc, background: uc + '18', border: `1px solid ${uc}40`,
                          borderRadius: 5, padding: '2px 6px',
                        }}>{a.urgency}</span>
                      </div>
                      <div style={{ fontSize: 12.5, color: 'var(--txt)', marginBottom: 4 }}>{a.action}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.5 }}>{a.rationale}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 의료 경고 */}
            {result.decision_tree.medical_warning && (
              <div style={{
                background: 'rgba(251,146,60,.08)', border: '1px solid rgba(251,146,60,.4)',
                borderRadius: 9, padding: '9px 13px', fontSize: 12, color: '#fb923c', lineHeight: 1.5,
              }}>
                {result.decision_tree.medical_warning}
              </div>
            )}

            {/* LLM 분석 — 누가 썼는지 표시 */}
            {llmLoading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11.5 }}>
                <div style={{ width: 14, height: 14, border: '2px solid var(--line2)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'sp .8s linear infinite' }} />
                {tr('LLM 정책 분석 계산 중… (Meta 추론 모델 실측 60~120초 — 위 의사결정 트리는 지금 바로 쓸 수 있음)', 'Computing LLM policy analysis… (Meta reasoning model measured at 60–120 s; the decision tree above is usable now)', 'Analyse LLM en cours… (modèle Meta mesuré à 60–120 s ; l’arbre de décision ci-dessus est déjà utilisable)')}
              </div>
            )}
            {llmError && (
              <div style={{ fontSize: 11.5, color: '#fb923c', fontFamily: 'var(--mono)' }}>
                {tr('LLM 분석을 받지 못함', 'LLM analysis not received', 'Analyse LLM non reçue')} — {llmError} · {tr('위 의사결정 트리 결과는 유효함', 'the decision-tree result above is still valid', 'le résultat de l’arbre ci-dessus reste valable')}
              </div>
            )}
            {result.llm_analysis ? (
              <div>
                <div style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--mono)', marginBottom: 8 }}>{providerLabel(result, tr)} {tr('통합 분석', 'integrated analysis', 'analyse intégrée')}{ageLabel(result, tr)}</div>
                <div style={{ fontSize: 13, lineHeight: 1.75, whiteSpace: 'pre-wrap', color: '#dfe6ef' }}>
                  {result.llm_analysis}
                </div>
                {result.usage && (
                  <div style={{ marginTop: 8, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}>
                    {tr('입력', 'in', 'entrée')} {nf(result.usage.input_tokens)}t · {tr('출력', 'out', 'sortie')} {nf(result.usage.output_tokens)}t
                    {result.usage.cache_read_tokens > 0 && ` · ${tr('캐시 절감', 'cache saved', 'économie cache')} ${nf(result.usage.cache_read_tokens)}t`}
                  </div>
                )}
              </div>
            ) : result.note ? (
              <div style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11, lineHeight: 1.6, textAlign: 'center', padding: '6px 0' }}>
                {result.note}
              </div>
            ) : null}
          </div>
        )}

        {status === 'error' && (
          <div style={{ color: '#fca5a5', fontSize: 11.5, lineHeight: 1.6, background: 'rgba(239,68,68,.08)', border: '1px solid rgba(239,68,68,.4)', borderRadius: 10, padding: '11px 13px' }}>
                <b>{tr('추론 엔진 호출 실패.', 'Reasoning engine call failed.', 'Échec de l’appel au moteur de raisonnement.')}</b><br />{errMsg}<br /><br />
                {tr('FastAPI 서버(포트 8000)가 실행 중인지 확인하세요.', 'Check that the FastAPI server (port 8000) is running.', 'Vérifiez que le serveur FastAPI (port 8000) fonctionne.')}
          </div>
        )}
      </div>
    </div>
  );
}
