/* Avisos amb el disseny de l'app (Autoescoles Rolan), a tot arreu:
 *  - Validació dels formularis: en lloc de la bombolla del navegador, un missatge sota el camp.
 *  - alert() i confirm(): finestres pròpies en lloc de les del navegador.
 * Funciona sola: només cal carregar aquest fitxer. Idioma segons <html lang> (ca / es).
 */
(function () {
  'use strict';
  if (window.__avisosRolan) return; window.__avisosRolan = true;

  var ES = /^es/i.test(document.documentElement.lang || '');
  var TX = ES ? {
    buit: 'Rellena este campo.', tria: 'Elige una opción.', marca: 'Marca esta casilla para continuar.',
    email: 'Escribe un correo electrónico válido.', url: 'Escribe una dirección web válida.',
    format: 'El formato no es correcto.', curt: 'Es demasiado corto (mínimo {n} caracteres).',
    llarg: 'Es demasiado largo (máximo {n} caracteres).', min: 'El valor mínimo es {n}.', max: 'El valor máximo es {n}.',
    num: 'Escribe un número válido.', fitxer: 'Elige un archivo.', data: 'Escribe una fecha válida.',
    ok: 'Entendido', si: 'Sí, continuar', no: 'Cancelar', avis: 'Aviso', segur: '¿Seguro?'
  } : {
    buit: 'Omple aquest camp.', tria: 'Tria una opció.', marca: 'Marca aquesta casella per continuar.',
    email: 'Escriu un correu electrònic vàlid.', url: 'Escriu una adreça web vàlida.',
    format: 'El format no és correcte.', curt: 'És massa curt (mínim {n} caràcters).',
    llarg: 'És massa llarg (màxim {n} caràcters).', min: 'El valor mínim és {n}.', max: 'El valor màxim és {n}.',
    num: 'Escriu un número vàlid.', fitxer: 'Tria un fitxer.', data: 'Escriu una data vàlida.',
    ok: 'Entesos', si: 'Sí, continuar', no: 'Cancel·lar', avis: 'Avís', segur: 'Segur?'
  };

  // ------------------------------------------------------------------ estils
  var css = '' +
    '.av-err{display:flex;align-items:flex-start;gap:7px;margin:7px 0 2px;padding:8px 11px;border-radius:10px;background:#FDECEC;' +
    'border:1px solid #F5C2C4;color:#9B1C21;font-size:13px;font-weight:600;line-height:1.35;animation:avIn .18s ease}' +
    '.av-err svg{flex:none;width:16px;height:16px;margin-top:1px}' +
    '.av-invalid{border-color:#E5484D!important;box-shadow:0 0 0 3px rgba(229,72,77,.14)!important}' +
    '@keyframes avIn{from{opacity:0;transform:translateY(-3px)}to{opacity:1;transform:none}}' +
    '.av-ov{position:fixed;inset:0;z-index:100000;background:rgba(16,24,48,.55);display:flex;align-items:center;justify-content:center;padding:18px;animation:avF .18s ease}' +
    '@keyframes avF{from{opacity:0}to{opacity:1}}' +
    '.av-box{background:#fff;border-radius:20px;max-width:420px;width:100%;box-shadow:0 24px 70px rgba(0,0,0,.35);overflow:hidden;' +
    'font-family:inherit;color:#14224F;animation:avP .22s cubic-bezier(.2,.9,.3,1.2);position:relative}' +
    '.av-box::after{content:"";position:absolute;left:0;right:0;bottom:0;height:6px;background:repeating-linear-gradient(90deg,#8BC53F 0 24px,transparent 24px 42px)}' +
    '@keyframes avP{from{transform:translateY(14px) scale(.97);opacity:0}to{transform:none;opacity:1}}' +
    '.av-cos{padding:26px 24px 8px;text-align:center}' +
    '.av-ico{width:54px;height:54px;border-radius:16px;margin:0 auto 14px;display:flex;align-items:center;justify-content:center;background:#EEF1FC;color:#2541B8}' +
    '.av-ico svg{width:28px;height:28px}.av-box.perill .av-ico{background:#FDECEC;color:#C8292F}' +
    '.av-tit{font-family:"Bricolage Grotesque",var(--disp,inherit);font-weight:800;font-size:19px;margin:0 0 6px;color:#14224F}' +
    '.av-txt{font-size:14.5px;line-height:1.5;color:#4B5675;margin:0;white-space:pre-line}' +
    '.av-acc{display:flex;gap:10px;justify-content:center;padding:18px 24px 26px;flex-wrap:wrap}' +
    '.av-b{border:0;border-radius:12px;padding:12px 20px;font:inherit;font-weight:700;font-size:14.5px;cursor:pointer;min-width:120px}' +
    '.av-b.pri{background:#2541B8;color:#fff;box-shadow:0 6px 16px rgba(37,65,184,.26)}.av-b.pri:hover{background:#1A2E82}' +
    '.av-box.perill .av-b.pri{background:#D93036;box-shadow:0 6px 16px rgba(217,48,54,.25)}.av-box.perill .av-b.pri:hover{background:#B5242A}' +
    '.av-b.sec{background:#EEF1FC;color:#1A2E82}.av-b.sec:hover{background:#E3E8FA}' +
    '@media(max-width:480px){.av-b{flex:1}}';
  var st = document.createElement('style'); st.textContent = css;
  (document.head || document.documentElement).appendChild(st);

  var ICO_ERR = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>';
  var ICO_INFO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/></svg>';
  var ICO_PREG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/></svg>';
  var ICO_PAPERERA = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>';

  // ------------------------------------------------------------------ validació de formularis
  function missatge(el) {
    var v = el.validity;
    if (v.customError) return el.validationMessage;
    if (v.valueMissing) {
      if (el.type === 'checkbox') return TX.marca;
      if (el.type === 'radio' || el.tagName === 'SELECT') return TX.tria;
      if (el.type === 'file') return TX.fitxer;
      return TX.buit;
    }
    if (v.typeMismatch) return el.type === 'email' ? TX.email : el.type === 'url' ? TX.url : TX.format;
    if (v.patternMismatch) return el.title || TX.format;
    if (v.tooShort) return TX.curt.replace('{n}', el.minLength);
    if (v.tooLong) return TX.llarg.replace('{n}', el.maxLength);
    if (v.rangeUnderflow) return TX.min.replace('{n}', el.min);
    if (v.rangeOverflow) return TX.max.replace('{n}', el.max);
    if (v.badInput) return el.type === 'date' ? TX.data : TX.num;
    return el.validationMessage || TX.format;
  }
  function amagat(el) {
    var cs = getComputedStyle(el);
    return !el.offsetParent || cs.opacity === '0' || cs.visibility === 'hidden' || el.offsetWidth < 4;
  }
  // on es posa el missatge: sota el camp (o sota el grup, si és una opció amagada com les targetes)
  function ancora(el) {
    if (el.closest('.tel-camp')) return el.closest('.tel-camp');
    if ((el.type === 'radio' || el.type === 'checkbox') && amagat(el)) {
      var lbl = el.closest('label');
      return (lbl && lbl.parentElement) || el.parentElement;
    }
    if (el.type === 'radio') { var g = el.closest('label'); return (g && g.parentElement) || el; }
    if (el.type === 'checkbox') return el.closest('label') || el;
    return el;
  }
  function treu(el) {
    var a = ancora(el), n = a && a.nextElementSibling;
    if (n && n.classList.contains('av-err')) n.remove();
    el.classList.remove('av-invalid');
    if (el.type === 'radio' && el.name) {
      document.querySelectorAll('.av-err[data-nom="' + el.name.replace(/"/g, '') + '"]').forEach(function (x) { x.remove(); });
    }
    if (el.type === 'radio' && el.name && el.form) {
      el.form.querySelectorAll('input[type=radio][name="' + el.name + '"]').forEach(function (r) { r.classList.remove('av-invalid'); });
    }
  }
  var primer = null, primerT = 0, senseFocus = false;
  document.addEventListener('invalid', function (e) {
    var el = e.target;
    if (!el || !el.validity) return;
    e.preventDefault();                                  // sense la bombolla del navegador
    if (el.type === 'radio' && el.name) {                // un sol missatge per grup d'opcions
      var ja = document.querySelector('.av-err[data-nom="' + el.name.replace(/"/g, '') + '"]');
      if (ja) return;
    }
    var a = ancora(el), n = a.nextElementSibling;
    if (!(n && n.classList.contains('av-err'))) {
      n = document.createElement('div'); n.className = 'av-err'; n.setAttribute('role', 'alert');
      if (el.type === 'radio' && el.name) n.setAttribute('data-nom', el.name);
      a.parentNode.insertBefore(n, a.nextSibling);
    }
    n.innerHTML = ICO_ERR + '<span></span>'; n.lastChild.textContent = missatge(el);
    if (!amagat(el)) el.classList.add('av-invalid');
    // només el primer camp erroni de cada enviament rep el focus
    var ara = Date.now();
    if (!senseFocus && (!primer || ara - primerT > 300)) {
      primer = el; primerT = ara;
      var r = (amagat(el) ? a : el).getBoundingClientRect();
      if (r.top < 80 || r.bottom > window.innerHeight - 40) window.scrollTo({ top: window.scrollY + r.top - 120, behavior: 'smooth' });
      if (!amagat(el)) try { el.focus({ preventScroll: true }); } catch (x) {}
    }
  }, true);
  function revisa(e) {
    var el = e.target;
    if (!el || !el.validity) return;
    setTimeout(function () { revisaAra(el); }, 0);   // després dels altres scripts (p. ex. el del telèfon)
  }
  function revisaAra(el) {
    if (el.validity.valid) treu(el);
    else if (el.classList.contains('av-invalid') || (ancora(el).nextElementSibling || {}).className === 'av-err') {
      var n = ancora(el).nextElementSibling; if (n && n.lastChild) n.lastChild.textContent = missatge(el);
    }
  }
  document.addEventListener('input', revisa, true);
  document.addEventListener('change', revisa, true);


  // ------------------------------------------------------------------ DNI / NIE (lletra de control)
  var LL = 'TRWAGMYFPDXBNJZSQVHLCKE';
  var TXD = ES ? { format: 'El DNI/NIE no tiene el formato correcto (8 cifras y una letra, o X/Y/Z + 7 cifras y una letra).',
                   lletra: 'La letra del DNI/NIE no corresponde al número. Revisa que esté bien escrito.' }
               : { format: 'El DNI/NIE no té el format correcte (8 xifres i una lletra, o X/Y/Z + 7 xifres i una lletra).',
                   lletra: "La lletra del DNI/NIE no correspon al número. Revisa que l'hagis escrit bé." };
  function errDni(v) {
    v = (v || '').toUpperCase().replace(/[\s.\-_/]/g, '');
    if (!v || /^PENDENT/.test(v)) return '';
    var m = /^(\d{7,8})([A-Z])$/.exec(v);
    if (m) return LL[parseInt(m[1], 10) % 23] === m[2] ? '' : TXD.lletra;
    m = /^([XYZ])(\d{7})([A-Z])$/.exec(v);
    if (m) return LL[parseInt('XYZ'.indexOf(m[1]) + m[2], 10) % 23] === m[3] ? '' : TXD.lletra;
    return TXD.format;
  }
  var SEL_DNI = 'input[data-dni], input[name="dni"], input[name="tutor_dni"]';
  function validaDni(el) { el.setCustomValidity(errDni(el.value)); }
  document.addEventListener('input', function (e) {
    var el = e.target;
    if (el.matches && el.matches(SEL_DNI)) {
      var p = el.selectionStart, up = el.value.toUpperCase();
      if (up !== el.value) { el.value = up; try { el.setSelectionRange(p, p); } catch (x) {} }
      validaDni(el);
    }
  }, true);
  document.addEventListener('blur', function (e) {
    var el = e.target;
    if (el.matches && el.matches(SEL_DNI) && el.value.trim()) { validaDni(el); if (!el.validity.valid) { senseFocus = true; try { el.checkValidity(); } finally { senseFocus = false; } } }
  }, true);
  function preparaDni() { document.querySelectorAll(SEL_DNI).forEach(function (el) { el.setAttribute('autocapitalize', 'characters'); validaDni(el); }); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', preparaDni); else preparaDni();

  // ------------------------------------------------------------------ finestres (alert / confirm)
  function finestra(opc) {
    var ov = document.createElement('div'); ov.className = 'av-ov';
    var perill = opc.perill ? ' perill' : '';
    ov.innerHTML = '<div class="av-box' + perill + '" role="dialog" aria-modal="true"><div class="av-cos"><div class="av-ico">' + opc.ico +
      '</div><div class="av-tit"></div><p class="av-txt"></p></div><div class="av-acc"></div></div>';
    ov.querySelector('.av-tit').textContent = opc.titol;
    ov.querySelector('.av-txt').textContent = opc.text;
    var acc = ov.querySelector('.av-acc'), anterior = document.activeElement;
    function tanca(res) {
      ov.remove(); document.removeEventListener('keydown', tecla, true);
      try { if (anterior && anterior.focus) anterior.focus({ preventScroll: true }); } catch (x) {}
      if (opc.fi) opc.fi(res);
    }
    (opc.botons || []).forEach(function (b) {
      var el = document.createElement('button'); el.type = 'button'; el.className = 'av-b ' + b.cls; el.textContent = b.text;
      el.onclick = function () { tanca(b.valor); }; acc.appendChild(el);
    });
    function tecla(e) {
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); tanca(false); }
      else if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); tanca(true); }
    }
    ov.addEventListener('click', function (e) { if (e.target === ov) tanca(false); });
    document.addEventListener('keydown', tecla, true);
    document.body.appendChild(ov);
    var p = acc.querySelector('.pri'); if (p) p.focus();
  }
  var natiuConfirm = window.confirm.bind(window);
  window.avisRolan = function (text, fi) {
    finestra({ ico: ICO_INFO, titol: TX.avis, text: String(text == null ? '' : text),
               botons: [{ text: TX.ok, cls: 'pri', valor: true }], fi: fi });
  };
  window.alert = function (text) { window.avisRolan(text); };

  // confirm(): torna false de moment i, si l'usuari accepta, es repeteix la mateixa acció
  // (enviar el formulari, el clic…) i aquest cop confirm() torna true.
  var acceptat = false;
  window.confirm = function (text) {
    if (acceptat) { acceptat = false; return true; }
    var ev = window.event;
    if (!ev || !ev.target || !document.body) return natiuConfirm(text);
    var t = ev.type, target = ev.target, submitter = ev.submitter || null;
    var perill = /elimin|esborr|borrar|treure|quitar|cancel/i.test(text || '');
    finestra({ ico: perill ? ICO_PAPERERA : ICO_PREG, titol: TX.segur, text: String(text || ''), perill: perill,
      botons: [{ text: TX.no, cls: 'sec', valor: false }, { text: TX.si, cls: 'pri', valor: true }],
      fi: function (ok) {
        if (!ok) return;
        acceptat = true;
        try {
          if (t === 'submit' && target.tagName === 'FORM') {
            if (target.requestSubmit) target.requestSubmit(submitter && submitter.form === target ? submitter : undefined);
            else target.submit();
          } else {
            var el = target.closest ? (target.closest('a,button,input,select,label,[onclick]') || target) : target;
            if (t === 'change' && 'value' in el) el.dispatchEvent(new Event('change', { bubbles: true }));
            else el.click();
          }
        } finally { setTimeout(function () { acceptat = false; }, 0); }
      } });
    return false;
  };
})();
