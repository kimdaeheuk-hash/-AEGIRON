import type { ExtraDict } from '@/i18n/types';
import {
  predictionStatus, isoWeek, apiUrl,
  type Prediction, type Scorecard, type Ledger, type AlertItem, type WeeklyForecasts, type KoreaImportReport, type ImportRow,
} from '@/lib/live';
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

// ── 주간 추세 예측 채점표 (2026-10-19) ─────────────────────────
// 90일 예측 채점표와 합치지 않는다. 판정 min_scored 건 전에는 Brier·적중을 '—'로 둔다.

const cellGrid = {
  display: 'grid', gap: 1, background: 'var(--line)', border: '1px solid var(--line)', borderRadius: 14, overflow: 'hidden',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(140px, 100%), 1fr))',
} as const;

function Cells({ cells }: { cells: [string, string, string?][] }) {
  return (
    <div style={cellGrid}>
      {cells.map(([label, value, color]) => (
        <div key={label} style={{ background: 'var(--panel)', padding: '16px 16px 14px' }}>
          <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 24, lineHeight: 1, color: color ?? 'var(--txt)' }}>{value}</div>
          <div style={{ fontSize: 12, marginTop: 8, color: 'var(--muted)', fontWeight: 600 }}>{label}</div>
        </div>
      ))}
    </div>
  );
}

export function WeeklyBoard({ data, labels, unavailable }: { data: WeeklyForecasts | null; labels: R; unavailable: string }) {
  if (!data) return <Unavailable text={unavailable} />;
  const W = labels.weekly;
  const L = W.labels;
  const c = data.scorecard;
  const ratio = (h: number | null, n: number | null) => (c.enough && h != null && n ? `${h}/${n}` : '—');
  return (
    <div>
      <Cells
        cells={[
          [L.scored, nf.format(c.scored)],
          [L.open, nf.format(c.open)],
          [L.void, nf.format(c.void)],
          [L.brierModel, c.enough && c.brier_model != null ? c.brier_model.toFixed(3) : '—'],
          [L.brierCoin, c.brier_coin.toFixed(2)],
          [L.hitsModel, ratio(c.hits_model, c.calls_model)],
          [L.hitsNaive, ratio(c.hits_naive, c.calls_naive)],
        ]}
      />
      {!c.enough && (
        <p style={{ fontSize: 13, fontWeight: 600, marginTop: 12 }}>
          {W.notEnough.replace('{n}', String(c.scored)).replaceAll('{min}', String(c.min_scored))}
        </p>
      )}
      <p style={{ color: 'var(--muted2)', fontSize: 12.5, lineHeight: 1.7, marginTop: 8 }}>{W.note}</p>
    </div>
  );
}

export function WeeklyList({ data, labels }: { data: WeeklyForecasts | null; labels: R }) {
  if (!data) return null;
  const W = labels.weekly;
  if (data.forecasts.length === 0) return <p style={{ color: 'var(--muted)' }}>{W.empty}</p>;
  const status = (o: string | null | undefined) =>
    o === 'up' ? [W.statusUp, 'var(--txt)'] : o === 'down' ? [W.statusDown, 'var(--txt)'] : o === 'void' ? [W.statusVoid, 'var(--amber)'] : [W.statusOpen, 'var(--muted)'];
  return (
    <div style={{ display: 'grid', gap: 8 }}>
      {data.forecasts.map((f) => {
        const [st, color] = status(f.outcome);
        return (
          <div
            key={f.id}
            style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 14px', alignItems: 'center', border: '1px solid var(--line)', borderRadius: 11, padding: '11px 14px', background: 'var(--panel)' }}
          >
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>#{f.id}</span>
            <span style={{ fontSize: 13.5, fontWeight: 600, minWidth: 130 }}>{W.series[f.series] ?? f.series}</span>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--muted)' }}>
              {W.base} {isoWeek(f.base_year, f.base_week)} ({nf.format(f.base_value)}) → {W.target} {isoWeek(f.target_year, f.target_week)}
            </span>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 700 }}>{W.probUp} {f.prob_up.toFixed(2)}</span>
            <span style={{ fontSize: 12, fontWeight: 700, color }}>
              ● {st}{f.actual_value != null && f.outcome !== 'void' ? ` (${nf.format(f.actual_value)})` : ''}
            </span>
            {f.content_hash && (
              <span style={{ fontSize: 11.5, fontFamily: 'var(--mono)', color: 'var(--cyan)' }}>🔏 {W.sealed}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── 대한민국 해외 유입 위험 주간 보고서 (2026-10-19) ─────────────
// 노출 지수는 확률이 아니다 — 고지를 표 바로 아래에 둔다.

function ImportTable({ rows, labels, withIndex }: { rows: ImportRow[]; labels: R['importReport']; withIndex: boolean }) {
  const th = { textAlign: 'left', padding: '8px 10px', fontSize: 11.5, color: 'var(--muted2)', fontWeight: 600, whiteSpace: 'nowrap' } as const;
  const td = { padding: '9px 10px', borderTop: '1px solid var(--line)', verticalAlign: 'top' } as const;
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 520 }}>
        <thead>
          <tr>
            {/* 휴대폰에서 표가 옆으로 밀릴 때 노출 지수가 먼저 보이도록 국가 바로 뒤에 둔다. */}
            <th style={th}>{labels.colCountry}</th>
            {withIndex && <th style={th}>{labels.colIndex}</th>}
            <th style={th}>{labels.colScore}</th>
            {withIndex && <th style={th}>{labels.colRoutes}</th>}
            <th style={th}>{labels.colDisease}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.country}>
              <td style={{ ...td, fontWeight: 600 }}>
                {r.name ?? r.country} <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>{r.country}</span>
              </td>
              {withIndex && <td style={{ ...td, fontFamily: 'var(--mono)', fontWeight: 700 }}>{r.exposure_index?.toFixed(1) ?? '—'}</td>}
              <td style={{ ...td, fontFamily: 'var(--mono)' }}>{r.raw_score.toFixed(1)}</td>
              {withIndex && <td style={{ ...td, fontFamily: 'var(--mono)' }}>{r.direct_routes_to_kor}</td>}
              <td style={{ ...td, color: 'var(--muted)' }}>{r.dominant_disease ?? labels.noDisease}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ImportReportView({ report, labels, weeklyLabels }: { report: KoreaImportReport | null; labels: R['importReport']; weeklyLabels: R['weekly'] }) {
  if (!report) return <Unavailable text={labels.notYet} />;
  const s = report.summary;
  const h3 = { fontWeight: 700, fontSize: 15, margin: '22px 0 10px' } as const;
  return (
    <div>
      <p style={{ fontFamily: 'var(--mono)', fontSize: 12.5, color: 'var(--muted)', marginBottom: 12 }}>
        {labels.week} <strong style={{ color: 'var(--txt)' }}>{report.week}</strong> · {labels.generated} {fmtTime(report.generated_at)}
      </p>
      <Cells
        cells={[
          [labels.summary.signal, nf.format(s.countries_with_signal)],
          [labels.summary.exposed, nf.format(s.exposed_countries)],
          [labels.summary.noRoute, nf.format(s.no_direct_route_high)],
          [labels.summary.alerts, nf.format(s.active_alerts)],
        ]}
      />

      <h3 style={h3}>{labels.topTitle}</h3>
      {report.routes_error && <p style={{ color: 'var(--amber)', fontSize: 13, marginBottom: 8 }}>⚠ {labels.routesError}</p>}
      {report.top_exposure.length ? <ImportTable rows={report.top_exposure} labels={labels} withIndex /> : <p style={{ color: 'var(--muted)' }}>{labels.topEmpty}</p>}

      <h3 style={h3}>{labels.noRouteTitle}</h3>
      {report.no_direct_route_high.length ? <ImportTable rows={report.no_direct_route_high} labels={labels} withIndex={false} /> : <p style={{ color: 'var(--muted)' }}>{labels.noRouteEmpty}</p>}

      {report.neighbor_trends.length > 0 && (
        <>
          <h3 style={h3}>{labels.trendsTitle}</h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 6 }}>
            {report.neighbor_trends.map((t) => (
              <li key={t.series} style={{ fontSize: 13, lineHeight: 1.7 }}>
                <strong>{weeklyLabels.series[t.series] ?? t.series}</strong>
                <span style={{ fontFamily: 'var(--mono)', color: 'var(--muted)' }}>
                  {' '}· {t.base_week} {nf.format(t.base_value)} → {t.target_week} {weeklyLabels.probUp} {t.prob_up.toFixed(2)}
                  {t.last_scored && ` · ${labels.lastScored} ${t.last_scored.target_week}: ${t.last_scored.prob_up.toFixed(2)} → ${t.last_scored.outcome === 'up' ? weeklyLabels.statusUp : weeklyLabels.statusDown}`}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      <ul style={{ margin: '20px 0 0', paddingLeft: 18, display: 'grid', gap: 4 }}>
        {labels.caveats.map((c) => (
          <li key={c} style={{ fontSize: 12.5, color: 'var(--muted2)', lineHeight: 1.7 }}>{c}</li>
        ))}
      </ul>
      {labels.originalNote && <p style={{ fontSize: 12, color: 'var(--muted2)', marginTop: 8 }}>{labels.originalNote}</p>}
      <p style={{ marginTop: 14 }}>
        <a href={apiUrl(`/api/korea-import-report?week=${report.week}&format=md`)} style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)' }}>
          {labels.markdown} →
        </a>
      </p>
    </div>
  );
}
