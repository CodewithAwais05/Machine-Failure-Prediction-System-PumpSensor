import { useState } from 'react';
import { useApi, fmtInt } from '../hooks';
import { CHART } from '../theme';
import { Caption, ChartFrame, Kpi, KpiGrid, Notice, Panel, Pills, Select, Skeleton, Slider } from '../components/ui';
import { BreakdownChart, Heatmap, StreamChart, TelemetryChart } from '../components/charts';

const GROUPS = ['machine_status', 'month', 'week', 'weekday', 'hour'];

export default function Dashboard({ meta, overview, dark, runId }) {
  const c = CHART[dark ? 'dark' : 'light'];
  const sensors = meta.sensors;
  const labelOf = (v) => sensors.find((s) => s.value === v)?.label || v;

  const [sensor, setSensor] = useState(overview.top_sensors[0]);
  const [view, setView] = useState('Latest samples');
  const [win, setWin] = useState(30);
  const [n, setN] = useState(3000);
  const [hours, setHours] = useState(48);
  const [event, setEvent] = useState(0);
  const [by, setBy] = useState('machine_status');
  const [start, setStart] = useState(0);
  const [nSig, setNSig] = useState(1000);

  const failureView = view === 'Around a failure';
  const hasEvents = overview.events.length > 0;
  const maxStart = Math.max(overview.clean_rows - 1000, 0);

  const tele = useApi('/api/telemetry', { sensor, view: failureView ? 'failure' : 'latest', window: win, n, hours, event }, { key: runId, debounce: 180 });
  const brk = useApi('/api/breakdown', { by }, { key: runId });
  const sig = useApi('/api/stream', { sensor, start: Math.min(start, maxStart), n: nSig }, { key: runId, debounce: 180 });
  const cor = useApi('/api/correlation', {}, { key: runId });

  return (
    <>
      <KpiGrid>
        <Kpi i={0} label="Records Loaded" value={fmtInt(overview.records)} sub={`${fmtInt(overview.raw_rows)} raw rows in`} />
        <Kpi i={1} label="Quarantined" value={fmtInt(overview.quarantined)} sub="failed schema validation" />
        <Kpi i={2} label="Failure-Window Rate" value={`${overview.failure_rate.toFixed(2)}%`} sub={`${fmtInt(overview.flagged)} records flagged`} />
        <Kpi i={3} label="Breakdown Events" value={overview.events.length} sub="machine_status = BROKEN" />
        <Kpi i={4} label="Active Sensors" value={overview.active_sensors} sub={`${overview.dead_sensors.join(', ')} dropped (empty)`} />
      </KpiGrid>

      <div className="grid-2">
        <Panel title="Live Sensor Telemetry Trend" loading={tele.loading}>
          <Select label="Sensor" value={sensor} onChange={setSensor} options={sensors} />
          <Pills id="tele" inline options={['Latest samples', 'Around a failure']} value={view} onChange={setView} />

          <div className="grid-2-inner">
            <Slider label="Rolling window (min)" min={1} max={240} value={win} onChange={setWin} />
            {!failureView && <Slider label="Samples" min={500} max={20000} step={500} value={n} onChange={setN} />}
            {failureView && hasEvents && <Slider label="Hours around failure" min={6} max={168} step={6} value={hours} onChange={setHours} />}
          </div>

          {failureView && hasEvents && (
            <Select
              label="Failure event"
              value={event}
              onChange={(v) => setEvent(Number(v))}
              options={overview.events.map((e) => ({ value: e.index, label: e.label }))}
            />
          )}
          {failureView && !hasEvents && <Notice>No BROKEN events in the data.</Notice>}

          {tele.error && <Notice kind="error">{tele.error}</Notice>}
          {!tele.data ? <Skeleton height={340} /> : (
            <ChartFrame name="telemetry" bg={c.bg}>
              <TelemetryChart d={tele.data} c={c} name={labelOf(sensor)} window={win} />
            </ChartFrame>
          )}
        </Panel>

        <Panel title="Breakdown Analysis" loading={brk.loading}>
          <Select label="Group failure-window records by" value={by} onChange={setBy} options={GROUPS.map((g) => ({ value: g, label: g }))} />
          {brk.error && <Notice kind="error">{brk.error}</Notice>}
          {!brk.data ? <Skeleton height={320} /> : (
            <ChartFrame name="breakdowns" bg={c.bg}>
              <BreakdownChart d={brk.data} c={c} />
            </ChartFrame>
          )}
        </Panel>
      </div>

      <div className="grid-2">
        <Panel title="Signal Conditioning: Raw Outliers vs Validated Stream" loading={sig.loading}>
          <Caption>Uses the sensor chosen in the telemetry panel.</Caption>
          {maxStart > 0 && <Slider label="Window start (row)" min={0} max={maxStart} step={1000} value={Math.min(start, maxStart)} onChange={setStart} />}
          <Slider label="Samples" min={200} max={3000} step={100} value={nSig} onChange={setNSig} />
          {sig.error && <Notice kind="error">{sig.error}</Notice>}
          {!sig.data ? <Skeleton height={300} /> : <StreamChart d={sig.data} c={c} />}
        </Panel>

        <Panel title="Correlation Matrix (Sensors Most Linked to Failure)" loading={cor.loading}>
          {cor.error && <Notice kind="error">{cor.error}</Notice>}
          {!cor.data ? <Skeleton height={420} /> : <Heatmap d={cor.data} c={c} />}
        </Panel>
      </div>
    </>
  );
}
