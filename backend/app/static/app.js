/**
 * Explain My Codebase — Frontend Controller
 */

// Initialize Mermaid with Dark Theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    darkMode: true,
    background: '#0c1017',
    primaryColor: '#4f46e5',
    primaryTextColor: '#f8fafc',
    primaryBorderColor: '#6366f1',
    lineColor: '#818cf8',
    secondaryColor: '#182030',
    tertiaryColor: '#111622',
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
  repoInput: document.getElementById('repoInput'),
  sampleSelect: document.getElementById('sampleSelect'),
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
};

// Check System Status on Load
async function checkSystemStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    if (data.ai_provider) {
      elements.aiProviderName.textContent = data.ai_provider;
    }
  } catch (err) {
    console.error('Status check failed', err);
  }
}

// Ingest & Analyze Repository
async function analyzeRepository(params) {
  if (state.isProcessing) return;
  state.isProcessing = true;
  showLoading('Ingesting & Analyzing Repository...', 'Cloning repository, categorizing architectural layers, and indexing vectors...');

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

    // Update Input field
    if (data.source_url) {
      elements.repoInput.value = data.source_url;
    }

    // Render Stats
    elements.repoStatsBar.classList.remove('hidden');
    elements.statsRepoName.textContent = data.repo_name;
    elements.statsFiles.textContent = `${data.total_files.toLocaleString()} files`;
    elements.statsLoc.textContent = `${data.total_loc.toLocaleString()} LOC`;
    elements.statsChunks.textContent = `${data.total_chunks} chunks`;

    // Render Languages
    elements.statsLanguages.innerHTML = '';
    (data.languages || []).slice(0, 4).forEach((lang) => {
      const pill = document.createElement('span');
      pill.className = 'text-[11px] px-2 py-0.5 rounded-full bg-dark-800 border border-dark-700 text-slate-300 flex items-center space-x-1';
      pill.innerHTML = `<span>${lang.language}</span> <span class="text-indigo-400 font-semibold">${lang.percentage}%</span>`;
      elements.statsLanguages.appendChild(pill);
    });

    // Render File Tree
    renderFileTree();

    // Render Architecture Tab
    await renderArchitecture(data.architecture);

    // Render Suggested Questions
    renderSuggestedQuestions(data.suggested_questions);

    // Switch to Architecture tab
    switchTab('arch');

    // Add Copilot notification
    addBotMessage(`🎉 Successfully analyzed **${data.repo_name}**!\n\nArchitecture Pattern: **${data.architecture.pattern || 'Modular Layered Architecture'}**\n\nExplore the interactive **System Map** or **Sequence Trace** diagrams in the center panel, filter modules on the left, or ask any question!`);

  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    hideLoading();
    state.isProcessing = false;
    if (window.lucide) lucide.createIcons();
  }
}

// Render Architecture Overview & Mermaid Diagram
async function renderArchitecture(arch) {
  if (!arch) return;

  elements.archTitle.textContent = arch.title || 'System Architecture Overview';
  elements.archSummary.innerHTML = marked.parse(arch.summary || '');

  // Pattern Badge
  if (arch.pattern) {
    elements.archPatternBadge.textContent = arch.pattern;
    elements.archPatternBadge.classList.remove('hidden');
  } else {
    elements.archPatternBadge.classList.add('hidden');
  }

  // Tech Stack Badges
  elements.techStackBadges.innerHTML = '';
  (arch.tech_stack || []).forEach((tech) => {
    const badge = document.createElement('span');
    badge.className = 'text-xs font-semibold px-2 py-1 rounded-md bg-indigo-950/80 text-indigo-300 border border-indigo-500/30';
    badge.textContent = tech;
    elements.techStackBadges.appendChild(badge);
  });

  // Render Diagram according to current mode
  await renderActiveDiagram();

  // Key Layers Breakdown
  elements.archLayersContainer.innerHTML = '';
  (arch.key_layers || []).forEach((layer) => {
    const card = document.createElement('div');
    card.className = 'bg-dark-900/90 border border-dark-700/80 rounded-xl p-4 hover:border-indigo-500/40 transition flex flex-col justify-between';
    card.innerHTML = `
      <div>
        <div class="flex items-center space-x-2 mb-2">
          <span class="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
          <h4 class="text-xs font-bold text-white uppercase tracking-wider">${layer.layer}</h4>
        </div>
        <p class="text-xs text-slate-400 leading-relaxed">${layer.description}</p>
      </div>
    `;
    elements.archLayersContainer.appendChild(card);
  });
}

// Render Diagram according to mode ('flow' | 'seq')
async function renderActiveDiagram() {
  if (!state.architecture) return;

  const arch = state.architecture;
  let code = state.diagramMode === 'seq' && arch.sequence_diagram ? arch.sequence_diagram : arch.mermaid_diagram;

  if (!code) return;

  let cleanDiagram = code.trim();
  cleanDiagram = cleanDiagram.replace(/^```mermaid\s*/i, '').replace(/```$/i, '').trim();

  try {
    const renderId = 'mermaid-main-' + Math.floor(Math.random() * 10000);
    const { svg } = await mermaid.render(renderId, cleanDiagram);
    elements.mermaidContainer.innerHTML = svg;
  } catch (e) {
    console.warn('Mermaid render issue:', e);
    elements.mermaidContainer.innerHTML = `<pre class="text-xs text-slate-300 font-mono bg-dark-950 p-4 rounded-lg overflow-auto border border-dark-700 max-w-full">${cleanDiagram}</pre>`;
  }
}

// Diagram Mode Toggles
elements.modeFlowBtn.addEventListener('click', async () => {
  state.diagramMode = 'flow';
  elements.modeFlowBtn.className = 'px-2.5 py-1 rounded-md text-[11px] font-semibold bg-indigo-600 text-white shadow-sm transition';
  elements.modeSeqBtn.className = 'px-2.5 py-1 rounded-md text-[11px] font-semibold text-slate-400 hover:text-white transition';
  await renderActiveDiagram();
});

elements.modeSeqBtn.addEventListener('click', async () => {
  state.diagramMode = 'seq';
  elements.modeSeqBtn.className = 'px-2.5 py-1 rounded-md text-[11px] font-semibold bg-indigo-600 text-white shadow-sm transition';
  elements.modeFlowBtn.className = 'px-2.5 py-1 rounded-md text-[11px] font-semibold text-slate-400 hover:text-white transition';
  await renderActiveDiagram();
});

// Render File Tree Explorer
function renderFileTree() {
  if (!state.fileTree) return;
  elements.fileTreeContainer.innerHTML = '';

  let visibleCount = 0;

  function buildNodeHtml(node, depth = 0) {
    const isMatchingModule = state.activeFilter === 'all' || node.module === state.activeFilter;
    const isMatchingSearch = !state.searchQuery || node.name.toLowerCase().includes(state.searchQuery.toLowerCase()) || node.path.toLowerCase().includes(state.searchQuery.toLowerCase());

    if (node.type === 'file') {
      if (!isMatchingModule || !isMatchingSearch) return null;
      visibleCount++;

      const div = document.createElement('div');
      div.className = `tree-node text-slate-300 hover:text-white ${state.activeFilePath === node.path ? 'active-file' : ''}`;
      div.style.paddingLeft = `${depth * 12 + 6}px`;

      const moduleClass = getModuleColorClass(node.module);

      div.innerHTML = `
        <span class="mr-1.5">${node.icon || '📄'}</span>
        <span class="truncate flex-1">${node.name}</span>
        <span class="module-badge ${moduleClass} ml-1">${node.module.split(' ')[0]}</span>
        <span class="text-[10px] text-slate-500 ml-1 font-mono">${node.loc}L</span>
      `;

      div.addEventListener('click', () => openFileInViewer(node.path));
      return div;
    } else {
      // Directory
      const container = document.createElement('div');
      const header = document.createElement('div');
      header.className = 'tree-node text-slate-400 font-semibold hover:text-slate-200';
      header.style.paddingLeft = `${depth * 12 + 6}px`;

      const childrenContainer = document.createElement('div');
      childrenContainer.className = 'space-y-0.5';

      let hasVisibleChild = false;
      (node.children || []).forEach((child) => {
        const childEl = buildNodeHtml(child, depth + 1);
        if (childEl) {
          hasVisibleChild = true;
          childrenContainer.appendChild(childEl);
        }
      });

      if (!hasVisibleChild && state.searchQuery) return null;

      header.innerHTML = `
        <i data-lucide="chevron-down" class="w-3.5 h-3.5 mr-1 text-slate-500 transition-transform"></i>
        <span class="mr-1.5">${node.icon || '📁'}</span>
        <span class="truncate flex-1">${node.name}</span>
        <span class="text-[10px] text-slate-600 ml-1">${node.loc}L</span>
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
    const el = buildNodeHtml(child, 0);
    if (el) elements.fileTreeContainer.appendChild(el);
  });

  elements.treeCountBadge.textContent = `${visibleCount} files`;
  if (window.lucide) lucide.createIcons();
}

function getModuleColorClass(moduleName) {
  switch (moduleName) {
    case 'Auth & Security':
      return 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
    case 'Database & Models':
      return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
    case 'API & Routes':
      return 'bg-sky-500/20 text-sky-300 border border-sky-500/30';
    case 'Frontend UI':
      return 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
    case 'Services & Utils':
      return 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30';
    case 'Tests':
      return 'bg-rose-500/20 text-rose-300 border border-rose-500/30';
    default:
      return 'bg-slate-700/40 text-slate-400 border border-slate-700';
  }
}

// Open File in Code Viewer (Globally attached to window)
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

    // Map language to Prism class
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
    };

    const prismClass = `language-${langMap[data.language] || 'clike'}`;
    elements.codeViewerBlock.className = prismClass;
    elements.codeViewerBlock.textContent = data.content;

    Prism.highlightElement(elements.codeViewerBlock);

    // If specific lines targeted, scroll to line
    if (startLine) {
      setTimeout(() => {
        const totalLines = data.loc || 1;
        const container = elements.codeViewerBlock.parentElement.parentElement;
        const scrollFraction = Math.max(0, (startLine - 2) / totalLines);
        container.scrollTop = scrollFraction * container.scrollHeight;
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
    elements.tabArchBtn.classList.add('active', 'text-indigo-400', 'bg-dark-800', 'border', 'border-dark-700');
    elements.tabArchBtn.classList.remove('text-slate-400');
    elements.tabCodeBtn.classList.remove('active', 'text-indigo-400', 'bg-dark-800', 'border', 'border-dark-700');
    elements.tabCodeBtn.classList.add('text-slate-400');

    elements.tabArchView.classList.remove('hidden');
    elements.tabCodeView.classList.add('hidden');
  } else {
    elements.tabCodeBtn.classList.add('active', 'text-indigo-400', 'bg-dark-800', 'border', 'border-dark-700');
    elements.tabCodeBtn.classList.remove('text-slate-400');
    elements.tabArchBtn.classList.remove('active', 'text-indigo-400', 'bg-dark-800', 'border', 'border-dark-700');
    elements.tabArchBtn.classList.add('text-slate-400');

    elements.tabCodeView.classList.remove('hidden');
    elements.tabArchView.classList.add('hidden');
  }
}

// Render Suggested Questions
function renderSuggestedQuestions(questions) {
  if (!questions || questions.length === 0) return;
  elements.suggestedChips.innerHTML = '';
  questions.forEach((q) => {
    const btn = document.createElement('button');
    btn.className = 'suggest-btn text-left text-xs bg-dark-800 hover:bg-dark-750 text-indigo-300 hover:text-indigo-200 p-1.5 rounded border border-dark-700 transition flex items-center space-x-1.5';
    btn.innerHTML = `<i data-lucide="help-circle" class="w-3 h-3 text-indigo-400 shrink-0"></i><span>${q}</span>`;
    btn.addEventListener('click', () => {
      elements.chatInput.value = q;
      submitChatMessage();
    });
    elements.suggestedChips.appendChild(btn);
  });
  if (window.lucide) lucide.createIcons();
}

// Chat Submissions
async function submitChatMessage() {
  const query = elements.chatInput.value.trim();
  if (!query || state.isProcessing) return;

  if (!state.repoId) {
    alert('Please ingest a repository first before asking questions.');
    return;
  }

  // Add user message
  addUserMessage(query);
  elements.chatInput.value = '';
  elements.retrievalStatus.textContent = '⚡ Searching codebase vectors...';

  // Add temporary assistant placeholder
  const botBubble = addBotMessage('Thinking and tracing codebase flow...');

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
      throw new Error(err.detail || 'Failed to generate answer');
    }

    const data = await res.json();

    // Update Chat History
    state.chatHistory.push({ role: 'user', content: query });
    state.chatHistory.push({ role: 'assistant', content: data.answer });

    // Format Markdown and replace file citations [path:start-end] with clickable links
    let formattedAnswer = data.answer;
    formattedAnswer = formattedAnswer.replace(/\[([a-zA-Z0-9_\-./\\]+):(\d+)-(\d+)\]/g, (match, rawPath, start, end) => {
      const cleanPath = rawPath.replace(/\\/g, '/');
      return `<button class="citation-link" onclick="window.openFileInViewer('${cleanPath}', ${start}, ${end})"><i data-lucide="file-text" class="w-3 h-3"></i> ${cleanPath}:${start}-${end}</button>`;
    });

    botBubble.querySelector('.markdown-body').innerHTML = marked.parse(formattedAnswer);

    // Render any nested mermaid blocks in chat
    const mermaidNodes = botBubble.querySelectorAll('.language-mermaid');
    for (const node of mermaidNodes) {
      let code = node.textContent.trim();
      code = code.replace(/^```mermaid\s*/i, '').replace(/```$/i, '').trim();
      const container = document.createElement('div');
      container.className = 'my-3 p-2 bg-dark-950/80 rounded border border-dark-700 flex justify-center';
      try {
        const renderId = 'mermaid-chat-' + Math.floor(Math.random() * 10000);
        const { svg } = await mermaid.render(renderId, code);
        container.innerHTML = svg;
      } catch (e) {
        container.innerHTML = `<pre class="text-xs text-slate-300 font-mono">${code}</pre>`;
      }
      node.parentElement.replaceWith(container);
    }

    elements.retrievalStatus.textContent = `${data.citations?.length || 0} files cited (${data.provider})`;

  } catch (err) {
    botBubble.querySelector('.markdown-body').innerHTML = `<p class="text-rose-400">❌ Error: ${err.message}</p>`;
    elements.retrievalStatus.textContent = 'Error during query';
  } finally {
    if (window.lucide) lucide.createIcons();
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  }
}

function addUserMessage(text) {
  const msg = document.createElement('div');
  msg.className = 'flex items-start space-x-2.5 justify-end';
  msg.innerHTML = `
    <div class="bg-indigo-600 text-white rounded-xl rounded-tr-none p-3 text-xs leading-relaxed max-w-[85%] shadow-md">
      ${text}
    </div>
    <div class="w-7 h-7 rounded-lg bg-indigo-500 flex items-center justify-center shrink-0">
      <i data-lucide="user" class="w-4 h-4 text-white"></i>
    </div>
  `;
  elements.chatMessages.appendChild(msg);
  if (window.lucide) lucide.createIcons();
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function addBotMessage(text) {
  const msg = document.createElement('div');
  msg.className = 'flex items-start space-x-2.5';
  msg.innerHTML = `
    <div class="w-7 h-7 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center shrink-0">
      <i data-lucide="bot" class="w-4 h-4 text-indigo-400"></i>
    </div>
    <div class="bg-dark-800 border border-dark-700 rounded-xl rounded-tl-none p-3.5 text-slate-200 leading-relaxed max-w-[90%] space-y-2">
      <div class="markdown-body">${marked.parse(text)}</div>
    </div>
  `;
  elements.chatMessages.appendChild(msg);
  if (window.lucide) lucide.createIcons();
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  return msg;
}

function showLoading(title, subtitle) {
  elements.loadingTitle.textContent = title;
  elements.loadingSubtitle.textContent = subtitle;
  elements.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
  elements.loadingOverlay.classList.add('hidden');
}

// Copy Code Button
elements.copyCodeBtn.addEventListener('click', () => {
  const code = elements.codeViewerBlock.textContent;
  navigator.clipboard.writeText(code);
  elements.copyCodeBtn.innerHTML = '<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i><span class="text-emerald-400">Copied!</span>';
  if (window.lucide) lucide.createIcons();
  setTimeout(() => {
    elements.copyCodeBtn.innerHTML = '<i data-lucide="copy" class="w-3 h-3"></i><span>Copy</span>';
    if (window.lucide) lucide.createIcons();
  }, 2000);
});

// Event Listeners
elements.analyzeBtn.addEventListener('click', () => {
  const url = elements.repoInput.value.trim();
  if (!url) {
    alert('Please enter a GitHub repository URL or choose a sample.');
    return;
  }
  analyzeRepository({ repo_url: url });
});

elements.sampleSelect.addEventListener('change', (e) => {
  const sampleKey = e.target.value;
  if (sampleKey) {
    analyzeRepository({ sample_key: sampleKey });
    elements.sampleSelect.value = "";
  }
});

elements.treeSearchInput.addEventListener('input', (e) => {
  state.searchQuery = e.target.value;
  renderFileTree();
});

document.querySelectorAll('.mod-filter').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mod-filter').forEach((b) => {
      b.classList.remove('active', 'bg-indigo-600', 'text-white');
      b.classList.add('bg-dark-800', 'text-slate-400');
    });
    btn.classList.add('active', 'bg-indigo-600', 'text-white');
    btn.classList.remove('bg-dark-800', 'text-slate-400');
    state.activeFilter = btn.dataset.mod;
    renderFileTree();
  });
});

elements.tabArchBtn.addEventListener('click', () => switchTab('arch'));
elements.tabCodeBtn.addEventListener('click', () => switchTab('code'));

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

elements.clearChatBtn.addEventListener('click', () => {
  state.chatHistory = [];
  elements.chatMessages.innerHTML = '';
  addBotMessage('Conversation cleared. Ask a new question about the codebase!');
});

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();
  checkSystemStatus();
});
