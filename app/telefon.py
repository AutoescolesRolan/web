"""Telèfons: prefix de país + número, iguals a tota l'app.

- Espanya (+34, per defecte): exactament 9 xifres. Es desa com sempre, només les 9 xifres.
- Altres països: de 4 a 14 xifres. Es desa amb el prefix: "+33 612345678".
- Si el camp és opcional i es deixa buit, no passa res.

A les plantilles: {% import "_telefon.html" as tel %} i {{ tel.camp("telefono", valor) }}.
El formulari envia el número al camp `name` i el prefix a `name + "__pais"`.
"""
from __future__ import annotations

import re

# (prefix, codi de país) — Espanya primer; la resta, els més habituals entre l'alumnat
PAISOS = [
    ("34", "ES"), ("376", "AD"), ("351", "PT"), ("33", "FR"), ("39", "IT"), ("49", "DE"), ("44", "GB"),
    ("31", "NL"), ("32", "BE"), ("41", "CH"), ("48", "PL"), ("40", "RO"), ("359", "BG"), ("380", "UA"),
    ("7", "RU"), ("995", "GE"), ("212", "MA"), ("213", "DZ"), ("221", "SN"), ("234", "NG"), ("233", "GH"),
    ("86", "CN"), ("91", "IN"), ("92", "PK"), ("880", "BD"), ("63", "PH"), ("1", "US/CA"), ("52", "MX"),
    ("53", "CU"), ("1809", "DO"), ("504", "HN"), ("57", "CO"), ("58", "VE"), ("593", "EC"), ("51", "PE"),
    ("591", "BO"), ("595", "PY"), ("598", "UY"), ("54", "AR"), ("56", "CL"), ("55", "BR"),
]
_PREFIXOS = sorted({p for p, _ in PAISOS}, key=len, reverse=True)


def normalitza(valor: str | None, pais: str | None = "34", obligatori: bool = False) -> str:
    """Torna el telèfon net per desar-lo, o "" si és buit i opcional. ValueError si no és vàlid."""
    v = (valor or "").strip()
    if not v:
        if obligatori:
            raise ValueError("buit")
        return ""
    if v.startswith("+") or v.startswith("00"):          # algú ha escrit el prefix al número
        xifres = re.sub(r"\D", "", v)
        if v.startswith("00"):
            xifres = xifres[2:]
        pre = next((p for p in _PREFIXOS if xifres.startswith(p)), None)
        if not pre:
            raise ValueError("prefix")
        pais, v = pre, xifres[len(pre):]
    pais = re.sub(r"\D", "", pais or "34") or "34"
    if pais not in {p for p, _ in PAISOS}:
        raise ValueError("prefix")
    xifres = re.sub(r"[\s.\-()/]", "", v)
    if not xifres.isdigit():
        raise ValueError("xifres")
    if pais == "34":
        if len(xifres) != 9:
            raise ValueError("llargada")
        return xifres
    if not 4 <= len(xifres) <= 14:
        raise ValueError("llargada")
    return f"+{pais} {xifres}"


def separa(valor: str | None) -> tuple[str, str]:
    """(prefix, número) d'un telèfon desat, per tornar-lo a mostrar al formulari."""
    v = (valor or "").strip()
    if v.startswith("+"):
        xifres = re.sub(r"\D", "", v)
        pre = next((p for p in _PREFIXOS if xifres.startswith(p)), None)
        if pre:
            return pre, xifres[len(pre):]
    return "34", re.sub(r"[\s.\-]", "", v)


def registra(env) -> None:
    env.globals["telefon_paisos"] = PAISOS
    env.globals["telefon_separa"] = separa
