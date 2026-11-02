"""Proves de la web: matrícula, pagament (Stripe simulat), correus, pràctiques, contacte i panell."""
import re
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import correu, db as _db, models, pagaments
from app.main import app

DNI_OK = "12345678Z"
DNI_TUTOR = "87654321X"


@pytest.fixture()
def cl(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fals")
    sessions = {}

    def crea(c, linies, url_ok, url_cancel):
        sid = f"cs_test_{len(sessions) + 1}"
        total = sum(pagaments.cents(p) for _, p in linies)
        sessions[sid] = {"id": sid, "payment_status": "paid", "currency": "eur", "amount_total": total,
                         "metadata": {"comanda": c.token, "import_cents": str(total)}, "payment_intent": f"pi_{sid}",
                         "_linies": linies}
        return SimpleNamespace(id=sid, url=f"https://checkout.stripe.test/{sid}")

    monkeypatch.setattr(pagaments, "crea_sessio", crea)
    monkeypatch.setattr(pagaments, "recupera", lambda sid: sessions.get(sid))
    correu.ENVIATS.clear()
    with TestClient(app) as c:
        c.sessions = sessions
        yield c


def dades_matricula(**kw):
    d = {"seccion": "badalona-centre", "pack_id": "", "nom": "Laia", "cognoms": "Puig Serra",
         "email": "laia@proves.cat", "telefon": "612345678", "telefon__pais": "34", "dni": DNI_OK,
         "naixement": "2000-05-10", "adreca": "C/ Major 1", "cp": "08912", "poblacio": "Badalona",
         "incloure_taxa": "0", "incloure_canon": "0"}
    d.update(kw)
    return d


def pack_id(codi):
    db = _db.SessionLocal()
    try:
        return str(db.query(models.Pack).filter(models.Pack.codi == codi).first().id)
    finally:
        db.close()


def _firma():
    import base64
    import io
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
    ImageDraw.Draw(im).line([(20, 70), (90, 20), (160, 75), (260, 30)], fill=(30, 41, 59, 255), width=4)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _firma_buida():
    import base64
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGBA", (300, 100), (0, 0, 0, 0)).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def signa(cl, token, **kw):
    firma = _firma()
    d = {"firma": firma, "accepta": "1", "accepta_condicions": "1", "consent_imatge": "no",
         "consent_comercial": "si", "inici_immediat": "1"}
    d.update(kw)
    return cl.post(f"/matricula/{token}/contracte", data=d, follow_redirects=False)


def comanda(token):
    db = _db.SessionLocal()
    try:
        return db.query(models.Comanda).filter(models.Comanda.token == token).first()
    finally:
        db.close()


def matricula_fins_a_stripe(cl, **kw):
    r = cl.post("/matricula", data=dades_matricula(pack_id=pack_id(kw.pop("pack", "B2")), **kw), follow_redirects=False)
    assert r.status_code == 303, r.text[:500]
    token = r.headers["location"].split("/")[2]
    r = signa(cl, token)
    assert r.status_code == 303 and r.headers["location"].startswith("https://checkout.stripe.test/")
    return token, r.headers["location"].rsplit("/", 1)[1]


def test_matricula_completa(cl):
    token, sid = matricula_fins_a_stripe(cl, incloure_taxa="1")
    c = comanda(token)
    assert c.estat == "signada" and c.contracte_pdf[:4] == b"%PDF" and c.taxa == 94.05
    assert c.total == 399 + 94.05
    r = cl.get(f"/pagament/{token}/ok?session_id={sid}", follow_redirects=False)
    assert r.headers["location"] == f"/comanda/{token}?nou=1"
    c = comanda(token)
    assert c.estat == "pagada" and c.num_rebut.startswith(f"W{date.today().year}-") and c.rebut_pdf[:4] == b"%PDF"
    assert len(correu.ENVIATS) == 2
    alumne, equip = correu.ENVIATS
    assert alumne["a"] == ["laia@proves.cat"] and alumne["respondre_a"] == "autoescolarolan05@gmail.com"
    assert len(alumne["adjunts"]) == 2 and "Matrícula confirmada" in alumne["assumpte"]
    assert equip["a"] == ["autoescolarolan05@gmail.com"] and equip["respondre_a"] == "laia@proves.cat"
    assert "Laia Puig Serra" in equip["assumpte"] and "Carnet B" in equip["assumpte"]
    r = cl.get(f"/comanda/{token}?nou=1")
    assert "Ja estàs matriculat/da" in r.text
    assert cl.get(f"/comanda/{token}/contracte.pdf").content[:4] == b"%PDF"
    assert cl.get(f"/comanda/{token}/rebut.pdf").content[:4] == b"%PDF"
    # tornar de Stripe un altre cop no torna a enviar res
    cl.get(f"/pagament/{token}/ok?session_id={sid}")
    assert len(correu.ENVIATS) == 2


def test_import_diferent_no_es_dona_per_pagat(cl):
    token, sid = matricula_fins_a_stripe(cl)
    cl.sessions[sid]["amount_total"] = 100
    r = cl.get(f"/pagament/{token}/ok?session_id={sid}")
    assert "Estem comprovant el pagament" in r.text
    assert comanda(token).estat == "signada" and not correu.ENVIATS


def test_sessio_d_una_altra_comanda(cl):
    t1, s1 = matricula_fins_a_stripe(cl)
    t2, s2 = matricula_fins_a_stripe(cl, email="altre@proves.cat")
    cl.get(f"/pagament/{t2}/ok?session_id={s1}")
    assert comanda(t2).estat == "signada"


def test_webhook(cl, monkeypatch):
    token, sid = matricula_fins_a_stripe(cl)
    ev = {"type": "checkout.session.completed", "data": {"object": cl.sessions[sid]}}
    monkeypatch.setattr(pagaments, "webhook_event", lambda p, s: ev)
    assert cl.post("/stripe/webhook", content=b"{}").status_code == 200
    assert comanda(token).estat == "pagada" and len(correu.ENVIATS) == 2
    cl.post("/stripe/webhook", content=b"{}")
    assert len(correu.ENVIATS) == 2


def test_webhook_sense_signatura(cl):
    assert cl.post("/stripe/webhook", content=b"{}").status_code == 400


def test_menor_necessita_tutor(cl):
    naix = (date.today() - timedelta(days=17 * 365 + 320)).isoformat()
    r = cl.post("/matricula", data=dades_matricula(pack_id=pack_id("B1"), naixement=naix))
    assert r.status_code == 400 and "tutor/a legal" in r.text
    r = cl.post("/matricula", data=dades_matricula(pack_id=pack_id("B1"), naixement=naix, tutor_nom="Joan Puig",
                                                    tutor_dni=DNI_TUTOR, tutor_accepta="1"), follow_redirects=False)
    assert r.status_code == 303
    token = r.headers["location"].split("/")[2]
    assert "Signatura del tutor/a legal" in cl.get(f"/matricula/{token}/contracte").text


def test_massa_jove_per_al_carnet(cl):
    naix = (date.today() - timedelta(days=14 * 365)).isoformat()
    r = cl.post("/matricula", data=dades_matricula(pack_id=pack_id("AM"), naixement=naix, tutor_nom="Joan",
                                                    tutor_dni=DNI_TUTOR, tutor_accepta="1"))
    assert r.status_code == 400 and "Encara no et pots matricular" in r.text


def test_dni_i_telefon(cl):
    assert "DNI/NIE no és correcte" in cl.post("/matricula", data=dades_matricula(pack_id=pack_id("B1"), dni="12345678A")).text
    assert "9 xifres" in cl.post("/matricula", data=dades_matricula(pack_id=pack_id("B1"), telefon="1234")).text


def test_carnet_a_demana_a2_de_dos_anys(cl):
    r = cl.post("/matricula", data=dades_matricula(pack_id=pack_id("A"), naixement="1990-01-01",
                                                    data_a2=(date.today() - timedelta(days=200)).isoformat()))
    assert r.status_code == 400 and "com a mínim 2 anys" in r.text
    r = cl.post("/matricula", data=dades_matricula(pack_id=pack_id("A"), naixement="1990-01-01", data_a2="2015-03-01"),
                follow_redirects=False)
    assert r.status_code == 303


def test_signatura_buida(cl):
    r = cl.post("/matricula", data=dades_matricula(pack_id=pack_id("B1")), follow_redirects=False)
    token = r.headers["location"].split("/")[2]
    r = signa(cl, token, firma=_firma_buida())
    assert "err=camps" in r.headers["location"] and comanda(token).estat == "dades"


def test_signar_sense_acceptar(cl):
    r = cl.post("/matricula", data=dades_matricula(pack_id=pack_id("B1")), follow_redirects=False)
    token = r.headers["location"].split("/")[2]
    r = signa(cl, token, accepta_condicions="")
    assert "err=camps" in r.headers["location"] and comanda(token).estat == "dades"


def _promo(**kw):
    db = _db.SessionLocal()
    try:
        p = models.Promocio(nom=kw.pop("nom", "Black Friday"), percentatge=kw.pop("pct", 20),
                            inici=datetime.now() - timedelta(days=1), fi=datetime.now() + timedelta(days=1), **kw)
        db.add(p)
        db.commit()
        return p.id
    finally:
        db.close()


def _esborra_promos():
    db = _db.SessionLocal()
    db.query(models.Promocio).delete()
    db.commit()
    db.close()


def test_promocio_automatica_i_codi(cl):
    _esborra_promos()
    _promo(banner_ca="Black Friday −20%", banner_es="Black Friday −20%")
    try:
        r = cl.get("/")
        assert "Black Friday −20%" in r.text and '<s class="abans">199€</s>' in r.text
        token, sid = matricula_fins_a_stripe(cl, pack="B1")
        c = comanda(token)
        assert c.descompte == 39.8 and c.total == 159.2 and c.promocio == "Black Friday"
        _promo(nom="Codi amics", pct=30, codi="AMICS")
        r = cl.post("/matricula", data=dades_matricula(pack_id=pack_id("B1"), codi_promo="amics"), follow_redirects=False)
        c = comanda(r.headers["location"].split("/")[2])
        assert c.total == 139.3 and c.promocio == "Codi amics"
        r = cl.post("/matricula", data=dades_matricula(pack_id=pack_id("B1"), codi_promo="FALS"))
        assert r.status_code == 400 and "codi de descompte no és vàlid" in r.text
    finally:
        _esborra_promos()


def test_practiques(cl):
    db = _db.SessionLocal()
    pp = db.query(models.PackPractiques).filter_by(classes=10, franja="TARDA").first()
    db.close()
    r = cl.post("/practiques", data={"pack_id": str(pp.id), "seccion": "el-masnou", "nom": "Marc", "cognoms": "Vila",
                                     "email": "marc@proves.cat", "telefon": "612345678", "dni": DNI_OK,
                                     "accepta_condicions": "1"}, follow_redirects=False)
    assert r.status_code == 303
    sid = r.headers["location"].rsplit("/", 1)[1]
    token = cl.sessions[sid]["metadata"]["comanda"]
    assert cl.sessions[sid]["amount_total"] == 38500
    cl.get(f"/pagament/{token}/ok?session_id={sid}")
    c = comanda(token)
    assert c.estat == "pagada" and c.producte == "Pack de 10 pràctiques de tarda" and c.contracte_pdf is None
    alumne, equip = correu.ENVIATS
    assert alumne["adjunts"] == [f"Rebut {c.num_rebut} Marc Vila.pdf"]
    assert equip["a"] == ["autoescolesrolan.elmasnou@gmail.com"]


def test_correu_en_castella_sense_catala(cl):
    cl.get("/idioma/es", headers={"referer": "/"})
    token, sid = matricula_fins_a_stripe(cl)
    cl.get(f"/pagament/{token}/ok?session_id={sid}")
    alumne = correu.ENVIATS[0]
    assert "Ya estás matriculado/a" in alumne["text"]
    print(alumne["text"])
    for paraula in ("secretaria del teu", "Veure la meva", "I ara què", "Total pagat"):
        assert paraula not in alumne["text"], paraula
    pagina = cl.get(f"/comanda/{token}").text
    assert "¡Ya estás matriculado/a!" in pagina or "Ya estás matriculado" in pagina or "Tu matrícula" in pagina
    cl.get("/idioma/ca", headers={"referer": "/"})


def test_contacte(cl):
    r = cl.post("/contacte", data={"centre": "sant-adria", "nom": "Anna", "email": "anna@proves.cat",
                                   "text": "Voldria informació del carnet de moto", "accepta": "1"})
    assert "Missatge enviat" in r.text
    m = correu.ENVIATS[-1]
    assert m["a"] == ["autoescolesrolan08@gmail.com"] and m["respondre_a"] == "anna@proves.cat"
    r = cl.post("/contacte", data={"centre": "sant-adria", "nom": "Robot", "email": "r@x.cat", "text": "hola hola",
                                   "accepta": "1", "web": "spam"})
    assert len([x for x in correu.ENVIATS if x["respondre_a"] == "r@x.cat"]) == 0


def _entra(cl, email="admin@proves.cat", pw="proves12345"):
    return cl.post("/gestio/entrar", data={"email": email, "contrasenya": pw}, follow_redirects=False)


def _csrf(cl, url):
    return re.search(r'name="csrf" value="([^"]+)"', cl.get(url).text).group(1)


def test_panell(cl):
    assert cl.get("/gestio", follow_redirects=False).headers["location"] == "/gestio/entrar"
    assert _entra(cl, pw="dolenta").status_code == 401
    assert _entra(cl).status_code == 303
    token, sid = matricula_fins_a_stripe(cl)
    cl.get(f"/pagament/{token}/ok?session_id={sid}")
    r = cl.get("/gestio")
    assert "Laia Puig Serra" in r.text and "Raó social" in r.text
    c = comanda(token)
    r = cl.get(f"/gestio/comanda/{c.id}")
    assert "Contracte signat (PDF)" in r.text
    n = len(correu.ENVIATS)
    tok = _csrf(cl, f"/gestio/comanda/{c.id}")
    cl.post(f"/gestio/comanda/{c.id}/correus", data={"csrf": tok, "qui": "alumne"})
    assert len(correu.ENVIATS) == n + 1
    cl.post(f"/gestio/comanda/{c.id}/correus", data={"csrf": "dolent", "qui": "alumne"})
    assert len(correu.ENVIATS) == n + 1
    x = cl.get("/gestio/exporta.xlsx")
    assert x.headers["content-type"].startswith("application/vnd.openxml") and x.content[:2] == b"PK"
    # preus
    tok = _csrf(cl, "/gestio/preus")
    pid = pack_id("B1")
    cl.post("/gestio/preus", data={"csrf": tok, f"preu_{pid}": "209,50", f"actiu_{pid}": "1"})
    assert "209,50€" in cl.get("/preus?carnet=B").text
    cl.post("/gestio/preus", data={"csrf": tok, f"preu_{pid}": "199", f"actiu_{pid}": "1"})
    # secretaria d'un altre centre no veu la comanda
    tok = _csrf(cl, "/gestio/usuaris")
    db = _db.SessionLocal()
    masnou = db.query(models.Centre).filter_by(codi="el-masnou").first().id
    db.close()
    cl.post("/gestio/usuaris", data={"csrf": tok, "accio": "nou", "email": "sec@proves.cat", "nom": "Sec",
                                     "rol": "secretaria", "centre_id": str(masnou), "contrasenya": "secretaria123"})
    cl.get("/gestio/sortir")
    assert _entra(cl, "sec@proves.cat", "secretaria123").status_code == 303
    assert "Laia Puig Serra" not in cl.get("/gestio").text
    assert cl.get(f"/gestio/comanda/{c.id}", follow_redirects=False).status_code == 303
    assert cl.get("/gestio/preus", follow_redirects=False).status_code == 303
    cl.get("/gestio/sortir")


def test_promocio_des_del_panell(cl):
    _entra(cl)
    tok = _csrf(cl, "/gestio/promocions")
    ara = datetime.now()
    r = cl.post("/gestio/promocions", data={"csrf": tok, "nom": "Black Friday", "percentatge": "15",
                                             "inici": (ara - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
                                             "fi": (ara + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
                                             "aplica": "practiques", "banner_ca": "Pràctiques −15%", "activa": "1"},
                follow_redirects=False)
    assert "fet=desada" in r.headers["location"]
    assert "Pràctiques −15%" in cl.get("/").text
    assert "<s class=\"abans\">341€</s>" in cl.get("/practiques").text
    _esborra_promos()
    cl.get("/gestio/sortir")


def test_pagines_en_castella(cl):
    cl.get("/idioma/es", headers={"referer": "/"})
    r = cl.get("/")
    assert 'lang="es"' in r.text
    cl.get("/idioma/ca", headers={"referer": "/"})


def test_mode_demostracio(monkeypatch):
    """Per veure-la a l'ordinador: pagament simulat sense Stripe."""
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.setenv("ROLAN_DEMO", "1")
    correu.ENVIATS.clear()
    with TestClient(app) as cl:
        r = cl.post("/matricula", data=dades_matricula(pack_id=pack_id("B1")), follow_redirects=False)
        token = r.headers["location"].split("/")[2]
        r = signa(cl, token)
        assert r.headers["location"].startswith("/pagament-demo/")
        p = cl.get(r.headers["location"])
        assert "Mode de demostració" in p.text and "199,00 €" in p.text
        r = cl.get(r.headers["location"] + "?accio=paga", follow_redirects=True)
        assert "Ja estàs matriculat/da" in r.text and comanda(token).estat == "pagada"
        _entra(cl)
        c = comanda(token)
        assert "Ja estàs matriculat/da a Autoescoles Rolan" in cl.get(f"/gestio/comanda/{c.id}/correu/alumne").text
        assert "Nova matrícula pagada" in cl.get(f"/gestio/comanda/{c.id}/correu/equip").text or \
               "Cal fer la factura a Holded" in cl.get(f"/gestio/comanda/{c.id}/correu/equip").text
        cl.get("/gestio/sortir")


def test_demo_no_s_activa_amb_stripe(monkeypatch):
    monkeypatch.setenv("ROLAN_DEMO", "1")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_x")
    assert not pagaments.demo()
