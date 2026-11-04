"""Assistent amb IA (Gemini de pagament) per a la web pública.

  - Respon dubtes de la matrícula, els packs, les taxes i els exàmens a partir de la guia
    app/ajuda/web.md i de les dades actuals de la web (preus, packs, taxes, centres). No veu
    cap dada personal: ni matrícules ni pagaments.
  - Abans d'enviar res a Gemini, s'amaguen DNI/NIE, correus, telèfons, IBAN i números de targeta.
  - «Parlar amb una persona» desa la consulta a Missatges (panell) i l'envia per correu.
  - Límits: missatges curts, només els darrers torns i un màxim de preguntes per IP.

Variables: GEMINI_API_KEY (la mateixa clau de PAGAMENT que l'app; sense ella, el xat no surt).
GEMINI_MODEL_XAT o GEMINI_MODEL per triar el model.
"""
import json
import os
import re
import time
import urllib.request
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import ajustos, models, preus
from .db import get_db

router = APIRouter()

GUIA = Path(__file__).parent / "ajuda" / "web.md"
MODEL_PER_DEFECTE = "gemini-3.1-flash-lite"
MAX_CARACTERS = 1000
MAX_TORNS = 12
LIMIT_HORA = 40
LIMIT_DIA = 150
LIMIT_PERSONA_HORA = 5
TIMEOUT_S = 30
_COMPTADOR = {}          # ip → [instants] (un sol procés a Render; en reiniciar es buida)


def actiu() -> bool:
    return bool((os.environ.get("GEMINI_API_KEY") or "").strip())


def _model() -> str:
    return ((os.environ.get("GEMINI_MODEL_XAT") or "").strip() or (os.environ.get("GEMINI_MODEL") or "").strip()
            or MODEL_PER_DEFECTE)


# ------------------------------------------------------------------ coneixement
def _eur(v) -> str:
    return preus.eur2(float(v or 0))


def _num(db, clau, defecte):
    try:
        return float((ajustos.get(db, clau, str(defecte)) or str(defecte)).replace(",", "."))
    except ValueError:
        return defecte


def dades_web(db: Session) -> str:
    """El que qualsevol visitant pot veure a la web: centres, packs, preus, taxes i promoció."""
    L = ["# Dades actuals de la web (font: la base de dades; mana sobre qualsevol altra cosa)"]
    L.append(f"- Escola: {ajustos.get(db, 'escola_nom', 'Autoescoles Rolan')} · telèfon general "
             f"{ajustos.get(db, 'escola_telefon', '934 647 857')}")
    L.append("## Centres")
    for c in db.query(models.Centre).filter(models.Centre.actiu == True).order_by(models.Centre.ordre).all():
        tel = " · ".join(x for x in (c.telefon, c.mobil) if x)
        horari = "; ".join(l.replace("|", ":").strip() for l in (c.horari_ca or "").splitlines() if l.strip())
        L.append(f"- {c.nom}: {c.adreca}, {c.cp_localitat}" + (f" · tel. {tel}" if tel else "")
                 + (f" · horari de teòrica: {horari}" if horari else ""))
    promo = preus.promo_automatica(db, "matricula")
    pct = float(promo.percentatge or 0) if promo else 0
    if promo:
        L.append(f"## Promoció vigent: {promo.nom} (−{pct:g} % als packs de matrícula, ja aplicat al pagament) "
                 f"fins al {preus.local(promo.fi).strftime('%d/%m/%Y') if promo.fi else '—'}")
    L.append("## Carnets i packs de matrícula (preus amb IVA)")
    taxa, taxa_a = _num(db, "taxa_dgt", 94.05), _num(db, "taxa_dgt_a", 28.87)
    canon, exped = _num(db, "canon_pistes", 35), _num(db, "preu_expedient", 125)
    for car in db.query(models.Carnet).filter(models.Carnet.actiu == True).order_by(models.Carnet.ordre).all():
        packs = [p for p in car.packs if p.actiu and p.preu > 0]
        if not packs:
            continue
        L.append(f"### Carnet {car.codi} — {car.nom_ca} ({car.sub_ca})")
        if car.examens_ca:
            L.append(f"- Exàmens del carnet: {car.examens_ca}")
        L.append(f"- Taxes: {car.taxes_ca}")
        for p in packs:
            preu = f"{_eur(p.preu)} €"
            if pct:
                preu = f"{_eur(round(p.preu * (1 - pct / 100), 2))} € amb la promoció (preu normal {_eur(p.preu)} €)"
            inclou = "; ".join(x.strip() for x in (p.inclou_ca or "").splitlines() if x.strip())
            L.append(f"- Pack «{p.nom_ca}»: {preu} · {p.classes} pràctiques de 45' · inclou: {inclou or '—'}")
        for tipus, titol in (("classes", "Classes soltes (es paguen al centre)"),
                             ("examens", "Exàmens i taxes (NO inclosos al pack si no surten a «inclou»)")):
            files = ajustos.tarifes(db, f"tarifes_{tipus}_{car.codi}")
            if files:
                L.append(f"- {titol}: " + "; ".join(f"{ca} {preu} €" for ca, _es, preu in files))
    L.append("## Taxes i altres imports")
    L.append(f"- Taxa oficial de la DGT (B, AM, A1, A2): {_eur(taxa)} € · carnet A: {_eur(taxa_a)} €. "
             "No inclosa als packs; es pot afegir al pagament de la matrícula o pagar al centre.")
    L.append(f"- Cànon de pistes (motos, obligatori per a l'examen de maniobres): {_eur(canon)} €. No inclòs als packs.")
    L.append(f"- Renovació d'expedient (si s'esgoten les convocatòries de la taxa): {_eur(exped)} € + l'examen corresponent.")
    pp = (db.query(models.PackPractiques).filter(models.PackPractiques.actiu == True)
          .order_by(models.PackPractiques.classes).all())
    if pp:
        L.append("## Packs de pràctiques per a alumnes ja matriculats (NO es compren a la web: al centre)")
        L.append("- " + "; ".join(f"{p.classes} classes: {_eur(p.preu)} €" for p in pp))
    return "\n".join(L)


def instruccions(db: Session, pagina: str = "", titol: str = "", idioma: str = "ca") -> str:
    try:
        guia = GUIA.read_text(encoding="utf-8")
    except OSError:
        guia = ""
    llengua = "CASTELLÀ" if idioma == "es" else "CATALÀ"
    on = (f"- Ara és a la pàgina {pagina[:200]}" + (f" («{titol[:120]}»)" if titol else "")
          + ". Si pregunta «què és això» o «com ho faig», parla d'aquesta pàgina.\n") if pagina else ""
    return (
        "Ets l'assistent virtual de la web d'" + ajustos.get(db, "escola_nom", "Autoescoles Rolan") + ". "
        "Parles amb una persona que mira la web i potser es vol matricular. El teu objectiu és resoldre-li els dubtes "
        "(sobretot què inclou cada pack, quines TAXES i quins EXÀMENS haurà de pagar per poder-se presentar, i com "
        "funciona la matrícula) perquè es pugui matricular tranquil·la, i acabar amb el pas següent i l'enllaç.\n\n"
        "Normes:\n" + on +
        "- Respon NOMÉS amb la informació de la guia i de les dades de sota. Si no hi és, digues que no ho saps i "
        "proposa parlar amb una persona (cal_persona = true). No t'inventis mai preus, dates, horaris, requisits ni normes.\n"
        "- Els preus i el que inclou cada pack surten de les dades de sota: dona'ls exactes, amb €. Quan expliquis "
        "el preu d'un pack, digues també què NO inclou (taxa de la DGT, cànon a les motos i, al B, els exàmens).\n"
        "- No tens accés a cap matrícula, pagament ni dada personal. Si et pregunten per la seva, proposa parlar amb una persona.\n"
        "- No demanis mai dades personals. Si te'n donen, no les repeteixis.\n"
        f"- IDIOMA: escriu TOTA la resposta en {llengua} (l'idioma en què escriu la persona). No barregis idiomes.\n"
        "- Sigues breu, clar i amable: 2-6 frases o una llista curta. Pots fer servir **negreta**.\n"
        "- Enllaça sempre la pàgina exacta amb el format [Nom](/ruta), fent servir NOMÉS les adreces de la guia.\n"
        "- Si demana parlar amb algú, o és una queixa, un problema amb un pagament o un cas personal, posa cal_persona = true.\n"
        "- No parlis de temes que no tinguin a veure amb l'autoescola.\n\n"
        + guia + "\n\n" + dades_web(db)
    )


# ------------------------------------------------------------------ privacitat
_PATRONS = [
    (re.compile(r"\b[XYZxyz]?\s?\d{7,8}\s?-?\s?[A-Za-z]\b"), "[DNI amagat]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[correu amagat]"),
    (re.compile(r"\b[A-Z]{2}\d{2}(?:\s?\d{4}){4,5}\b"), "[IBAN amagat]"),
    (re.compile(r"(?<!\d)(?:\+?34[\s.-]?)?[6-9]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?!\d)"), "[telèfon amagat]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[número amagat]"),
]


def amaga_dades(text: str) -> str:
    for patro, subst in _PATRONS:
        text = patro.sub(subst, text)
    return text


# ------------------------------------------------------------------ idioma
_CA = re.compile(r"(?<!\w)(amb|què|també|perquè|això|aquest|aquesta|els|dels|als|pel|meu|meva|teu|teva|puc|pots|vull|"
                 r"tinc|tens|quin|quina|quins|quines|quan|com|on|és|són|fer|ara|molt|gràcies|hi ha|cap|haig|he de)(?!\w)"
                 r"|\bl'|\bd'|·l", re.I)
_ES = re.compile(r"(?<!\w)(con|qué|también|porque|esto|este|esta|los|las|tengo|tienes|tiene|quiero|puedo|puedes|hay|"
                 r"dónde|donde|cómo|cuándo|cuando|cuál|cual|soy|es|son|hacer|ahora|mucho|gracias|tengo que)(?!\w)|ñ|¿|¡", re.I)


def idioma_de(text: str, defecte: str = "ca") -> str:
    ca, es = len(_CA.findall(text or "")), len(_ES.findall(text or ""))
    return "ca" if ca > es else ("es" if es > ca else defecte)


# ------------------------------------------------------------------ Gemini
_ESQUEMA = {"type": "OBJECT", "properties": {"resposta": {"type": "STRING"}, "cal_persona": {"type": "BOOLEAN"}},
            "required": ["resposta", "cal_persona"]}


def _crida_gemini(sistema: str, torns: list) -> dict:
    cos = {
        "systemInstruction": {"parts": [{"text": sistema}]},
        "contents": [{"role": ("model" if t["rol"] == "assistent" else "user"), "parts": [{"text": t["text"]}]}
                     for t in torns],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": _ESQUEMA,
                             "temperature": 0.3, "maxOutputTokens": 900},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{_model()}:generateContent",
        data=json.dumps(cos).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": (os.environ.get("GEMINI_API_KEY") or "").strip()})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        resp = json.loads(r.read().decode("utf-8"))
    text = "".join(p.get("text", "") for p in resp["candidates"][0]["content"]["parts"])
    text = re.sub(r"^```(?:json)?|```$", "", text.strip()).strip()
    return json.loads(text)


# ------------------------------------------------------------------ límits
def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")) or "?"


def _dins_limit(clau: str, per_hora: int, per_dia: int = 0) -> bool:
    ara = time.time()
    llista = [t for t in _COMPTADOR.get(clau, []) if ara - t < 86400]
    hora = sum(1 for t in llista if ara - t < 3600)
    if hora >= per_hora or (per_dia and len(llista) >= per_dia):
        _COMPTADOR[clau] = llista
        return False
    llista.append(ara)
    _COMPTADOR[clau] = llista
    return True


def _neteja_torns(missatges) -> list:
    torns = []
    for m in (missatges or [])[-MAX_TORNS:]:
        if not isinstance(m, dict):
            continue
        rol = "assistent" if m.get("rol") == "assistent" else "usuari"
        text = str(m.get("text") or "").strip()[:MAX_CARACTERS]
        if text:
            torns.append({"rol": rol, "text": amaga_dades(text) if rol == "usuari" else text})
    while torns and torns[0]["rol"] != "usuari":
        torns.pop(0)
    return torns


# ------------------------------------------------------------------ rutes
@router.get("/assistent/qui")
def qui():
    return JSONResponse({"actiu": actiu(), "context": "visitant"})


@router.post("/assistent/xat")
async def xat(request: Request, db: Session = Depends(get_db)):
    if not actiu():
        return JSONResponse({"ok": False, "motiu": "desactivat"}, status_code=503)
    try:
        cos = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "motiu": "format"}, status_code=400)
    torns = _neteja_torns(cos.get("missatges") if isinstance(cos, dict) else None)
    if not torns or torns[-1]["rol"] != "usuari":
        return JSONResponse({"ok": False, "motiu": "buit"}, status_code=400)
    if not _dins_limit(f"xat:{_ip(request)}", LIMIT_HORA, LIMIT_DIA):
        return JSONResponse({"ok": False, "motiu": "limit"}, status_code=429)
    idioma = idioma_de(torns[-1]["text"], "es" if cos.get("idioma") == "es" else "ca")
    try:
        r = _crida_gemini(instruccions(db, str(cos.get("pagina") or "")[:300], str(cos.get("titol") or ""), idioma), torns)
        resposta = str(r.get("resposta") or "").strip()
    except Exception as e:
        print(f"[assistent] Gemini no ha respost: {e}")
        return JSONResponse({"ok": False, "motiu": "error"}, status_code=502)
    if not resposta:
        return JSONResponse({"ok": False, "motiu": "error"}, status_code=502)
    return JSONResponse({"ok": True, "resposta": resposta[:4000], "cal_persona": bool(r.get("cal_persona"))})


@router.post("/assistent/persona")
async def persona(request: Request, db: Session = Depends(get_db)):
    """«Parlar amb una persona»: es desa a Missatges i s'envia per correu a l'escola."""
    from . import comandes, correu
    from html import escape
    try:
        cos = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "motiu": "format"}, status_code=400)
    nom = str(cos.get("nom") or "").strip()[:160]
    contacte = str(cos.get("contacte") or "").strip()[:160]
    missatge = str(cos.get("missatge") or "").strip()[:3000]
    if not missatge or not contacte:
        return JSONResponse({"ok": False, "motiu": "falten"}, status_code=400)
    if not _dins_limit(f"persona:{_ip(request)}", LIMIT_PERSONA_HORA):
        return JSONResponse({"ok": False, "motiu": "limit"}, status_code=429)
    es_correu = "@" in contacte
    conversa = [m for m in (cos.get("conversa") or [])[-12:] if isinstance(m, dict)]
    text_conv = "\n".join(f"- {'Assistent' if m.get('rol') == 'assistent' else 'Persona'}: "
                          f"{str(m.get('text') or '')[:600]}" for m in conversa)
    m = models.Missatge(nom=nom or "(sense nom)", email=contacte if es_correu else "",
                        telefon="" if es_correu else contacte,
                        text=(missatge + ("\n\n— Conversa amb l'assistent —\n" + text_conv if text_conv else ""))[:5000])
    db.add(m)
    db.commit()
    # a qui va: els correus d'admin del panell; si no n'hi ha, la secretaria del primer centre
    dest = ajustos.correus_admin(db)
    if not dest:
        c = db.query(models.Centre).filter(models.Centre.actiu == True, models.Centre.email != "").order_by(models.Centre.ordre).first()
        dest = [c.email] if c else [ajustos.correu_general(db)]
    dest = [d for d in dest if d]
    html = (f"<p><b>{escape(m.nom)}</b> ha demanat parlar amb una persona des de l'assistent de la web:</p>"
            f'<blockquote style="border-left:3px solid #8BC53F;margin:10px 0;padding:6px 12px;color:#14224F">'
            f'{escape(missatge).replace(chr(10), "<br>")}</blockquote>'
            f"<p>Contacte: {escape(contacte)}</p>"
            + (f'<p style="color:#6b7280;font-size:13px">Conversa amb l\'assistent:<br>{escape(text_conv).replace(chr(10), "<br>")}</p>'
               if text_conv else "")
            + ("<p>Respon aquest correu i la resposta li arriba directament.</p>" if es_correu
               else "<p>Ha deixat un telèfon: truca-li o escriu-li.</p>"))
    text = (f"{m.nom} ha demanat parlar amb una persona des de l'assistent de la web:\n\n{missatge}\n\n"
            f"Contacte: {contacte}\n\n" + (f"Conversa amb l'assistent:\n{text_conv}\n" if text_conv else ""))
    if dest:
        ok, msg = correu.envia(dest, f"Consulta des de l'assistent · {m.nom}", comandes._html_correu(html), text,
                               respondre_a=contacte if es_correu else "")
        m.enviat = f"{'OK' if ok else 'NO'} · {msg}"[:200]
        db.commit()
    return JSONResponse({"ok": True})
