// Chart palettes (same colours as the matplotlib theme in src/eda.py).
export const CHART = {
  light: {
    bg: '#FFFFFF', fg: '#1B1B22', muted: '#5E6370', grid: '#E6E8EC', spine: '#C9CDD4',
    before: '#A02C4D', after: '#2D3142',
    series: ['#C05A7C', '#6B1E33', '#2D3142', '#7F8489', '#D393B4'],
    warn: '#F3B74F', recover: '#9AA0A6',
  },
  dark: {
    bg: '#1F1B25', fg: '#ECE8F0', muted: '#A39DAE', grid: '#342E3C', spine: '#4A4354',
    before: '#E58BAA', after: '#8FA3D6',
    series: ['#E58BAA', '#B0476A', '#8FA3D6', '#9AA0A6', '#F0B6CC'],
    warn: '#C9962E', recover: '#6E7480',
  },
};

const COLD = [59, 76, 192];
const MID = [221, 221, 221];
const HOT = [180, 4, 38];

// Approximation of matplotlib's "coolwarm" colormap for values in [-1, 1].
export function coolwarm(v) {
  const t = Math.max(-1, Math.min(1, Number.isFinite(v) ? v : 0));
  const [a, b, k] = t < 0 ? [COLD, MID, t + 1] : [MID, HOT, t];
  const rgb = a.map((x, i) => Math.round(x + (b[i] - x) * k));
  return `rgb(${rgb.join(',')})`;
}
