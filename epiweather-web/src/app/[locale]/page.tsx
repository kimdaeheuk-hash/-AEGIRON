import Link from 'next/link';
import { getDictionary, localePath, isLocale, type Locale } from '@/i18n';
import type { EngineDict, EngineMode } from '@/i18n/types';
import { Section, SectionHeading, Card, Grid } from '@/components/site/Section';
import { HeroBackdrop } from '@/components/site/HeroBackdrop';
import { IntroVideo } from '@/components/site/IntroVideo';
import { PhotoFigure } from '@/components/site/PhotoFigure';
import { getSourceHealth, type SourceHealthSummary } from '@/lib/status';
import { introVideo } from '@/lib/video';

/**
 * 홈.
 *
 * ## 2026-10-18 — 히어로·엔진 구성 재작성 (2026-08-06 캡틴 지시서 2단계)
 * 08-06 검수에서 '완전 공개' 히어로는 공개 정책이지 제품이 아니라는 판정을 받았다.
 * 원본 문구("경보를 넘어, 예측과 시뮬레이션까지")와 처음 홈의 배경을 되살리고, 첫 화면
 * 바로 아래에 **실제 엔진**을 둔다.
 *
 * 엔진마다 가동 방식(매시·매일·경보 시·요청 시)을 단다. 상시 도는 것과 부를 때만 도는
 * 것을 같은 무게로 적으면 그 자체로 과장이다. 지시서가 히어로에 넣으라던 '발원지 격자
 * 추론'(patient_zero)은 넣지 않았다 — 그 모듈은 난수로 숨긴 정답을 합성 신호로 되맞히는
 * 시연이라 실데이터 추론이라고 쓸 수 없다.
 *
 * 가동 배지는 고정 문구가 아니라 `/api/status` 실측값이다. 못 읽으면 초록 불을 켜지 않는다.
 *
 * ★ 절대 규칙 ★ 정확도·선행일수 주장 금지.
 */

export default async function HomePage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const dict = getDictionary(locale);
  const t = dict.home;
  const health = await getSourceHealth();
  const video = introVideo();

  return (
    <>
      {/* ── 히어로 ─────────────────────────────────────────── */}
      {/* hero-band: 밝은 배색에서도 첫 화면만 어두운 띠로 둘 수 있게 토큰을 갈아 끼운다(globals.css). */}
      <div className="hero-band">
      <section
        style={{
          position: 'relative', maxWidth: 1320, margin: '0 auto', overflow: 'hidden',
          padding: 'clamp(48px,8vw,110px) clamp(14px,2.4vw,26px) clamp(36px,5vw,60px)',
        }}
      >
        <HeroBackdrop />
        {/* keep-all: 한국어가 줄 끝에서 낱말 중간('경/보')에 끊기지 않게 한다. */}
        <div style={{ position: 'relative', zIndex: 2, maxWidth: 860, wordBreak: 'keep-all' }}>
          <LiveBadge health={health} okText={t.heroLiveOk} unknownText={t.heroLiveUnknown} />

          <h1
            style={{
              fontFamily: 'var(--disp)', fontWeight: 800,
              fontSize: 'clamp(34px,5.4vw,64px)', lineHeight: 1.08,
              letterSpacing: '-.03em', whiteSpace: 'pre-line',
            }}
          >
            {renderTitle(t.heroTitle)}
          </h1>

          <p
            style={{
              color: 'var(--muted)', fontSize: 'clamp(15px,1.3vw,18px)',
              lineHeight: 1.8, marginTop: 24, maxWidth: 700,
            }}
          >
            {t.heroLead}
          </p>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 32, alignItems: 'center' }}>
            <Link
              href="/dashboard"
              style={{
                fontFamily: 'var(--mono)', fontSize: 13, textDecoration: 'none', fontWeight: 500,
                background: 'linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 78%, #000))', color: 'var(--on-accent)',
                borderRadius: 10, padding: '13px 22px', boxShadow: '0 8px 30px color-mix(in srgb, var(--accent) 28%, transparent)',
              }}
            >
              {t.heroPrimaryCta} →
            </Link>
            <a
              href="#engines"
              style={{
                fontFamily: 'var(--mono)', fontSize: 13, textDecoration: 'none',
                border: '1px solid var(--line2)', color: 'var(--txt)',
                borderRadius: 10, padding: '13px 22px', background: 'var(--panel)',
              }}
            >
              {t.heroSecondaryCta}
            </a>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>
              {t.heroNoLogin}
            </span>
          </div>
        </div>
      </section>
      </div>

      {/* ── 메인 소개 영상(환경변수로 켜짐 · 없으면 아무것도 안 그림) ── */}
      {video && (
        <Section pad="sm">
          <IntroVideo video={video} label={t.introVideoLabel} />
        </Section>
      )}

      {/* ── 실측 수치 ──────────────────────────────────────── */}
      <Section pad="sm">
        <div
          style={{
            display: 'grid', gap: 1, background: 'var(--line)', border: '1px solid var(--line)',
            borderRadius: 16, overflow: 'hidden', wordBreak: 'keep-all',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(150px, 100%), 1fr))',
          }}
        >
          {t.stats.map((s) => (
            <div key={s.label} style={{ background: 'var(--panel)', padding: 'clamp(20px,2.2vw,26px)' }}>
              <div
                style={{
                  fontFamily: 'var(--mono)', fontWeight: 700,
                  fontSize: 'clamp(28px,3.2vw,40px)', letterSpacing: '-.02em', lineHeight: 1,
                }}
              >
                {s.value}
              </div>
              <div style={{ fontSize: 13, marginTop: 10, fontWeight: 600 }}>{s.label}</div>
              <div style={{ color: 'var(--muted2)', fontSize: 12, marginTop: 6, lineHeight: 1.55 }}>
                {s.note}
              </div>
            </div>
          ))}
        </div>
        <p style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)', marginTop: 10 }}>
          {t.statsAsOf}
        </p>
      </Section>

      {/* ── 사진(퍼블릭 도메인, 출처 표기) ─────────────────── */}
      <Section pad="sm">
        <PhotoFigure photo={t.photo} />
      </Section>

      {/* ── 엔진 구성 ──────────────────────────────────────── */}
      <div id="engines" style={{ scrollMarginTop: 80, wordBreak: 'keep-all' }}>
        <Section>
          <SectionHeading eyebrow="ENGINE" title={t.engineTitle} lead={t.engineLead} />
          <ModeLegend modes={t.engineModes} />
          <div style={{ display: 'grid', gap: 34, marginTop: 30 }}>
            {t.engineGroups.map((group, gi) => (
              <div key={group.key}>
                <h3
                  style={{
                    display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 14,
                    fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 18, letterSpacing: '-.01em',
                  }}
                >
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--accent)', fontWeight: 500 }}>
                    {String(gi + 1).padStart(2, '0')}
                  </span>
                  {group.label}
                </h3>
                <Grid min={280}>
                  {group.engines.map((e) => (
                    <EngineCard
                      key={e.id}
                      engine={e}
                      modeLabel={t.engineModes[e.mode]}
                      caveatLabel={t.engineCaveatLabel}
                    />
                  ))}
                </Grid>
              </div>
            ))}
          </div>
        </Section>
      </div>

      {/* ── 스페셜 프로그램 강조(헤임달·발할라) ─────────────── */}
      <Section>
        <Card accent>
          <div style={{ wordBreak: 'keep-all' }}>
            <SectionHeading eyebrow={t.specialEyebrow} title={t.specialTitle} lead={t.specialLead} />
            <Grid min={300}>
              {t.specialCards.map((c) => (
                <div
                  key={c.code}
                  style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 20, background: 'var(--panel)' }}
                >
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '.12em', color: 'var(--accent)', fontWeight: 700 }}>
                    {c.code}
                  </div>
                  <h3 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 16, margin: '8px 0 10px' }}>{c.name}</h3>
                  <p style={{ color: 'var(--muted)', fontSize: 13.5, lineHeight: 1.72 }}>{c.body}</p>
                </div>
              ))}
            </Grid>
            <Link
              href={localePath(locale, 'programs')}
              style={{
                display: 'inline-block', marginTop: 20,
                fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)', textDecoration: 'none', fontWeight: 700,
              }}
            >
              {t.specialCta} →
            </Link>
          </div>
        </Card>
      </Section>

      {/* ── 우리가 공개하는 것 ─────────────────────────────── */}
      <Section>
        <SectionHeading eyebrow="OPEN BY DEFAULT" title={t.openTitle} lead={t.openLead} />
        <Grid min={260}>
          {t.openItems.map((item) => (
            <Card key={item.title}>
              <h3 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 17, marginBottom: 10 }}>
                {item.title}
              </h3>
              <p style={{ color: 'var(--muted)', fontSize: 13.5, lineHeight: 1.7, marginBottom: 16 }}>
                {item.body}
              </p>
              <Link
                href={item.href.startsWith('/dashboard') ? item.href : localePath(locale, item.href)}
                style={{
                  fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)', textDecoration: 'none',
                }}
              >
                {item.linkLabel} →
              </Link>
            </Card>
          ))}
        </Grid>
      </Section>

      {/* ── ★ 검증되지 않은 것 ★ 이 사이트의 핵심 블록 ───── */}
      <Section>
        <Card accent>
          <div style={{ maxWidth: 820 }}>
            <p
              style={{
                fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.12em',
                textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 12,
              }}
            >
              VALIDATION
            </p>
            <h2
              style={{
                fontFamily: 'var(--disp)', fontWeight: 800,
                fontSize: 'clamp(23px,2.8vw,34px)', lineHeight: 1.2, letterSpacing: '-.025em',
              }}
            >
              {t.honestTitle}
            </h2>
            <p style={{ color: 'var(--muted)', fontSize: 15, lineHeight: 1.75, marginTop: 14 }}>
              {t.honestLead}
            </p>

            <ul style={{ listStyle: 'none', display: 'grid', gap: 14, marginTop: 26 }}>
              {t.honestPoints.map((point, i) => (
                <li key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  <span
                    aria-hidden="true"
                    style={{
                      fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--accent)',
                      paddingTop: 3, flexShrink: 0,
                    }}
                  >
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <span
                    style={{ color: 'var(--txt)', fontSize: 14, lineHeight: 1.72 }}
                    dangerouslySetInnerHTML={{ __html: boldify(point) }}
                  />
                </li>
              ))}
            </ul>

            <p
              style={{
                color: 'var(--muted)', fontSize: 14, lineHeight: 1.75, marginTop: 26,
                paddingTop: 22, borderTop: '1px solid var(--line)',
              }}
            >
              {t.honestClose}
            </p>

            <Link
              href={localePath(locale, 'transparency')}
              style={{
                display: 'inline-block', marginTop: 20,
                fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)', textDecoration: 'none',
              }}
            >
              {t.honestCta} →
            </Link>
          </div>
        </Card>
      </Section>

      {/* ── 신호 → 경보 흐름 ──────────────────────────────── */}
      <Section>
        <SectionHeading eyebrow="PIPELINE" title={t.pipelineTitle} lead={t.pipelineLead} />
        <Grid min={210}>
          {t.pipelineSteps.map((step) => (
            <Card key={step.step}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)', marginBottom: 10 }}>
                {step.step}
              </div>
              <h3 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 16, marginBottom: 8 }}>
                {step.title}
              </h3>
              <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.68 }}>{step.body}</p>
            </Card>
          ))}
        </Grid>
      </Section>

      {/* ── 누구를 위한 것인가 ────────────────────────────── */}
      <Section>
        <SectionHeading eyebrow="USE CASES" title={t.audienceTitle} lead={t.audienceLead} />
        <Grid min={280}>
          {t.audiences.map((a) => (
            <Card key={a.title}>
              <h3 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 17, marginBottom: 10 }}>
                {a.title}
              </h3>
              <p style={{ color: 'var(--muted)', fontSize: 13.5, lineHeight: 1.7, marginBottom: 16 }}>
                {a.body}
              </p>
              <Link
                href={localePath(locale, a.href)}
                style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}
              >
                {dict.common.readMore} →
              </Link>
            </Card>
          ))}
        </Grid>
      </Section>

      {/* ── 마무리 CTA ────────────────────────────────────── */}
      <Section pad="sm">
        <Card>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ maxWidth: 560 }}>
              <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(20px,2.2vw,27px)', letterSpacing: '-.02em' }}>
                {t.ctaTitle}
              </h2>
              <p style={{ color: 'var(--muted)', fontSize: 14, lineHeight: 1.7, marginTop: 12 }}>
                {t.ctaBody}
              </p>
            </div>
            <Link
              href={localePath(locale, 'contact')}
              style={{
                fontFamily: 'var(--mono)', fontSize: 13, textDecoration: 'none',
                background: 'var(--accent)', color: 'var(--on-accent)', borderRadius: 10, padding: '13px 22px',
              }}
            >
              {t.ctaButton} →
            </Link>
          </div>
        </Card>
      </Section>
    </>
  );
}

/** [[낱말]] 을 강조색으로. 강조가 둘이면 붉은색·하늘색을 번갈아 쓴다(처음 홈의 배색). */
function renderTitle(title: string) {
  const parts = title.split(/(\[\[.+?\]\])/g);
  let n = 0;
  return parts.map((part, i) => {
    const m = part.match(/^\[\[(.+)\]\]$/);
    if (!m) return part;
    const color = n++ % 2 === 0 ? 'var(--accent)' : 'var(--cyan)';
    return <span key={i} style={{ color }}>{m[1]}</span>;
  });
}

function LiveBadge({
  health, okText, unknownText,
}: { health: SourceHealthSummary | null; okText: string; unknownText: string }) {
  // 전부 정상일 때만 초록. 일부가 빠졌으면 수를 그대로 보이되 호박색, 못 읽었으면 회색.
  const color = !health ? 'var(--muted2)' : health.ok === health.total ? 'var(--ok)' : 'var(--amber)';
  const text = health
    ? okText.replace('{ok}', String(health.ok)).replace('{total}', String(health.total))
    : unknownText;
  return (
    <p
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 8,
        fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.08em', color,
        border: `1px solid color-mix(in srgb, ${color} 35%, transparent)`,
        background: `color-mix(in srgb, ${color} 7%, transparent)`,
        borderRadius: 999, padding: '6px 14px', marginBottom: 24,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 6, height: 6, borderRadius: 999, background: color,
          boxShadow: health ? `0 0 8px ${color}` : 'none',
          animation: health ? 'blink 1.6s infinite' : 'none',
        }}
      />
      {text}
    </p>
  );
}

const MODE_COLOR: Record<EngineMode, string> = {
  hourly: 'var(--ok)',
  daily: 'var(--ok)',
  onAlert: 'var(--amber)',
  onRequest: 'var(--muted2)',
};

function ModeChip({ mode, label }: { mode: EngineMode; label: string }) {
  const color = MODE_COLOR[mode];
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
        fontFamily: 'var(--mono)', fontSize: 10.5, color: mode === 'onRequest' ? 'var(--muted)' : color,
        border: '1px solid var(--line2)', borderRadius: 999, padding: '3px 9px',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 5, height: 5, borderRadius: 999,
          background: mode === 'onRequest' ? 'transparent' : color,
          border: mode === 'onRequest' ? `1px solid ${color}` : 'none',
        }}
      />
      {label}
    </span>
  );
}

function ModeLegend({ modes }: { modes: Record<EngineMode, string> }) {
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {(Object.keys(modes) as EngineMode[]).map((m) => (
        <ModeChip key={m} mode={m} label={modes[m]} />
      ))}
    </div>
  );
}

function EngineCard({
  engine, modeLabel, caveatLabel,
}: { engine: EngineDict; modeLabel: string; caveatLabel: string }) {
  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <code style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--cyan)', wordBreak: 'break-all' }}>
          {engine.id}
        </code>
        <ModeChip mode={engine.mode} label={modeLabel} />
      </div>
      <h4 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 16, margin: '12px 0 8px', lineHeight: 1.35 }}>
        {engine.name}
      </h4>
      <p style={{ color: 'var(--muted)', fontSize: 13.5, lineHeight: 1.72 }}>{engine.body}</p>
      {engine.caveat && (
        <p
          style={{
            marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--line)',
            color: 'var(--muted)', fontSize: 12.5, lineHeight: 1.65,
          }}
        >
          <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--amber)', marginRight: 8 }}>
            {caveatLabel}
          </span>
          {engine.caveat}
        </p>
      )}
    </Card>
  );
}

/**
 * 사전 문구의 **강조** 표기만 <strong>으로 바꾼다.
 * 마크다운 라이브러리를 끌어오지 않는 이유: 여기서 필요한 건 강조 하나뿐이고,
 * 사전은 우리가 직접 쓰는 파일이라 외부 입력이 아니다. 그래도 그 외 태그는
 * 만들지 않도록 굵게 표기만 치환한다.
 */
function boldify(text: string): string {
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}
