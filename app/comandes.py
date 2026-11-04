"""Matrícules i compres de pràctiques: tancar la comanda quan Stripe confirma el pagament,
generar el rebut i enviar els correus a l'alumne, a la secretaria del centre i a admin."""
import html as _html
import os
from datetime import datetime

from sqlalchemy import func

from . import ajustos, correu, documents, models, preus


def url_publica() -> str:
    return (os.environ.get("PUBLIC_URL") or os.environ.get("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")


def _seguent_rebut(db) -> str:
    any_ = datetime.now().year
    prefix = f"W{any_}-"
    darrer = (db.query(func.max(models.Comanda.num_rebut))
              .filter(models.Comanda.num_rebut.like(prefix + "%")).scalar())
    n = int(darrer.split("-")[1]) + 1 if darrer else 1
    return f"{prefix}{n:05d}"


def tanca(db, c, id_pagament: str = "") -> bool:
    """Marca la comanda com a pagada (només un cop), fa el rebut i envia els correus.
    Torna True si l'ha tancada ara."""
    db.refresh(c)
    if c.estat == "pagada":
        return False
    c.estat = "pagada"
    c.pagat_en = datetime.utcnow()
    c.stripe_pagament = id_pagament or c.stripe_pagament
    c.num_rebut = _seguent_rebut(db)
    db.commit()
    try:
        c.rebut_pdf = documents.rebut_pdf(db, c)
        db.commit()
    except Exception as e:                       # el pagament ja és bo: el PDF es pot refer des del panell
        print(f"[comanda {c.id}] no s'ha pogut fer el rebut: {e}")
        db.rollback()
    envia_correus(db, c)
    return True


# --------------------------------------------------------------------------- correus
def _html_correu(cos_html: str, es: bool = False) -> str:
    base = url_publica()
    logo = (f'<img src="{base}/static/img/logo-rolan.png" alt="Autoescoles Rolan" width="64" height="64" '
            f'style="border-radius:50%">' if base else
            '<div style="font-weight:800;color:#14224F;font-size:18px">Autoescoles Rolan</div>')
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"></head>'
            '<body style="margin:0;background:#f4f6fb;padding:24px">'
            '<div style="max-width:580px;margin:0 auto;background:#fff;border:1px solid #e6e9f2;border-radius:14px;'
            'padding:26px 28px;font-family:Arial,Helvetica,sans-serif;color:#222b45;font-size:14px;line-height:1.6">'
            f'<div style="text-align:center;margin-bottom:16px">{logo}</div>{cos_html}'
            '<hr style="border:none;border-top:1px solid #e6e9f2;margin:22px 0 10px">'
            '<div style="font-size:12px;color:#8a93ab;text-align:center">Autoescoles Rolan · '
            + ("Formando conductores desde 1987" if es else "Formant conductors des de 1987") + '</div>'
            '</div></body></html>')


def _taula(files):
    tr = "".join(f'<tr><td style="padding:5px 12px 5px 0;color:#66708C;vertical-align:top">{_html.escape(k)}</td>'
                 f'<td style="padding:5px 0;color:#14224F;font-weight:600">{_html.escape(str(v))}</td></tr>'
                 for k, v in files if v not in (None, ""))
    return f'<table style="border-collapse:collapse;margin:10px 0 14px">{tr}</table>'


def _text_taula(files):
    return "\n".join(f"  {k}: {v}" for k, v in files if v not in (None, ""))


def _boto(url, text):
    return (f'<p style="margin:18px 0"><a href="{url}" style="display:inline-block;background:#2541B8;color:#fff;'
            f'text-decoration:none;font-weight:700;padding:11px 18px;border-radius:10px">{_html.escape(text)}</a></p>')


def _resum(c, es: bool):
    centre = c.centre
    files = [("Centre" if not es else "Centro", centre.nom if centre else ""),
             ("Carnet", c.carnet_codi) if c.tipus == "matricula" else ("", ""),
             ("Pack" if c.tipus == "matricula" else ("Prácticas" if es else "Pràctiques"), c.producte_en("es" if es else "ca"))]
    if c.descompte:
        files.append(("Descuento" if es else "Descompte", f"{c.promocio} (−{preus.eur2(c.descompte)} €)"))
    if c.taxa:
        files.append(("Tasa DGT" if es else "Taxa DGT", f"{preus.eur2(c.taxa)} €"))
    if c.canon:
        files.append(("Canon de pistas" if es else "Cànon de pistes", f"{preus.eur2(c.canon)} €"))
    files.append(("Total pagado" if es else "Total pagat", f"{preus.eur2(c.total)} € (IVA inclòs)" if not es
                  else f"{preus.eur2(c.total)} € (IVA incluido)"))
    files.append(("N.º de recibo" if es else "Núm. de rebut", c.num_rebut))
    return [f for f in files if f[0]]


def _adjunts(c):
    adj = []
    if c.contracte_pdf:
        adj.append((documents.nom_contracte(c), c.contracte_pdf, "application/pdf"))
    if c.rebut_pdf:
        adj.append((documents.nom_rebut(c), c.rebut_pdf, "application/pdf"))
    return adj


VIES_CONTACTE = {"whatsapp": ("WhatsApp", "WhatsApp"), "correu": ("Correu electrònic", "Correo electrónico"),
                 "trucada": ("Trucada", "Llamada")}


def via_contacte(c, es=False) -> str:
    v = VIES_CONTACTE.get(c.contacte_preferit or "")
    return (v[1] if es else v[0]) if v else ""


def _frase_contacte(c, es):
    via = c.contacte_preferit or ""
    if es:
        return {"whatsapp": "La secretaría de tu centro te contactará por WhatsApp para empezar.",
                "correu": "La secretaría de tu centro te contactará por correo para empezar.",
                "trucada": "La secretaría de tu centro te llamará para empezar."}.get(
            via, "La secretaría de tu centro se pondrá en contacto contigo para empezar.")
    return {"whatsapp": "La secretaria del teu centre et contactarà per WhatsApp per començar.",
            "correu": "La secretaria del teu centre et contactarà per correu per començar.",
            "trucada": "La secretaria del teu centre et trucarà per començar."}.get(
        via, "La secretaria del teu centre es posarà en contacte amb tu per començar.")


def correu_alumne(db, c):
    es = c.idioma == "es"
    centre = c.centre
    enllac = f"{url_publica()}/comanda/{c.token}" if url_publica() else ""
    tel = " · ".join(x for x in ((centre.telefon if centre else ""), (centre.mobil if centre else "")) if x)
    resum = _resum(c, es)
    if c.tipus == "matricula":
        assumpte = "Matrícula confirmada · Autoescoles Rolan"
        if es:
            intro = f"¡Hola, {c.nom}! Ya estás matriculado/a en Autoescoles Rolan. Te adjuntamos el contrato firmado y el recibo del pago."
            passos = [_frase_contacte(c, True),
                      "Para el expediente necesitarás: DNI/NIE original, certificado médico para el permiso y 2 fotos tamaño carnet.",
                      "Para presentarte al examen, si no la has pagado ahora, falta la tasa de la DGT."]
        else:
            intro = f"Hola, {c.nom}! Ja estàs matriculat/da a Autoescoles Rolan. T'adjuntem el contracte signat i el rebut del pagament."
            passos = [_frase_contacte(c, False),
                      "Per a l'expedient necessitaràs: DNI/NIE original, certificat mèdic per al permís i 2 fotos de carnet.",
                      "Per presentar-te a l'examen, si no l'has pagada ara, falta la taxa de la DGT."]
        if c.taxa:
            passos = passos[:2]
    else:
        assumpte = ("Compra de prácticas confirmada · Autoescoles Rolan" if es
                    else "Compra de pràctiques confirmada · Autoescoles Rolan")
        intro = (f"¡Hola, {c.nom}! Hemos recibido el pago de tus prácticas. Te adjuntamos el recibo." if es else
                 f"Hola, {c.nom}! Hem rebut el pagament de les teves pràctiques. T'adjuntem el rebut.")
        passos = (["La secretaría de tu centro las añadirá a tu expediente y te dirá cuándo empiezas."] if es else
                  ["La secretaria del teu centre les afegirà al teu expedient i et dirà quan comences."])
    dubte = ("¿Tienes alguna duda? Responde a este correo: llega directamente a la secretaría de tu centro"
             if es else "Tens algun dubte? Respon aquest correu: arriba directament a la secretaria del teu centre")
    dubte += f" ({tel})." if tel else "."
    titol_passos = "Qué pasa ahora" if es else "I ara què?"
    boto = "Ver mi matrícula" if es else "Veure la meva matrícula"
    if c.tipus != "matricula":
        boto = "Ver mi compra" if es else "Veure la meva compra"
    html = (f"<p>{_html.escape(intro)}</p>{_taula(resum)}"
            f'<p style="font-weight:700;color:#14224F;margin:16px 0 6px">{titol_passos}</p><ul style="padding-left:18px;margin:0">'
            + "".join(f"<li>{_html.escape(p)}</li>" for p in passos) + "</ul>"
            + (_boto(enllac, boto) if enllac else "") + f"<p>{_html.escape(dubte)}</p>")
    text = (f"{intro}\n\n{_text_taula(resum)}\n\n{titol_passos}\n" + "\n".join(f"- {p}" for p in passos)
            + (f"\n\n{boto}: {enllac}" if enllac else "") + f"\n\n{dubte}\n")
    return assumpte, _html_correu(html, es), text


def correu_equip(db, c):
    centre = c.centre
    tipus = "matrícula" if c.tipus == "matricula" else "compra de pràctiques"
    assumpte = (f"Nova {tipus} web · " + (f"Carnet {c.carnet_codi} · " if c.tipus == "matricula" else "")
                + f"{c.nom_complet} ({centre.nom if centre else 'sense centre'})")
    dades = [("Nom", c.nom_complet), ("DNI/NIE", c.dni),
             ("Data de naixement", c.naixement.strftime("%d/%m/%Y") if c.naixement else ""),
             ("Correu", c.email), ("Telèfon", c.telefon), ("Contactar per", via_contacte(c)),
             ("Adreça", " · ".join(x for x in (c.adreca, f"{c.cp} {c.localitat}".strip()) if x)),
             ("Tutor/a legal", f"{c.tutor_nom} · {c.tutor_dni}" if c.tutor_nom else ""),
             ("Horari preferit", {"MATI": "Matí", "TARDA": "Tarda"}.get(c.franja, c.franja)),
             ("Observacions", c.observacions), ("Idioma", "castellà" if c.idioma == "es" else "català")]
    pagament = [("Centre", centre.nom if centre else ""), ("Producte", c.producte),
                ("Preu", f"{preus.eur2(c.preu_base)} €"),
                ("Descompte", f"{c.promocio} (−{preus.eur2(c.descompte)} €)" if c.descompte else ""),
                ("Taxa DGT", f"{preus.eur2(c.taxa)} €" if c.taxa else ("no pagada" if c.tipus == "matricula" else "")),
                ("Cànon de pistes", f"{preus.eur2(c.canon)} €" if c.canon else ""),
                ("Total pagat", f"{preus.eur2(c.total)} €"), ("Rebut", c.num_rebut),
                ("Pagament Stripe", c.stripe_pagament)]
    base = url_publica()
    enllac = f"{base}/gestio/comanda/{c.id}" if base else ""
    via = via_contacte(c)
    on = {"whatsapp": c.telefon, "trucada": c.telefon, "correu": c.email}.get(c.contacte_preferit or "", "")
    avis_via = {"whatsapp": "Vol que el/la contacteu per WhatsApp", "correu": "Vol que el/la contacteu per correu electrònic",
                "trucada": "Vol que el/la truqueu"}.get(c.contacte_preferit or "", "")
    if avis_via:
        avis_via += (f" ({on})" if on else "") + "."
    html = (f"<p>Hi ha una nova {tipus} pagada a la web. Cal fer la factura a Holded i obrir l'expedient.</p>"
            + (f'<p style="background:#EEF8E4;border:1px solid #cfe8b0;border-radius:10px;padding:10px 14px;'
               f'color:#14224F;font-weight:700">{_html.escape(avis_via)}</p>' if avis_via else "")
            + ""
            f'<p style="font-weight:700;color:#14224F;margin:14px 0 0">Alumne/a</p>{_taula(dades)}'
            f'<p style="font-weight:700;color:#14224F;margin:14px 0 0">Pagament</p>{_taula(pagament)}'
            + (_boto(enllac, "Obrir al panell") if enllac else "")
            + "<p>Si respons aquest correu, la resposta arriba a l'alumne/a.</p>")
    text = (f"Nova {tipus} pagada a la web. Cal fer la factura a Holded i obrir l'expedient.\n"
            + (f"{avis_via}\n" if avis_via else "") + "\nAlumne/a\n"
            f"{_text_taula(dades)}\n\nPagament\n{_text_taula(pagament)}\n"
            + (f"\nPanell: {enllac}\n" if enllac else "") + "\nSi respons aquest correu, la resposta arriba a l'alumne/a.\n")
    return assumpte, _html_correu(html), text


def destinataris_equip(db, c) -> list:
    out = []
    if c.centre and c.centre.email:
        out.append(c.centre.email)
    for e in ajustos.correus_admin(db):
        if e.lower() not in [x.lower() for x in out]:
            out.append(e)
    if not out:
        g = ajustos.correu_general(db)
        if g:
            out.append(g)
    return out


def envia_correus(db, c, nomes=None):
    """Envia els correus de la comanda i n'apunta el resultat. nomes: «alumne» o «equip»."""
    adj = _adjunts(c)
    registre = []
    hora = datetime.now(preus.TZ).strftime("%d/%m/%Y %H:%M")
    if nomes in (None, "alumne"):
        a, h, t = correu_alumne(db, c)
        ok, msg = correu.envia(c.email, a, h, t, adj, respondre_a=(c.centre.email if c.centre else ""))
        registre.append(f"{hora} · alumne ({c.email}): {'OK' if ok else 'NO'} · {msg}")
    if nomes in (None, "equip"):
        a, h, t = correu_equip(db, c)
        dest = destinataris_equip(db, c)
        ok, msg = correu.envia(dest, a, h, t, adj, respondre_a=c.email)
        registre.append(f"{hora} · equip ({', '.join(dest) or '—'}): {'OK' if ok else 'NO'} · {msg}")
    c.correus = ((c.correus or "") + "\n" + "\n".join(registre)).strip()
    db.commit()
    return registre



# ------------------------------------------------------------------ recordatori de matrícula sense pagar
MAX_HORES_RECORDATORI = 48     # només matrícules començades fa menys de 2 dies


def correu_recordatori(db, c):
    es = c.idioma == "es"
    enllac = f"{url_publica()}/matricula/{c.token}/contracte"
    producte = c.producte_en("es" if es else "ca")
    promo = preus.promo_automatica(db, "matricula")
    avis_promo = ""
    if promo and promo.fi:
        dia = preus.local(promo.fi).strftime("%d/%m")
        avis_promo = (f"La promoción {promo.nom} (−{promo.percentatge:g} %) termina el {dia}." if es
                      else f"La promoció {promo.nom} (−{promo.percentatge:g} %) s'acaba el {dia}.")
    if es:
        assumpte = "Tu matrícula está a medias · Autoescoles Rolan"
        p1 = f"¡Hola, {c.nom}! Has empezado la matrícula de {producte} en Autoescoles Rolan, pero aún no la has terminado."
        p2 = "Puedes seguir donde lo dejaste: tus datos ya están guardados."
        boto = "Terminar la matrícula"
        p3 = ("¿Tienes alguna duda? Responde a este correo y te contestará la secretaría de tu centro. "
              "Si ya no te interesa, ignora este mensaje: no te enviaremos más.")
    else:
        assumpte = "La teva matrícula està a mitges · Autoescoles Rolan"
        p1 = f"Hola, {c.nom}! Has començat la matrícula de {producte} a Autoescoles Rolan, però encara no l'has acabada."
        p2 = "Pots continuar on ho vas deixar: les teves dades ja estan desades."
        boto = "Acabar la matrícula"
        p3 = ("Tens algun dubte? Respon aquest correu i et contestarà la secretaria del teu centre. "
              "Si ja no t'interessa, ignora aquest missatge: no te n'enviarem cap més.")
    html = (f"<p>{_html.escape(p1)}</p><p>{_html.escape(p2)}</p>"
            + (f"<p><b>{_html.escape(avis_promo)}</b></p>" if avis_promo else "")
            + _boto(enllac, boto) + f'<p style="color:#66708C">{_html.escape(p3)}</p>')
    text = f"{p1}\n\n{p2}\n" + (f"\n{avis_promo}\n" if avis_promo else "") + f"\n{boto}: {enllac}\n\n{p3}\n"
    return assumpte, _html_correu(html, es), text


def envia_recordatoris(db) -> int:
    """Un sol recordatori per matrícula començada i no pagada (si la persona no n'ha fet cap altra després)."""
    try:
        hores = float((ajustos.get(db, "recordatori_hores", "3") or "0").replace(",", "."))
    except ValueError:
        hores = 0
    if hores <= 0 or not url_publica():
        return 0
    from datetime import timedelta
    ara = datetime.utcnow()
    candidates = (db.query(models.Comanda)
                  .filter(models.Comanda.tipus == "matricula", models.Comanda.estat.in_(["dades", "signada"]),
                          models.Comanda.recordatori_en.is_(None), models.Comanda.email != "",
                          models.Comanda.creat_en <= ara - timedelta(hours=hores),
                          models.Comanda.creat_en >= ara - timedelta(hours=MAX_HORES_RECORDATORI))
                  .order_by(models.Comanda.id).all())
    enviats = 0
    for c in candidates:
        # si després n'ha començat (o pagat) una altra amb el mateix correu, no se li recorda aquesta
        mes_nova = (db.query(models.Comanda).filter(models.Comanda.email == c.email, models.Comanda.id > c.id).first())
        c.recordatori_en = ara
        db.commit()
        if mes_nova:
            continue
        a, h, t = correu_recordatori(db, c)
        ok, msg = correu.envia(c.email, a, h, t, respondre_a=(c.centre.email if c.centre else ""))
        hora = datetime.now(preus.TZ).strftime("%d/%m/%Y %H:%M")
        c.correus = ((c.correus or "") + f"\n{hora} · recordatori ({c.email}): {'OK' if ok else 'NO'} · {msg}").strip()
        db.commit()
        enviats += 1
    return enviats
