import Link from 'next/link';
import type { Dictionary } from '@/i18n/types';
import { localePath, type Locale } from '@/i18n/config';
import { Logo } from './Logo';

/**
 * 사이트 공통 푸터.
 *
 * 예전 푸터에는 링크가 **하나도 없었다**(로고 + 저작권 한 줄). 페이지가 늘어난
 * 지금은 그게 방문자에게도 검색엔진에게도 손해다 — 푸터는 사이트 전체 구조를
 * 알려주는 지도 역할을 한다.
 *
 * 정직성 문구를 여기에 둔 이유: 어느 페이지로 바로 들어와도 "아직 검증된
 * 트랙레코드가 없다"가 보여야 한다. 홈에만 두면 딥링크로 들어온 사람은 못 본다.
 */
const COLUMNS: { titleKey: 'product' | 'company'; links: { key: keyof Dictionary['nav']; path: string }[] }[] = [
  {
    titleKey: 'product',
    links: [
      { key: 'platform', path: 'platform' },
      { key: 'methodology', path: 'methodology' },
      { key: 'transparency', path: 'transparency' },
      { key: 'dataSources', path: 'data-sources' },
      { key: 'briefings', path: 'briefings' },
    ],
  },
  {
    titleKey: 'company',
    links: [
      { key: 'about', path: 'about' },
      { key: 'contact', path: 'contact' },
    ],
  },
];

export function SiteFooter({ locale, dict }: { locale: Locale; dict: Dictionary }) {
  const year = new Date().getFullYear();

  return (
    <footer style={{ borderTop: '1px solid var(--line)', marginTop: 40 }}>
      <div
        style={{
          maxWidth: 1320, margin: '0 auto',
          padding: 'clamp(32px,4vw,52px) clamp(14px,2.4vw,26px) 28px',
          display: 'grid', gap: 34,
          gridTemplateColumns: 'minmax(220px, 1.4fr) repeat(auto-fit, minmax(140px, 1fr))',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <Logo size={26} />
            <span style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 16 }}>
              {dict.common.siteName}
            </span>
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.6, maxWidth: 320 }}>
            {dict.footer.tagline}
          </p>
        </div>

        {COLUMNS.map((col) => (
          <div key={col.titleKey}>
            <h2
              style={{
                fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.08em',
                textTransform: 'uppercase', color: 'var(--muted2)', marginBottom: 12,
              }}
            >
              {dict.footer[col.titleKey]}
            </h2>
            <ul style={{ listStyle: 'none', display: 'grid', gap: 9 }}>
              {col.links.map(({ key, path }) => (
                <li key={key}>
                  <Link
                    href={localePath(locale, path)}
                    style={{ color: 'var(--muted)', textDecoration: 'none', fontSize: 13 }}
                  >
                    {dict.nav[key]}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}

        <div>
          <h2
            style={{
              fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.08em',
              textTransform: 'uppercase', color: 'var(--muted2)', marginBottom: 12,
            }}
          >
            {dict.footer.legal}
          </h2>
          <ul style={{ listStyle: 'none', display: 'grid', gap: 9 }}>
            <li>
              <Link href={localePath(locale, 'privacy')} style={{ color: 'var(--muted)', textDecoration: 'none', fontSize: 13 }}>
                {dict.footer.privacy}
              </Link>
            </li>
            <li>
              <Link href={localePath(locale, 'terms')} style={{ color: 'var(--muted)', textDecoration: 'none', fontSize: 13 }}>
                {dict.footer.terms}
              </Link>
            </li>
          </ul>
        </div>
      </div>

      {/* ★ 정직성 고지 — 어느 페이지로 들어와도 보이게 푸터에 고정한다. */}
      <div style={{ borderTop: '1px solid var(--line)' }}>
        <p
          style={{
            maxWidth: 1320, margin: '0 auto',
            padding: '18px clamp(14px,2.4vw,26px)',
            color: 'var(--muted2)', fontSize: 12, lineHeight: 1.65,
          }}
        >
          {dict.footer.disclaimer}
        </p>
      </div>

      <div style={{ borderTop: '1px solid var(--line)' }}>
        <div
          style={{
            maxWidth: 1320, margin: '0 auto',
            padding: '16px clamp(14px,2.4vw,26px) 30px',
            display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap',
            fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)',
          }}
        >
          <span>© {year} {dict.common.siteName}. {dict.footer.rights}</span>
          <span>{dict.footer.location}</span>
        </div>
      </div>
    </footer>
  );
}
