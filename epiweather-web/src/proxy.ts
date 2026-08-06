import { NextResponse, type NextRequest } from 'next/server';
import { locales, defaultLocale } from '@/i18n/config';

/**
 * 로케일 없는 경로로 들어오면 알맞은 언어로 보낸다.
 *
 * ※ Next.js 16부터 `middleware.ts`가 `proxy.ts`로 이름이 바뀌었다(기능은 동일).
 *   내보내는 함수 이름도 `proxy`여야 한다.
 *
 * 왜 필요한가: 검색·SNS·명함 어디에서든 루트(`/`)로 들어올 수 있는데 로케일이
 * 없으면 페이지가 없다. 브라우저 언어를 보고 ko/en/fr 중 하나로 보내되
 * **모르는 언어면 한국어**로 둔다(추측해서 엉뚱한 언어를 보여주지 않는다).
 *
 * `/dashboard`는 건드리지 않는다 — 언어와 무관한 실시간 화면이고, 이미 공유된
 * 링크를 깨지 않아야 한다.
 */

const SKIP_PREFIXES = ['/dashboard', '/robots.txt', '/sitemap.xml'];

function pickLocale(header: string | null): string {
  if (!header) return defaultLocale;
  // "fr-CA,fr;q=0.9,en;q=0.8" → ["fr-ca", "fr", "en"]
  const wanted = header
    .split(',')
    .map((part) => part.split(';')[0].trim().toLowerCase())
    .filter(Boolean);
  for (const tag of wanted) {
    const base = tag.split('-')[0];
    const hit = locales.find((l) => l === base);
    if (hit) return hit;
  }
  return defaultLocale;
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (SKIP_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return NextResponse.next();
  }

  const hasLocale = locales.some(
    (l) => pathname === `/${l}` || pathname.startsWith(`/${l}/`),
  );
  if (hasLocale) return NextResponse.next();

  const locale = pickLocale(request.headers.get('accept-language'));
  const url = request.nextUrl.clone();
  url.pathname = `/${locale}${pathname === '/' ? '' : pathname}`;
  return NextResponse.redirect(url);
}

export const config = {
  // 내부 경로(_next)·API·정적 파일은 건너뛴다.
  matcher: ['/((?!_next|api|.*\\..*).*)'],
};
