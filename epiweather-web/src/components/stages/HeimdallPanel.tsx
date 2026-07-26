'use client';
import { useState } from 'react';
import { fetchGenomeScreen, GenomeScreen } from '@/lib/api';
import ClassifiedBadge from './ClassifiedBadge';

// HEIMDALL 실측 패널 — 백엔드 유전체 스크리너(genome_signals) 호출·렌더.
// 서열 하나를 넣으면 CAI·CpG·엔트로피·국소이상·조립시그니처를 서버에서 실제 계산.
const SAMPLE = 'ATGTTTGTTTTTCTTGTTTTATTGCCACTAGTCTCTAGTCAGTGTGTTAATCTTACAACCAGAACTCAATTACCCCCTGCATAC';

export default function HeimdallPanel() {
  const [seq, setSeq] = useState(SAMPLE);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [r, setR] = useState<GenomeScreen | null>(null);

  async function run() {
    setBusy(true); setErr(null); setR(null);
    try { setR(await fetchGenomeScreen(seq)); }
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
