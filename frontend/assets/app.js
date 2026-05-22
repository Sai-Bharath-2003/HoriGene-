/* app.js — shared utilities for all pages */
const API = 'http://localhost:5000';

/* ── Nav scroll effect ─────────────────────────────────────────── */
const nav = document.getElementById('nav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 40);
  }, { passive: true });
}

/* ── Hamburger menu ────────────────────────────────────────────── */
const ham = document.getElementById('hamburger');
const navLinks = document.querySelector('.nav-links');
if (ham && navLinks) {
  ham.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    ham.classList.toggle('open');
  });
}

/* ── Animated stat counters ────────────────────────────────────── */
function animateCounter(el) {
  const target = parseInt(el.dataset.target, 10);
  const dur    = 1800;
  const start  = performance.now();
  function step(now) {
    const p = Math.min((now - start) / dur, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(ease * target).toLocaleString();
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

const counterEls = document.querySelectorAll('.stat-num[data-target]');
if (counterEls.length) {
  // Use IntersectionObserver so counters run when scrolled into view
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        animateCounter(e.target);
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.5 });
  counterEls.forEach(el => obs.observe(el));
}

/* ── Scroll-reveal ─────────────────────────────────────────────── */
const revealEls = document.querySelectorAll('.family-card, .protein-card, .detail-panel, .team-card');
if (revealEls.length) {
  const revObs = new IntersectionObserver((entries) => {
    entries.forEach((e, i) => {
      if (e.isIntersecting) {
        e.target.style.transition = `opacity 0.5s ${i * 0.04}s ease, transform 0.5s ${i * 0.04}s ease`;
        e.target.style.opacity  = '1';
        e.target.style.transform = 'translateY(0)';
        revObs.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });
  revealEls.forEach(el => {
    el.style.opacity  = '0';
    el.style.transform = 'translateY(20px)';
    revObs.observe(el);
  });
}

/* ── Toast notifications ───────────────────────────────────────── */
function showToast(msg, type = 'success') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✓' : '✗'}</span> ${msg}`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

/* ── API helpers ───────────────────────────────────────────────── */
async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* ── Family tag color helper ───────────────────────────────────── */
function familyTag(fam) {
  return `<span class="protein-family-tag tag-${fam}">${fam.toUpperCase()}</span>`;
}

/* ── Expose globals ────────────────────────────────────────────── */
window.HG = { API, apiFetch, familyTag, showToast };
