import Link from 'next/link';
import type { Dictionary } from '@/i18n/types';
import { localePath, type Locale } from '@/i18n/config';
import { Logo } from './Logo';
import { LocaleSwitcher } from './LocaleSwitcher';
import { MobileMenu } from './MobileMenu';

/**
 * 사이트 공통 네비게이션.
 *
 * ★ 2026-10-18 재구성 ★ 캡틴 지시: "맨 위 페이지 제목들이 정리가 안 된 것처럼 보인다 —
 * 회사, 플랫폼, 기술 등을 순서대로 정리해라." 예전에는 링크 여덟 개를 한 줄에 늘어놓고
 * 넘치면 옆으로 밀었다. 휴대폰에서는 절반이 잘려 보였고, 무엇이 무엇의 하위인지도 안 보였다.
 *
 * 이제는 방문자가 읽는 순서대로 여섯 묶음이다 —
 *   회사 → 플랫폼 → 기술 → 스페셜 프로그램 → 활용 분야 → 검증·데이터
 * 넓은 화면은 묶음마다 펼침 메뉴, 좁은 화면은 '메뉴' 버튼 하나로 접는다.
 */
export type NavItem = { label: string; href: string };
export type NavGroup = { label: string; href?: string; items?: NavItem[]; emphasis?: boolean };

export function navGroups(locale: Locale, nav: Dictionary['nav']): NavGroup[] {
  const p = (path: string) => localePath(locale, path);
  return [
    { label: nav.company, items: [
      { label: nav.about, href: p('about') },
      { label: nav.contact, href: p('contact') },
    ] },
    { label: nav.platform, href: p('platform') },
    { label: nav.technology, items: [
      { label: nav.techSpec1, href: p('technology') },
      { label: nav.techSpec2, href: p('technology-advanced') },
      { label: nav.engines, href: p('engines') },
      { label: nav.methodology, href: p('methodology') },
    ] },
    // 스페셜 프로그램(헤임달·발할라)은 강조색 — 캡틴이 "R&D처럼 중요하다"고 지목한 항목이다.
    { label: nav.programs, href: p('programs'), emphasis: true },
    { label: nav.solutions, items: [
      { label: nav.solGovernment, href: p('solutions/government') },
      { label: nav.solReinsurance, href: p('solutions/reinsurance') },
      { label: nav.solNgo, href: p('solutions/ngo') },
    ] },
    { label: nav.trust, items: [
      { label: nav.transparency, href: p('transparency') },
      { label: nav.dataSources, href: p('data-sources') },
      { label: nav.briefings, href: p('briefings') },
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
          <Link href="/dashboard" className="nav-cta">
            {dict.nav.dashboard} →
          </Link>
          <MobileMenu groups={groups} openLabel={dict.nav.openMenu} closeLabel={dict.nav.closeMenu} dashboard={dict.nav.dashboard} />
        </div>
      </nav>
    </header>
  );
}
