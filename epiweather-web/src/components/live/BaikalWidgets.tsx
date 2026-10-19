import type { BaikalDict, SystemCode, SystemDict, EngineGroupDict } from '@/i18n/types';
import type { BaikalResult, BaikalSnapshot, BaikalSystem, BaikalTransition } from '@/lib/live';
import { fmtTime, Unavailable } from './LiveWidgets';

/**
 * BAIKAL MOB 화면 부품 (2026-10-19) — 아이기론 대표 시스템.
 *
 * ★ 상태를 지어내지 않는다 ★
 * - 운영 API(/api/baikal)를 못 읽으면 상태 카드를 그리지 않고 "읽지 못함"을 쓴다.
 * - 스냅숏이 낡았으면(stale) 카드 위에 그 사실을 먼저 쓴다 — 몇 시간 전의 '정상'이
 *   지금처럼 읽히지 않게.
 * - 시스템마다 판정 범위(scope)와 측정/추정/대리 라벨을 같이 그린다.
 * - 근거 문장은 운영 로그 원문(한국어)이다. en·fr 판에서는 그 사실을 밝힌다.
 */

export const SYSTEM_ORDER: SystemCode[] = ['HUGINN', 'MIMIR', 'FORSETI', 'SKULD', 'HEIMDALL', 'VALHALLA', 'VAR'];

/** 시스템별 묶음 색 — 홈 엔진 구성·대표 시스템 화면이 같은 색을 쓴다. */
export const SYSTEM_TONE: Record<SystemCode, string> = {
  HUGINN: 'var(--t-teal)',
  MIMIR: 'var(--t-sky)',
  FORSETI: 'var(--t-crimson)',
  SKULD: 'var(--t-indigo)',
  HEIMDALL: 'var(--t-violet)',
  VALHALLA: 'var(--t-forest)',
  VAR: 'var(--t-amber)',
};

const STATUS_COLOR: Record<string, string> = {
  ok: '#15803d',
  degraded: '#b45309',
  down: '#b91c1c',
  undetermined: '#6b7280',
};

/** "HUGINN · 후긴" — 현지 표기가 코드명과 같으면(en·fr 'Huginn') 한 번만 쓴다. */
export function systemTitle(s: SystemDict): string {
  return s.name.toLowerCase() === s.code.toLowerCase() ? s.code : `${s.code} · ${s.name}`;
}

export function systemByCode(systems: SystemDict[]): Record<string, SystemDict> {
  return Object.fromEntries(systems.map((s) => [s.code, s]));
}

export function StatusBadge({ status, label }: { status: string; label: string }) {
  return (
    <span
      style={{
        fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 700, color: '#fff',
        background: STATUS_COLOR[status] ?? STATUS_COLOR.undetermined,
        borderRadius: 6, padding: '4px 9px', whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
}

/** 3층 구조 — 엔진 → YGGDRASIL → BAIKAL MOB */
export function LayerDiagram({ labels }: { labels: BaikalDict }) {
  return (
    <ol
      style={{
        listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 14,
        gridTemplateColumns: 'repeat(auto-fit, minmax(min(250px, 100%), 1fr))',
      }}
    >
      {labels.layers.map((layer, i) => (
        <li
          key={layer.code}
          style={{
            position: 'relative', border: '1px solid var(--line2)', borderRadius: 14, padding: '20px 20px 22px',
            background: 'var(--panel)', borderTop: `4px solid ${i === labels.layers.length - 1 ? 'var(--accent)' : 'var(--cyan)'}`,
          }}
        >
          <div style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.12em', color: 'var(--muted2)' }}>{layer.code}</div>
          <h3 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 20, margin: '8px 0 2px', letterSpacing: '-.01em' }}>{layer.name}</h3>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)', fontWeight: 700 }}>{layer.role}</div>
          <p style={{ color: 'var(--muted)', fontSize: 13.5, lineHeight: 1.72, marginTop: 10 }}>{layer.body}</p>
          {i < labels.layers.length - 1 && (
            <span aria-hidden="true" style={{ position: 'absolute', right: 14, top: 16, fontFamily: 'var(--mono)', color: 'var(--muted2)', fontSize: 18 }}>→</span>
          )}
        </li>
      ))}
    </ol>
  );
}

function SummaryLine({ snap, labels }: { snap: BaikalSnapshot; labels: BaikalDict }) {
  const c = snap.summary.counts;
  const text = labels.summaryLine
    .replace('{ok}', String(c.ok ?? 0))
    .replace('{degraded}', String(c.degraded ?? 0))
    .replace('{down}', String(c.down ?? 0))
    .replace('{undetermined}', String(c.undetermined ?? 0));
  return (
    <p style={{ fontFamily: 'var(--mono)', fontSize: 12.5, color: 'var(--txt)', fontWeight: 600 }}>
      {text}
      <span style={{ color: 'var(--muted2)', fontWeight: 400 }}> · {labels.observedAt} {fmtTime(snap.observed_at)}</span>
    </p>
  );
}

/** 7개 시스템 상태 카드. compact 면 근거만(홈), 아니면 판정 범위·요청 시 엔진까지(대표 시스템 페이지). */
export function SystemStatusGrid({
  data, systems, labels, compact = false,
}: {
  data: BaikalResult | null;
  systems: SystemDict[];
  labels: BaikalDict;
  compact?: boolean;
}) {
  if (!data) return <Unavailable text={labels.unavailable} />;
  if (!data.available) return <Unavailable text={labels.notYet} />;
  const meta = systemByCode(systems);
  const byKey: Record<string, BaikalSystem> = Object.fromEntries(data.systems.map((s) => [s.key, s]));
  return (
    <div>
      {data.stale && (
        <p
          role="status"
          style={{ border: '1px solid #b45309', background: 'rgba(180,83,9,.08)', color: 'var(--txt)', borderRadius: 10, padding: '12px 14px', fontSize: 13.5, marginBottom: 14 }}
        >
          {labels.staleNote.replace('{n}', String(data.snapshot_age_minutes ?? '?'))}
        </p>
      )}
      <SummaryLine snap={data} labels={labels} />
      <div
        style={{
          display: 'grid', gap: 12, marginTop: 14, opacity: data.stale ? 0.6 : 1,
          gridTemplateColumns: `repeat(auto-fit, minmax(min(${compact ? 220 : 300}px, 100%), 1fr))`,
        }}
      >
        {SYSTEM_ORDER.map((code) => {
          const s = byKey[code];
          const m = meta[code];
          if (!m) return null;
          return (
            <article
              key={code}
              style={{ border: '1px solid var(--line2)', borderLeft: `4px solid ${SYSTEM_TONE[code]}`, borderRadius: 12, padding: '14px 16px', background: 'var(--panel)' }}
            >
              <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
                <div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 12.5, fontWeight: 800, letterSpacing: '.04em' }}>{systemTitle(m)}</div>
                  <div style={{ fontSize: 12.5, color: 'var(--muted)', marginTop: 2 }}>{m.role}</div>
                </div>
                {s ? <StatusBadge status={s.status} label={labels.statusLabels[s.status] ?? s.status} />
                   : <StatusBadge status="undetermined" label={labels.statusLabels.undetermined} />}
              </header>
              {s && (
                <>
                  <p style={{ fontSize: 13, lineHeight: 1.65, marginTop: 10, color: 'var(--txt)' }}>
                    <span style={{ color: 'var(--muted2)' }}>{labels.reasonLabel} · </span>{s.reason}
                  </p>
                  {!compact && (
                    <>
                      {s.scope_ko && (
                        <p style={{ fontSize: 12, lineHeight: 1.6, marginTop: 8, color: 'var(--muted)' }}>
                          <span style={{ color: 'var(--muted2)' }}>{labels.scopeLabel} · </span>{s.scope_ko}
                        </p>
                      )}
                      {s.on_request && s.on_request.length > 0 && (
                        <p style={{ fontFamily: 'var(--mono)', fontSize: 11, marginTop: 8, color: 'var(--muted2)' }}>
                          {labels.onRequestLabel}: {s.on_request.join(' · ')}
                        </p>
                      )}
                    </>
                  )}
                  <p style={{ fontFamily: 'var(--mono)', fontSize: 10.5, marginTop: 8, color: 'var(--muted2)' }}>
                    {labels.evidenceLabels[s.evidence_class] ?? s.evidence_class}
                  </p>
                </>
              )}
            </article>
          );
        })}
      </div>
      {labels.reasonOriginalNote && (
        <p style={{ fontSize: 11.5, color: 'var(--muted2)', marginTop: 10 }}>{labels.reasonOriginalNote}</p>
      )}
    </div>
  );
}

/** 피드백 루프 — 정답 적재 → 예측 → 채점 */
export function LoopPanel({ data, labels }: { data: BaikalResult | null; labels: BaikalDict }) {
  if (!data) return <Unavailable text={labels.unavailable} />;
  if (!data.available) return <Unavailable text={labels.notYet} />;
  const loop = data.loop;
  const link = (key: string) => loop.links.find((l) => l.key === key) ?? { key };
  const gt = link('ground_truth');
  const pr = link('predictions');
  const sc = link('scoring');
  const show = (v: unknown) => (v === null || v === undefined ? '—' : String(v));
  const tiles: [string, [string, unknown][]][] = [
    [labels.loopLinks.ground_truth, [[labels.loopFields.live, gt.live], [labels.loopFields.other, gt.other]]],
    [labels.loopLinks.predictions, [[labels.loopFields.total, pr.total], [labels.loopFields.named, pr.named_disease]]],
    [labels.loopLinks.scoring, [[labels.loopFields.resolved, sc.resolved], [labels.loopFields.unresolved, sc.unresolved]]],
  ];
  const stateColor = loop.state === 'measuring' ? 'ok' : 'undetermined';
  return (
    <div>
      <p style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <StatusBadge status={stateColor} label={labels.loopStates[loop.state] ?? loop.state} />
        {loop.earliest_due && (
          <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--muted)' }}>
            {labels.loopFields.earliestDue} {loop.earliest_due}
          </span>
        )}
      </p>
      <div style={{ display: 'grid', gap: 12, marginTop: 14, gridTemplateColumns: 'repeat(auto-fit, minmax(min(200px, 100%), 1fr))' }}>
        {tiles.map(([title, fields], i) => (
          <div key={title} style={{ border: '1px solid var(--line2)', borderRadius: 12, padding: '14px 16px', background: 'var(--panel)' }}>
            <div style={{ fontWeight: 700, fontSize: 14 }}>{title}{i < tiles.length - 1 ? ' →' : ''}</div>
            <dl style={{ margin: '10px 0 0', display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px', fontSize: 13 }}>
              {fields.map(([k, v]) => (
                <div key={k} style={{ display: 'contents' }}>
                  <dt style={{ color: 'var(--muted)' }}>{k}</dt>
                  <dd style={{ margin: 0, fontFamily: 'var(--mono)', fontWeight: 700 }}>{show(v)}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
      <p style={{ fontSize: 12.5, color: 'var(--muted)', lineHeight: 1.7, marginTop: 12 }}>{labels.loopNote}</p>
      {data.weekly_loop && <WeeklyLoop loop={data.weekly_loop} labels={labels} />}
    </div>
  );
}

/** 주간 추세 예측 루프 — 90일 루프와 따로. 판정 min_scored 건 전에는 성적을 말하지 않는다. */
function WeeklyLoop({ loop, labels }: { loop: NonNullable<BaikalSnapshot['weekly_loop']>; labels: BaikalDict }) {
  const c = loop.card;
  const F = labels.weeklyFields;
  const fields: [string, string][] = c
    ? [[F.scored, String(c.scored)], [F.open, String(c.open)], [F.void, String(c.void)]]
    : [];
  if (c?.enough) {
    fields.push([F.brier, `${c.brier_model ?? '—'} (${F.coin} ${c.brier_coin})`]);
    fields.push([F.hits, `${c.hits_model ?? '—'}/${c.calls_model ?? '—'}`]);
  }
  return (
    <div style={{ marginTop: 22, border: '1px solid var(--line2)', borderRadius: 12, padding: '14px 16px', background: 'var(--panel)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <strong style={{ fontSize: 14 }}>{labels.weeklyTitle}</strong>
        <StatusBadge status={loop.state === 'measuring' ? 'ok' : 'undetermined'} label={labels.loopStates[loop.state] ?? loop.state} />
      </div>
      {fields.length > 0 && (
        <dl style={{ margin: '10px 0 0', display: 'flex', flexWrap: 'wrap', gap: '4px 18px', fontSize: 13 }}>
          {fields.map(([k, v]) => (
            <div key={k} style={{ display: 'flex', gap: 6 }}>
              <dt style={{ color: 'var(--muted)' }}>{k}</dt>
              <dd style={{ margin: 0, fontFamily: 'var(--mono)', fontWeight: 700 }}>{v}</dd>
            </div>
          ))}
        </dl>
      )}
      {c && !c.enough && (
        <p style={{ fontSize: 12.5, color: 'var(--muted)', marginTop: 8 }}>{labels.weeklyNotEnough.replace('{min}', String(c.min_scored))}</p>
      )}
      <p style={{ fontSize: 12.5, color: 'var(--muted)', lineHeight: 1.7, marginTop: 8 }}>{labels.weeklyNote}</p>
    </div>
  );
}

function transitionLabel(status: string | null, labels: BaikalDict): string {
  if (!status) return labels.observationStart;
  return (labels.statusLabels as Record<string, string>)[status]
    ?? (labels.loopStates as Record<string, string>)[status]
    ?? status;
}

/** 상태 변화 기록 — 바뀐 순간만 */
export function TransitionList({
  transitions, systems, labels,
}: {
  transitions: BaikalTransition[];
  systems: SystemDict[];
  labels: BaikalDict;
}) {
  if (!transitions.length) return <Unavailable text={labels.transitionsEmpty} />;
  const meta = systemByCode(systems);
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 560 }}>
        <tbody>
          {transitions.map((t) => (
            <tr key={t.id} style={{ borderTop: '1px solid var(--line)' }}>
              <td style={{ padding: '9px 10px 9px 0', fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--muted2)', whiteSpace: 'nowrap', verticalAlign: 'top' }}>{fmtTime(t.observed_at)}</td>
              <td style={{ padding: '9px 10px', fontFamily: 'var(--mono)', fontWeight: 700, whiteSpace: 'nowrap', verticalAlign: 'top' }}>
                {meta[t.subject] ? systemTitle(meta[t.subject]) : t.subject === 'LOOP' ? labels.loopSubject : t.subject === 'LOOP_WEEKLY' ? labels.weeklySubject : t.subject}
              </td>
              <td style={{ padding: '9px 10px', whiteSpace: 'nowrap', verticalAlign: 'top' }}>
                {transitionLabel(t.from_status, labels)} → <strong>{transitionLabel(t.to_status, labels)}</strong>
              </td>
              <td style={{ padding: '9px 0 9px 10px', color: 'var(--muted)', verticalAlign: 'top' }}>{t.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** YGGDRASIL 흐름 — 코드에 있는 흐름만 */
export function FlowList({ systems, labels }: { systems: SystemDict[]; labels: BaikalDict }) {
  const meta = systemByCode(systems);
  return (
    <div>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8 }}>
        {labels.flows.map((f) => (
          <li
            key={f.id}
            style={{
              display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 12, alignItems: 'baseline',
              border: `1px ${f.kind === 'feedback' ? 'dashed' : 'solid'} var(--line2)`, borderRadius: 10, padding: '10px 14px',
              background: 'var(--panel)',
            }}
          >
            <span style={{ fontSize: 13.5 }}>
              <strong style={{ fontFamily: 'var(--mono)', color: SYSTEM_TONE[f.from] }}>{meta[f.from] ? systemTitle(meta[f.from]) : f.from}</strong>
              <span style={{ color: 'var(--muted2)' }}> → </span>
              <strong style={{ fontFamily: 'var(--mono)', color: SYSTEM_TONE[f.to] }}>{meta[f.to] ? systemTitle(meta[f.to]) : f.to}</strong>
              <span style={{ color: 'var(--muted)' }}> · {f.label}</span>
            </span>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)', whiteSpace: 'nowrap' }}>{f.cadence}</span>
          </li>
        ))}
      </ul>
      <p style={{ fontSize: 12.5, color: 'var(--muted)', lineHeight: 1.7, marginTop: 12 }}>{labels.feedbackNote}</p>
      <p style={{ fontSize: 12.5, color: 'var(--muted)', lineHeight: 1.7, marginTop: 4 }}>{labels.isolatedNote}</p>
    </div>
  );
}

/** 7개 시스템 표 — 영문명·현지 표기·역할·이름의 유래·주요 엔진 */
export function SystemsTable({
  systems, engineGroups, labels,
}: {
  systems: SystemDict[];
  engineGroups: EngineGroupDict[];
  labels: BaikalDict;
}) {
  const enginesBy: Record<string, string[]> = Object.fromEntries(
    engineGroups.map((g) => [g.system, g.engines.map((e) => e.name)]),
  );
  return (
    <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(min(320px, 100%), 1fr))' }}>
      {SYSTEM_ORDER.map((code, i) => {
        const s = systems.find((x) => x.code === code);
        if (!s) return null;
        return (
          <article key={code} style={{ border: '1px solid var(--line2)', borderTop: `4px solid ${SYSTEM_TONE[code]}`, borderRadius: 12, padding: '16px 18px', background: 'var(--panel)' }}>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>SYSTEM {String(i + 1).padStart(2, '0')}</div>
            <h3 style={{ fontFamily: 'var(--disp)', fontWeight: 800, fontSize: 18, margin: '6px 0 2px' }}>{systemTitle(s)}</h3>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)', fontWeight: 700 }}>{labels.colRole} · {s.role}</div>
            <p style={{ fontSize: 12.5, color: 'var(--muted2)', marginTop: 8, fontStyle: 'italic' }}>{s.myth}</p>
            <p style={{ fontSize: 13.5, color: 'var(--txt)', lineHeight: 1.7, marginTop: 8 }}>{s.summary}</p>
            {enginesBy[code]?.length ? (
              <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.7, marginTop: 10 }}>
                <span style={{ color: 'var(--muted2)' }}>{labels.colEngines} · </span>{enginesBy[code].join(' · ')}
              </p>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
