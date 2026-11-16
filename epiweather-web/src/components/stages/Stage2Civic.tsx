'use client';
import { useStore } from '@/lib/store';
import { CIVIC } from '@/lib/algorithms';
import LiveObserved from './LiveObserved';
import { useDashLang, useT } from '@/lib/dashLang';
import { nameOf } from '@/lib/dashNames';

// ★ 2026-10-18 ★ 예전엔 여기서 localhost:8000(하드코딩)의 '2020 COVID 백테스트'를 불러
// "✅ 실측 검증 — 검색이 대구 집단감염보다 28일 먼저" 를 띄웠다. 운영에선 늘 연결 거부였고,
// 설령 열렸어도 그 결과는 선행 근거가 아니다 — 검색 급증일(2020-01-20)이 국내 첫 확진 발표일과
// 같아 '첫 확진 대비 선행 0일'이다(마스크는 -7일). 뉴스를 따라간 것이지 앞선 게 아니다.
// 그래서 호출과 카드를 지우고, 아래 선행일수가 가정값이라는 것을 상시로 적는다.

export default function Stage2Civic() {
  const { civicOn, toggleCivic } = useStore();
  const tr = useT();
  const lang = useDashLang();
  const active = CIVIC.filter(s => civicOn[s.id]);
  const lead = active.length ? Math.max(...active.map(s => s.lead)) : 0;

  return (
    <div style={{ animation: 'fade .25s' }}>
      <div className="ptitle">{tr('민간 우선 신호망', 'Civic-first signal network', 'Réseau de signaux citoyens')}</div>
      <div className="psub">
        {tr('코로나의 교훈 — 정부 발표는 늦었다. 아래 다섯 가지 민간 신호(자가증상·하수·OTC·키트·검사소)가 그 공백을 메울 수 있는지를 보는 시나리오입니다. 신호별 선행일수는 데이터 파트너십 전까지의 가정값이며, 아직 실측으로 검증된 신호는 없습니다.',
          'The COVID lesson: official announcements came late. This scenario asks whether the five civic signals below (self-reported symptoms, wastewater, OTC, test kits, labs) could fill that gap. Lead times per signal are assumed values until data partnerships exist; no signal has been verified by measurement yet.',
          'La leçon du COVID : les annonces officielles sont arrivées tard. Ce scénario examine si les cinq signaux citoyens ci-dessous (symptômes, eaux usées, sans ordonnance, autotests, laboratoires) pourraient combler ce retard. Les délais d’avance sont des hypothèses en attendant des partenariats de données ; aucun signal n’a encore été vérifié par la mesure.')}
      </div>
      <LiveObserved stage={2} />
      <div className="card">
        {/* 히어로 배너 */}
        <div style={{
          padding: 16, borderRadius: 13,
          background: 'linear-gradient(135deg,rgba(167,139,250,.10),rgba(18,25,37,.5))',
          border: '1px solid var(--line2)',
          display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap',
        }}>
          <div style={{ flex: 1, minWidth: 260, fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 16, lineHeight: 1.3 }}>
            {tr('시민·민간 신호 융합 —', 'Citizen and civic signals combined —', 'Signaux citoyens combinés —')}{' '}
            <b style={{ color: 'var(--violet)' }}>{tr('정부 D-0보다 먼저', 'ahead of the government’s D-0', 'avant le J-0 officiel')}</b>
          </div>
          <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 34, color: 'var(--violet)', textAlign: 'right' }}>
            +{lead}{tr('일', 'd', ' j')}
            <small style={{ display: 'block', fontSize: 9.5, color: 'var(--muted)', letterSpacing: '.14em', marginTop: 2 }}>{tr('정부 대비 선행 · 가정값', 'lead over government · assumed', 'avance sur l’officiel · hypothèse')}</small>
          </div>
        </div>

        {/* 상시 고지 — 선행일수는 가정값 */}
        <div style={{ marginTop: 12, padding: '9px 13px', borderRadius: 11, background: 'rgba(251,191,36,.06)', border: '1px solid rgba(251,191,36,.3)', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', lineHeight: 1.6 }}>
          ⚠ {tr('아래 신호별 선행일수(D−14 등)는 시나리오 가정값이며 실측이 아닙니다. 민간 신호가 정부 발표보다 앞선다는 것을 검증한 기록은 아직 없습니다.',
            'The lead times below (D−14 etc.) are scenario assumptions, not measurements. There is no record yet verifying that civic signals precede official announcements.',
            'Les délais ci-dessous (J−14, etc.) sont des hypothèses de scénario, pas des mesures. Aucun relevé ne vérifie encore que les signaux citoyens précèdent les annonces officielles.')}
        </div>

        {/* 신호 목록 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 14 }}>
          {CIVIC.map(s => {
            const off = !civicOn[s.id];
            return (
              <div key={s.id}
                onClick={() => toggleCivic(s.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 11,
                  padding: '10px 12px',
                  background: 'rgba(255,255,255,.025)',
                  border: '1px solid var(--line)',
                  borderRadius: 10, cursor: 'pointer',
                  opacity: off ? .35 : 1,
                }}
              >
                <div style={{
                  width: 30, height: 30, borderRadius: 8,
                  background: `${s.col}22`, color: s.col,
                  display: 'grid', placeItems: 'center', fontSize: 15,
                }}>
                  {s.ic}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 700 }}>{nameOf(s.nm, lang)}</div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', marginTop: 1 }}>
                    {s.sub} · {tr('품질', 'quality', 'qualité')} {Math.round(s.q * 100)} · {tr('볼륨', 'volume', 'volume')} {Math.round(s.v * 100)}
                  </div>
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, textAlign: 'right' }}>
                  <div style={{ fontSize: 16, color: 'var(--violet)' }}>D−{s.lead}</div>
                  <div style={{ fontSize: 8.5, color: 'var(--muted)' }}>{tr('선행', 'lead', 'avance')}</div>
                </div>
              </div>
            );
          })}

          {/* 정부 기준선 */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 11,
            padding: '10px 12px',
            background: 'rgba(255,255,255,.025)',
            border: '1px solid rgba(239,68,68,.4)',
            borderRadius: 10, opacity: .7,
          }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8,
              background: 'rgba(239,68,68,.15)', color: '#ef4444',
              display: 'grid', placeItems: 'center', fontSize: 15,
            }}>
              🏛
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12.5, fontWeight: 700 }}>{tr('정부 공식 발표', 'Official government announcement', 'Annonce officielle')}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted)', marginTop: 1 }}>GOV · {tr('기준선', 'baseline', 'référence')}</div>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, textAlign: 'right' }}>
              <div style={{ fontSize: 16, color: '#ef4444' }}>D-0</div>
              <div style={{ fontSize: 8.5, color: 'var(--muted)' }}>{tr('기준', 'base', 'réf.')}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
