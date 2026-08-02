'use client';
import { useState } from 'react';
import { fetchGenomeScreen, GenomeScreen } from '@/lib/api';
import ClassifiedBadge from './ClassifiedBadge';

// HEIMDALL 실측 패널 — 백엔드 유전체 스크리너(genome_signals) 호출·렌더.
// 서열 하나를 넣으면 CAI·CpG·엔트로피·국소이상·조립시그니처를 서버에서 실제 계산.
const SAMPLE = 'ATGTTTGTTTTTCTTGTTTTATTGCCACTAGTCTCTAGTCAGTGTGTTAATCTTACAACCAGAACTCAATTACCCCCTGCATAC';

export default function HeimdallPanel() {
  const [seq, setSeq] = useState(SAMPLE);
  const [refSeqText, setRefSeqText] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [r, setR] = useState<GenomeScreen | null>(null);
  const [useMsa, setUseMsa] = useState(false);
  const [useEvo2, setUseEvo2] = useState(false);
  const [domain, setDomain] = useState('unknown');

  async function run() {
    setBusy(true); setErr(null); setR(null);
    const refs = refSeqText.split(/\n+/).map(s => s.trim()).filter(Boolean);
    try {
      setR(await fetchGenomeScreen(seq, {
        referenceSequences: refs, useEvo2, useMsa, organismDomain: domain,
      }));
    }
    catch (e) { setErr(String(e)); }
    finally { setBusy(false); }
  }

  return (
    <div className="card" style={{ marginTop: 14 }}>
      <ClassifiedBadge c={r?.classification} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.14em', color: 'var(--violet)' }}>
          HEIMDALL · 유전체 실측 스크리닝
        </span>
        <span style={{ fontFamily: 'var(--kr)', fontSize: 10.5, color: 'var(--muted2)' }}>
          (백엔드 실계산 — 판정 아닌 우선순위)
        </span>
      </div>

      <textarea value={seq} onChange={e => setSeq(e.target.value)} rows={3}
        spellCheck={false}
        style={{
          width: '100%', fontFamily: 'var(--mono)', fontSize: 11, lineHeight: 1.5,
          background: 'var(--panel2)', color: 'var(--txt)', border: '1px solid var(--line2)',
          borderRadius: 8, padding: 10, resize: 'vertical',
        }} />

      <div style={{ marginTop: 8 }}>
        <div style={{ fontFamily: 'var(--kr)', fontSize: 10.5, color: 'var(--muted2)', marginBottom: 4 }}>
          레퍼런스 서열(선택) — 같은 계통의 실제 공개 자연서열을 한 줄에 하나씩(3개 이상 권장). 넣으면 임의 임계값 대신 실측 z-score·백분위를 함께 계산.
        </div>
        <textarea value={refSeqText} onChange={e => setRefSeqText(e.target.value)} rows={2}
          spellCheck={false} placeholder={"서열1\n서열2\n서열3..."}
          style={{
            width: '100%', fontFamily: 'var(--mono)', fontSize: 10.5, lineHeight: 1.5,
            background: 'var(--panel2)', color: 'var(--txt)', border: '1px solid var(--line2)',
            borderRadius: 8, padding: 8, resize: 'vertical',
          }} />
      </div>

      <div style={{ marginTop: 10, padding: '10px 12px', borderRadius: 8,
                    background: 'var(--panel2)', border: '1px solid var(--line2)' }}>
        <div style={{ fontFamily: 'var(--kr)', fontSize: 10.5, color: 'var(--muted2)', marginBottom: 6 }}>
          심화 분석(선택) — 외부 모델을 호출하므로 수십 초 더 걸립니다.
        </div>
        <label style={{ display: 'flex', gap: 7, alignItems: 'flex-start', cursor: 'pointer', marginBottom: 7 }}>
          <input type="checkbox" checked={useMsa} onChange={e => setUseMsa(e.target.checked)}
                 style={{ marginTop: 2 }} />
          <span style={{ fontFamily: 'var(--kr)', fontSize: 11, color: 'var(--txt)' }}>
            상동성 커버리지<span style={{ color: '#34d399' }}> · 바이러스에도 유효</span>
            <span style={{ display: 'block', fontSize: 10, color: 'var(--muted2)', marginTop: 1 }}>
              자연계에 이 서열 전체를 설명하는 단백질이 있는지 검색. 없으면 여러 출처를 이어붙인 재조합 후보.
            </span>
          </span>
        </label>
        <label style={{ display: 'flex', gap: 7, alignItems: 'flex-start', cursor: 'pointer' }}>
          <input type="checkbox" checked={useEvo2} onChange={e => setUseEvo2(e.target.checked)}
                 style={{ marginTop: 2 }} />
          <span style={{ fontFamily: 'var(--kr)', fontSize: 11, color: 'var(--txt)' }}>
            Evo2 순서 자연스러움
            <span style={{ display: 'block', fontSize: 10, color: 'var(--muted2)', marginTop: 1 }}>
              세균·고균·진핵·파지에만 유효. 코로나·독감·에볼라 등 진핵숙주 감염 바이러스는 모델 학습에서
              제외돼 판정 불가(점수만 참고로 표시, 플래그 안 올림).
            </span>
          </span>
        </label>
        {useEvo2 && (
          <div style={{ marginTop: 8, display: 'flex', gap: 7, alignItems: 'center' }}>
            <span style={{ fontFamily: 'var(--kr)', fontSize: 10.5, color: 'var(--muted2)' }}>분류군</span>
            <select value={domain} onChange={e => setDomain(e.target.value)}
              style={{ fontFamily: 'var(--kr)', fontSize: 11, background: 'var(--panel)',
                       color: 'var(--txt)', border: '1px solid var(--line2)',
                       borderRadius: 6, padding: '4px 8px' }}>
              <option value="unknown">미선언 — 안전하게 플래그 억제</option>
              <option value="bacteria_archaea">세균·고균 (탄저·페스트·야토병 등)</option>
              <option value="eukaryote">진핵 유전체</option>
              <option value="phage">파지 (세균 감염 바이러스)</option>
              <option value="eukaryotic_virus">진핵숙주 감염 바이러스 — 판정 불가</option>
            </select>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <button onClick={run} disabled={busy} style={{
          cursor: busy ? 'default' : 'pointer', fontFamily: 'var(--kr)', fontWeight: 700, fontSize: 12,
          color: '#fff', background: busy ? 'var(--muted2)' : 'linear-gradient(135deg,#8b5cf6,#6d28d9)',
          border: 'none', borderRadius: 8, padding: '9px 18px',
        }}>{busy ? '스크리닝 중…' : '스크리닝 실행'}</button>
        {err && <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#f43f5e', alignSelf: 'center' }}>
          {err.includes('503') ? '인증 필요(API 키 미설정)' : err}
        </span>}
      </div>

      {r?.ok && (
        <div style={{ marginTop: 14 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(120px,1fr))', gap: 8 }}>
            <Metric label="GC 함량" v={fmt(r.gc_content)} />
            <Metric label="Shannon 엔트로피" v={`${fmt(r.shannon_entropy_bits)} bit`} />
            <Metric label="CpG O/E" v={fmt(r.cpg_observed_expected)} warn={r.cpg_observed_expected != null && r.cpg_observed_expected < 0.2} />
            <Metric label="CAI(인간)" v={r.cai_human ? fmt(r.cai_human.cai) : '—'} />
            <Metric label="국소 조성 이상" v={`${r.window_composition_anomaly?.anomaly_count ?? 0}구간`} warn={(r.window_composition_anomaly?.anomaly_count ?? 0) > 0} />
            <Metric label="조립 시그니처" v={r.restriction_even_spacing?.even_spacing_flagged.length ? r.restriction_even_spacing.even_spacing_flagged.join(',') : '없음'} warn={!!r.restriction_even_spacing?.even_spacing_flagged.length} />
          </div>

          {r.cai_human?.orf_used && (
            <div style={{ marginTop: 8, fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--muted2)' }}>
              CAI는 원본 프레임이 안 맞아 자동탐지한 ORF({r.cai_human.orf_used.strand}가닥, 프레임 {r.cai_human.orf_used.frame}, {r.cai_human.orf_used.length}nt)로 계산됨
            </div>
          )}
          {r.segments_note && (
            <div style={{ marginTop: 8, fontFamily: 'var(--kr)', fontSize: 10.5, color: '#fbbf24' }}>
              ⓘ {r.segments_note} (모호 염기 {r.ambiguous_bases_removed}개 제외, 분석 구간 {r.analyzed_segment_length}nt)
            </div>
          )}

          {r.reference_comparison && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted2)', letterSpacing: '.08em', marginBottom: 6 }}>
                레퍼런스 실측 비교 (n={r.reference_comparison.n_reference_sequences})
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(130px,1fr))', gap: 8 }}>
                {(['gc_content', 'shannon_entropy_bits', 'cpg_observed_expected'] as const).map(k => {
                  const m = r.reference_comparison?.[k];
                  if (!m) return null;
                  const label = k === 'gc_content' ? 'GC 함량' : k === 'shannon_entropy_bits' ? '엔트로피' : 'CpG O/E';
                  return (
                    <div key={k} style={{ background: 'var(--panel2)', border: '1px solid var(--line)', borderRadius: 8, padding: '9px 11px' }}>
                      <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)' }}>{label} · z-score</div>
                      <div style={{ fontFamily: 'var(--mono)', fontWeight: 800, fontSize: 15 }}>{m.z_score}</div>
                      <div style={{ fontFamily: 'var(--kr)', fontSize: 10, color: 'var(--muted2)' }}>백분위 {m.percentile}%</div>
                    </div>
                  );
                })}
              </div>
              <div style={{ marginTop: 6, fontFamily: 'var(--kr)', fontSize: 10, color: 'var(--muted2)' }}>
                {r.reference_comparison.note}
              </div>
            </div>
          )}

          {r.msa_homology && (
            <div style={{ marginTop: 12, padding: '10px 12px', borderRadius: 8,
                          background: 'rgba(52,211,153,.06)', border: '1px solid rgba(52,211,153,.25)' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: '#34d399', marginBottom: 6 }}>
                상동성 커버리지 · 자연계에 전체를 설명하는 단백질이 있는가
              </div>
              {r.msa_homology.ok ? (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(110px,1fr))', gap: 8 }}>
                    <Metric label="최고 커버리지" v={pct(r.msa_homology.best_coverage)}
                      warn={(r.msa_homology.best_coverage ?? 1) < 0.9} />
                    <Metric label="상동체 히트" v={`${r.msa_homology.total_hits ?? 0}건`}
                      warn={(r.msa_homology.total_hits ?? 0) === 0} />
                    <Metric label="번역 단백질" v={`${r.msa_homology.protein_length_aa ?? '—'} aa`} />
                  </div>
                  <div style={{ marginTop: 6, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}>
                    자연 단백질 실측 99.8% / 키메라 실측 최대 74.8% — 90% 미만이면 재조합 후보
                  </div>
                  {r.msa_homology.top_hits && r.msa_homology.top_hits.length > 0 && (
                    <div style={{ marginTop: 6, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)' }}>
                      최상위: {r.msa_homology.top_hits[0].id} ({r.msa_homology.top_hits[0].database}) 동일도 {r.msa_homology.top_hits[0].identity}
                    </div>
                  )}
                </>
              ) : (
                <div style={{ fontFamily: 'var(--kr)', fontSize: 11, color: 'var(--muted2)' }}>
                  {r.msa_homology.reason}
                </div>
              )}
            </div>
          )}

          {r.evo2_naturalness && (
            <div style={{ marginTop: 12, padding: '10px 12px', borderRadius: 8,
                          background: 'var(--panel2)', border: '1px solid var(--line2)' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--violet)', marginBottom: 6 }}>
                Evo2 · 순서의 자연스러움
              </div>
              {r.evo2_naturalness.ok ? (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(110px,1fr))', gap: 8 }}>
                    <Metric label="예측 일치율" v={pct(r.evo2_naturalness.match_rate)} />
                    <Metric label="평균 확신도" v={fmt(r.evo2_naturalness.mean_confidence)} />
                    <Metric label="국소 이상"
                      v={`${r.evo2_naturalness.local_anomaly_positions?.length ?? 0}구간`}
                      warn={!!r.evo2_naturalness.local_anomaly_positions?.length} />
                  </div>
                  {r.evo2_naturalness.suppressed_flags && (
                    <div style={{ marginTop: 8, fontFamily: 'var(--kr)', fontSize: 10.5, color: '#fbbf24',
                                  lineHeight: 1.6 }}>
                      ⓘ {r.evo2_naturalness.suppressed_flags}
                    </div>
                  )}
                </>
              ) : (
                <div style={{ fontFamily: 'var(--kr)', fontSize: 11, color: 'var(--muted2)' }}>
                  {r.evo2_naturalness.reason}
                </div>
              )}
            </div>
          )}

          {r.flags && r.flags.length > 0 && (
            <div style={{ marginTop: 10 }}>
              {r.flags.map((f, i) => (
                <div key={i} style={{
                  fontFamily: 'var(--kr)', fontSize: 11.5, color: '#fb923c',
                  padding: '6px 10px', marginTop: 4, borderRadius: 7,
                  background: 'rgba(251,146,60,.08)', border: '1px solid rgba(251,146,60,.25)',
                }}>⚠ {f.note}</div>
              ))}
            </div>
          )}

          <div style={{ marginTop: 10, fontFamily: 'var(--kr)', fontSize: 10.5, color: 'var(--muted2)', lineHeight: 1.6 }}>
            {r.disclaimer}
          </div>
        </div>
      )}
      {r && !r.ok && (
        <div style={{ marginTop: 12, fontFamily: 'var(--kr)', fontSize: 12, color: 'var(--muted)' }}>
          {r.reason}
        </div>
      )}
    </div>
  );
}

function Metric({ label, v, warn = false }: { label: string; v: string; warn?: boolean }) {
  return (
    <div style={{
      background: 'var(--panel2)', border: `1px solid ${warn ? 'rgba(251,146,60,.4)' : 'var(--line)'}`,
      borderRadius: 8, padding: '10px 12px',
    }}>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted2)', letterSpacing: '.04em' }}>{label}</div>
      <div style={{ fontFamily: 'var(--mono)', fontWeight: 800, fontSize: 16, marginTop: 4, color: warn ? '#fb923c' : 'var(--txt)' }}>{v}</div>
    </div>
  );
}

function fmt(n?: number | null): string {
  return n == null ? '—' : String(n);
}

function pct(n?: number | null): string {
  return n == null ? '—' : `${(n * 100).toFixed(1)}%`;
}
