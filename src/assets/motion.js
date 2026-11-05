/*
 * Pump dashboard motion engine.
 *
 * Runs inside a zero-height component iframe and drives the parent Streamlit page.
 * GLOSSARY is injected by theme.py before this file.
 *
 *   - staggered scroll reveals (GSAP)            - smooth lagging cursor ring + dot
 *   - scroll progress bar                        - cursor spotlight on cards
 *   - KPI / gauge count-up                       - button ripple
 *   - glossary pop-up for dotted terms           - sliding thumb for the page tabs
 *
 * Every listener hangs off one AbortController, so a re-run replaces the previous
 * instance cleanly. Nothing here is required for the page to work.
 */
(function () {
  'use strict';

  var P, D;
  try { P = window.parent; D = P.document; } catch (e) { return; }

  try { if (P.__pfCleanup) P.__pfCleanup(); } catch (e) {}
  try { if (P.__pfx) P.__pfx.abort(); } catch (e) {}

  var AC = new P.AbortController();
  P.__pfx = AC;
  var SIG = AC.signal;
  var PASSIVE = { signal: SIG, passive: true };

  var G = window.gsap;
  var reduce = P.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = P.matchMedia('(pointer: fine)').matches;
  var raf = function (fn) { return P.requestAnimationFrame(fn); };
  var closest = function (t, sel) { return t && t.closest ? t.closest(sel) : null; };

  var cleanups = [];
  SIG.addEventListener('abort', function () {
    cleanups.forEach(function (fn) { try { fn(); } catch (e) {} });
  });

  /* ---------------------------------------------------------- count-up */
  var ease = function (t) { return t >= 1 ? 1 : 1 - Math.pow(2, -10 * t); };

  function countUp(el) {
    if (el.dataset.pfDone) return;
    el.dataset.pfDone = '1';
    var txt = el.textContent.trim();
    var m = /^(-?)([\d,]*\.?\d+)(%?)$/.exec(txt);
    if (!m || reduce) return;
    var raw = m[2];
    var grouped = raw.indexOf(',') > -1;
    var dec = (raw.split('.')[1] || '').length;
    var to = parseFloat(raw.replace(/,/g, '')) * (m[1] ? -1 : 1);
    var dur = Math.min(1500, 750 + Math.log10(Math.abs(to) + 1) * 150);
    var t0 = null;
    var fmt = function (v) {
      return v.toLocaleString('en-US', {
        minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: grouped
      }) + m[3];
    };
    el.textContent = fmt(0);
    (function step(ts) {
      if (SIG.aborted) { el.textContent = txt; return; }
      if (t0 === null) t0 = ts;
      var k = Math.min(1, (ts - t0) / dur);
      if (k < 1) { el.textContent = fmt(to * ease(k)); raf(step); }
      else { el.textContent = txt; }
    })(P.performance.now());
  }

  /* ---------------------------------------------------------- reveals */
  var REVEAL = '.pf-kpi, [class*="st-key-panel"], [data-testid="stExpander"]';
  var NUMS = '.pf-kpi .v, .pf-gauge .num';
  var io = null;
  var queue = [];
  var flushing = false;

  function flush() {
    flushing = false;
    var batch = queue.splice(0);
    batch.sort(function (a, b) {
      var ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      return (Math.round(ra.top / 40) - Math.round(rb.top / 40)) || (ra.left - rb.left);
    });
    batch.forEach(function (el, i) {
      el.dataset.pfR = '1';
      P.setTimeout(function () { el.querySelectorAll(NUMS).forEach(countUp); }, 180 + Math.min(i * 80, 400));
      G.to(el, {
        opacity: 1, y: 0, scale: 1,
        duration: .9, delay: Math.min(i * .08, .4), ease: 'power3.out',
        clearProps: 'opacity,transform,willChange',
        overwrite: true
      });
    });
  }

  function setupReveals() {
    if (!G || reduce || !P.IntersectionObserver) return;

    io = new P.IntersectionObserver(function (items) {
      items.forEach(function (it) {
        if (!it.isIntersecting) return;
        io.unobserve(it.target);
        queue.push(it.target);
      });
      if (queue.length && !flushing) { flushing = true; raf(flush); }
    }, { threshold: 0.05, rootMargin: '0px 0px -4% 0px' });

    function scan() {
      D.querySelectorAll(REVEAL).forEach(function (el) {
        if (el.dataset.pfR) return;
        // nested panels ride along with their parent's reveal
        var host = el.parentElement ? el.parentElement.closest(REVEAL) : null;
        if (host) { el.dataset.pfR = '1'; return; }
        el.dataset.pfR = '0';
        G.set(el, { opacity: 0, y: el.classList.contains('pf-kpi') ? 22 : 30,
                    scale: el.classList.contains('pf-kpi') ? .96 : 1, willChange: 'transform, opacity' });
        io.observe(el);
      });
    }

    // anything still waiting when this instance is replaced must not stay invisible
    cleanups.push(function () {
      io.disconnect();
      D.querySelectorAll('[data-pf-r="0"]').forEach(function (el) {
        el.dataset.pfR = '';
        el.style.opacity = ''; el.style.transform = ''; el.style.willChange = '';
      });
    });

    return scan;
  }

  /* ---------------------------------------------------------- spotlight + ripple */
  var spot = null;
  var SPOT = '.pf-kpi, [class*="st-key-panel"], .pf-result';

  D.addEventListener('pointermove', function (e) {
    var t = closest(e.target, SPOT);
    if (!t) return;
    var first = !spot;
    spot = { el: t, x: e.clientX, y: e.clientY };
    if (first) raf(function () {
      if (!spot) return;
      var r = spot.el.getBoundingClientRect();
      spot.el.style.setProperty('--mx', (spot.x - r.left) + 'px');
      spot.el.style.setProperty('--my', (spot.y - r.top) + 'px');
      spot = null;
    });
  }, PASSIVE);

  D.addEventListener('pointerdown', function (e) {
    var b = closest(e.target, '.stButton > button, .stDownloadButton > button');
    if (!b || reduce) return;
    var r = b.getBoundingClientRect(), s = Math.max(r.width, r.height) * 2;
    var d = D.createElement('span');
    d.className = 'pf-ripple';
    d.style.cssText = 'width:' + s + 'px;height:' + s + 'px;left:' + (e.clientX - r.left - s / 2) +
                      'px;top:' + (e.clientY - r.top - s / 2) + 'px';
    b.appendChild(d);
    P.setTimeout(function () { d.remove(); }, 700);
  }, PASSIVE);

  /* ---------------------------------------------------------- progress bar */
  D.querySelectorAll('#pf-bar').forEach(function (n) { n.remove(); });
  var bar = D.createElement('div');
  bar.id = 'pf-bar';
  D.body.appendChild(bar);
  cleanups.push(function () { bar.remove(); });

  var barQueued = false, barEl = null;
  D.addEventListener('scroll', function (ev) {
    var main = ev.target;
    if (!main || !main.matches || !main.matches('[data-testid="stMain"], section.main, .stMain')) return;
    barEl = main;
    if (barQueued) return;
    barQueued = true;
    raf(function () {
      barQueued = false;
      var max = barEl.scrollHeight - barEl.clientHeight;
      bar.style.transform = 'scaleX(' + (max > 0 ? Math.min(1, barEl.scrollTop / max) : 0) + ')';
    });
  }, { signal: SIG, passive: true, capture: true });

  /* ---------------------------------------------------------- cursor ring */
  if (fine && !reduce) {
    D.querySelectorAll('#pf-ring, #pf-dot').forEach(function (n) { n.remove(); });
    var ring = D.createElement('div'); ring.id = 'pf-ring';
    var dot = D.createElement('div'); dot.id = 'pf-dot';
    D.body.appendChild(ring); D.body.appendChild(dot);
    cleanups.push(function () { ring.remove(); dot.remove(); });

    var tx = 0, ty = 0, rx = 0, ry = 0, running = false, shown = false;
    var HOT = 'a, button, [role="button"], [role="slider"], summary, label[data-baseweb="radio"], ' +
              '[data-testid="stRadio"] label, [data-baseweb="select"], input, .term';

    function loop() {
      if (SIG.aborted) return;
      rx += (tx - rx) * .2;
      ry += (ty - ry) * .2;
      ring.style.transform = 'translate3d(' + rx.toFixed(1) + 'px,' + ry.toFixed(1) + 'px,0)';
      if (Math.abs(tx - rx) + Math.abs(ty - ry) > .1) raf(loop);
      else running = false;
    }

    D.addEventListener('pointermove', function (e) {
      if (e.pointerType && e.pointerType !== 'mouse') return;
      tx = e.clientX; ty = e.clientY;
      dot.style.transform = 'translate3d(' + tx + 'px,' + ty + 'px,0)';
      if (!shown) { shown = true; rx = tx; ry = ty; ring.style.opacity = 1; dot.style.opacity = 1; }
      ring.classList.toggle('hot', !!closest(e.target, HOT));
      if (!running) { running = true; raf(loop); }
    }, PASSIVE);
    D.addEventListener('pointerdown', function () { ring.classList.add('down'); }, PASSIVE);
    D.addEventListener('pointerup', function () { ring.classList.remove('down'); }, PASSIVE);
    D.documentElement.addEventListener('mouseleave', function () {
      shown = false; ring.style.opacity = 0; dot.style.opacity = 0;
    }, PASSIVE);
  }

  /* ---------------------------------------------------------- glossary pop-up */
  var pop = D.getElementById('term-pop') || D.body.appendChild(D.createElement('div'));
  pop.id = 'term-pop';
  pop.setAttribute('role', 'dialog');

  function hidePop() {
    if (pop.style.display === 'none' || !pop.style.display) return;
    if (G && !reduce) {
      G.to(pop, { opacity: 0, y: 14, duration: .22, ease: 'power2.in',
                  onComplete: function () { pop.style.display = 'none'; } });
    } else { pop.style.display = 'none'; }
  }

  function showPop(key) {
    var g = (typeof GLOSSARY !== 'undefined') ? GLOSSARY[key] : null;
    if (!g) return;
    pop.innerHTML = '<button aria-label="Close">\u00d7</button><h3>' + g[1] + '</h3>' +
      '<h5>What it is</h5><p>' + g[2] + '</p><h5>What it does</h5><p>' + g[3] +
      '</p><h5>How it works</h5><p>' + g[4] + '</p><h5>Example</h5><p>' + g[5] + '</p>';
    pop.style.display = 'block';
    if (G && !reduce) {
      G.killTweensOf(pop);
      G.fromTo(pop, { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: .45, ease: 'power3.out' });
    } else { pop.style.opacity = 1; }
  }

  cleanups.push(function () { pop.style.display = 'none'; });

  D.addEventListener('click', function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    var term = t.closest('.term');
    if (term) { e.preventDefault(); e.stopPropagation(); showPop(term.dataset.term); return; }
    if (t.closest('#term-pop button') || !t.closest('#term-pop')) hidePop();
  }, { signal: SIG, capture: true });

  D.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') hidePop();
    if ((e.key === 'Enter' || e.key === ' ') && e.target && e.target.classList && e.target.classList.contains('term')) {
      e.preventDefault(); showPop(e.target.dataset.term);
    }
  }, { signal: SIG });

  /* ---------------------------------------------------------- sliding tab thumb */
  function placeThumb(group) {
    var inp = group.querySelector('input:checked');
    var opt = inp && (inp.closest('label') || inp.closest('[data-testid="stRadioOption"]'));
    if (!opt) return;
    var r = opt.getBoundingClientRect(), g = group.getBoundingClientRect();
    if (!r.width || !g.width) return;
    var s = group.style;
    s.setProperty('--tx', (r.left - g.left - group.clientLeft).toFixed(1) + 'px');
    s.setProperty('--ty', (r.top - g.top - group.clientTop).toFixed(1) + 'px');
    s.setProperty('--tw', r.width.toFixed(1) + 'px');
    s.setProperty('--th', r.height.toFixed(1) + 'px');
    if (!group.dataset.thumb) {
      group.dataset.thumb = 'on';
      // enable the slide only after the first position is painted
      raf(function () { raf(function () { group.dataset.thumb = 'live'; }); });
    }
  }
  function placeAllThumbs() {
    D.querySelectorAll('[data-testid="stRadio"] [role="radiogroup"]').forEach(placeThumb);
  }
  D.addEventListener('click', function () {
    P.setTimeout(placeAllThumbs, 0); P.setTimeout(placeAllThumbs, 120);
  }, PASSIVE);
  P.addEventListener('resize', function () { raf(placeAllThumbs); }, PASSIVE);
  if (D.fonts && D.fonts.ready) D.fonts.ready.then(function () { raf(placeAllThumbs); });

  /* ---------------------------------------------------------- one observer for the page */
  var scanReveals = setupReveals();
  var queued = false;

  function pass() {
    queued = false;
    if (scanReveals) scanReveals();
    D.querySelectorAll('.pf-kpi .v:not([data-pf-done]), .pf-gauge .num:not([data-pf-done])').forEach(function (n) {
      var host = n.closest(REVEAL);
      if (!host || host.dataset.pfR !== '0') countUp(n);   // wait for the card to be revealed
    });
    placeAllThumbs();
  }

  var mo = new P.MutationObserver(function () {
    if (!queued) { queued = true; raf(pass); }
  });
  mo.observe(D.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-checked', 'checked'] });
  cleanups.push(function () { mo.disconnect(); });

  pass();

  P.__pfCleanup = function () { try { AC.abort(); } catch (e) {} };
})();