'use client';
import { useState } from 'react';
import {
  pOrigin, pRate, pDens,
  fisherCombine, calcCI, threatColor, threatLabel,
  fetchNCBI, fetchPubMed, fetchBioRxiv, fetchWHO,
  NCBIResult, PubMedPaper, BioRxivPaper, WHOItem,
} from '@/lib/syntheticThreat';
import { fetchGenomeScreen } from '@/lib/api';
import HeimdallPanel from './HeimdallPanel';
import LiveObserved from './LiveObserved';
import { useT } from '@/lib/dashLang';

interface ScanResult {
  total: number; ci: { lo: number; hi: number };
  gScore: number; eScore: number; intelScore: number;
  /** 서버 실측값 — null이면 서버가 못 잼(비코딩 등). 프론트 자가계산 금지. */
  cai: number | null; cpgR: number | null; ent: number | null; gc: number | null;
  gPs: number[];
  genomeFlags: { metric: string; note: string }[];
  originCount: number; spreadRate: number; densCorr: number;
  ncbi: NCBIResult; pubmed: PubMedPaper[]; biorxiv: BioRxivPaper[]; who: WHOItem[];
}

export default function Stage0Synthetic() {
  const [acc, setAcc] = useState('MN908947');
  const [origins, setOrigins] = useState('1');
  const [day7, setDay7] = useState('22');
  const [day1, setDay1] = useState('1');
  const [dens, setDens] = useState('0.82');
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [scanErr, setScanErr] = useState('');
  const [aiStatus, setAiStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [aiText, setAiText] = useState('');
  const [aiProv, setAiProv] = useState('');
  const tr = useT();

  async function runScan() {
    setScanning(true);
    setResult(null);
    setAiStatus('idle');
    setScanErr('');

    try {
    const originCount = Math.max(1, parseInt(origins) || 1);
    const d7 = Math.max(1, parseInt(day7) || 22);
    const d1 = Math.max(1, parseInt(day1) || 1);
    const densCorr = Math.min(1, Math.max(0, parseFloat(dens) || 0.82));
    const spreadRate = d7 / d1;
    const accession = acc.trim() || 'MN908947';

    const [ncbi, pubmed, biorxiv, who] = await Promise.all([
      fetchNCBI(accession), fetchPubMed(), fetchBioRxiv(), fetchWHO(),
    ]);

    // ★ 유전체 4지표는 서버 실측 단일 진실원천 ★ 예전엔 프론트가 코돈-엔트로피를
    // 자체 계산했는데 서버(뉴클레오타이드 Shannon)와 정의가 달라 같은 서열이 두 값이
    // 됐다. 이제 genome-screen을 불러 값도 p도 서버 판정에서만 낸다. CAI·GC는
    // 서버에 참고범위가 없어 중립(0.7)으로 두고 그 사실을 적는다 — 임계 날조 금지.
    // Evo2·MSA는 느려서 스캔에 안 넣는다(아래 HEIMDALL 패널에서 선택 실행).
    const seq = ncbi.seq || 'ATGGAGAGCCTTGTCCCTGGT';
    const screen = await fetchGenomeScreen(seq);
    if (!screen.ok) throw new Error(screen.reason || tr('유전체 스크리닝 실패', 'Genome screening failed', 'Échec du criblage génomique'));
    const flagged = new Set((screen.flags ?? []).map(f => f.metric));
    const cai = screen.cai_human?.cai ?? null;
    const cpgR = screen.cpg_observed_expected ?? null;
    const ent = screen.shannon_entropy_bits ?? null;
    const gc = screen.gc_content ?? null;
    const gPs = [
      0.7,
      flagged.has('cpg_oe') ? 0.01 : 0.7,
      flagged.has('shannon_entropy') ? 0.01 : 0.7,
      0.7,
    ];
    const genomeFlags = screen.flags ?? [];
    const gScore = fisherCombine(gPs);

    const ePs = [pOrigin(originCount), pRate(spreadRate), pDens(densCorr)];
    const eScore = fisherCombine(ePs);

    const pmScore = Math.min(80, pubmed.length * 14 + (pubmed[0]?.source === 'PubMed_REAL' ? 10 : 0));
    const bxScore = Math.min(70, biorxiv.length * 12 + (biorxiv[0]?.source === 'bioRxiv_REAL' ? 12 : 0));
    const whoScore = Math.max(...who.map(w => w.risk || 0));
    const intelPsRaw = [0.001 + pmScore / 110, 0.001 + bxScore / 110, 0.001 + whoScore / 110].map(p => Math.min(0.9, p));
    const intelScore = fisherCombine(intelPsRaw);

    const total = fisherCombine([...gPs, ...ePs, ...intelPsRaw]);
    const ci = calcCI(total, gPs.length + ePs.length + intelPsRaw.length);

    setResult({ total, ci, gScore, eScore, intelScore, cai, cpgR, ent, gc, gPs, genomeFlags, originCount, spreadRate, densCorr, ncbi, pubmed, biorxiv, who });
    } catch (e) {
      setScanErr(e instanceof Error ? e.message : String(e));
    } finally {
      setScanning(false);
    }
  }

  async function runAI() {
    if (!result) return;
    setAiStatus('loading');
    setAiProv('');
    try {
      const summary = {
        종합: result.total, CI: result.ci,
        유전체: { CAI: result.cai, CpG억제비율: result.cpgR, 엔트로피: result.ent, GC: result.gc, 점수: result.gScore },
        역학: { 발원지: result.originCount, 전파율: +result.spreadRate.toFixed(1), 밀도상관: result.densCorr, 점수: result.eScore },
        인텔: { PubMed건수: result.pubmed.length, 점수: result.intelScore },
        접근번호: result.ncbi.acc,
      };
      const res = await fetch('/api/synthetic-threat/analyze', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary }),
      });
      if (!res.ok) {
        let detail = '';
        try { detail = (await res.json()).detail || ''; } catch { /* 본문 없음 */ }
        throw new Error(`${tr('서버 오류', 'Server error', 'Erreur serveur')} (${res.status})${detail ? ' — ' + detail.slice(0, 140) : ''}`);
      }
      const data = await res.json();
      setAiText(data.analysis);
      const _t = (data.timings_ms || {}) as Record<string, number>;
      const _ms = (_t.claude_ms || 0) + (_t.meta_ms || 0);
      const _prov = data.llm_provider === 'meta_model_api' ? ('Meta ' + (data.llm_model || '')) : (data.llm_provider || '');
      setAiProv(_prov + (_ms ? ` · ${(_ms / 1000).toFixed(1)}${tr('초', 's', ' s')}` : ''));
      setAiStatus('done');
    } catch (e) {
      setAiText(e instanceof Error ? e.message : String(e));
      setAiStatus('error');
    }
  }

  const c = result ? threatColor(result.total) : 'var(--muted)';

  const flaggedMetrics = new Set((result?.genomeFlags ?? []).map(f => f.metric));
  const sevenSignals = result ? [
    { lbl: 'CAI', val: result.cai == null ? '—' : result.cai.toFixed(3), note: result.cai == null ? tr('비코딩(판정 없음)', 'non-coding (no judgement)', 'non codant (pas de jugement)') : tr('서버 참고범위 없음', 'no server reference range', 'pas de plage de référence serveur'), sc: result.gPs[0] },
    { lbl: tr('CpG 억제', 'CpG suppression', 'Suppression CpG'), val: result.cpgR == null ? '—' : result.cpgR.toFixed(3), note: flaggedMetrics.has('cpg_oe') ? tr('극단적 억제 ⚠', 'extreme suppression ⚠', 'suppression extrême ⚠') : tr('정상', 'normal', 'normal'), sc: result.gPs[1] },
    { lbl: tr('엔트로피', 'Entropy', 'Entropie'), val: result.ent == null ? '—' : result.ent.toFixed(2), note: flaggedMetrics.has('shannon_entropy') ? tr('저복잡도 ⚠', 'low complexity ⚠', 'faible complexité ⚠') : tr('자연', 'natural', 'naturel'), sc: result.gPs[2] },
    { lbl: tr('GC 편향', 'GC bias', 'Biais GC'), val: result.gc == null ? '—' : (result.gc * 100).toFixed(0) + '%', note: tr('서버 참고범위 없음', 'no server reference range', 'pas de plage de référence serveur'), sc: result.gPs[3] },
  ] : [];

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">{tr('합성위협 탐지 엔진', 'Synthetic threat detection engine', 'Moteur de détection des menaces synthétiques')}</div>
      <div className="psub">
        {tr('진단 이전, 설계-탐지 이중성 원리로 유전체·역학·인텔 7신호를 Fisher 결합해 합성/자연 기원을 가른다.',
          'Before diagnosis, using the design–detection duality, it combines seven genomic, epidemiological and intelligence signals with Fisher’s method to separate synthetic from natural origin.',
          'Avant le diagnostic, selon la dualité conception–détection, il combine sept signaux génomiques, épidémiologiques et de renseignement par la méthode de Fisher pour distinguer origine synthétique et naturelle.')}
      </div>
      <LiveObserved stage={0} />

      {/* HEIMDALL 실측 스크리닝 — 백엔드 genome_signals 실계산 */}
      <HeimdallPanel />

      {/* 입력 바 */}
      <div className="card" style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)' }}>{tr('GENBANK 접근번호', 'GENBANK accession', 'Numéro d’accès GENBANK')}</span>
          <input value={acc} onChange={e => setAcc(e.target.value)} placeholder="MN908947"
            style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--txt)', background: 'var(--bg2)', border: '1px solid var(--line2)', borderRadius: 7, padding: '7px 11px', width: 130, outline: 'none' }} />
        </div>
        {[
          { lbl: tr('발원지 수', 'Origins', 'Origines'), v: origins, set: setOrigins, w: 70 },
          { lbl: tr('D+7 환자', 'Cases D+7', 'Cas J+7'), v: day7, set: setDay7, w: 70 },
          { lbl: tr('D+1 환자', 'Cases D+1', 'Cas J+1'), v: day1, set: setDay1, w: 70 },
          { lbl: tr('밀도상관', 'Density corr.', 'Corr. densité'), v: dens, set: setDens, w: 70 },
        ].map((f, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)' }}>{f.lbl}</span>
            <input value={f.v} onChange={e => f.set(e.target.value)}
              style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--txt)', background: 'var(--bg2)', border: '1px solid var(--line2)', borderRadius: 7, padding: '7px 9px', width: f.w, outline: 'none' }} />
          </div>
        ))}
        <button onClick={runScan} disabled={scanning}
          style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#fff', background: scanning ? 'var(--muted2)' : 'var(--accent)', border: 'none', borderRadius: 7, padding: '9px 16px', cursor: scanning ? 'wait' : 'pointer', fontWeight: 700 }}>
          {scanning ? tr('스캔 중…', 'Scanning…', 'Analyse…') : tr('▶ 전체 스캔', '▶ Full scan', '▶ Analyse complète')}
        </button>
      </div>

      {scanErr && !scanning && (
        <div className="card" style={{ marginTop: 12, color: '#ff8080', fontFamily: 'var(--mono)', fontSize: 11, padding: '14px 12px' }}>
          {tr('스캔 실패', 'Scan failed', 'Échec de l’analyse')}: {scanErr} — {tr('유전체 지표는 서버 실측만 쓰므로 프론트 계산으로 대체하지 않습니다.', 'Genomic metrics come only from server measurements, so they are not replaced by browser calculations.', 'Les indicateurs génomiques proviennent uniquement des mesures du serveur ; ils ne sont pas remplacés par un calcul dans le navigateur.')}
        </div>
      )}
      {!result && !scanning && !scanErr && (
        <div className="card" style={{ marginTop: 12, textAlign: 'center', color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11, padding: '24px 0' }}>
          {tr('GenBank 접근번호와 역학 파라미터를 입력하고 전체 스캔을 실행하세요.', 'Enter a GenBank accession and epidemiological parameters, then run a full scan.', 'Saisissez un numéro GenBank et des paramètres épidémiologiques, puis lancez l’analyse complète.')}
        </div>
      )}
      {scanning && (
        <div className="card" style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10, color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11, padding: '14px 0', justifyContent: 'center' }}>
          <div style={{ width: 14, height: 14, border: '2px solid var(--line2)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'sp .8s linear infinite' }} />
          {tr('NCBI·PubMed·bioRxiv 병렬 스캔 중…', 'Scanning NCBI · PubMed · bioRxiv in parallel…', 'Analyse parallèle NCBI · PubMed · bioRxiv…')}
        </div>
      )}

      {result && (<>
        {/* 7신호 그리드 */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 8, marginTop: 14 }}>
          {sevenSignals.map((s, i) => (
            <div key={i} className="oc">
              <div className="ok">{s.lbl}</div>
              <div className="ov" style={{ fontSize: 15, color: s.sc < 0.05 ? '#ff2d55' : s.sc < 0.2 ? '#ffcc00' : '#00ff88' }}>{s.val}</div>
              <div className="od">{s.note}</div>
            </div>
          ))}
          <div className="oc">
            <div className="ok">{tr('역학 이상', 'Epidemiological anomaly', 'Anomalie épidémiologique')}</div>
            <div className="ov" style={{ fontSize: 15, color: threatColor(result.eScore) }}>{result.eScore}</div>
            <div className="od">{result.eScore > 70 ? tr('비자연 패턴', 'unnatural pattern', 'schéma non naturel') : result.eScore > 40 ? tr('경계', 'borderline', 'limite') : tr('자연', 'natural', 'naturel')}</div>
          </div>
          <div className="oc">
            <div className="ok">{tr('바이오안보', 'Biosecurity', 'Biosécurité')}</div>
            <div className="ov" style={{ fontSize: 15, color: threatColor(result.intelScore) }}>{result.intelScore}</div>
            <div className="od">{tr(`논문 ${result.pubmed.length}건`, `${result.pubmed.length} papers`, `${result.pubmed.length} articles`)}</div>
          </div>
          <div className="oc" style={{ borderColor: 'rgba(244,63,94,.4)' }}>
            <div className="ok">{tr('종합 Fisher', 'Combined Fisher', 'Fisher combiné')}</div>
            <div className="ov" style={{ fontSize: 18, color: c }}>{result.total}</div>
            <div className="od">95% CI [{result.ci.lo}, {result.ci.hi}]</div>
          </div>
        </div>

        <div className="grid2" style={{ marginTop: 14 }}>
          {/* 좌: 유전체+역학 */}
          <div>
            <div className="card">
              <div className="card-h"><span className="lbl">{tr('유전체 분석 (4신호 · 서버 실측)', 'Genomic analysis (4 signals · server-measured)', 'Analyse génomique (4 signaux · mesurés par le serveur)')}</span><span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--cold,#00c8ff)' }}>{result.ncbi.acc} · {result.ncbi.seq.length}bp · {result.ncbi.source === 'NCBI_REAL' ? tr('실시간', 'live', 'en direct') : tr('폴백', 'fallback', 'secours')}</span></div>
              {result.genomeFlags.filter(f => !['cpg_oe', 'shannon_entropy'].includes(f.metric)).map((f, i) => (
                <div key={i} style={{ fontFamily: 'var(--kr)', fontSize: 10.5, color: '#fb923c', padding: '6px 10px', marginBottom: 6, borderRadius: 7, background: 'rgba(251,146,60,.08)', border: '1px solid rgba(251,146,60,.25)' }}>⚠ {f.note}</div>
              ))}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                {sevenSignals.map((s, i) => {
                  const pc = s.sc < 0.01 ? '#ff2d55' : s.sc < 0.1 ? '#ffcc00' : '#00ff88';
                  const bw = Math.round((1 - s.sc) * 100);
                  return (
                    <div key={i}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, width: 76 }}>{s.lbl}</span>
                        <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,.06)', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ width: `${bw}%`, height: '100%', background: pc, transition: 'width .5s' }} />
                        </div>
                        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, width: 44, textAlign: 'right', color: pc }}>{s.val}</span>
                      </div>
                      <div style={{ fontFamily: 'var(--mono)', fontSize: 8.5, color: 'var(--muted2)', marginLeft: 84 }}>{s.note}</div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="card">
              <div className="card-h"><span className="lbl">{tr('역학 패턴', 'Epidemiological pattern', 'Schéma épidémiologique')}</span><span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)' }}>{tr('자동탐지', 'auto-detected', 'détection auto')}</span></div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', lineHeight: 1.7 }}>
                {tr(`발원지 ${result.originCount}곳 · 7일 전파율 ${result.spreadRate.toFixed(1)}배 · 밀도상관 ${result.densCorr}`, `${result.originCount} origins · 7-day spread ×${result.spreadRate.toFixed(1)} · density corr. ${result.densCorr}`, `${result.originCount} origines · propagation 7 j ×${result.spreadRate.toFixed(1)} · corr. densité ${result.densCorr}`)} → {' '}
                <b style={{ color: threatColor(result.eScore) }}>
                  {result.eScore > 70 ? tr('⚠ 비자연 패턴', '⚠ unnatural pattern', '⚠ schéma non naturel') : result.eScore > 40 ? tr('△ 주의 수준', '△ caution level', '△ niveau de vigilance') : tr('✅ 자연 전파', '✅ natural spread', '✅ propagation naturelle')}
                </b>
              </div>
            </div>
          </div>

          {/* 우: 인텔 피드 + 이중성 + 판정 + AI */}
          <div>
            <div className="card">
              <div className="card-h"><span className="lbl">{tr('PubMed 바이오안보', 'PubMed biosecurity', 'PubMed biosécurité')}</span></div>
              <FeedList items={result.pubmed.map(p => ({ title: p.title, meta: `${p.authors} · ${p.year} ${p.source === 'FALLBACK' ? tr('[폴백]', '[fallback]', '[secours]') : tr('[실시간]', '[live]', '[direct]')}`, href: `https://pubmed.ncbi.nlm.nih.gov/${p.pmid}/`, color: 'var(--violet)' }))} />
            </div>
            <div className="card">
              <div className="card-h"><span className="lbl">{tr('bioRxiv 프리프린트', 'bioRxiv preprints', 'Prépublications bioRxiv')}</span></div>
              <FeedList items={result.biorxiv.map(p => ({ title: p.title, meta: `${p.authors} · ${p.date} ${p.source === 'bioRxiv_REAL' ? tr('[실시간]', '[live]', '[direct]') : tr('[폴백]', '[fallback]', '[secours]')}`, href: `https://doi.org/${p.doi}`, color: 'var(--syn,#ff7730)' }))} />
            </div>
            <div className="card">
              <div className="card-h"><span className="lbl">{tr('WHO 발생 동향', 'WHO outbreak trends', 'Tendances des épidémies (OMS)')}</span><span style={{ fontFamily: 'var(--mono)', fontSize: 8.5, color: 'var(--muted2)' }}>{result.who[0]?.source === 'WHO_REAL' ? tr('실시간 (WHO 뉴스 피드 필터링, 위험도는 휴리스틱)', 'live (filtered WHO news feed; risk is a heuristic)', 'en direct (fil d’actualités OMS filtré ; risque heuristique)') : tr('폴백', 'fallback', 'secours')}</span></div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                {result.who.map((w, i) => {
                  const wc = w.risk > 60 ? '#ff2d55' : w.risk > 35 ? '#ffcc00' : '#00ff88';
                  return (
                    <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '8px 9px', background: 'rgba(255,255,255,.025)', border: '1px solid var(--line)', borderLeft: `3px solid ${wc}`, borderRadius: 4 }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 10.5, fontWeight: 600, color: wc }}>{w.title}</div>
                        <div style={{ fontFamily: 'var(--mono)', fontSize: 8, color: 'var(--muted2)' }}>{w.date}</div>
                      </div>
                      <div style={{ fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 700, color: wc }}>{w.risk}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="card">
              <div className="card-h"><span className="lbl">{tr('설계-탐지 이중성', 'Design–detection duality', 'Dualité conception–détection')}</span></div>
              <div style={{ display: 'flex', border: '1px solid var(--line)', borderRadius: 8, overflow: 'hidden' }}>
                {[
                  { tag: 'DESIGN', v: 'BioNeMo / Evo', sub: tr('생물학 문법 학습 · 서열 생성', 'learns biological grammar · generates sequences', 'apprend la grammaire biologique · génère des séquences'), col: 'var(--syn,#ff7730)' },
                  { tag: 'SAME MODEL', v: 'Grammar Deviation', sub: tr('설계를 알아야 탐지한다', 'to detect it you must know the design', 'pour détecter, il faut connaître la conception'), col: 'var(--accent)' },
                  { tag: 'DETECT', v: 'Stage 0 Engine', sub: tr('7신호 Fisher 앙상블', '7-signal Fisher ensemble', 'ensemble de Fisher à 7 signaux'), col: 'var(--ok,#00ff88)' },
                ].map((d, i) => (
                  <div key={i} style={{ flex: 1, padding: 10, textAlign: 'center', borderLeft: i ? '1px solid var(--line)' : undefined }}>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 7.5, color: 'var(--muted)', marginBottom: 5 }}>{d.tag}</div>
                    <div style={{ fontFamily: 'var(--disp)', fontWeight: 700, fontSize: 11.5, color: d.col, lineHeight: 1.3 }}>{d.v}</div>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 8, color: 'var(--muted2)', marginTop: 4 }}>{d.sub}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card" style={{ borderColor: c, background: result.total > 70 ? 'rgba(255,45,85,.05)' : undefined }}>
              <div className="card-h"><span className="lbl">{tr('Fisher 앙상블 종합 판정', 'Fisher ensemble verdict', 'Verdict de l’ensemble de Fisher')}</span></div>
              <div style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 17, color: c, marginBottom: 6 }}>{threatLabel(result.total)}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted)', lineHeight: 1.7 }}>
                {tr('종합', 'Total', 'Total')} {result.total} (95% CI: {result.ci.lo}~{result.ci.hi}) · {tr('7신호 Fisher 결합', '7-signal Fisher combination', 'combinaison de Fisher à 7 signaux')}<br />
                {tr('유전체', 'Genomic', 'Génomique')} {result.gScore} · {tr('역학', 'Epidemiological', 'Épidémiologique')} {result.eScore} · {tr('인텔', 'Intelligence', 'Renseignement')} {result.intelScore}<br />
                {result.total > 70 ? tr('즉시 조치: 0단계 경보 + 1~8단계 병행 + 바이오안보 당국 통보', 'Act now: stage-0 alert + run stages 1–8 in parallel + notify biosecurity authorities', 'Agir maintenant : alerte étape 0 + étapes 1–8 en parallèle + informer les autorités de biosécurité') :
                  result.total > 40 ? tr('권고: BioNeMo 서열 확인 + 역학 추가 감시', 'Recommended: check the sequence with BioNeMo + extra epidemiological watch', 'Recommandé : vérifier la séquence avec BioNeMo + veille épidémiologique accrue') : tr('1~8단계 표준 조기경보로 이관', 'Hand over to standard early warning (stages 1–8)', 'Transférer à l’alerte précoce standard (étapes 1–8)')}
              </div>
            </div>

            <div className="card">
              <div className="card-h">
                <span className="lbl">🧠 {tr('AI 통합 위협 분석', 'AI integrated threat analysis', 'Analyse intégrée des menaces par IA')}</span>
                <button onClick={runAI} disabled={aiStatus === 'loading'}
                  style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--txt)', background: 'rgba(244,63,94,.14)', border: '1px solid var(--accent)', borderRadius: 7, padding: '6px 11px', cursor: 'pointer' }}>
                  {aiStatus === 'loading' ? tr('분석 중…', 'Analysing…', 'Analyse…') : tr('분석 실행', 'Run analysis', 'Lancer l’analyse')}
                </button>
              </div>
              {aiStatus === 'idle' && <div style={{ color: 'var(--muted2)', fontFamily: 'var(--mono)', fontSize: 10.5, textAlign: 'center', padding: '10px 0' }}>{tr('스캔 후 AI 통합 분석을 실행하세요.', 'Run the AI analysis after a scan.', 'Lancez l’analyse IA après une analyse.')}</div>}
              {aiStatus === 'loading' && <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 10.5 }}><div style={{ width: 12, height: 12, border: '2px solid var(--line2)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'sp .7s linear infinite' }} />{tr('7신호 통합 분석 중…', 'Analysing 7 signals…', 'Analyse des 7 signaux…')}</div>}
              {aiStatus === 'done' && aiProv && <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: '#34d399', marginBottom: 4 }}>\u2713 {aiProv} \ubd84\uc11d</div>}{(aiStatus === 'done' || aiStatus === 'error') && <div style={{ fontFamily: 'var(--mono)', fontSize: 10.5, lineHeight: 1.7, whiteSpace: 'pre-wrap', color: aiStatus === 'error' ? '#ff8080' : 'var(--txt)' }}>{aiText}</div>}
            </div>
          </div>
        </div>
      </>)}

      <div style={{ marginTop: 16, fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)', lineHeight: 1.7, borderTop: '1px solid var(--line)', paddingTop: 12 }}>
        <b style={{ color: 'var(--muted)' }}>※ {tr('0단계 — 합성위협 탐지', 'Stage 0 — synthetic threat detection', 'Étape 0 — détection des menaces synthétiques')}</b>: {tr('CAI·CpG억제비율·엔트로피·GC편향(유전체 4신호 · 서버 실측 단일원천) + 발원지수·전파율·밀도상관(역학 3신호) + PubMed·bioRxiv·WHO(인텔 3신호) 를 Fisher 결합. NCBI·PubMed·bioRxiv·WHO 모두 실시간 API 연동 (WHO는 전용 DON RSS가 폐지되어 일반 뉴스 피드를 발생 키워드로 필터링 — 위험도는 WHO 공식 등급이 아닌 키워드 기반 휴리스틱). AI 분석은 서버(FastAPI) 경유로 Claude 호출.',
          'CAI, CpG suppression, entropy and GC bias (4 genomic signals, server measurement as the single source) + number of origins, spread rate and density correlation (3 epidemiological signals) + PubMed, bioRxiv and WHO (3 intelligence signals), combined with Fisher’s method. NCBI, PubMed, bioRxiv and WHO are all live APIs (WHO’s dedicated DON RSS was discontinued, so the general news feed is filtered by outbreak keywords; risk is a keyword heuristic, not an official WHO grade). AI analysis calls Claude through the server (FastAPI).',
          'CAI, suppression CpG, entropie et biais GC (4 signaux génomiques, mesure serveur comme source unique) + nombre d’origines, taux de propagation et corrélation de densité (3 signaux épidémiologiques) + PubMed, bioRxiv et OMS (3 signaux de renseignement), combinés par la méthode de Fisher. NCBI, PubMed, bioRxiv et OMS sont des API en direct (le flux RSS DON dédié de l’OMS ayant été supprimé, le fil d’actualités général est filtré par mots-clés ; le risque est une heuristique, pas un niveau officiel de l’OMS). L’analyse IA appelle Claude via le serveur (FastAPI).')}
      </div>
    </div>
  );
}

function FeedList({ items }: { items: { title: string; meta: string; href: string; color: string }[] }) {
  const tr = useT();
  if (!items.length) return <div style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 10, textAlign: 'center', padding: '8px 0' }}>{tr('결과 없음', 'No results', 'Aucun résultat')}</div>;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5, maxHeight: 200, overflowY: 'auto' }}>
      {items.map((it, i) => (
        <a key={i} href={it.href} target="_blank" rel="noreferrer"
          style={{ display: 'block', padding: '8px 9px', background: 'rgba(255,255,255,.025)', border: '1px solid var(--line)', borderLeft: `3px solid ${it.color}`, borderRadius: 4, textDecoration: 'none' }}>
          <div style={{ fontSize: 10.5, fontWeight: 600, color: it.color, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{it.title}</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 8, color: 'var(--muted2)', marginTop: 2 }}>{it.meta}</div>
        </a>
      ))}
    </div>
  );
}
