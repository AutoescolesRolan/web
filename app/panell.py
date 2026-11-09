"""Panell intern (/gestio): matrícules i compres rebudes, missatges, preus, promocions,
centres, dades de l'autoescola i usuaris. Només admin i secretàries."""
import io
import os
import secrets
import time
import hashlib
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import ajustos, comandes, documents, models, preus
from .db import get_db

router = APIRouter(prefix="/gestio")


def _r(request, nom, ctx, db, status_code=200):
    from .main import render
    ctx = dict(ctx)
    ctx.setdefault("u", usuari(request, db))
    ctx.setdefault("csrf", _csrf(request))
    return render(request, nom, ctx, db=db, status_code=status_code)


# ------------------------------------------------------------------ accés
def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def comprova_pw(pw: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), (h or "").encode())
    except Exception:
        return False


def primer_admin(db):
    """Crea el primer admin amb ADMIN_EMAIL i ADMIN_PASSWORD (només si encara no hi ha cap usuari)."""
    if db.query(models.Usuari).first():
        return
    email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
    pw = os.environ.get("ADMIN_PASSWORD") or ""
    if email and len(pw) >= 10:
        db.add(models.Usuari(email=email, nom="Admin", contrasenya=hash_pw(pw), rol="admin"))
        db.commit()
        print(f"[panell] creat l'usuari admin {email}")


def usuari(request, db):
    uid = request.session.get("uid")
    u = db.get(models.Usuari, uid) if uid else None
    return u if u and u.actiu else None


def _csrf(request):
    t = request.session.get("csrf")
    if not t:
        t = secrets.token_urlsafe(24)
        request.session["csrf"] = t
    return t


async def _form(request):
    f = await request.form()
    if not secrets.compare_digest(str(f.get("csrf") or ""), str(request.session.get("csrf") or "")):
        return None
    return f


class _Fora(Exception):
    pass


def _cal(request, db, admin=False):
    u = usuari(request, db)
    if not u or (admin and u.rol != "admin"):
        raise _Fora()
    return u


def _redir_login():
    return RedirectResponse("/gestio/entrar", status_code=303)


_INTENTS = {}


@router.get("/entrar", response_class=HTMLResponse)
def entrar(request: Request, db: Session = Depends(get_db)):
    return _r(request, "panell/entrar.html", {}, db)


@router.post("/entrar", response_class=HTMLResponse)
async def entrar_post(request: Request, db: Session = Depends(get_db)):
    f = await request.form()
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or (request.client.host if request.client else "")
    ara = time.time()
    intents = [t for t in _INTENTS.get(ip, []) if ara - t < 900]
    if len(intents) >= 8:
        return _r(request, "panell/entrar.html", {"err": "massa"}, db, 429)
    email = (f.get("email") or "").strip().lower()
    u = db.query(models.Usuari).filter(models.Usuari.email == email, models.Usuari.actiu == True).first()
    if not u or not comprova_pw(f.get("contrasenya") or "", u.contrasenya):
        intents.append(ara)
        _INTENTS[ip] = intents
        return _r(request, "panell/entrar.html", {"err": "dades", "email": email}, db, 401)
    _INTENTS.pop(ip, None)
    request.session.clear()
    if dos_factors_actiu() and not _dispositiu_confiat(request, db, u):
        if not _envia_codi(db, u):
            return _r(request, "panell/entrar.html", {"err": "correu", "email": email}, db, 503)
        request.session["pendent_uid"] = u.id
        request.session["pendent_des_de"] = int(ara)
        return RedirectResponse("/gestio/codi", status_code=303)
    request.session["uid"] = u.id
    return RedirectResponse("/gestio", status_code=303)


# ------------------------------------------------------------------ segon factor (codi per correu)
MINUTS_CODI = 10
INTENTS_CODI = 5
DIES_DISPOSITIU = 30
COOKIE_DISPOSITIU = "rolan_gestio_disp"


def dos_factors_actiu() -> bool:
    """El codi per correu es demana sempre que el correu estigui configurat (es pot apagar amb DOS_FACTORS=off)."""
    from . import correu
    if (os.environ.get("DOS_FACTORS") or "").strip().lower() in ("0", "off", "no", "false"):
        return False
    return correu.configurat()


def _hash(*parts) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _envia_codi(db, u) -> bool:
    from . import correu
    db.query(models.CodiAcces).filter(models.CodiAcces.usuari_id == u.id,
                                      models.CodiAcces.usat == False).update({"usat": True})
    codi = f"{secrets.randbelow(1_000_000):06d}"
    sal = secrets.token_hex(16)
    db.add(models.CodiAcces(usuari_id=u.id, sal=sal, hash=_hash(sal, codi),
                            caduca=datetime.utcnow() + timedelta(minutes=MINUTS_CODI)))
    db.commit()
    cos = (f"<p>Hola{', ' + u.nom if u.nom else ''}!</p><p>El teu codi per entrar al panell de la web és:</p>"
           f'<p style="font-size:30px;font-weight:800;letter-spacing:6px;color:#14224F;margin:14px 0">{codi}</p>'
           f"<p>Caduca d'aquí a {MINUTS_CODI} minuts. Si no has intentat entrar tu, canvia la contrasenya i avisa l'admin.</p>")
    text = (f"El teu codi per entrar al panell de la web és: {codi}\n\nCaduca d'aquí a {MINUTS_CODI} minuts. "
            "Si no has intentat entrar tu, canvia la contrasenya i avisa l'admin.\n")
    ok, msg = correu.envia(u.email, "Codi d'accés al panell · Autoescoles Rolan",
                           comandes._html_correu(cos), text)
    if not ok:
        print(f"[panell] no s'ha pogut enviar el codi d'accés a {u.email}: {msg}")
    return ok


def _dispositiu_confiat(request, db, u) -> bool:
    tok = request.cookies.get(COOKIE_DISPOSITIU) or ""
    if not tok:
        return False
    d = db.query(models.DispositiuConfiat).filter(models.DispositiuConfiat.hash == _hash("disp", tok)).first()
    return bool(d and d.usuari_id == u.id and d.caduca > datetime.utcnow())


def _pendent(request, db):
    uid = request.session.get("pendent_uid")
    des_de = request.session.get("pendent_des_de") or 0
    if not uid or time.time() - des_de > MINUTS_CODI * 60 * 3:
        return None
    u = db.get(models.Usuari, uid)
    return u if u and u.actiu else None


def _amaga(email):
    nom, _, dom = email.partition("@")
    return (nom[:2] + "•" * max(1, len(nom) - 2)) + "@" + dom


@router.get("/codi", response_class=HTMLResponse)
def codi(request: Request, err: str = "", reenviat: str = "", db: Session = Depends(get_db)):
    u = _pendent(request, db)
    if not u:
        return _redir_login()
    return _r(request, "panell/codi.html", {"correu_amagat": _amaga(u.email), "err": err, "reenviat": reenviat,
                                             "dies": DIES_DISPOSITIU, "minuts": MINUTS_CODI}, db)


@router.post("/codi")
async def codi_post(request: Request, db: Session = Depends(get_db)):
    u = _pendent(request, db)
    if not u:
        return _redir_login()
    f = await request.form()
    if f.get("accio") == "reenvia":
        darrer = (db.query(models.CodiAcces).filter(models.CodiAcces.usuari_id == u.id)
                  .order_by(models.CodiAcces.id.desc()).first())
        if darrer and (datetime.utcnow() - darrer.creat_en).total_seconds() < 60:
            return RedirectResponse("/gestio/codi?err=espera", status_code=303)
        if not _envia_codi(db, u):
            return RedirectResponse("/gestio/codi?err=correu", status_code=303)
        request.session["pendent_des_de"] = int(time.time())
        return RedirectResponse("/gestio/codi?reenviat=1", status_code=303)
    escrit = "".join(ch for ch in str(f.get("codi") or "") if ch.isdigit())
    c = (db.query(models.CodiAcces).filter(models.CodiAcces.usuari_id == u.id, models.CodiAcces.usat == False)
         .order_by(models.CodiAcces.id.desc()).first())
    if not c or c.caduca < datetime.utcnow() or c.intents >= INTENTS_CODI:
        return RedirectResponse("/gestio/codi?err=caducat", status_code=303)
    if not secrets.compare_digest(_hash(c.sal, escrit), c.hash):
        c.intents += 1
        if c.intents >= INTENTS_CODI:
            c.usat = True
        db.commit()
        return RedirectResponse("/gestio/codi?err=" + ("caducat" if c.usat else "codi"), status_code=303)
    c.usat = True
    request.session.clear()
    request.session["uid"] = u.id
    resp = RedirectResponse("/gestio", status_code=303)
    if f.get("recorda") == "1":
        tok = secrets.token_urlsafe(32)
        db.add(models.DispositiuConfiat(usuari_id=u.id, hash=_hash("disp", tok),
                                        caduca=datetime.utcnow() + timedelta(days=DIES_DISPOSITIU)))
        resp.set_cookie(COOKIE_DISPOSITIU, tok, max_age=DIES_DISPOSITIU * 86400, httponly=True, samesite="lax",
                        secure=os.environ.get("HTTPS_ONLY", "").lower() in ("1", "true", "si"), path="/gestio")
    db.query(models.DispositiuConfiat).filter(models.DispositiuConfiat.caduca < datetime.utcnow()).delete()
    db.query(models.CodiAcces).filter(models.CodiAcces.caduca < datetime.utcnow() - timedelta(days=1)).delete()
    db.commit()
    return resp


@router.get("/sortir")
def sortir(request: Request):
    request.session.pop("uid", None)
    return _redir_login()


# ------------------------------------------------------------------ comandes
def _filtre_centre(q, u):
    if u.rol != "admin" and u.centre_id:
        q = q.filter(models.Comanda.centre_id == u.centre_id)
    return q


def _consulta(db, u, estat="pagada", tipus="", centre="", cerca=""):
    q = _filtre_centre(db.query(models.Comanda), u)
    if estat == "pagada":
        q = q.filter(models.Comanda.estat == "pagada")
    elif estat == "pendent":
        q = q.filter(models.Comanda.estat != "pagada")
    if tipus in ("matricula", "practiques"):
        q = q.filter(models.Comanda.tipus == tipus)
    if centre.isdigit():
        q = q.filter(models.Comanda.centre_id == int(centre))
    if cerca:
        like = f"%{cerca.strip()}%"
        q = q.filter(or_(models.Comanda.nom.ilike(like), models.Comanda.cognoms.ilike(like),
                         models.Comanda.dni.ilike(like), models.Comanda.email.ilike(like),
                         models.Comanda.num_rebut.ilike(like)))
    return q.order_by(models.Comanda.pagat_en.desc().nullslast(), models.Comanda.creat_en.desc())


@router.get("", response_class=HTMLResponse)
def inici(request: Request, estat: str = "pagada", tipus: str = "", centre: str = "", q: str = "",
          db: Session = Depends(get_db)):
    try:
        u = _cal(request, db)
    except _Fora:
        return _redir_login()
    files = _consulta(db, u, estat, tipus, centre, q).limit(500).all()
    total = sum(c.total for c in files if c.estat == "pagada")
    mes = datetime.now().strftime("%Y-%m")
    del_mes = [c for c in _consulta(db, u, "pagada").all() if c.pagat_en and c.pagat_en.strftime("%Y-%m") == mes]
    return _r(request, "panell/comandes.html", {
        "files": files, "estat": estat, "tipus": tipus, "centre": centre, "q": q, "total": total,
        "mes_n": len(del_mes), "mes_total": sum(c.total for c in del_mes),
        "centres": db.query(models.Centre).order_by(models.Centre.ordre).all(),
        "falten": ajustos.falten_dades_legals(db) if u.rol == "admin" else []}, db)


def _comanda_permesa(request, db, cid):
    u = _cal(request, db)
    c = db.get(models.Comanda, cid)
    if not c or (u.rol != "admin" and u.centre_id and c.centre_id != u.centre_id):
        raise _Fora()
    return u, c


@router.get("/comanda/{cid}", response_class=HTMLResponse)
def comanda(cid: int, request: Request, fet: str = "", db: Session = Depends(get_db)):
    try:
        u, c = _comanda_permesa(request, db, cid)
    except _Fora:
        return _redir_login()
    return _r(request, "panell/comanda.html", {"c": c, "fet": fet,
                                               "pack": db.get(models.Pack, c.pack_id) if c.pack_id else None}, db)


@router.post("/comanda/{cid}/correus")
async def comanda_correus(cid: int, request: Request, db: Session = Depends(get_db)):
    try:
        u, c = _comanda_permesa(request, db, cid)
    except _Fora:
        return _redir_login()
    f = await _form(request)
    if f is None or c.estat != "pagada":
        return RedirectResponse(f"/gestio/comanda/{cid}", status_code=303)
    qui = f.get("qui") if f.get("qui") in ("alumne", "equip") else None
    comandes.envia_correus(db, c, qui)
    return RedirectResponse(f"/gestio/comanda/{cid}?fet=correus", status_code=303)


@router.post("/comanda/{cid}/nota")
async def comanda_nota(cid: int, request: Request, db: Session = Depends(get_db)):
    try:
        u, c = _comanda_permesa(request, db, cid)
    except _Fora:
        return _redir_login()
    f = await _form(request)
    if f is not None:
        c.nota_interna = (f.get("nota") or "")[:5000]
        db.commit()
    return RedirectResponse(f"/gestio/comanda/{cid}?fet=nota", status_code=303)


@router.get("/comanda/{cid}/correu/{qui}", response_class=HTMLResponse)
def comanda_correu(cid: int, qui: str, request: Request, db: Session = Depends(get_db)):
    """El correu tal com el rep l'alumne o la secretaria (per veure'l o reenviar-lo a mà)."""
    try:
        u, c = _comanda_permesa(request, db, cid)
    except _Fora:
        return _redir_login()
    if c.estat != "pagada" or qui not in ("alumne", "equip"):
        return Response(status_code=404)
    _, html, _ = comandes.correu_alumne(db, c) if qui == "alumne" else comandes.correu_equip(db, c)
    return HTMLResponse(html)


@router.get("/comanda/{cid}/{doc}.pdf")
def comanda_pdf(cid: int, doc: str, request: Request, db: Session = Depends(get_db)):
    try:
        u, c = _comanda_permesa(request, db, cid)
    except _Fora:
        return _redir_login()
    if doc == "contracte" and c.contracte_pdf:
        return Response(c.contracte_pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{documents.nom_contracte(c)}"'})
    if doc == "rebut" and c.estat == "pagada":
        if not c.rebut_pdf:
            c.rebut_pdf = documents.rebut_pdf(db, c)
            db.commit()
        return Response(c.rebut_pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{documents.nom_rebut(c)}"'})
    return Response(status_code=404)


CAP_EXCEL = ["Rebut", "Pagat el", "Estat", "Tipus", "Centre", "Carnet", "Producte", "Preu", "Descompte", "Promoció",
             "Taxa DGT", "Cànon", "Total", "Nom", "Cognoms", "DNI/NIE", "Naixement", "Correu", "Telèfon", "Adreça",
             "CP", "Població", "Tutor/a", "DNI tutor/a", "Horari", "Contactar per", "Observacions", "Pagament Stripe",
             "Idioma", "Creada el", "Nota interna"]


def _capcalera(ws, cap):
    from openpyxl.styles import Font, PatternFill
    ws.append(cap)
    for cel in ws[1]:
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill("solid", fgColor="14224F")


def _ajusta(ws):
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(40, max(10, max(len(str(x.value or "")) for x in col) + 2))
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"


def fulla_comandes(ws, llista):
    """Omple una fulla d'Excel amb les comandes (també la fa servir la còpia de seguretat)."""
    ws.title = "Comandes"
    _capcalera(ws, CAP_EXCEL)
    for c in llista:
        ws.append([c.num_rebut, c.pagat_en.strftime("%d/%m/%Y %H:%M") if c.pagat_en else "", c.estat,
                   "Matrícula" if c.tipus == "matricula" else "Pràctiques", c.centre.nom if c.centre else "",
                   c.carnet_codi, c.producte, c.preu_base, c.descompte, c.promocio, c.taxa, c.canon, c.total,
                   c.nom, c.cognoms, c.dni, c.naixement.strftime("%d/%m/%Y") if c.naixement else "", c.email,
                   c.telefon, c.adreca, c.cp, c.localitat, c.tutor_nom, c.tutor_dni,
                   {"MATI": "Matí", "TARDA": "Tarda"}.get(c.franja, c.franja), comandes.via_contacte(c), c.observacions,
                   c.stripe_pagament, c.idioma, c.creat_en.strftime("%d/%m/%Y %H:%M") if c.creat_en else "",
                   c.nota_interna])
    _ajusta(ws)


def fulla_missatges(ws, llista):
    ws.title = "Missatges"
    _capcalera(ws, ["Data", "Centre", "Nom", "Correu", "Telèfon", "Missatge"])
    for m in llista:
        ws.append([m.creat_en.strftime("%d/%m/%Y %H:%M") if m.creat_en else "", m.centre.nom if m.centre else "",
                   m.nom, m.email, m.telefon, m.text])
    _ajusta(ws)


@router.get("/exporta.xlsx")
def exporta(request: Request, estat: str = "pagada", tipus: str = "", centre: str = "", q: str = "",
            db: Session = Depends(get_db)):
    try:
        u = _cal(request, db)
    except _Fora:
        return _redir_login()
    from openpyxl import Workbook
    wb = Workbook()
    fulla_comandes(wb.active, _consulta(db, u, estat, tipus, centre, q).all())
    buf = io.BytesIO()
    wb.save(buf)
    nom = f"comandes-web-{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"'})


@router.get("/missatges", response_class=HTMLResponse)
def missatges(request: Request, db: Session = Depends(get_db)):
    try:
        u = _cal(request, db)
    except _Fora:
        return _redir_login()
    q = db.query(models.Missatge)
    if u.rol != "admin" and u.centre_id:
        q = q.filter(models.Missatge.centre_id == u.centre_id)
    return _r(request, "panell/missatges.html", {"files": q.order_by(models.Missatge.creat_en.desc()).limit(300).all()}, db)


# ------------------------------------------------------------------ preus
def _float(v, defecte=0.0):
    try:
        return round(float(str(v).replace("€", "").replace(" ", "").replace(",", ".")), 2)
    except (TypeError, ValueError):
        return defecte


@router.get("/preus", response_class=HTMLResponse)
def preus_pagina(request: Request, fet: str = "", db: Session = Depends(get_db)):
    try:
        _cal(request, db, admin=True)
    except _Fora:
        return _redir_login()
    return _r(request, "panell/preus.html", {
        "carnets": db.query(models.Carnet).order_by(models.Carnet.ordre).all(),
        "practiques": db.query(models.PackPractiques).order_by(models.PackPractiques.classes, models.PackPractiques.franja).all(),
        "aj": ajustos.tots(db), "fet": fet}, db)


@router.post("/preus")
async def preus_desa(request: Request, db: Session = Depends(get_db)):
    try:
        _cal(request, db, admin=True)
    except _Fora:
        return _redir_login()
    f = await _form(request)
    if f is None:
        return RedirectResponse("/gestio/preus", status_code=303)
    for p in db.query(models.Pack).all():
        if f"preu_{p.id}" in f:
            p.preu = _float(f.get(f"preu_{p.id}"), p.preu)
            p.actiu = f.get(f"actiu_{p.id}") == "1"
            p.destacat = f.get(f"destacat_{p.id}") == "1"
    for p in db.query(models.PackPractiques).all():
        if f"pp_preu_{p.id}" in f:
            p.preu = _float(f.get(f"pp_preu_{p.id}"), p.preu)
            p.actiu = f.get(f"pp_actiu_{p.id}") == "1"
    for clau in ("taxa_dgt", "taxa_dgt_a", "canon_pistes", "preu_expedient"):
        if clau in f:
            ajustos.desa(db, clau, str(_float(f.get(clau))))
    for clau in f.keys():
        if clau.startswith(("tarifes_classes_", "tarifes_examens_")) and len(clau) < 40:
            ajustos.desa(db, clau, (f.get(clau) or "").strip())
    db.commit()
    return RedirectResponse("/gestio/preus?fet=1", status_code=303)


# ------------------------------------------------------------------ promocions
def _dt(v):
    try:
        return datetime.strptime((v or "").strip(), "%Y-%m-%dT%H:%M")
    except ValueError:
        return None


@router.get("/promocions", response_class=HTMLResponse)
def promocions(request: Request, edita: int = 0, err: str = "", fet: str = "", db: Session = Depends(get_db)):
    try:
        _cal(request, db, admin=True)
    except _Fora:
        return _redir_login()
    return _r(request, "panell/promocions.html", {
        "promos": db.query(models.Promocio).order_by(models.Promocio.inici.desc()).all(),
        "edita": db.get(models.Promocio, edita) if edita else None, "ara": preus.ara_local(), "err": err, "fet": fet,
        "carnets": _carnets_promo(db)}, db)


def _carnets_promo(db):
    return [c.codi.upper() for c in db.query(models.Carnet).filter(models.Carnet.actiu == True)
            .order_by(models.Carnet.ordre).all()]


@router.post("/promocions")
async def promocio_desa(request: Request, db: Session = Depends(get_db)):
    try:
        _cal(request, db, admin=True)
    except _Fora:
        return _redir_login()
    f = await _form(request)
    if f is None:
        return RedirectResponse("/gestio/promocions", status_code=303)
    pid = int(f.get("id") or 0) if str(f.get("id") or "").isdigit() else 0
    if f.get("accio") == "esborra" and pid:
        p = db.get(models.Promocio, pid)
        if p:
            db.delete(p)
            db.commit()
        return RedirectResponse("/gestio/promocions?fet=esborrada", status_code=303)
    nom = (f.get("nom") or "").strip()
    pct = _float(f.get("percentatge"))
    inici, fi = _dt(f.get("inici")), _dt(f.get("fi"))
    tots = _carnets_promo(db)
    triats = [c for c in tots if f.get(f"carnet_{c}") == "1"]
    if not nom or not (0 < pct <= 90) or not inici or not fi or fi <= inici or not triats:
        return RedirectResponse(f"/gestio/promocions?err=1{'&edita=' + str(pid) if pid else ''}", status_code=303)
    p = db.get(models.Promocio, pid) if pid else models.Promocio()
    p.nom, p.percentatge, p.inici, p.fi = nom[:120], pct, inici, fi
    p.codi = "".join(ch for ch in (f.get("codi") or "").upper() if ch.isalnum() or ch in "-_")[:40]
    p.aplica = "matricula"                       # les ofertes són sempre dels packs inicials (matrícula)
    p.carnets = "" if len(triats) == len(tots) else ",".join(triats)
    p.banner_ca = (f.get("banner_ca") or "").strip()[:200]
    p.banner_es = (f.get("banner_es") or "").strip()[:200]
    p.activa = f.get("activa") == "1"
    if not pid:
        db.add(p)
    db.commit()
    return RedirectResponse("/gestio/promocions?fet=desada", status_code=303)


# ------------------------------------------------------------------ centres i dades
@router.get("/centres", response_class=HTMLResponse)
def centres(request: Request, fet: str = "", db: Session = Depends(get_db)):
    try:
        _cal(request, db, admin=True)
    except _Fora:
        return _redir_login()
    return _r(request, "panell/centres.html", {"centres": db.query(models.Centre).order_by(models.Centre.ordre).all(),
                                                "fet": fet}, db)


@router.post("/centres")
async def centres_desa(request: Request, db: Session = Depends(get_db)):
    try:
        _cal(request, db, admin=True)
    except _Fora:
        return _redir_login()
    f = await _form(request)
    if f is None:
        return RedirectResponse("/gestio/centres", status_code=303)
    for c in db.query(models.Centre).all():
        if f"nom_{c.id}" not in f:
            continue
        for camp in ("nom", "adreca", "cp_localitat", "telefon", "mobil", "email", "maps", "horari_ca", "horari_es"):
            setattr(c, camp, (f.get(f"{camp}_{c.id}") or "").strip())
        c.actiu = f.get(f"actiu_{c.id}") == "1"
    db.commit()
    return RedirectResponse("/gestio/centres?fet=1", status_code=303)


CLAUS_ESCOLA = [("escola_nom", "Nom comercial"), ("escola_rao_social", "Raó social"), ("escola_nif", "NIF"),
                ("escola_domicili", "Domicili fiscal"), ("escola_localitat", "Localitat"),
                ("escola_telefon", "Telèfon general"), ("escola_email", "Correu general"),
                ("escola_titular", "Titular"), ("escola_num_provincial", "Núm. d'autorització de la DGT"),
                ("correus_admin", "Correus que reben còpia de totes les matrícules (separats per comes)"),
                ("google_maps_api_key", "Clau de Google Maps (per completar l'adreça a la matrícula)"),
                ("google_analytics_id", "ID de Google Analytics (comença per G-)"),
                ("recordatori_hores", "Recordatori de matrícula sense pagar: hores d'espera (0 = no s'envia)")]


@router.get("/dades", response_class=HTMLResponse)
def dades(request: Request, fet: str = "", db: Session = Depends(get_db)):
    try:
        _cal(request, db, admin=True)
    except _Fora:
        return _redir_login()
    from . import correu, pagaments
    return _r(request, "panell/dades.html", {"aj": ajustos.tots(db), "claus": CLAUS_ESCOLA, "fet": fet,
                                              "correu_ok": correu.configurat(), "stripe_ok": pagaments.configurat(),
                                              "stripe_test": pagaments.mode_proves(),
                                              "url": comandes.url_publica(),
                                              "maps_ok": bool(__import__("app.web", fromlist=["x"]).clau_maps(db)),
                                              "ga_id": ajustos.ga_id(db), "dos_factors": dos_factors_actiu(),
                                              "assistent_ok": __import__("app.assistent", fromlist=["x"]).actiu()}, db)


@router.post("/dades")
async def dades_desa(request: Request, db: Session = Depends(get_db)):
    try:
        _cal(request, db, admin=True)
    except _Fora:
        return _redir_login()
    f = await _form(request)
    if f is not None:
        for clau, _ in CLAUS_ESCOLA:
            if clau in f:
                ajustos.desa(db, clau, (f.get(clau) or "").strip())
        db.commit()
    return RedirectResponse("/gestio/dades?fet=1", status_code=303)


@router.get("/copia-seguretat.zip")
def copia_seguretat(request: Request, db: Session = Depends(get_db)):
    try:
        u = _cal(request, db, admin=True)
    except _Fora:
        return _redir_login()
    from fastapi.responses import FileResponse
    from starlette.background import BackgroundTask
    from . import copia
    cami, nom = copia.genera(db)
    ajustos.desa(db, "ultima_copia", f"{datetime.now().strftime('%d/%m/%Y %H:%M')} · {u.nom or u.email}")
    db.commit()
    return FileResponse(cami, media_type="application/zip", filename=nom,
                        background=BackgroundTask(os.remove, cami))


# ------------------------------------------------------------------ usuaris
@router.get("/usuaris", response_class=HTMLResponse)
def usuaris(request: Request, fet: str = "", err: str = "", db: Session = Depends(get_db)):
    try:
        _cal(request, db, admin=True)
    except _Fora:
        return _redir_login()
    return _r(request, "panell/usuaris.html", {"usuaris": db.query(models.Usuari).order_by(models.Usuari.email).all(),
                                                "centres": db.query(models.Centre).order_by(models.Centre.ordre).all(),
                                                "fet": fet, "err": err}, db)


@router.post("/usuaris")
async def usuaris_desa(request: Request, db: Session = Depends(get_db)):
    try:
        jo = _cal(request, db, admin=True)
    except _Fora:
        return _redir_login()
    f = await _form(request)
    if f is None:
        return RedirectResponse("/gestio/usuaris", status_code=303)
    accio = f.get("accio")
    uid = int(f.get("id") or 0) if str(f.get("id") or "").isdigit() else 0
    pw = f.get("contrasenya") or ""
    if accio == "nou":
        email = (f.get("email") or "").strip().lower()
        if "@" not in email or len(pw) < 10 or db.query(models.Usuari).filter(models.Usuari.email == email).first():
            return RedirectResponse("/gestio/usuaris?err=nou", status_code=303)
        centre = int(f.get("centre_id")) if str(f.get("centre_id") or "").isdigit() else None
        db.add(models.Usuari(email=email, nom=(f.get("nom") or "").strip()[:160], contrasenya=hash_pw(pw),
                             rol="admin" if f.get("rol") == "admin" else "secretaria", centre_id=centre))
    elif uid:
        u = db.get(models.Usuari, uid)
        if not u:
            return RedirectResponse("/gestio/usuaris", status_code=303)
        if accio == "contrasenya":
            if len(pw) < 10:
                return RedirectResponse("/gestio/usuaris?err=pw", status_code=303)
            u.contrasenya = hash_pw(pw)
            db.query(models.DispositiuConfiat).filter(models.DispositiuConfiat.usuari_id == u.id).delete()
        elif accio == "activa" and u.id != jo.id:
            u.actiu = not u.actiu
            db.query(models.DispositiuConfiat).filter(models.DispositiuConfiat.usuari_id == u.id).delete()
        elif accio == "edita":
            rol = "admin" if f.get("rol") == "admin" else "secretaria"
            if u.id == jo.id and rol != "admin":
                return RedirectResponse("/gestio/usuaris?err=jo", status_code=303)   # no et pots treure l'admin a tu
            u.nom = (f.get("nom") or "").strip()[:160]
            u.rol = rol
            u.centre_id = int(f.get("centre_id")) if str(f.get("centre_id") or "").isdigit() else None
    db.commit()
    return RedirectResponse("/gestio/usuaris?fet=1", status_code=303)
