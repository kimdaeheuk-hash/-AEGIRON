// 0단계 합성위협 탐지 — 원본 epiweather-stage0-v3.html에서 TypeScript로 이식
// CAI(코돈적응지수)·CpG억제비율·엔트로피·GC편향 + Fisher's 결합
import { API_BASE } from '@/lib/api';

const HCF: Record<string, number> = {
  TTT:.17,TTC:.204,TTA:.073,TTG:.127,CTT:.129,CTC:.198,CTA:.07,CTG:.405,
  ATT:.157,ATC:.224,ATA:.07,ATG:1.0,GTT:.109,GTC:.147,GTA:.07,GTG:.289,
  TCT:.145,TCC:.22,TCA:.148,TCG:.044,CCT:.174,CCC:.198,CCA:.27,CCG:.063,
  ACT:.129,ACC:.36,ACA:.284,ACG:.062,GCT:.183,GCC:.405,GCA:.227,GCG:.074,
  TAT:.175,TAC:.195,CAT:.105,CAC:.15,CAA:.273,CAG:.341,AAT:.169,AAC:.196,
  AAA:.432,AAG:.314,GAT:.213,GAC:.258,GAA:.426,GAG:.442,TGT:.095,TGC:.122,
  TGG:.13,CGT:.046,CGC:.105,CGA:.062,CGG:.115,AGA:.204,AGG:.206,AGT:.148,
  AGC:.24,GGT:.107,GGC:.224,GGA:.248,GGG:.165,
};

function cleanSeq(seq: string) {
  return seq.toUpperCase().replace(/[^ATGC]/g, '');
}

export function calcCAI(rawSeq: string) {
  const seq = cleanSeq(rawSeq);
  if (seq.length < 30) return 0.2;
  let s = 0, n = 0;
  for (let i = 0; i < seq.length - 2; i += 3) {
    const f = HCF[seq.slice(i, i + 3)];
    if (f && f > 0) { s += Math.log(f); n++; }
  }
  return n > 0 ? Math.exp(s / n) : 0.2;
}

export function calcCpG(rawSeq: string) {
  const seq = cleanSeq(rawSeq);
  if (seq.length < 40) return 0.5;
  let cpg = 0, c = 0, g = 0;
  for (let i = 0; i < seq.length - 1; i++) {
    if (seq[i] === 'C') { c++; if (seq[i + 1] === 'G') cpg++; }
    if (seq[i] === 'G') g++;
  }
  const obs = cpg / (seq.length - 1), exp = (c / seq.length) * (g / seq.length);
  return exp > 0 ? +(obs / exp).toFixed(3) : 2.0;
}

export function calcEnt(rawSeq: string) {
  const seq = cleanSeq(rawSeq);
  const cc: Record<string, number> = {};
  for (let i = 0; i < seq.length - 2; i += 3) {
    const c = seq.slice(i, i + 3);
    cc[c] = (cc[c] || 0) + 1;
  }
  const v = Object.values(cc).filter(x => x > 0);
  const t = v.reduce((a, b) => a + b, 0);
  if (t < 2) return 0;
  return -v.reduce((s, x) => { const p = x / t; return s + p * Math.log2(p); }, 0);
}

export function calcGC(rawSeq: string) {
  const seq = cleanSeq(rawSeq);
  return seq.split('').filter(b => b === 'G' || b === 'C').length / seq.length;
}

export function pCAI(v: number) { return v > 0.55 ? 0.001 : v > 0.45 ? 0.01 : v > 0.38 ? 0.05 : v > 0.28 ? 0.2 : 0.75; }
export function pCpG(v: number) { return v > 1.20 ? 0.001 : v > 0.80 ? 0.02 : v > 0.60 ? 0.15 : v > 0.25 ? 0.7 : 0.4; }
export function pEnt(v: number) { return v < 1.5 ? 0.001 : v < 2.8 ? 0.02 : v < 3.2 ? 0.1 : v > 6.0 ? 0.05 : 0.75; }
export function pGC(v: number) { return v > 0.72 ? 0.005 : v < 0.28 ? 0.01 : v > 0.65 ? 0.08 : v < 0.33 ? 0.1 : 0.7; }
export function pOrigin(v: number) { return v > 3 ? 0.001 : v > 1 ? 0.04 : 0.75; }
export function pRate(v: number) { return v > 500 ? 0.001 : v > 100 ? 0.005 : v > 20 ? 0.04 : v > 5 ? 0.2 : 0.65; }
export function pDens(v: number) { return v < 0.15 ? 0.003 : v < 0.35 ? 0.04 : v < 0.5 ? 0.15 : 0.7; }

export function fisherCombine(pVals: number[]) {
  if (!pVals.length) return 0;
  const chi = -2 * pVals.reduce((s, p) => s + Math.log(Math.max(0.0001, p)), 0);
  const k = pVals.length;
  let s = 0, t = Math.exp(-chi / 2);
  for (let i = 0; i < k; i++) { s += t; t *= chi / (2 * (i + 1)); }
  const pF = Math.min(0.9999, s);
  return Math.min(100, Math.round((1 - pF) * 100));
}

export function calcCI(score: number, nSignals: number) {
  const m = Math.round(14 / Math.sqrt(nSignals));
  return { lo: Math.max(0, score - m), hi: Math.min(100, score + m) };
}

export function threatColor(s: number) { return s > 70 ? '#ff2d55' : s > 40 ? '#ffcc00' : '#00ff88'; }
export function threatLabel(s: number) { return s > 70 ? '⚠ 합성위협 고위험' : s > 40 ? '△ 합성위협 의심' : '✅ 자연추정'; }

export interface NCBIResult { seq: string; acc: string; source: 'NCBI_REAL' | 'FALLBACK'; }
export interface PubMedPaper { pmid: string; title: string; authors: string; year: string; source: string; }
export interface BioRxivPaper { doi: string; title: string; authors: string; date: string; source: string; }
export interface WHOItem { title: string; date?: string; country?: string; risk: number; source: string; }

const NCBI_FALLBACK_SEQ: Record<string, string> =
  { MN908947: 'ATGGAGAGCCTTGTCCCTGGTTTCAACGAGAAAACACACGTCCAACTCAGTTTGCCTGTTTTACAGGTTCCCTTGAGGTTTAGTGAAATTGGAAGAC' };

export async function fetchNCBI(acc: string): Promise<NCBIResult> {
  try {
    const r = await fetch(
      `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=${acc}&rettype=fasta&retmode=text`,
      { signal: AbortSignal.timeout(9000) },
    );
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const txt = await r.text();
    const seq = txt.split('\n').filter(l => !l.startsWith('>')).join('').slice(0, 800);
    if (!seq) throw new Error('빈 서열');
    return { seq, acc, source: 'NCBI_REAL' };
  } catch {
    return { seq: NCBI_FALLBACK_SEQ[acc] || 'ATGGAGAGCCTTGTCCCTGGTTTCAACGAG', acc, source: 'FALLBACK' };
  }
}

export async function fetchPubMed(): Promise<PubMedPaper[]> {
  try {
    const r1 = await fetch(
      'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=synthetic+biology+pathogen+biosecurity&retmax=4&sort=date&retmode=json',
      { signal: AbortSignal.timeout(9000) },
    );
    if (!r1.ok) throw new Error();
    const j1 = await r1.json();
    const ids: string[] = j1.esearchresult?.idlist || [];
    if (!ids.length) return [];
    const r2 = await fetch(
      `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=${ids.join(',')}&retmode=json`,
      { signal: AbortSignal.timeout(9000) },
    );
    if (!r2.ok) throw new Error();
    const j2 = await r2.json();
    return ids.map(id => {
      const r = j2.result?.[id] || {};
      return {
        pmid: id, title: r.title || '—',
        authors: (r.authors || []).slice(0, 2).map((a: { name: string }) => a.name).join(', '),
        year: r.pubdate?.slice(0, 4) || '', source: 'PubMed_REAL',
      };
    });
  } catch {
    return [
      { pmid: '1', title: 'AI-designed viral genomes: biosecurity detection methods', authors: 'King SH et al.', year: '2025', source: 'FALLBACK' },
      { pmid: '2', title: 'Screening evasion of DNA synthesis using AI', authors: 'Horvitz E et al.', year: '2025', source: 'FALLBACK' },
    ];
  }
}

const API = API_BASE;

// bioRxiv API는 브라우저에서 CORS로 차단되므로 서버(FastAPI) 경유로 호출
export async function fetchBioRxiv(): Promise<BioRxivPaper[]> {
  try {
    const r = await fetch(`${API}/api/synthetic-threat/biorxiv`, { signal: AbortSignal.timeout(9000) });
    if (!r.ok) throw new Error();
    const j = await r.json();
    if (!j.papers?.length) throw new Error();
    return j.papers;
  } catch {
    return [
      { doi: '10.1101/2025.09.12.675911', title: 'First AI-generated viral genomes capable of replication', authors: 'King SH, Hie B', date: '2025-09', source: 'FALLBACK' },
      { doi: '10.1101/2025.00000', title: 'Foundation models for pathogen genome generation', authors: '—', date: '2025', source: 'FALLBACK' },
    ];
  }
}

// WHO 전용 DON RSS는 폐지됨 — 서버가 WHO 일반 뉴스 피드를 발생 키워드로 필터링해 반환
export async function fetchWHO(): Promise<WHOItem[]> {
  try {
    const r = await fetch(`${API}/api/synthetic-threat/who`, { signal: AbortSignal.timeout(9000) });
    if (!r.ok) throw new Error();
    const j = await r.json();
    if (!j.items?.length) throw new Error();
    return j.items;
  } catch {
    return [
      { title: 'Unusual cluster of pneumonia - Republic of Korea', date: '2026-05', risk: 55, source: 'FALLBACK' },
      { title: 'Novel influenza A variant - Southeast Asia', date: '2026-04', risk: 35, source: 'FALLBACK' },
      { title: 'Ebola outbreak update - Central Africa', date: '2026-03', risk: 42, source: 'FALLBACK' },
    ];
  }
}
