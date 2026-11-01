import { useEffect, useState } from 'react';
import { Spinner } from './ui';

const STEPS = ['Extract', 'Clean', 'Validate', 'Engineer features'];

export default function Loader({ connecting, elapsedHint }) {
  const [t, setT] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setT((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);

  // The backend does not report which step it is on, so the highlight advances on a timer.
  const active = Math.min(STEPS.length - 1, Math.floor(t / 12));

  return (
    <div className="loader" role="status" aria-live="polite">
      <Spinner dark large />

      {connecting ? (
        <>
          <h2>Connecting to the backend</h2>
          <p className="caption" style={{ maxWidth: 440 }}>
            Free hosting puts the server to sleep when it is idle. Waking it up can take up to a minute.
          </p>
        </>
      ) : (
        <>
          <h2>Running the ETL pipeline</h2>
          <p className="caption" style={{ maxWidth: 440 }}>
            Extracting, cleaning, validating and engineering features. The first run takes about a minute.
            {elapsedHint ? ` (${Math.round(elapsedHint)} s so far)` : ''}
          </p>
          <div className="loader-bar" />
          <div className="steps">
            {STEPS.map((s, i) => (
              <span key={s} className={`step${i < active ? ' done' : ''}${i === active ? ' active' : ''}`}>{s}</span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
