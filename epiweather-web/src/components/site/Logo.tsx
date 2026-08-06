/** 레이더 로고 — 기존 Command/Home 화면과 같은 마크를 사이트 전역에서 재사용한다. */
export function Logo({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <circle cx="24" cy="24" r="21" stroke="var(--line2)" strokeWidth="1.5" />
      <circle cx="24" cy="24" r="13" stroke="var(--line)" strokeWidth="1.2" />
      <circle cx="24" cy="24" r="5" stroke="var(--line)" strokeWidth="1.2" />
      <path d="M24 24 L24 3" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
      <path
        d="M24 24 L41 15"
        stroke="var(--accent)"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.45"
      />
      <circle cx="33" cy="17" r="2.6" fill="var(--accent)" />
    </svg>
  );
}
