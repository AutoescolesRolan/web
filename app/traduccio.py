"""Traducció automàtica dels textos fixos de les plantilles (català ⇄ castellà).

Moltes plantilles tenen el text escrit directament (unes en català i d'altres en castellà).
En lloc de reescriure-les totes amb claus, aquesta extensió de Jinja agafa, en compilar cada
plantilla, els trossos de text que hi ha entre etiquetes HTML (i els atributs placeholder,
title, aria-label i alt) i els passa per `_tx()`. En pintar la pàgina, `_tx()` mira l'idioma
de la persona i, si el text és al diccionari (app/traduccions.py), en posa la versió bona.

  - Si un text no és al diccionari, surt tal com està (mai no es trenca res).
  - El diccionari té, per a cada text, la versió catalana i la castellana: així s'arreglen
    també els textos que estaven en castellà a les pantalles en català (i al revés).
  - No es toca res de dins de <script>, <style> ni de les expressions {{ ... }}.
"""
import re

from jinja2 import nodes  # noqa: F401  (per si cal en el futur)
from jinja2.ext import Extension
from jinja2.lexer import Token
from markupsafe import Markup

_ATRS = re.compile(r'(\s(?:placeholder|title|aria-label|alt)=")([^"{}<>]*)(")')
_LLETRES = re.compile(r"[A-Za-zÀ-ÿ]{2,}")
_JS_LIT = re.compile(r"""(['"])((?:(?!\1)[^\\\n<>{}]){3,300})\1""")
_CONF = re.compile(r"""(?:confirm|alert|prompt)\((&#39;|')([^'&<>{}]{3,300})(?:&#39;|')""")


def _es_frase(txt):
    """Sembla text per a persones (i no un selector, una URL o un nom de variable)?"""
    if not _LLETRES.search(txt) or "/" in txt[:1] or txt.startswith(("#", ".", "http", "data-")):
        return False
    return " " in txt.strip() or bool(re.search(r"[À-ÿ]", txt))


def normalitza(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


_DICC = None
_PER_IDIOMA = {}


def diccionari():
    global _DICC
    if _DICC is None:
        try:
            from .traduccions import TR
        except Exception:
            TR = {}
        from .traduccions_web import TR_WEB
        TR = {**TR, **TR_WEB}           # els textos de la web mana sobre els antics
        _DICC = {normalitza(k): v for k, v in TR.items()}
        _PER_IDIOMA.clear()
    return _DICC


def tradueix(text: str, idioma: str) -> str:
    """Versió `idioma` d'un text fix (o el mateix text si no és al diccionari)."""
    if not text:
        return text
    clau = normalitza(text)
    v = diccionari().get(clau)
    if not v:
        return text
    nou = v[0] if idioma == "ca" else v[1]
    if not nou or nou == clau:
        return text
    # conserva els espais del principi i del final (separen el text de les expressions)
    ini = text[:len(text) - len(text.lstrip())]
    fi = text[len(text.rstrip()):]
    return ini + nou + fi


def _idioma_ctx(ctx) -> str:
    try:
        from . import i18n
        req = ctx.get("request")
        if req is not None:
            if req.url.path.startswith("/gestio"):     # el panell intern és només en català
                return "ca"
            return i18n.get_idioma(req)
        return i18n.IDIOMA_DEFECTO
    except Exception:
        return "ca"


def _tx(ctx, text):
    return Markup(tradueix(text, _idioma_ctx(ctx)))


def _txjs(ctx, text):
    """Per a textos dins de JavaScript: sense cometes ni salts que trenquin el codi."""
    nou = tradueix(text, _idioma_ctx(ctx))
    if nou == text:
        return Markup(text)
    return Markup(nou.replace("\\", "\\\\").replace("'", "\\'").replace('"', '”').replace("\n", " "))


class TraduccioAuto(Extension):
    """Passa els textos fixos de les plantilles per _tx()."""

    def __init__(self, environment):
        super().__init__(environment)
        from jinja2 import pass_context
        environment.globals["_tx"] = pass_context(_tx)
        environment.globals["_txjs"] = pass_context(_txjs)

    def filter_stream(self, stream):
        estat = {"tag": False, "cometa": None, "raw": None}   # dins d'una etiqueta? d'un <script>?
        for tok in stream:
            if tok.type != "data":
                yield tok
                continue
            yield from self._parteix(tok, estat)

    def _parteix(self, tok, estat):
        s, n, i = tok.value, len(tok.value), 0
        buf_text = []

        def text_fora(txt):
            # text entre etiquetes: el separem en espais + contingut + espais
            if not txt:
                return []
            if estat["raw"]:
                return [Token(tok.lineno, "data", txt)]
            cos = txt.strip()
            if not cos or not _LLETRES.search(cos) or ("{" in cos and ":" in cos) or cos.startswith(("//", "/*")):
                return [Token(tok.lineno, "data", txt)]   # buit, CSS o JS: es deixa igual
            ini = txt[:len(txt) - len(txt.lstrip())]
            fi = txt[len(txt.rstrip()):]
            out = []
            if ini:
                out.append(Token(tok.lineno, "data", ini))
            out += [Token(tok.lineno, "variable_begin", "{{"), Token(tok.lineno, "name", "_tx"),
                    Token(tok.lineno, "lparen", "("), Token(tok.lineno, "string", cos),
                    Token(tok.lineno, "rparen", ")"), Token(tok.lineno, "variable_end", "}}")]
            if fi:
                out.append(Token(tok.lineno, "data", fi))
            return out

        sortida = []
        tros = []   # caràcters acumulats del tros actual
        while i < n:
            c = s[i]
            if estat["tag"]:
                tros.append(c)
                if estat["cometa"]:
                    if c == estat["cometa"]:
                        estat["cometa"] = None
                elif c in "\"'":
                    estat["cometa"] = c
                elif c == ">":
                    estat["tag"] = False
                    etiqueta = "".join(tros)
                    sortida += self._atributs(tok, etiqueta)
                    tros = []
                    low = etiqueta.lower()
                    if low.startswith("<script") or low.startswith("<style"):
                        estat["raw"] = "script" if low.startswith("<script") else "style"
                i += 1
                continue
            if c == "<":
                if estat["raw"]:
                    fi = f"</{estat['raw']}"
                    if s[i:i + len(fi)].lower() == fi:
                        sortida += self._js(tok, "".join(tros)) if estat["raw"] == "script" else [Token(tok.lineno, "data", "".join(tros))]
                        tros = []
                        estat["raw"] = None
                    else:
                        tros.append(c)
                        i += 1
                        continue
                else:
                    sortida += text_fora("".join(tros))
                    tros = []
                if s[i:i + 4] == "<!--":
                    j = s.find("-->", i)
                    j = n if j < 0 else j + 3
                    sortida.append(Token(tok.lineno, "data", s[i:j]))
                    i = j
                    continue
                estat["tag"] = True
                tros.append(c)
                i += 1
                continue
            tros.append(c)
            i += 1
        resta = "".join(tros)
        if estat["tag"]:
            # l'etiqueta continua al següent tros (té expressions al mig): no en toquem els atributs
            sortida.append(Token(tok.lineno, "data", resta))
        elif estat["raw"]:
            sortida += self._js(tok, resta) if estat["raw"] == "script" else [Token(tok.lineno, "data", resta)]
        else:
            sortida += text_fora(resta)
        # ajunta els «data» seguits
        for t in sortida:
            if t.type == "data" and not t.value:
                continue
            yield t

    def _js(self, tok, codi):
        """Literals de text de JavaScript ('Segur que vols…?') → {{ _txjs("…") }}."""
        out, pos = [], 0
        for m in _JS_LIT.finditer(codi):
            txt = m.group(2)
            if not _es_frase(txt):
                continue
            out.append(Token(tok.lineno, "data", codi[pos:m.start(2)]))
            out += [Token(tok.lineno, "variable_begin", "{{"), Token(tok.lineno, "name", "_txjs"),
                    Token(tok.lineno, "lparen", "("), Token(tok.lineno, "string", txt),
                    Token(tok.lineno, "rparen", ")"), Token(tok.lineno, "variable_end", "}}")]
            pos = m.end(2)
        out.append(Token(tok.lineno, "data", codi[pos:]))
        return out

    def _atributs(self, tok, etiqueta):
        """placeholder/title/aria-label/alt d'una etiqueta sencera."""
        if not _ATRS.search(etiqueta) and not _CONF.search(etiqueta):
            return [Token(tok.lineno, "data", etiqueta)]
        out, pos = [], 0
        trossos = sorted(list(_ATRS.finditer(etiqueta)) + list(_CONF.finditer(etiqueta)), key=lambda m: m.start(2))
        for m in trossos:
            if m.re is _CONF:
                valor = m.group(2)
                if not _es_frase(valor) or m.start(2) < pos:
                    continue
                out.append(Token(tok.lineno, "data", etiqueta[pos:m.start(2)]))
                out += [Token(tok.lineno, "variable_begin", "{{"), Token(tok.lineno, "name", "_txjs"),
                        Token(tok.lineno, "lparen", "("), Token(tok.lineno, "string", valor),
                        Token(tok.lineno, "rparen", ")"), Token(tok.lineno, "variable_end", "}}")]
                pos = m.end(2)
                continue
            if m.start(2) < pos:
                continue
            valor = m.group(2)
            if not _LLETRES.search(valor):
                continue
            out.append(Token(tok.lineno, "data", etiqueta[pos:m.start(2)]))
            out += [Token(tok.lineno, "variable_begin", "{{"), Token(tok.lineno, "name", "_tx"),
                    Token(tok.lineno, "lparen", "("), Token(tok.lineno, "string", valor),
                    Token(tok.lineno, "rparen", ")"), Token(tok.lineno, "variable_end", "}}")]
            pos = m.end(2)
        out.append(Token(tok.lineno, "data", etiqueta[pos:]))
        return out


def _valor(ctx, v):
    """Tot el que s'escriu amb {{ ... }}: si és un text del diccionari (noms de packs, etapes,
    estats...), surt en l'idioma de la persona. La resta, igual."""
    if type(v) is str and 1 < len(v) < 400 and diccionari():
        nou = tradueix(v, _idioma_ctx(ctx))
        return nou
    return v


def activa(env):
    from jinja2 import pass_context
    env.add_extension(TraduccioAuto)
    env.finalize = pass_context(_valor)
    env.filters["tx"] = pass_context(lambda ctx, v: tradueix(str(v), _idioma_ctx(ctx)) if v is not None else "")


def fragments(env, noms=None):
    """Tots els textos que l'extensió passaria per _tx() (per fer el diccionari)."""
    trobats = {}
    ext = TraduccioAuto(env)
    for nom in (noms or env.list_templates(extensions=["html"])):
        try:
            src, _, _ = env.loader.get_source(env, nom)
            stream = env._tokenize(src, nom)
        except Exception as e:
            print("no es pot llegir", nom, e)
            continue
        toks = list(stream)
        estat = {"tag": False, "cometa": None, "raw": None}
        anterior = None
        for tok in toks:
            if tok.type != "data":
                anterior = tok
                continue
            for t in ext._parteix(tok, estat):
                if t.type == "string":
                    trobats.setdefault(normalitza(t.value), set()).add(nom)
    return trobats
