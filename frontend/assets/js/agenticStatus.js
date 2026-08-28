/**
 * BugSense AI — Agentic Status Poller & Live State Machine Visualizer
 */
import { apiRequest } from './api.js';
import { escapeHtml, renderDiffHtml } from './utils.js';

export class AgenticStatusTracker {
  constructor(submissionId, containerElement, onComplete) {
    this.submissionId = submissionId;
    this.container = containerElement;
    this.onComplete = onComplete;
    this.pollInterval = null;
  }

  start() {
    this.poll();
    this.pollInterval = setInterval(() => this.poll(), 2000);
  }

  stop() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  async poll() {
    try {
      const data = await apiRequest(`/agentic/${this.submissionId}/status`);
      if (!data) return;

      this.render(data);

      if (!data.is_running && data.status !== 'in_progress') {
        this.stop();
        if (this.onComplete) {
          this.onComplete(data);
        }
      }
    } catch (err) {
      console.error('Agentic polling error:', err);
    }
  }

  render(data) {
    if (!this.container) return;

    const isRunning = data.is_running;
    const statusPill = isRunning
      ? '<span class="badge-severity badge-Medium"><span class="spinner" style="width: 12px; height: 12px;"></span> Running Agentic Loop</span>'
      : (data.status === 'verified'
        ? '<span class="badge-severity badge-Low" style="background: rgba(16, 185, 129, 0.15); color: #10b981; border-color: #10b981;">✓ All Fixes Verified</span>'
        : '<span class="badge-severity badge-Info">Completed</span>');

    let logsHtml = '';
    if (data.logs && data.logs.length > 0) {
      logsHtml = data.logs.map(log => {
        const actionUpper = log.action_taken.toUpperCase();
        let badgeColor = 'var(--accent-primary)';
        if (log.action_taken === 'verify') {
          badgeColor = log.verified ? 'var(--accent-emerald)' : 'var(--severity-high)';
        }

        return `
          <div class="timeline-step">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <strong style="color: ${badgeColor}; font-size: 13px;">[${actionUpper}] Attempt #${log.attempt_number}</strong>
              <span style="font-size: 11px; color: var(--text-muted);">${new Date(log.created_at).toLocaleTimeString()}</span>
            </div>
            <div style="font-size: 13px; color: var(--text-secondary);">${escapeHtml(log.outcome)}</div>
            ${log.diff_applied ? `<div class="diff-container" style="margin-top: 8px;">${renderDiffHtml(log.diff_applied)}</div>` : ''}
          </div>
        `;
      }).join('');
    } else {
      logsHtml = '<div style="color: var(--text-muted); font-size: 13px;">Initializing autonomous sandbox environment...</div>';
    }

    this.container.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h4 style="font-size: 16px;">🤖 Autonomous Agentic Debugger</h4>
        ${statusPill}
      </div>
      <div class="agentic-timeline">
        ${logsHtml}
      </div>
    `;
  }
}
