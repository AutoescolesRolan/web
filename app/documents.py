"""Contracte de matrícula i rebut de pagament, en PDF.

El contracte surt de la plantilla .docx de cada pack (app/contractes), la mateixa que fa
servir l'autoescola en paper, amb les dades de l'alumne, la signatura feta a la pantalla i
el segell de l'autoescola. Tot en Python (reportlab + Pillow): funciona igual a Render.
"""
import base64
import hashlib
import io
import os
import unicodedata
from datetime import datetime
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import ajustos, preus

DIR = os.path.dirname(__file__)
LOGO = os.path.join(DIR, "static", "img", "logo-rolan.png")
CONTRACTES = os.path.join(DIR, "contractes")
TINTA = colors.HexColor("#14224F")
BLAU = colors.HexColor("#1A2E82")
GRIS = colors.HexColor("#66708C")


def _data(d):
    return d.strftime("%d/%m/%Y") if d else ""


def context_contracte(db, c, pack) -> dict:
    a = ajustos.tots(db)
    clausula = f" + {pack.classes} classes 45'" if pack and pack.classes and (c.carnet_codi == "B") else ""
    return {
        "escola_nom": a.get("escola_rao_social") or a.get("escola_nom", ""),
        "escola_nif": a.get("escola_nif", ""), "escola_domicili": a.get("escola_domicili", ""),
        "escola_telefon": a.get("escola_telefon", ""), "escola_email": ajustos.correu_general(db),
        "escola_titular": a.get("escola_titular", ""), "escola_num_provincial": a.get("escola_num_provincial", ""),
        "escola_localitat": a.get("escola_localitat", ""),
        "alumne_nom": c.nom_complet, "alumne_dni": c.dni,
        "alumne_naixement": c.naixement.strftime("%d.%m.%Y") if c.naixement else "",
        "alumne_adreca": c.adreca, "alumne_cp_localitat": " - ".join(x for x in (c.cp, c.localitat) if x),
        "pack_codi": c.carnet_codi, "pack_classes_clausula": clausula,
        "pack_preu_total": preus.eur(c.preu_base),
        "data_contracte": (c.signat_en or datetime.now()).strftime("%d.%m.%Y"),
    }


def blocs_contracte(db, c, pack):
    """Text del contracte en blocs: ('titol'|'text'|'consent', text)."""
    from docx import Document
    from docxtpl import DocxTemplate
    from docx.oxml.ns import qn
    from docx.table import Table as DocxT
    from docx.text.paragraph import Paragraph as DocxP

    ruta = os.path.join(CONTRACTES, (pack.contracte if pack else "") or "B.docx")
    if not os.path.exists(ruta):
        ruta = os.path.join(CONTRACTES, "B.docx")
    tpl = DocxTemplate(ruta)
    tpl.render(context_contracte(db, c, pack))
    buf = io.BytesIO()
    tpl.save(buf)
    buf.seek(0)
    doc = Document(buf)
    blocs = []
    for fill in doc.element.body.iterchildren():
        if fill.tag == qn("w:p"):
            p = DocxP(fill, doc)
            t = " ".join((p.text or "").split())
            if not t:
                continue
            estil = (getattr(p.style, "name", "") or "").lower()
            es_titol = estil.startswith(("heading", "títol", "titulo")) or (t.isupper() and len(t) < 60)
            blocs.append(("titol" if es_titol else "text", t))
        elif fill.tag == qn("w:tbl"):
            for row in DocxT(fill, doc).rows:
                vist, netes = set(), []
                for cel in row.cells:
                    t = " ".join((cel.text or "").split())
                    if t and t not in vist:
                        netes.append(t)
                        vist.add(t)
                if netes:
                    blocs.append(("text", " · ".join(netes)))
    # la línia de signatures de la plantilla de paper no cal: les signatures van al final
    blocs = [b for b in blocs if not b[1].lower().startswith(("data ", "signat alumne"))]
    # caselles SÍ/NO de la protecció de dades → la tria de l'alumne
    acc = c.acceptacions or ""
    sortida = []
    for i, (tipus, t) in enumerate(blocs):
        n = " ".join(t.upper().replace("Í", "I").split())
        if n in ("SI NO", "SI/NO", "SI - NO", "SI-NO"):
            seg = blocs[i + 1][1].lower() if i + 1 < len(blocs) else ""
            if any(k in seg for k in ("fotografia", "imatge", "vídeo", "video", "màrqueting")):
                sortida.append(("consent", "imatge=si" in acc))
            elif any(k in seg for k in ("comercial", "nous serveis", "informativ")):
                sortida.append(("consent", "comercial=si" in acc))
            else:
                sortida.append(("consent", None))
        else:
            sortida.append((tipus, t))
    return sortida


def _segell(nom, localitat, nif) -> io.BytesIO:
    S = 620
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    blau = (26, 46, 130, 235)
    d.ellipse([12, 12, S - 12, S - 12], outline=blau, width=10)
    d.ellipse([46, 46, S - 46, S - 46], outline=blau, width=5)

    def fnt(sz, bold=True):
        for n in (["DejaVuSans-Bold.ttf", "DejaVuSans.ttf"] if bold else ["DejaVuSans.ttf"]):
            try:
                return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{n}", sz)
            except Exception:
                pass
        return ImageFont.load_default()

    def centrat(txt, y, f):
        d.text(((S - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=blau)

    parts = (nom or "AUTOESCOLES ROLAN").upper().split()
    if len(parts) > 1:
        centrat(parts[0], 150, fnt(58))
        centrat(" ".join(parts[1:])[:16], 220, fnt(58))
    else:
        centrat(parts[0], 185, fnt(58))
    centrat("· SIGNAT I SEGELLAT ·", 300, fnt(30))
    if nif:
        centrat(f"NIF {nif}", 350, fnt(30, False))
    if localitat:
        centrat(localitat.upper(), 392, fnt(30, False))
    centrat("★  ★  ★", 445, fnt(34))
    im = im.rotate(9, expand=True, resample=Image.BICUBIC)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    buf.seek(0)
    return buf


def _estils():
    ss = getSampleStyleSheet()
    base = ss["Normal"]
    return {
        "org": ParagraphStyle("org", parent=base, fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=TINTA),
        "sub": ParagraphStyle("sub", parent=base, fontName="Helvetica", fontSize=8.5, leading=11, textColor=GRIS,
                              spaceBefore=2),
        "tit": ParagraphStyle("tit", parent=base, fontName="Helvetica-Bold", fontSize=15, textColor=TINTA,
                              spaceBefore=8, spaceAfter=10),
        "h": ParagraphStyle("h", parent=base, fontName="Helvetica-Bold", fontSize=10.5, textColor=BLAU,
                            spaceBefore=8, spaceAfter=3),
        "p": ParagraphStyle("p", parent=base, fontName="Helvetica", fontSize=9.3, leading=13,
                            alignment=TA_JUSTIFY, textColor=colors.HexColor("#222b45"), spaceAfter=3),
        "kv": ParagraphStyle("kv", parent=base, fontName="Helvetica-Bold", fontSize=9.3, textColor=TINTA),
        "sig": ParagraphStyle("sig", parent=base, fontName="Helvetica", fontSize=9, textColor=TINTA,
                              alignment=TA_CENTER, leading=12),
        "dreta": ParagraphStyle("dreta", parent=base, fontName="Helvetica", fontSize=9, textColor=GRIS,
                                alignment=TA_RIGHT),
        "petit": ParagraphStyle("petit", parent=base, fontName="Helvetica", fontSize=7.8, leading=10,
                                textColor=GRIS, alignment=TA_JUSTIFY),
    }


def _capcalera(db, st, titol):
    a = ajustos.tots(db)
    nom = a.get("escola_nom") or "Autoescoles Rolan"
    linia = " · ".join(x for x in (a.get("escola_rao_social"), f"NIF {a['escola_nif']}" if a.get("escola_nif") else "",
                                    a.get("escola_domicili") or a.get("escola_localitat")) if x)
    bloc = [Paragraph(escape(nom), st["org"])]
    if linia:
        bloc.append(Paragraph(escape(linia), st["sub"]))
    story = []
    if os.path.exists(LOGO):
        story.append(Table([[RLImage(LOGO, width=17 * mm, height=17 * mm), bloc]], colWidths=[20 * mm, None],
                           style=TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                             ("LEFTPADDING", (0, 0), (-1, -1), 0)])))
    else:
        story += bloc
    story.append(Paragraph(escape(titol), st["tit"]))
    return story


def contracte_pdf(db, c, pack) -> bytes:
    a = ajustos.tots(db)
    st = _estils()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title="Contracte de matrícula")
    story = _capcalera(db, st, "Contracte de matrícula")
    e = escape
    story.append(Paragraph(f"<b>Alumne/a:</b> {e(c.nom_complet)} &nbsp;&nbsp; <b>DNI/NIE:</b> {e(c.dni)}"
                           f" &nbsp;&nbsp; <b>Data de naixement:</b> {_data(c.naixement)}", st["p"]))
    adreca = " · ".join(x for x in (c.adreca, " ".join(y for y in (c.cp, c.localitat) if y)) if x)
    story.append(Paragraph(f"<b>Adreça:</b> {e(adreca or '—')} &nbsp;&nbsp; <b>Telèfon:</b> {e(c.telefon)}"
                           f" &nbsp;&nbsp; <b>Correu:</b> {e(c.email)}", st["p"]))
    centre = c.centre.nom if c.centre else ""
    story.append(Paragraph(f"<b>Centre:</b> {e(centre)} &nbsp;&nbsp; <b>Carnet:</b> {e(c.carnet_codi)}"
                           f" &nbsp;&nbsp; <b>Pack:</b> {e(c.producte)} ({preus.eur2(c.preu_base)} €)", st["p"]))
    if c.tutor_nom:
        story.append(Paragraph(f"<b>Tutor/a legal:</b> {e(c.tutor_nom)} &nbsp;&nbsp; <b>DNI/NIE:</b> "
                               f"{e(c.tutor_dni)}", st["p"]))
    story.append(Spacer(1, 6))
    for tipus, t in blocs_contracte(db, c, pack):
        if tipus == "titol":
            story.append(Paragraph(e(t), st["h"]))
        elif tipus == "consent":
            marca = ("[ X ] SÍ &nbsp;&nbsp; [ &nbsp; ] NO" if t is True else
                     "[ &nbsp; ] SÍ &nbsp;&nbsp; [ X ] NO" if t is False else "[ &nbsp; ] SÍ &nbsp;&nbsp; [ &nbsp; ] NO")
            story.append(Paragraph(f"<b>{marca}</b>", st["kv"]))
        else:
            story.append(Paragraph(e(t), st["p"]))

    # Annex de la contractació en línia
    story.append(Paragraph("Contractació en línia", st["h"]))
    signat = preus.local(c.signat_en)
    linies = [f"Contracte signat electrònicament a la web el {signat.strftime('%d/%m/%Y a les %H:%M') if signat else ''}"
              f" (hora de Barcelona) des de l'adreça IP {e(c.ip_signatura or '—')}."]
    extres = "".join([f" + taxa DGT {preus.eur2(c.taxa)} €" if c.taxa else "",
                      f" + cànon de pistes {preus.eur2(c.canon)} €" if c.canon else ""])
    if c.descompte:
        linies.append(f"Promoció aplicada al pack: {e(c.promocio)} (−{preus.eur2(c.descompte)} €).")
    linies.append(f"Pagament en línia amb targeta: pack {preus.eur2(c.preu_base - c.descompte)} €{extres}. "
                  f"Total: {preus.eur2(c.total)} €, IVA inclòs.")
    if "inici_immediat=si" in (c.acceptacions or ""):
        linies.append("L'alumne/a ha demanat expressament començar el servei abans que acabi el termini de "
                      "desistiment de 14 dies i ha estat informat/da que, si en desisteix, haurà de pagar la part "
                      "del servei ja prestada (art. 108 del Text refós de la Llei general per a la defensa dels "
                      "consumidors i usuaris).")
    for l in linies:
        story.append(Paragraph(l, st["p"]))
    story.append(Spacer(1, 16))

    firma = Spacer(1, 46)
    if c.signatura and "," in c.signatura:
        try:
            png = base64.b64decode(c.signatura.split(",", 1)[1])
            firma = RLImage(io.BytesIO(png), width=52 * mm, height=22 * mm, kind="proportional")
        except Exception:
            pass
    data = _data(preus.local(c.signat_en))
    if c.tutor_nom:
        signant = (f"El tutor/a legal<br/>{e(c.tutor_nom)} · DNI {e(c.tutor_dni)}<br/><font size=8 color='#66708C'>"
                   f"en representació de {e(c.nom_complet)} · Signat el {data}</font>")
    else:
        signant = f"L'alumne/a<br/>{e(c.nom_complet)}<br/><font size=8 color='#66708C'>Signat el {data}</font>"
    nom = a.get("escola_nom") or "Autoescoles Rolan"
    t = Table([[firma, RLImage(_segell(nom, a.get("escola_localitat"), a.get("escola_nif")), width=34 * mm, height=34 * mm)],
               [Paragraph(signant, st["sig"]),
                Paragraph(f"Per {e(nom)}<br/><font size=8 color='#66708C'>Segell de l'autoescola</font>", st["sig"])]],
              colWidths=[85 * mm, 85 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, 0), "BOTTOM"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                           ("LINEABOVE", (0, 1), (0, 1), 0.7, colors.HexColor("#B0B7CC")),
                           ("TOPPADDING", (0, 1), (-1, 1), 6)]))
    story.append(t)
    doc.build(story)
    return buf.getvalue()


def rebut_pdf(db, c) -> bytes:
    """Rebut del pagament (no és factura: la factura la fa la secretaria)."""
    st = _estils()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=f"Rebut {c.num_rebut}")
    story = _capcalera(db, st, "Rebut de pagament")
    e = escape
    dades = [["Número de rebut", c.num_rebut], ["Data del pagament", _data(preus.local(c.pagat_en))],
             ["Alumne/a", c.nom_complet], ["DNI/NIE", c.dni], ["Correu", c.email],
             ["Centre", c.centre.nom if c.centre else ""], ["Forma de pagament", "Targeta (pagament en línia)"]]
    t = Table([[Paragraph(f"<b>{e(k)}</b>", st["p"]), Paragraph(e(v or "—"), st["p"])] for k, v in dades],
              colWidths=[45 * mm, None])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#E6E9F2")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [t, Spacer(1, 14)]
    linies = [["Concepte", "Import"], [Paragraph(e(c.producte), st["p"]), f"{preus.eur2(c.preu_base)} €"]]
    if c.descompte:
        linies.append([Paragraph(e(f"Descompte · {c.promocio}"), st["p"]), f"−{preus.eur2(c.descompte)} €"])
    if c.taxa:
        linies.append([Paragraph("Taxa oficial de la DGT", st["p"]), f"{preus.eur2(c.taxa)} €"])
    if c.canon:
        linies.append([Paragraph("Cànon de pistes", st["p"]), f"{preus.eur2(c.canon)} €"])
    linies.append([Paragraph("<b>Total pagat (IVA inclòs)</b>", st["p"]), f"{preus.eur2(c.total)} €"])
    t2 = Table(linies, colWidths=[None, 35 * mm])
    t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF1FC")),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("TEXTCOLOR", (0, 0), (-1, -1), TINTA),
                            ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTNAME", (1, -1), (1, -1), "Helvetica-Bold"),
                            ("LINEABOVE", (0, -1), (-1, -1), 0.8, TINTA), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [t2, Spacer(1, 18)]
    if c.carnet_codi and c.tipus == "matricula" and not c.taxa:
        story.append(Paragraph(e(_text_taxes(db, c)), st["petit"]))
    story.append(Paragraph("Aquest document acredita el pagament. La factura corresponent la rebràs de "
                           "l'autoescola. Referència del pagament: " + e(c.stripe_pagament or c.stripe_sessio or "—"),
                           st["petit"]))
    doc.build(story)
    return buf.getvalue()


def _text_taxes(db, c):
    from . import models
    carnet = db.query(models.Carnet).filter(models.Carnet.codi == c.carnet_codi).first()
    return (carnet.taxes_ca + ". Es paguen a l'autoescola quan es presenta la documentació per a l'examen."
            if carnet and carnet.taxes_ca else "")


def _net(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return "".join(ch if ch.isalnum() or ch in " -_" else "" for ch in t).strip().replace("  ", " ")


def nom_contracte(c):
    return _net(f"Contracte {c.carnet_codi} {c.nom_complet}") + ".pdf"


def nom_rebut(c):
    return _net(f"Rebut {c.num_rebut} {c.nom_complet}") + ".pdf"


def empremta(b: bytes) -> str:
    return hashlib.sha256(b or b"").hexdigest()
