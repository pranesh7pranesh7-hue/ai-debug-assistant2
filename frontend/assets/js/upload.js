import { apiRequest } from './api.js';
import { requireAuth } from './auth.js';
import { renderScorePill, renderSeverityBadge } from './severityBadges.js';
import { escapeHtml, showToast } from './utils.js';

export function initUploadPage() {
  requireAuth();

  const langSelect = document.getElementById('lang-select');
  const codeArea = document.getElementById('code-input');
  const filenameInput = document.getElementById('filename-input');
  const filePicker = document.getElementById('file-picker');
  const dropZone = document.getElementById('drop-zone');
  const submitBtn = document.getElementById('submit-upload-btn');
  const presetSelect = document.getElementById('preset-select');

  const zipPreviewBar = document.getElementById('zip-preview-bar');
  const zipArchiveTitle = document.getElementById('zip-archive-title');
  const zipFileSelect = document.getElementById('zip-file-select');

  const resultsSection = document.getElementById('analysis-results-section');
  const resultsContent = document.getElementById('analysis-results-content');
  const resultsCountBadge = document.getElementById('results-count-badge');
  const resultsActionButtons = document.getElementById('results-action-buttons');

  let extractedZipFiles = [];

  // Multi-Language Presets
  const PRESETS = {
    mutable_default: {
      lang: "Python",
      filename: "cache_store.py",
      code: `def register_user(username, roles=[]):\n    roles.append("user")\n    return {"user": username, "roles": roles}\n\n# Calling repeatedly retains past roles!\nprint(register_user("Alice"))\nprint(register_user("Bob"))`
    },
    undefined_var: {
      lang: "Python",
      filename: "service.py",
      code: `name = "John"\nage = 20\n\nprint("Name:", name)\nprint("Age:", age)\n\n# Undefined variable 'salary' referenced\nprint("Salary:", salary)`
    },
    resource_leak: {
      lang: "Python",
      filename: "log_processor.py",
      code: `def process_records(filepath):\n    # Resource leak: unclosed file descriptor\n    f = open(filepath, "r")\n    data = f.read()\n    return len(data)`
    },
    sql_injection: {
      lang: "Python",
      filename: "auth_repository.py",
      code: `import sqlite3\n\ndef authenticate_account(db, user_input):\n    cursor = db.cursor()\n    # SQL Injection via f-string interpolation\n    query = f"SELECT * FROM accounts WHERE username = '{user_input}'"\n    cursor.execute(query)\n    return cursor.fetchall()`
    },
    off_by_one: {
      lang: "Python",
      filename: "indexer.py",
      code: `def extract_elements(data_array):\n    collected = []\n    # Off-by-one: range(len + 1) throws IndexError\n    for idx in range(len(data_array) + 1):\n        collected.append(data_array[idx])\n    return collected`
    },
    c_buffer_overflow: {
      lang: "C",
      filename: "network_receiver.c",
      code: `#include <stdio.h>\n#include <string.h>\n\nvoid process_packet(char *user_input) {\n    char buffer[32];\n    // Dangerous gets() without bounds checking\n    gets(buffer);\n    // Format string vulnerability\n    printf(user_input);\n}\n\nint main() {\n    process_packet("test");\n    return 0;\n}`
    },
    cpp_memory_leak: {
      lang: "C++",
      filename: "session_manager.cpp",
      code: `#include <iostream>\n\nclass SessionHandler {\npublic:\n    void create_session() {\n        // Memory leak: allocated on heap without matching delete\n        int* raw_handle = new int[100];\n        raw_handle[0] = 42;\n        // Missing delete[] raw_handle\n    }\n};\n\nint main() {\n    SessionHandler s;\n    s.create_session();\n    return 0;\n}`
    },
    java_resource_leak: {
      lang: "Java",
      filename: "FileStreamReader.java",
      code: `import java.io.*;\n\npublic class FileStreamReader {\n    public void readFile(String path) throws IOException {\n        // Resource leak: unclosed FileInputStream\n        FileInputStream fis = new FileInputStream(path);\n        int content = fis.read();\n        System.out.println("Read: " + content);\n    }\n}`
    },
    java_string_equality: {
      lang: "Java",
      filename: "AuthValidator.java",
      code: `public class AuthValidator {\n    public boolean checkRole(String userRole) {\n        // Dangerous: String reference equality == instead of .equals()\n        if (userRole == "ADMIN") {\n            return true;\n        }\n        return false;\n    }\n}`
    },
    js_eval_injection: {
      lang: "JavaScript",
      filename: "dynamic_parser.js",
      code: `function executeUserScript(userInput) {\n    // Dangerous: arbitrary code execution via eval\n    const result = eval(userInput);\n    console.log("Result:", result);\n    return result;\n}`
    }
  };

  function loadExtractedFile(item) {
    if (!item) return;
    codeArea.value = item.raw_code || '';
    filenameInput.value = item.filename || 'script.py';
    if (langSelect && item.language) {
      langSelect.value = item.language;
    }
    if (resultsSection) {
      resultsSection.style.display = 'none';
    }
  }

  if (zipFileSelect) {
    zipFileSelect.addEventListener('change', (e) => {
      const idx = parseInt(e.target.value, 10);
      if (!isNaN(idx) && extractedZipFiles[idx]) {
        loadExtractedFile(extractedZipFiles[idx]);
      }
    });
  }

  if (presetSelect) {
    presetSelect.addEventListener('change', (e) => {
      const chosen = PRESETS[e.target.value];
      if (chosen) {
        if (zipPreviewBar) zipPreviewBar.style.display = 'none';
        extractedZipFiles = [];
        if (langSelect && chosen.lang) langSelect.value = chosen.lang;
        filenameInput.value = chosen.filename;
        codeArea.value = chosen.code;
        // Reset results display when loading new preset
        if (resultsSection) {
          resultsSection.style.display = 'none';
        }
      }
    });
  }

  if (langSelect) {
    langSelect.addEventListener('change', (e) => {
      const lang = e.target.value;
      const extMap = {
        'Python': '.py', 'C': '.c', 'C++': '.cpp', 'Java': '.java',
        'JavaScript': '.js', 'TypeScript': '.ts', 'Go': '.go',
        'Rust': '.rs', 'C#': '.cs', 'PHP': '.php', 'Ruby': '.rb',
        'SQL': '.sql', 'Shell': '.sh'
      };
      if (extMap[lang]) {
        const cur = filenameInput.value.trim() || 'service.py';
        const nameOnly = cur.replace(/\.[^/.]+$/, "");
        filenameInput.value = (nameOnly || 'service') + extMap[lang];
      }
    });
  }

  // File Picker change
  if (filePicker) {
    filePicker.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        handleFileSelect(file);
      }
    });
  }

  // Drag and Drop
  if (dropZone) {
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.style.borderColor = 'var(--accent-primary)';
    });
    dropZone.addEventListener('dragleave', () => {
      dropZone.style.borderColor = 'var(--border-subtle)';
    });
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.style.borderColor = 'var(--border-subtle)';
      if (e.dataTransfer.files.length > 0) {
        handleFileSelect(e.dataTransfer.files[0]);
      }
    });
  }

  async function handleFileSelect(file) {
    if (file.name.toLowerCase().endsWith('.zip')) {
      // Immediate server-side extraction of ZIP archive
      filenameInput.value = file.name;
      showToast(`Extracting ${file.name}...`, 'info');

      try {
        const formData = new FormData();
        formData.append('file', file);
        if (langSelect && langSelect.value && langSelect.value !== 'auto') {
          formData.append('language', langSelect.value);
        }
        const uploadRes = await apiRequest('/upload/file', {
          method: 'POST',
          body: formData,
          suppressToast: false,
        });

        if (uploadRes && uploadRes.length > 0) {
          extractedZipFiles = uploadRes;
          if (uploadRes.length > 1) {
            if (zipPreviewBar) {
              zipPreviewBar.style.display = 'block';
              if (zipArchiveTitle) {
                zipArchiveTitle.textContent = `📦 Extracted ${uploadRes.length} files from ${file.name}`;
              }
              if (zipFileSelect) {
                zipFileSelect.innerHTML = uploadRes.map((f, idx) => `
                  <option value="${idx}">${escapeHtml(f.filename)} (${f.language || 'Code'})</option>
                `).join('');
                zipFileSelect.value = '0';
              }
            }
          } else {
            if (zipPreviewBar) zipPreviewBar.style.display = 'none';
          }
          loadExtractedFile(uploadRes[0]);
          showToast(`Successfully extracted ${uploadRes.length} file(s) from ${file.name}`, 'success');
        } else {
          renderValidationError('The uploaded ZIP archive contains no supported code files.');
        }
      } catch (err) {
        console.error('ZIP extraction error:', err);
        renderValidationError(`Failed to extract ZIP archive: ${err.message || 'Unknown error'}`);
      }
      return;
    }

    // Single source file
    if (zipPreviewBar) zipPreviewBar.style.display = 'none';
    extractedZipFiles = [];
    filenameInput.value = file.name;

    const extToLang = {
      '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
      '.jsx': 'JavaScript', '.tsx': 'TypeScript', '.c': 'C',
      '.cpp': 'C++', '.h': 'C', '.hpp': 'C++', '.java': 'Java',
      '.go': 'Go', '.rb': 'Ruby', '.php': 'PHP', '.cs': 'C#',
      '.rs': 'Rust', '.sql': 'SQL', '.sh': 'Shell'
    };

    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (extToLang[ext] && langSelect) {
      langSelect.value = extToLang[ext];
    }

    const reader = new FileReader();
    reader.onload = (evt) => {
      codeArea.value = evt.target.result;
    };
    reader.readAsText(file);
  }

  // Submit button
  if (submitBtn) {
    submitBtn.addEventListener('click', async () => {
      const rawCode = codeArea.value.trim();
      const filename = filenameInput.value.trim() || 'script.py';
      const selectedLang = langSelect ? langSelect.value : 'auto';

      if (!rawCode) {
        renderValidationError("Please paste source code or select a file to analyze.");
        return;
      }

      // Display loading state in Analysis Results section
      showLoadingState();

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner"></span> Ingesting Code & Running Analysis...';

      try {
        const payload = {
          filename,
          code: rawCode,
          language: (selectedLang && selectedLang !== 'auto') ? selectedLang : null,
        };

        const uploadRes = await apiRequest('/upload', {
          method: 'POST',
          body: JSON.stringify(payload),
          suppressToast: true,
        });

        if (uploadRes && uploadRes.id) {
          const submissionId = uploadRes.id;

          // Trigger Analysis pipeline
          await apiRequest(`/analysis/${submissionId}/run`, {
            method: 'POST',
            suppressToast: true,
          });

          // Fetch full analyzed bugs
          const bugReportData = await apiRequest(`/bugs/${submissionId}`, {
            suppressToast: true,
          });

          if (bugReportData) {
            renderAnalysisSuccess(bugReportData, rawCode);
          }
        }
      } catch (err) {
        handleAnalysisError(err, rawCode);
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Analyze Code with BugSense AI';
      }
    });
  }

  // --- Rendering Helpers for Analysis Results Section ---

  function showLoadingState() {
    if (!resultsSection || !resultsContent) return;
    resultsSection.style.display = 'block';
    if (resultsCountBadge) resultsCountBadge.style.display = 'none';
    if (resultsActionButtons) resultsActionButtons.innerHTML = '';

    resultsContent.innerHTML = `
      <div class="analysis-loading-box">
        <span class="spinner" style="width: 32px; height: 32px; border-width: 3px;"></span>
        <div style="margin-top: 16px; font-size: 15px; font-weight: 600; color: #ffffff;">
          Analyzing your code with AST parser, static linters, & AI...
        </div>
        <div style="margin-top: 6px; font-size: 13px; color: var(--text-muted);">
          Checking syntax, resource leaks, security rules, and code complexity.
        </div>
      </div>
    `;

    // Smooth scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function renderValidationError(message) {
    if (!resultsSection || !resultsContent) return;
    resultsSection.style.display = 'block';
    if (resultsCountBadge) {
      resultsCountBadge.style.display = 'inline-flex';
      resultsCountBadge.className = 'badge-severity badge-Critical';
      resultsCountBadge.textContent = 'Validation Error';
    }
    if (resultsActionButtons) resultsActionButtons.innerHTML = '';

    resultsContent.innerHTML = `
      <div class="analysis-card analysis-card-Critical">
        <div class="analysis-card-top">
          <div class="analysis-card-meta">
            ${renderSeverityBadge('High')}
            <span style="font-weight: 700; color: var(--severity-critical); font-size: 15px;">Input Validation Error</span>
          </div>
        </div>
        <div class="analysis-field">
          <div class="analysis-field-label">Message</div>
          <div class="analysis-field-content">${escapeHtml(message)}</div>
        </div>
        <div class="analysis-field">
          <div class="analysis-field-label">Recommended Fix</div>
          <div class="analysis-fix-box">Provide valid source code in the editor above or select a preset, then click Analyze.</div>
        </div>
      </div>
    `;
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function handleAnalysisError(err, rawCode) {
    if (!resultsSection || !resultsContent) return;
    resultsSection.style.display = 'block';

    const errData = err.errorData || {};
    const errCode = errData.code || 'ANALYSIS_ERROR';
    const errMsg = errData.message || err.message || 'An unexpected error occurred during code analysis.';
    const details = errData.details || {};

    if (resultsActionButtons) resultsActionButtons.innerHTML = '';

    if (errCode === 'CODE_SYNTAX_ERROR') {
      const lineNum = details.line || 1;
      const colNum = details.column || 0;
      const codeSnippet = details.text || getLineSnippet(rawCode, lineNum);

      if (resultsCountBadge) {
        resultsCountBadge.style.display = 'inline-flex';
        resultsCountBadge.className = 'badge-severity badge-Critical';
        resultsCountBadge.textContent = '1 Syntax Error';
      }

      // Generate context-aware root cause and fix for syntax errors
      const { rootCause, fixGuidance } = generateSyntaxExplanations(errMsg, codeSnippet);

      resultsContent.innerHTML = `
        <div class="analysis-card analysis-card-Critical">
          <div class="analysis-card-top">
            <div class="analysis-card-meta">
              ${renderSeverityBadge('High')}
              <span class="analysis-meta-tag">Line ${lineNum}${colNum ? `:${colNum}` : ''}</span>
              <span class="analysis-meta-tag">Rule: SyntaxError</span>
              <span class="analysis-meta-tag">Category: syntax</span>
            </div>
            <span style="font-weight: 700; color: var(--severity-critical); font-size: 13px;">Critical Syntax Flaw</span>
          </div>

          <div class="analysis-field">
            <div class="analysis-field-label">Message</div>
            <div class="analysis-field-content">
              <strong>${escapeHtml(errMsg)}</strong>
            </div>
            ${codeSnippet ? `<pre class="analysis-code-snippet"><code>Line ${lineNum}: ${escapeHtml(codeSnippet)}</code></pre>` : ''}
          </div>

          <div class="analysis-field">
            <div class="analysis-field-label">Root Cause</div>
            <div class="analysis-explanation-box">
              ${escapeHtml(rootCause)}
            </div>
          </div>

          <div class="analysis-field">
            <div class="analysis-field-label">Recommended Fix</div>
            <div class="analysis-fix-box">
              ${escapeHtml(fixGuidance)}
            </div>
          </div>
        </div>
      `;
    } else {
      // General Server or Connection Error
      if (resultsCountBadge) {
        resultsCountBadge.style.display = 'inline-flex';
        resultsCountBadge.className = 'badge-severity badge-Critical';
        resultsCountBadge.textContent = 'Analysis Failed';
      }

      resultsContent.innerHTML = `
        <div class="analysis-card analysis-card-Critical">
          <div class="analysis-card-top">
            <div class="analysis-card-meta">
              ${renderSeverityBadge('High')}
              <span style="font-weight: 700; color: var(--severity-critical); font-size: 15px;">Analysis Failed</span>
            </div>
          </div>

          <div class="analysis-field">
            <div class="analysis-field-label">Details</div>
            <div class="analysis-field-content">${escapeHtml(errMsg)}</div>
          </div>

          <div class="analysis-field">
            <div class="analysis-field-label">Recommended Action</div>
            <div class="analysis-fix-box">
              Please check the server connection, verify backend is running on port 8000, and try again.
            </div>
          </div>
        </div>
      `;
    }

    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function renderAnalysisSuccess(reportData, rawCode) {
    if (!resultsSection || !resultsContent) return;
    resultsSection.style.display = 'block';

    const submissionId = reportData.submission_id;
    const totalBugs = reportData.total_bugs || 0;
    const bugs = reportData.bugs || [];

    if (resultsCountBadge) {
      resultsCountBadge.style.display = 'inline-flex';
      if (totalBugs === 0) {
        resultsCountBadge.className = 'badge-severity badge-Low';
        resultsCountBadge.style.background = 'rgba(16, 185, 129, 0.15)';
        resultsCountBadge.style.color = '#10b981';
        resultsCountBadge.style.borderColor = '#10b981';
        resultsCountBadge.textContent = '0 Issues Found';
      } else {
        const hasCritical = reportData.critical_count > 0 || reportData.high_count > 0;
        resultsCountBadge.className = `badge-severity ${hasCritical ? 'badge-Critical' : 'badge-Medium'}`;
        resultsCountBadge.textContent = `${totalBugs} Issue${totalBugs > 1 ? 's' : ''} Detected`;
      }
    }

    if (resultsActionButtons) {
      resultsActionButtons.innerHTML = `
        <a href="report.html?id=${submissionId}" class="btn btn-primary btn-sm">
          📊 Open Interactive Diagnostic View & Agentic Patching &rarr;
        </a>
      `;
    }

    if (totalBugs === 0) {
      resultsContent.innerHTML = `
        <div class="analysis-card analysis-card-Success">
          <div class="analysis-card-top">
            <div class="analysis-card-meta">
              <span class="badge-severity badge-Low" style="background: rgba(16, 185, 129, 0.15); color: #10b981; border-color: #10b981;">
                ✓ Clean Code
              </span>
              <span style="font-weight: 700; color: #10b981; font-size: 15px;">Zero Defects Detected</span>
            </div>
          </div>
          <div class="analysis-field">
            <div class="analysis-field-content" style="color: #e2e8f0;">
              🎉 Excellent! Static AST analysis, security vulnerability scanners (Bandit), and code complexity analyzers found no bugs, resource leaks, or syntax violations in this script.
            </div>
          </div>
        </div>
      `;
      resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      return;
    }

    // Render individual cards for each detected bug
    resultsContent.innerHTML = bugs.map((bug, idx) => {
      const lineSnippet = getLineSnippet(rawCode, bug.line);
      const sev = bug.severity || 'Medium';

      // Parse root cause and recommended fix from AI explanation if formatted
      const { rootCause, recommendedFix } = parseExplanationText(bug.explanation, bug.message);

      return `
        <div class="analysis-card analysis-card-${sev}">
          <div class="analysis-card-top">
            <div class="analysis-card-meta">
              ${renderSeverityBadge(sev)}
              <span class="analysis-meta-tag">Line ${bug.line}${bug.column ? `:${bug.column}` : ''}</span>
              <span class="analysis-meta-tag">Rule: ${escapeHtml(bug.rule_id)}</span>
              <span class="analysis-meta-tag">Tool: ${escapeHtml(bug.tool)}</span>
              <span class="analysis-meta-tag">Category: ${escapeHtml(bug.category)}</span>
            </div>
            ${renderScorePill(bug.severity_score)}
          </div>

          <div class="analysis-field">
            <div class="analysis-field-label">Issue #${idx + 1} Message</div>
            <div class="analysis-field-content">
              <strong>${escapeHtml(bug.message)}</strong>
            </div>
            ${lineSnippet ? `<pre class="analysis-code-snippet"><code>Line ${bug.line}: ${escapeHtml(lineSnippet)}</code></pre>` : ''}
          </div>

          ${rootCause ? `
            <div class="analysis-field">
              <div class="analysis-field-label">Root Cause</div>
              <div class="analysis-explanation-box">
                ${escapeHtml(rootCause)}
              </div>
            </div>
          ` : ''}

          ${recommendedFix ? `
            <div class="analysis-field">
              <div class="analysis-field-label">Recommended Fix</div>
              <div class="analysis-fix-box">
                ${escapeHtml(recommendedFix)}
              </div>
            </div>
          ` : ''}
        </div>
      `;
    }).join('');

    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // --- Helper text parsers ---

  function getLineSnippet(code, lineNum) {
    if (!code) return '';
    const lines = code.split('\n');
    if (lineNum >= 1 && lineNum <= lines.length) {
      return lines[lineNum - 1].trim();
    }
    return '';
  }

  function generateSyntaxExplanations(msg, snippet) {
    let rootCause = "The Python interpreter failed to parse the source code due to invalid syntax.";
    let fixGuidance = "Inspect the highlighted line and check for matching colons, quotes, and brackets.";

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

  function parseExplanationText(explanation, defaultMsg) {
    if (!explanation) {
      return {
        rootCause: `Static code analysis flagged this condition: ${defaultMsg}`,
        recommendedFix: "Refactor the flagged line to handle edge cases and follow Python best practices.",
      };
    }

    // Check if markdown formatted with sections
    let rootCause = "";
    let recommendedFix = "";

    const lines = explanation.split('\n');
    let currentSection = "";

    for (let line of lines) {
      const l = line.trim();
      if (l.includes("Root Cause")) {
        currentSection = "root";
      } else if (l.includes("Runtime Impact")) {
        currentSection = "impact";
      } else if (l.includes("Fix") || l.includes("Remediation")) {
        currentSection = "fix";
      } else if (l.startsWith("###") || l.startsWith("##")) {
        currentSection = "other";
      } else if (l) {
        if (currentSection === "root" || currentSection === "impact") {
          rootCause += (rootCause ? "\n" : "") + l;
        } else if (currentSection === "fix") {
          recommendedFix += (recommendedFix ? "\n" : "") + l;
        } else if (!rootCause) {
          rootCause += (rootCause ? "\n" : "") + l;
        }
      }
    }

    if (!rootCause) rootCause = explanation;
    if (!recommendedFix) recommendedFix = "Review line and apply the recommended fix guidance.";

    return { rootCause, recommendedFix };
  }
}
