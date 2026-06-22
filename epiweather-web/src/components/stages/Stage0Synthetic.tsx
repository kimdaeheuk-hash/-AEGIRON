'use client';
import { useState } from 'react';
import {
  calcCAI, calcCpG, calcEnt, calcGC,
  pCAI, pCpG, pEnt, pGC, pOrigin, pRate, pDens,
  fisherCombine, calcCI, threatColor, threatLabel,
  fetchNCBI, fetchPubMed, fetchBioRxiv, fetchWHO,
  NCBIResult, PubMedPaper, BioRxivPaper, WHOItem,
} from '@/lib/syntheticThreat';

const API = 'http://localhost:8000';

interface ScanResult {
  total: number; ci: { lo: number; hi: number };
  gScore: number; eScore: number; intelScore: number;
  cai: number; cpgR: number; ent: number; gc: number;
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
  const [aiStatus, setAiStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [aiText, setAiText] = useState('');

  async function runScan() {
    setScanning(true);
    setResult(null);
    setAiStatus('idle');

    const originCount = Math.max(1, parseInt(origins) || 1);
    const d7 = Math.max(1, parseInt(day7) || 22);
    const d1 = Math.max(1, parseInt(day1) || 1);
    const densCorr = Math.min(1, Math.max(0, parseFloat(dens) || 0.82));
    const spreadRate = d7 / d1;
    const accession = acc.trim() || 'MN908947';

    const [ncbi, pubmed, biorxiv, who] = await Promise.all([
      fetchNCBI(accession), fetchPubMed(), fetchBioRxiv(), fetchWHO(),
    ]);

    const seq = ncbi.seq || 'ATGGAGAGCCTTGTCCCTGGT';
    const cai = calcCAI(seq), cpgR = calcCpG(seq), ent = calcEnt(seq), gc = calcGC(seq);
    const gPs = [pCAI(cai), pCpG(cpgR), pEnt(ent), pGC(gc)];
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

    setResult({ total, ci, gScore, eScore, intelScore, cai, cpgR, ent, gc, originCount, spreadRate, densCorr, ncbi, pubmed, biorxiv, who });
    setScanning(false);
  }

  async function runAI() {
    if (!result) return;
    setAiStatus('loading');
    try {
      const summary = {
        종합: result.total, CI: result.ci,
        유전체: { CAI: result.cai, CpG억제비율: result.cpgR, 엔트로피: result.ent, GC: result.gc, 점수: result.gScore },
        역학: { 발원지: result.originCount, 전파율: +result.spreadRate.toFixed(1), 밀도상관: result.densCorr, 점수: result.eScore },
        인텔: { PubMed건수: result.pubmed.length, 점수: result.intelScore },
        접근번호: result.ncbi.acc,
      };
      const res = await fetch(`${API}/api/synthetic-threat/analyze`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary }),
      });
      if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
      const data = await res.json();
      setAiText(data.analysis);
      setAiStatus('done');
    } catch (e) {
      setAiText(e instanceof Error ? e.message : String(e));
      setAiStatus('error');
    }
  }

  const c = result ? threatColor(result.total) : 'var(--muted)';

  const sevenSignals = result ? [
    { lbl: 'CAI', val: result.cai.toFixed(3), note: result.cai > 0.45 ? '과최적화 ⚠' : result.cai > 0.28 ? '정상' : '낮음', sc: pCAI(result.cai) },
    { lbl: 'CpG 억제', val: result.cpgR.toFixed(3), note: result.cpgR > 0.80 ? '억제없음 ⚠' : result.cpgR < 0.25 ? '강억제' : '정상', sc: pCpG(result.cpgR) },
    { lbl: '엔트로피', val: result.ent.toFixed(2), note: result.ent < 2.8 ? '너무균일 ⚠' : result.ent > 5.9 ? '과복잡' : '자연', sc: pEnt(result.ent) },
    { lbl: 'GC 편향', val: (result.gc * 100).toFixed(0) + '%', note: result.gc > 0.65 ? '편향↑' : result.gc < 0.33 ? '편향↓' : '정상', sc: pGC(result.gc) },
  ] : [];

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">합성위협 탐지 엔진</div>
      <div className="psub">
        진단 이전, <em style={{ color: 'var(--violet)', fontStyle: 'normal', fontWeight: 600 }}>설계-탐지 이중성</em> 원리로
        유전체·역학·인텔 7신호를 Fisher&apos;s 결합해 합성/자연 기원을 가른다.
      </div>

      {/* 입력 바 */}
      <div className="card" style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)' }}>GENBANK 접근번호</span>
          <input value={acc} onChange={e => setAcc(e.target.value)} placeholder="MN908947"
            style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--txt)', background: 'var(--bg2)', border: '1px solid var(--line2)', borderRadius: 7, padding: '7px 11px', width: 130, outline: 'none' }} />
        </div>
        {[
          { lbl: '발원지 수', v: origins, set: setOrigins, w: 70 },
          { lbl: 'D+7 환자', v: day7, set: setDay7, w: 70 },
          { lbl: 'D+1 환자', v: day1, set: setDay1, w: 70 },
          { lbl: '밀도상관', v: dens, set: setDens, w: 70 },
        ].map((f, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)' }}>{f.lbl}</span>
            <input value={f.v} onChange={e => f.set(e.target.value)}
              style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--txt)', background: 'var(--bg2)', border: '1px solid var(--line2)', borderRadius: 7, padding: '7px 9px', width: f.w, outline: 'none' }} />
          </div>
        ))}
        <button onClick={runScan} disabled={scanning}
          style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#fff', background: scanning ? 'var(--muted2)' : 'var(--accent)', border: 'none', borderRadius: 7, padding: '9px 16px', cursor: scanning ? 'wait' : 'pointer', fontWeight: 700 }}>
          {scanning ? '스캔 중…' : '▶ 전체 스캔'}
        </button>
      </div>

      {!result && !scanning && (
        <div className="card" style={{ marginTop: 12, textAlign: 'center', color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11, padding: '24px 0' }}>
          GenBank 접근번호와 역학 파라미터를 입력하고 전체 스캔을 실행하세요.
        </div>
      )}
      {scanning && (
        <div className="card" style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10, color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11, padding: '14px 0', justifyContent: 'center' }}>
          <div style={{ width: 14, height: 14, border: '2px solid var(--line2)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'sp .8s linear infinite' }} />
          NCBI·PubMed·bioRxiv 병렬 스캔 중…
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
            <div className="ok">역학 이상</div>
            <div className="ov" style={{ fontSize: 15, color: threatColor(result.eScore) }}>{result.eScore}</div>
            <div className="od">{result.eScore > 70 ? '비자연 패턴' : result.eScore > 40 ? '경계' : '자연'}</div>
          </div>
          <div className="oc">
            <div className="ok">바이오안보</div>
            <div className="ov" style={{ fontSize: 15, color: threatColor(result.intelScore) }}>{result.intelScore}</div>
            <div className="od">논문 {result.pubmed.length}건</div>
          </div>
          <div className="oc" style={{ borderColor: 'rgba(244,63,94,.4)' }}>
            <div className="ok">종합 Fisher</div>
            <div className="ov" style={{ fontSize: 18, color: c }}>{result.total}</div>
            <div className="od">95% CI [{result.ci.lo}, {result.ci.hi}]</div>
          </div>
        </div>

        <div className="grid2" style={{ marginTop: 14 }}>
          {/* 좌: 유전체+역학 */}
          <div>
            <div className="card">
              <div className="card-h"><span className="lbl">유전체 분석 (4신호)</span><span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--cold,#00c8ff)' }}>{result.ncbi.acc} · {result.ncbi.seq.length}bp · {result.ncbi.source === 'NCBI_REAL' ? '실시간' : '폴백'}</span></div>
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
              <div className="card-h"><span className="lbl">역학 패턴</span><span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)' }}>자동탐지</span></div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', lineHeight: 1.7 }}>
                발원지 {result.originCount}곳 · 7일 전파율 {result.spreadRate.toFixed(1)}배 · 밀도상관 {result.densCorr} → {' '}
                <b style={{ color: threatColor(result.eScore) }}>
                  {result.eScore > 70 ? '⚠ 비자연 패턴' : result.eScore > 40 ? '△ 주의 수준' : '✅ 자연 전파'}
                </b>
              </div>
            </div>
          </div>

          {/* 우: 인텔 피드 + 이중성 + 판정 + AI */}
          <div>
            <div className="card">
              <div className="card-h"><span className="lbl">PubMed 바이오안보</span></div>
              <FeedList items={result.pubmed.map(p => ({ title: p.title, meta: `${p.authors} · ${p.year} ${p.source === 'FALLBACK' ? '[폴백]' : '[실시간]'}`, href: `https://pubmed.ncbi.nlm.nih.gov/${p.pmid}/`, color: 'var(--violet)' }))} />
            </div>
            <div className="card">
              <div className="card-h"><span className="lbl">bioRxiv 프리프린트</span></div>
              <FeedList items={result.biorxiv.map(p => ({ title: p.title, meta: `${p.authors} · ${p.date} ${p.source === 'bioRxiv_REAL' ? '[실시간]' : '[폴백]'}`, href: `https://doi.org/${p.doi}`, color: 'var(--syn,#ff7730)' }))} />
            </div>
            <div className="card">
              <div className="card-h"><span className="lbl">WHO 발생 동향</span><span style={{ fontFamily: 'var(--mono)', fontSize: 8.5, color: 'var(--muted2)' }}>{result.who[0]?.source === 'WHO_REAL' ? '실시간 (WHO 뉴스 피드 필터링, 위험도는 휴리스틱)' : '폴백'}</span></div>
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
              <div className="card-h"><span className="lbl">설계-탐지 이중성</span></div>
              <div style={{ display: 'flex', border: '1px solid var(--line)', borderRadius: 8, overflow: 'hidden' }}>
                {[
                  { tag: 'DESIGN', v: 'BioNeMo / Evo', sub: '생물학 문법 학습 · 서열 생성', col: 'var(--syn,#ff7730)' },
                  { tag: 'SAME MODEL', v: 'Grammar Deviation', sub: '설계를 알아야 탐지한다', col: 'var(--accent)' },
                  { tag: 'DETECT', v: 'Stage 0 Engine', sub: '7신호 Fisher 앙상블', col: 'var(--ok,#00ff88)' },
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
              <div className="card-h"><span className="lbl">Fisher&apos;s 앙상블 종합 판정</span></div>
              <div style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 17, color: c, marginBottom: 6 }}>{threatLabel(result.total)}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--muted)', lineHeight: 1.7 }}>
                종합 {result.total} (95% CI: {result.ci.lo}~{result.ci.hi}) · 7신호 Fisher&apos;s combination<br />
                유전체 {result.gScore} · 역학 {result.eScore} · 인텔 {result.intelScore}<br />
                {result.total > 70 ? '즉시 조치: 0단계 경보 + 1~8단계 병행 + 바이오안보 당국 통보' :
                  result.total > 40 ? '권고: BioNeMo 서열 확인 + 역학 추가 감시' : '1~8단계 표준 조기경보로 이관'}
              </div>
            </div>

            <div className="card">
              <div className="card-h">
                <span className="lbl">🧠 AI 통합 위협 분석</span>
                <button onClick={runAI} disabled={aiStatus === 'loading'}
                  style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--txt)', background: 'rgba(244,63,94,.14)', border: '1px solid var(--accent)', borderRadius: 7, padding: '6px 11px', cursor: 'pointer' }}>
                  {aiStatus === 'loading' ? '분석 중…' : '분석 실행'}
                </button>
              </div>
              {aiStatus === 'idle' && <div style={{ color: 'var(--muted2)', fontFamily: 'var(--mono)', fontSize: 10.5, textAlign: 'center', padding: '10px 0' }}>스캔 후 AI 통합 분석을 실행하세요.</div>}
              {aiStatus === 'loading' && <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 10.5 }}><div style={{ width: 12, height: 12, border: '2px solid var(--line2)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'sp .7s linear infinite' }} />7신호 통합 분석 중…</div>}
              {(aiStatus === 'done' || aiStatus === 'error') && <div style={{ fontFamily: 'var(--mono)', fontSize: 10.5, lineHeight: 1.7, whiteSpace: 'pre-wrap', color: aiStatus === 'error' ? '#ff8080' : 'var(--txt)' }}>{aiText}</div>}
            </div>
          </div>
        </div>
      </>)}

      <div style={{ marginTop: 16, fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)', lineHeight: 1.7, borderTop: '1px solid var(--line)', paddingTop: 12 }}>
        <b style={{ color: 'var(--muted)' }}>※ 0단계 — 합성위협 탐지</b>: CAI·CpG억제비율·엔트로피·GC편향(유전체 4신호) + 발원지수·전파율·밀도상관(역학 3신호) + PubMed·bioRxiv·WHO(인텔 3신호) 를 Fisher&apos;s 결합. NCBI·PubMed·bioRxiv·WHO 모두 실시간 API 연동 (WHO는 전용 DON RSS가 폐지되어 일반 뉴스 피드를 발생 키워드로 필터링 — 위험도는 WHO 공식 등급이 아닌 키워드 기반 휴리스틱). AI 분석은 서버(FastAPI) 경유로 Claude 호출.
      </div>
    </div>
  );
}

function FeedList({ items }: { items: { title: string; meta: string; href: string; color: string }[] }) {
  if (!items.length) return <div style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 10, textAlign: 'center', padding: '8px 0' }}>결과 없음</div>;
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
