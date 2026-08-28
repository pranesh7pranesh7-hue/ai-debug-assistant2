/**
 * BugSense AI — Bug Report View, Detail Drawer & Interactive AI Chat
 */
import { apiRequest } from './api.js';
import { requireAuth } from './auth.js';
import { AgenticStatusTracker } from './agenticStatus.js';
import { renderScorePill, renderSeverityBadge } from './severityBadges.js';
import { escapeHtml, renderDiffHtml, showToast } from './utils.js';

export async function initReportPage() {
  requireAuth();

  const urlParams = new URLSearchParams(window.location.search);
  const submissionId = urlParams.get('id');

  if (!submissionId) {
    showToast('No submission ID provided in URL.', 'error');
    setTimeout(() => { window.location.href = 'index.html'; }, 1000);
    return;
  }

  const bugListContainer = document.getElementById('bug-list-container');
  const drawerContainer = document.getElementById('drawer-container');
  const agenticContainer = document.getElementById('agentic-tracker-container');
  const pdfDownloadBtn = document.getElementById('download-pdf-btn');
  const startAgenticBtn = document.getElementById('start-agentic-btn');

  let currentBugs = [];
  let selectedBug = null;
  let chatHistory = [];

  // Setup PDF download link
  if (pdfDownloadBtn) {
    pdfDownloadBtn.addEventListener('click', () => {
      window.open(`/api/reports/${submissionId}/pdf`, '_blank');
    });
  }

  // Load Bug Data
  async function loadBugs() {
    try {
      const data = await apiRequest(`/bugs/${submissionId}`);
      if (!data) return;

      currentBugs = data.bugs;
      document.getElementById('report-filename').textContent = data.filename;
      document.getElementById('stat-total-bugs').textContent = data.total_bugs;
      document.getElementById('stat-critical').textContent = data.critical_count;
      document.getElementById('stat-high').textContent = data.high_count;

      renderBugList(currentBugs);

      if (currentBugs.length > 0) {
        selectBug(currentBugs[0]);
      } else {
        drawerContainer.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 40px;">🎉 Clean code! Zero static defects or bug patterns found.</div>';
      }
    } catch (err) {
      console.error('Failed to load bugs:', err);
    }
  }

  function renderBugList(bugs) {
    if (!bugListContainer) return;
    if (bugs.length === 0) {
      bugListContainer.innerHTML = '<div style="color: var(--text-muted); padding: 20px;">No bugs matching filter.</div>';
      return;
    }

    bugListContainer.innerHTML = bugs.map(bug => `
      <div class="bug-item ${selectedBug?.id === bug.id ? 'active' : ''}" data-bug-id="${bug.id}">
        <div class="bug-header">
          <div>
            ${renderSeverityBadge(bug.severity)}
            <span class="bug-loc" style="margin-left: 8px;">Line ${bug.line}:${bug.column}</span>
          </div>
          ${renderScorePill(bug.severity_score)}
        </div>
        <div class="bug-title">${escapeHtml(bug.message)}</div>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">
          Tool: <strong>${bug.tool}</strong> &bull; Rule: <code>${bug.rule_id}</code> &bull; ${bug.category}
        </div>
      </div>
    `).join('');

    // Attach click handlers
    bugListContainer.querySelectorAll('.bug-item').forEach(el => {
      el.addEventListener('click', () => {
        const id = parseInt(el.dataset.bugId, 10);
        const target = currentBugs.find(b => b.id === id);
        if (target) selectBug(target);
      });
    });
  }

  function selectBug(bug) {
    selectedBug = bug;
    renderBugList(currentBugs); // update active class
    renderDetailDrawer(bug);
  }

  function renderDetailDrawer(bug) {
    if (!drawerContainer) return;

    drawerContainer.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <div>
          ${renderSeverityBadge(bug.severity)}
          <span style="font-weight: 700; margin-left: 8px; font-size: 16px;">Line ${bug.line}</span>
        </div>
        <div>${renderScorePill(bug.severity_score)}</div>
      </div>

      <h3 style="font-size: 16px; margin-bottom: 8px;">${escapeHtml(bug.message)}</h3>
      <div style="font-size: 12px; color: var(--text-muted);">
        Rule: <code>${bug.rule_id}</code> | Category: <strong>${bug.category}</strong> | Analyzer: <strong>${bug.tool}</strong>
      </div>

      <!-- AI Root Cause Explanation Box -->
      <div class="explanation-box">
        <strong style="color: #ffffff; display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
          🧠 AI Root-Cause Diagnostic
        </strong>
        <div style="white-space: pre-wrap; font-family: inherit;">${escapeHtml(bug.explanation || 'Generating AI explanation...')}</div>
      </div>

      <!-- Action Buttons -->
      <div style="display: flex; gap: 10px; margin: 16px 0;">
        <button id="generate-fix-btn" class="btn btn-primary btn-sm">
          ⚡ Synthesize AI Fix
        </button>
      </div>

      <!-- Candidate Fix & Diff Viewer -->
      <div id="fix-preview-area" style="display: none;">
        <h4 style="font-size: 14px; margin-top: 16px;">Proposed Patch & Unified Diff</h4>
        <div id="diff-output" class="diff-container"></div>
        <div id="fix-rationale" style="font-size: 12px; color: var(--text-secondary); margin-top: 6px;"></div>
      </div>

      <!-- AI Pair Debugger Chat Panel -->
      <h4 style="font-size: 14px; margin-top: 24px; border-top: 1px solid var(--border-subtle); padding-top: 16px;">
        💬 Ask AI Pair Debugger
      </h4>
      <div class="chat-container">
        <div id="chat-messages" class="chat-messages">
          <div class="chat-bubble chat-bubble-ai">
            Hello! I am your AI debugging assistant. Ask me anything about this line, potential edge cases, or how to refactor.
          </div>
        </div>
        <div class="chat-input-bar">
          <input type="text" id="chat-input" placeholder="e.g. Why does this fail on empty input?" />
          <button id="chat-send-btn" class="btn btn-primary btn-sm">Send</button>
        </div>
      </div>
    `;

    // Fix Generation Button Listener
    const fixBtn = document.getElementById('generate-fix-btn');
    if (fixBtn) {
      fixBtn.addEventListener('click', async () => {
        fixBtn.disabled = true;
        fixBtn.innerHTML = '<span class="spinner"></span> Synthesizing Patch...';
        try {
          const fixData = await apiRequest(`/fixes/${bug.id}/generate`, { method: 'POST' });
          if (fixData) {
            document.getElementById('fix-preview-area').style.display = 'block';
            document.getElementById('diff-output').innerHTML = renderDiffHtml(fixData.diff_text);
            document.getElementById('fix-rationale').textContent = `Rationale: ${fixData.rationale}`;
            showToast('AI Patch generated cleanly!', 'success');
          }
        } catch (err) {
          showToast('Failed to synthesize patch.', 'error');
        } finally {
          fixBtn.disabled = false;
          fixBtn.innerHTML = '⚡ Synthesize AI Fix';
        }
      });
    }

    // Chat listeners
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chatBox = document.getElementById('chat-messages');

    async function sendChatMessage() {
      const msg = chatInput.value.trim();
      if (!msg) return;

      chatInput.value = '';
      chatBox.innerHTML += `<div class="chat-bubble chat-bubble-user">${escapeHtml(msg)}</div>`;
      chatBox.scrollTop = chatBox.scrollHeight;

      chatHistory.push({ role: 'user', content: msg });

      const typingIndicator = document.createElement('div');
      typingIndicator.className = 'chat-bubble chat-bubble-ai';
      typingIndicator.innerHTML = '<span class="spinner" style="width: 12px; height: 12px;"></span> AI is thinking...';
      chatBox.appendChild(typingIndicator);
      chatBox.scrollTop = chatBox.scrollHeight;

      try {
        const replyData = await apiRequest('/reports/chat', {
          method: 'POST',
          body: JSON.stringify({
            submission_id: parseInt(submissionId, 10),
            bug_id: bug.id,
            message: msg,
            chat_history: chatHistory,
          }),
        });

        typingIndicator.remove();
        if (replyData && replyData.reply) {
          chatBox.innerHTML += `<div class="chat-bubble chat-bubble-ai">${escapeHtml(replyData.reply)}</div>`;
          chatHistory.push({ role: 'assistant', content: replyData.reply });
        }
      } catch (e) {
        typingIndicator.innerHTML = 'Failed to fetch AI reply.';
      }
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    if (chatSendBtn) chatSendBtn.addEventListener('click', sendChatMessage);
    if (chatInput) {
      chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
      });
    }
  }

  // Agentic Loop Launch Button
  if (startAgenticBtn) {
    startAgenticBtn.addEventListener('click', async () => {
      startAgenticBtn.disabled = true;
      startAgenticBtn.innerHTML = '<span class="spinner"></span> Launching Agentic Loop...';
      try {
        const tracker = new AgenticStatusTracker(submissionId, agenticContainer, (finalStatus) => {
          showToast('Agentic Debugging Loop Finished!', 'success');
          loadBugs(); // reload updated statuses
        });
        tracker.start();

        await apiRequest(`/agentic/${submissionId}/start`, { method: 'POST' });
      } catch (err) {
        showToast('Error starting agentic loop.', 'error');
      } finally {
        startAgenticBtn.disabled = false;
        startAgenticBtn.innerHTML = '🤖 Run Autonomous Agentic Debugger';
      }
    });
  }

  // Initial load
  await loadBugs();
}
