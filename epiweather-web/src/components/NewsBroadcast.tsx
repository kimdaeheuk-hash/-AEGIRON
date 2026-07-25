'use client';
import { useState, useEffect, useRef } from 'react';
import { fetchDailyBrief, DailyBrief, BriefSegment } from '@/lib/api';

// 홈페이지 '뉴스 방송 화면' — /api/daily-brief 러시트를 실제 뉴스처럼 렌더링.
// 헤드라인 바 + 앵커 리드(텔레프롬프터식 자동 순환) + 하단 자막(chyron) + 스크롤
// 티커 + LIVE 배지. 정직성: is_official_alert=false이므로 '공식 경보 아님 · AI
// 자동생성'을 항상 노출하고, 조용한 날은 조용한 화면 그대로 보여준다(가짜 위기 X).

const TIER_COLOR: Record<string, string> = {
  critical: '#f43f5e', high: '#fb923c', medium: '#fbbf24', low: '#38bdf8',
};
const SEGMENT_MS = 7000; // 세그먼트(앵커 리드) 자동 전환 주기
const REFRESH_MS = 90_000; // 브리핑 재요청 주기

export default function NewsBroadcast() {
  const [brief, setBrief] = useState<DailyBrief | null>(null);
  const [error, setError] = useState(false);
  const [idx, setIdx] = useState(0);
  const [lang, setLang] = useState<'ko' | 'en'>('ko');
  const idxRef = useRef(0);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const b = await fetchDailyBrief(lang);
        if (alive) { setBrief(b); setError(false); }
      } catch {
        if (alive) setError(true);
      }
    }
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => { alive = false; clearInterval(t); };
  }, [lang]);

  // 세그먼트 자동 순환 (텔레프롬프터처럼 한 꼭지씩)
  useEffect(() => {
    if (!brief || brief.segments.length <= 1) return;
    const t = setInterval(() => {
      idxRef.current = (idxRef.current + 1) % brief.segments.length;
      setIdx(idxRef.current);
    }, SEGMENT_MS);
    return () => clearInterval(t);
  }, [brief]);

  useEffect(() => { idxRef.current = 0; setIdx(0); }, [brief?.date, brief?.format.id]);

  if (error && !brief) return null; // 백엔드 미가동 시 홈 나머지는 정상 노출

  const seg: BriefSegment | undefined = brief?.segments[idx];
  const accent = seg?.tier ? TIER_COLOR[seg.tier] ?? '#38bdf8' : '#34d399';
  const t = (ko: string, en: string) => (lang === 'ko' ? ko : en);

  return (
    <section style={{ maxWidth: 1320, margin: '0 auto', padding: '0 clamp(14px,2.4vw,26px) 80px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 18, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.18em', color: 'var(--accent)', marginBottom: 10 }}>
            NEWS CENTER · 자동 생성 브리핑
          </div>
          <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(24px,3vw,34px)', letterSpacing: '-.02em' }}>
            아이기론 뉴스센터
          </h2>
        </div>
        <div style={{ display: 'flex', gap: 6, fontFamily: 'var(--mono)', fontSize: 11 }}>
          {(['ko', 'en'] as const).map(l => (
            <button key={l} onClick={() => setLang(l)} style={{
              cursor: 'pointer', padding: '6px 12px', borderRadius: 8,
              border: '1px solid var(--line2)',
              background: lang === l ? 'var(--accent)' : 'var(--panel)',
              color: lang === l ? '#fff' : 'var(--muted)',
            }}>{l.toUpperCase()}</button>
          ))}
        </div>
      </div>

      {/* ── 방송 화면 ─────────────────────────────────────────── */}
      <div style={{
        position: 'relative', borderRadius: 18, overflow: 'hidden',
        border: '1px solid var(--line2)', background: '#070b12',
        aspectRatio: '16 / 8', minHeight: 340,
      }}>
        {/* 스튜디오 배경 그라디언트 */}
        <div style={{ position: 'absolute', inset: 0, background:
          `radial-gradient(120% 90% at 78% 10%, ${accent}22, transparent 55%), linear-gradient(160deg,#0b1220,#070b12)` }} />

        {/* 상단 바: 프로그램명 + LIVE + 포맷 */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, display: 'flex',
          alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px',
          fontFamily: 'var(--mono)', fontSize: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: '#fff',
              background: 'var(--accent)', borderRadius: 5, padding: '3px 9px', fontWeight: 700, letterSpacing: '.1em' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff', animation: 'blink 1.4s infinite' }} />LIVE
            </span>
            <span style={{ color: 'var(--muted)' }}>{brief?.program_name ?? '아이기론 역병예보'}</span>
          </div>
          {brief && (
            <span style={{ color: 'var(--muted2)', border: '1px solid var(--line2)', borderRadius: 5, padding: '3px 9px' }}>
              {brief.format.name}
            </span>
          )}
        </div>

        {/* 앵커 자리(합성 AI 진행자 플레이스홀더) */}
        <div style={{ position: 'absolute', right: 'clamp(18px,4vw,64px)', bottom: 88, display: 'flex', gap: 14, alignItems: 'flex-end' }}>
          {(brief?.presenters ?? [{ presenter_id: 'a', role: 'anchor', name: '' }]).slice(0, 2).map((p, i) => (
            <AnchorAvatar key={p.presenter_id} accent={accent} dimmed={brief?.format.host_mode === 'duo' && seg?.dialogue
              ? seg.dialogue[Math.min(i, seg.dialogue.length - 1)]?.speaker !== p.role : false} />
          ))}
        </div>

        {/* 중앙: 헤드라인 + 앵커 리드(텔레프롬프터) */}
        <div style={{ position: 'absolute', left: 0, right: 0, top: '30%', padding: '0 clamp(18px,4vw,48px)', maxWidth: '68%' }}>
          <div style={{ fontFamily: 'var(--kr)', fontWeight: 800, fontSize: 'clamp(17px,2.3vw,27px)',
            lineHeight: 1.25, color: '#fff', textShadow: '0 2px 20px rgba(0,0,0,.6)' }}>
            {brief?.headline ?? t('브리핑 불러오는 중…', 'Loading briefing…')}
          </div>
          {seg && (
            <p key={seg.segment_id} style={{ marginTop: 14, fontFamily: 'var(--kr)', fontSize: 'clamp(13px,1.5vw,16px)',
              lineHeight: 1.7, color: 'rgba(255,255,255,.86)', maxWidth: 620, animation: 'fadeUp .5s ease' }}>
              {seg.anchor_script}
            </p>
          )}
        </div>

        {/* 하단 자막(chyron / lower-third) */}
        {seg && (
          <div style={{ position: 'absolute', left: 0, bottom: 44, display: 'flex', alignItems: 'stretch' }}>
            <div style={{ background: accent, color: '#04070d', fontFamily: 'var(--mono)', fontWeight: 800,
              fontSize: 11, letterSpacing: '.08em', padding: '9px 12px', display: 'grid', placeItems: 'center' }}>
              {seg.kind === 'quiet' ? t('감시', 'WATCH') : t('속보', 'ALERT')}
            </div>
            <div style={{ background: 'rgba(4,7,13,.82)', color: '#fff', fontFamily: 'var(--kr)', fontWeight: 700,
              fontSize: 'clamp(12px,1.4vw,15px)', padding: '9px 16px', borderRight: '1px solid rgba(255,255,255,.1)' }}>
              {seg.lower_third}
            </div>
          </div>
        )}

        {/* 하단 스크롤 티커 */}
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 34, background: '#04070d',
          borderTop: `2px solid ${accent}`, display: 'flex', alignItems: 'center', overflow: 'hidden' }}>
          <span style={{ flexShrink: 0, background: accent, color: '#04070d', fontFamily: 'var(--mono)', fontWeight: 800,
            fontSize: 11, height: '100%', display: 'grid', placeItems: 'center', padding: '0 12px', letterSpacing: '.1em' }}>
            {t('실시간', 'LIVE')}
          </span>
          <div style={{ whiteSpace: 'nowrap', animation: 'ticker 32s linear infinite', paddingLeft: '100%',
            fontFamily: 'var(--mono)', fontSize: 12, color: 'rgba(255,255,255,.82)' }}>
            {(brief?.ticker?.length ? brief.ticker : [t('신규 격상 위협 없음 · 정기 감시 지속', 'No newly elevated threats · routine surveillance')])
              .join('     ◆     ')}
          </div>
        </div>

        {/* 세그먼트 진행 점 */}
        {brief && brief.segments.length > 1 && (
          <div style={{ position: 'absolute', top: 46, left: 'clamp(18px,4vw,48px)', display: 'flex', gap: 6 }}>
            {brief.segments.map((s, i) => (
              <span key={s.segment_id} style={{ width: i === idx ? 18 : 6, height: 6, borderRadius: 3,
                background: i === idx ? accent : 'rgba(255,255,255,.25)', transition: 'width .3s' }} />
            ))}
          </div>
        )}
      </div>

      {/* ── 정직성 고지 바 ────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginTop: 14,
        padding: '12px 16px', background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 12 }}>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, fontWeight: 800, letterSpacing: '.1em',
          color: '#fbbf24', border: '1px solid rgba(251,191,36,.35)', borderRadius: 6, padding: '4px 9px', flexShrink: 0 }}>
          {t('공식 경보 아님 · AI 자동생성', 'NOT AN OFFICIAL ALERT · AI-GENERATED')}
        </span>
        <span style={{ fontFamily: 'var(--kr)', fontSize: 11.5, color: 'var(--muted2)', lineHeight: 1.6 }}>
          {brief?.disclosure ?? t('공개 데이터를 AI가 자동 요약한 브리핑입니다.', 'An AI-generated automated summary of public data.')}
        </span>
        {brief && (
          <span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)', flexShrink: 0 }}>
            {brief.date} · {brief.generation_method === 'llm_polished' ? 'LLM' : 'template'}
          </span>
        )}
      </div>

      <style>{`
        @keyframes ticker { 0% { transform: translateX(0); } 100% { transform: translateX(-100%); } }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
        @media (max-width: 760px) {
          section > div > div[style*="max-width: 68%"], section div[style*="maxWidth: '68%'"] { max-width: 100% !important; }
        }
      `}</style>
    </section>
  );
}

// 합성 AI 진행자 실루엣 플레이스홀더(실제 영상은 페이퍼클립이 생성). 방송 느낌만 낸다.
function AnchorAvatar({ accent, dimmed }: { accent: string; dimmed: boolean }) {
  return (
    <div style={{ width: 'clamp(70px,10vw,120px)', opacity: dimmed ? 0.4 : 1, transition: 'opacity .4s',
      filter: 'drop-shadow(0 6px 24px rgba(0,0,0,.5))' }}>
      <svg viewBox="0 0 100 130" style={{ width: '100%', height: 'auto', display: 'block' }}>
        <defs>
          <linearGradient id={`bd-${accent}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity=".9" />
            <stop offset="100%" stopColor={accent} stopOpacity=".25" />
          </linearGradient>
        </defs>
        {/* 어깨/상의 */}
        <path d="M8 130 C8 96 30 84 50 84 C70 84 92 96 92 130 Z" fill={`url(#bd-${accent})`} />
        <path d="M50 84 L50 130" stroke="rgba(0,0,0,.25)" strokeWidth="1" />
        {/* 머리 */}
        <circle cx="50" cy="52" r="24" fill="#e8d4c0" />
        {/* 단정한 헤어 */}
        <path d="M24 52 C24 30 76 30 76 52 C76 44 70 34 50 34 C30 34 24 44 24 52 Z" fill="#2a2018" />
        <path d="M26 54 C22 66 26 74 30 76 L30 58 Z M74 54 C78 66 74 74 70 76 L70 58 Z" fill="#2a2018" />
      </svg>
    </div>
  );
}
