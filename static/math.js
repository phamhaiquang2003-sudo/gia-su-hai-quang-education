window.renderQuestionMath = function (element) {
  if (!element || typeof renderMathInElement !== 'function') return;
  renderMathInElement(element, {
    delimiters: [
      {left: '$$', right: '$$', display: true},
      {left: '\\[', right: '\\]', display: true},
      {left: '\\(', right: '\\)', display: false},
      {left: '$', right: '$', display: false}
    ],
    throwOnError: false,
    trust: false
  });
};

document.querySelectorAll('.question-list, .review-grid').forEach(window.renderQuestionMath);
