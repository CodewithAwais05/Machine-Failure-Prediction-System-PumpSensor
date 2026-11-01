import { Button, Slider, Toggle } from './ui';

export default function Sidebar({ meta, dark, setDark, inject, setInject, level, setLevel, onRerun, busy, open, onClose }) {
  return (
    <>
      {open && <div className="scrim" onClick={onClose} aria-hidden="true" />}

      <aside className={`sidebar${open ? ' open' : ''}`} aria-label="Settings">
        <h3>{meta?.title || 'Pump Failure Prediction Dashboard'}</h3>

        <Toggle label="Dark mode" checked={dark} onChange={setDark} />

        <hr />

        <div>
          <div className="side-label">Data source</div>
          <p className="caption">
            Backend file: <code>{meta?.raw_file || 'data/raw/sensor.csv'}</code> (pump sensor data, loaded automatically)
          </p>
          {meta && (
            <p className="caption" style={{ marginTop: '0.4rem' }}>
              {meta.target_mode === 'early_warning'
                ? `Target: BROKEN within the next ${meta.horizon_hours} h`
                : 'Target: machine is BROKEN or RECOVERING'}
            </p>
          )}
        </div>

        <hr />

        <div className="side-label">Cleaning demo</div>

        <Toggle
          label="Simulate dirty data"
          checked={inject}
          onChange={setInject}
          help="The real file already has gaps (e.g. sensor_50 is ~35% empty) but few glitches. This corrupts a COPY (dropouts, spikes, -999 sentinels, messy status text, duplicates) so the before/after graphs show more cleaning work. Turn it off to see the real data only."
        />

        <Slider label="Noise intensity" min={0.5} max={3} step={0.5} value={level} onChange={setLevel} disabled={!inject} />

        <Button onClick={onRerun} busy={busy}>Re-run pipeline</Button>
      </aside>
    </>
  );
}
