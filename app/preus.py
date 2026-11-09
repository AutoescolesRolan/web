"""Preus i promocions (Black Friday, etc.).

Les promocions es guarden amb l'hora de Barcelona. Una promoció sense codi s'aplica sola;
una amb codi només si l'alumne l'escriu. No se sumen: s'aplica la que surt més a compte.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from . import models

TZ = ZoneInfo("Europe/Madrid")


def ara_local() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)


def local(dt):
    """Hora UTC desada → hora de Barcelona."""
    if not dt:
        return dt
    from datetime import timezone
    return dt.replace(tzinfo=timezone.utc).astimezone(TZ).replace(tzinfo=None)


def eur(v) -> str:
    """199 → «199», 94.05 → «94,05», 1050 → «1.050»."""
    v = round(float(v or 0), 2)
    if abs(v - round(v)) < 0.005:
        return f"{int(round(v)):,}".replace(",", ".")
    enter, dec = f"{v:.2f}".split(".")
    return f"{int(enter):,}".replace(",", ".") + "," + dec


def eur2(v) -> str:
    """Sempre amb dos decimals: 199 → «199,00»."""
    enter, dec = f"{round(float(v or 0), 2):.2f}".split(".")
    return f"{int(enter):,}".replace(",", ".") + "," + dec


def _vigents(db, tipus, carnet=None):
    """Promocions en marxa. Amb `carnet`, només les que valen per a aquell carnet
    (una promoció sense carnets triats val per a tots)."""
    ara = ara_local()
    q = (db.query(models.Promocio)
         .filter(models.Promocio.activa == True, models.Promocio.inici <= ara, models.Promocio.fi >= ara)
         .filter(models.Promocio.aplica.in_(("tot", tipus))))
    return [p for p in q.all() if carnet is None or p.per_al_carnet(carnet)]


def promo_automatica(db, tipus, carnet=None):
    """La promoció sense codi que fa més descompte ara mateix (o None)."""
    autos = [p for p in _vigents(db, tipus, carnet) if not (p.codi or "").strip()]
    return max(autos, key=lambda p: p.percentatge or 0) if autos else None


def promo_per_codi(db, tipus, codi, carnet=None):
    codi = (codi or "").strip().upper()
    if not codi:
        return None
    for p in _vigents(db, tipus, carnet):
        if (p.codi or "").strip().upper() == codi:
            return p
    return None


def banner(db):
    """Text de la promoció que es mostra a dalt de la web (la primera automàtica vigent)."""
    ara = ara_local()
    p = (db.query(models.Promocio)
         .filter(models.Promocio.activa == True, models.Promocio.inici <= ara, models.Promocio.fi >= ara,
                 models.Promocio.codi == "")
         .order_by(models.Promocio.percentatge.desc()).first())
    return p


def calcula(db, preu: float, tipus: str, codi: str = "", carnet=None) -> dict:
    """Preu final d'un producte. tipus: «matricula» o «practiques»; carnet: «B», «AM»…"""
    preu = round(float(preu or 0), 2)
    millor = promo_automatica(db, tipus, carnet)
    codi_estat = None
    if (codi or "").strip():
        pc = promo_per_codi(db, tipus, codi, carnet)
        codi_estat = bool(pc)
        if pc and (not millor or (pc.percentatge or 0) > (millor.percentatge or 0)):
            millor = pc
    pct = float(millor.percentatge or 0) if millor else 0
    pct = max(0.0, min(pct, 90.0))
    descompte = round(preu * pct / 100, 2)
    return {"preu_base": preu, "descompte": descompte, "total": round(preu - descompte, 2),
            "pct": pct, "promocio": millor.nom if millor and descompte else "",
            "codi_valid": codi_estat}
