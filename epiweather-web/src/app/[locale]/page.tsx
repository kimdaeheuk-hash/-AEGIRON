import Link from 'next/link';
import { getDictionary, localePath, isLocale, type Locale } from '@/i18n';
import { Section, SectionHeading, Card, Grid } from '@/components/site/Section';

/**
 * 홈 — '완전 공개' 노선(캡틴 확정 2026-08-06).
 *
 * 왜 이 구성인가: 조사한 경쟁사 세 곳(BlueDot·Airfinity·Perimeter)은 홈페이지의
 * 절반이 '누가 우리를 쓰는가'(고객 로고·정부 계약·논문 수)다. 우리는 그게 하나도
 * 없으므로 같은 틀을 쓰면 그 자리가 통째로 빈다. 대신 셋 다 못 하는 것을 한다 —
 * **실제 시스템을 그냥 열어둔다.** 그쪽은 고객 계약 때문에 못 열고, 우리는 지킬
 * 계약이 없어서 열 수 있다. 약점과 강점이 같은 자리에서 나온다.
 *
 * ★ 절대 규칙 ★ 정확도·선행일수 주장 금지. 대신 '검증되지 않은 것' 블록을
 * 홈 한가운데에 둔다 — 우리가 먼저 말하지 않으면 실사에서 대신 드러난다.
 */

export default async function HomePage(props: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await props.params;
  const locale = (isLocale(raw) ? raw : 'ko') as Locale;
  const dict = getDictionary(locale);
  const t = dict.home;

  return (
    <>
      {/* ── 히어로 ─────────────────────────────────────────── */}
      <Section>
        <div style={{ maxWidth: 860 }}>
          <p
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.1em',
              textTransform: 'uppercase', color: 'var(--accent)',
              border: '1px solid rgba(244,63,94,.3)', borderRadius: 999,
              padding: '6px 13px', marginBottom: 22,
            }}
          >
            <span
              aria-hidden="true"
              style={{ width: 6, height: 6, borderRadius: 999, background: 'var(--accent)' }}
            />
            {t.heroEyebrow}
          </p>

          <h1
            style={{
              fontFamily: 'var(--disp)', fontWeight: 800,
              fontSize: 'clamp(31px,5.2vw,62px)', lineHeight: 1.1,
              letterSpacing: '-.03em', whiteSpace: 'pre-line',
            }}
          >
            {t.heroTitle}
          </h1>

          <p
            style={{
              color: 'var(--muted)', fontSize: 'clamp(15px,1.3vw,18px)',
              lineHeight: 1.75, marginTop: 22, maxWidth: 660,
            }}
          >
            {t.heroLead}
          </p>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 30, alignItems: 'center' }}>
            <Link
              href="/dashboard"
              style={{
                fontFamily: 'var(--mono)', fontSize: 13, textDecoration: 'none',
                background: 'var(--accent)', color: '#fff', borderRadius: 10,
                padding: '13px 22px', fontWeight: 500,
              }}
            >
              {t.heroPrimaryCta} →
            </Link>
            <Link
              href={localePath(locale, 'platform')}
              style={{
                fontFamily: 'var(--mono)', fontSize: 13, textDecoration: 'none',
                border: '1px solid var(--line2)', color: 'var(--txt)',
                borderRadius: 10, padding: '13px 22px', background: 'var(--panel)',
              }}
            >
              {t.heroSecondaryCta}
            </Link>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>
              {t.heroNoLogin}
            </span>
          </div>
        </div>
      </Section>

      {/* ── 실측 수치 ──────────────────────────────────────── */}
      <Section pad="sm">
        <Grid min={200}>
          {t.stats.map((s) => (
            <Card key={s.label}>
              <div
                style={{
                  fontFamily: 'var(--mono)', fontWeight: 700,
                  fontSize: 'clamp(26px,3vw,38px)', letterSpacing: '-.02em',
                }}
              >
                {s.value}
              </div>
              <div style={{ fontSize: 13, marginTop: 6, fontWeight: 600 }}>{s.label}</div>
              <div style={{ color: 'var(--muted2)', fontSize: 12, marginTop: 6, lineHeight: 1.55 }}>
                {s.note}
              </div>
            </Card>
          ))}
        </Grid>
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
              NOT YET VALIDATED
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
                background: 'var(--accent)', color: '#fff', borderRadius: 10, padding: '13px 22px',
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
