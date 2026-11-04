/* Assistent amb IA de la web (matrícula, packs, taxes i exàmens).
   Crea el botó i el panell si el servidor diu que està actiu (/assistent/qui) i guarda la
   conversa a la pestanya (sessionStorage) perquè no es perdi en canviar de pàgina. */
(function () {
  if (document.getElementById('ast')) return;
  var es = (document.documentElement.lang || '').slice(0, 2) === 'es';
  var pagina = location.pathname;
  var ICO_XAT = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.5 4.5h13a2.5 2.5 0 0 1 2.5 2.5v8.5a2.5 2.5 0 0 1-2.5 2.5h-7.2L7 21.2V18H5.5A2.5 2.5 0 0 1 3 15.5V7a2.5 2.5 0 0 1 2.5-2.5z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="8" cy="11.25" r="1.35" fill="currentColor"/><circle cx="12" cy="11.25" r="1.35" fill="currentColor"/><circle cx="16" cy="11.25" r="1.35" fill="currentColor"/></svg>';
  var ICO_IA = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.9 4.6L18.5 9l-4.6 1.9L12 15.5l-1.9-4.6L5.5 9l4.6-1.4z"/><path d="M19 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/></svg>';
  var ICO_PROF = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 9.5 12 5l10 4.5-10 4.5z"/><path d="M6 11.3V16c0 1.4 2.7 3 6 3s6-1.6 6-3v-4.7"/><path d="M22 9.5V15"/></svg>';
  var ICO_ENVIA = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/></svg>';

  var T = es ? {
    l1: '¿Tienes dudas?', l2: 'Pregunta al asistente', titol: 'Asistente Rolan', subtitol: 'Respuestas automáticas con IA',
    tanca: 'Cerrar', placeholder: 'Escribe tu pregunta…', enviar: 'Enviar', cancel: 'Cancelar',
    nota: 'No escribas datos personales (DNI, tarjeta…). Puede equivocarse.', persona: 'Hablar con una persona',
    hola: { visitant: '¡Hola! 👋 Soy el asistente de Autoescoles Rolan. Pregúntame lo que quieras de la matrícula: qué incluye cada pack, qué tasas y exámenes tendrás que pagar para presentarte o cómo funciona el pago.' },
    sug: { visitant: ['¿Qué incluye cada pack del B?', '¿Qué tasas tendré que pagar?', '¿Los exámenes se pagan aparte?', '¿Cómo funciona la matrícula?'],
           matricula: ['¿Qué tasas tendré que pagar?', '¿Los exámenes se pagan aparte?', '¿Puedo pagar la tasa más adelante?', '¿Qué pasa después de pagar?'] },
    error: 'Ahora no puedo responder. Vuelve a probarlo en un momento o habla con una persona.',
    limit: 'Has hecho muchas preguntas seguidas. Espera un rato o habla con una persona.',
    ofereix: 'Si quieres, una persona de la autoescuela te responderá:', ofereix_boto: 'Hablar con una persona',
    pers_titol: 'Te contestará una persona de la autoescuela', pers_nom: 'Tu nombre', pers_contacte: 'Correo o teléfono para responderte',
    pers_msg: '¿En qué te podemos ayudar?', pers_ok: '¡Recibido! Te responderemos lo antes posible.', pers_falta: 'Indica cómo contactarte y tu consulta.'
  } : {
    l1: 'Tens dubtes?', l2: "Pregunta a l'assistent", titol: 'Assistent Rolan', subtitol: 'Respostes automàtiques amb IA',
    tanca: 'Tancar', placeholder: 'Escriu la teva pregunta…', enviar: 'Enviar', cancel: 'Cancel·lar',
    nota: 'No escriguis dades personals (DNI, targeta…). Es pot equivocar.', persona: 'Parlar amb una persona',
    hola: { visitant: "Hola! 👋 Soc l'assistent d'Autoescoles Rolan. Pregunta'm el que vulguis de la matrícula: què inclou cada pack, quines taxes i exàmens hauràs de pagar per presentar-te o com funciona el pagament." },
    sug: { visitant: ['Què inclou cada pack del B?', 'Quines taxes hauré de pagar?', 'Els exàmens es paguen a part?', 'Com funciona la matrícula?'],
           matricula: ['Quines taxes hauré de pagar?', 'Els exàmens es paguen a part?', 'Puc pagar la taxa més endavant?', 'Què passa després de pagar?'] },
    error: "Ara no puc respondre. Torna-ho a provar d'aquí a un moment o parla amb una persona.",
    limit: 'Has fet moltes preguntes seguides. Espera una estona o parla amb una persona.',
    ofereix: "Si vols, et respondrà una persona de l'autoescola:", ofereix_boto: 'Parlar amb una persona',
    pers_titol: "Et respondrà una persona de l'autoescola", pers_nom: 'El teu nom', pers_contacte: 'Correu o telèfon per respondre’t',
    pers_msg: 'En què et podem ajudar?', pers_ok: 'Rebut! Et respondrem al més aviat possible.', pers_falta: 'Indica com et podem contactar i la teva consulta.'
  };

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function el(html) { var d = document.createElement('div'); d.innerHTML = html.trim(); return d.firstChild; }

  fetch('/assistent/qui?pagina=' + encodeURIComponent(pagina), { credentials: 'same-origin' })
    .then(function (r) { return r.json(); })
    .then(function (q) { if (q && q.actiu) munta(q); })
    .catch(function () {});

  function munta(q) {
    var context = 'visitant';
    var ICO_BOTO = ICO_XAT, ICO_CAP = ICO_IA;
    var arrel = el('<div class="ast" id="ast" data-context="' + esc(context) + '">' +
      '<button type="button" class="ast-boto" id="ast-boto" aria-haspopup="dialog" aria-controls="ast-panell" aria-label="' + esc(T.l1 + ' ' + T.l2) + '">' +
        '<span class="ast-ic">' + ICO_BOTO + '</span><span class="ast-l"><span class="ast-l1">' + esc(T.l1) + '</span><span class="ast-l2">' + esc(T.l2) + '</span></span></button>' +
      '<div class="ast-panell" id="ast-panell" role="dialog" aria-modal="false" aria-labelledby="ast-titol">' +
        '<div class="ast-cap"><span class="ast-av">' + ICO_CAP + '</span><div><b id="ast-titol">' + esc(T.titol) + '</b><small>' + esc(T.subtitol) + '</small></div>' +
          '<button type="button" class="ast-tanca" id="ast-tanca" aria-label="' + esc(T.tanca) + '">×</button></div>' +
        '<div class="ast-msgs" id="ast-msgs" aria-live="polite"></div>' +
        '<div class="ast-pers" id="ast-pers"><b>' + esc(T.pers_titol) + '</b>' +
          '<input type="text" id="ast-p-nom" autocomplete="name" placeholder="' + esc(T.pers_nom) + '" value="' + esc(q.nom || '') + '">' +
          '<input type="text" id="ast-p-contacte" autocomplete="email" placeholder="' + esc(T.pers_contacte) + '" value="' + esc(q.contacte || '') + '">' +
          '<textarea id="ast-p-msg" rows="3" placeholder="' + esc(T.pers_msg) + '"></textarea>' +
          '<div class="ast-fila"><button type="button" class="ast-cancel" id="ast-p-cancel">' + esc(T.cancel) + '</button><button type="button" class="ast-env" id="ast-p-env">' + esc(T.enviar) + '</button></div></div>' +
        '<div class="ast-peu"><form class="ast-form" id="ast-form">' +
          '<textarea id="ast-text" rows="1" maxlength="1000" placeholder="' + esc(T.placeholder) + '" aria-label="' + esc(T.placeholder) + '"></textarea>' +
          '<button type="submit" class="ast-envia" id="ast-envia" aria-label="' + esc(T.enviar) + '">' + ICO_ENVIA + '</button></form>' +
          '<p class="ast-nota">' + esc(T.nota) + ' <a id="ast-persona-link" role="button" tabindex="0">' + esc(T.persona) + '</a></p></div>' +
      '</div></div>');
    document.body.appendChild(arrel);

    var CLAU = 'rolan_web_assistent';
    var estat = { obert: false, missatges: [] };
    try { var g = JSON.parse(sessionStorage.getItem(CLAU) || 'null'); if (g && g.missatges) estat = g; } catch (e) {}
    function desa() { try { sessionStorage.setItem(CLAU, JSON.stringify({ obert: estat.obert, missatges: estat.missatges.slice(-30) })); } catch (e) {} }

    var boto = document.getElementById('ast-boto'), msgs = document.getElementById('ast-msgs');
    var form = document.getElementById('ast-form'), text = document.getElementById('ast-text');
    var envia = document.getElementById('ast-envia'), pers = document.getElementById('ast-pers');

    // entrada: el botó cau i rebota, només la primera pàgina de la visita
    try {
      if (!sessionStorage.getItem('rolan_ast_vist')) {
        boto.classList.add('ast-cau');
        boto.addEventListener('animationend', function () { boto.classList.remove('ast-cau'); }, { once: true });
        sessionStorage.setItem('rolan_ast_vist', '1');
      }
    } catch (e) {}

    // Markdown mínim i segur: negreta, enllaços interns o de dgt.es/boe.es, llistes i salts de línia
    function md(s) {
      var h = esc(s);
      h = h.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
      h = h.replace(/\[([^\]]+)\]\(((?:\/[^\s)]*)|(?:https:\/\/(?:www\.)?(?:dgt\.es|sede\.dgt\.gob\.es|boe\.es)[^\s)]*))\)/g,
        function (m, t, u) { return '<a href="' + u + '"' + (u.charAt(0) === '/' ? '' : ' target="_blank" rel="noopener"') + '>' + t + '</a>'; });
      var out = [], llista = false;
      h.split(/\n/).forEach(function (l) {
        var m = l.match(/^\s*(?:[-*•]|\d+\.)\s+(.*)$/);
        if (m) { if (!llista) { out.push('<ul>'); llista = true; } out.push('<li>' + m[1] + '</li>'); }
        else { if (llista) { out.push('</ul>'); llista = false; } if (l.trim()) out.push('<p>' + l + '</p>'); }
      });
      if (llista) out.push('</ul>');
      return out.join('');
    }
    function bombolla(rol, contingut, extra) {
      var d = document.createElement('div');
      d.className = 'ast-m ' + (rol === 'usuari' ? 'u' : 'a') + (extra ? ' ' + extra : '');
      if (rol === 'usuari') d.textContent = contingut; else d.innerHTML = md(contingut);
      msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight;
      return d;
    }
    function suggeriments() {
      var w = document.createElement('div'); w.className = 'ast-sug';
      (/^\/(matricula|pagament)/.test(pagina) ? T.sug.matricula : T.sug.visitant).forEach(function (s) {
        var b = document.createElement('button'); b.type = 'button'; b.textContent = s;
        b.addEventListener('click', function () { pregunta(s); });
        w.appendChild(b);
      });
      msgs.appendChild(w);
    }
    function ofereixPersona() {
      bombolla('assistent', T.ofereix);
      var b = document.createElement('button'); b.type = 'button'; b.className = 'ast-persona-boto'; b.textContent = T.ofereix_boto;
      b.addEventListener('click', obrePersona);
      msgs.appendChild(b); msgs.scrollTop = msgs.scrollHeight;
    }
    function pinta() {
      msgs.innerHTML = '';
      bombolla('assistent', T.hola.visitant);
      if (!estat.missatges.length) suggeriments();
      estat.missatges.forEach(function (m) { bombolla(m.rol, m.text); });
    }
    var tactil = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    var panell = document.getElementById('ast-panell');
    // Al mòbil, la finestra queda per sobre del teclat (no hi queda amagada a sota)
    function ajusta() {
      var vv = window.visualViewport;
      if (!vv || window.innerWidth > 560) { panell.style.bottom = ''; panell.style.maxHeight = ''; return; }
      var baix = Math.max(0, window.innerHeight - (vv.height + vv.offsetTop));
      panell.style.bottom = (baix + 10) + 'px';
      panell.style.maxHeight = Math.max(220, vv.height - 20) + 'px';
    }
    if (window.visualViewport) { window.visualViewport.addEventListener('resize', ajusta); window.visualViewport.addEventListener('scroll', ajusta); }
    function obre() {
      estat.obert = true; arrel.classList.add('ast-obert'); desa(); pinta(); ajusta();
      if (!tactil) setTimeout(function () { text.focus(); }, 30);   // al mòbil no s'obre el teclat sol
    }
    function tanca() { estat.obert = false; arrel.classList.remove('ast-obert'); desa(); boto.focus(); }
    boto.addEventListener('click', obre);
    document.getElementById('ast-tanca').addEventListener('click', tanca);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && estat.obert) tanca(); });

    function pregunta(s) {
      s = (s || '').trim();
      if (!s || envia.disabled) return;
      var sug = msgs.querySelector('.ast-sug'); if (sug) sug.remove();
      estat.missatges.push({ rol: 'usuari', text: s.slice(0, 1000) }); desa();
      bombolla('usuari', s);
      var esp = document.createElement('div'); esp.className = 'ast-m a'; esp.innerHTML = '<span class="ast-escrivint"><i></i><i></i><i></i></span>';
      msgs.appendChild(esp); msgs.scrollTop = msgs.scrollHeight;
      envia.disabled = true;
      fetch('/assistent/xat', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ missatges: estat.missatges.slice(-12), pagina: pagina, titol: document.title, idioma: es ? 'es' : 'ca' }) })
        .then(function (r) { return r.json(); })
        .then(function (r) {
          esp.remove();
          if (r.ok) {
            estat.missatges.push({ rol: 'assistent', text: r.resposta }); desa();
            bombolla('assistent', r.resposta);
            if (r.cal_persona) ofereixPersona();
          } else { bombolla('assistent', r.motiu === 'limit' ? T.limit : T.error, 'err'); ofereixPersona(); }
        })
        .catch(function () { esp.remove(); bombolla('assistent', T.error, 'err'); ofereixPersona(); })
        .then(function () { envia.disabled = false; text.focus(); });
    }
    form.addEventListener('submit', function (e) { e.preventDefault(); var s = text.value; text.value = ''; text.style.height = ''; pregunta(s); });
    text.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit')); } });
    text.addEventListener('input', function () { text.style.height = 'auto'; text.style.height = Math.min(text.scrollHeight, 120) + 'px'; });

    function obrePersona() {
      pers.classList.add('on');
      var m = document.getElementById('ast-p-msg'), c = document.getElementById('ast-p-contacte');
      if (!m.value) { var u = estat.missatges.filter(function (x) { return x.rol === 'usuari'; }); if (u.length) m.value = u[u.length - 1].text; }
      (c.value ? m : c).focus();
    }
    var link = document.getElementById('ast-persona-link');
    link.addEventListener('click', obrePersona);
    link.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); obrePersona(); } });
    document.getElementById('ast-p-cancel').addEventListener('click', function () { pers.classList.remove('on'); });
    document.getElementById('ast-p-env').addEventListener('click', function () {
      var nom = document.getElementById('ast-p-nom').value, contacte = document.getElementById('ast-p-contacte').value,
          missatge = document.getElementById('ast-p-msg').value, b = this;
      if (!contacte.trim() || !missatge.trim()) { bombolla('assistent', T.pers_falta, 'err'); return; }
      b.disabled = true;
      fetch('/assistent/persona', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ nom: nom, contacte: contacte, missatge: missatge, conversa: estat.missatges.slice(-20), pagina: pagina }) })
        .then(function (r) { return r.json(); })
        .then(function (r) {
          if (r.ok) { pers.classList.remove('on'); document.getElementById('ast-p-msg').value = ''; bombolla('assistent', T.pers_ok); }
          else bombolla('assistent', r.motiu === 'limit' ? T.limit : T.pers_falta, 'err');
        })
        .catch(function () { bombolla('assistent', T.error, 'err'); })
        .then(function () { b.disabled = false; });
    });

    if (estat.obert) obre();
  }
})();
