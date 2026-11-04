"""Dades inicials: les de la web actual d'Autoescoles Rolan (centres, horaris, preus).

Només s'omple el que és buit: si després es canvia alguna cosa al panell, no es trepitja.
"""
from . import models

AJUSTOS = {
    "escola_nom": "Autoescoles Rolan",
    "escola_rao_social": "",            # raó social completa (per a l'avís legal i el contracte)
    "escola_nif": "B63534333",
    "escola_domicili": "",              # domicili fiscal complet
    "escola_localitat": "Badalona",
    "escola_telefon": "934 647 857",
    "escola_email": "",                 # correu general (si és buit, el de Badalona Centre)
    "escola_titular": "",
    "escola_num_provincial": "",        # número d'autorització de la DGT
    "taxa_dgt": "94.05",                # taxa d'examen de la DGT (B, AM, A1, A2)
    "taxa_dgt_a": "28.87",              # taxa del carnet A
    "canon_pistes": "33.00",            # cànon de pistes (motos)
    "preu_expedient": "125",            # renovació d'expedient (text de la pàgina de preus)
    "correus_admin": "",                # qui rep còpia de totes les matrícules (separats per comes)
}

_TAXA = "Taxa oficial DGT | Tasa oficial DGT | 94,05"
_TEORIC = "Examen teòric | Examen teórico | 47,99"
_TEORIC_B = "Examen teòric | Examen teórico | 55,99"     # nov. 2026: només el carnet B
_TRAM = "Tramitació d'expedient | Tramitación de expediente | 125"
_CANON = "Cànon de pistes (obligatori per a l'examen de maniobres) | Canon de pistas (obligatorio para el examen de maniobras) | 33"
_MANIOBRES = "Examen de maniobres | Examen de maniobras | 61"
_CIRCULACIO = "Examen de circulació | Examen de circulación | 75"
_PR_MAN = "Pràctiques maniobres | Prácticas maniobras | 33,50"
_PR_CIRC = "Pràctiques circulació | Prácticas circulación | 53"
TARIFES = {   # «text català | text castellà | preu» per línia; es canvien al panell (Preus)
    "tarifes_classes_B": "\n".join(["Classe matí (6h–14h) | Clase mañana (6h–14h) | 36",
                                     "Classe tarda (14h–21h) | Clase tarde (14h–21h) | 42",
                                     "Classe dissabtes/festius | Clase sábados/festivos | 49"]),
    "tarifes_examens_B": "\n".join([_TAXA, _TEORIC_B, "Examen pràctic | Examen práctico | 72,50", _TRAM]),
    "tarifes_classes_AM": _PR_MAN,
    "tarifes_examens_AM": "\n".join([_TAXA, _TEORIC, _MANIOBRES, _TRAM, _CANON]),
    "tarifes_classes_A1": "\n".join([_PR_MAN, _PR_CIRC]),
    "tarifes_examens_A1": "\n".join([_TAXA, _TEORIC, _MANIOBRES, _CIRCULACIO, _TRAM, _CANON]),
    "tarifes_classes_A2": "\n".join([_PR_MAN, _PR_CIRC]),
    "tarifes_examens_A2": "\n".join([_TAXA, _TEORIC, _MANIOBRES, _CIRCULACIO, _TRAM, _CANON]),
    "tarifes_classes_A": "",
    "tarifes_examens_A": "\n".join([_TRAM, _CANON]),
}
AJUSTOS.update(TARIFES)
AJUSTOS["escola_email"] = "badalona@autoescolesrolan.cat"

CENTRES = [
    dict(codi="badalona-centre", nom="Badalona Centre", adreca="C/ Creu 49", cp_localitat="08912 Badalona",
         telefon="934 647 857", mobil="655 643 588", email="autoescolarolan05@gmail.com",
         maps="Autoescoles Rolan, Carrer de la Creu 49, 08912 Badalona",
         horari_ca="Només es fan cursos intensius", horari_es="Solo se hacen cursos intensivos", ordre=1),
    dict(codi="sant-adria", nom="Sant Adrià de Besòs", adreca="C/ Mossèn Cinto Verdaguer 15",
         cp_localitat="08930 Sant Adrià de Besòs", telefon="934 621 500", mobil="623 611 364",
         email="autoescolesrolan08@gmail.com",
         maps="Autoescoles Rolan, Carrer de Mossèn Cinto Verdaguer 15, 08930 Sant Adrià de Besòs",
         horari_ca="\n".join(f"{d} | 11:15–12:00 · 18:15–19:00" for d in ("Dilluns", "Dimarts", "Dimecres", "Dijous")),
         horari_es="\n".join(f"{d} | 11:15–12:00 · 18:15–19:00" for d in ("Lunes", "Martes", "Miércoles", "Jueves")),
         ordre=2),
    dict(codi="el-masnou", nom="El Masnou", adreca="C/ Itàlia 29", cp_localitat="08320 El Masnou",
         telefon="931 719 298", mobil="640 122 131", email="autoescolesrolan.elmasnou@gmail.com",
         maps="Autoescoles Rolan, Carrer d'Itàlia 29, 08320 El Masnou",
         horari_ca="Dilluns | 11:00–12:00 · 20:00–21:00\nDimarts | 16:00–17:00\nDimecres | 11:00–12:00 · 20:00–21:00\nDijous | 16:00–17:00",
         horari_es="Lunes | 11:00–12:00 · 20:00–21:00\nMartes | 16:00–17:00\nMiércoles | 11:00–12:00 · 20:00–21:00\nJueves | 16:00–17:00",
         ordre=3),
]

_T_B = ("Taxes de la DGT no incloses (94,05 €)", "Tasas de la DGT no incluidas (94,05 €)")
_T_MOTO = ("Taxes no incloses (94,05 € + cànon de pistes 33 €)", "Tasas no incluidas (94,05 € + canon de pistas 33 €)")

CARNETS = [
    dict(codi="B", nom_ca="Cotxe (turisme)", nom_es="Coche (turismo)", sub_ca="Turisme · a partir de 18 anys",
         sub_es="Turismo · a partir de 18 años", edat=18, ordre=1,
         examens_ca="Teòric comú i pràctic de circulació", examens_es="Teórico común y práctico de circulación",
         taxes_ca=_T_B[0], taxes_es=_T_B[1]),
    dict(codi="AM", nom_ca="Ciclomotor 49cc", nom_es="Ciclomotor 49cc", sub_ca="Fins a 49 cc · a partir de 15 anys",
         sub_es="Hasta 49 cc · a partir de 15 años", edat=15, ordre=2,
         examens_ca="Teòric AM i pràctic de maniobres", examens_es="Teórico AM y práctico de maniobras",
         taxes_ca=_T_MOTO[0], taxes_es=_T_MOTO[1]),
    dict(codi="A1", nom_ca="Motocicleta A1 (fins a 125 cc)", nom_es="Motocicleta A1 (hasta 125 cc)", sub_ca="Fins a 125 cc · a partir de 16 anys",
         sub_es="Hasta 125 cc · a partir de 16 años", edat=16, ordre=3,
         examens_ca="Teòric comú, teòric específic, maniobres i circulació",
         examens_es="Teórico común, teórico específico, maniobras y circulación",
         taxes_ca=_T_MOTO[0], taxes_es=_T_MOTO[1]),
    dict(codi="A2", nom_ca="Motocicleta A2 (fins a 47 CV)", nom_es="Motocicleta A2 (hasta 47 CV)", sub_ca="Fins a 47 CV · a partir de 18 anys",
         sub_es="Hasta 47 CV · a partir de 18 años", edat=18, ordre=4,
         examens_ca="Teòric comú, teòric específic, maniobres i circulació",
         examens_es="Teórico común, teórico específico, maniobras y circulación",
         taxes_ca=_T_MOTO[0], taxes_es=_T_MOTO[1]),
    dict(codi="A", nom_ca="Motocicleta A (des de A2)", nom_es="Motocicleta A (desde A2)", sub_ca="Més de 2 anys amb l'A2",
         sub_es="Más de 2 años con el A2", edat=20, ordre=5,
         examens_ca="Pràctic de maniobres i circulació", examens_es="Práctico de maniobras y circulación",
         taxes_ca="Taxes no incloses (28,87 € + cànon de pistes 33 €)",
         taxes_es="Tasas no incluidas (28,87 € + canon de pistas 33 €)"),
]

_BASE_B_CA = ["Matrícula", "Curs intensiu de teòrica", "Tramitació de l'expedient"]   # nov. 2026: sense examen teòric
_BASE_B_ES = ["Matrícula", "Curso intensivo de teórica", "Tramitación del expediente"]
_MOTO_COMPLET_CA = ["Matrícula", "Tramitació de l'expedient", "1r examen teòric comú + específic",
                    "1r examen de maniobres", "1r examen de circulació", "2 pràctiques de maniobres",
                    "3 pràctiques de circulació"]
_MOTO_COMPLET_ES = ["Matrícula", "Tramitación del expediente", "1.er examen teórico común + específico",
                    "1.er examen de maniobras", "1.er examen de circulación", "2 prácticas de maniobras",
                    "3 prácticas de circulación"]
_MOTO_ESP_CA = ["Matrícula", "Tramitació de l'expedient", "1r examen teòric específic", "1r examen de maniobres",
                "1r examen de circulació", "2 pràctiques de maniobres", "3 pràctiques de circulació"]
_MOTO_ESP_ES = ["Matrícula", "Tramitación del expediente", "1.er examen teórico específico",
                "1.er examen de maniobras", "1.er examen de circulación", "2 prácticas de maniobras",
                "3 prácticas de circulación"]

PACKS = {
    "B": [
        dict(codi="B1", nom_ca="Pack 1 · Sense pràctiques", nom_es="Pack 1 · Sin prácticas", classes=0, preu=199,
             inclou_ca=_BASE_B_CA, inclou_es=_BASE_B_ES, contracte="B.docx"),
        dict(codi="B2", nom_ca="Pack 2 · 5 pràctiques", nom_es="Pack 2 · 5 prácticas", classes=5, preu=399,
             inclou_ca=_BASE_B_CA + ["5 pràctiques de 45'"], inclou_es=_BASE_B_ES + ["5 prácticas de 45'"],
             contracte="B.docx"),
        dict(codi="B3", nom_ca="Pack 3 · 12 pràctiques", nom_es="Pack 3 · 12 prácticas", classes=12, preu=599,
             inclou_ca=_BASE_B_CA + ["12 pràctiques de 45'"], inclou_es=_BASE_B_ES + ["12 prácticas de 45'"],
             contracte="B.docx"),
        dict(codi="B4", nom_ca="Pack 4 · 20 pràctiques", nom_es="Pack 4 · 20 prácticas", classes=20, preu=799,
             inclou_ca=_BASE_B_CA + ["20 pràctiques de 45'"], inclou_es=_BASE_B_ES + ["20 prácticas de 45'"],
             contracte="B.docx", destacat=True),
    ],
    "AM": [
        dict(codi="AM", nom_ca="Pack AM · Ciclomotor", nom_es="Pack AM · Ciclomotor", classes=2, preu=319,
             inclou_ca=["Matrícula", "Tramitació de l'expedient", "1r examen teòric", "2 pràctiques de maniobres",
                        "1r examen de maniobres"],
             inclou_es=["Matrícula", "Tramitación del expediente", "1.er examen teórico", "2 prácticas de maniobras",
                        "1.er examen de maniobras"], contracte="AM.docx"),
    ],
    "A1": [
        dict(codi="A1-C", nom_ca="Sense carnet previ · Complet", nom_es="Sin carnet previo · Completo", classes=4,
             preu=595, inclou_ca=_MOTO_COMPLET_CA, inclou_es=_MOTO_COMPLET_ES, contracte="A1A2_dues_teoriques.docx"),
        dict(codi="A1-E", nom_ca="Ja tinc el carnet B · Només específica",
             nom_es="Ya tengo el carnet B · Solo específica", classes=2, preu=499,
             inclou_ca=_MOTO_ESP_CA, inclou_es=_MOTO_ESP_ES, contracte="A2_especifica_499.docx"),
    ],
    "A2": [
        dict(codi="A2-C", nom_ca="Sense carnet previ · Complet", nom_es="Sin carnet previo · Completo", classes=4,
             preu=595, inclou_ca=_MOTO_COMPLET_CA, inclou_es=_MOTO_COMPLET_ES, contracte="A1A2_dues_teoriques.docx"),
        dict(codi="A2-E", nom_ca="Ja tinc el carnet B · Només específica",
             nom_es="Ya tengo el carnet B · Solo específica", classes=2, preu=499,
             inclou_ca=_MOTO_ESP_CA, inclou_es=_MOTO_ESP_ES, contracte="A2_especifica_499.docx"),
        dict(codi="A2-D", nom_ca="Tinc l'A1 fa +2 anys · Només circulació",
             nom_es="Tengo el A1 desde hace +2 años · Solo circulación", classes=2, preu=389,
             inclou_ca=["Matrícula", "Tramitació de l'expedient", "2 pràctiques de circulació",
                        "1r examen de circulació"],
             inclou_es=["Matrícula", "Tramitación del expediente", "2 prácticas de circulación",
                        "1.er examen de circulación"], contracte="A2_directe_circulacio.docx"),
    ],
    "A": [
        dict(codi="A", nom_ca="Pack A · 2 maniobres + 4 circulació", nom_es="Pack A · 2 maniobras + 4 circulación", classes=6, preu=345,
             inclou_ca=["3 h de teòrica", "2 pràctiques de maniobres", "4 pràctiques de circulació"],
             inclou_es=["3 h de teórica", "2 prácticas de maniobras", "4 prácticas de circulación"],
             contracte="A.docx"),
    ],
}

PRACTIQUES = [(10, 341, 385), (15, 494, 560), (20, 636, 724), (30, 920, 1050)]


NOMS_ANTICS = {   # noms de la primera versió → noms de l'ERP
    "carnet": {"Cotxe": "B", "Ciclomotor": "AM", "Moto A1": "A1", "Moto A2": "A2", "Moto A": "A"},
    "pack": {"Pack ciclomotor": "AM", "Pack moto A": "A", "Ja tinc el B · Només teòrica específica": None,
             "Tinc l'A1 fa més de 2 anys · Només circulació": "A2-D"},
}


def _actualitza(db):
    nous_c = {c["codi"]: c for c in CARNETS}
    for c in db.query(models.Carnet).all():
        if c.nom_ca in NOMS_ANTICS["carnet"] and c.codi in nous_c:
            c.nom_ca, c.nom_es = nous_c[c.codi]["nom_ca"], nous_c[c.codi]["nom_es"]
    nous_p = {p["codi"]: p for llista in PACKS.values() for p in llista}
    for p in db.query(models.Pack).all():
        if p.nom_ca in NOMS_ANTICS["pack"] and p.codi in nous_p:
            p.nom_ca, p.nom_es, p.classes = nous_p[p.codi]["nom_ca"], nous_p[p.codi]["nom_es"], nous_p[p.codi]["classes"]
        elif p.codi in ("A1-C", "A2-C") and p.classes == 5:
            p.classes = 4
    e = db.get(models.Ajust, "escola_email")
    if e and not (e.valor or "").strip():
        e.valor = AJUSTOS["escola_email"]
    _canvis_preus_nov_2026(db)


PREUS_ANTICS = {   # nov. 2026: preus nous dels exàmens del carnet B (només si encara hi ha el preu antic)
    "Examen teòric | Examen teórico | 47,99": "Examen teòric | Examen teórico | 55,99",
    "Examen pràctic | Examen práctico | 69,50": "Examen pràctic | Examen práctico | 72,50",
}


def _canvis_preus_nov_2026(db):
    for a in db.query(models.Ajust).filter(models.Ajust.clau.in_(["tarifes_examens_B", "tarifes_classes_B"])).all():
        linies = (a.valor or "").split("\n")
        noves = [PREUS_ANTICS.get(l.strip(), l) for l in linies]
        if noves != linies:
            a.valor = "\n".join(noves)
            print(f"[inici] preus actualitzats a {a.clau}")
    # packs inicials del B: 5 / 12 / 20 pràctiques i sense examen teòric (un sol cop)
    marca_b = "fet_packs_b_nov_2026"
    if not db.get(models.Ajust, marca_b):
        nous = {p["codi"]: p for p in PACKS["B"]}
        for p in db.query(models.Pack).filter(models.Pack.codi.in_(list(nous))).all():
            n = nous[p.codi]
            p.nom_ca, p.nom_es, p.classes = n["nom_ca"], n["nom_es"], n["classes"]
            p.inclou_ca = "\n".join(n["inclou_ca"])
            p.inclou_es = "\n".join(n["inclou_es"])
        db.add(models.Ajust(clau=marca_b, valor="1"))
        print("[inici] packs del carnet B actualitzats")
    # els packs de pràctiques de matí deixen de sortir (un sol cop: si després es tornen a activar, es respecta)
    marca = "fet_packs_mati_nov_2026"
    if not db.get(models.Ajust, marca):
        for p in db.query(models.PackPractiques).filter(models.PackPractiques.franja == "MATI").all():
            p.actiu = False
        db.add(models.Ajust(clau=marca, valor="1"))
        print("[inici] packs de pràctiques de matí amagats")


def omple(db):
    """Afegeix el que falti (per codi): no toca res del que ja existeix."""
    for clau, valor in AJUSTOS.items():
        if not db.get(models.Ajust, clau):
            db.add(models.Ajust(clau=clau, valor=valor))
    for c in CENTRES:
        if not db.query(models.Centre).filter(models.Centre.codi == c["codi"]).first():
            db.add(models.Centre(actiu=True, **c))
    db.flush()
    # una web sense cap centre visible no deixa matricular ningú: si cap no surt, es tornen a mostrar
    if not db.query(models.Centre).filter(models.Centre.actiu == True).first():
        for c in db.query(models.Centre).all():
            c.actiu = True
    for c in CARNETS:
        carnet = db.query(models.Carnet).filter(models.Carnet.codi == c["codi"]).first()
        if not carnet:
            carnet = models.Carnet(actiu=True, **c)
            db.add(carnet)
            db.flush()
        for i, p in enumerate(PACKS.get(c["codi"], [])):
            if db.query(models.Pack).filter(models.Pack.codi == p["codi"]).first():
                continue
            p = dict(p)
            p["inclou_ca"] = "\n".join(p["inclou_ca"])
            p["inclou_es"] = "\n".join(p["inclou_es"])
            db.add(models.Pack(carnet_id=carnet.id, ordre=i, actiu=True, **p))
    if not db.query(models.PackPractiques).first():
        for n, mati, tarda in PRACTIQUES:      # nov. 2026: només es mostren els packs de tarda
            db.add(models.PackPractiques(classes=n, franja="MATI", preu=mati, actiu=False))
            db.add(models.PackPractiques(classes=n, franja="TARDA", preu=tarda, actiu=True))
    _actualitza(db)
    db.commit()
    print(f"[inici] centres: {db.query(models.Centre).count()} "
          f"({db.query(models.Centre).filter(models.Centre.actiu == True).count()} a la web) · "
          f"carnets: {db.query(models.Carnet).count()} · packs: {db.query(models.Pack).count()} · "
          f"packs de pràctiques: {db.query(models.PackPractiques).count()}")
