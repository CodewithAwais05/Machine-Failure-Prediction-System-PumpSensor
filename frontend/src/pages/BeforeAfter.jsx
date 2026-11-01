import { useState } from 'react';
import { useApi, fmtInt } from '../hooks';
import { CHART } from '../theme';
import { Caption, ChartFrame, DataTable, Kpi, KpiGrid, MultiSelect, Notice, Panel, Pills, Select, Skeleton, Slider, Toggle } from '../components/ui';
import { BoxGrid, HistGrid, MissingBars, SingleHist, StreamChart } from '../components/charts';

const VIEWS = ['Missing values', 'Distributions', 'Boxplots', 'Single feature', 'Sensor stream', 'Summary table'];

export default function BeforeAfter({ meta, overview, dark, runId }) {
  const c = CHART[dark ? 'dark' : 'light'];
  const ba = overview.ba;
  const sensors = meta.sensors;

  const [view, setView] = useState('Missing values');
  const [cols, setCols] = useState(meta.default_plot_sensors);
  const [log, setLog] = useState(true);
  const [zoom, setZoom] = useState(true);
  const [single, setSingle] = useState(sensors[0].value);
  const [streamSensor, setStreamSensor] = useState(sensors[0].value);
  const [start, setStart] = useState(0);
  const [n, setN] = useState(1000);

  const maxStart = Math.max(overview.clean_rows - 200, 0);
  const need = (v) => view === v;
  const colsReady = cols.length > 0;

  const missing = useApi('/api/ba/missing', {}, { enabled: need('Missing values'), key: runId });
  const dist = useApi('/api/ba/distributions', { cols }, { enabled: need('Distributions') && colsReady, key: runId, debounce: 200 });
  const box = useApi('/api/ba/boxplots', { cols }, { enabled: need('Boxplots') && colsReady, key: runId, debounce: 200 });
  const one = useApi('/api/ba/single', { col: single }, { enabled: need('Single feature'), key: runId });
  const stream = useApi('/api/stream', { sensor: streamSensor, start: Math.min(start, maxStart), n }, { enabled: need('Sensor stream'), key: runId, debounce: 180 });
  const table = useApi('/api/ba/table', {}, { enabled: need('Summary table'), key: runId });

  const current = { 'Missing values': missing, Distributions: dist, Boxplots: box, 'Single feature': one, 'Sensor stream': stream, 'Summary table': table }[view];

  return (
    <>
      <KpiGrid>
        <Kpi i={0} label="Rows In" value={fmtInt(ba.rows_in)} sub="raw" />
        <Kpi i={1} label="Rows Out" value={fmtInt(ba.rows_out)} sub={`${fmtInt(ba.removed)} removed`} />
        <Kpi i={2} label="Duplicates" value={fmtInt(ba.duplicates)} sub="removed" />
        <Kpi i={3} label="Invalid / Outliers" value={fmtInt(ba.impossible + ba.outliers)} sub={`${fmtInt(ba.impossible)} sentinels + ${fmtInt(ba.outliers)} spikes`} />
        <Kpi i={4} label="Missing Imputed" value={fmtInt(ba.missing_before)} sub="-> 0 after cleaning" />
      </KpiGrid>

      <Pills id="ba" inline options={VIEWS} value={view} onChange={setView} />

      <Panel title={`Before vs After - ${view}`} loading={current?.loading}>
        {(view === 'Distributions' || view === 'Boxplots') && (
          <MultiSelect label="Sensors" options={sensors} value={cols} onChange={setCols} />
        )}
        {view === 'Distributions' && <Toggle label="Log-scale counts (makes rare spikes visible)" checked={log} onChange={setLog} />}
        {view === 'Boxplots' && <Toggle label="Zoom to valid range (hides -999 sentinels)" checked={zoom} onChange={setZoom} />}
        {view === 'Single feature' && <Select label="Sensor" value={single} onChange={setSingle} options={sensors} />}
        {view === 'Sensor stream' && (
          <>
            <Select label="Sensor" value={streamSensor} onChange={setStreamSensor} options={sensors} />
            <div className="grid-2-inner">
              {maxStart > 0 && <Slider label="Window start (row)" min={0} max={maxStart} step={500} value={Math.min(start, maxStart)} onChange={setStart} />}
              <Slider label="Samples" min={200} max={3000} step={100} value={n} onChange={setN} />
            </div>
          </>
        )}

        {current?.error && <Notice kind="error">{current.error}</Notice>}
        {(view === 'Distributions' || view === 'Boxplots') && !colsReady && <Notice>Select at least one sensor.</Notice>}

        {view === 'Missing values' && (missing.data ? (
          <>
            <ChartFrame name="ba_missing" bg={c.bg}><MissingBars d={missing.data} c={c} /></ChartFrame>
            <Caption>sensor_15 is 100% empty in the source and is dropped. {missing.data.note}</Caption>
          </>
        ) : <Skeleton height={360} />)}

        {view === 'Distributions' && colsReady && (dist.data ? <HistGrid items={dist.data.items} c={c} log={log} /> : <Skeleton height={360} />)}
        {view === 'Boxplots' && colsReady && (box.data ? <BoxGrid items={box.data.items} zoom={zoom} c={c} /> : <Skeleton height={360} />)}

        {view === 'Single feature' && (one.data ? (
          <ChartFrame name={`ba_${single}`} bg={c.bg}><SingleHist d={one.data} c={c} /></ChartFrame>
        ) : <Skeleton height={320} />)}

        {view === 'Sensor stream' && (stream.data ? <StreamChart d={stream.data} c={c} /> : <Skeleton height={320} />)}

        {view === 'Summary table' && (table.data ? <DataTable columns={table.data.columns} rows={table.data.rows} /> : <Skeleton height={320} />)}
      </Panel>
    </>
  );
}
