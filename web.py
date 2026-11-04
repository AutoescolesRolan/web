"""Pàgines públiques, matrícula, compra de pràctiques, pagament i contacte."""
import calendar
import secrets
import time
from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from . import ajustos, comandes, correu, dni as dnimod, documents, i18n, models, pagaments, preus, telefon
from .db import get_db

router = APIRouter()
ORDRE = ["B", "AM", "A1", "A2", "A"]
MESOS_ABANS_TEORIC = 3      # la DGT deixa fer el primer teòric 3 mesos abans de l'edat del permís


def _r(*a, **k):
    from .main import render
    return render(*a, **k)


def _num(db, clau, defecte):
    try:
        return float((ajustos.get(db, clau, str(defecte)) or str(defecte)).replace(",", "."))
    except ValueError:
        return float(defecte)


def _suma_mesos(d: date, mesos: int) -> date:
    m = d.month - 1 + mesos
    a, mes = d.year + m // 12, m % 12 + 1
    return date(a, mes, min(d.day, calendar.monthrange(a, mes)[1]))


def _edat(naix: date, avui: date = None) -> int:
    avui = avui or date.today()
    return avui.year - naix.year - ((avui.month, avui.day) < (naix.month, naix.day))


def _tel(v, pais):
    try:
        return telefon.normalitza(v, pais or "34", obligatori=True)
    except ValueError:
        return ""


def _dni(v):
    try:
        return dnimod.normalitza(v, obligatori=True)
    except ValueError:
        return ""


def _data(txt):
    try:
        return datetime.strptime((txt or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


# ------------------------------------------------------------------ preus per a les plantilles
def preus_carnets_web(db) -> dict:
    """Preus de la web (inici, /preus i matrícula), amb la promoció vigent si n'hi ha."""
    taxa, taxa_a, canon = _num(db, "taxa_dgt", 94.05), _num(db, "taxa_dgt_a", 28.87), _num(db, "canon_pistes", 33)
    promo = preus.promo_automatica(db, "matricula")
    pct = float(promo.percentatge or 0) if promo else 0
    out = {}
    for c in db.query(models.Carnet).filter(models.Carnet.actiu == True).all():
        packs = sorted([p for p in c.packs if p.actiu and p.preu > 0], key=lambda p: (p.preu, p.id))
        llista = []
        for p in packs:
            final = round(p.preu * (1 - pct / 100), 2)
            llista.append({"id": p.id, "nom": p.nom_ca, "nom_es": p.nom_es, "curt": p.nom_ca.split(" · ")[0].strip(),
                           "preu": float(p.preu), "preu_txt": preus.eur(final), "preu_abans": preus.eur(p.preu) if pct else "",
                           "codigo": p.codi, "classes": p.classes, "destacat": bool(p.destacat)})
        des_de = min((round(p.preu * (1 - pct / 100), 2) for p in packs), default=0)
        des_de_abans = min((p.preu for p in packs), default=0)
        codi = c.codi.upper()
        taxa_txt = preus.eur(taxa_a if codi == "A" else taxa)
        canon_txt = "" if codi == "B" else preus.eur(canon)
        out[codi] = {"packs": llista, "des_de": des_de, "des_de_txt": preus.eur(des_de),
                     "des_de_abans": preus.eur(des_de_abans) if pct else "", "unic": len(llista) <= 1,
                     "taxa_txt": taxa_txt, "canon_txt": canon_txt}
    out["_expedient"] = preus.eur(_num(db, "preu_expedient", 125))
    out["_taxa"] = preus.eur(taxa)
    out["_promo"] = promo
    return out


def _packs_practiques(db):
    promo = preus.promo_automatica(db, "practiques")
    pct = float(promo.percentatge or 0) if promo else 0
    out = []
    for p in (db.query(models.PackPractiques).filter(models.PackPractiques.actiu == True)
              .order_by(models.PackPractiques.classes, models.PackPractiques.franja).all()):
        out.append({"id": p.id, "classes": p.classes, "franja": p.franja, "preu": p.preu,
                    "preu_txt": preus.eur(round(p.preu * (1 - pct / 100), 2)),
                    "preu_abans": preus.eur(p.preu) if pct else ""})
    return out, promo


def clau_maps(db) -> str:
    """Clau de Google Maps per completar l'adreça mentre s'escriu (la mateixa que a l'ERP)."""
    import os
    return (os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip() or ajustos.get(db, "google_maps_api_key")


def _centres(db):
    return db.query(models.Centre).filter(models.Centre.actiu == True).order_by(models.Centre.ordre).all()


# ------------------------------------------------------------------ pàgines
@router.get("/", response_class=HTMLResponse)
def inici(request: Request, db: Session = Depends(get_db)):
    return _r(request, "web/home.html", {"pw": preus_carnets_web(db), "centres": _centres(db)}, db=db)


@router.get("/preus", response_class=HTMLResponse)
def preus_pagina(request: Request, carnet: str = "", db: Session = Depends(get_db)):
    sel = (carnet or "").strip().upper()
    if sel not in ORDRE:
        sel = ""
    packs, _ = _packs_practiques(db)
    carnets = {c.codi: c for c in db.query(models.Carnet).filter(models.Carnet.actiu == True).all()}
    desglossament = [{"codi": codi, "carnet": carnets[codi],
                      "classes": ajustos.tarifes(db, f"tarifes_classes_{codi}"),
                      "examens": ajustos.tarifes(db, f"tarifes_examens_{codi}"),
                      "packs": packs if codi == "B" else []}
                     for codi in ORDRE if codi in carnets]
    return _r(request, "web/preus.html", {"pw": preus_carnets_web(db), "sel": sel, "desglossament": desglossament},
              db=db)


@router.get("/centres")
def centres_pagina():
    return RedirectResponse("/#centres", status_code=301)


@router.get("/qui-som", response_class=HTMLResponse)
def qui_som(request: Request, db: Session = Depends(get_db)):
    return _r(request, "web/qui_som.html", {}, db=db)


@router.get("/avis-legal", response_class=HTMLResponse)
def avis_legal(request: Request, db: Session = Depends(get_db)):
    return _r(request, "web/legal_avis.html", {}, db=db)


@router.get("/privacitat", response_class=HTMLResponse)
def privacitat(request: Request, db: Session = Depends(get_db)):
    return _r(request, "web/legal_privacitat.html", {}, db=db)


@router.get("/cookies", response_class=HTMLResponse)
def cookies(request: Request, db: Session = Depends(get_db)):
    return _r(request, "web/legal_cookies.html", {}, db=db)


@router.get("/condicions", response_class=HTMLResponse)
def condicions(request: Request, db: Session = Depends(get_db)):
    return _r(request, "web/legal_condicions.html", {}, db=db)


# ------------------------------------------------------------------ contacte
_ENVIAMENTS = {}


def _massa_enviaments(ip: str) -> bool:
    ara = time.time()
    llista = [t for t in _ENVIAMENTS.get(ip, []) if ara - t < 600]
    _ENVIAMENTS[ip] = llista
    if len(llista) >= 5:
        return True
    llista.append(ara)
    return False


def _ip(request):
    return (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or (
        request.client.host if request.client else "")


@router.get("/contacte", response_class=HTMLResponse)
def contacte(request: Request, centre: str = "", db: Session = Depends(get_db)):
    return _r(request, "web/contacte.html", {"centres": _centres(db), "dades": {"centre": centre}}, db=db)


@router.post("/contacte", response_class=HTMLResponse)
async def contacte_envia(request: Request, db: Session = Depends(get_db)):
    f = await request.form()
    d = {k: (f.get(k) or "").strip() for k in ("centre", "nom", "email", "telefon", "text", "web")}
    ctx = {"centres": _centres(db), "dades": d}
    if d["web"]:                      # camp trampa: només l'omplen els robots
        return _r(request, "web/contacte.html", {**ctx, "fet": True}, db=db)
    centre = db.query(models.Centre).filter(models.Centre.codi == d["centre"]).first()
    if not (centre and d["nom"] and "@" in d["email"] and len(d["text"]) >= 5) or f.get("accepta") != "1":
        return _r(request, "web/contacte.html", {**ctx, "err": "camps"}, db=db, status_code=400)
    if _massa_enviaments(_ip(request)):
        return _r(request, "web/contacte.html", {**ctx, "err": "massa"}, db=db, status_code=429)
    m = models.Missatge(centre_id=centre.id, nom=d["nom"][:160], email=d["email"][:160],
                        telefon=d["telefon"][:40], text=d["text"][:5000])
    db.add(m)
    db.commit()
    from html import escape
    cos = (f"<p><b>{escape(m.nom)}</b> ha escrit des de la web ({escape(centre.nom)}):</p>"
           f'<blockquote style="border-left:3px solid #8BC53F;margin:10px 0;padding:6px 12px;color:#14224F">'
           f'{escape(m.text).replace(chr(10), "<br>")}</blockquote>'
           f"<p>Correu: {escape(m.email)}<br>Telèfon: {escape(m.telefon or '—')}</p>"
           "<p>Respon aquest correu i la resposta li arriba directament.</p>")
    text = (f"{m.nom} ha escrit des de la web ({centre.nom}):\n\n{m.text}\n\nCorreu: {m.email}\n"
            f"Telèfon: {m.telefon or '—'}\n\nRespon aquest correu i la resposta li arriba directament.\n")
    dest = [centre.email] if centre.email else ajustos.correus_admin(db)
    ok, msg = correu.envia(dest, f"Consulta web · {m.nom} ({centre.nom})", comandes._html_correu(cos), text,
                           respondre_a=m.email)
    m.enviat = f"{'OK' if ok else 'NO'} · {msg}"[:200]
    db.commit()
    return _r(request, "web/contacte.html", {**ctx, "fet": True}, db=db)


# ------------------------------------------------------------------ matrícula
def _cataleg(db, carnet=""):
    out = []
    for c in db.query(models.Carnet).filter(models.Carnet.actiu == True).order_by(models.Carnet.ordre).all():
        if carnet and c.codi != carnet:
            continue
        packs = [p for p in c.packs if p.actiu and p.preu > 0]
        if packs:
            out.append({"carnet": c, "packs": packs})
    return out


def _ctx_matricula(db, request, carnet="", pack="", dades=None, err="", extra=None):
    carnet = (carnet or "").upper()
    if carnet not in ORDRE:
        carnet = ""
    p = db.query(models.Pack).filter(models.Pack.codi == pack).first() if pack else None
    pw = preus_carnets_web(db)
    ctx = {"cataleg": _cataleg(db, carnet), "carnet_sel": db.query(models.Carnet).filter(models.Carnet.codi == carnet).first() if carnet else None,
           "seccions": _centres(db), "pack_actual": p.id if p else (int(dades.get("pack_id") or 0) if dades and (dades.get("pack_id") or "").isdigit() else None),
           "dades": dades or {}, "err": err, "pw": pw, "promo": pw["_promo"],
           "taxa_dgt": _num(db, "taxa_dgt", 94.05), "taxa_dgt_a": _num(db, "taxa_dgt_a", 28.87),
           "canon_pistes": _num(db, "canon_pistes", 33),
           "stripe_on": pagaments.configurat(), "stripe_test": pagaments.mode_proves(),
           "avui_iso": date.today().isoformat(), "maps_api_key": clau_maps(db)}
    ctx.update(extra or {})
    return ctx


@router.get("/matricula", response_class=HTMLResponse)
def matricula(request: Request, carnet: str = "", pack: str = "", db: Session = Depends(get_db)):
    if pack and not carnet:
        p = db.query(models.Pack).filter(models.Pack.codi == pack).first()
        carnet = p.carnet.codi if p else ""
    return _r(request, "web/matricula.html", _ctx_matricula(db, request, carnet, pack), db=db)


@router.post("/matricula", response_class=HTMLResponse)
async def matricula_desa(request: Request, db: Session = Depends(get_db)):
    f = await request.form()
    camps = ("seccion", "pack_id", "nom", "cognoms", "email", "telefon", "telefon__pais", "dni", "naixement",
             "data_a2", "adreca", "adreca2", "cp", "poblacio", "tutor_nom", "tutor_dni", "tutor_accepta",
             "incloure_taxa", "incloure_canon", "codi_promo", "franja", "observacions", "web", "carnet_url")
    d = {k: (f.get(k) or "").strip() for k in camps}

    def error(codi, **extra):
        return _r(request, "web/matricula.html",
                  _ctx_matricula(db, request, d["carnet_url"], "", d, codi, extra), db=db, status_code=400)

    if d["web"]:
        return RedirectResponse("/", status_code=303)
    pack = db.get(models.Pack, int(d["pack_id"])) if d["pack_id"].isdigit() else None
    centre = db.query(models.Centre).filter(models.Centre.codi == d["seccion"], models.Centre.actiu == True).first()
    falta = [nom for ok, nom in (
        (centre, "el centre"), (pack and pack.actiu, "el pack"), (d["nom"], "el nom"), (d["cognoms"], "els cognoms"),
        ("@" in d["email"], "el correu"), (d["adreca"], "l'adreça"), (d["cp"], "el codi postal"),
        (d["poblacio"], "la població")) if not ok]
    if falta:
        return error("camps", falta=falta)
    tel = _tel(d["telefon"], d["telefon__pais"])
    if not tel:
        return error("telefon")
    dni = _dni(d["dni"])
    if not dni:
        return error("dni")
    naix = _data(d["naixement"])
    if not naix or naix >= date.today() or naix.year < 1920:
        return error("naix")
    carnet = pack.carnet
    obre = _suma_mesos(naix, carnet.edat * 12 - MESOS_ABANS_TEORIC)
    if obre > date.today():
        return error("edat", edat_min_msg=carnet.edat, edat_des_de=obre.strftime("%d/%m/%Y"))
    obs = []
    if carnet.codi == "A":
        a2 = _data(d["data_a2"])
        if not a2:
            return error("a2_buit")
        if a2 > date.today():
            return error("a2_futur")
        if _edat(naix, a2) < 18:
            return error("a2_impossible")
        des_de = _suma_mesos(a2, 24)
        if des_de > date.today():
            return error("a2_falten", des_de=des_de.strftime("%d/%m/%Y"))
        obs.append(f"Permís A2 des del {a2.strftime('%d/%m/%Y')}")
    tutor_nom, tutor_dni = "", ""
    if _edat(naix) < 18:
        if not (d["tutor_nom"] and d["tutor_dni"] and d["tutor_accepta"] == "1"):
            return error("tutor")
        tutor_dni = _dni(d["tutor_dni"])
        if not tutor_dni:
            return error("dni")
        tutor_nom = d["tutor_nom"]
    calc = preus.calcula(db, pack.preu, "matricula", d["codi_promo"])
    if d["codi_promo"] and calc["codi_valid"] is False:
        return error("codi")
    es_moto = carnet.codi in ("AM", "A1", "A2", "A")
    taxa = (_num(db, "taxa_dgt_a", 28.87) if carnet.codi == "A" else _num(db, "taxa_dgt", 94.05)) \
        if d["incloure_taxa"] == "1" else 0
    canon = _num(db, "canon_pistes", 33) if (es_moto and d["incloure_canon"] == "1") else 0
    if d["observacions"]:
        obs.append(d["observacions"][:1000])
    adreca = ", ".join(x for x in (d["adreca"], d["adreca2"]) if x)
    ll = i18n.get_idioma(request)
    c = models.Comanda(
        token=secrets.token_urlsafe(24), tipus="matricula", estat="dades", idioma=ll, centre_id=centre.id,
        carnet_codi=carnet.codi, pack_id=pack.id, producte=f"Carnet {carnet.codi} · {pack.nom_ca}", producte_es=f"Carnet {carnet.codi} · {pack.nom_es}",
        preu_base=calc["preu_base"], descompte=calc["descompte"], promocio=calc["promocio"],
        taxa=taxa, canon=canon, total=round(calc["total"] + taxa + canon, 2),
        franja=d["franja"] if d["franja"] in ("MATI", "TARDA") else "",
        nom=d["nom"][:120], cognoms=d["cognoms"][:160], dni=dni, naixement=naix, email=d["email"][:160],
        telefon=tel, adreca=adreca[:200], cp=d["cp"][:10], localitat=d["poblacio"][:120],
        tutor_nom=tutor_nom[:200], tutor_dni=tutor_dni, observacions="\n".join(obs))
    db.add(c)
    db.commit()
    request.session["comanda"] = c.token
    return RedirectResponse(f"/matricula/{c.token}/contracte", status_code=303)


def _te_traç(firma: str) -> bool:
    """La signatura té algun traç (no és una imatge buida)."""
    import base64
    import io
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(base64.b64decode(firma.split(",", 1)[1])))
        im.load()
        alfa = im.getchannel("A") if "A" in im.getbands() else im.convert("L").point(lambda v: 255 - v)
        caixa = alfa.point(lambda v: 255 if v > 40 else 0).getbbox()
        return bool(caixa) and (caixa[2] - caixa[0]) >= 15
    except Exception:
        return False


def _comanda(db, token, tipus=None):
    c = db.query(models.Comanda).filter(models.Comanda.token == token).first() if token and len(token) > 20 else None
    if c and tipus and c.tipus != tipus:
        return None
    return c


def _pack(db, c):
    return db.get(models.Pack, c.pack_id) if c.pack_id else None


@router.get("/matricula/{token}/contracte", response_class=HTMLResponse)
def contracte(token: str, request: Request, cancelat: str = "", err: str = "", db: Session = Depends(get_db)):
    c = _comanda(db, token, "matricula")
    if not c:
        return RedirectResponse("/matricula", status_code=303)
    if c.estat == "pagada":
        return RedirectResponse(f"/comanda/{c.token}", status_code=303)
    pack = _pack(db, c)
    return _r(request, "web/contracte.html", {
        "c": c, "pack": pack, "carnet": pack.carnet if pack else None, "menor": bool(c.tutor_nom),
        "cancelat": cancelat, "err": err, "stripe_on": pagaments.configurat(),
        "stripe_test": pagaments.mode_proves()}, db=db)


@router.get("/matricula/{token}/contracte.pdf")
def contracte_pdf(token: str, db: Session = Depends(get_db)):
    """El contracte per llegir-lo abans de signar (sense signatura)."""
    c = _comanda(db, token, "matricula")
    if not c:
        return Response(status_code=404)
    if c.contracte_pdf:
        dades = c.contracte_pdf
    else:
        dades = documents.contracte_pdf(db, c, _pack(db, c))
    return Response(dades, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{documents.nom_contracte(c)}"'})


@router.post("/matricula/{token}/contracte")
async def contracte_signa(token: str, request: Request, db: Session = Depends(get_db)):
    c = _comanda(db, token, "matricula")
    if not c:
        return RedirectResponse("/matricula", status_code=303)
    if c.estat == "pagada":
        return RedirectResponse(f"/comanda/{c.token}", status_code=303)
    f = await request.form()
    firma = (f.get("firma") or "").strip()
    if c.estat != "signada":
        if not (firma.startswith("data:image/png;base64,") and 200 < len(firma) < 600_000 and _te_traç(firma)
                and f.get("accepta") == "1" and f.get("accepta_condicions") == "1"
                and f.get("consent_imatge") in ("si", "no") and f.get("consent_comercial") in ("si", "no")
                and f.get("contacte") in comandes.VIES_CONTACTE):
            return RedirectResponse(f"/matricula/{c.token}/contracte?err=camps", status_code=303)
        c.contacte_preferit = f.get("contacte")
        c.signatura = firma
        c.signat_en = datetime.utcnow()
        c.ip_signatura = _ip(request)[:64]
        c.acceptacions = ";".join([f"imatge={f.get('consent_imatge')}", f"comercial={f.get('consent_comercial')}",
                                   "contracte=si", "condicions=si"])
        c.contracte_pdf = documents.contracte_pdf(db, c, _pack(db, c))
        c.estat = "signada"
        db.commit()
    return _a_pagar(request, db, c)


def _linies(c):
    linies = [(c.producte + (f" · {c.promocio}" if c.descompte else ""), round(c.preu_base - c.descompte, 2))]
    if c.taxa:
        linies.append(("Taxa oficial DGT", c.taxa))
    if c.canon:
        linies.append(("Cànon de pistes", c.canon))
    return linies


def _base(request):
    return (comandes.url_publica() or str(request.base_url)).rstrip("/")


def _a_pagar(request, db, c):
    if c.tipus == "practiques" and not VENDA_PRACTIQUES:
        return RedirectResponse("/preus", status_code=303)
    tornada = f"/matricula/{c.token}/contracte" if c.tipus == "matricula" else f"/practiques/{c.token}"
    if not pagaments.configurat():
        return RedirectResponse(f"{tornada}?err=nopago", status_code=303)
    try:
        base = _base(request)
        sess = pagaments.crea_sessio(c, _linies(c), url_ok=f"{base}/pagament/{c.token}/ok?session_id={{CHECKOUT_SESSION_ID}}",
                                     url_cancel=f"{base}{tornada}?cancelat=1")
    except Exception as e:
        print(f"[stripe] no s'ha pogut crear la sessió de la comanda {c.id}: {e}")
        return RedirectResponse(f"{tornada}?err=pagament", status_code=303)
    c.stripe_sessio = sess.id
    db.commit()
    return RedirectResponse(sess.url, status_code=303)


@router.get("/pagament-demo/{sid}", response_class=HTMLResponse)
def pagament_demo(sid: str, request: Request, accio: str = "", db: Session = Depends(get_db)):
    """Pàgina de pagament simulada (només per veure la web a l'ordinador, amb ROLAN_DEMO=1)."""
    s = pagaments.sessio_demo(sid)
    if not s:
        return RedirectResponse("/", status_code=303)
    if accio == "paga":
        s["payment_status"] = "paid"
        return RedirectResponse(s["url_ok"], status_code=303)
    if accio == "cancela":
        return RedirectResponse(s["url_cancel"], status_code=303)
    c = _comanda(db, s["metadata"]["comanda"])
    return _r(request, "web/pagament_demo.html", {"s": s, "c": c}, db=db)


@router.post("/pagament/{token}")
def torna_a_pagar(token: str, request: Request, db: Session = Depends(get_db)):
    c = _comanda(db, token)
    if not c:
        return RedirectResponse("/", status_code=303)
    if c.estat == "pagada":
        return RedirectResponse(f"/comanda/{c.token}", status_code=303)
    if c.estat != "signada":
        return RedirectResponse(f"/matricula/{c.token}/contracte" if c.tipus == "matricula" else "/preus", status_code=303)
    return _a_pagar(request, db, c)


@router.get("/pagament/{token}/ok")
def pagament_ok(token: str, request: Request, session_id: str = "", db: Session = Depends(get_db)):
    c = _comanda(db, token)
    if not c:
        return RedirectResponse("/", status_code=303)
    if c.estat != "pagada":
        try:
            sess = pagaments.recupera(session_id) if session_id and pagaments.configurat() else None
        except Exception as e:
            print(f"[stripe] no s'ha pogut comprovar la sessió {session_id}: {e}")
            sess = None
        if sess is not None and pagaments.sessio_pagada(sess, c, c.total):
            c.stripe_sessio = session_id
            db.commit()
            comandes.tanca(db, c, pagaments.id_pagament(sess))
        else:
            return _r(request, "web/pagament_pendent.html", {"c": c}, db=db)
    return RedirectResponse(f"/comanda/{c.token}?nou=1", status_code=303)


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    try:
        ev = pagaments.webhook_event(payload, request.headers.get("stripe-signature", ""))
    except Exception as e:
        print(f"[stripe] webhook rebutjat: {e}")
        return Response(status_code=400)
    if ev is None:
        return Response(status_code=400)
    g = pagaments._get
    if g(ev, "type") in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        sess = g(g(ev, "data"), "object")
        token = g(g(sess, "metadata") or {}, "comanda", "") or ""
        c = _comanda(db, token)
        if c and c.estat != "pagada" and pagaments.sessio_pagada(sess, c, c.total):
            c.stripe_sessio = g(sess, "id", c.stripe_sessio) or c.stripe_sessio
            db.commit()
            comandes.tanca(db, c, pagaments.id_pagament(sess))
    return {"ok": True}


# ------------------------------------------------------------------ pàgina privada de la comanda
@router.get("/comanda/{token}", response_class=HTMLResponse)
def comanda(token: str, request: Request, nou: str = "", db: Session = Depends(get_db)):
    c = _comanda(db, token)
    if not c:
        return _r(request, "web/no_trobat.html", {}, db=db, status_code=404)
    if c.estat != "pagada":
        if c.tipus == "matricula":
            return RedirectResponse(f"/matricula/{c.token}/contracte", status_code=303)
        return RedirectResponse(f"/practiques/{c.token}", status_code=303)
    return _r(request, "web/comanda.html", {"c": c, "nou": nou == "1"}, db=db)


@router.get("/comanda/{token}/{doc}.pdf")
def comanda_doc(token: str, doc: str, db: Session = Depends(get_db)):
    c = _comanda(db, token)
    if not c or c.estat != "pagada":
        return Response(status_code=404)
    if doc == "contracte" and c.contracte_pdf:
        return Response(c.contracte_pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{documents.nom_contracte(c)}"'})
    if doc == "rebut":
        if not c.rebut_pdf:
            c.rebut_pdf = documents.rebut_pdf(db, c)
            db.commit()
        return Response(c.rebut_pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{documents.nom_rebut(c)}"'})
    return Response(status_code=404)


# ------------------------------------------------------------------ pràctiques
# Decisió de l'escola (nov. 2026): els packs de pràctiques NO es venen a la web, perquè només els ha de
# poder pagar qui ja està matriculat (es paguen al centre). El codi es conserva per si es reactiva.
VENDA_PRACTIQUES = False


@router.get("/practiques", response_class=HTMLResponse)
def practiques(request: Request, pack: int = 0, db: Session = Depends(get_db)):
    if not VENDA_PRACTIQUES:
        return RedirectResponse("/preus", status_code=303)
    packs, promo = _packs_practiques(db)
    return _r(request, "web/practiques.html", {"packs": packs, "promo": promo, "seccions": _centres(db),
                                                "dades": {"pack_id": str(pack) if pack else ""},
                                                "stripe_on": pagaments.configurat(),
                                                "stripe_test": pagaments.mode_proves()}, db=db)


@router.post("/practiques", response_class=HTMLResponse)
async def practiques_desa(request: Request, db: Session = Depends(get_db)):
    if not VENDA_PRACTIQUES:
        return RedirectResponse("/preus", status_code=303)
    f = await request.form()
    d = {k: (f.get(k) or "").strip() for k in ("pack_id", "seccion", "nom", "cognoms", "email", "telefon",
                                               "telefon__pais", "dni", "codi_promo", "observacions", "web")}
    packs, promo = _packs_practiques(db)

    def error(codi):
        return _r(request, "web/practiques.html", {"packs": packs, "promo": promo, "seccions": _centres(db),
                                                    "dades": d, "err": codi, "stripe_on": pagaments.configurat(),
                                                    "stripe_test": pagaments.mode_proves()}, db=db, status_code=400)

    if d["web"]:
        return RedirectResponse("/", status_code=303)
    p = db.get(models.PackPractiques, int(d["pack_id"])) if d["pack_id"].isdigit() else None
    centre = db.query(models.Centre).filter(models.Centre.codi == d["seccion"], models.Centre.actiu == True).first()
    if not (p and p.actiu and centre and d["nom"] and d["cognoms"] and "@" in d["email"]
            and f.get("accepta_condicions") == "1"):
        return error("camps")
    tel = _tel(d["telefon"], d["telefon__pais"])
    if not tel:
        return error("telefon")
    dni = _dni(d["dni"])
    if not dni:
        return error("dni")
    calc = preus.calcula(db, p.preu, "practiques", d["codi_promo"])
    if d["codi_promo"] and calc["codi_valid"] is False:
        return error("codi")
    franja = {"MATI": "matí", "TARDA": "tarda"}.get(p.franja, p.franja.lower())
    franja_es = {"MATI": "mañana", "TARDA": "tarde"}.get(p.franja, p.franja.lower())
    c = models.Comanda(
        token=secrets.token_urlsafe(24), tipus="practiques", estat="signada", idioma=i18n.get_idioma(request),
        centre_id=centre.id, carnet_codi="B", pack_id=None, producte=f"Pack de {p.classes} pràctiques de {franja}",
        producte_es=f"Pack de {p.classes} prácticas de {franja_es}",
        preu_base=calc["preu_base"], descompte=calc["descompte"], promocio=calc["promocio"], total=calc["total"],
        franja=p.franja, nom=d["nom"][:120], cognoms=d["cognoms"][:160], dni=dni, email=d["email"][:160],
        telefon=tel, observacions=d["observacions"][:1000],
        acceptacions="condicions=si")
    db.add(c)
    db.commit()
    return _a_pagar(request, db, c)


@router.get("/practiques/{token}", response_class=HTMLResponse)
def practiques_comanda(token: str, request: Request, cancelat: str = "", err: str = "", db: Session = Depends(get_db)):
    c = _comanda(db, token, "practiques")
    if not c:
        return RedirectResponse("/preus", status_code=303)
    if c.estat == "pagada":
        return RedirectResponse(f"/comanda/{c.token}", status_code=303)
    if not VENDA_PRACTIQUES:
        return RedirectResponse("/preus", status_code=303)
    return _r(request, "web/practiques_pagar.html", {"c": c, "cancelat": cancelat, "err": err,
                                                      "stripe_on": pagaments.configurat()}, db=db)
