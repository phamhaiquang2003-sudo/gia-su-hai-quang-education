(() => {
  const form = document.getElementById('exam-form');
  const clock = document.getElementById('countdown');
  if (!form || !clock) return;
  const display = document.getElementById('timer-text');
  const progress = document.getElementById('progress-fill');
  const totalAnswered = document.getElementById('answered-count');
  const end = Date.now() + Number(clock.dataset.remaining) * 1000;
  const count = Number(form.dataset.questionCount);
  let submitted = false;
  let timeout;

  function updateProgress() {
    let answered = 0;
    for (let i = 1; i <= count; i++) {
      const fields = [...form.elements].filter(el => el.name === `q${i}` || el.name.startsWith(`q${i}_`));
      if (fields.some(el => el.type === 'radio' ? el.checked : el.value.trim())) answered++;
    }
    totalAnswered.textContent = answered;
    progress.style.width = `${100 * answered / count}%`;
  }

  function save() {
    if (submitted) return;
    const payload = new FormData(form);
    fetch(form.dataset.saveUrl, {method: 'POST', body: payload, credentials: 'same-origin', keepalive: true})
      .catch(() => {});
  }
  form.addEventListener('change', () => { updateProgress(); save(); });
  form.addEventListener('input', () => {
    updateProgress();
    clearTimeout(timeout);
    timeout = setTimeout(save, 600);
  });
  form.addEventListener('submit', () => {
    submitted = true;
    clearTimeout(timeout);
    document.getElementById('submit-button').disabled = true;
  });

  function tick() {
    if (submitted) return;
    const left = Math.max(0, Math.ceil((end - Date.now()) / 1000));
    display.textContent = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`;
    clock.classList.toggle('urgent', left <= 60);
    if (left === 0) {
      submitted = true;
      clearTimeout(timeout);
      document.getElementById('auto-submit').value = '1';
      form.submit();
    }
  }
  updateProgress();
  tick();
  setInterval(tick, 300);
})();
