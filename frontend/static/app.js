/**
 * AI Research Assistant - Frontend Application Logic
 * Implements SSE streaming, step transitions, Markdown rendering, and report exports.
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const statusBadge = document.getElementById('statusBadge');
  const statusText = document.getElementById('statusText');
  const researchForm = document.getElementById('researchForm');
  const topicInput = document.getElementById('topicInput');
  const startBtn = document.getElementById('startBtn');
  const chipButtons = document.querySelectorAll('.chip-btn');

  // Progress Elements
  const progressSection = document.getElementById('progressSection');
  const currentStepTitle = document.getElementById('currentStepTitle');
  const currentStepMessage = document.getElementById('currentStepMessage');
  const progressPercentage = document.getElementById('progressPercentage');
  const progressBar = document.getElementById('progressBar');
  const queriesPreview = document.getElementById('queriesPreview');
  const queriesTags = document.getElementById('queriesTags');

  // Steps
  const stepElements = {
    planning: document.getElementById('step-planning'),
    searching: document.getElementById('step-searching'),
    extracting: document.getElementById('step-extracting'),
    summarizing: document.getElementById('step-summarizing'),
    synthesizing: document.getElementById('step-synthesizing'),
  };

  // Error & Result Elements
  const errorBox = document.getElementById('errorBox');
  const errorMessage = document.getElementById('errorMessage');
  const resultSection = document.getElementById('resultSection');
  const reportContent = document.getElementById('reportContent');
  const reportModelBadge = document.getElementById('reportModelBadge');
  const reportSourcesCountBadge = document.getElementById('reportSourcesCountBadge');
  const sourceTabCount = document.getElementById('sourceTabCount');
  const sourcesGrid = document.getElementById('sourcesGrid');
  const copyBtn = document.getElementById('copyBtn');
  const downloadBtn = document.getElementById('downloadBtn');

  // Tab controls
  const tabButtons = document.querySelectorAll('.tab-btn');
  const reportView = document.getElementById('reportView');
  const sourcesView = document.getElementById('sourcesView');

  let activeResultData = null;
  let activeEventSource = null;

  // Initialize Backend Health Check
  checkBackendHealth();

  async function checkBackendHealth() {
    try {
      const res = await fetch('/api/health');
      if (!res.ok) throw new Error('Health check returned non-200');
      const data = await res.json();

      if (data.status === 'healthy') {
        statusBadge.className = 'status-pill status-connected';
        statusText.textContent = `${data.active_provider.toUpperCase()} (${data.active_model})`;
      } else {
        statusBadge.className = 'status-pill status-error';
        statusText.textContent = 'API Key Needed (.env)';
      }
    } catch (err) {
      statusBadge.className = 'status-pill status-error';
      statusText.textContent = 'Backend Offline';
    }
  }

  // Handle Suggested Chip Clicks
  chipButtons.forEach(chip => {
    chip.addEventListener('click', () => {
      topicInput.value = chip.dataset.topic;
      startResearch(chip.dataset.topic);
    });
  });

  // Handle Form Submission
  researchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const topic = topicInput.value.trim();
    if (!topic) return;
    startResearch(topic);
  });

  // Tab Switching
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const targetTab = btn.dataset.tab;
      if (targetTab === 'reportView') {
        reportView.classList.remove('hidden');
        reportView.classList.add('active');
        sourcesView.classList.add('hidden');
        sourcesView.classList.remove('active');
      } else {
        sourcesView.classList.remove('hidden');
        sourcesView.classList.add('active');
        reportView.classList.add('hidden');
        reportView.classList.remove('active');
      }
    });
  });

  // Reset UI State for New Research
  function resetResearchUI() {
    if (activeEventSource) {
      activeEventSource.close();
      activeEventSource = null;
    }

    errorBox.classList.add('hidden');
    resultSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    queriesPreview.classList.add('hidden');
    queriesTags.innerHTML = '';
    activeResultData = null;

    updateProgress(5, 'Starting research...', 'Initializing RAG agent...');
    Object.values(stepElements).forEach(el => {
      el.classList.remove('active', 'completed');
    });

    startBtn.disabled = true;
    startBtn.querySelector('.btn-text').textContent = 'Researching...';
  }

  function updateProgress(percent, title, message) {
    progressBar.style.width = `${percent}%`;
    progressPercentage.textContent = `${percent}%`;
    if (title) currentStepTitle.textContent = title;
    if (message) currentStepMessage.textContent = message;
  }

  function setStepState(activeStep) {
    const stepOrder = ['planning', 'searching', 'extracting', 'summarizing', 'synthesizing'];
    const activeIndex = stepOrder.indexOf(activeStep);

    stepOrder.forEach((stepName, idx) => {
      const el = stepElements[stepName];
      if (!el) return;

      if (idx < activeIndex) {
        el.classList.remove('active');
        el.classList.add('completed');
      } else if (idx === activeIndex) {
        el.classList.add('active');
        el.classList.remove('completed');
      } else {
        el.classList.remove('active', 'completed');
      }
    });
  }

  function showError(msg) {
    if (activeEventSource) {
      activeEventSource.close();
      activeEventSource = null;
    }
    progressSection.classList.add('hidden');
    errorBox.classList.remove('hidden');
    errorMessage.textContent = msg || 'An unknown error occurred during research.';
    startBtn.disabled = false;
    startBtn.querySelector('.btn-text').textContent = 'Start Research';
  }

  // Start Research via SSE Stream
  function startResearch(topic) {
    resetResearchUI();

    const streamUrl = `/api/research/stream?topic=${encodeURIComponent(topic)}`;
    activeEventSource = new EventSource(streamUrl);

    activeEventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);

        if (payload.type === 'progress') {
          handleProgressEvent(payload);
        } else if (payload.type === 'complete') {
          handleCompletion(payload.result);
        } else if (payload.type === 'error') {
          showError(payload.message);
        }
      } catch (err) {
        console.error('Failed to parse SSE payload:', err, event.data);
      }
    };

    activeEventSource.onerror = (err) => {
      console.warn('SSE connection error. Retrying or falling back...', err);
      // Fallback: If SSE fails immediately, attempt standard POST request
      if (activeEventSource.readyState === EventSource.CLOSED) {
        activeEventSource.close();
        fallbackPostResearch(topic);
      }
    };
  }

  // Fallback direct REST endpoint if SSE stream is blocked
  async function fallbackPostResearch(topic) {
    try {
      updateProgress(40, 'Running Research Pipeline', 'Fetching sources and synthesizing report...');
      const response = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic }),
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Research request failed');
      }
      const data = await response.json();
      handleCompletion(data);
    } catch (e) {
      showError(e.message);
    }
  }

  function handleProgressEvent(p) {
    updateProgress(p.progress, getTitleForStep(p.step), p.message);
    setStepState(p.step);

    if (p.step === 'searching' && p.data && p.data.queries) {
      queriesPreview.classList.remove('hidden');
      queriesTags.innerHTML = '';
      p.data.queries.forEach(q => {
        const tag = document.createElement('span');
        tag.className = 'query-tag';
        tag.textContent = q;
        queriesTags.appendChild(tag);
      });
    }
  }

  function getTitleForStep(step) {
    switch (step) {
      case 'planning': return 'Planning Search Strategy';
      case 'searching': return 'Executing Web Searches';
      case 'extracting': return 'Extracting Clean Content';
      case 'summarizing': return 'Analyzing & Summarizing Evidence';
      case 'synthesizing': return 'Synthesizing Grounded Report';
      default: return 'Processing';
    }
  }

  function handleCompletion(result) {
    if (activeEventSource) {
      activeEventSource.close();
      activeEventSource = null;
    }

    updateProgress(100, 'Research Complete', 'Structured report synthesized.');
    Object.values(stepElements).forEach(el => el.classList.add('completed'));

    activeResultData = result;

    // Populate Report Header Metadata
    reportModelBadge.textContent = `${result.provider_used.toUpperCase()}: ${result.model_used}`;
    reportSourcesCountBadge.textContent = `${result.sources.length} Sources Analyzed`;
    sourceTabCount.textContent = result.sources.length;

    // Enhance Report with styled citation pills
    let styledReport = result.report;
    styledReport = styledReport.replace(/\[(\d+)\]/g, (match, p1) => {
      return `<a href="#source-${p1}" class="citation-pill" title="Jump to Source ${p1}">[${p1}]</a>`;
    });

    // Render Markdown
    if (window.marked && window.DOMPurify) {
      const rawHtml = marked.parse(styledReport);
      reportContent.innerHTML = DOMPurify.sanitize(rawHtml);
    } else {
      reportContent.textContent = result.report;
    }

    // Populate Sources Tab
    populateSourcesGrid(result.sources);

    // Show Result Panel
    resultSection.classList.remove('hidden');
    progressSection.classList.add('hidden');
    startBtn.disabled = false;
    startBtn.querySelector('.btn-text').textContent = 'Start Research';

    // Scroll smoothly to results
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function populateSourcesGrid(sources) {
    sourcesGrid.innerHTML = '';
    sources.forEach(src => {
      const card = document.createElement('div');
      card.className = 'source-card';
      card.id = `source-${src.id}`;

      card.innerHTML = `
        <div class="source-card-header">
          <span class="source-index">${src.id}</span>
          <a href="${src.url}" target="_blank" rel="noopener noreferrer" class="source-title">
            ${src.title || 'Untitled Source'}
          </a>
        </div>
        <div class="source-url">${src.url}</div>
        <div class="source-summary">${src.summary || src.snippet || 'No summary available.'}</div>
      `;

      sourcesGrid.appendChild(card);
    });
  }

  // Copy Markdown to Clipboard
  copyBtn.addEventListener('click', async () => {
    if (!activeResultData) return;
    try {
      await navigator.clipboard.writeText(activeResultData.report);
      const span = copyBtn.querySelector('span');
      const original = span.textContent;
      span.textContent = 'Copied!';
      setTimeout(() => { span.textContent = original; }, 2000);
    } catch (err) {
      alert('Unable to copy to clipboard.');
    }
  });

  // Download Markdown file
  downloadBtn.addEventListener('click', () => {
    if (!activeResultData) return;
    const cleanTopic = activeResultData.topic
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    const filename = `research-report-${cleanTopic || 'export'}.md`;

    const blob = new Blob([activeResultData.report], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
});
