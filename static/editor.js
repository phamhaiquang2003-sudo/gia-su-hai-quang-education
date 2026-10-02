(() => {
  const form = document.getElementById('quiz-editor');
  if (!form) return;
  const list = document.getElementById('question-editor');
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pickerButton = '<button class="button ghost open-formula" type="button">∑ Công thức</button>';
  const field = (label, value = '', placeholder = '', className = '') => `<div class="latex-field"><label>${label}<input class="${className}" type="text" maxlength="${className === 'correct-short' ? 2000 : 1000}" value="${esc(value)}" placeholder="${esc(placeholder)}" required></label>${pickerButton}</div>`;
  const mathButtons = [
    ['Phân số', String.raw`\(\frac{a}{b}\)`],
    ['Căn bậc hai', String.raw`\(\sqrt{x}\)`],
    ['Lũy thừa', String.raw`\(x^2\)`],
    ['Hệ phương trình', String.raw`\[\begin{cases}x+y=3\\x-y=1\end{cases}\]`]
  ];

  function add(row = {}) {
    if (list.children.length >= 100) { alert('Tối đa 100 câu hỏi.'); return; }
    const node = document.createElement('section');
    node.className = 'question-editor panel';
    node.innerHTML = `<div class="panel-heading"><h3>Câu ${list.children.length + 1}</h3><button type="button" class="button ghost remove-question">Xóa câu</button></div>
      <div class="identity-grid"><label>Dạng câu<select class="question-type"><option value="mcq">Trắc nghiệm A–D</option><option value="true_false">Đúng / sai (4 ý, 1 điểm)</option><option value="short">Trả lời ngắn</option></select></label><label>Điểm tối đa<input class="question-points" type="number" min="0.01" max="100" step="0.01" value="${esc(row.points ?? 1)}" required></label></div>
      <label>Nội dung câu hỏi<textarea class="question-prompt" rows="4" maxlength="3000" required placeholder="Gõ hoặc dán câu hỏi; dùng \\( \\frac{a}{b} \\) cho công thức">${esc(row.prompt)}</textarea></label>
      <div class="math-toolbar">${pickerButton}${mathButtons.map(([label, snippet]) => `<button class="button ghost insert-math" type="button" data-snippet="${esc(snippet)}">${label}</button>`).join('')}</div>
      <label>Hình minh họa (tối đa 3 ảnh, mỗi ảnh 3 MB) <input class="question-images" type="file" accept="image/png,image/jpeg,image/webp,image/gif" multiple></label>
      <div class="paste-image-row"><button class="button ghost paste-question-image" type="button">Dán ảnh đã sao chép</button><span class="hint">Hoặc đặt con trỏ trong ô “Nội dung câu hỏi” và nhấn Ctrl+V. Ảnh sẽ hiện bên dưới ô nhập.</span></div>
      <p class="image-paste-status hint" role="status" aria-live="polite"></p>
      <div class="image-previews"></div><button class="button ghost clear-images" type="button" hidden>Bỏ ảnh đã chọn</button>
      <div class="question-specific"></div>
      <details class="question-preview-wrap"><summary>Xem trước công thức và nội dung</summary><div class="question-preview math-content"></div></details>`;
    list.appendChild(node);
    const type = node.querySelector('.question-type');
    const points = node.querySelector('.question-points');
    const prompt = node.querySelector('.question-prompt');
    const specific = node.querySelector('.question-specific');
    const imagesInput = node.querySelector('.question-images');
    const previews = node.querySelector('.image-previews');
    const pasteStatus = node.querySelector('.image-paste-status');
    let objectUrls = [];
    let previewTimer;
    type.value = row.type || 'mcq';

    function updateImagePreviews() {
      objectUrls.forEach(URL.revokeObjectURL);
      objectUrls = [];
      previews.replaceChildren();
      const files = [...imagesInput.files];
      if (files.length > 3) {
        alert('Mỗi câu chỉ có tối đa 3 hình. Hãy chọn lại.');
        imagesInput.value = '';
        node.querySelector('.clear-images').hidden = true;
        return;
      }
      if (files.some(file => file.size > 3 * 1024 * 1024)) {
        alert('Mỗi hình tối đa 3 MB. Hãy chọn lại.');
        imagesInput.value = '';
        node.querySelector('.clear-images').hidden = true;
        return;
      }
      for (const file of files) {
        const url = URL.createObjectURL(file);
        objectUrls.push(url);
        const img = document.createElement('img');
        img.src = url;
        img.alt = `Hình minh họa: ${file.name}`;
        previews.appendChild(img);
      }
      node.querySelector('.clear-images').hidden = files.length === 0;
    }

    const imageTypes = {'image/png': '.png', 'image/jpeg': '.jpg', 'image/webp': '.webp', 'image/gif': '.gif'};

    async function copiedImages(files, htmlText) {
      const direct = files.filter(file => file && imageTypes[file.type]);
      if (direct.length) return direct;
      if (!htmlText) return [];
      const html = new DOMParser().parseFromString(htmlText, 'text/html');
      const sources = [...html.querySelectorAll('img[src]')].map(image => image.getAttribute('src'));
      const images = [];
      for (const source of sources) {
        if (!/^data:image\/(?:png|jpeg|webp|gif);base64,/i.test(source) || source.length > 4 * 1024 * 1024 + 100) continue;
        try { images.push(await (await fetch(source)).blob()); } catch (_) { /* invalid clipboard image */ }
      }
      return images;
    }

    function attachImages(blobs) {
      if (!blobs.length) return false;
      if (imagesInput.files.length + blobs.length > 3) {
        pasteStatus.textContent = 'Mỗi câu chỉ nhận tối đa 3 ảnh. Hãy bỏ bớt ảnh trước khi dán.';
        return false;
      }
      if (blobs.some(blob => !imageTypes[blob.type] || blob.size > 3 * 1024 * 1024)) {
        pasteStatus.textContent = 'Chỉ nhận ảnh PNG, JPG, WebP hoặc GIF, tối đa 3 MB mỗi ảnh.';
        return false;
      }
      const files = new DataTransfer();
      [...imagesInput.files].forEach(file => files.items.add(file));
      blobs.forEach((blob, index) => files.items.add(new File([blob],
        `anh-cau-hoi-${Date.now()}-${index}${imageTypes[blob.type]}`, {type: blob.type})));
      imagesInput.files = files.files;
      updateImagePreviews();
      pasteStatus.textContent = `Đã thêm ${blobs.length} ảnh vào câu hỏi. Ảnh hiện bên dưới nội dung khi học sinh làm bài.`;
      return true;
    }

    async function pasteFromButton() {
      if (!navigator.clipboard?.read) {
        pasteStatus.textContent = 'Trình duyệt chưa cho phép đọc clipboard. Hãy nhấp vào ô Nội dung câu hỏi và nhấn Ctrl+V.';
        prompt.focus();
        return;
      }
      try {
        const items = await navigator.clipboard.read();
        const files = [], htmlParts = [];
        for (const item of items) {
          const imageType = item.types.find(type => imageTypes[type]);
          if (imageType) files.push(await item.getType(imageType));
          else if (item.types.includes('text/html')) htmlParts.push(await (await item.getType('text/html')).text());
        }
        const found = await copiedImages(files, htmlParts.join(''));
        if (!found.length) {
          pasteStatus.textContent = 'Không đọc được ảnh từ clipboard. Hãy chụp phần ảnh bằng Win+Shift+S rồi Ctrl+V, hoặc chọn tệp ảnh ở trên.';
          return;
        }
        attachImages(found);
      } catch (_) {
        pasteStatus.textContent = 'Trình duyệt không cho đọc clipboard. Hãy nhấp vào ô Nội dung câu hỏi và nhấn Ctrl+V.';
        prompt.focus();
      }
    }

    function updatePreview() {
      const preview = node.querySelector('.question-preview');
      preview.replaceChildren();
      const text = document.createElement('div');
      text.textContent = prompt.value || '(Chưa nhập câu hỏi)';
      preview.appendChild(text);
      if (type.value !== 'short') {
        const items = [...specific.querySelectorAll('input[type="text"]')];
        items.forEach((input, index) => {
          if (!input.value.trim()) return;
          const line = document.createElement('div');
          line.textContent = `${type.value === 'mcq' ? 'ABCD'[index] : 'abcd'[index]}. ${input.value}`;
          preview.appendChild(line);
        });
      } else {
        const correct = specific.querySelector('.correct-short')?.value.trim();
        if (correct) {
          const teacherOnly = document.createElement('div');
          teacherOnly.className = 'latex-answer-preview';
          teacherOnly.textContent = `Đáp án mẫu (chỉ giáo viên): ${correct}`;
          preview.appendChild(teacherOnly);
        }
      }
      if (window.renderQuestionMath) window.renderQuestionMath(preview);
    }

    function render() {
      const kind = type.value;
      points.disabled = kind === 'true_false';
      if (kind === 'true_false') points.value = '1';
      if (kind === 'mcq') {
        specific.innerHTML = '<p>Nhập bốn phương án và chọn đáp án đúng.</p>' +
          'ABCD'.split('').map((key, i) => field(`Phương án ${key}`, row.options?.[i] || '')).join('') +
          `<label>Đáp án đúng<select class="correct-mcq">${'ABCD'.split('').map(k => `<option value="${k}" ${row.correct === k ? 'selected' : ''}>${k}</option>`).join('')}</select></label>`;
      } else if (kind === 'true_false') {
        specific.innerHTML = '<p>Nhập đủ bốn ý. Đúng 1 ý: 0,1 điểm; 2 ý: 0,25; 3 ý: 0,5; 4 ý: 1 điểm.</p>' +
          Array.from({length:4}, (_, i) => `<div class="truth-edit">${field(`Ý ${'abcd'[i]}`, row.statements?.[i] || '')}<label>Đáp án<select><option value="D" ${row.correct?.[i] === 'D' ? 'selected' : ''}>Đúng</option><option value="S" ${row.correct?.[i] === 'S' ? 'selected' : ''}>Sai</option></select></label></div>`).join('');
      } else {
        specific.innerHTML = field('Đáp án đúng (phân tách bằng dấu ;)',
                                   Array.isArray(row.correct) ? row.correct.join('; ') : row.correct || '',
                                   'Ví dụ: 1/2; 0,5', 'correct-short');
      }
      updatePreview();
    }

    type.addEventListener('change', () => { row = {}; render(); });
    node.addEventListener('input', () => { clearTimeout(previewTimer); previewTimer = setTimeout(updatePreview, 180); });
    imagesInput.addEventListener('change', () => { updateImagePreviews(); pasteStatus.textContent = ''; });
    node.querySelector('.clear-images').addEventListener('click', () => { imagesInput.value = ''; updateImagePreviews(); pasteStatus.textContent = ''; });
    node.querySelector('.paste-question-image').addEventListener('click', pasteFromButton);
    prompt.addEventListener('paste', async event => {
      const clipboard = event.clipboardData;
      if (!clipboard) return;
      const files = [...clipboard.items].filter(item => item.kind === 'file').map(item => item.getAsFile()).filter(Boolean);
      const html = clipboard.getData('text/html');
      const hasImage = files.some(file => imageTypes[file.type]) || /<img\b/i.test(html);
      if (!hasImage) return; // Normal text and LaTeX paste still works.
      event.preventDefault();
      const plainText = clipboard.getData('text/plain');
      const htmlText = new DOMParser().parseFromString(html, 'text/html').body.textContent.trim();
      if (plainText.trim() && htmlText && !/^https?:\/\//i.test(plainText.trim())) {
        prompt.setRangeText(plainText, prompt.selectionStart, prompt.selectionEnd, 'end');
        prompt.dispatchEvent(new Event('input', {bubbles: true}));
      }
      const found = await copiedImages(files, html);
      if (!found.length) {
        pasteStatus.textContent = 'Ảnh sao chép không có dữ liệu mà trình duyệt đọc được. Hãy dùng Win+Shift+S rồi Ctrl+V hoặc chọn tệp ảnh.';
        return;
      }
      attachImages(found);
    });
    node.querySelectorAll('.insert-math').forEach(button => button.addEventListener('click', () => {
      const snippet = button.dataset.snippet;
      prompt.focus();
      prompt.setRangeText(snippet, prompt.selectionStart, prompt.selectionEnd, 'end');
      updatePreview();
    }));
    node.querySelector('.remove-question').addEventListener('click', () => {
      objectUrls.forEach(URL.revokeObjectURL);
      node.remove();
      [...list.children].forEach((el, i) => el.querySelector('h3').textContent = `Câu ${i+1}`);
    });
    render();
  }

  document.getElementById('add-question').addEventListener('click', () => add());
  let initial = [];
  try { initial = JSON.parse(JSON.parse(document.getElementById('quiz-initial').textContent)); } catch (_) { /* first visit */ }
  if (Array.isArray(initial) && initial.length) initial.forEach(add); else add();
  form.addEventListener('submit', event => {
    if (!list.children.length) { event.preventDefault(); alert('Hãy thêm ít nhất một câu hỏi.'); return; }
    const quiz = [...list.children].map((node, index) => {
      const kind = node.querySelector('.question-type').value;
      node.querySelector('.question-images').name = `image_${index + 1}`;
      const row = {type:kind, prompt:node.querySelector('.question-prompt').value.trim(),
                   points:kind === 'true_false' ? 1 : node.querySelector('.question-points').value};
      if (kind === 'mcq') {
        row.options = [...node.querySelectorAll('.question-specific input')].map(input => input.value.trim());
        row.correct = node.querySelector('.correct-mcq').value;
      } else if (kind === 'true_false') {
        const statements = [...node.querySelectorAll('.truth-edit')].map(el => ({text:el.querySelector('input').value.trim(), answer:el.querySelector('select').value}));
        row.statements = statements.map(el => el.text);
        row.correct = statements.map(el => el.answer);
      } else row.correct = node.querySelector('.correct-short').value;
      return row;
    });
    document.getElementById('quiz-json').value = JSON.stringify(quiz);
  });
})();
