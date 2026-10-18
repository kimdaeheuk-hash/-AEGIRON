/**
 * 히어로 배경 — 전 세계 감시망을 닮은 점·연결선.
 *
 * 2026-08-06 검수에서 캡틴이 "첫 화면은 처음 만든 게 더 나았다"고 해서, 처음 홈
 * (`components/Home.tsx`)의 배경을 그대로 옮겨 왔다. 장식이라 스크린리더에서 숨긴다.
 */
const DOTS: [number, number][] = [
  [8, 22], [18, 12], [30, 30], [42, 8], [55, 24], [68, 14], [80, 32], [92, 18],
  [14, 46], [26, 58], [38, 44], [50, 62], [63, 48], [75, 60], [88, 46],
  [10, 74], [22, 82], [34, 70], [48, 86], [60, 76], [72, 84], [84, 72],
];

export function HeroBackdrop() {
  return (
    <div
      aria-hidden="true"
      style={{ position: 'absolute', inset: 0, zIndex: 0, opacity: 0.55, pointerEvents: 'none' }}
    >
      <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" style={{ width: '100%', height: '100%' }}>
        <defs>
          <radialGradient id="hero-fade" cx="50%" cy="30%" r="70%">
            <stop offset="0%" style={{ stopColor: 'var(--hero-glow)', stopOpacity: 0.5 }} />
            <stop offset="100%" style={{ stopColor: 'var(--hero-glow)', stopOpacity: 0 }} />
          </radialGradient>
        </defs>
        {DOTS.map(([x, y], i) =>
          DOTS.slice(i + 1, i + 3).map(([x2, y2], j) => (
            <line key={`${i}-${j}`} x1={x} y1={y} x2={x2} y2={y2} stroke="var(--line2)" strokeWidth=".15" />
          )),
        )}
        {DOTS.map(([x, y], i) => (
          <circle
            key={i}
            cx={x}
            cy={y}
            r={i % 5 === 0 ? 0.9 : 0.5}
            fill={i % 7 === 0 ? 'var(--cyan)' : i % 5 === 0 ? 'var(--accent)' : 'var(--muted2)'}
            opacity={i % 5 === 0 ? 1 : 0.6}
          >
            {i % 5 === 0 && (
              <animate attributeName="opacity" values="1;.3;1" dur={`${2 + (i % 4)}s`} repeatCount="indefinite" />
            )}
          </circle>
        ))}
        <circle cx="50" cy="30" r="45" fill="url(#hero-fade)" />
      </svg>
    </div>
  );
}
