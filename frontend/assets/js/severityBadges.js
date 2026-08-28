/**
 * BugSense AI — Severity Badges & Score Indicator
 */

export function renderSeverityBadge(severity) {
  const sev = severity || 'Info';
  return `<span class="badge-severity badge-${sev}">${sev}</span>`;
}

export function renderScorePill(score) {
  const num = Math.round(score || 0);
  let color = 'var(--severity-info)';
  if (num >= 85) color = 'var(--severity-critical)';
  else if (num >= 70) color = 'var(--severity-high)';
  else if (num >= 50) color = 'var(--severity-medium)';
  else if (num >= 30) color = 'var(--severity-low)';

  return `<span style="font-weight: 700; color: ${color}; font-size: 13px;">${num}/100</span>`;
}
