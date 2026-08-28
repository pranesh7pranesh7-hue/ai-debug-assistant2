# BugSense AI — Frontend User Interface

Modern, responsive HTML5 / Vanilla CSS3 / ES6 JavaScript web application.

## Pages

- **`index.html`**: Main dashboard with quick stats, recent code submissions, and instant scan widget.
- **`upload.html`**: Ingestion interface with preset bug scenarios, drag-and-drop file upload, and pre-checks.
- **`report.html`**: Comprehensive audit results view, severity filtering, AI root-cause diagnostics, side-by-side unified diffs, 1-click patch synthesizer, live agentic debugging progress tracker, and interactive AI pair programmer chat.
- **`history.html`**: Full chronological table of past analyses and downloadable reports.
- **`login.html` & `register.html`**: JWT-based developer authentication.

## Architecture

- Pure Vanilla JS (ES6 modules) with centralized fetch API layer in `assets/js/api.js`.
- Custom CSS design system with dark glassmorphism, responsive CSS grid, and CSS variables for themes.
- Zero external frontend frameworks (no React, no Vue, no Tailwind) — hand-crafted for high performance.
