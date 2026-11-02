"""DNI i NIE: comprovació de la lletra de control (algorisme oficial del Ministeri de l'Interior).

- DNI: 8 xifres + lletra. La lletra és la del residu de dividir el número entre 23
  a la taula TRWAGMYFPDXBNJZSQVHLCKE. (Si s'escriuen 7 xifres s'hi afegeix el 0 del davant.)
- NIE: X, Y o Z + 7 xifres + lletra. La X, Y, Z valen 0, 1, 2 per calcular la lletra.

Només comprova que el número estigui ben format i que la lletra quadri (detecta errors en
teclejar); no pot saber si el document existeix ni de qui és.
"""
from __future__ import annotations

import re

LLETRES = "TRWAGMYFPDXBNJZSQVHLCKE"
_DNI = re.compile(r"^(\d{7,8})([A-Z])$")
_NIE = re.compile(r"^([XYZ])(\d{7})([A-Z])$")


def lletra(numero: int) -> str:
    return LLETRES[numero % 23]


def neteja(valor: str | None) -> str:
    return re.sub(r"[\s.\-_/]", "", (valor or "").upper())


def normalitza(valor: str | None, obligatori: bool = False) -> str:
    """Torna el DNI/NIE net (majúscules, sense espais ni guions) o "" si és buit i opcional.
    ValueError("format") si no té forma de DNI/NIE; ValueError("lletra") si la lletra no quadra."""
    v = neteja(valor)
    if not v:
        if obligatori:
            raise ValueError("buit")
        return ""
    m = _DNI.match(v)
    if m:
        num = m.group(1).zfill(8)
        if lletra(int(num)) != m.group(2):
            raise ValueError("lletra")
        return num + m.group(2)
    m = _NIE.match(v)
    if m:
        if lletra(int("XYZ".index(m.group(1)) * 10**7 + int(m.group(2)))) != m.group(3):
            raise ValueError("lletra")
        return v
    raise ValueError("format")


def es_valid(valor: str | None) -> bool:
    try:
        return bool(normalitza(valor, obligatori=True))
    except ValueError:
        return False


MISSATGES = {
    "format": "El DNI/NIE no té el format correcte (8 xifres i una lletra, o X/Y/Z + 7 xifres i una lletra).",
    "lletra": "La lletra del DNI/NIE no correspon al número. Revisa que l'hagis escrit bé.",
    "buit": "Cal el DNI o NIE.",
}
