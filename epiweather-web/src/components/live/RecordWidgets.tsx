import type { ExtraDict } from '@/i18n/types';
import { predictionStatus, type Prediction, type Scorecard, type Ledger, type AlertItem } from '@/lib/live';
import { fmtTime, TierBadge, Unavailable } from './LiveWidgets';

/**
 * 공개 예측 원장 위젯 — 판정 대기·실패까지 지우지 않고 그대로 보인다.
 * 근거 문장(basis·evidence)은 백엔드가 한국어로 쓰므로 원문 그대로 둔다.
 */

type R = ExtraDict['record'];

const nf = new Intl.NumberFormat('en-US');

export function ScoreBoard({ score, labels, unavailable }: { score: Scorecard | null; labels: R; unavailable: string }) {
  if (!score) return <Unavailable text={unavailable} />;
  const L = labels.scoreLabels;
  const cells: [string, string, string?][] = [
    [L.total, nf.format(score.total)],
    [L.resolved, nf.format(score.resolved)],
    [L.hit, nf.format(score.correct), 'var(--ok)'],
    [L.miss, nf.format(score.incorrect), 'var(--accent)'],
    [L.open, nf.format(score.unresolved)],
    [L.overdue, nf.format(score.overdue?.length ?? 0)],
    [L.brier, score.brier == null ? '—' : score.brier.toFixed(3)],
    [L.legacy, nf.format(score.unscoreable_legacy)],
  ];
  return (
    <div>
      <div
        style={{
          display: 'grid', gap: 1, background: 'var(--line)', border: '1px solid var(--line)', borderRadius: 14, overflow: 'hidden',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(140px, 100%), 1fr))',
        }}
      >
        {cells.map(([label, value, color]) => (
          <div key={label} style={{ background: 'var(--panel)', padding: '16px 16px 14px' }}>
            <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 26, lineHeight: 1, color: color ?? 'var(--txt)' }}>{value}</div>
            <div style={{ fontSize: 12, marginTop: 8, color: 'var(--muted)', fontWeight: 600 }}>{label}</div>
          </div>
        ))}
      </div>
      <p style={{ color: 'var(--muted2)', fontSize: 12.5, lineHeight: 1.7, marginTop: 12 }}>{labels.scoreNote}</p>
    </div>
  );
}

const STATUS_COLOR = { hit: 'var(--ok)', miss: 'var(--accent)', open: 'var(--muted)', other: 'var(--amber)' } as const;

export function PredictionTable({
  predictions, labels, unavailable, showCriteria,
}: { predictions: Prediction[] | null; labels: R; unavailable: string; showCriteria: boolean }) {
  if (!predictions) return <Unavailable text={unavailable} />;
  if (predictions.length === 0) return <p style={{ color: 'var(--muted)' }}>{labels.empty}</p>;
  const statusLabel = { hit: labels.statusHit, miss: labels.statusMiss, open: labels.statusOpen, other: labels.statusOther };
  return (
    <div style={{ display: 'grid', gap: 8 }}>
      {predictions.map((p) => {
        const st = predictionStatus(p);
        return (
          <details key={p.id} style={{ border: '1px solid var(--line)', borderRadius: 11, background: 'var(--panel)' }}>
            <summary
              style={{
                listStyle: 'none', cursor: 'pointer', padding: '12px 14px',
                display: 'grid', gap: 10, alignItems: 'center',
                gridTemplateColumns: 'minmax(0,52px) minmax(0,1.3fr) minmax(0,2fr) 70px 92px 86px',
              }}
              className="record-row"
            >
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>#{p.id}</span>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--muted)' }}>{fmtTime(p.predicted_at)}</span>
              <span style={{ fontSize: 13.5, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {p.country} · {p.disease}
              </span>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 700 }}>{p.risk_score.toFixed(1)}</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: STATUS_COLOR[st] }}>● {statusLabel[st]}</span>
              <span style={{ fontSize: 11.5, fontFamily: 'var(--mono)', color: p.content_hash ? 'var(--cyan)' : 'var(--muted2)' }}>
                {p.content_hash ? `🔏 ${labels.proofSealed}` : labels.proofNone}
              </span>
            </summary>
            <div style={{ padding: '0 14px 14px', fontSize: 12.5, color: 'var(--muted)', lineHeight: 1.7, display: 'grid', gap: 6 }}>
              {p.resolves_by && <div><b>{labels.colStatus}</b> · ~{p.resolves_by}</div>}
              {typeof p.confidence === 'number' && <div>confidence {p.confidence.toFixed(2)}</div>}
              {showCriteria && p.resolution_criteria && <div>{p.resolution_criteria}</div>}
              {p.content_hash && (
                <div style={{ fontFamily: 'var(--mono)', fontSize: 11, wordBreak: 'break-all' }}>
                  SHA-256 {p.content_hash} · {labels.proofSealed} {fmtTime(p.ots_submitted_at)}
                </div>
              )}
            </div>
          </details>
        );
      })}
    </div>
  );
}

export function LedgerList({ ledger, labels, unavailable }: { ledger: Ledger | null; labels: R; unavailable: string }) {
  if (!ledger) return <Unavailable text={unavailable} />;
  if (ledger.entries.length === 0) return <p style={{ color: 'var(--muted)' }}>{labels.ledgerEmpty}</p>;
  return (
    <div style={{ display: 'grid', gap: 8 }}>
      {ledger.entries.map((e) => (
        <div
          key={e.id}
          style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', border: '1px solid var(--line)', borderRadius: 11, padding: '11px 14px', background: 'var(--panel)' }}
        >
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--muted)' }}>{fmtTime(e.crossed_at)}</span>
          <span style={{ fontSize: 13.5, fontWeight: 600, flex: 1, minWidth: 160 }}>
            {e.disease}{e.country_iso3 ? ` · ${e.country_iso3}` : ''}
          </span>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{e.severity.toFixed(0)} / {e.threshold.toFixed(0)}</span>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 700, color: e.outcome === 'open' ? 'var(--muted)' : 'var(--ok)' }}>
            ● {e.outcome}
          </span>
        </div>
      ))}
    </div>
  );
}

export function AlertAnatomy({ alert, labels, date }: { alert: AlertItem | null; labels: R; date?: string }) {
  if (!alert) return <p style={{ color: 'var(--muted)' }}>{labels.anatomyEmpty}</p>;
  const F = labels.anatomyFields;
  return (
    <div style={{ border: '1px solid var(--line2)', borderRadius: 14, overflow: 'hidden', background: 'var(--panel)' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', padding: '16px 18px', borderBottom: '1px solid var(--line)' }}>
        <TierBadge tier={alert.tier} />
        <strong style={{ fontSize: 16, flex: 1, minWidth: 200 }}>{alert.label}</strong>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 22, fontWeight: 700 }}>{alert.score.toFixed(1)}</span>
      </div>
      <dl style={{ display: 'grid', gap: 1, background: 'var(--line)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(220px, 100%), 1fr))' }}>
        {[
          [F.level, alert.tier],
          [F.score, alert.score.toFixed(1)],
          [F.source, alert.source],
          [F.time, date ?? '—'],
        ].map(([k, v]) => (
          <div key={k} style={{ background: 'var(--panel)', padding: '11px 18px' }}>
            <dt style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--muted2)', letterSpacing: '.06em' }}>{k}</dt>
            <dd style={{ fontFamily: 'var(--mono)', fontSize: 13, marginTop: 4, wordBreak: 'break-all' }}>{v}</dd>
          </div>
        ))}
      </dl>
      <div style={{ padding: '16px 18px 18px' }}>
        <p style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--muted2)', letterSpacing: '.06em', marginBottom: 10 }}>{F.reason}</p>
        <ol style={{ display: 'grid', gap: 9, paddingLeft: 18 }}>
          {(alert.evidence ?? []).map((ev, i) => (
            <li key={i} style={{ fontSize: 13.5, lineHeight: 1.7, color: 'var(--txt)' }}>{ev}</li>
          ))}
        </ol>
      </div>
    </div>
  );
}
