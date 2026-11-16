'use client';
import { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { THREAT, PRESETS, CIVIC, currentRt } from '@/lib/algorithms';
import OriginSelector from './OriginSelector';
import Stage0Synthetic from './stages/Stage0Synthetic';
import Stage1PatientZero from './stages/Stage1PatientZero';
import Stage2Civic from './stages/Stage2Civic';
import Stage3Global from './stages/Stage3Global';
import Stage4Domestic from './stages/Stage4Domestic';
import Stage5Network from './stages/Stage5Network';
import Stage6Defense from './stages/Stage6Defense';
import Stage7AI from './stages/Stage7AI';
import Stage8Biodefense from './stages/Stage8Biodefense';
import Stage9Dashboard from './stages/Stage9Dashboard';
import { DASH_LANGS, DashLangContext, numLocale, type DashLang } from '@/lib/dashLang';
import { placeName } from '@/lib/observationNames';

const STAGES = [
  { id: 0, sub: 'SYNTHETIC',    ic: '🧬' },
  { id: 1, sub: 'PATIENT ZERO', ic: '🎯' },
  { id: 2, sub: 'CIVIC FIRST',  ic: '🧑‍🤝‍🧑' },
  { id: 3, sub: 'GLOBAL',        ic: '🌐' },
  { id: 4, sub: 'DOMESTIC',      ic: '🗺' },
  { id: 5, sub: 'NETWORK',       ic: '🕸' },
  { id: 6, sub: 'DEFENSE',       ic: '🛡' },
  { id: 7, sub: 'AI POLICY',     ic: '🧠' },
  { id: 8, sub: 'BIODEFENSE',    ic: '🦠' },
  { id: 9, sub: 'LIVE DATA', ic: '📡' },
];

/** 대시보드 틀 문구 — 3개 언어 (2026-11-16, ⑪). 단계 안의 시뮬레이션 화면은 아직 한국어(화면에 그렇게 적음). */
const T: Record<DashLang, {
  stages: string[]; brand: string; tagline: string; parallel: string;
  estate: [string, string, string]; origin: string; threat: string; response: string;
  threats: Record<'flu' | 'novel' | 'severe', string>; presets: Record<'none' | 'mild' | 'strong', string>;
  lives: (n: string) => string; livesLabel: string; scenario: string; integrated: string; from: (city: string, threat: string) => string;
  model: string; stat: Record<number, string>; tag: Record<number, string>; language: string; koOnly: string | null;
}> = {
  ko: {
    stages: ['합성위협 탐지', '발원지 추적', '민간 신호', '글로벌 유입', '국내 확산', '도착 예측', '방어 대응', 'AI 추론', '전략 비축', '실시간 대시보드'],
    brand: '역병예보', tagline: '10단계 통합 관제센터 · 합성위협 탐지 → 실시간 대시보드', parallel: '10단계 동시 추론',
    estate: ['✓ 방어 우세', '⚠ 억제', '⚠ 확산 위험'], origin: '해외 발원지', threat: '위협 강도', response: '대응 수준',
    threats: { flu: '계절 R₀2.2', novel: '신종 R₀2.8', severe: '고위험 R₀3.4' }, presets: { none: '무대응', mild: '중간', strong: '강력' },
    lives: (n) => `${n}명`, livesLabel: '구한 생명', scenario: '모델 시나리오', integrated: '통합 시나리오',
    from: (c, t) => `${c}발 ${t}`, model: '(모델)',
    stat: { 0: '스캔', 4: '+4주', 5: '전국', 7: '9단계', 8: '시뮬' }, tag: { 1: '시연', 2: '가정', 3: '추정', 6: '모델' },
    language: '언어', koOnly: null,
  },
  en: {
    stages: ['Synthetic threat detection', 'Origin tracing', 'Civic signals', 'Global import', 'Domestic spread', 'Arrival forecast', 'Defence response', 'AI reasoning', 'Strategic stockpile', 'Live dashboard'],
    brand: 'AEGIRON', tagline: '10-stage command centre · synthetic threat detection → live dashboard', parallel: '10 stages in parallel',
    estate: ['✓ Defence ahead', '⚠ Contained', '⚠ Spread risk'], origin: 'Overseas origin', threat: 'Threat level', response: 'Response level',
    threats: { flu: 'Seasonal R₀2.2', novel: 'Novel R₀2.8', severe: 'High-risk R₀3.4' }, presets: { none: 'None', mild: 'Moderate', strong: 'Strong' },
    lives: (n) => n, livesLabel: 'Lives saved', scenario: 'model scenario', integrated: 'Integrated scenario',
    from: (c, t) => `${t} from ${c}`, model: '(model)',
    stat: { 0: 'Scan', 4: '+4 wk', 5: 'Nationwide', 7: '9 steps', 8: 'Sim' }, tag: { 1: 'demo', 2: 'assumed', 3: 'estimate', 6: 'model' },
    language: 'Language',
    koOnly: 'The frame and the “What is actually observed now” panels are in English. The model-scenario screens inside each stage are still in Korean.',
  },
  fr: {
    stages: ['Détection des menaces synthétiques', 'Traçage de l’origine', 'Signaux citoyens', 'Importation mondiale', 'Propagation nationale', 'Prévision d’arrivée', 'Réponse de défense', 'Raisonnement IA', 'Stock stratégique', 'Tableau de bord en direct'],
    brand: 'AEGIRON', tagline: 'Centre de commandement en 10 étapes · détection des menaces synthétiques → tableau de bord en direct', parallel: '10 étapes en parallèle',
    estate: ['✓ Défense en avance', '⚠ Contenu', '⚠ Risque de propagation'], origin: 'Origine à l’étranger', threat: 'Niveau de menace', response: 'Niveau de réponse',
    threats: { flu: 'Saisonnier R₀2,2', novel: 'Nouveau R₀2,8', severe: 'Haut risque R₀3,4' }, presets: { none: 'Aucune', mild: 'Modérée', strong: 'Forte' },
    lives: (n) => n, livesLabel: 'Vies sauvées', scenario: 'scénario de modèle', integrated: 'Scénario intégré',
    from: (c, t) => `${t} depuis ${c}`, model: '(modèle)',
    stat: { 0: 'Scan', 4: '+4 sem', 5: 'National', 7: '9 étapes', 8: 'Sim' }, tag: { 1: 'démo', 2: 'hypothèse', 3: 'estimation', 6: 'modèle' },
    language: 'Langue',
    koOnly: 'Le cadre et les panneaux « Ce qui est réellement observé maintenant » sont en français. Les écrans de scénario de modèle à l’intérieur de chaque étape sont encore en coréen.',
  },
};

const THREAT_NAME: Record<'en' | 'fr', Record<'flu' | 'novel' | 'severe', string>> = {
  en: { flu: 'seasonal epidemic', novel: 'novel infection', severe: 'high-risk novel infection' },
  fr: { flu: 'épidémie saisonnière', novel: 'nouvelle infection', severe: 'nouvelle infection à haut risque' },
};

export default function Command({ initialLang = 'ko' }: { initialLang?: DashLang }) {
  const {
    origin, originsCatalog, threat, lev, stage, civicOn,
    pz, glob, savedLives, rt,
    setOrigin, setThreat, setPreset, setStage, recompute, loadOrigins,
  } = useStore();

  // 앱 시작 시 초기 계산 + 실제 전세계 국가 카탈로그 로드
  useEffect(() => { recompute(); loadOrigins(); }, []);
  // ?stage=N 딥링크 (데모·공유용) — 첫 마운트에만 읽는다.
  // 언어는 서버가 ?lang= 을 읽어 넘겨준다(첫 화면부터 그 언어 — 깜빡임 없음)
  const [lang, setLang] = useState<DashLang>(initialLang);
  useEffect(() => {
    const n = Number(new URLSearchParams(window.location.search).get('stage'));
    if (Number.isInteger(n) && n >= 0 && n <= 9) setStage(n);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    document.documentElement.lang = numLocale(lang);
  }, [lang]);
  const switchLang = (l: DashLang) => {
    const u = new URL(window.location.href);
    if (l === 'ko') u.searchParams.delete('lang');
    else u.searchParams.set('lang', l);
    window.history.replaceState(null, '', u.toString());
    setLang(l);
  };
  const t = T[lang];
  const nf = (n: number) => n.toLocaleString(numLocale(lang));

  const civicLead = Math.max(...CIVIC.filter(s => civicOn[s.id]).map(s => s.lead), 0);
  const stageStats: Record<number, string> = {
    0: t.stat[0],
    1: pz ? (pz.top.prob * 100).toFixed(0) + '%' : '—',
    2: 'D−' + civicLead,
    3: glob ? 'D+' + glob.arrival : 'D+—',
    4: t.stat[4],
    5: t.stat[5],
    6: savedLives >= 1000 ? (savedLives / 1000).toFixed(0) + 'k' : nf(savedLives),
    7: t.stat[7],
    8: t.stat[8],
    9: 'LIVE',
  };
  const rtSafe = currentRt(lev, threat);
  const estateText = rtSafe < 1 ? t.estate[0] : rtSafe < 1.5 ? t.estate[1] : t.estate[2];
  const estateCol = rtSafe < 1 ? 'var(--ok)' : rtSafe < 1.5 ? '#fbbf24' : '#ef4444';
  const city = originsCatalog.find(c => c.id === origin) ?? originsCatalog[0];
  const cityName = lang === 'ko' ? city.nm : (placeName(city.nm, lang) ?? city.nm);
  const threatName = lang === 'ko' ? THREAT[threat].nm : THREAT_NAME[lang][threat];

  const stageComponents = [
    <Stage0Synthetic key={0} />,
    <Stage1PatientZero key={1} />,
    <Stage2Civic key={2} />,
    <Stage3Global key={3} />,
    <Stage4Domestic key={4} />,
    <Stage5Network key={5} />,
    <Stage6Defense key={6} />,
    <Stage7AI key={7} />,
    <Stage8Biodefense key={8} />,
    <Stage9Dashboard key={9} />,
  ];

  return (
    <DashLangContext.Provider value={lang}>
    <div style={{ position: 'relative', zIndex: 1, maxWidth: 1320, margin: '0 auto', padding: 'clamp(14px,2.4vw,26px)' }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', borderBottom: '1px solid var(--line)', paddingBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            width: 42, height: 42, borderRadius: 11,
            background: 'radial-gradient(circle at 30% 30%,#1a2433,#0d1320)',
            border: '1px solid var(--line2)', display: 'grid', placeItems: 'center',
            position: 'relative', overflow: 'hidden',
          }}>
            <div style={{
              position: 'absolute', inset: 0,
              background: 'conic-gradient(from 0deg,transparent 0deg,var(--accent) 30deg,transparent 60deg)',
              animation: 'radar 3s linear infinite', opacity: .55,
            }} />
            <svg viewBox="0 0 24 24" fill="none" stroke="#f43f5e" strokeWidth="1.8" style={{ width: 22, height: 22, position: 'relative', zIndex: 2 }}>
              <circle cx="12" cy="12" r="2" />
              <circle cx="12" cy="12" r="6" opacity=".5" />
              <circle cx="12" cy="12" r="10" opacity=".25" />
            </svg>
          </div>
          <div>
            <h1 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(20px,2.6vw,26px)', letterSpacing: '-.02em', lineHeight: 1 }}>
              {t.brand} <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--accent)', verticalAlign: 'middle' }}>COMMAND</span>
            </h1>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', letterSpacing: '.18em', marginTop: 5 }}>
              {t.tagline}
            </div>
          </div>
        </div>
        <div style={{ textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 10 }}>
          <div style={{ fontSize: 13, color: estateCol }}>{estateText}</div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 9, letterSpacing: '.14em', marginTop: 4, color: 'var(--ok)' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--ok)', boxShadow: '0 0 8px var(--ok)', animation: 'blink 1.6s infinite' }} />
            {t.parallel}
          </div>
          <div role="group" aria-label={t.language} style={{ display: 'flex', justifyContent: 'flex-end', gap: 6, marginTop: 6 }}>
            {DASH_LANGS.map((l) => (
              <button key={l} type="button" onClick={() => switchLang(l)} aria-pressed={l === lang}
                style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.1em', padding: '3px 7px', borderRadius: 6, cursor: 'pointer',
                  border: `1px solid ${l === lang ? 'var(--accent)' : 'var(--line2)'}`, background: 'none', color: l === lang ? 'var(--txt)' : 'var(--muted)' }}>
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 시나리오 바 */}
      <div style={{
        display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end',
        margin: '16px 0 18px', padding: '14px 16px',
        background: 'var(--panel)', border: '1px solid var(--line)',
        borderRadius: 14, backdropFilter: 'blur(14px)',
        position: 'relative', zIndex: 20,
      }}>
        {/* 발원지 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.16em', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 6 }}>{t.origin}</span>
          <OriginSelector value={origin} origins={originsCatalog} onChange={setOrigin} />
        </div>

        {/* 위협 강도 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.16em', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 6 }}>{t.threat}</span>
          <div style={{ display: 'flex', background: 'var(--bg2)', border: '1px solid var(--line)', borderRadius: 9, overflow: 'hidden' }}>
            {(['flu', 'novel', 'severe'] as const).map(k => (
              <button key={k}
                onClick={() => setThreat(k)}
                style={{
                  fontFamily: 'var(--kr)', fontSize: 12, fontWeight: 600,
                  color: threat === k ? 'var(--txt)' : 'var(--muted)',
                  background: threat === k ? 'rgba(244,63,94,.16)' : 'none',
                  border: 'none', padding: '8px 12px', cursor: 'pointer',
                  transition: '.18s', whiteSpace: 'nowrap',
                }}
              >
                {t.threats[k]}
              </button>
            ))}
          </div>
        </div>

        {/* 대응 수준 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.16em', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 6 }}>{t.response}</span>
          <div style={{ display: 'flex', gap: 5 }}>
            {(['none', 'mild', 'strong'] as const).map(p => {
              const isActive = JSON.stringify(lev) === JSON.stringify(PRESETS[p]);
              return (
                <button key={p}
                  onClick={() => setPreset(p)}
                  style={{
                    fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--txt)',
                    background: isActive ? 'rgba(52,211,153,.16)' : 'rgba(255,255,255,.05)',
                    border: `1px solid ${isActive ? 'var(--ok)' : 'var(--line2)'}`,
                    borderRadius: 9, padding: '9px 12px', cursor: 'pointer',
                  }}
                >
                  {t.presets[p]}
                </button>
              );
            })}
          </div>
        </div>

        <div style={{ marginLeft: 'auto', textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted)' }}>
          <b style={{ color: 'var(--ok)', fontSize: 14, display: 'block' }}>{t.lives(nf(savedLives))}</b>
          {/* 이 숫자는 위 시나리오(발원지·위협·대응)를 넣은 SEIR 모델 값이다 — 실제로 구한 생명이 아니다. */}
          {t.livesLabel} · <span style={{ color: 'var(--amber)' }}>{t.scenario}</span>
        </div>
      </div>

      {/* 메인 레이아웃 */}
      <div className="shell">
        {/* 사이드바 */}
        <div className="sidenav" style={{ display: 'flex', flexDirection: 'column', gap: 6, position: 'sticky', top: 14, alignSelf: 'start', maxHeight: 'calc(100vh - 30px)', overflowY: 'auto', paddingRight: 4 }}>
          {STAGES.map(s => (
            <button key={s.id}
              onClick={() => setStage(s.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 11,
                padding: '12px 13px',
                background: s.id === stage ? 'linear-gradient(135deg,rgba(244,63,94,.14),rgba(14,22,35,.6))' : 'var(--panel)',
                border: `1px solid ${s.id === stage ? 'var(--accent)' : 'var(--line)'}`,
                borderRadius: 12, cursor: 'pointer', textAlign: 'left',
                width: '100%', color: s.id === stage ? 'var(--txt)' : 'var(--muted)',
                transition: '.22s', position: 'relative',
              }}
            >
              <div style={{
                position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)',
                width: 3, height: s.id === stage ? '60%' : 0,
                background: 'var(--accent)', borderRadius: '0 2px 2px 0', transition: '.25s',
              }} />
              <div style={{
                width: 28, height: 28, borderRadius: 8,
                background: s.id === stage ? 'var(--accent)' : 'var(--bg2)',
                border: `1px solid ${s.id === stage ? 'var(--accent)' : 'var(--line2)'}`,
                display: 'grid', placeItems: 'center',
                fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 12,
                color: s.id === stage ? '#fff' : 'var(--muted)', flexShrink: 0,
              }}>
                {s.id}
              </div>
              <div>
                <div style={{ fontFamily: 'var(--disp)', fontWeight: 700, fontSize: 13, color: 'var(--txt)', lineHeight: 1.15 }}>
                  {s.ic} {t.stages[s.id]}
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 8.5, color: 'var(--muted)', marginTop: 2, letterSpacing: '.06em' }}>{s.sub}</div>
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, marginLeft: 'auto', flexShrink: 0, textAlign: 'right', whiteSpace: 'nowrap' }}>
                <b style={{ display: 'block', fontSize: 12, color: 'var(--ok)' }}>{stageStats[s.id]}</b>
                {t.tag[s.id] ?? ''}
              </div>
            </button>
          ))}

          <div style={{ marginTop: 6, padding: 12, background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 12, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)', lineHeight: 1.6 }}>
            <b style={{ color: 'var(--ok)' }}>{t.integrated}</b><br />
            {t.from(cityName, threatName)}<br />
            {t.livesLabel} <b style={{ color: 'var(--ok)' }}>{t.lives(nf(savedLives))}</b> <span style={{ color: 'var(--amber)' }}>{t.model}</span>
          </div>
        </div>

        {/* 컨텐츠 */}
        <div style={{ minWidth: 0 }}>
          {t.koOnly && (
            <p lang={numLocale(lang)} style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--amber)', margin: '0 0 12px', lineHeight: 1.6 }}>
              {t.koOnly}
            </p>
          )}
          {stageComponents[stage]}
        </div>
      </div>

      <style>{`
        .ptitle { font-family: var(--disp); font-weight: 800; font-size: clamp(18px,2.3vw,24px); letter-spacing: -.02em; line-height: 1.15; margin-bottom: 4px; }
        .psub { font-family: var(--mono); font-size: 11px; color: var(--muted); letter-spacing: .04em; margin-bottom: 18px; line-height: 1.6; }
        .card { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: clamp(14px,2vw,20px); backdrop-filter: blur(14px); }
        .card + .card { margin-top: 14px; }
        .card-h { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 10px; flex-wrap: wrap; }
        .lbl { font-family: var(--mono); font-size: 10px; letter-spacing: .18em; color: var(--muted); text-transform: uppercase; }
        .grid2 { display: grid; grid-template-columns: 1.4fr 1fr; gap: 14px; }
        .shell { display: grid; grid-template-columns: 240px 1fr; gap: 18px; }
        .rank-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 14px; }
        .grm-wrap { height: 260px; }
        @media(max-width:760px) {
          .shell { grid-template-columns: 1fr; }
          .sidenav { position: static !important; max-height: none !important; overflow-y: visible !important; }
          .rank-grid { grid-template-columns: 1fr; }
          .grm-wrap { height: 200px; }
        }
        .oc { border-radius: 12px; padding: 11px; border: 1px solid var(--line); background: rgba(255,255,255,.025); }
        .ok { font-size: 10.5px; color: var(--muted); display: flex; align-items: center; gap: 5px; }
        .ov { font-family: var(--mono); font-weight: 700; font-size: 19px; margin-top: 5px; }
        .od { font-family: var(--mono); font-size: 9px; margin-top: 2px; color: var(--muted2); }
        .outcomes { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 4px; }
        @media(max-width:760px) { .grid2 { grid-template-columns: 1fr; } }
      `}</style>
    </div>
    </DashLangContext.Provider>
  );
}
