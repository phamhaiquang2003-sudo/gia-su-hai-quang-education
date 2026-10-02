// Interactions for the public, fictional-data GitHub Pages preview only.
(() => {
  const banner = document.querySelector('.preview-bar');
  if (!banner) return;
  const config = JSON.parse(document.getElementById('preview-config').textContent);
  const status = document.getElementById('preview-status');
  const inDemo = location.pathname.includes('/demo/');
  const page = name => `${inDemo ? '' : 'demo/'}${name}.html`;
  const home = inDemo ? '../index.html' : 'index.html';
  const attemptKey = 'hq-pages-attempt-v1';
  const resultKey = 'hq-pages-result-v1';
  const read = key => { try { return JSON.parse(sessionStorage.getItem(key)); } catch (_) { return null; } };
  const write = (key, value) => { try { sessionStorage.setItem(key, JSON.stringify(value)); } catch (_) {} };
  const remove = key => { try { sessionStorage.removeItem(key); } catch (_) {} };
  function notify(text) {
    status.hidden = false;
    status.textContent = text;
    status.scrollIntoView({behavior: 'smooth', block: 'nearest'});
  }

  const password = document.querySelector('input[name=password]');
  if (password) {
    password.type = 'text';
    password.value = 'DEMO-GV';
    password.autocomplete = 'off';
    password.setAttribute('aria-label', 'Mật khẩu mẫu DEMO-GV; không nhập mật khẩu thật');
    const hint = document.createElement('p');
    hint.className = 'hint';
    hint.textContent = 'Bấm Đăng nhập để xem giao diện giáo viên. Không nhập mật khẩu thật vào bản demo.';
    password.closest('label').after(hint);
  }
  const code = document.querySelector('input[name=code]');
  if (code) code.value = 'DEMO-HS';
  document.querySelectorAll('form[onsubmit]').forEach(form => form.removeAttribute('onsubmit'));

  function normalizeShort(text) {
    text = text.normalize('NFKC').trim().toLowerCase().replace(/\s+/g, ' ');
    return /^[+-]?\d+(?:[.,]\d+)?$/.test(text) ? String(Number(text.replace(',', '.'))) : text;
  }

  function grade(values) {
    let score = 0;
    const review = config.grading.map((question, index) => {
      const chosen = values[index];
      let right, awarded, chosenText, correctText;
      if (question.type === 'true_false') {
        const count = question.correct.filter((answer, i) => answer === chosen[i]).length;
        awarded = [0, 0.1, 0.25, 0.5, 1][count];
        right = count === 4;
        chosenText = chosen.map((answer, i) => `${'abcd'[i]}. ${answer || '—'}`).join(', ');
        correctText = question.correct.map((answer, i) => `${'abcd'[i]}. ${answer}`).join(', ');
      } else {
        right = question.type === 'mcq' ? chosen === question.correct :
          Boolean(chosen.trim()) && question.correct.some(answer => normalizeShort(answer) === normalizeShort(chosen));
        awarded = right ? question.points : 0;
        chosenText = chosen || '—';
        correctText = Array.isArray(question.correct) ? question.correct.join('; ') : question.correct;
      }
      score += awarded;
      return {number: index + 1, chosen: chosenText, correct: correctText, awarded, right, max: question.points};
    });
    return {score: Math.round(score * 100) / 100, review};
  }

  const exam = document.getElementById('exam-form');
  let attempt, submitted = false, timer;
  function examValues() {
    const data = new FormData(exam);
    return config.grading.map((question, i) => question.type === 'true_false' ?
      question.correct.map((_, j) => data.get(`q${i + 1}_${j}`) || '') : data.get(`q${i + 1}`) || '');
  }
  function saveExam() {
    if (submitted) return;
    attempt.values = examValues();
    write(attemptKey, attempt);
    const count = attempt.values.filter(value => Array.isArray(value) ? value.some(Boolean) : value.trim()).length;
    document.getElementById('answered-count').textContent = count;
    document.getElementById('progress-fill').style.width = `${100 * count / config.grading.length}%`;
  }
  function submitExam() {
    if (submitted) return;
    saveExam();
    submitted = true;
    clearInterval(timer);
    write(resultKey, grade(attempt.values));
    remove(attemptKey);
    location.href = page('ket-qua');
  }
  if (exam) {
    attempt = read(attemptKey);
    if (!attempt || !Array.isArray(attempt.values) || attempt.values.length !== config.grading.length || !Number.isFinite(attempt.end)) {
      attempt = {end: Date.now() + 900000, values: ['', ['', '', '', ''], '']};
    }
    for (const [i, value] of attempt.values.entries()) {
      if (Array.isArray(value)) {
        value.forEach((answer, j) => {
          const field = exam.querySelector(`input[name="q${i + 1}_${j}"][value="${answer}"]`);
          if (field) field.checked = true;
        });
      } else if (config.grading[i].type === 'mcq') {
        const field = exam.querySelector(`input[name="q${i + 1}"][value="${value}"]`);
        if (field) field.checked = true;
      } else exam.elements.namedItem(`q${i + 1}`).value = value;
    }
    exam.addEventListener('input', saveExam);
    exam.addEventListener('change', saveExam);
    const tick = () => {
      const left = Math.max(0, Math.ceil((attempt.end - Date.now()) / 1000));
      document.getElementById('timer-text').textContent = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`;
      document.getElementById('countdown').classList.toggle('urgent', left <= 60);
      if (!left) submitExam();
    };
    saveExam();
    timer = setInterval(tick, 300);
    tick();
  }

  const reviewGrid = document.querySelector('.review-grid');
  if (reviewGrid) {
    const result = read(resultKey);
    if (result && Array.isArray(result.review) && result.review.length === config.grading.length) {
      document.querySelector('.score-highlight strong').textContent = `${result.score}/${config.total}`;
      reviewGrid.replaceChildren();
      for (const item of result.review) {
        const row = document.createElement('div');
        row.className = `review-item ${item.right ? 'right' : 'wrong'}`;
        for (const [tag, text] of [['strong', `Câu ${item.number}`], ['span', `Em chọn ${item.chosen}`],
                                  ['span', `Đáp án ${item.correct}`], ['span', `${item.awarded} / ${item.max} điểm`]]) {
          const field = document.createElement(tag);
          field.textContent = text;
          row.appendChild(field);
        }
        reviewGrid.appendChild(row);
      }
      window.renderQuestionMath?.(reviewGrid);
    }
    const restart = document.createElement('a');
    restart.className = 'button ghost demo-result-reset';
    restart.href = page('lam-bai');
    restart.textContent = 'Làm lại đề mẫu →';
    restart.addEventListener('click', () => { remove(attemptKey); remove(resultKey); });
    document.querySelector('.result-card').appendChild(restart);
  }

  document.addEventListener('submit', event => {
    event.preventDefault();
    const form = event.target;
    if (form === exam) { submitExam(); return; }
    if (form.querySelector('[name=password]')) { location.href = page('giao-vien'); return; }
    if (form.querySelector('[name=code]')) { location.href = home; return; }
    if (form.action.endsWith('/lam-bai.html')) { location.href = page('lam-bai'); return; }
    if (form.classList.contains('inline')) { location.href = page('hoc-sinh'); return; }
    if (form.id === 'quiz-editor') {
      notify('Đã xem trước đề bạn vừa soạn. Đây là bản demo giao diện: đề chưa được đăng hoặc lưu vào một lớp học thật.');
      return;
    }
    if (form.querySelector('[name=name]')) {
      notify(form.closest('.panel')?.querySelector('h2')?.textContent.includes('học sinh') ?
        'Thao tác mẫu: mã minh họa là DEMO-HS. Bản demo không tạo tài khoản học sinh thật.' :
        'Bạn đã thử biểu mẫu tạo nhóm. Bản demo chưa lưu nhóm lớp thật.');
      return;
    }
    notify('Bạn đang xem giao diện quản lý mẫu. Bản demo chưa lưu thao tác quản lý này; dữ liệu minh họa vẫn giữ nguyên.');
  });

  document.querySelectorAll('a').forEach(link => {
    if (link.textContent.includes('Tải CSV')) link.addEventListener('click', event => {
      event.preventDefault();
      const content = `\uFEFFHọc sinh,Nhóm,Điểm,Tổng điểm\r\nHọc sinh mẫu A,Lớp minh họa,${config.exampleScore},${config.total}\r\n`;
      const url = URL.createObjectURL(new Blob([content], {type: 'text/csv;charset=utf-8'}));
      const download = document.createElement('a');
      download.href = url;
      download.download = 'ket-qua-minh-hoa.csv';
      download.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  });
})();
