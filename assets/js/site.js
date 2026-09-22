/* ==========================================================
   site.js — comportamiento común del sitio
   ========================================================== */
(function () {
  'use strict';

  /* ---------- Tema claro / oscuro ---------- */
  var THEME_KEY = 'rg-theme';

  function readTheme() {
    try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; }
  }
  function writeTheme(v) {
    try { localStorage.setItem(THEME_KEY, v); } catch (e) { /* modo privado */ }
  }
  function systemTheme() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function applyTheme(v) {
    document.documentElement.setAttribute('data-theme', v);
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-label', v === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro');
      btn.setAttribute('aria-pressed', String(v === 'dark'));
      var sun = btn.querySelector('[data-icon="sun"]');
      var moon = btn.querySelector('[data-icon="moon"]');
      if (sun) sun.classList.toggle('hidden', v !== 'dark');
      if (moon) moon.classList.toggle('hidden', v === 'dark');
    });
  }

  applyTheme(readTheme() || systemTheme());

  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('[data-theme-toggle]');
    if (!btn) return;
    var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    writeTheme(next);
  });

  /* ---------- Navegación móvil ---------- */
  var toggle = document.querySelector('[data-nav-toggle]');
  var panel = document.getElementById('nav-panel');
  if (toggle && panel) {
    toggle.addEventListener('click', function () {
      var open = panel.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    panel.addEventListener('click', function (ev) {
      if (ev.target.tagName === 'A') {
        panel.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ---------- Marcar el enlace de la página actual ---------- */
  var here = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav__links a, .nav__panel a').forEach(function (a) {
    var target = (a.getAttribute('href') || '').split('/').pop().split('#')[0];
    if (target && target === here) a.setAttribute('aria-current', 'page');
  });

  /* ---------- Año en el pie ---------- */
  document.querySelectorAll('[data-year]').forEach(function (el) {
    el.textContent = String(new Date().getFullYear());
  });

  /* ---------- Biblioteca filtrable ---------- */
  var lib = document.querySelector('[data-library]');
  if (lib) {
    var chips = Array.prototype.slice.call(lib.querySelectorAll('.chip[data-filter]'));
    var input = lib.querySelector('[data-search]');
    var items = Array.prototype.slice.call(lib.querySelectorAll('[data-cats]'));
    var counter = lib.querySelector('[data-count]');
    var empty = lib.querySelector('[data-empty]');
    var active = 'todos';

    function render() {
      var q = (input && input.value || '').trim().toLowerCase();
      var shown = 0;
      items.forEach(function (item) {
        var cats = (item.getAttribute('data-cats') || '').split(/\s+/);
        var matchCat = active === 'todos' || cats.indexOf(active) !== -1;
        var matchText = !q || item.textContent.toLowerCase().indexOf(q) !== -1;
        var ok = matchCat && matchText;
        item.classList.toggle('hidden', !ok);
        if (ok) shown++;
      });
      if (counter) counter.textContent = shown === 1 ? '1 recurso' : shown + ' recursos';
      if (empty) empty.classList.toggle('hidden', shown !== 0);
    }

    function activar(filtro) {
      var elegido = null;
      chips.forEach(function (c) {
        var suyo = c.getAttribute('data-filter') === filtro;
        c.setAttribute('aria-pressed', String(suyo));
        if (suyo) elegido = c;
      });
      active = elegido ? filtro : 'todos';
      if (!elegido) {
        chips.forEach(function (c) {
          c.setAttribute('aria-pressed', String(c.getAttribute('data-filter') === 'todos'));
        });
      }
      render();
    }

    chips.forEach(function (chip) {
      chip.addEventListener('click', function () { activar(chip.getAttribute('data-filter')); });
    });
    if (input) input.addEventListener('input', render);

    // Permite entrar directo a una categoría: recursos.html#zonas
    var desdeHash = function () {
      var h = (location.hash || '').replace('#', '');
      activar(h || 'todos');
    };
    window.addEventListener('hashchange', desdeHash);
    desdeHash();
  }

  /* ---------- Checklists con progreso (persistente por página) ---------- */
  document.querySelectorAll('[data-checklist]').forEach(function (list) {
    var id = 'rg-check-' + (list.getAttribute('data-checklist') || 'x');
    var boxes = Array.prototype.slice.call(list.querySelectorAll('input[type="checkbox"]'));
    var bar = document.querySelector('[data-progress="' + list.getAttribute('data-checklist') + '"]');
    var label = document.querySelector('[data-progress-label="' + list.getAttribute('data-checklist') + '"]');
    var saved = [];
    try { saved = JSON.parse(localStorage.getItem(id) || '[]'); } catch (e) { saved = []; }

    function paint() {
      var done = boxes.filter(function (b) { return b.checked; }).length;
      var pct = boxes.length ? Math.round((done / boxes.length) * 100) : 0;
      if (bar) bar.style.width = pct + '%';
      if (label) label.textContent = done + ' de ' + boxes.length + ' · ' + pct + ' %';
    }

    boxes.forEach(function (box, i) {
      if (saved.indexOf(i) !== -1) box.checked = true;
      box.addEventListener('change', function () {
        var done = [];
        boxes.forEach(function (b, j) { if (b.checked) done.push(j); });
        try { localStorage.setItem(id, JSON.stringify(done)); } catch (e) { /* ignorar */ }
        paint();
      });
    });
    paint();

    var reset = document.querySelector('[data-checklist-reset="' + list.getAttribute('data-checklist') + '"]');
    if (reset) {
      reset.addEventListener('click', function () {
        boxes.forEach(function (b) { b.checked = false; });
        try { localStorage.removeItem(id); } catch (e) { /* ignorar */ }
        paint();
      });
    }
  });


  /* ---------- Al imprimir, abrir los acordeones ---------- */
  if (window.matchMedia) {
    var mq = window.matchMedia('print');
    var openAll = function (on) {
      document.querySelectorAll('details.acc').forEach(function (d) {
        if (on) { if (!d.open) { d.open = true; d.dataset.wasClosed = '1'; } }
        else if (d.dataset.wasClosed) { d.open = false; delete d.dataset.wasClosed; }
      });
    };
    if (mq.addEventListener) mq.addEventListener('change', function (e) { openAll(e.matches); });
    window.addEventListener('beforeprint', function () { openAll(true); });
    window.addEventListener('afterprint', function () { openAll(false); });
  }

  /* ---------- Copiar al portapapeles ---------- */
  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('[data-copy]');
    if (!btn) return;
    var src = document.querySelector(btn.getAttribute('data-copy'));
    if (!src) return;
    var text = src.textContent;
    var done = function () {
      var old = btn.textContent;
      btn.textContent = 'Copiado ✓';
      setTimeout(function () { btn.textContent = old; }, 1800);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(text, done); });
    } else {
      fallback(text, done);
    }
  });

  function fallback(text, cb) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); cb(); } catch (e) { /* ignorar */ }
    document.body.removeChild(ta);
  }
})();
