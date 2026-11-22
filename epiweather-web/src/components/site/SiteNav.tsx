import Link from 'next/link';
import type { Dictionary } from '@/i18n/types';
import { dashboardHref, localePath, type Locale } from '@/i18n/config';
import { Logo } from './Logo';
import { LocaleSwitcher } from './LocaleSwitcher';
import { MobileMenu } from './MobileMenu';

/**
 * 사이트 공통 네비게이션.
 *
 * 2026-11-22 개편: 세 고리(극지 → 헤임달 → 발할라)를 맨 앞에 두고, 나머지는 '회사' 묶음 하나로 접는다.
 * 헤임달·발할라는 운영 화면(/dashboard) 안의 구획이라 그 앵커로 보낸다.
 * 넓은 화면은 묶음마다 펼침 메뉴, 좁은 화면은 '메뉴' 버튼 하나로 접는다.
 */
export type NavItem = { label: string; href: string };
export type NavGroup = { label: string; href?: string; items?: NavItem[]; emphasis?: boolean };

export function navGroups(locale: Locale, nav: Dictionary['nav']): NavGroup[] {
  const p = (path: string) => localePath(locale, path);
  const dash = dashboardHref(locale);
  return [
    { label: nav.heimdall, href: `${dash}#heimdall`, emphasis: true },
    { label: nav.valhalla, href: `${dash}#valhalla`, emphasis: true },
    { label: nav.polar, href: p('polar'), emphasis: true },
    { label: nav.government, href: p('solutions/government') },
    { label: nav.company, items: [
      { label: nav.about, href: p('about') },
      { label: nav.methodology, href: p('methodology') },
      { label: nav.developers, href: p('developers') },
      { label: nav.security, href: p('security') },
      { label: nav.contact, href: p('contact') },
    ] },
  ];
}

export function SiteNav({ locale, dict }: { locale: Locale; dict: Dictionary }) {
  const groups = navGroups(locale, dict.nav);
  return (
    <header className="site-header">
      <nav aria-label={dict.common.siteName} className="site-nav">
        <Link href={localePath(locale)} className="site-brand">
          <Logo size={30} />
          <span>{dict.common.siteName}</span>
        </Link>

        <ul className="nav-groups">
          {groups.map((g) => (
            <li key={g.label} className={g.items ? 'nav-group has-menu' : 'nav-group'}>
              {g.href ? (
                <Link href={g.href} className={g.emphasis ? 'nav-top emphasis' : 'nav-top'}>
                  {g.label}
                </Link>
              ) : (
                // 묶음 제목은 링크가 아니다 — 누르거나(포커스) 올리면 하위 메뉴가 열린다.
                <button type="button" className="nav-top" aria-haspopup="true">
                  {g.label}
                  <span aria-hidden="true" className="nav-caret">▾</span>
                </button>
              )}
              {g.items && (
                <ul className="nav-menu">
                  {g.items.map((it) => (
                    <li key={it.href}>
                      <Link href={it.href}>{it.label}</Link>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>

        <div className="nav-actions">
          <LocaleSwitcher current={locale} label={dict.nav.language} />
          <Link href={dashboardHref(locale)} className="nav-cta">
            {dict.nav.dashboard} →
          </Link>
          <MobileMenu groups={groups} openLabel={dict.nav.openMenu} closeLabel={dict.nav.closeMenu} dashboard={dict.nav.dashboard} dashboardHref={dashboardHref(locale)} />
        </div>
      </nav>
    </header>
  );
}
