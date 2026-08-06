/**
 * OG 이미지용 폰트 로더.
 *
 * ★ 왜 필요한가 ★ ImageResponse는 Satori로 그리는데, 기본 폰트에 **한글이 없다.**
 * 그대로 두면 한국어 OG 카드의 글자가 통째로 빈칸이나 두부(□)로 나온다 —
 * 링크 공유 미리보기가 깨진 채로 나가는 게 이미지를 안 넣느니만 못하다.
 *
 * 전체 한글 폰트는 수 MB라 서버리스 함수에 얹기 부담스럽다. 그래서 Google Fonts의
 * `text=` 파라미터로 **그 이미지에 실제로 쓰이는 글자만** 담은 부분셋을 받는다
 * (보통 수십 KB). 프랑스어 악센트 문자도 같은 경로로 해결된다.
 *
 * 실패해도 예외를 던지지 않는다 — 폰트를 못 받으면 기본 폰트로라도 이미지가 나가야
 * 페이지 메타데이터가 깨지지 않는다.
 */

const GOOGLE_CSS = 'https://fonts.googleapis.com/css2';
// Satori에 넘길 폰트 이름. 실제 파일이 무엇이든 이 이름으로 참조한다.
export const OG_FONT_FAMILY = 'OgSans';

/** 폰트는 자주 안 바뀐다 — 하루 캐시로 매 요청 왕복을 없앤다. */
const REVALIDATE = 86400;

type LoadedFont = { name: string; data: ArrayBuffer; weight: 400 | 700; style: 'normal' };

async function subset(family: string, weight: 400 | 700, text: string): Promise<ArrayBuffer | null> {
  try {
    const url =
      `${GOOGLE_CSS}?family=${encodeURIComponent(family)}:wght@${weight}` +
      `&text=${encodeURIComponent(text)}&display=swap`;
    const css = await fetch(url, {
      // 이 UA가 아니면 Google이 woff2를 준다 — Satori는 woff2를 못 읽는다.
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36' },
      next: { revalidate: REVALIDATE },
    }).then((r) => (r.ok ? r.text() : ''));

    const src = css.match(/src:\s*url\(([^)]+)\)/)?.[1];
    if (!src) return null;
    const res = await fetch(src, { next: { revalidate: REVALIDATE } });
    if (!res.ok) return null;
    return await res.arrayBuffer();
  } catch {
    return null;
  }
}

/**
 * 이미지에 들어갈 문자열들을 주면, 그 글자만 담은 폰트를 돌려준다.
 * 한글이 섞여 있으면 한글 폰트를, 아니면 라틴 폰트를 쓴다.
 */
export async function ogFonts(...texts: string[]): Promise<LoadedFont[]> {
  const joined = texts.filter(Boolean).join(' ');
  // 부분셋에 없는 글자는 안 그려지므로, 브랜드명·숫자 등 고정 요소를 항상 포함한다.
  const charset = Array.from(
    new Set((joined + 'AEGIRON Busan, KR 0123456789·—…').split('')),
  ).join('');

  const hasHangul = /[가-힣]/.test(joined);
  const family = hasHangul ? 'Noto Sans KR' : 'Noto Sans';

  const [regular, bold] = await Promise.all([
    subset(family, 400, charset),
    subset(family, 700, charset),
  ]);

  const fonts: LoadedFont[] = [];
  if (regular) fonts.push({ name: OG_FONT_FAMILY, data: regular, weight: 400, style: 'normal' });
  if (bold) fonts.push({ name: OG_FONT_FAMILY, data: bold, weight: 700, style: 'normal' });
  return fonts;
}
