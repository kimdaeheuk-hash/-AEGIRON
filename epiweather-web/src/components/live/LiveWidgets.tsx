import Image from 'next/image';
import Link from 'next/link';
import type { ExtraDict } from '@/i18n/types';
import type { OpsStatus, RiskRow, AlertItem } from '@/lib/live';

/**
 * 실가동 위젯 — 홈·/live·/record 가 함께 쓴다.
 * 값은 전부 운영 API 실측(lib/live.ts). 못 읽으면 '읽지 못했다'를 그대로 보인다.
 */

type L = ExtraDict['live'];

export function fmtTime(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 16).replace('T', ' ') + ' UTC';
}

const nf = new Intl.NumberFormat('en-US');

export function OpsCounters({ ops, labels }: { ops: OpsStatus | null; labels: L }) {
  if (!ops) return <Unavailable text={labels.unavailable} />;
  const items: [string, string][] = [
    [labels.counters.predictions, nf.format(ops.counts.predictions)],
    [labels.counters.alerts, nf.format(ops.counts.alerts)],
    [labels.counters.extracted, nf.format(ops.counts.extracted)],
    [labels.counters.sentinel, nf.format(ops.counts.sentinel)],
    [labels.counters.declarations, nf.format(ops.counts.declarations)],
    [labels.counters.sources, `${ops.healthy}/${ops.total}`],
  ];
  return (
    <div>
      <div
        style={{
          display: 'grid', gap: 1, background: 'var(--line)', border: '1px solid var(--line)',
          borderRadius: 14, overflow: 'hidden',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(160px, 100%), 1fr))',
        }}
      >
        {items.map(([label, value]) => (
          <div key={label} style={{ background: 'var(--panel)', padding: '18px 18px 16px' }}>
            <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 'clamp(24px,2.6vw,32px)', lineHeight: 1 }}>
              {value}
            </div>
            <div style={{ fontSize: 12.5, marginTop: 9, color: 'var(--muted)', fontWeight: 600 }}>{label}</div>
          </div>
        ))}
      </div>
      <LiveStamp text={labels.countersNote} />
    </div>
  );
}

export function RiskTop({ rows, labels }: { rows: RiskRow[] | null; labels: L }) {
  if (!rows || rows.length === 0) return <Unavailable text={labels.riskUnavailable} />;
  const max = Math.max(...rows.map((r) => r.risk_score), 1);
  return (
    <div style={{ display: 'grid', gap: 9 }}>
      {rows.map((r, i) => (
        <div key={r.country} style={{ display: 'grid', gridTemplateColumns: '28px minmax(0,150px) 1fr 52px', gap: 12, alignItems: 'center' }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>{String(i + 1).padStart(2, '0')}</span>
          <span style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)', marginRight: 7 }}>{r.country}</span>
            {r.name}
          </span>
          <span style={{ height: 8, borderRadius: 999, background: 'var(--panel2)', overflow: 'hidden' }}>
            <span style={{ display: 'block', height: '100%', width: `${(r.risk_score / max) * 100}%`, background: 'var(--cyan)', borderRadius: 999 }} />
          </span>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 13, textAlign: 'right', fontWeight: 700 }}>{r.risk_score.toFixed(1)}</span>
        </div>
      ))}
      <Link href="/dashboard" style={{ marginTop: 8, fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)', textDecoration: 'none', fontWeight: 700 }}>
        {labels.riskOpen} →
      </Link>
    </div>
  );
}

export function ScreenGallery({ labels, limit }: { labels: L; limit?: number }) {
  const screens = limit ? labels.screens.slice(0, limit) : labels.screens;
  return (
    <div style={{ display: 'grid', gap: 18, gridTemplateColumns: 'repeat(auto-fit, minmax(min(420px, 100%), 1fr))' }}>
      {screens.map((s) => {
        const mobile = s.file.includes('mobile');
        return (
          <figure key={s.file} style={{ margin: 0, border: '1px solid var(--line)', borderRadius: 14, overflow: 'hidden', background: 'var(--panel)' }}>
            <div style={{ position: 'relative', aspectRatio: mobile ? '9 / 10' : '16 / 10.4', background: '#0b1018' }}>
              <Image
                src={`/media/live/${s.file}`}
                alt={s.title}
                fill
                sizes="(max-width: 900px) 100vw, 640px"
                style={{ objectFit: mobile ? 'contain' : 'cover', objectPosition: 'top center' }}
              />
              <span
                style={{
                  position: 'absolute', top: 12, left: 12, fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 700,
                  padding: '5px 10px', borderRadius: 999,
                  background: s.kind === 'live' ? '#0f766e' : '#a15c07', color: '#fff',
                }}
              >
                ● {s.kind === 'live' ? labels.kindLive : labels.kindModel}
              </span>
            </div>
            <figcaption style={{ padding: '14px 16px 16px', wordBreak: 'keep-all' }}>
              <strong style={{ display: 'block', fontSize: 14.5, marginBottom: 6 }}>{s.title}</strong>
              <span style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.65 }}>{s.caption}</span>
            </figcaption>
          </figure>
        );
      })}
    </div>
  );
}

export function SourceGrid({ ops, labels }: { ops: OpsStatus | null; labels: L }) {
  if (!ops) return <Unavailable text={labels.unavailable} />;
  return (
    <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(auto-fill, minmax(min(210px, 100%), 1fr))' }}>
      {ops.sources.map((s) => {
        const ok = s.status === 'ok';
        return (
          <div key={s.source} style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '10px 12px', background: 'var(--panel)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600 }}>{s.source}</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: ok ? 'var(--ok)' : 'var(--amber)' }}>
                ● {ok ? labels.sourceOk : labels.sourceIssue}
              </span>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--muted2)', marginTop: 5 }}>
              {labels.sourceStale} {fmtTime(s.last_success_at)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const TIER_COLOR: Record<string, string> = {
  critical: '#b42318', high: '#c2410c', medium: '#a15c07', low: '#4b5563',
};

export function AlertList({ alerts, labels }: { alerts: { items: AlertItem[] } | null; labels: L }) {
  if (!alerts) return <Unavailable text={labels.unavailable} />;
  if (alerts.items.length === 0) return <p style={{ color: 'var(--muted)', fontSize: 14 }}>{labels.alertsEmpty}</p>;
  return (
    <div style={{ display: 'grid', gap: 10 }}>
      {alerts.items.map((a) => (
        <div key={a.source} style={{ display: 'flex', gap: 14, alignItems: 'center', border: '1px solid var(--line)', borderRadius: 11, padding: '12px 14px', background: 'var(--panel)' }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', color: '#fff', background: TIER_COLOR[a.tier] ?? '#4b5563', borderRadius: 6, padding: '4px 8px', flexShrink: 0 }}>
            {a.tier}
          </span>
          <span style={{ fontSize: 14, fontWeight: 600, flex: 1, minWidth: 0 }}>{a.label}</span>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 700 }}>{a.score.toFixed(1)}</span>
        </div>
      ))}
    </div>
  );
}

export function TierBadge({ tier }: { tier: string }) {
  return (
    <span style={{ fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#fff', background: TIER_COLOR[tier] ?? '#4b5563', borderRadius: 6, padding: '4px 9px' }}>
      {tier}
    </span>
  );
}

export function Unavailable({ text }: { text: string }) {
  return (
    <p style={{ color: 'var(--muted)', fontSize: 13.5, border: '1px dashed var(--line2)', borderRadius: 10, padding: '14px 16px' }}>
      {text}
    </p>
  );
}

function LiveStamp({ text }: { text: string }) {
  return (
    <p style={{ display: 'flex', alignItems: 'center', gap: 7, fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)', marginTop: 10 }}>
      <span aria-hidden="true" style={{ width: 6, height: 6, borderRadius: 999, background: 'var(--ok)', animation: 'blink 1.6s infinite' }} />
      {text}
    </p>
  );
}
