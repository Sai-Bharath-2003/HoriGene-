/* dna.js — animated DNA double helix on canvas */
(function () {
  const canvas = document.getElementById('dnaCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let W, H, animId;
  const STRANDS = 3;       // number of helices across screen
  const SPEED   = 0.4;

  function resize() {
    W = canvas.width  = canvas.offsetWidth;
    H = canvas.height = canvas.offsetHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  // Color themes per helix
  const themes = [
    { a: '#00d4aa', b: '#0077ff' },
    { a: '#0077ff', b: '#7c5cbf' },
    { a: '#00d4aa', b: '#00a885' },
  ];

  let t = 0;

  function drawHelix(xCenter, theme, phase) {
    const amplitude = 60;
    const period    = 180;   // px per full cycle
    const nodes     = 8;     // dots per cycle

    // Draw back-strand (behind)
    for (let y = -period; y < H + period; y += 2) {
      const angle  = (y / period) * Math.PI * 2 + phase + t;
      const x1     = xCenter + Math.sin(angle) * amplitude;
      const x2     = xCenter - Math.sin(angle) * amplitude;
      const depth  = Math.cos(angle);           // -1 to 1
      const front  = depth > 0;

      const alpha  = 0.15 + Math.abs(depth) * 0.25;

      if (!front) {
        ctx.beginPath();
        ctx.arc(x1, y, 1.5, 0, Math.PI * 2);
        ctx.fillStyle = hexAlpha(theme.a, alpha * 0.7);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(x2, y, 1.5, 0, Math.PI * 2);
        ctx.fillStyle = hexAlpha(theme.b, alpha * 0.7);
        ctx.fill();
      }
    }

    // Rungs (back)
    const rungCount = Math.ceil(H / period * nodes) + 2;
    for (let i = -1; i < rungCount; i++) {
      const y     = (i / nodes) * period + ((phase * period) / (Math.PI * 2)) + (t / (Math.PI * 2)) * period;
      const yMod  = ((y % H) + H) % H - period / 2;
      const angle = (yMod / period) * Math.PI * 2 + phase + t;
      const x1    = xCenter + Math.sin(angle) * amplitude;
      const x2    = xCenter - Math.sin(angle) * amplitude;
      const depth = Math.cos(angle);
      const alpha = 0.06 + Math.abs(depth) * 0.08;

      if (depth <= 0) {
        ctx.beginPath();
        ctx.moveTo(x1, yMod + period / 2);
        ctx.lineTo(x2, yMod + period / 2);
        ctx.strokeStyle = hexAlpha('#ffffff', alpha);
        ctx.lineWidth   = 1;
        ctx.stroke();
      }
    }

    // Draw front-strand (in front)
    for (let y = -period; y < H + period; y += 2) {
      const angle  = (y / period) * Math.PI * 2 + phase + t;
      const x1     = xCenter + Math.sin(angle) * amplitude;
      const x2     = xCenter - Math.sin(angle) * amplitude;
      const depth  = Math.cos(angle);
      const front  = depth > 0;
      const alpha  = 0.15 + Math.abs(depth) * 0.35;

      if (front) {
        ctx.beginPath();
        ctx.arc(x1, y, 2, 0, Math.PI * 2);
        ctx.fillStyle = hexAlpha(theme.a, alpha);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(x2, y, 2, 0, Math.PI * 2);
        ctx.fillStyle = hexAlpha(theme.b, alpha);
        ctx.fill();
      }
    }

    // Rungs (front)
    for (let i = -1; i < rungCount; i++) {
      const y     = (i / nodes) * period + ((phase * period) / (Math.PI * 2)) + (t / (Math.PI * 2)) * period;
      const yMod  = ((y % H) + H) % H - period / 2;
      const angle = (yMod / period) * Math.PI * 2 + phase + t;
      const x1    = xCenter + Math.sin(angle) * amplitude;
      const x2    = xCenter - Math.sin(angle) * amplitude;
      const depth = Math.cos(angle);
      const alpha = 0.08 + Math.abs(depth) * 0.12;

      if (depth > 0) {
        ctx.beginPath();
        ctx.moveTo(x1, yMod + period / 2);
        ctx.lineTo(x2, yMod + period / 2);
        ctx.strokeStyle = hexAlpha('#ffffff', alpha);
        ctx.lineWidth   = 1.5;
        ctx.stroke();

        // node dots at rung ends
        ctx.beginPath();
        ctx.arc(x1, yMod + period / 2, 3, 0, Math.PI * 2);
        ctx.fillStyle = hexAlpha(theme.a, alpha + 0.15);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(x2, yMod + period / 2, 3, 0, Math.PI * 2);
        ctx.fillStyle = hexAlpha(theme.b, alpha + 0.15);
        ctx.fill();
      }
    }
  }

  function frame() {
    ctx.clearRect(0, 0, W, H);
    t += 0.008 * SPEED;

    const spacing = W / (STRANDS + 1);
    for (let i = 0; i < STRANDS; i++) {
      drawHelix(spacing * (i + 1), themes[i % themes.length], (i * Math.PI * 2) / STRANDS);
    }

    animId = requestAnimationFrame(frame);
  }
  frame();

  // ─── Floating particles ─────────────────────────────────────────────────
  const particleWrap = document.getElementById('particles');
  if (particleWrap) {
    const COUNT = 25;
    for (let i = 0; i < COUNT; i++) {
      const p = document.createElement('div');
      p.className = 'particle';
      const size = 2 + Math.random() * 4;
      const left = Math.random() * 100;
      const dur  = 8 + Math.random() * 12;
      const del  = Math.random() * -15;
      p.style.cssText = `
        width:${size}px; height:${size}px;
        left:${left}%;
        animation-duration:${dur}s;
        animation-delay:${del}s;
        background: ${Math.random() > 0.5 ? '#00d4aa' : '#0077ff'};
      `;
      particleWrap.appendChild(p);
    }
  }

  // helper: hex color + alpha
  function hexAlpha(hex, a) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${a})`;
  }
})();
