/**
 * OG 이미지 공통 틀.
 *
 * 왜 필요한가: 어제까지 링크를 공유하면 미리보기 이미지가 없어 밋밋한 텍스트
 * 카드만 떴다. 재보험사·국제기구에 링크를 보내는 게 실제 영업 경로인데, 첫인상이
 * 거기서 결정된다.
 *
 * ★ 제약 ★ ImageResponse는 브라우저가 아니라 Satori로 렌더링한다:
 * - flex 기반 레이아웃만 쓴다(자식이 둘 이상인 요소에는 display:flex가 필수).
 * - CSS 변수·외부 폰트·이미지 URL을 못 쓴다 → 색을 리터럴로 박고 SVG를 인라인한다.
 * - 한글은 기본 폰트에 없어 깨질 수 있어, 이미지에는 **로마자 위주**로 담고
 *   제목은 짧게 자른다(길면 잘리는 게 아니라 레이아웃이 무너진다).
 */

export const OG_SIZE = { width: 1200, height: 630 };
export const OG_CONTENT_TYPE = 'image/png';

const BG = '#050810';
const ACCENT = '#f43f5e';
const TEXT = '#e9eef5';
const MUTED = '#7c8aa0';
const LINE = 'rgba(120,140,170,.22)';

export function OgFrame({
  eyebrow,
  title,
  footnote,
}: {
  eyebrow: string;
  title: string;
  footnote: string;
}) {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        background: BG,
        padding: 72,
        // Satori에는 CSS 변수가 없으므로 그라디언트를 직접 적는다.
        backgroundImage:
          'radial-gradient(900px 500px at 85% -10%, rgba(244,63,94,.18), transparent 60%)',
      }}
    >
      {/* 상단 — 브랜드 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
        <svg width="52" height="52" viewBox="0 0 48 48">
          <circle cx="24" cy="24" r="21" stroke={LINE} strokeWidth="1.6" fill="none" />
          <circle cx="24" cy="24" r="13" stroke={LINE} strokeWidth="1.3" fill="none" />
          <path d="M24 24 L24 3" stroke={ACCENT} strokeWidth="2.4" />
          <circle cx="33" cy="17" r="3" fill={ACCENT} />
        </svg>
        <div
          style={{
            fontSize: 30,
            fontWeight: 700,
            color: TEXT,
            letterSpacing: -0.5,
          }}
        >
          AEGIRON
        </div>
      </div>

      {/* 중앙 — 제목 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div
          style={{
            fontSize: 21,
            color: ACCENT,
            letterSpacing: 3,
            textTransform: 'uppercase',
          }}
        >
          {eyebrow}
        </div>
        <div
          style={{
            fontSize: title.length > 60 ? 50 : 62,
            fontWeight: 700,
            color: TEXT,
            lineHeight: 1.18,
            letterSpacing: -1.5,
            // 넘치면 레이아웃이 무너지므로 줄 수를 제한한다.
            display: 'flex',
            maxWidth: 1000,
          }}
        >
          {title}
        </div>
      </div>

      {/* 하단 — 정직성 한 줄. 공유 카드에서도 이 원칙이 보여야 한다. */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderTop: `1px solid ${LINE}`,
          paddingTop: 26,
        }}
      >
        <div style={{ fontSize: 22, color: MUTED, maxWidth: 820, display: 'flex' }}>
          {footnote}
        </div>
        <div style={{ fontSize: 20, color: MUTED, display: 'flex' }}>Busan, KR</div>
      </div>
    </div>
  );
}

/** 이미지에 담을 길이로 자른다 — 넘치면 잘리는 게 아니라 판이 깨진다. */
export function clampTitle(text: string, max = 82): string {
  const flat = (text || '').replace(/\s+/g, ' ').trim();
  return flat.length > max ? `${flat.slice(0, max - 1)}…` : flat;
}
