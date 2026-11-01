import { useMemo } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, LabelList, Line, LineChart,
  ReferenceArea, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { motion } from 'framer-motion';
import { coolwarm } from '../theme';
import { fmtNum, fmtTime } from '../hooks';
import { Notice } from './ui';

const axis = (c) => ({
  tick: { fill: c.muted, fontSize: 11 },
  axisLine: { stroke: c.spine },
  tickLine: false,
});

function Tip({ active, payload, label, labelFormatter }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="tip">
      <b>{labelFormatter ? labelFormatter(label) : label}</b>
      {payload.filter((p) => p.value !== null && p.value !== undefined).map((p) => (
        <div key={p.dataKey + p.name} style={{ color: p.color || p.stroke }}>
          {p.name}: {typeof p.value === 'number' ? fmtNum(p.value) : p.value}
        </div>
      ))}
    </div>
  );
}

const Legend = ({ items }) => (
  <div className="legend">
    {items.map((it) => (
      <span key={it.label}>
        <i className={`swatch${it.box ? ' box' : ''}`} style={{ background: it.color }} />
        {it.label}
      </span>
    ))}
  </div>
);

/* ============================================================
   Live sensor telemetry (line + rolling mean + failure shading)
   ============================================================ */

export function TelemetryChart({ d, c, name, window }) {
  const rows = useMemo(
    () => d.x.map((x, i) => ({ x, y: d.y[i], m: d.mean ? d.mean[i] : null })),
    [d]
  );

  if (!rows.length) return <Notice>No data for this selection.</Notice>;

  const legend = [{ label: name, color: c.series[0] }];
  if (d.mean) legend.push({ label: `${window}-sample mean`, color: c.after });
  if (d.warn.length) legend.push({ label: 'Failure window', color: c.warn, box: true });
  if (d.recover.length) legend.push({ label: 'Recovering', color: c.recover, box: true });
  if (d.broken.length) legend.push({ label: 'Breakdown', color: c.series[1] });

  return (
    <div>
      <div className="chart-title">{d.title}</div>
      <div style={{ height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke={c.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="x" type="number" domain={['dataMin', 'dataMax']} tickFormatter={fmtTime} {...axis(c)} minTickGap={48} />
            <YAxis tickFormatter={fmtNum} width={48} domain={['auto', 'auto']} {...axis(c)} />
            <Tooltip content={<Tip labelFormatter={fmtTime} />} />
            {d.warn.map(([s, e], i) => <ReferenceArea key={`w${i}`} x1={s} x2={e} fill={c.warn} fillOpacity={0.25} strokeOpacity={0} ifOverflow="hidden" />)}
            {d.recover.map(([s, e], i) => <ReferenceArea key={`r${i}`} x1={s} x2={e} fill={c.recover} fillOpacity={0.25} strokeOpacity={0} ifOverflow="hidden" />)}
            <Line dataKey="y" name={name} stroke={c.series[0]} strokeOpacity={0.55} strokeWidth={1} dot={false} isAnimationActive animationDuration={800} />
            {d.mean && <Line dataKey="m" name={`${window}-sample mean`} stroke={c.after} strokeWidth={1.8} dot={false} isAnimationActive animationDuration={800} />}
            {d.broken.filter((b) => b.y !== null).map((b, i) => (
              <ReferenceDot
                key={`b${i}`}
                x={b.x}
                y={b.y}
                ifOverflow="visible"
                shape={({ cx, cy }) => (
                  <path d={`M${cx - 5} ${cy - 5}L${cx + 5} ${cy + 5}M${cx + 5} ${cy - 5}L${cx - 5} ${cy + 5}`} stroke={c.series[1]} strokeWidth={2.4} strokeLinecap="round" />
                )}
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <Legend items={legend} />
    </div>
  );
}

/* ============================================================
   Breakdown bars
   ============================================================ */

export function BreakdownChart({ d, c }) {
  if (!d.items.length) return <Notice>No failure records.</Notice>;

  return (
    <div style={{ height: 320 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={d.items} margin={{ top: 22, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={c.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" interval={0} angle={-25} textAnchor="end" height={54} {...axis(c)} />
          <YAxis width={52} tickFormatter={(v) => v.toLocaleString('en-US')} {...axis(c)} />
          <Tooltip cursor={{ fill: c.grid, opacity: 0.5 }} content={<Tip />} />
          <Bar dataKey="value" name="Records in failure window" radius={[4, 4, 0, 0]} animationDuration={700}>
            {d.items.map((_, i) => <Cell key={i} fill={c.series[i % c.series.length]} />)}
            {d.items.length <= 16 && <LabelList dataKey="value" position="top" fill={c.fg} fontSize={11} formatter={(v) => v.toLocaleString('en-US')} />}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ============================================================
   Raw vs validated stream (two panels, same y-range)
   ============================================================ */

function MiniLine({ title, color, data, ylim, c }) {
  return (
    <div>
      <div className="chart-title" style={{ color, fontWeight: 600 }}>{title}</div>
      <div style={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid stroke={c.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="x" type="number" domain={['dataMin', 'dataMax']} tickFormatter={fmtTime} {...axis(c)} minTickGap={40} />
            <YAxis domain={ylim || ['auto', 'auto']} allowDataOverflow tickFormatter={fmtNum} width={48} {...axis(c)} />
            <Tooltip content={<Tip labelFormatter={fmtTime} />} />
            <Line dataKey="y" name="Reading" stroke={color} strokeWidth={1.1} dot={false} connectNulls={false} isAnimationActive animationDuration={700} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function StreamChart({ d, c }) {
  const before = useMemo(() => (d.empty ? [] : d.before.x.map((x, i) => ({ x, y: d.before.y[i] }))), [d]);
  const after = useMemo(() => (d.empty ? [] : d.after.x.map((x, i) => ({ x, y: d.after.y[i] }))), [d]);

  if (d.empty) return <Notice>No data for this selection.</Notice>;

  return (
    <div className="grid-2-inner">
      <MiniLine title="Before: raw readings (outliers and gaps)" color={c.before} data={before} ylim={d.ylim} c={c} />
      <MiniLine title="After: validated and cleaned readings" color={c.after} data={after} ylim={d.ylim} c={c} />
    </div>
  );
}

/* ============================================================
   Correlation heat-map (SVG)
   ============================================================ */

export function Heatmap({ d, c }) {
  const n = d.cols.length;
  const cell = Math.max(24, Math.min(44, 620 / n));
  const left = 118;
  const top = 8;
  const bottom = 112;
  const w = left + n * cell + 70;
  const h = top + n * cell + bottom;

  return (
    <div className="svg-wrap">
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" style={{ minWidth: 420, maxWidth: 780, display: 'block', margin: '0 auto' }} role="img" aria-label="Correlation matrix">
        <defs>
          <linearGradient id="cm" x1="0" y1="1" x2="0" y2="0">
            {[-1, -0.5, 0, 0.5, 1].map((v, i) => <stop key={v} offset={`${i * 25}%`} stopColor={coolwarm(v)} />)}
          </linearGradient>
        </defs>

        {d.matrix.map((row, i) => row.map((v, j) => (
          <g key={`${i}-${j}`} className="hm-cell" style={{ animationDelay: `${(i + j) * 14}ms`, transformBox: 'fill-box', transformOrigin: 'center' }}>
            <rect x={left + j * cell} y={top + i * cell} width={cell} height={cell} fill={v === null ? c.grid : coolwarm(v)}>
              <title>{`${d.cols[i]} × ${d.cols[j]}: ${v === null ? 'n/a' : v.toFixed(2)}`}</title>
            </rect>
            {n <= 18 && v !== null && (
              <text x={left + j * cell + cell / 2} y={top + i * cell + cell / 2 + 3} textAnchor="middle" fontSize={n > 10 ? 8 : 9} fill="#111" pointerEvents="none">
                {v.toFixed(2)}
              </text>
            )}
          </g>
        )))}

        {d.cols.map((name, i) => (
          <g key={name}>
            <text x={left - 6} y={top + i * cell + cell / 2 + 3} textAnchor="end" fontSize={9.5} fill={c.muted}>{name}</text>
            <text transform={`translate(${left + i * cell + cell / 2 + 3}, ${top + n * cell + 8}) rotate(60)`} fontSize={9.5} fill={c.muted}>{name}</text>
          </g>
        ))}

        <rect x={left + n * cell + 18} y={top} width={12} height={n * cell} fill="url(#cm)" />
        {[1, 0, -1].map((v) => (
          <text key={v} x={left + n * cell + 36} y={top + ((1 - v) / 2) * n * cell + 3} fontSize={9.5} fill={c.muted}>{v}</text>
        ))}
      </svg>
    </div>
  );
}

/* ============================================================
   Missing values before vs after (log-like scale)
   ============================================================ */

const symlog = (v) => Math.log10(1 + v / 0.1) / Math.log10(1 + 100 / 0.1);

export function MissingBars({ d, c }) {
  if (!d.items.length) return <Notice>No missing or blank values before or after cleaning.</Notice>;

  return (
    <div>
      <div className="mv">
        {d.items.map((it, i) => (
          <MissingRow key={it.name} it={it} c={c} i={i} />
        ))}
      </div>
      <Legend items={[{ label: 'Before', color: c.before }, { label: 'After', color: c.after }, { label: 'Scale: % of rows (symlog)', color: 'transparent' }]} />
    </div>
  );
}

function MissingRow({ it, c, i }) {
  const bar = (v, color, delay) => (
    <div className="mv-row">
      <motion.div
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${Math.max(symlog(v) * 100, 0.4) * 0.8}%` }}
        transition={{ duration: 0.8, delay, ease: [0.2, 0.7, 0.2, 1] }}
      />
      <span>{v.toFixed(2)}%</span>
    </div>
  );

  return (
    <>
      <div className="mv-name" title={it.name}>{it.name}</div>
      <div className="mv-bars">
        {bar(it.before, c.before, i * 0.03)}
        {bar(it.after, c.after, i * 0.03 + 0.08)}
      </div>
    </>
  );
}

/* ============================================================
   Histograms: raw vs cleaned
   ============================================================ */

function HistCell({ it, c, log }) {
  const rows = useMemo(
    () => it.mid.map((x, i) => ({
      x,
      b: log && it.before[i] === 0 ? null : it.before[i],
      a: log && it.after[i] === 0 ? null : it.after[i],
    })),
    [it, log]
  );

  return (
    <div className="chart-cell">
      <h4>{it.label}</h4>
      <div style={{ height: 190 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke={c.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="x" tickFormatter={fmtNum} interval="preserveStartEnd" minTickGap={28} {...axis(c)} />
            <YAxis
              width={42}
              scale={log ? 'log' : 'linear'}
              domain={log ? [1, 'auto'] : [0, 'auto']}
              allowDataOverflow
              tickFormatter={(v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : v)}
              {...axis(c)}
            />
            <Tooltip content={<Tip labelFormatter={(v) => `≈ ${fmtNum(v)}`} />} />
            <Bar dataKey="a" name="After" fill={c.after} fillOpacity={0.55} animationDuration={600} />
            <Line dataKey="b" name="Before" stroke={c.before} strokeWidth={1.6} dot={false} type="stepAfter" connectNulls isAnimationActive animationDuration={600} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function HistGrid({ items, c, log }) {
  return (
    <div>
      <Legend items={[{ label: 'Before', color: c.before }, { label: 'After', color: c.after }]} />
      <div className="chart-grid" style={{ marginTop: '0.8rem' }}>
        {items.map((it) => <HistCell key={it.col} it={it} c={c} log={log} />)}
      </div>
    </div>
  );
}

export function SingleHist({ d, c }) {
  const rows = useMemo(() => d.mid.map((x, i) => ({ x, b: d.before[i], a: d.after[i] })), [d]);

  const panel = (key, title, color) => (
    <div>
      <div className="chart-title" style={{ fontWeight: 600, color: c.fg }}>{d.col}: {title}</div>
      <div style={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 6, right: 10, left: 0, bottom: 0 }} barCategoryGap={1}>
            <CartesianGrid stroke={c.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="x" tickFormatter={fmtNum} interval="preserveStartEnd" minTickGap={30} {...axis(c)} />
            <YAxis width={48} tickFormatter={(v) => v.toLocaleString('en-US')} {...axis(c)} />
            <Tooltip content={<Tip labelFormatter={(v) => `≈ ${fmtNum(v)}`} />} />
            <Bar dataKey={key} name="Frequency" fill={color} animationDuration={700} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  return (
    <div className="grid-2-inner">
      {panel('b', 'BEFORE CLEANING', c.before)}
      {panel('a', 'AFTER CLEANING', c.after)}
    </div>
  );
}

/* ============================================================
   Box plots: raw vs cleaned (SVG)
   ============================================================ */

function BoxCell({ it, zoom, c }) {
  const W = 230;
  const H = 250;
  const pad = { l: 50, r: 10, t: 12, b: 28 };
  const [lo, hi] = zoom ? it.ylim : [Math.min(it.before.min, it.after.min), Math.max(it.before.max, it.after.max)];
  const span = hi - lo || 1;
  const y = (v) => pad.t + (H - pad.t - pad.b) * (1 - (v - lo) / span);
  const clipId = `clip-${it.col}-${zoom ? 'z' : 'f'}`;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => lo + span * t);
  const inner = W - pad.l - pad.r;

  const box = (b, cx, color) => {
    const bw = inner * 0.34;
    return (
      <g className="box-in">
        <line x1={cx} x2={cx} y1={y(b.wl)} y2={y(b.q1)} stroke={c.muted} />
        <line x1={cx} x2={cx} y1={y(b.q3)} y2={y(b.wh)} stroke={c.muted} />
        <line x1={cx - bw / 4} x2={cx + bw / 4} y1={y(b.wl)} y2={y(b.wl)} stroke={c.muted} />
        <line x1={cx - bw / 4} x2={cx + bw / 4} y1={y(b.wh)} y2={y(b.wh)} stroke={c.muted} />
        <rect x={cx - bw / 2} y={Math.min(y(b.q3), y(b.q1))} width={bw} height={Math.max(Math.abs(y(b.q1) - y(b.q3)), 1.5)} fill={color} stroke={c.fg} strokeWidth={0.8} />
        <line x1={cx - bw / 2} x2={cx + bw / 2} y1={y(b.med)} y2={y(b.med)} stroke={c.fg} strokeWidth={1.6} />
        {b.fliers.map((f, i) => <circle key={i} cx={cx} cy={y(f)} r={1.4} fill={c.muted} opacity={0.7} />)}
      </g>
    );
  };

  return (
    <div className="chart-cell">
      <h4>{it.label}</h4>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`Box plot of ${it.label}, before and after cleaning`}>
        <defs><clipPath id={clipId}><rect x={pad.l} y={pad.t} width={inner} height={H - pad.t - pad.b} /></clipPath></defs>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke={c.grid} strokeDasharray="3 3" />
            <text x={pad.l - 6} y={y(t) + 3} textAnchor="end" fontSize={9} fill={c.muted}>{fmtNum(t)}</text>
          </g>
        ))}
        <g clipPath={`url(#${clipId})`}>
          {box(it.before, pad.l + inner * 0.27, c.before)}
          {box(it.after, pad.l + inner * 0.73, c.after)}
        </g>
        <text x={pad.l + inner * 0.27} y={H - 9} textAnchor="middle" fontSize={10} fill={c.muted}>Before</text>
        <text x={pad.l + inner * 0.73} y={H - 9} textAnchor="middle" fontSize={10} fill={c.muted}>After</text>
      </svg>
    </div>
  );
}

export function BoxGrid({ items, zoom, c }) {
  return (
    <div className="chart-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))' }}>
      {items.map((it) => <BoxCell key={`${it.col}-${zoom}`} it={it} zoom={zoom} c={c} />)}
    </div>
  );
}
