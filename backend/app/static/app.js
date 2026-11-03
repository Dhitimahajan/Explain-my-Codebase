/**
 * Explain My Codebase — Frontend Controller
 */

// Initialize Mermaid with clean neutral theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  themeVariables: {
    primaryColor: '#EBF2ED',
    primaryTextColor: '#1C1F1D',
    primaryBorderColor: '#4A6B56',
    lineColor: '#4A6B56',
    secondaryColor: '#F5F4EE',
    tertiaryColor: '#FFFFFF',
    fontFamily: 'Inter, -apple-system, sans-serif',
    fontSize: '12px',
  },
  securityLevel: 'loose',
});

// App State
const state = {
  repoId: null,
  repoName: null,
  fileTree: null,
  architecture: null,
  diagramMode: 'flow', // 'flow' | 'seq'
  activeFilter: 'all',
  searchQuery: '',
  activeFilePath: null,
  chatHistory: [],
  isProcessing: false,
};

// DOM Elements
const elements = {
  landingView: document.getElementById('landingView'),
  workspaceView: document.getElementById('workspaceView'),
  topSearchBar: document.getElementById('topSearchBar'),
  heroRepoInput: document.getElementById('heroRepoInput'),
  heroAnalyzeBtn: document.getElementById('heroAnalyzeBtn'),
  repoInput: document.getElementById('repoInput'),
  analyzeBtn: document.getElementById('analyzeBtn'),
  loadingOverlay: document.getElementById('loadingOverlay'),
  loadingTitle: document.getElementById('loadingTitle'),
  loadingSubtitle: document.getElementById('loadingSubtitle'),
  repoStatsBar: document.getElementById('repoStatsBar'),
  statsRepoName: document.getElementById('statsRepoName'),
  statsFiles: document.getElementById('statsFiles'),
  statsLoc: document.getElementById('statsLoc'),
  statsChunks: document.getElementById('statsChunks'),
  statsLanguages: document.getElementById('statsLanguages'),
  aiProviderName: document.getElementById('aiProviderName'),
  fileTreeContainer: document.getElementById('fileTreeContainer'),
  treeSearchInput: document.getElementById('treeSearchInput'),
  treeCountBadge: document.getElementById('treeCountBadge'),
  tabArchBtn: document.getElementById('tabArchBtn'),
  tabCodeBtn: document.getElementById('tabCodeBtn'),
  tabArchView: document.getElementById('tabArchView'),
  tabCodeView: document.getElementById('tabCodeView'),
  archTitle: document.getElementById('archTitle'),
  archSummary: document.getElementById('archSummary'),
  archPatternBadge: document.getElementById('archPatternBadge'),
  techStackBadges: document.getElementById('techStackBadges'),
  mermaidContainer: document.getElementById('mermaidContainer'),
  archLayersContainer: document.getElementById('archLayersContainer'),
  modeFlowBtn: document.getElementById('modeFlowBtn'),
  modeSeqBtn: document.getElementById('modeSeqBtn'),
  codeViewerBlock: document.getElementById('codeViewerBlock'),
  codeLangBadge: document.getElementById('codeLangBadge'),
  codeLineCount: document.getElementById('codeLineCount'),
  activeFilePath: document.getElementById('activeFilePath'),
  codeFileInfo: document.getElementById('codeFileInfo'),
  codeTabLabel: document.getElementById('codeTabLabel'),
  copyCodeBtn: document.getElementById('copyCodeBtn'),
  chatForm: document.getElementById('chatForm'),
  chatInput: document.getElementById('chatInput'),
  chatMessages: document.getElementById('chatMessages'),
  clearChatBtn: document.getElementById('clearChatBtn'),
  suggestedChips: document.getElementById('suggestedChips'),
  retrievalStatus: document.getElementById('retrievalStatus'),
  toastContainer: document.getElementById('toastContainer'),
};

// Toast Notifications
function showToast(message, type = 'info') {
  if (!elements.toastContainer) return;
  const toast = document.createElement('div');
  const bg = type === 'error' ? 'bg-rose-50 border-rose-200 text-rose-800' : 'bg-surface border-border text-charcoal';
  toast.className = `toast pointer-events-auto flex items-center space-x-2 px-3.5 py-2.5 rounded-xl border shadow-md text-xs font-medium ${bg}`;
  
  const iconName = type === 'error' ? 'alert-circle' : 'check-circle-2';
  toast.innerHTML = `<i data-lucide="${iconName}" class="w-4 h-4 shrink-0"></i><span>${message}</span>`;
  
  elements.toastContainer.appendChild(toast);
  if (window.lucide) lucide.createIcons();

  requestAnimationFrame(() => toast.classList.add('show'));

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Show/Hide Loading
function showLoading(title, subtitle) {
  if (title) elements.loadingTitle.textContent = title;
  if (subtitle) elements.loadingSubtitle.textContent = subtitle;
  elements.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
  elements.loadingOverlay.classList.add('hidden');
}

// Check System Status on Load
async function checkSystemStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    if (data.ai_provider && elements.aiProviderName) {
      elements.aiProviderName.textContent = data.ai_provider;
    }
  } catch (err) {
    console.warn('Status check failed', err);
  }
}

// Ingest & Analyze Repository
async function analyzeRepository(params) {
  if (state.isProcessing) return;
  state.isProcessing = true;
  showLoading('Analyzing Repository...', 'Parsing AST, categorizing architectural layers, and indexing vectors...');

  try {
    const res = await fetch('/api/repo/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Analysis failed');
    }

    const data = await res.json();
    state.repoId = data.repo_id;
    state.repoName = data.repo_name;
    state.fileTree = data.file_tree;
    state.architecture = data.architecture;

    // Transition views
    elements.landingView.classList.add('hidden');
    elements.workspaceView.classList.remove('hidden');
    elements.topSearchBar.classList.remove('hidden');

    if (data.source_url) {
      elements.repoInput.value = data.source_url;
      elements.heroRepoInput.value = data.source_url;
    }

    // Render Stats Bar
    elements.repoStatsBar.classList.remove('hidden');
    elements.statsRepoName.textContent = data.repo_name;
    elements.statsFiles.textContent = `${data.total_files.toLocaleString()} files`;
    elements.statsLoc.textContent = `${data.total_loc.toLocaleString()} LOC`;
    elements.statsChunks.textContent = `${data.total_chunks} chunks`;

    // Render Languages
    elements.statsLanguages.innerHTML = '';
    (data.languages || []).slice(0, 4).forEach((lang) => {
      const pill = document.createElement('span');
      pill.className = 'text-[11px] px-2 py-0.5 rounded-full bg-surface border border-border text-charcoal-muted flex items-center space-x-1';
      pill.innerHTML = `<span>${lang.language}</span> <span class="text-sage font-semibold">${lang.percentage}%</span>`;
      elements.statsLanguages.appendChild(pill);
    });

    // Render Components
    renderFileTree();
    await renderArchitecture(data.architecture);
    renderSuggestedQuestions(data.suggested_questions);
    switchTab('arch');

    showToast(`Successfully analyzed ${data.repo_name}`);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    hideLoading();
    state.isProcessing = false;
    if (window.lucide) lucide.createIcons();
  }
}

// Render Architecture
async function renderArchitecture(arch) {
  if (!arch) return;

  elements.archTitle.textContent = arch.title || 'System Architecture Overview';
  elements.archSummary.innerHTML = marked.parse(arch.summary || '');

  if (arch.pattern) {
    elements.archPatternBadge.textContent = arch.pattern;
    elements.archPatternBadge.classList.remove('hidden');
  } else {
    elements.archPatternBadge.classList.add('hidden');
  }

  // Tech stack pills
  elements.techStackBadges.innerHTML = '';
  (arch.tech_stack || []).forEach((tech) => {
    const badge = document.createElement('span');
    badge.className = 'text-xs font-medium px-2 py-0.5 rounded-md bg-sage-subtle text-sage border border-sage-border';
    badge.textContent = tech;
    elements.techStackBadges.appendChild(badge);
  });

  await renderActiveDiagram();

  // Layers breakdown
  elements.archLayersContainer.innerHTML = '';
  (arch.key_layers || []).forEach((layer) => {
    const card = document.createElement('div');
    card.className = 'bg-surface border border-border rounded-xl p-3.5 shadow-sm space-y-1.5';
    card.innerHTML = `
      <div class="flex items-center space-x-2">
        <span class="w-2 h-2 rounded-full bg-sage"></span>
        <h4 class="text-xs font-semibold text-charcoal">${layer.layer}</h4>
      </div>
      <p class="text-xs text-charcoal-muted leading-relaxed">${layer.description}</p>
    `;
    elements.archLayersContainer.appendChild(card);
  });
}

// Render Active Diagram (Flow vs Seq)
async function renderActiveDiagram() {
  if (!state.architecture) return;
  const arch = state.architecture;
  let code = state.diagramMode === 'seq' && arch.sequence_diagram ? arch.sequence_diagram : arch.mermaid_diagram;
  if (!code) return;

  let clean = code.trim().replace(/^```mermaid\s*/i, '').replace(/```$/i, '').trim();

  try {
    const renderId = 'mermaid-render-' + Math.floor(Math.random() * 100000);
    const { svg } = await mermaid.render(renderId, clean);
    elements.mermaidContainer.innerHTML = svg;
  } catch (err) {
    console.warn('Mermaid render warning:', err);
    elements.mermaidContainer.innerHTML = `<pre class="text-xs text-charcoal-muted font-mono bg-sidebar p-4 rounded-lg overflow-auto border border-border max-w-full">${clean}</pre>`;
  }
}

// Diagram Mode Toggles
elements.modeFlowBtn.addEventListener('click', async () => {
  state.diagramMode = 'flow';
  elements.modeFlowBtn.className = 'px-2.5 py-1 rounded-md text-[11px] font-semibold bg-surface text-charcoal shadow-sm transition';
  elements.modeSeqBtn.className = 'px-2.5 py-1 rounded-md text-[11px] font-semibold text-charcoal-muted hover:text-charcoal transition';
  await renderActiveDiagram();
});

elements.modeSeqBtn.addEventListener('click', async () => {
  state.diagramMode = 'seq';
  elements.modeSeqBtn.className = 'px-2.5 py-1 rounded-md text-[11px] font-semibold bg-surface text-charcoal shadow-sm transition';
  elements.modeFlowBtn.className = 'px-2.5 py-1 rounded-md text-[11px] font-semibold text-charcoal-muted hover:text-charcoal transition';
  await renderActiveDiagram();
});

// Render File Tree Explorer
function renderFileTree() {
  if (!state.fileTree) return;
  elements.fileTreeContainer.innerHTML = '';
  let visibleCount = 0;

  function buildNode(node, depth = 0) {
    const isMatchingModule = state.activeFilter === 'all' || node.module === state.activeFilter;
    const isMatchingSearch = !state.searchQuery || node.name.toLowerCase().includes(state.searchQuery.toLowerCase()) || node.path.toLowerCase().includes(state.searchQuery.toLowerCase());

    if (node.type === 'file') {
      if (!isMatchingModule || !isMatchingSearch) return null;
      visibleCount++;

      const div = document.createElement('div');
      div.className = `tree-node ${state.activeFilePath === node.path ? 'active-file' : ''}`;
      div.style.paddingLeft = `${depth * 12 + 6}px`;

      div.innerHTML = `
        <span class="mr-1.5 opacity-70">📄</span>
        <span class="truncate flex-1">${node.name}</span>
        <span class="text-[10px] text-charcoal-light ml-1 font-mono">${node.loc}L</span>
      `;

      div.addEventListener('click', () => openFileInViewer(node.path));
      return div;
    } else {
      const container = document.createElement('div');
      const header = document.createElement('div');
      header.className = 'tree-node font-semibold text-charcoal';
      header.style.paddingLeft = `${depth * 12 + 6}px`;

      const childrenContainer = document.createElement('div');
      childrenContainer.className = 'space-y-0.5';

      let hasVisibleChild = false;
      (node.children || []).forEach((child) => {
        const childEl = buildNode(child, depth + 1);
        if (childEl) {
          hasVisibleChild = true;
          childrenContainer.appendChild(childEl);
        }
      });

      if (!hasVisibleChild && state.searchQuery) return null;

      header.innerHTML = `
        <i data-lucide="chevron-down" class="w-3.5 h-3.5 mr-1 text-charcoal-light transition-transform"></i>
        <span class="mr-1.5 opacity-70">📁</span>
        <span class="truncate flex-1">${node.name}</span>
        <span class="text-[10px] text-charcoal-light ml-1">${node.loc}L</span>
      `;

      let isOpen = true;
      header.addEventListener('click', () => {
        isOpen = !isOpen;
        childrenContainer.style.display = isOpen ? 'block' : 'none';
        const chevron = header.querySelector('i');
        if (chevron) {
          chevron.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(-90deg)';
        }
      });

      container.appendChild(header);
      container.appendChild(childrenContainer);
      return container;
    }
  }

  (state.fileTree.children || []).forEach((child) => {
    const el = buildNode(child, 0);
    if (el) elements.fileTreeContainer.appendChild(el);
  });

  elements.treeCountBadge.textContent = `${visibleCount} files`;
  if (window.lucide) lucide.createIcons();
}

// Module Filters
document.querySelectorAll('.mod-filter').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mod-filter').forEach((b) => {
      b.classList.remove('active', 'bg-sage', 'text-white');
      b.classList.add('bg-surface', 'text-charcoal-muted');
    });
    btn.classList.add('active', 'bg-sage', 'text-white');
    btn.classList.remove('bg-surface', 'text-charcoal-muted');
    state.activeFilter = btn.getAttribute('data-mod');
    renderFileTree();
  });
});

// Tree Search Filter
elements.treeSearchInput.addEventListener('input', (e) => {
  state.searchQuery = e.target.value.trim();
  renderFileTree();
});

// Open File in Code Viewer
async function openFileInViewer(filePath, startLine = null, endLine = null) {
  if (!state.repoId) return;

  const normalizedPath = filePath.replace(/\\/g, '/');
  state.activeFilePath = normalizedPath;
  renderFileTree();

  elements.codeTabLabel.textContent = normalizedPath.split('/').pop();
  elements.activeFilePath.textContent = normalizedPath;
  elements.codeFileInfo.classList.remove('hidden');

  switchTab('code');
  elements.codeViewerBlock.textContent = '// Loading file content...';

  try {
    const res = await fetch(`/api/repo/${state.repoId}/file?path=${encodeURIComponent(normalizedPath)}`);
    if (!res.ok) throw new Error('File not found');

    const data = await res.json();
    elements.codeLangBadge.textContent = data.language;
    elements.codeLineCount.textContent = `${data.loc} lines`;

    const langMap = {
      'Python': 'python',
      'TypeScript': 'typescript',
      'TypeScript (React)': 'tsx',
      'JavaScript': 'javascript',
      'JavaScript (React)': 'jsx',
      'Go': 'go',
      'Rust': 'rust',
      'Java': 'java',
      'C++': 'cpp',
      'SQL': 'sql',
      'JSON': 'json',
      'YAML': 'yaml',
      'HTML': 'html',
      'CSS': 'css'
    };

    const prismClass = `language-${langMap[data.language] || 'clike'}`;
    elements.codeViewerBlock.className = prismClass;
    elements.codeViewerBlock.textContent = data.content;
    Prism.highlightElement(elements.codeViewerBlock);

    if (startLine) {
      setTimeout(() => {
        const total = data.loc || 1;
        const container = elements.codeViewerBlock.parentElement.parentElement;
        container.scrollTop = Math.max(0, ((startLine - 2) / total) * container.scrollHeight);
      }, 100);
    }
  } catch (err) {
    elements.codeViewerBlock.textContent = `// Error loading file: ${err.message}`;
  }
}
window.openFileInViewer = openFileInViewer;

// Tab Switching
function switchTab(tab) {
  if (tab === 'arch') {
    elements.tabArchBtn.classList.add('active', 'text-sage', 'bg-sage-subtle', 'border-sage-border');
    elements.tabArchBtn.classList.remove('text-charcoal-muted');
    elements.tabCodeBtn.classList.remove('active', 'text-sage', 'bg-sage-subtle', 'border-sage-border');
    elements.tabCodeBtn.classList.add('text-charcoal-muted');

    elements.tabArchView.classList.remove('hidden');
    elements.tabCodeView.classList.add('hidden');
  } else {
    elements.tabCodeBtn.classList.add('active', 'text-sage', 'bg-sage-subtle', 'border-sage-border');
    elements.tabCodeBtn.classList.remove('text-charcoal-muted');
    elements.tabArchBtn.classList.remove('active', 'text-sage', 'bg-sage-subtle', 'border-sage-border');
    elements.tabArchBtn.classList.add('text-charcoal-muted');

    elements.tabCodeView.classList.remove('hidden');
    elements.tabArchView.classList.add('hidden');
  }
}
elements.tabArchBtn.addEventListener('click', () => switchTab('arch'));
elements.tabCodeBtn.addEventListener('click', () => switchTab('code'));

// Copy Code Button
elements.copyCodeBtn.addEventListener('click', () => {
  const code = elements.codeViewerBlock.textContent;
  navigator.clipboard.writeText(code).then(() => {
    showToast('Code copied to clipboard');
  });
});

// Render Suggested Questions
function renderSuggestedQuestions(questions) {
  if (!questions || questions.length === 0) return;
  elements.suggestedChips.innerHTML = '';
  questions.forEach((q) => {
    const btn = document.createElement('button');
    btn.className = 'suggest-btn text-left text-xs bg-surface hover:bg-subtle text-charcoal p-1.5 rounded-lg border border-border transition flex items-center space-x-1.5';
    btn.innerHTML = `<i data-lucide="help-circle" class="w-3.5 h-3.5 text-sage shrink-0"></i><span>${q}</span>`;
    btn.addEventListener('click', () => {
      elements.chatInput.value = q;
      submitChatMessage();
    });
    elements.suggestedChips.appendChild(btn);
  });
  if (window.lucide) lucide.createIcons();
}

// Chat Handlers
function addUserMessage(text) {
  const div = document.createElement('div');
  div.className = 'flex justify-end';
  div.innerHTML = `
    <div class="bg-sage text-white px-3 py-2 rounded-xl rounded-tr-none text-xs leading-relaxed max-w-[85%] shadow-sm">
      ${text}
    </div>
  `;
  elements.chatMessages.appendChild(div);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function addBotMessage(text) {
  const div = document.createElement('div');
  div.className = 'flex items-start space-x-2';
  div.innerHTML = `
    <div class="w-6 h-6 rounded-md bg-sage text-white flex items-center justify-center shrink-0">
      <i data-lucide="bot" class="w-3.5 h-3.5"></i>
    </div>
    <div class="bg-surface border border-border rounded-xl rounded-tl-none p-3 text-charcoal leading-relaxed max-w-[88%] shadow-sm space-y-1">
      <div class="markdown-body">${marked.parse(text)}</div>
    </div>
  `;
  elements.chatMessages.appendChild(div);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  if (window.lucide) lucide.createIcons();
  return div;
}

async function submitChatMessage() {
  const query = elements.chatInput.value.trim();
  if (!query || state.isProcessing) return;

  if (!state.repoId) {
    showToast('Please analyze a repository first.', 'error');
    return;
  }

  addUserMessage(query);
  elements.chatInput.value = '';
  elements.retrievalStatus.textContent = 'Searching vectors...';

  const botBubble = addBotMessage('Tracing codebase context...');

  try {
    const res = await fetch('/api/chat/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        repo_id: state.repoId,
        query: query,
        history: state.chatHistory,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Query failed');
    }

    const data = await res.json();
    state.chatHistory.push({ role: 'user', content: query });
    state.chatHistory.push({ role: 'assistant', content: data.answer });

    // Format citations to clickable buttons
    let formatted = data.answer;
    formatted = formatted.replace(/\[([a-zA-Z0-9_\-./\\]+):(\d+)-(\d+)\]/g, (match, rawPath, start, end) => {
      const cleanPath = rawPath.replace(/\\/g, '/');
      return `<button class="citation-link" onclick="window.openFileInViewer('${cleanPath}', ${start}, ${end})"><i data-lucide="file-text" class="w-3 h-3"></i> ${cleanPath}:${start}-${end}</button>`;
    });

    botBubble.querySelector('.markdown-body').innerHTML = marked.parse(formatted);

    // Render nested diagrams in chat
    const mermaidNodes = botBubble.querySelectorAll('.language-mermaid');
    for (const node of mermaidNodes) {
      const code = node.textContent.trim();
      const mDiv = document.createElement('div');
      mDiv.className = 'my-2 bg-sidebar p-2 rounded-lg border border-border';
      const mId = 'chat-m-' + Math.floor(Math.random() * 100000);
      try {
        const { svg } = await mermaid.render(mId, code);
        mDiv.innerHTML = svg;
      } catch (e) {
        mDiv.innerHTML = `<pre class="text-[11px] font-mono text-charcoal-muted">${code}</pre>`;
      }
      node.parentElement.replaceWith(mDiv);
    }
  } catch (err) {
    botBubble.querySelector('.markdown-body').innerHTML = `<p class="text-rose-600 font-medium">Error: ${err.message}</p>`;
  } finally {
    elements.retrievalStatus.textContent = '';
    if (window.lucide) lucide.createIcons();
  }
}

// Clear Chat
elements.clearChatBtn.addEventListener('click', () => {
  elements.chatMessages.innerHTML = '';
  state.chatHistory = [];
  addBotMessage('Chat history cleared. What would you like to explore next?');
});

// Chat Form submit & Enter key
elements.chatForm.addEventListener('submit', (e) => {
  e.preventDefault();
  submitChatMessage();
});

elements.chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitChatMessage();
  }
});

// Ingest Submissions
elements.heroAnalyzeBtn.addEventListener('click', () => {
  const url = elements.heroRepoInput.value.trim();
  if (!url) return showToast('Please enter a GitHub repository URL.', 'error');
  analyzeRepository({ repo_url: url });
});

elements.heroRepoInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    const url = elements.heroRepoInput.value.trim();
    if (!url) return showToast('Please enter a GitHub repository URL.', 'error');
    analyzeRepository({ repo_url: url });
  }
});

elements.analyzeBtn.addEventListener('click', () => {
  const url = elements.repoInput.value.trim();
  if (!url) return showToast('Please enter a GitHub repository URL.', 'error');
  analyzeRepository({ repo_url: url });
});

elements.repoInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    const url = elements.repoInput.value.trim();
    if (!url) return showToast('Please enter a GitHub repository URL.', 'error');
    analyzeRepository({ repo_url: url });
  }
});

// Sample buttons
document.querySelectorAll('.sample-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    const key = btn.getAttribute('data-key');
    analyzeRepository({ sample_key: key });
  });
});

// Initialization
window.addEventListener('DOMContentLoaded', () => {
  checkSystemStatus();
  if (window.lucide) lucide.createIcons();
});
