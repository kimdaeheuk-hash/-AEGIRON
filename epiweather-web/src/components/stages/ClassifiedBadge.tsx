'use client';
import { Classification } from '@/lib/api';

// 기밀 프로그램 헤더 — 코드명·담당센터·보안등급을 방송체로 노출.
export default function ClassifiedBadge({ c }: { c?: Classification }) {
  if (!c) return null;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
      padding: '10px 14px', marginBottom: 12, borderRadius: 10,
      background: 'rgba(244,63,94,.06)', border: '1px solid rgba(244,63,94,.28)',
    }}>
      <span style={{
        fontFamily: 'var(--mono)', fontWeight: 800, fontSize: 11, letterSpacing: '.12em',
        color: '#fff', background: '#f43f5e', borderRadius: 5, padding: '4px 10px', flexShrink: 0,
      }}>
        ⬢ {c.program_code}
      </span>
      <span style={{ fontFamily: 'var(--kr)', fontSize: 12.5, fontWeight: 700 }}>{c.program_name_ko}</span>
      <span style={{ fontFamily: 'var(--kr)', fontSize: 11, color: 'var(--muted)' }}>
        {c.owning_center_ko} · {c.designation_ko}
      </span>
      <span style={{
        marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, fontWeight: 700,
        color: '#fbbf24', border: '1px solid rgba(251,191,36,.4)', borderRadius: 5, padding: '3px 8px', flexShrink: 0,
      }}>
        🔒 {c.classification_ko}
      </span>
    </div>
  );
}
