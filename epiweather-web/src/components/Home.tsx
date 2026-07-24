'use client';
import Link from 'next/link';

const STATS = [
  { v: '21', l: '실시간 데이터 소스', s: 'WHO·CDC·현지어뉴스·기후·위성' },
  { v: '79', l: 'API 엔드포인트', s: '조기경보 · 예측 · 시뮬레이션' },
  { v: '217', l: '국가 참조 데이터', s: 'World Bank 기반 취약성 지수' },
  { v: '179', l: '현지어 뉴스 커버리지', s: '국가 수, 최초 보도 포착' },
];

const REASONS = [
  {
    ic: '🧠',
    tag: 'PREDICT + SIMULATE',
    title: '예측과 시뮬레이션까지 통합한 엔진',
    body:
      '7·14일 위험 예측, 다도시 SEIR 확산 시뮬레이션, 질병별 인과체인 추론까지 — Imperial College London·Northeastern MOBS Lab 등 세계 최고 연구기관이 10년 넘게 검증해 온 역학 모델링 방법론을, 실제 상업 제품으로 패키징한 곳은 아이기론이 유일합니다.',
  },
  {
    ic: '🌍',
    tag: 'BLIND SPOT COVERAGE',
    title: '대형 경쟁사가 놓치는 사각지대',
    body:
      '나이지리아·에티오피아·예멘·마다가스카르·파푸아뉴기니 — 상업성이 낮아 선진국 중심 경쟁사들이 잘 가지 않는 오지·취약국가까지, 179개국 현지어 뉴스로 국제언론보다 먼저 최초 보도를 포착합니다.',
  },
  {
    ic: '🔍',
    tag: 'RADICAL TRANSPARENCY',
    title: '정확도를 마케팅하지 않습니다',
    body:
      '지표별 신뢰도 자가진단, AI-사람 판정 일치율 실측 추적, 경쟁사 대비 정직성 벤치마크까지 시스템 안에 내장돼 있습니다. 증명되지 않은 숫자는 내세우지 않고, 검증 과정 자체를 공개합니다.',
  },
  {
    ic: '📊',
    tag: 'RISK QUANTIFICATION',
    title: '보험업계가 이해하는 언어로',
    body:
      '재보험사·항공사·인도지원기구를 위한 국가별 노출지수(Exposure Index) — 신호강도·취약성·확산잠재력을 가중합산해 리스크를 숫자로 계량화합니다.',
  },
];

const ENGINES = [
  { nm: 'forecast_engine', d: '선형회귀 + EWMA 앙상블 7/14일 예측' },
  { nm: 'digital_twin', d: '항공노선 기반 다도시 SEIR 확산 시뮬레이션' },
  { nm: 'knowledge_graph', d: '질병별 원인→결과 인과체인 추론' },
  { nm: 'risk_quantification', d: '보험·재보험사용 노출지수 계량화' },
  { nm: 'ai_inference', d: 'Claude 기반 통합 정책분석 (RAG)' },
  { nm: 'benchmark_baselines', d: '경쟁사 대비 정직성 벤치마크' },
];

export default function Home() {
  return (
    <div style={{ position: 'relative', zIndex: 1 }}>
      {/* ── 네비 ───────────────────────────────────────────── */}
      <nav
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          maxWidth: 1320, margin: '0 auto', padding: '20px clamp(14px,2.4vw,26px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Logo size={34} />
          <span style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 18, letterSpacing: '-.02em' }}>
            AEGIRON
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 22, fontFamily: 'var(--mono)', fontSize: 12 }}>
          <Link href="/methodology" style={{ color: 'var(--muted)', textDecoration: 'none' }}>방법론</Link>
          <Link
            href="/dashboard"
            style={{
              color: 'var(--txt)', textDecoration: 'none', border: '1px solid var(--line2)',
              borderRadius: 9, padding: '9px 16px', background: 'var(--panel)',
            }}
          >
            라이브 대시보드 →
          </Link>
        </div>
      </nav>

      {/* ── 히어로 ─────────────────────────────────────────── */}
      <section style={{ position: 'relative', maxWidth: 1320, margin: '0 auto', padding: 'clamp(40px,8vw,110px) clamp(14px,2.4vw,26px) 60px', overflow: 'hidden' }}>
        <HeroBackdrop />
        <div style={{ position: 'relative', zIndex: 2, maxWidth: 780 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8, fontFamily: 'var(--mono)', fontSize: 11,
            letterSpacing: '.16em', color: 'var(--ok)', border: '1px solid rgba(52,211,153,.3)',
            borderRadius: 999, padding: '6px 14px', marginBottom: 22, background: 'rgba(52,211,153,.06)',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--ok)', boxShadow: '0 0 8px var(--ok)', animation: 'blink 1.6s infinite' }} />
            21개 소스 실시간 가동 중
          </div>

          <h1 style={{
            fontFamily: 'var(--disp)', fontWeight: 800, letterSpacing: '-.03em', lineHeight: 1.08,
            fontSize: 'clamp(34px,5.4vw,62px)', marginBottom: 22,
          }}>
            경보를 넘어,<br />
            <span style={{ color: 'var(--accent)' }}>예측</span>과{' '}
            <span style={{ color: 'var(--cyan)' }}>시뮬레이션</span>까지
          </h1>

          <p style={{ fontFamily: 'var(--kr)', fontSize: 'clamp(14px,1.6vw,17px)', color: 'var(--muted)', lineHeight: 1.75, marginBottom: 36, maxWidth: 640 }}>
            아이기론(AEGIRON)은 감염병이 국제 뉴스가 되기 전, 21개 실시간 데이터 소스를 종합해
            국가별 리스크를 계산하고 7·14일 앞을 예측하며 확산을 시뮬레이션하는
            AI 감염병 인텔리전스 시스템입니다.
          </p>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <Link href="/dashboard" style={{
              fontFamily: 'var(--kr)', fontWeight: 700, fontSize: 14, color: '#fff', textDecoration: 'none',
              background: 'linear-gradient(135deg, var(--accent), #d61f52)',
              borderRadius: 11, padding: '14px 24px', boxShadow: '0 8px 30px rgba(244,63,94,.28)',
            }}>
              라이브 대시보드 보기
            </Link>
            <Link href="/methodology" style={{
              fontFamily: 'var(--kr)', fontWeight: 700, fontSize: 14, color: 'var(--txt)', textDecoration: 'none',
              background: 'var(--panel)', border: '1px solid var(--line2)', borderRadius: 11, padding: '14px 24px',
            }}>
              방법론 자세히 보기
            </Link>
          </div>
        </div>
      </section>

      {/* ── 통계 스트립 ────────────────────────────────────── */}
      <section style={{ maxWidth: 1320, margin: '0 auto', padding: '0 clamp(14px,2.4vw,26px) 70px' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 1,
          background: 'var(--line)', border: '1px solid var(--line)', borderRadius: 18, overflow: 'hidden',
        }}>
          {STATS.map(s => (
            <div key={s.l} style={{ background: 'var(--panel)', padding: '26px 22px' }}>
              <div style={{ fontFamily: 'var(--mono)', fontWeight: 800, fontSize: 'clamp(30px,3.4vw,42px)', color: 'var(--txt)', lineHeight: 1 }}>
                {s.v}<span style={{ fontSize: 16, color: 'var(--muted2)' }}>+</span>
              </div>
              <div style={{ fontFamily: 'var(--kr)', fontWeight: 700, fontSize: 13, marginTop: 10 }}>{s.l}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)', marginTop: 4, letterSpacing: '.02em' }}>{s.s}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── 왜 아이기론인가 ────────────────────────────────── */}
      <section style={{ maxWidth: 1320, margin: '0 auto', padding: '0 clamp(14px,2.4vw,26px) 80px' }}>
        <SectionHeading eyebrow="WHY AEGIRON" title="왜 아이기론인가" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginTop: 30 }}>
          {REASONS.map(r => (
            <div key={r.title} style={{
              background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 18,
              padding: 26, backdropFilter: 'blur(14px)',
            }}>
              <div style={{ fontSize: 26, marginBottom: 14 }}>{r.ic}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.16em', color: 'var(--accent)', marginBottom: 8 }}>{r.tag}</div>
              <h3 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 17, marginBottom: 10, lineHeight: 1.3 }}>{r.title}</h3>
              <p style={{ fontFamily: 'var(--kr)', fontSize: 13, color: 'var(--muted)', lineHeight: 1.7 }}>{r.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── 방법론 티저 ────────────────────────────────────── */}
      <section style={{ maxWidth: 1320, margin: '0 auto', padding: '0 clamp(14px,2.4vw,26px) 90px' }}>
        <div style={{
          background: 'linear-gradient(135deg, rgba(56,189,248,.08), rgba(14,22,35,.6))',
          border: '1px solid var(--line2)', borderRadius: 22, padding: 'clamp(28px,4vw,48px)',
          display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 32, alignItems: 'center',
        }}>
          <div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.16em', color: 'var(--cyan)', marginBottom: 10 }}>HOW IT WORKS</div>
            <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(22px,2.6vw,30px)', lineHeight: 1.25, marginBottom: 16 }}>
              어떻게 가능한가
            </h2>
            <p style={{ fontFamily: 'var(--kr)', fontSize: 14, color: 'var(--muted)', lineHeight: 1.75, marginBottom: 22 }}>
              신호 수집부터 예측·시뮬레이션까지, 50개 이상의 알고리즘 모듈이
              계층적으로 연결돼 있습니다. 데이터 소스, 추론 방식, 검증 방법론까지
              전부 공개합니다.
            </p>
            <Link href="/methodology" style={{
              fontFamily: 'var(--kr)', fontWeight: 700, fontSize: 13, color: 'var(--cyan)', textDecoration: 'none',
              display: 'inline-flex', alignItems: 'center', gap: 6,
            }}>
              전체 기술 방법론 보기 →
            </Link>
          </div>
          <div style={{ display: 'grid', gap: 8 }}>
            {ENGINES.map(e => (
              <div key={e.nm} style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '11px 14px',
                background: 'var(--panel2)', border: '1px solid var(--line)', borderRadius: 11,
              }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--cyan)', boxShadow: '0 0 6px var(--cyan)', flexShrink: 0 }} />
                <code style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--txt)', flexShrink: 0 }}>{e.nm}</code>
                <span style={{ fontFamily: 'var(--kr)', fontSize: 11.5, color: 'var(--muted2)' }}>{e.d}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 푸터 ───────────────────────────────────────────── */}
      <footer style={{ borderTop: '1px solid var(--line)', padding: 'clamp(24px,3vw,36px) clamp(14px,2.4vw,26px)' }}>
        <div style={{
          maxWidth: 1320, margin: '0 auto', display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', flexWrap: 'wrap', gap: 14,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Logo size={22} />
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>
              AEGIRON — AI Infectious Disease Intelligence
            </span>
          </div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>
            © 2026 AEGIRON. Busan, South Korea.
          </div>
        </div>
      </footer>

      <style>{`
        @media (max-width: 760px) {
          section > div[style*="grid-template-columns: 1.1fr 1fr"] { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}

function SectionHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.18em', color: 'var(--accent)', marginBottom: 10 }}>{eyebrow}</div>
      <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(24px,3vw,34px)', letterSpacing: '-.02em' }}>{title}</h2>
    </div>
  );
}

function Logo({ size = 32 }: { size?: number }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: size * 0.32,
      background: 'radial-gradient(circle at 30% 30%,#1a2433,#0d1320)',
      border: '1px solid var(--line2)', display: 'grid', placeItems: 'center',
      position: 'relative', overflow: 'hidden', flexShrink: 0,
    }}>
      <div style={{
        position: 'absolute', inset: 0,
        background: 'conic-gradient(from 0deg,transparent 0deg,var(--accent) 30deg,transparent 60deg)',
        animation: 'radar 3s linear infinite', opacity: .55,
      }} />
      <svg viewBox="0 0 24 24" fill="none" stroke="#f43f5e" strokeWidth="1.8" style={{ width: size * 0.6, height: size * 0.6, position: 'relative', zIndex: 2 }}>
        <circle cx="12" cy="12" r="2" />
        <circle cx="12" cy="12" r="6" opacity=".5" />
        <circle cx="12" cy="12" r="10" opacity=".25" />
      </svg>
    </div>
  );
}

/** 히어로 배경 — 전세계 네트워크 느낌의 점·연결선 + 레이더 스윕 */
function HeroBackdrop() {
  const dots = [
    [8, 22], [18, 12], [30, 30], [42, 8], [55, 24], [68, 14], [80, 32], [92, 18],
    [14, 46], [26, 58], [38, 44], [50, 62], [63, 48], [75, 60], [88, 46],
    [10, 74], [22, 82], [34, 70], [48, 86], [60, 76], [72, 84], [84, 72],
  ];
  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 0, opacity: .55, pointerEvents: 'none' }}>
      <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" style={{ width: '100%', height: '100%' }}>
        <defs>
          <radialGradient id="fade" cx="50%" cy="30%" r="70%">
            <stop offset="0%" stopColor="#f43f5e" stopOpacity=".5" />
            <stop offset="100%" stopColor="#f43f5e" stopOpacity="0" />
          </radialGradient>
        </defs>
        {dots.map(([x, y], i) => (
          dots.slice(i + 1, i + 3).map(([x2, y2], j) => (
            <line key={`${i}-${j}`} x1={x} y1={y} x2={x2} y2={y2} stroke="var(--line2)" strokeWidth=".15" />
          ))
        ))}
        {dots.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={i % 5 === 0 ? 0.9 : 0.5}
            fill={i % 7 === 0 ? 'var(--cyan)' : i % 5 === 0 ? 'var(--accent)' : 'var(--muted2)'}
            opacity={i % 5 === 0 ? 1 : .6}
          >
            {i % 5 === 0 && <animate attributeName="opacity" values="1;.3;1" dur={`${2 + (i % 4)}s`} repeatCount="indefinite" />}
          </circle>
        ))}
        <circle cx="50" cy="30" r="45" fill="url(#fade)" />
      </svg>
    </div>
  );
}
