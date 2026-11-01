import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

/* ---------- animated number (counts up when the value changes) ---------- */

export function CountUp({ value }) {
  const [shown, setShown] = useState(value);

  useEffect(() => {
    const m = typeof value === 'string' ? value.match(/^(\D*?)(-?[\d,]*\.?\d+)([\s\S]*)$/) : null;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!m || reduce) {
      setShown(value);
      return undefined;
    }

    const target = parseFloat(m[2].replace(/,/g, ''));
    const decimals = (m[2].split('.')[1] || '').length;
    const grouped = m[2].includes(',');
    let raf;
    let t0;

    const step = (ts) => {
      if (t0 === undefined) t0 = ts;
      const p = Math.min(1, (ts - t0) / 900);
      const v = target * (1 - Math.pow(1 - p, 3));
      const text = grouped
        ? v.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
        : v.toFixed(decimals);
      setShown(m[1] + text + m[3]);
      if (p < 1) raf = requestAnimationFrame(step);
    };

    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  return <>{shown}</>;
}

/* ---------- cards ---------- */

export function Kpi({ label, value, sub, i = 0 }) {
  return (
    <motion.div
      className="kpi"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: i * 0.06, ease: [0.2, 0.7, 0.2, 1] }}
    >
      <div className="kpi-label">{label}</div>
      <div className="kpi-value"><CountUp value={String(value)} /></div>
      <div className="kpi-sub">{sub || '\u00A0'}</div>
    </motion.div>
  );
}

export function KpiGrid({ children }) {
  return <div className="kpi-grid">{children}</div>;
}

export function Panel({ title, loading, children }) {
  return (
    <section className="panel">
      {loading && <div className="loading-bar" aria-hidden="true" />}
      {title && <div className="panel-title">{title}</div>}
      <div className="stack">{children}</div>
    </section>
  );
}

export function Notice({ kind = 'info', children }) {
  return <div className={`notice ${kind}`} role={kind === 'error' ? 'alert' : 'status'}>{children}</div>;
}

export const Caption = ({ children }) => <p className="caption">{children}</p>;

export function Skeleton({ height = 280 }) {
  return <div className="skeleton" style={{ height }} aria-hidden="true" />;
}

export function Spinner({ dark, large }) {
  return <span className={`spinner${dark ? ' dark' : ''}${large ? ' lg' : ''}`} aria-hidden="true" />;
}

/* ---------- inputs ---------- */

export function Pills({ options, value, onChange, id, inline }) {
  return (
    <div className={`pills${inline ? ' inline' : ''}`} role="radiogroup">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          role="radio"
          aria-checked={value === o}
          className="pill"
          onClick={() => onChange(o)}
        >
          {value === o && (
            <motion.span
              layoutId={`pill-${id}`}
              className="pill-bg"
              transition={{ type: 'spring', stiffness: 420, damping: 34 }}
            />
          )}
          <span className="pill-text">{o}</span>
        </button>
      ))}
    </div>
  );
}

export function Select({ label, value, onChange, options, help }) {
  const uid = useRef(`sel-${Math.random().toString(36).slice(2, 8)}`).current;

  return (
    <div className="field">
      <label htmlFor={uid}>
        {label}
        {help && <span className="help" title={help}>?</span>}
      </label>
      <select id={uid} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

export function Slider({ label, min, max, step = 1, value, onChange, disabled }) {
  const pct = max > min ? ((value - min) / (max - min)) * 100 : 0;

  return (
    <div className="field">
      <div className="slider-head">
        <span>{label}</span>
        <output>{value}</output>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        aria-label={label}
        style={{ '--pct': `${pct}%` }}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

export function Toggle({ label, checked, onChange, help }) {
  return (
    <div className="field">
      <button type="button" role="switch" aria-checked={checked} className="toggle" onClick={() => onChange(!checked)}>
        <span className="track"><span className="knob" /></span>
        <span>{label}</span>
        {help && <span className="help" title={help}>?</span>}
      </button>
    </div>
  );
}

export function MultiSelect({ label, options, value, onChange }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const ref = useRef(null);

  useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const labelOf = (v) => options.find((o) => o.value === v)?.label || v;

  const toggle = (v) =>
    onChange(options.map((o) => o.value).filter((x) => (x === v ? !value.includes(v) : value.includes(x))));

  const visible = options.filter((o) => o.label.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="field ms" ref={ref}>
      <span className="field-label">{label}</span>
      <div className="ms-box" onClick={() => setOpen(true)} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && setOpen((o) => !o)}>
        {value.length === 0 && <span className="caption">Choose sensors</span>}
        {value.map((v) => (
          <span className="chip" key={v}>
            {labelOf(v)}
            <button type="button" aria-label={`Remove ${labelOf(v)}`} onClick={(e) => { e.stopPropagation(); toggle(v); }}>×</button>
          </span>
        ))}
      </div>
      <AnimatePresence>
        {open && (
          <motion.div
            className="ms-pop"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
          >
            <input className="input" placeholder="Search sensors" value={query} onChange={(e) => setQuery(e.target.value)} autoFocus />
            <div className="ms-list">
              {visible.map((o) => (
                <label className="ms-item" key={o.value}>
                  <input type="checkbox" checked={value.includes(o.value)} onChange={() => toggle(o.value)} />
                  {o.label}
                </label>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function Button({ children, busy, ...rest }) {
  return (
    <button type="button" className="btn" {...rest} disabled={busy || rest.disabled}>
      {busy && <Spinner />}
      {children}
    </button>
  );
}

/* ---------- expander ---------- */

export function Expander({ title, children }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="expander">
      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <span>{title}</span>
        <svg className={`chev${open ? ' open' : ''}`} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6" /></svg>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.2, 0.7, 0.2, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div className="expander-body">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ---------- data table ---------- */

const cell = (v) => {
  if (v === null || v === undefined) return '';
  if (typeof v === 'number') return Number.isInteger(v) ? v.toLocaleString('en-US') : String(v);
  return String(v);
};

export function DataTable({ columns, rows }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((v, j) => <td key={j} className={typeof v === 'number' ? 'num' : undefined}>{cell(v)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------- PNG export of a chart (like Streamlit's "Download PNG") ---------- */

export function ChartFrame({ name, bg, children }) {
  const ref = useRef(null);

  const save = () => {
    const svg = ref.current?.querySelector('svg.recharts-surface') || ref.current?.querySelector('svg');
    if (!svg) return;

    const { width, height } = svg.getBoundingClientRect();
    const clone = svg.cloneNode(true);
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.setAttribute('width', width);
    clone.setAttribute('height', height);

    const img = new Image();

    img.onload = () => {
      const scale = 2;
      const canvas = document.createElement('canvas');
      canvas.width = width * scale;
      canvas.height = height * scale;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0, width, height);

      canvas.toBlob((blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${name}.png`;
        a.click();
        setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      });
    };

    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(new XMLSerializer().serializeToString(clone));
  };

  return (
    <div>
      <div ref={ref}>{children}</div>
      <div className="png-row">
        <button type="button" className="btn ghost small" onClick={save}>Download PNG</button>
      </div>
    </div>
  );
}
