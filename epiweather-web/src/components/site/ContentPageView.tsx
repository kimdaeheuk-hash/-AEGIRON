import Link from 'next/link';
import type { ContentPage, PageBlock } from '@/i18n/types';
import { localePath, type Locale } from '@/i18n/config';
import { Section, SectionHeading, Grid } from './Section';
import { PhotoFigure } from './PhotoFigure';

/**
 * 콘텐츠 페이지 하나를 그리는 단일 렌더러.
 *
 * 페이지마다 컴포넌트를 따로 만들면 11개 페이지 × 3개 언어를 손으로 관리하게 되고,
 * 문구 하나 고칠 때마다 세 군데를 건드려야 한다. 콘텐츠를 사전으로 빼고 렌더러를
 * 하나만 두면 **언어 추가가 사전 파일 하나로 끝난다** — 캡틴이 경계한 '맨날 수정'을
 * 구조로 막는 방식이다.
 *
 * 2026-10-18 오후: 블록마다 묶음 색(tone)·꼬리표(kicker)·사양표(specs)·사진(photo)·
 * 깊은 남청색 띠(deep)를 받는다. 기술 스펙과 엔진 카탈로그가 묶음을 색으로 가르기 위해서다.
 */
export function ContentPageView({ page, locale }: { page: ContentPage; locale: Locale }) {
  return (
    // keep-all: 한국어가 줄 끝에서 낱말 중간('스/크리닝')에 끊기지 않게 한다(홈과 같은 규칙).
    <div style={{ wordBreak: 'keep-all' }}>
      <Section>
        <SectionHeading as="h1" eyebrow={page.eyebrow} title={page.title} lead={page.lead} />
        {page.photo && (
          <div style={{ marginTop: 8 }}>
            <PhotoFigure photo={page.photo} priority />
          </div>
        )}
      </Section>

      {page.blocks.map((block, i) =>
        block.deep ? (
          <div key={i} className="band-deep">
            <Section pad="sm">
              <BlockCard block={block} />
            </Section>
          </div>
        ) : (
          <Section key={i} pad="sm">
            <BlockCard block={block} />
          </Section>
        ),
      )}

      {page.cta && <CtaBand cta={page.cta} locale={locale} />}
    </div>
  );
}

/** 페이지 하단 행동 유도 띠 — 실가동·원장처럼 사전 블록이 아닌 페이지도 같은 모양을 쓴다. */
export function CtaBand({ cta, locale }: { cta: NonNullable<ContentPage['cta']>; locale: Locale }) {
  return (
    <div className="band-deep">
      <Section pad="sm">
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', padding: 'clamp(10px,2vw,22px) 0', wordBreak: 'keep-all' }}>
          <div style={{ maxWidth: 620 }}>
            <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(20px,2.3vw,28px)', letterSpacing: '-.02em' }}>
              {cta.title}
            </h2>
            <p style={{ color: 'var(--muted)', fontSize: 14.5, lineHeight: 1.7, marginTop: 11 }}>{cta.body}</p>
          </div>
          <Link
            href={cta.href.startsWith('/') ? cta.href : localePath(locale, cta.href)}
            style={{
              fontFamily: 'var(--mono)', fontSize: 13, textDecoration: 'none', fontWeight: 600,
              background: 'var(--accent)', color: 'var(--on-accent)', borderRadius: 10, padding: '13px 22px',
            }}
          >
            {cta.label} →
          </Link>
        </div>
      </Section>
    </div>
  );
}

function BlockCard({ block }: { block: PageBlock }) {
  const toned = Boolean(block.tone);
  return (
    <div
      data-tone={block.tone}
      className={toned ? 'toned-card' : undefined}
      style={{
        border: `1px solid ${block.accent ? 'var(--accent-line)' : 'var(--line)'}`,
        background: block.accent ? 'var(--accent-soft)' : 'var(--panel)',
        borderRadius: 14,
        padding: 'clamp(18px,2.2vw,30px)',
      }}
    >
      <div style={{ maxWidth: block.items || block.specs ? undefined : 860 }}>
        {block.kicker && (
          <p className={toned ? 'tone-chip' : undefined} style={toned ? { marginBottom: 12 } : {
            fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.1em', color: 'var(--accent)', marginBottom: 12,
          }}>
            {block.kicker}
          </p>
        )}
        <h2
          style={{
            fontFamily: 'var(--disp)', fontWeight: 800,
            fontSize: 'clamp(19px,2.1vw,26px)', lineHeight: 1.25, letterSpacing: '-.02em',
          }}
        >
          {block.title}
        </h2>

        {block.body && (
          <p style={{ color: 'var(--muted)', fontSize: 14.5, lineHeight: 1.8, marginTop: 14, maxWidth: 900 }}>
            {block.body}
          </p>
        )}

        {block.photo && (
          <div style={{ marginTop: 20 }}>
            <PhotoFigure photo={block.photo} aspect="21 / 8" />
          </div>
        )}

        {block.specs && (
          <dl
            style={{
              marginTop: 20, display: 'grid', gap: 1, background: 'var(--line)',
              border: '1px solid var(--line)', borderRadius: 12, overflow: 'hidden',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(300px, 100%), 1fr))',
            }}
          >
            {block.specs.map((s) => (
              <div key={s.label} style={{ background: 'var(--panel)', padding: '14px 16px', display: 'grid', gap: 5 }}>
                <dt style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.06em', color: 'var(--muted2)' }}>{s.label}</dt>
                <dd style={{ fontSize: 14.5, fontWeight: 600, lineHeight: 1.55 }}>{s.value}</dd>
              </div>
            ))}
          </dl>
        )}

        {block.points && (
          <ul style={{ listStyle: 'none', display: 'grid', gap: 13, marginTop: block.body ? 22 : 18 }}>
            {block.points.map((point, j) => (
              <li key={j} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <span
                  aria-hidden="true"
                  style={{
                    fontFamily: 'var(--mono)', fontSize: 11,
                    color: toned ? 'var(--tone)' : block.accent ? 'var(--accent)' : 'var(--muted2)',
                    paddingTop: 3, flexShrink: 0, fontWeight: 700,
                  }}
                >
                  {String(j + 1).padStart(2, '0')}
                </span>
                <span
                  style={{ color: 'var(--txt)', fontSize: 14, lineHeight: 1.74 }}
                  dangerouslySetInnerHTML={{ __html: boldify(point) }}
                />
              </li>
            ))}
          </ul>
        )}

        {block.items && (
          <div style={{ marginTop: block.body || block.points || block.specs ? 24 : 18 }}>
            <Grid min={260}>
              {block.items.map((item) => (
                <div
                  key={item.title}
                  className={toned ? 'tone-item' : undefined}
                  style={{
                    border: '1px solid var(--line)', borderRadius: 11,
                    padding: 17, background: 'var(--code-bg)',
                  }}
                >
                  <h3 style={{ fontSize: 14.5, fontWeight: 700, marginBottom: 8, lineHeight: 1.4 }}>{item.title}</h3>
                  <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.7 }}>{item.body}</p>
                  {item.meta && (
                    <p
                      style={{
                        fontFamily: 'var(--mono)', fontSize: 11, color: toned ? 'var(--tone)' : 'var(--muted2)',
                        marginTop: 11, paddingTop: 10, borderTop: '1px solid var(--line)', wordBreak: 'break-word',
                      }}
                    >
                      {item.meta}
                    </p>
                  )}
                </div>
              ))}
            </Grid>
          </div>
        )}

        {block.note && (
          <p
            style={{
              color: 'var(--muted2)', fontSize: 12.5, lineHeight: 1.7, marginTop: 20,
              paddingTop: 16, borderTop: '1px solid var(--line)',
            }}
          >
            {block.note}
          </p>
        )}
      </div>
    </div>
  );
}

/** 사전의 **강조** 표기만 <strong>으로. 그 외 태그는 만들지 않는다. */
function boldify(text: string): string {
  const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}
