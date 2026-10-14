'use strict';

// Local visual feedback only: no API calls, navigation to the app, or data writes.
const liveButton = document.querySelector('#live-mode');
const imageButton = document.querySelector('#image-mode');
function setMode(mode) {
  const showImages = mode === 'images';
  document.querySelectorAll('.live-surface').forEach(node => { node.hidden = showImages; });
  document.querySelectorAll('.image-surface').forEach(node => { node.hidden = !showImages; });
  liveButton.setAttribute('aria-pressed', String(!showImages));
  imageButton.setAttribute('aria-pressed', String(showImages));
  document.querySelectorAll('details[open]').forEach(node => { node.open = false; });
}
liveButton.addEventListener('click', () => setMode('live'));
imageButton.addEventListener('click', () => setMode('images'));

document.querySelectorAll('.tactile').forEach(button => {
  let releaseTimer;
  button.addEventListener('click', () => {
    window.clearTimeout(releaseTimer);
    button.classList.add('is-pressed');
    releaseTimer = window.setTimeout(() => button.classList.remove('is-pressed'), 180);
  });
  button.addEventListener('blur', () => button.classList.remove('is-pressed'));
});

const dropdowns = [...document.querySelectorAll('.dropdown')];
dropdowns.forEach(dropdown => {
  const summary = dropdown.querySelector('summary');
  dropdown.addEventListener('toggle', () => {
    summary.setAttribute('aria-expanded', String(dropdown.open));
    if (dropdown.open) dropdowns.forEach(other => { if (other !== dropdown) other.open = false; });
  });
  dropdown.querySelector('.selected-option').addEventListener('click', () => {
    dropdown.open = false;
    summary.focus();
  });
  dropdown.addEventListener('keydown', event => {
    if (event.key === 'Escape') { dropdown.open = false; summary.focus(); }
  });
});
document.addEventListener('click', event => {
  dropdowns.forEach(dropdown => { if (!dropdown.contains(event.target)) dropdown.open = false; });
});
const hero = document.querySelector('.hero');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let sparkleTimer;
function sparkle() {
  if (reducedMotion.matches || hero.classList.contains('is-sparkling')) return;
  hero.classList.add('is-sparkling');
  window.clearTimeout(sparkleTimer);
  sparkleTimer = window.setTimeout(() => hero.classList.remove('is-sparkling'), 700);
}
hero.addEventListener('pointerenter', sparkle);
hero.addEventListener('focusin', sparkle);
