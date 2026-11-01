import { useEffect, useState } from 'react';
import { get } from './api';

/**
 * Fetch JSON from the API. The previous result stays on screen while the next
 * one loads, so charts update smoothly instead of flashing blank.
 */
export function useApi(path, params, { enabled = true, key = 0, debounce = 0 } = {}) {
  const [state, setState] = useState({ data: null, loading: enabled, error: null });
  const signature = `${path}?${JSON.stringify(params || {})}#${key}`;

  useEffect(() => {
    if (!enabled || !path) return undefined;

    const controller = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));

    const timer = setTimeout(() => {
      get(path, params, controller.signal)
        .then((data) => setState({ data, loading: false, error: null }))
        .catch((err) => {
          if (err.name === 'AbortError') return;
          setState((s) => ({ ...s, loading: false, error: err.message }));
        });
    }, debounce);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, enabled]);

  return state;
}

export const fmtInt = (n) => Number(n).toLocaleString('en-US');

export function fmtNum(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return '';
  const a = Math.abs(v);
  if (a >= 10000) return Number(v).toExponential(1);
  if (a >= 100) return v.toFixed(0);
  if (a >= 1) return v.toFixed(1);
  return v.toFixed(2);
}

// Server timestamps are naive (no timezone), so they are formatted as UTC to show the same clock time.
export function fmtTime(ms) {
  return new Date(ms).toISOString().slice(5, 16).replace('T', ' ');
}
