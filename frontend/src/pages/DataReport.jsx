import { useState } from 'react';
import { apiUrl, post } from '../api';
import { useApi } from '../hooks';
import { Button, Caption, DataTable, Expander, Notice, Panel, Skeleton } from '../components/ui';

export default function DataReport({ runId }) {
  const report = useApi('/api/report', {}, { key: runId });
  const preview = useApi('/api/data/preview', { rows: 500 }, { key: runId });
  const rejected = useApi('/api/rejected', {}, { key: runId });

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(null);

  const save = async () => {
    setSaving(true);
    setSaved(null);
    try {
      setSaved({ kind: 'ok', text: (await post('/api/data/save')).message });
    } catch (e) {
      setSaved({ kind: 'error', text: e.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Panel title="Cleaning Report" loading={report.loading}>
        {report.error && <Notice kind="error">{report.error}</Notice>}
        {!report.data ? <Skeleton height={260} /> : (
          <>
            <DataTable columns={['metric', 'value']} rows={report.data.summary.map((r) => [r.metric, r.value])} />
            <Expander title="Full report (JSON)">
              <pre className="json">{JSON.stringify(report.data.full, null, 2)}</pre>
            </Expander>
            <div className="btn-row" style={{ marginTop: 0 }}>
              <a className="btn" href={apiUrl('/api/report/download')} download="cleaning_report.json">Download report (JSON)</a>
            </div>
          </>
        )}
      </Panel>

      <Panel title="Cleaned + Engineered Data" loading={preview.loading}>
        {preview.error && <Notice kind="error">{preview.error}</Notice>}
        {!preview.data ? <Skeleton height={320} /> : (
          <>
            <Caption>
              {preview.data.shape[0].toLocaleString('en-US')} rows x {preview.data.shape[1]} columns (first 500 shown)
            </Caption>
            <DataTable columns={preview.data.columns} rows={preview.data.rows} />
            <div className="btn-row" style={{ marginTop: 0 }}>
              <a className="btn" href={apiUrl('/api/data/sample.csv')} download="clean_features_sample.csv">Download 1,000-row sample (CSV)</a>
              <Button onClick={save} busy={saving}>Save full dataset to data/ (CSV + SQLite)</Button>
            </div>
            {saved && <Notice kind={saved.kind}>{saved.text}</Notice>}
          </>
        )}
      </Panel>

      <Panel title="Quarantined Rows (failed Pydantic validation)" loading={rejected.loading}>
        {rejected.error && <Notice kind="error">{rejected.error}</Notice>}
        {!rejected.data ? <Skeleton height={80} /> : rejected.data.rows.length === 0 ? (
          <Notice kind="ok">No rows were quarantined - every cleaned row passed schema validation.</Notice>
        ) : (
          <>
            <Caption>{rejected.data.total.toLocaleString('en-US')} rows quarantined (first {rejected.data.rows.length} shown)</Caption>
            <DataTable columns={['row_index', 'reason']} rows={rejected.data.rows.map((r) => [r.row_index, r.reason])} />
          </>
        )}
      </Panel>
    </>
  );
}
