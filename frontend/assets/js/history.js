/**
 * BugSense AI — Submissions History View Module
 */
import { apiRequest } from './api.js';
import { requireAuth } from './auth.js';
import { escapeHtml, formatDate } from './utils.js';

export async function initHistoryPage() {
  requireAuth();

  const tableBody = document.getElementById('history-table-body');
  const loadingIndicator = document.getElementById('history-loading');

  try {
    const submissions = await apiRequest('/upload/history');
    if (loadingIndicator) loadingIndicator.style.display = 'none';

    if (!submissions || submissions.length === 0) {
      if (tableBody) {
        tableBody.innerHTML = `
          <tr>
            <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 30px;">
              No prior analysis history found. <a href="upload.html">Upload Python code to get started</a>.
            </td>
          </tr>
        `;
      }
      return;
    }

    const getLangBadge = (lang) => {
      const l = lang || 'Python';
      const icons = { 'Python': '🐍', 'Java': '☕', 'C': '🇨', 'C++': '➕', 'JavaScript': '🟨', 'TypeScript': '🔷', 'Go': '🐹', 'Rust': '🦀', 'C#': '🔷', 'PHP': '🐘' };
      const icon = icons[l] || '🌐';
      return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: var(--bg-tertiary); font-size: 12px; font-weight: 500; color: var(--text-primary); border: 1px solid var(--border-subtle);">${icon} ${escapeHtml(l)}</span>`;
    };

    if (tableBody) {
      tableBody.innerHTML = submissions.map(sub => `
        <tr>
          <td><strong style="color: #ffffff;">${escapeHtml(sub.filename)}</strong></td>
          <td>${getLangBadge(sub.language)}</td>
          <td>${sub.lines_of_code || '—'} lines</td>
          <td><span style="color: var(--text-secondary); font-size: 13px;">${formatDate(sub.uploaded_at)}</span></td>
          <td>
            <a href="report.html?id=${sub.id}" class="btn btn-primary btn-sm">
              📊 View Audit Report
            </a>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    if (loadingIndicator) {
      loadingIndicator.innerHTML = '<span style="color: var(--severity-critical);">Failed to load history.</span>';
    }
  }
}
