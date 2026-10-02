(() => {
  const dialog = document.getElementById('latex-picker');
  const editor = document.getElementById('question-editor');
  const catalog = window.LATEX_CATALOG;
  if (!dialog || !editor || !Array.isArray(catalog)) return;
  const search = document.getElementById('latex-search');
  const tabs = dialog.querySelector('.latex-tabs');
  const results = dialog.querySelector('.latex-results');
  const normalize = text => String(text).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  let activeField = null;
  let selectionStart = 0;
  let selectionEnd = 0;
  let currentGroup = 'Tất cả';
  let searchTimer;

  function renderResults() {
    results.replaceChildren();
    const terms = normalize(search.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    for (const group of catalog) {
      if (currentGroup !== 'Tất cả' && currentGroup !== group.name) continue;
      const matches = group.items.filter(([label, tex]) =>
        terms.every(term => normalize(`${group.name} ${label} ${tex}`).includes(term)));
      if (!matches.length) continue;
      const section = document.createElement('section');
      section.className = 'latex-group';
      const heading = document.createElement('h3');
      heading.textContent = group.name;
      section.appendChild(heading);
      const grid = document.createElement('div');
      grid.className = 'latex-items';
      for (const [label, tex, display = false] of matches) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'latex-item';
        button.setAttribute('aria-label', `Chèn ${label}`);
        const title = document.createElement('strong');
        title.textContent = label;
        const preview = document.createElement('span');
        preview.className = 'latex-render';
        try {
          katex.render(tex, preview, {displayMode: display, throwOnError: true, trust: false});
        } catch (_) {
          preview.textContent = tex;
        }
        const code = document.createElement('code');
        code.textContent = tex;
        button.append(title, preview, code);
        button.addEventListener('click', () => insert(tex, display));
        grid.appendChild(button);
        count++;
      }
      section.appendChild(grid);
      results.appendChild(section);
    }
    if (!count) {
      const empty = document.createElement('p');
      empty.textContent = 'Không tìm thấy công thức. Bạn vẫn có thể gõ LaTeX trực tiếp vào ô đang soạn.';
      results.appendChild(empty);
    }
  }

  function renderTabs() {
    tabs.replaceChildren();
    for (const group of ['Tất cả', ...catalog.map(item => item.name)]) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `button ghost${currentGroup === group ? ' selected' : ''}`;
      button.textContent = group;
      button.addEventListener('click', () => {
        currentGroup = group;
        search.value = '';
        renderTabs();
        renderResults();
      });
      tabs.appendChild(button);
    }
  }

  function insert(tex, display) {
    const field = activeField;
    if (!field || !field.isConnected) { dialog.close(); return; }
    const snippet = display ? `\\[${tex}\\]` : `\\(${tex}\\)`;
    dialog.close();
    field.focus();
    field.setRangeText(snippet, selectionStart, selectionEnd, 'end');
    field.dispatchEvent(new Event('input', {bubbles: true}));
  }

  editor.addEventListener('click', event => {
    const button = event.target.closest('.open-formula');
    if (!button || !editor.contains(button)) return;
    const card = button.closest('.question-editor');
    activeField = button.closest('.latex-field')?.querySelector('input,textarea') || card.querySelector('.question-prompt');
    selectionStart = activeField.selectionStart ?? activeField.value.length;
    selectionEnd = activeField.selectionEnd ?? selectionStart;
    currentGroup = 'Tất cả';
    search.value = '';
    renderTabs();
    renderResults();
    dialog.showModal();
    search.focus();
  });
  dialog.querySelector('.latex-close').addEventListener('click', () => dialog.close());
  search.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(renderResults, 120);
  });
})();
