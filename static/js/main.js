/**
 * AI Document Formatter — shared frontend utilities.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Animate score bars on results page
  document.querySelectorAll('.score-fill, .cat-bar-fill, .viol-bar').forEach(el => {
    const width = el.style.width;
    el.style.width = '0';
    requestAnimationFrame(() => {
      el.style.transition = 'width 0.8s ease';
      el.style.width = width;
    });
  });
});
