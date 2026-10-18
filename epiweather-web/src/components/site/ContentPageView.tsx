import Link from 'next/link';
import type { ContentPage } from '@/i18n/types';
import { localePath, type Locale } from '@/i18n/config';
import { Section, SectionHeading, Card, Grid } from './Section';

/**
 * 콘텐츠 페이지 하나를 그리는 단일 렌더러.
 *
 * 페이지마다 컴포넌트를 따로 만들면 11개 페이지 × 3개 언어를 손으로 관리하게 되고,
 * 문구 하나 고칠 때마다 세 군데를 건드려야 한다. 콘텐츠를 사전으로 빼고 렌더러를
 * 하나만 두면 **언어 추가가 사전 파일 하나로 끝난다** — 캡틴이 경계한 '맨날 수정'을
 * 구조로 막는 방식이다.
 */
export function ContentPageView({ page, locale }: { page: ContentPage; locale: Locale }) {
  return (
    <>
      <Section>
        <SectionHeading as="h1" eyebrow={page.eyebrow} title={page.title} lead={page.lead} />
      </Section>

      {page.blocks.map((block, i) => (
        <Section key={i} pad="sm">
          <Card accent={block.accent}>
            <div style={{ maxWidth: block.items ? undefined : 860 }}>
              <h2
                style={{
                  fontFamily: 'var(--disp)', fontWeight: 800,
                  fontSize: 'clamp(19px,2.1vw,26px)', lineHeight: 1.25, letterSpacing: '-.02em',
                }}
              >
                {block.title}
              </h2>

              {block.body && (
                <p style={{ color: 'var(--muted)', fontSize: 14.5, lineHeight: 1.78, marginTop: 14 }}>
                  {block.body}
                </p>
              )}

              {block.points && (
                <ul style={{ listStyle: 'none', display: 'grid', gap: 13, marginTop: block.body ? 22 : 18 }}>
                  {block.points.map((point, j) => (
                    <li key={j} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                      <span
                        aria-hidden="true"
                        style={{
                          fontFamily: 'var(--mono)', fontSize: 11,
                          color: block.accent ? 'var(--accent)' : 'var(--muted2)',
                          paddingTop: 3, flexShrink: 0,
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
                <div style={{ marginTop: block.body || block.points ? 24 : 18 }}>
                  <Grid min={250}>
                    {block.items.map((item) => (
                      <div
                        key={item.title}
                        style={{
                          border: '1px solid var(--line)', borderRadius: 11,
                          padding: 17, background: 'var(--code-bg)',
                        }}
                      >
                        <h3 style={{ fontSize: 14.5, fontWeight: 700, marginBottom: 8 }}>{item.title}</h3>
                        <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.68 }}>{item.body}</p>
                        {item.meta && (
                          <p
                            style={{
                              fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)',
                              marginTop: 11, paddingTop: 10, borderTop: '1px solid var(--line)',
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
          </Card>
        </Section>
      ))}

      {page.cta && (
        <Section pad="sm">
          <Card>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ maxWidth: 560 }}>
                <h2 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 'clamp(19px,2.1vw,25px)', letterSpacing: '-.02em' }}>
                  {page.cta.title}
                </h2>
                <p style={{ color: 'var(--muted)', fontSize: 14, lineHeight: 1.7, marginTop: 11 }}>
                  {page.cta.body}
                </p>
              </div>
              <Link
                href={page.cta.href.startsWith('/') ? page.cta.href : localePath(locale, page.cta.href)}
                style={{
                  fontFamily: 'var(--mono)', fontSize: 13, textDecoration: 'none',
                  background: 'var(--accent)', color: 'var(--on-accent)', borderRadius: 10, padding: '13px 22px',
                }}
              >
                {page.cta.label} →
              </Link>
            </div>
          </Card>
        </Section>
      )}
    </>
  );
}

/** 사전의 **강조** 표기만 <strong>으로. 그 외 태그는 만들지 않는다. */
function boldify(text: string): string {
  const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}
