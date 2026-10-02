(() => {
  const grid = document.getElementById('catalog-grid');
  if (!grid) return;
  const cards = [...grid.querySelectorAll('.catalog-card')];
  const subjectLinks = [...document.querySelectorAll('[data-subject-link]')];
  const search = document.getElementById('catalog-search');
  const sort = document.getElementById('catalog-sort');
  const count = document.getElementById('catalog-count');
  const empty = document.getElementById('catalog-empty');
  const sidebar = document.getElementById('catalog-sidebar');
  const toggle = document.querySelector('.filter-toggle');
  const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();
  const validSubjects = new Set(subjectLinks.map(link => link.dataset.subjectLink));
  let subject = 'vat-ly';

  function applyFilters() {
    const terms = normalize(search.value.trim()).split(/\s+/).filter(Boolean);
    const categories = [...document.querySelectorAll('[name=catalog-category]:checked')].map(field => field.value);
    const fee = document.querySelector('[name=catalog-fee]:checked').value;
    const visible = cards.filter(card => {
      const tags = card.dataset.category.split(' ');
      const inSubject = subject === 'hsa' || subject === 'thpt' ? tags.includes(subject) : card.dataset.subject === subject;
      const inCategory = !categories.length || categories.some(category => tags.includes(category));
      const price = Number(card.dataset.price);
      const inFee = fee === 'all' || (fee === 'free' ? price === 0 : price > 0);
      const inSearch = terms.every(term => normalize(card.dataset.title).includes(term));
      const matches = inSubject && inCategory && inFee && inSearch;
      card.hidden = !matches;
      return matches;
    });
    const comparators = {
      newest: (a, b) => Number(b.dataset.date) - Number(a.dataset.date),
      popular: (a, b) => Number(b.dataset.popularity) - Number(a.dataset.popularity),
      price: (a, b) => Number(a.dataset.price) - Number(b.dataset.price),
      duration: (a, b) => Number(a.dataset.duration) - Number(b.dataset.duration)
    };
    visible.sort(comparators[sort.value] || comparators.newest).forEach(card => grid.appendChild(card));
    count.textContent = `Hiển thị ${visible.length} bài kiểm tra`;
    empty.hidden = visible.length > 0;
  }

  function resetFilters() {
    search.value = '';
    sort.value = 'newest';
    document.querySelectorAll('[name=catalog-category]').forEach(field => { field.checked = false; });
    document.querySelector('[name=catalog-fee][value=all]').checked = true;
    applyFilters();
  }

  function setSubject(value) {
    subject = validSubjects.has(value) ? value : 'vat-ly';
    subjectLinks.forEach(link => {
      if (link.dataset.subjectLink === subject) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    const label = subjectLinks.find(link => link.dataset.subjectLink === subject).textContent.trim();
    document.getElementById('catalog-title').textContent = subject === 'hsa' ?
      'Tổng hợp các đề thi đánh giá năng lực HSA/TSA' : subject === 'thpt' ?
      'Tổng hợp các đề thi thử tốt nghiệp THPT' : `Tổng hợp các bài kiểm tra, đề thi môn ${label}`;
    document.title = `Thư viện ${label} · HQ Education`;
    resetFilters();
  }

  subjectLinks.forEach(link => link.addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    const url = new URL(location.href);
    url.searchParams.set('mon', link.dataset.subjectLink);
    history.pushState(null, '', url);
    setSubject(link.dataset.subjectLink);
  }));
  window.addEventListener('popstate', () => setSubject(new URLSearchParams(location.search).get('mon')));
  search.addEventListener('input', applyFilters);
  sort.addEventListener('change', applyFilters);
  document.querySelectorAll('[name=catalog-category], [name=catalog-fee]').forEach(field => field.addEventListener('change', applyFilters));
  document.getElementById('reset-filters').addEventListener('click', resetFilters);
  document.getElementById('empty-reset').addEventListener('click', resetFilters);
  toggle.addEventListener('click', () => {
    const opened = sidebar.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(opened));
    if (opened) search.focus();
  });
  setSubject(new URLSearchParams(location.search).get('mon'));
})();
