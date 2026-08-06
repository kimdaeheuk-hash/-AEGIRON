/**
 * 사이트 공통 레이아웃 조각.
 *
 * 예전에는 스타일이 페이지마다 인라인으로 흩어져 있어서, 페이지가 늘어나면
 * 여백·제목 크기가 페이지마다 어긋난다. 여기 모아두면 한 곳만 고쳐도 전 페이지에
 * 반영된다 — 페이지 수를 늘리기로 한 이상 이게 먼저다.
 */

export function Section({
  children,
  narrow = false,
  pad = 'lg',
}: {
  children: React.ReactNode;
  narrow?: boolean;
  pad?: 'sm' | 'lg';
}) {
  return (
    <section
      style={{
        maxWidth: narrow ? 880 : 1320,
        margin: '0 auto',
        padding:
          pad === 'lg'
            ? 'clamp(48px,6vw,86px) clamp(14px,2.4vw,26px)'
            : 'clamp(26px,3vw,40px) clamp(14px,2.4vw,26px)',
      }}
    >
      {children}
    </section>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  lead,
  as: Tag = 'h2',
}: {
  eyebrow?: string;
  title: string;
  lead?: string;
  as?: 'h1' | 'h2';
}) {
  return (
    <header style={{ marginBottom: 32, maxWidth: 760 }}>
      {eyebrow && (
        <p
          style={{
            fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.12em',
            textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 12,
          }}
        >
          {eyebrow}
        </p>
      )}
      <Tag
        style={{
          fontFamily: 'var(--disp)', fontWeight: 800,
          fontSize: Tag === 'h1' ? 'clamp(30px,4.6vw,56px)' : 'clamp(23px,2.8vw,34px)',
          lineHeight: 1.16, letterSpacing: '-.025em', whiteSpace: 'pre-line',
        }}
      >
        {title}
      </Tag>
      {lead && (
        <p style={{ color: 'var(--muted)', fontSize: 'clamp(14px,1.15vw,16px)', lineHeight: 1.75, marginTop: 16 }}>
          {lead}
        </p>
      )}
    </header>
  );
}

export function Card({
  children,
  accent = false,
}: {
  children: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <div
      style={{
        border: `1px solid ${accent ? 'rgba(244,63,94,.32)' : 'var(--line)'}`,
        background: accent ? 'rgba(244,63,94,.05)' : 'var(--panel)',
        borderRadius: 14,
        padding: 'clamp(18px,2vw,26px)',
        height: '100%',
      }}
    >
      {children}
    </div>
  );
}

export function Grid({
  children,
  min = 240,
}: {
  children: React.ReactNode;
  min?: number;
}) {
  return (
    <div
      style={{
        display: 'grid',
        gap: 16,
        gridTemplateColumns: `repeat(auto-fit, minmax(min(${min}px, 100%), 1fr))`,
      }}
    >
      {children}
    </div>
  );
}
