"""Web d'Autoescoles Rolan amb matrícula i pagament en línia.

Independent de Rolan Gestió (ERP) i de Formació: la web, la matrícula, el pagament amb Stripe,
els correus de confirmació i un panell intern senzill (/gestio).
"""
import os
import secrets
from datetime import date, datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import ajustos, db as _db, i18n, models, preus, seed, telefon, traduccio

DIR = os.path.dirname(__file__)
APP_VERSION = "2026-11-02 · web amb matrícula i pagament"

_secret = (os.environ.get("SECRET_KEY") or "").strip()
if not _secret:
    print("⚠️  SECRET_KEY no definida: es fa servir una clau temporal (les sessions es perden en reiniciar).")
    _secret = secrets.token_urlsafe(48)

app = FastAPI(title="Autoescoles Rolan · Web", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=_secret, same_site="lax",
                   https_only=os.environ.get("HTTPS_ONLY", "").lower() in ("1", "true", "si"),
                   max_age=60 * 60 * 24 * 14, session_cookie="rolan_web")


@app.middleware("http")
async def capcaleres(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith(("/gestio", "/comanda", "/matricula/", "/pagament")):
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Robots-Tag"] = "noindex"
    return resp


app.mount("/static", StaticFiles(directory=os.path.join(DIR, "static")), name="static")

templates = Jinja2Templates(directory=os.path.join(DIR, "templates"))
traduccio.activa(templates.env)
telefon.registra(templates.env)
templates.env.globals["i18n_get_idioma"] = i18n.get_idioma
templates.env.globals["any_actual"] = lambda: date.today().year
templates.env.globals["eur"] = preus.eur
templates.env.globals["eur2"] = preus.eur2
templates.env.filters["local"] = preus.local
from . import pagaments as _pagaments  # noqa: E402
templates.env.globals["mode_demo"] = _pagaments.demo
templates.env.globals["app_version"] = APP_VERSION
from . import assistent as _assistent  # noqa: E402
templates.env.globals["assistent_actiu"] = _assistent.actiu


_SENSE_POPUP = ("/matricula", "/pagament", "/comanda", "/practiques", "/stripe")


def _promo_popup(p, request):
    """Dades del pop-up de la promoció (només si n'hi ha una d'automàtica per a les matrícules)."""
    if not p or (p.aplica or "tot") not in ("tot", "matricula") or not (p.percentatge or 0) > 0 or not p.fi:
        return None
    fi = p.fi.replace(tzinfo=preus.TZ)          # les dates de les promocions són hora de Barcelona
    queda = fi - datetime.now(preus.TZ)
    if queda.total_seconds() <= 0:
        return None
    return {"id": p.id, "nom": p.nom, "pct": f"{p.percentatge:g}", "fi_ms": int(fi.timestamp() * 1000),
            "setmana": queda.days < 7, "popup": not request.url.path.startswith(_SENSE_POPUP),
            "tots": not p.llista_carnets, "abast_ca": abast_promo(p, "ca"), "abast_es": abast_promo(p, "es")}


def abast_promo(p, idioma="ca"):
    """«a tots els packs» o «als packs del carnet B» / «dels carnets B i AM»."""
    ll = p.llista_carnets if p else []
    i = " y " if idioma == "es" else " i "
    noms = (", ".join(ll[:-1]) + i + ll[-1]) if len(ll) > 1 else (ll[0] if ll else "")
    if idioma == "es":
        return "en todos los packs" if not ll else (f"en los packs del carnet {noms}" if len(ll) == 1 else f"en los packs de los carnets {noms}")
    return "a tots els packs" if not ll else (f"als packs del carnet {noms}" if len(ll) == 1 else f"als packs dels carnets {noms}")


templates.env.globals["abast_promo"] = abast_promo


def render(request, nom, ctx=None, db=None, status_code=200):
    ctx = dict(ctx or {})
    ctx["request"] = request
    ll = i18n.get_idioma(request)
    ctx.setdefault("ll", ll)
    ctx.setdefault("T", lambda ca, es: es if ll == "es" else ca)
    if db is not None:
        aj = ajustos.tots(db)
        ctx.setdefault("escola", lambda clau, defecte="": (aj.get(clau) or defecte))
        ctx.setdefault("correu_escola", ajustos.correu_general(db))
        ctx.setdefault("promo_banner", preus.banner(db))
        ctx.setdefault("promo_popup", _promo_popup(ctx["promo_banner"], request))
        ctx.setdefault("ga_id", ajustos.ga_id(db))
        ctx.setdefault("centres_peu", db.query(models.Centre).filter(models.Centre.actiu == True)
                       .order_by(models.Centre.ordre).all())
    else:
        ctx.setdefault("escola", lambda clau, defecte="": defecte)
    return templates.TemplateResponse(request, nom, ctx, status_code=status_code)


@app.on_event("startup")
def _inici():
    # La base de dades pot trigar a estar a punt (p. ex. en crear-la per primer cop a Render):
    # s'hi torna a provar durant uns 2 minuts abans de rendir-se.
    import time
    for intent in range(25):
        try:
            _db.Base.metadata.create_all(_db.engine)
            break
        except Exception as e:
            if intent == 24:
                raise
            print(f"[inici] la base de dades encara no respon ({type(e).__name__}); torno a provar en 5 s")
            time.sleep(5)
    _afegeix_columnes_noves()
    db = _db.SessionLocal()
    try:
        seed.omple(db)
        from . import panell
        panell.primer_admin(db)
    finally:
        db.close()
    _engega_recordatoris()


def _engega_recordatoris():
    """Cada 10 minuts mira si hi ha matrícules començades i no pagades per enviar-los el recordatori."""
    if (os.environ.get("RECORDATORIS") or "").strip().lower() in ("0", "off", "no"):
        return
    import threading
    import time as _t
    from . import comandes

    def bucle():
        _t.sleep(60)
        while True:
            db = _db.SessionLocal()
            try:
                comandes.envia_recordatoris(db)
            except Exception as e:
                print(f"[recordatoris] error: {e}")
            finally:
                db.close()
            _t.sleep(600)
    threading.Thread(target=bucle, name="recordatoris", daemon=True).start()


# Columnes afegides després de crear la base de dades a Render: (taula, columna, tipus SQL)
COLUMNES_NOVES = [("comandes", "contacte_preferit", "VARCHAR(20) DEFAULT ''"),
                  ("comandes", "recordatori_en", "TIMESTAMP"),
                  ("promocions", "carnets", "VARCHAR(60) DEFAULT ''")]


def _afegeix_columnes_noves():
    from sqlalchemy import inspect, text
    insp = inspect(_db.engine)
    for taula, col, tipus in COLUMNES_NOVES:
        if col not in {c["name"] for c in insp.get_columns(taula)}:
            with _db.engine.begin() as con:
                con.execute(text(f"ALTER TABLE {taula} ADD COLUMN {col} {tipus}"))
            print(f"[inici] columna nova: {taula}.{col}")


@app.get("/idioma/{codi}")
def idioma(codi: str, request: Request):
    if codi in i18n.IDIOMAS_DISPONIBLES:
        request.session["idioma"] = codi
    ref = request.headers.get("referer") or "/"
    from urllib.parse import urlparse
    u = urlparse(ref)
    desti = (u.path or "/") + (f"?{u.query}" if u.query else "")
    if u.netloc and u.netloc != request.url.netloc:
        desti = "/"
    return RedirectResponse(desti, status_code=303)


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    base = (os.environ.get("PUBLIC_URL") or "").rstrip("/")
    return ("User-agent: *\nDisallow: /gestio\nDisallow: /comanda/\nDisallow: /matricula/\nDisallow: /pagament/\n"
            + (f"Sitemap: {base}/sitemap.xml\n" if base else ""))


@app.get("/sitemap.xml")
def sitemap():
    base = (os.environ.get("PUBLIC_URL") or "").rstrip("/")
    urls = "".join(f"<url><loc>{base}{p}</loc></url>" for p in
                   ("/", "/preus", "/matricula", "/qui-som", "/contacte", "/condicions"))
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    + urls + "</urlset>", media_type="application/xml")


@app.exception_handler(StarletteHTTPException)
async def _error_http(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and not request.url.path.startswith(("/static", "/gestio")):
        from .db import SessionLocal
        db = SessionLocal()
        try:
            return render(request, "web/no_trobat.html", {}, db=db, status_code=404)
        finally:
            db.close()
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


@app.get("/salut")
def salut():
    return {"ok": True, "versio": APP_VERSION, "ara": datetime.utcnow().isoformat(timespec="seconds")}


from . import web as _web  # noqa: E402
from . import panell as _panell  # noqa: E402

app.include_router(_web.router)
app.include_router(_panell.router)
app.include_router(_assistent.router)
