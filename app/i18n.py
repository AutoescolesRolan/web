"""Idioma de la web: català per defecte; castellà si la persona el tria (es guarda a la sessió)."""
IDIOMA_DEFECTO = "ca"
IDIOMAS_DISPONIBLES = ("ca", "es")


def get_idioma(request) -> str:
    try:
        v = request.session.get("idioma", IDIOMA_DEFECTO)
        return v if v in IDIOMAS_DISPONIBLES else IDIOMA_DEFECTO
    except Exception:
        return IDIOMA_DEFECTO
