import Link from 'next/link';
import type { Dictionary } from '@/i18n/types';
import { localePath, type Locale } from '@/i18n/config';
import { Logo } from './Logo';
import { LocaleSwitcher } from './LocaleSwitcher';

/**
 * 사이트 공통 네비게이션.
 *
 * 예전 홈페이지는 항목이 '방법론'과 '대시보드' 둘뿐이라 페이지가 늘어도 방문자가
 * 찾아갈 길이 없었다. 조사한 경쟁사(BlueDot·Airfinity·Perimeter)는 공통적으로
 * ①제품 ②근거 ③활용처 ④회사 ⑤행동유도(CTA)를 둔다 — 그 골격을 따르되,
 * 우리에게만 있는 '우리가 모르는 것'을 최상위에 노출한다.
 */
const LINKS: { key: keyof Dictionary['nav']; path: string }[] = [
  { key: 'platform', path: 'platform' },
  { key: 'methodology', path: 'methodology' },
  { key: 'transparency', path: 'transparency' },
  { key: 'dataSources', path: 'data-sources' },
  { key: 'briefings', path: 'briefings' },
  { key: 'about', path: 'about' },
];

export function SiteNav({ locale, dict }: { locale: Locale; dict: Dictionary }) {
  return (
    <header style={{ borderBottom: '1px solid var(--line)', position: 'sticky', top: 0, zIndex: 40, backdropFilter: 'blur(10px)', background: 'rgba(5,8,16,.72)' }}>
      <nav
        aria-label={dict.common.siteName}
        style={{
          display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap',
          maxWidth: 1320, margin: '0 auto', padding: '14px clamp(14px,2.4vw,26px)',
        }}
      >
        <Link
          href={localePath(locale)}
          style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', color: 'var(--txt)' }}
        >
          <Logo size={30} />
          <span style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 17, letterSpacing: '-.02em' }}>
            {dict.common.siteName}
          </span>
        </Link>

        <ul
          style={{
            display: 'flex', alignItems: 'center', gap: 18, listStyle: 'none',
            marginLeft: 'auto', flexWrap: 'wrap', fontFamily: 'var(--mono)', fontSize: 12,
          }}
        >
          {LINKS.map(({ key, path }) => (
            <li key={key}>
              <Link
                href={localePath(locale, path)}
                style={{ color: 'var(--muted)', textDecoration: 'none', whiteSpace: 'nowrap' }}
              >
                {dict.nav[key]}
              </Link>
            </li>
          ))}
        </ul>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <LocaleSwitcher current={locale} label={dict.nav.language} />
          <Link
            href="/dashboard"
            style={{
              fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--txt)', textDecoration: 'none',
              border: '1px solid var(--line2)', borderRadius: 9, padding: '8px 14px',
              background: 'var(--panel)', whiteSpace: 'nowrap',
            }}
          >
            {dict.nav.dashboard} →
          </Link>
        </div>
      </nav>
    </header>
  );
}
