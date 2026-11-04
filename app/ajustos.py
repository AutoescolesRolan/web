"""Dades de l'autoescola i opcions (taula «ajustos»)."""
from . import models


def tots(db) -> dict:
    return {a.clau: (a.valor or "") for a in db.query(models.Ajust).all()}


def get(db, clau, defecte=""):
    a = db.get(models.Ajust, clau)
    return (a.valor or "").strip() if a and a.valor else defecte


def desa(db, clau, valor):
    a = db.get(models.Ajust, clau)
    if a:
        a.valor = valor
    else:
        db.add(models.Ajust(clau=clau, valor=valor))


def correu_general(db) -> str:
    """Correu general de l'escola: el dels ajustos o, si és buit, el del primer centre."""
    v = get(db, "escola_email")
    if v:
        return v
    c = db.query(models.Centre).filter(models.Centre.actiu == True).order_by(models.Centre.ordre).first()
    return c.email if c else ""


def correus_admin(db) -> list:
    return [x.strip() for x in get(db, "correus_admin").replace(";", ",").split(",") if x.strip()]


def tarifes(db, clau) -> list:
    """«Concepte ca | Concepte es | 99,99» per línia → [(ca, es, preu_text)]."""
    out = []
    for linia in get(db, clau).splitlines():
        parts = [p.strip() for p in linia.split("|")]
        if len(parts) == 3 and parts[0]:
            out.append(tuple(parts))
    return out


def falten_dades_legals(db) -> list:
    """Dades que cal omplir abans de publicar (avís legal, contracte)."""
    noms = {"escola_rao_social": "Raó social", "escola_domicili": "Domicili fiscal",
            "escola_num_provincial": "Número d'autorització de la DGT"}
    return [n for k, n in noms.items() if not get(db, k)]


def ga_id(db) -> str:
    """ID de mesura de Google Analytics 4 (G-XXXXXXX), o "" si no n'hi ha o no és vàlid."""
    import os
    import re
    v = (get(db, "google_analytics_id", "") or os.environ.get("GOOGLE_ANALYTICS_ID") or "").strip().upper()
    return v if re.fullmatch(r"G-[A-Z0-9]{4,20}", v) else ""
