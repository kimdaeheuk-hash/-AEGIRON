'use client';
import { useMemo, useState, type CSSProperties } from 'react';
import { OriginCity } from '@/lib/api';

// 발원지 검색 드롭다운 — 큐레이션 8개 도시(실제 발병사례 기반) + World Bank
// 실제 전세계 국가(tier=auto, 위험도 미보정·참고용)를 검색·지역별로 보여줌.
// 국가명 한글 표기는 브라우저 내장 Intl.DisplayNames로 생성(별도 번역 불필요).

const REGION_KO: Record<string, string> = {
  'East Asia & Pacific': '동아시아·태평양',
  'Europe & Central Asia': '유럽·중앙아시아',
  'Latin America & Caribbean': '중남미·카리브해',
  'Middle East, North Africa, Afghanistan & Pakistan': '중동·북아프리카·아프간·파키스탄',
  'Middle East & North Africa': '중동·북아프리카',
  'North America': '북미',
  'South Asia': '남아시아',
  'Sub-Saharan Africa': '사하라이남 아프리카',
};

function displayName(o: OriginCity): string {
  if (o.tier === 'curated') return o.nm;
  if (o.iso2) {
    try {
      const dn = new Intl.DisplayNames(['ko'], { type: 'region' }).of(o.iso2);
      if (dn) return dn;
    } catch {
      // Intl.DisplayNames 미지원 브라우저 — 아래 영문명 폴백
    }
  }
  return o.nm;
}

export default function OriginSelector({ value, origins, onChange }: {
  value: string; origins: OriginCity[]; onChange: (id: string) => void;
}) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);

  const selected = origins.find(o => o.id === value);
  const selectedLabel = selected ? displayName(selected) : value;

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matches = (o: OriginCity) =>
      !q || displayName(o).toLowerCase().includes(q) || o.nm.toLowerCase().includes(q) || o.id.toLowerCase().includes(q);
    const filtered = origins.filter(matches);
    const curated = filtered.filter(o => o.tier === 'curated');
    const byRegion = new Map<string, OriginCity[]>();
    for (const o of filtered) {
      if (o.tier !== 'auto') continue;
      const key = o.region ?? '기타';
      if (!byRegion.has(key)) byRegion.set(key, []);
      byRegion.get(key)!.push(o);
    }
    return { curated, byRegion };
  }, [origins, query]);

  function pick(id: string) {
    onChange(id);
    setQuery('');
    setOpen(false);
  }

  return (
    <div style={{ position: 'relative', width: 230 }}>
      <input
        value={open ? query : selectedLabel}
        onChange={e => { setQuery(e.target.value); setOpen(true); }}
        onFocus={() => { setQuery(''); setOpen(true); }}
        onBlur={() => setOpen(false)}
        placeholder="국가 검색…"
        style={{
          width: '100%', fontFamily: 'var(--kr)', fontSize: 12.5, color: 'var(--txt)',
          background: 'var(--bg2)', border: '1px solid var(--line)', borderRadius: 9,
          padding: '8px 11px', cursor: 'text',
        }}
      />
      {open && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4, width: 300, maxHeight: 340,
          overflowY: 'auto', background: 'var(--panel)', border: '1px solid var(--line)',
          borderRadius: 10, zIndex: 50, boxShadow: '0 12px 32px rgba(0,0,0,.45)', padding: 6,
        }}>
          {grouped.curated.length > 0 && (
            <div style={{ marginBottom: 6 }}>
              <div style={groupLabelStyle}>주요 사례(실측 기반)</div>
              {grouped.curated.map(o => (
                <Option key={o.id} label={displayName(o)} sub={o.note} onPick={() => pick(o.id)} />
              ))}
            </div>
          )}
          {[...grouped.byRegion.entries()].map(([region, items]) => (
            <div key={region} style={{ marginBottom: 6 }}>
              <div style={groupLabelStyle}>{REGION_KO[region] ?? region}</div>
              {items.map(o => (
                <Option key={o.id} label={displayName(o)} auto onPick={() => pick(o.id)} />
              ))}
            </div>
          ))}
          {grouped.curated.length === 0 && grouped.byRegion.size === 0 && (
            <div style={{ padding: '10px 8px', fontFamily: 'var(--kr)', fontSize: 11.5, color: 'var(--muted2)' }}>
              검색 결과 없음
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const groupLabelStyle: CSSProperties = {
  fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.1em', color: 'var(--muted2)',
  textTransform: 'uppercase', padding: '4px 8px',
};

function Option({ label, sub, auto, onPick }: { label: string; sub?: string; auto?: boolean; onPick: () => void }) {
  return (
    <div
      onMouseDown={(e) => { e.preventDefault(); onPick(); }}
      style={{
        display: 'flex', alignItems: 'center', gap: 6, padding: '7px 8px', borderRadius: 7,
        cursor: 'pointer', fontFamily: 'var(--kr)', fontSize: 12,
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--panel2)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
    >
      <span>{label}</span>
      {auto && (
        <span style={{
          fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--muted2)',
          border: '1px solid var(--line2)', borderRadius: 4, padding: '1px 5px', flexShrink: 0,
        }}>참고용</span>
      )}
      {sub && <span style={{ fontFamily: 'var(--kr)', fontSize: 10, color: 'var(--muted2)', marginLeft: 'auto' }}>{sub}</span>}
    </div>
  );
}
