// 0단계 합성위협 탐지 — 원본 epiweather-stage0-v3.html에서 TypeScript로 이식
// 역학 p-값 + Fisher's 결합 + 인텔 피드. 유전체 4지표(CAI·CpG·엔트로피·GC)는
// 서버 실측 단일원천(genome-screen)이라 여기서 계산하지 않는다(2026-11-02 삭제 —
// 프론트 코돈-엔트로피와 서버 뉴클레오타이드 Shannon이 달라 두 값이 됐다).
import { API_BASE } from '@/lib/api';

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
