import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { post } from '../api';
import { useApi } from '../hooks';
import { Button, CountUp, Expander, Kpi, KpiGrid, Notice, Panel, Select, Skeleton, Caption } from '../components/ui';

function classify(p) {
  if (p < 0.15) return { css: 'ok', title: 'PUMP NORMAL / HEALTHY' };
  if (p < 0.3) return { css: 'warn', title: 'ELEVATED RISK - SCHEDULE INSPECTION' };
  return { css: 'bad', title: 'HIGH FAILURE RISK - ACT NOW' };
}

export default function RiskInference({ runId, result, setResult }) {
  const [poll, setPoll] = useState(0);
  const { data: bundle, error } = useApi('/api/risk/bundle', {}, { key: `${runId}-${poll}` });

  // The model trains in the background on the first visit: keep asking until it is ready.
  useEffect(() => {
    if (bundle && !bundle.ready) {
      const t = setTimeout(() => setPoll((p) => p + 1), 2000);
      return () => clearTimeout(t);
    }
    return undefined;
  }, [bundle]);

  const [preset, setPreset] = useState(null);
  const [inputs, setInputs] = useState({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState(null);

  const names = bundle?.ready ? Object.keys(bundle.presets) : [];
  const active = preset && names.includes(preset) ? preset : names[0];

  useEffect(() => {
    if (!bundle?.ready || !active) return;
    const base = bundle.presets[active];
    setInputs(Object.fromEntries(bundle.top_sensors.map((k) => [k, String(Math.round(base[k] * 1000) / 1000)])));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bundle?.ready, active]);

  if (error) return <Notice kind="error">{error}</Notice>;

  if (!bundle || !bundle.ready) {
    return (
      <Panel title="Real-Time Pump Failure Risk Inference (ML Engine)" loading>
        <Caption>Training baseline model (first visit only)...</Caption>
        <Skeleton height={220} />
      </Panel>
    );
  }

  const { ranges, metrics: m } = bundle;
  const label = (k) => k.replace('sensor_', 'Sensor ');

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setFailure(null);

    try {
      const readings = { ...bundle.presets[active] };
      Object.entries(inputs).forEach(([k, v]) => {
        const num = parseFloat(v);
        if (Number.isFinite(num)) readings[k] = num;
      });
      setResult(await post('/api/risk/predict', { readings }));
    } catch (err) {
      setFailure(err.message);
    } finally {
      setBusy(false);
    }
  };

  const horizon = bundle.target_mode === 'early_warning' ? `within the next ${bundle.horizon_hours} h` : 'now';
  const verdict = result ? classify(result.probability) : null;

  return (
    <>
      <Panel title="Real-Time Pump Failure Risk Inference (ML Engine)">
        <Select
          label="Start from a historical reading"
          value={active}
          onChange={setPreset}
          options={names.map((n) => ({ value: n, label: n }))}
        />

        <Caption>
          All {Object.keys(bundle.presets[active]).length} sensors start from the chosen reading. Adjust the {bundle.top_sensors.length} sensors
          most linked to failure below; the remaining sensors keep their reading.
        </Caption>

        <form onSubmit={submit} className="stack" style={{ display: 'grid', gap: '1rem' }}>
          <div className="grid-3">
            {bundle.top_sensors.map((k) => {
              const [lo, hi] = ranges[k];
              return (
                <div className="field" key={`${active}-${k}`}>
                  <label htmlFor={`in-${k}`}>{label(k)}</label>
                  <input
                    id={`in-${k}`}
                    className="input"
                    type="number"
                    inputMode="decimal"
                    step={(hi - lo) / 100 || 1}
                    value={inputs[k] ?? ''}
                    onChange={(e) => setInputs((s) => ({ ...s, [k]: e.target.value }))}
                  />
                  <span className="range-hint">Training range: {lo.toFixed(2)} to {hi.toFixed(2)}</span>
                </div>
              );
            })}
          </div>

          <button type="submit" className="btn block" disabled={busy}>
            {busy && <span className="spinner" aria-hidden="true" />}
            Run Pump Risk Diagnosis
          </button>
        </form>

        {failure && <Notice kind="error">{failure}</Notice>}

        {result && (
          <motion.div
            key={result.probability}
            className={`result ${verdict.css}`}
            initial={{ opacity: 0, scale: 0.97, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 24 }}
            role="status"
          >
            <div className="result-title">
              {verdict.title} (<CountUp value={`${Math.round(result.probability * 100)}%`} /> Failure Probability)
            </div>
            <div className="result-sub">
              Deviation from healthy: {result.deviation_mean_abs.toFixed(2)} σ (avg) | Sensors beyond 3σ: {result.n_sensors_beyond_3sd} | Sensors reading 0: {result.n_zero_sensors}
            </div>
            <div className="meter" aria-hidden="true">
              <motion.div initial={{ width: 0 }} animate={{ width: `${Math.max(result.probability * 100, 1)}%` }} transition={{ duration: 0.8, ease: [0.2, 0.7, 0.2, 1] }} />
            </div>
          </motion.div>
        )}

        {result && (
          <Caption>
            Probability that the pump is broken {horizon}. Average failure-window rate in the held-out test period: {(result.base_rate * 100).toFixed(1)}%.
          </Caption>
        )}
      </Panel>

      <Expander title="About this model">
        <p>
          HistGradientBoosting baseline. The pump has {m.failure_events} failure events, so the split is by event: trained on the first{' '}
          {m.train_rows.toLocaleString('en-US')} records, tested on the last {m.test_rows.toLocaleString('en-US')} (from {m.test_start}, {m.test_events} failure events).
        </p>
        <KpiGrid>
          <Kpi label="ROC-AUC" value={m.roc_auc.toFixed(2)} sub="0.50 = coin flip" />
          <Kpi label="PR-AUC" value={m.pr_auc.toFixed(2)} sub={`baseline ${m.base_rate.toFixed(2)}`} />
          <Kpi label="Features" value={bundle.n_features} sub="sensors + deviation features" />
        </KpiGrid>
        <p>
          This is a single-reading baseline - it does not see trends over time, and with only a few failure events the test score is a rough
          indication, not a guarantee. <code>machine_status</code> is excluded on purpose (it defines the target), and RECOVERING rows are left
          out of training. Rolling/lag features and cross-validation by event belong in Phase 2.
        </p>
      </Expander>
    </>
  );
}
