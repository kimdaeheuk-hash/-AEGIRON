'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { NavGroup } from './SiteNav';

/**
 * 좁은 화면 메뉴 — '메뉴' 버튼 하나에 여섯 묶음을 순서대로 접어 둔다.
 *
 * <details> 를 쓰면 자바스크립트 없이도 열리고 닫힌다. 다만 페이지를 옮겨도 레이아웃은
 * 그대로 남아 메뉴가 열린 채로 남는다 — 그래서 key 를 현재 경로로 둬서, 경로가 바뀌면
 * 새로 그려지며(=닫힌 상태로) 시작하게 한다.
 */
export function MobileMenu({
  groups, openLabel, closeLabel, dashboard,
}: { groups: NavGroup[]; openLabel: string; closeLabel: string; dashboard: string }) {
  const pathname = usePathname();
  return (
    <details key={pathname} className="mobile-menu">
      <summary aria-label={openLabel}>
        <span className="when-closed" aria-hidden="true">☰</span>
        <span className="when-open" aria-hidden="true">✕</span>
        <span className="sr-only">{openLabel} / {closeLabel}</span>
      </summary>
      <div className="mobile-panel">
        {groups.map((g) => (
          <div key={g.label} className="mobile-group">
            {g.href ? (
              <Link href={g.href} className={g.emphasis ? 'mobile-top emphasis' : 'mobile-top'}>{g.label}</Link>
            ) : (
              <p className="mobile-top">{g.label}</p>
            )}
            {g.items && (
              <ul>
                {g.items.map((it) => (
                  <li key={it.href}><Link href={it.href}>{it.label}</Link></li>
                ))}
              </ul>
            )}
          </div>
        ))}
        <Link href="/dashboard" className="mobile-cta">{dashboard} →</Link>
      </div>
    </details>
  );
}
