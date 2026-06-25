'use client';
import { useState } from 'react';
import { useStore } from '@/lib/store';
import { THREAT, CIVIC, currentRt } from '@/lib/algorithms';

const API = 'http://localhost:8000';

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
  note?: string;
  error?: string;
  cache_hit?: boolean;
  usage?: { input_tokens: number; output_tokens: number; cache_creation_tokens: number; cache_read_tokens: number };
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
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [result, setResult] = useState<InferResponse | null>(null);
  const [errMsg, setErrMsg] = useState('');

  if (!pz || !glob || !def || !def0) return null;

  const sp = THREAT[threat];
  const civicLead = Math.max(...CIVIC.filter(s => civicOn[s.id]).map(s => s.lead), 0);
  const rt = currentRt(lev, threat);

  const summaryItems = [
    { label: '발원지 추적', val: `격자(${pz.top.r},${pz.top.c})`, sub: `${(pz.top.prob * 100).toFixed(1)}% 확률` },
    { label: '민간 선행', val: `D−${civicLead}일`, sub: '정부 대비', color: 'var(--violet)' },
    { label: '한국 유입', val: `D+${glob.arrival}`, sub: `${glob.city.nm}발` },
    { label: '위협', val: sp.nm, sub: `R₀ ${sp.R0}` },
    { label: '방어 효과', val: `${savedLives.toLocaleString()}명`, sub: '구한 생명', color: 'var(--ok)' },
    { label: 'Rt', val: rt.toFixed(2), sub: rt < 1 ? '차단' : '억제', color: rt < 1 ? 'var(--ok)' : '#fb923c' },
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

    try {
      const res = await fetch(`${API}/api/ai/infer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
      const data: InferResponse = await res.json();
      setResult(data);
      setStatus('done');
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : String(e));
      setStatus('error');
    }
  }

  const alertColor = result ? (ALERT_COLOR[result.alert_level] ?? '#64748b') : undefined;

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">AI 통합 역학 추론</div>
      <div className="psub">
        7단계 전체 상황을 FastAPI 추론 엔진(의사결정 트리 + RAG + Claude)으로 종합 분석.
      </div>

      {/* 요약 카드 */}
      <div className="card">
        <div className="card-h"><span className="lbl">통합 상황 요약</span></div>
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
          <span className="lbl">AI 정책 추론</span>
          <button
            onClick={runAI}
            disabled={status === 'loading'}
            style={{
              fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--txt)',
              background: 'rgba(244,63,94,.14)', border: '1px solid var(--accent)',
              borderRadius: 9, padding: '9px 12px', cursor: 'pointer',
            }}
          >
            {status === 'loading' ? '추론 중…' : 'AI 추론 실행'}
          </button>
        </div>

        {status === 'idle' && (
          <div style={{ color: 'var(--muted2)', fontFamily: 'var(--mono)', fontSize: 11.5, textAlign: 'center', padding: '18px 0', lineHeight: 1.6 }}>
            7단계 전체 신호·예측·대응 효과를 근거로<br />의사결정 트리 + Claude RAG가 통합 정책 권고를 추론합니다.
          </div>
        )}

        {status === 'loading' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11.5, padding: '10px 0' }}>
            <div style={{ width: 14, height: 14, border: '2px solid var(--line2)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'sp .8s linear infinite' }} />
            추론 엔진 분석 중…
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
                {result.mode === 'full_rag_llm' ? '✓ RAG + Claude 분석 완료' :
                 result.mode === 'decision_tree_only' ? '의사결정 트리 (API 키 없음)' :
                 '의사결정 트리 (LLM 오류 시 대체)'}
              </div>
              {result.cache_hit && (
                <div style={{ color: 'var(--ok)', fontFamily: 'var(--mono)', fontSize: 10, marginLeft: 'auto' }}>
                  ⚡ 캐시 히트
                </div>
              )}
            </div>

            {/* 의사결정 트리 — 우선순위 행동 */}
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--mono)', marginBottom: 8 }}>우선순위 대응</div>
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

            {/* Claude LLM 분석 */}
            {result.llm_analysis ? (
              <div>
                <div style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--mono)', marginBottom: 8 }}>Claude 통합 분석</div>
                <div style={{ fontSize: 13, lineHeight: 1.75, whiteSpace: 'pre-wrap', color: '#dfe6ef' }}>
                  {result.llm_analysis}
                </div>
                {result.usage && (
                  <div style={{ marginTop: 8, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}>
                    입력 {result.usage.input_tokens.toLocaleString()}t · 출력 {result.usage.output_tokens.toLocaleString()}t
                    {result.usage.cache_read_tokens > 0 && ` · 캐시 절감 ${result.usage.cache_read_tokens.toLocaleString()}t`}
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
            <b>추론 엔진 호출 실패.</b><br />{errMsg}<br /><br />
            FastAPI 서버(포트 8000)가 실행 중인지 확인하세요.
          </div>
        )}
      </div>
    </div>
  );
}
