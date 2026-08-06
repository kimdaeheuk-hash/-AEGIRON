'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { locales, localeNames, htmlLang, type Locale } from '@/i18n/config';

/**
 * 언어 전환기.
 *
 * ★ 핵심 ★ **보고 있던 페이지를 유지한 채** 언어만 바꾼다. 홈으로 되돌리면
 * 방문자가 읽던 자리를 잃고, 검색엔진 입장에서도 언어판끼리 대응이 깨진다.
 * 그래서 현재 경로에서 로케일 조각만 갈아끼운다.
 */
export function LocaleSwitcher({ current, label }: { current: Locale; label: string }) {
  const pathname = usePathname() || `/${current}`;
  const rest = pathname.replace(new RegExp(`^/(${locales.join('|')})`), '');

  return (
    <nav aria-label={label} style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      {locales.map((locale, i) => {
        const active = locale === current;
        return (
          <span key={locale} style={{ display: 'flex', alignItems: 'center' }}>
            {i > 0 && (
              <span aria-hidden="true" style={{ color: 'var(--muted2)', fontSize: 10, padding: '0 2px' }}>
                ·
              </span>
            )}
            <Link
              href={`/${locale}${rest}`}
              hrefLang={htmlLang[locale]}
              aria-current={active ? 'true' : undefined}
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 11,
                textDecoration: 'none',
                padding: '4px 5px',
                borderRadius: 6,
                color: active ? 'var(--txt)' : 'var(--muted2)',
                background: active ? 'var(--panel)' : 'transparent',
              }}
            >
              {locale.toUpperCase()}
              <span className="sr-only"> {localeNames[locale]}</span>
            </Link>
          </span>
        );
      })}
    </nav>
  );
}
