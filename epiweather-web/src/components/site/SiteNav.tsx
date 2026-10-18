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
    <header style={{ borderBottom: '1px solid var(--line)', position: 'sticky', top: 0, zIndex: 40, backdropFilter: 'blur(10px)', background: 'var(--nav-bg)' }}>
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

        {/* ★ 모바일에서 줄바꿈 대신 가로 스크롤 ★
            wrap으로 두면 좁은 화면에서 링크가 여러 줄로 쌓여 네비 높이가 185px까지
            올라갔다(390px 기기 실측). 844px 화면의 22%를 메뉴가 먹는다는 뜻이다.
            한 줄을 유지하고 넘치는 만큼만 옆으로 밀면 모든 링크가 그대로 닿는다. */}
        <ul
          className="nav-links"
          style={{
            display: 'flex', alignItems: 'center', gap: 18, listStyle: 'none',
            marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 12,
            overflowX: 'auto', overflowY: 'hidden',
            // ★ minWidth: 0이 없으면 overflow가 동작하지 않는다 ★
            // flex 아이템의 기본 min-width는 auto라, 내용보다 작게 줄어들기를
            // 거부하고 그대로 부모를 밀어낸다. 그러면 스크롤 컨테이너가 아니라
            // 페이지 전체에 가로 스크롤이 생긴다(390px에서 408px 폭 실측).
            minWidth: 0,
            flex: '1 1 auto',
            scrollbarWidth: 'none',
            WebkitOverflowScrolling: 'touch',
          }}
        >
          {LINKS.map(({ key, path }) => (
            <li key={key} style={{ flexShrink: 0 }}>
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
