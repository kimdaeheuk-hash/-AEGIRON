'use client';
import Link from 'next/link';

const LAYERS = [
  {
    n: '01',
    tag: 'DATA COLLECTION',
    title: '데이터 수집층',
    color: 'var(--cyan)',
    body: '전 세계 21개 실시간 소스를 1시간 주기로 수집합니다. WHO·CDC 공식 통계, 179개국 현지어 뉴스(Google News RSS), 기후·산림파괴 위성 데이터(NASA FIRMS), 유전체 계통 분석(Nextstrain), 항공편·공급망·SNS 신호까지 — 대부분 무료 공개 API이며, 수집 실패 시 소스별 상태를 자동 추적해 "조용한 실패"를 방지합니다.',
    items: ['WHO / CDC / KDCA / HK CHP / Japan IDWR', '179개국 현지어 뉴스 (Google News RSS)', 'NASA FIRMS · Global Forest Watch (환경 선행지표)', 'Nextstrain (유전체 계통) · WAHIS (동물질병)', 'Mastodon · Google Trends · medRxiv 프리프린트'],
  },
  {
    n: '02',
    tag: 'ANOMALY DETECTION',
    title: '신호 처리 · 이상탐지층',
    color: 'var(--violet)',
    body: '수집된 원시 데이터를 z-score 기반 이상도로 변환하고, 소스별 신뢰도(WHO 1.00 ~ 미확인 출처 0.10)를 가중해 단일 위험지수(GAI)로 합산합니다. 신호 "급증"뿐 아니라 "급감"(보고체계 붕괴 신호)도 함께 감지하며, 저평균·계절성 지표는 오탐 방지를 위해 판정 대상에서 자동 제외합니다.',
    items: ['GAI (Global Anomaly Index) — 6계층 가중합산', '5분 내 1차 탐지(Sentinel) → 실검색 재확인', '증상군집(출혈열·호흡기 등) 동시급등 탐지', '경보 피로 방지 — 일일 등급별 상한'],
  },
  {
    n: '03',
    tag: 'INFERENCE + SIMULATION',
    title: '추론 · 시뮬레이션층',
    color: 'var(--accent)',
    body: '아이기론의 핵심 차별점입니다. 선형회귀+EWMA 앙상블로 7·14일 위험을 예측하고, 항공노선 데이터 기반 다도시 SEIR 모델로 확산을 시뮬레이션하며, 질병별 원인→결과 인과체인을 지식그래프로 추론합니다. 이 방법론들은 Imperial College London(CovidSim, MRIIDS 2.0)과 Northeastern MOBS Lab(GLEAM)이 10년 넘게 학술적으로 검증해 온 역학 모델링 접근을 기반으로 하며, 이를 실시간 상업 제품으로 패키징한 것이 아이기론의 위치입니다.',
    items: ['forecast_engine — 7/14일 위험도 예측', 'digital_twin — 다도시 SEIR 확산 시뮬레이션', 'knowledge_graph — 질병별 인과체인 추론', 'risk_quantification — 보험·재보험사용 노출지수', 'ai_inference — Claude 기반 통합 정책분석(RAG)'],
  },
  {
    n: '04',
    tag: 'VERIFICATION',
    title: '검증 · 투명성층',
    color: 'var(--ok)',
    body: '아이기론은 정확도를 마케팅하지 않고, 검증 과정 자체를 공개합니다. 실제 발병 이력을 기준점 삼아 백테스트를 수행하고, 단일 임계값이 아니라 여러 민감도 결과를 함께 보여줘 숫자를 임의로 유리하게 고르지 못하도록 설계했습니다. 경쟁사(BlueDot 등) 공개 수치와의 비교 벤치마크 모듈도 내장돼 있습니다.',
    items: ['historical_backtest — 실제 발병 이력 기준 검증', 'benchmark_baselines — 경쟁사 대비 정직성 비교', 'sentinel — AI 판정 vs 사람 판정 분리 기록', 'source_health — 소스별 연속실패·신선도 추적'],
  },
];

export default function Methodology() {
  return (
    <div style={{ position: 'relative', zIndex: 1, maxWidth: 1100, margin: '0 auto', padding: 'clamp(14px,2.4vw,26px)' }}>
      {/* 네비 */}
      <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 0' }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <Logo size={30} />
          <span style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 16, color: 'var(--txt)' }}>AEGIRON</span>
        </Link>
        <Link href="/dashboard" style={{
          fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--txt)', textDecoration: 'none',
          border: '1px solid var(--line2)', borderRadius: 9, padding: '9px 16px', background: 'var(--panel)',
        }}>
          라이브 대시보드 →
        </Link>
      </nav>

      {/* 헤더 */}
      <div style={{ padding: '40px 0 50px', borderBottom: '1px solid var(--line)' }}>
        <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.18em', color: 'var(--accent)', marginBottom: 14 }}>METHODOLOGY</div>
        <h1 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(28px,4vw,44px)', letterSpacing: '-.02em', lineHeight: 1.15, marginBottom: 20 }}>
          아이기론의 추론 엔진이<br />어떻게 작동하는가
        </h1>
        <p style={{ fontFamily: 'var(--kr)', fontSize: 15, color: 'var(--muted)', lineHeight: 1.8, maxWidth: 680 }}>
          데이터가 수집돼 예측·시뮬레이션 결과로 나오기까지, 4개 층을 거칩니다.
          사용하는 데이터 소스, 추론 방식, 검증 방법론을 전부 공개합니다.
        </p>
      </div>

      {/* 4개 층 */}
      <div style={{ padding: '50px 0' }}>
        {LAYERS.map((l, i) => (
          <div key={l.n} style={{ display: 'flex', gap: 28, marginBottom: i < LAYERS.length - 1 ? 48 : 0 }}>
            <div style={{ flexShrink: 0, width: 56, textAlign: 'center' }}>
              <div style={{
                fontFamily: 'var(--mono)', fontWeight: 800, fontSize: 20, color: l.color,
                width: 56, height: 56, borderRadius: 16, display: 'grid', placeItems: 'center',
                border: `1px solid ${l.color}44`, background: `${l.color}0d`,
              }}>
                {l.n}
              </div>
              {i < LAYERS.length - 1 && (
                <div style={{ width: 1, flex: 1, minHeight: 40, background: 'var(--line)', margin: '10px auto 0' }} />
              )}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.16em', color: l.color, marginBottom: 8 }}>{l.tag}</div>
              <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 22, marginBottom: 12 }}>{l.title}</h2>
              <p style={{ fontFamily: 'var(--kr)', fontSize: 14, color: 'var(--muted)', lineHeight: 1.8, marginBottom: 18, maxWidth: 680 }}>{l.body}</p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 8 }}>
                {l.items.map(it => (
                  <div key={it} style={{
                    display: 'flex', alignItems: 'center', gap: 9, padding: '9px 13px',
                    background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 10,
                  }}>
                    <span style={{ width: 4, height: 4, borderRadius: '50%', background: l.color, flexShrink: 0 }} />
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--txt)' }}>{it}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 정직성 노트 */}
      <div style={{
        background: 'var(--panel)', border: '1px solid var(--line2)', borderRadius: 18,
        padding: 'clamp(22px,3vw,32px)', margin: '10px 0 60px',
      }}>
        <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.16em', color: 'var(--amber)', marginBottom: 12 }}>
          ⚠ A NOTE ON HONESTY
        </div>
        <p style={{ fontFamily: 'var(--kr)', fontSize: 13.5, color: 'var(--muted)', lineHeight: 1.85, maxWidth: 720 }}>
          아이기론은 2026년 가동을 시작한 시스템으로, 예측 정확도에 대한 장기 검증 데이터는
          아직 축적되는 과정에 있습니다. 저희는 검증되지 않은 정확도 수치를 마케팅에 쓰지
          않으며, 대신 검증 방법론과 백테스트 과정 자체를 투명하게 공개하는 쪽을 택했습니다.
          실시간 데이터 수집은 21개 소스 전부가 정상 가동 중이며, 트랙레코드는 시간이 지날수록
          축적됩니다.
        </p>
      </div>

      {/* CTA */}
      <div style={{ textAlign: 'center', padding: '20px 0 60px' }}>
        <Link href="/dashboard" style={{
          fontFamily: 'var(--kr)', fontWeight: 700, fontSize: 14, color: '#fff', textDecoration: 'none',
          background: 'linear-gradient(135deg, var(--accent), #d61f52)',
          borderRadius: 11, padding: '15px 30px', display: 'inline-block',
          boxShadow: '0 8px 30px rgba(244,63,94,.28)',
        }}>
          라이브 대시보드에서 직접 확인하기
        </Link>
      </div>
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
