import { useCallback, useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { get, post } from './api';
import { fmtInt } from './hooks';
import Sidebar from './components/Sidebar';
import Loader from './components/Loader';
import { Notice, Pills, Button } from './components/ui';
import Dashboard from './pages/Dashboard';
import BeforeAfter from './pages/BeforeAfter';
import RiskInference from './pages/RiskInference';
import DataReport from './pages/DataReport';

const PAGES = ['Dashboard', 'Before vs After', 'Risk Inference', 'Data & Report'];

export default function App() {
  const [dark, setDark] = useState(() => document.documentElement.dataset.theme === 'dark');
  const [inject, setInject] = useState(true);
  const [level, setLevel] = useState(1);
  const [page, setPage] = useState(() => {
    const saved = localStorage.getItem('sg-page');
    return PAGES.includes(saved) ? saved : PAGES[0];
  });
  const [status, setStatus] = useState(null);
  const [connected, setConnected] = useState(false);
  const [pollKey, setPollKey] = useState(0);
  const [meta, setMeta] = useState(null);
  const [overview, setOverview] = useState(null);
  const [risk, setRisk] = useState(null);
  const [menu, setMenu] = useState(false);
  const synced = useRef(false);

  /* ---------- theme ---------- */
  useEffect(() => {
    const mode = dark ? 'dark' : 'light';
    document.documentElement.dataset.theme = mode;
    try { localStorage.setItem('sg-theme', mode); } catch { /* private mode */ }
  }, [dark]);

  useEffect(() => {
    try { localStorage.setItem('sg-page', page); } catch { /* private mode */ }
  }, [page]);

  /* ---------- poll the pipeline status until it is ready ---------- */
  useEffect(() => {
    let stop = false;
    let timer;

    const tick = async () => {
      try {
        const s = await get('/api/status');
        if (stop) return;
        setStatus(s);
        setConnected(true);

        if (!synced.current) {
          synced.current = true;
          setInject(s.params.inject);
          setLevel(s.params.level);
        }

        if (s.state === 'running' || s.state === 'idle') timer = setTimeout(tick, 1500);
      } catch {
        if (stop) return;
        setConnected(false);
        timer = setTimeout(tick, 3000);
      }
    };

    tick();
    return () => { stop = true; clearTimeout(timer); };
  }, [pollKey]);

  useEffect(() => {
    if (connected && !meta) get('/api/meta').then(setMeta).catch(() => {});
  }, [connected, meta]);

  const ready = status?.state === 'ready';
  const runId = status?.run_id ?? 0;

  useEffect(() => {
    if (!ready) return;
    get('/api/overview').then(setOverview).catch(() => {});
    setRisk(null);
  }, [ready, runId]);

  /* ---------- (re)run the pipeline ---------- */
  const run = useCallback(async () => {
    try {
      const s = await post('/api/pipeline/run', { inject, level });
      setStatus(s);
      setPollKey((k) => k + 1);
    } catch { /* the poller will show the connection state */ }
  }, [inject, level]);

  // Like Streamlit: changing the cleaning-demo settings re-runs the pipeline automatically.
  useEffect(() => {
    if (!status || status.state === 'idle') return undefined;
    const p = status.params;
    if (p.inject === inject && Math.abs(p.level - level) < 1e-9) return undefined;

    const t = setTimeout(run, 700);
    return () => clearTimeout(t);
  }, [inject, level, status?.params?.inject, status?.params?.level, status?.state, run]);

  const busy = status?.state === 'running';
  const showPage = ready && overview && meta;
  const failed = status?.state === 'error';

  return (
    <div className="shell">
      <Sidebar
        meta={meta}
        dark={dark}
        setDark={setDark}
        inject={inject}
        setInject={setInject}
        level={level}
        setLevel={setLevel}
        onRerun={run}
        busy={busy}
        open={menu}
        onClose={() => setMenu(false)}
      />

      <div className="main">
        <button type="button" className="menu-btn" onClick={() => setMenu(true)} aria-label="Open settings">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>

        <motion.div className="sg-header" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: [0.2, 0.7, 0.2, 1] }}>
          <div>
            {meta?.title || 'Pump Failure Prediction Dashboard'}
            {showPage && inject && <span className="sg-chip">noise demo ON</span>}
          </div>
          {showPage && <span className="sg-sub">{fmtInt(overview.records)} cleaned records</span>}
        </motion.div>

        {failed && (
          <div className="stack" style={{ display: 'grid', gap: '1rem' }}>
            <Notice kind="error">Pipeline failed: {status.error}</Notice>
            <div><Button onClick={run}>Try again</Button></div>
          </div>
        )}

        {!failed && !showPage && <Loader connecting={!connected} elapsedHint={status?.elapsed} />}

        {showPage && (
          <>
            <Pills id="page" options={PAGES} value={page} onChange={setPage} />

            <motion.div
              key={page}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28, ease: [0.2, 0.7, 0.2, 1] }}
            >
              {page === 'Dashboard' && <Dashboard meta={meta} overview={overview} dark={dark} runId={runId} />}
              {page === 'Before vs After' && <BeforeAfter meta={meta} overview={overview} dark={dark} runId={runId} />}
              {page === 'Risk Inference' && <RiskInference dark={dark} runId={runId} result={risk} setResult={setRisk} />}
              {page === 'Data & Report' && <DataReport runId={runId} />}
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}
