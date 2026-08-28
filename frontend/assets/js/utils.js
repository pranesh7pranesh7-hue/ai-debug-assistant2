/**
 * BugSense AI — Utilities & Toast Notification Manager
 */

export function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type === 'error' ? 'toast-error' : (type === 'success' ? 'toast-success' : '')}`;
  toast.innerHTML = `<span>${escapeHtml(message)}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

export function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export function formatDate(isoString) {
  if (!isoString) return 'N/A';
  let str = String(isoString).trim();
  if (!str.endsWith('Z') && !/[+-]\d{2}(:\d{2})?$/.test(str)) {
    str = str.replace(' ', 'T') + 'Z';
  }
  const d = new Date(str);
  if (isNaN(d.getTime())) return isoString;
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatDateTime(isoString) {
  if (!isoString) return 'N/A';
  let str = String(isoString).trim();
  // Ensure naive ISO timestamp from backend is treated as UTC
  if (!str.endsWith('Z') && !/[+-]\d{2}(:\d{2})?$/.test(str)) {
    str = str.replace(' ', 'T') + 'Z';
  }
  const d = new Date(str);
  if (isNaN(d.getTime())) return isoString;
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

export function renderDiffHtml(diffText) {
  if (!diffText) return '<div style="color: var(--text-muted);">No diff generated yet.</div>';
  const lines = diffText.split('\n');
  return lines.map(line => {
    const escaped = escapeHtml(line);
    if (line.startsWith('+') && !line.startsWith('+++')) {
      return `<span class="diff-add">${escaped}</span>`;
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      return `<span class="diff-del">${escaped}</span>`;
    }
    return `<span>${escaped}</span>`;
  }).join('\n');
}

/**
 * Normalizes Python code by stripping surrounding markdown fences
 * and cleaning line-number prefixes if copied from code viewers.
 */
export function normalizePythonCode(rawCode) {
  if (!rawCode) return '';
  let code = rawCode.trim();

  // 1. Strip surrounding markdown code fences
  if (code.startsWith('```')) {
    const lines = code.split(/\r?\n/);
    if (lines.length >= 2 && lines[0].startsWith('```') && lines[lines.length - 1].trim().startsWith('```')) {
      code = lines.slice(1, -1).join('\n').trim();
    } else if (lines.length >= 1 && lines[0].startsWith('```')) {
      code = lines.slice(1).join('\n').trim();
    }
  }

  // 2. Check if all non-empty lines have line number prefixes
  const lines = code.split(/\r?\n/);
  const nonEmpty = lines.filter(l => l.trim().length > 0);
  if (nonEmpty.length > 0) {
    // Format A: Colon, Pipe, or Tab
    const patternSep = /^\s*\d+[:\|\t]\s?(.*)$/;
    if (nonEmpty.every(l => patternSep.test(l))) {
      return lines.map(l => {
        if (!l.trim()) return '';
        const m = l.match(patternSep);
        return m ? m[1] : l;
      }).join('\n');
    }

    // Format B: Space separated: e.g. "44  def foo():"
    const patternSpace = /^(\s*\d+)(\s+)(.*)$/;
    if (nonEmpty.every(l => patternSpace.test(l))) {
      const matchDetails = nonEmpty.map(l => l.match(patternSpace));
      const minSepLen = Math.min(...matchDetails.map(m => m[2].length));
      return lines.map(l => {
        if (!l.trim()) return '';
        const m = l.match(patternSpace);
        if (m) {
          const spaces = m[2];
          const rest = m[3];
          const keptIndent = spaces.slice(minSepLen);
          return keptIndent + rest;
        }
        return l;
      }).join('\n');
    }
  }

  return code;
}

export function getLineSnippet(code, lineNum) {
  if (!code) return '';
  const lines = code.split(/\r?\n/);
  if (lineNum >= 1 && lineNum <= lines.length) {
    return lines[lineNum - 1].trim();
  }
  return '';
}

export function generateSyntaxExplanations(msg, snippet) {
  let rootCause = "The Python interpreter encountered a syntax error while parsing this snippet.";
  let fixGuidance = "Inspect the highlighted line and check for matching colons, quotes, indentation, and brackets.";

  const msgLower = (msg || '').toLowerCase();
  if (msgLower.includes("expected ':'") || msgLower.includes("colon")) {
    rootCause = "In Python, compound statements such as 'if', 'for', 'while', 'def', 'class', and 'with' require a colon (':') at the end of their header line.";
    fixGuidance = "Add a colon (':') at the end of the condition or statement header.";
  } else if (msgLower.includes("unexpected indent") || msgLower.includes("indentation")) {
    rootCause = "Python relies on consistent indentation (spaces) to delineate code blocks. An unexpected space or tab was encountered.";
    fixGuidance = "Ensure all statements within the same block share uniform 4-space indentation.";
  } else if (msgLower.includes("unmatched") || msgLower.includes("was never closed") || msgLower.includes("closing parenthesis")) {
    rootCause = "An opening parenthesis '(', bracket '[', or brace '{' was not properly closed.";
    fixGuidance = "Add the missing closing bracket/parenthesis to balance the expression.";
  }

  return { rootCause, fixGuidance };
}

