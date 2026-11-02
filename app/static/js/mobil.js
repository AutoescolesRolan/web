/* Ajustos per al mòbil (web, àrea de l'alumne i Rolan Gestió):
   - Mentre s'escriu (teclat obert) les barres fixes de baix («Pagar…», cistella, xat) es queden
     quietes al seu lloc, perquè no tapin el camp ni facin moure la pàgina.
   - Les taules massa amples es poden lliscar de costat dins seu, sense moure tota la pàgina. */
(function () {
  var tactil = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
  function esCamp(el) {
    if (!el || !el.tagName) return false;
    var t = el.tagName, ty = (el.type || '').toLowerCase();
    return t === 'TEXTAREA' || t === 'SELECT' || (t === 'INPUT' && ['checkbox', 'radio', 'button', 'submit', 'file', 'range'].indexOf(ty) < 0);
  }
  if (tactil) {
    document.addEventListener('focusin', function (e) { if (esCamp(e.target) && !e.target.closest('#ast-panell')) document.body.classList.add('teclat'); });
    document.addEventListener('focusout', function () { setTimeout(function () { if (!esCamp(document.activeElement)) document.body.classList.remove('teclat'); }, 120); });
  }
  var css = document.createElement('style');
  css.textContent = 'body.teclat .bar,body.teclat .paybar,body.teclat .cistbar,body.teclat .pr-barra{position:static!important}' +
                    'body.teclat .ast-boto{display:none!important}' +
                    '.taula-llisca{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}';
  document.head.appendChild(css);
  function embolcalla() {
    document.querySelectorAll('table').forEach(function (t) {
      var p = t.parentElement, dins = false;
      while (p && p !== document.body) {
        var o = getComputedStyle(p).overflowX;
        if (o === 'auto' || o === 'scroll') { dins = true; break; }
        p = p.parentElement;
      }
      if (dins || t.closest('.calendar-grid')) return;
      var vw = document.documentElement.clientWidth;
      if (t.getBoundingClientRect().right <= vw + 1 && t.scrollWidth <= t.clientWidth + 1) return;
      var w = document.createElement('div'); w.className = 'taula-llisca';
      t.parentNode.insertBefore(w, t); w.appendChild(t);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', embolcalla); else embolcalla();
})();

/* Files clicables: <tr data-href="/ficha/12"> obre la fitxa clicant qualsevol lloc de la fila
   (els enllaços, botons i camps de dins continuen fent el seu). Ctrl/⌘ o el botó del mig: pestanya nova. */
(function () {
  function desti(e) {
    if (e.defaultPrevented) return null;
    var tr = e.target.closest && e.target.closest('tr[data-href]');
    if (!tr || e.target.closest('a,button,input,select,textarea,label,summary,[contenteditable]')) return null;
    if (window.getSelection && String(window.getSelection())) return null;   // estava seleccionant text
    return tr.getAttribute('data-href');
  }
  document.addEventListener('click', function (e) {
    var h = desti(e); if (!h) return;
    if (e.ctrlKey || e.metaKey || e.shiftKey) window.open(h, '_blank'); else location.href = h;
  });
  document.addEventListener('auxclick', function (e) { if (e.button === 1) { var h = desti(e); if (h) window.open(h, '_blank'); } });
})();
