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
    "tarifes_cotxe": "\n".join([
        "Matrícula | Matrícula | 99,99",
        "Taxes d'examen (DGT) | Tasas de examen (DGT) | 94,05",
        "Ensenyament teòric | Enseñanza teórica | 150,00",
        "Renovació d'expedient | Renovación de expediente | 125,00",
        "Examen teòric | Examen teórico | 47,99",
        "Classe matí 45' (6 h a 14 h) | Clase mañana 45' (6 h a 14 h) | 36,00",
        "Classe tarda 45' (14 h a 21 h) | Clase tarde 45' (14 h a 21 h) | 42,00",
        "Classe dissabtes i festius | Clase sábados y festivos | 49,00",
        "Examen pràctic | Examen práctico | 69,50",
    ]),
    "tarifes_moto": "\n".join([
        "Examen teòric | Examen teórico | 47,99",
        "Pràctica de maniobres | Práctica de maniobras | 33,50",
        "Pràctica de circulació | Práctica de circulación | 53,00",
        "Examen de maniobres | Examen de maniobras | 61,00",
        "Examen de circulació | Examen de circulación | 75,00",
    ]),
}

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
    dict(codi="B", nom_ca="Cotxe", nom_es="Coche", sub_ca="Turisme · a partir de 18 anys",
         sub_es="Turismo · a partir de 18 años", edat=18, ordre=1,
         examens_ca="Teòric comú i pràctic de circulació", examens_es="Teórico común y práctico de circulación",
         taxes_ca=_T_B[0], taxes_es=_T_B[1]),
    dict(codi="AM", nom_ca="Ciclomotor", nom_es="Ciclomotor", sub_ca="Fins a 49 cc · a partir de 15 anys",
         sub_es="Hasta 49 cc · a partir de 15 años", edat=15, ordre=2,
         examens_ca="Teòric AM i pràctic de maniobres", examens_es="Teórico AM y práctico de maniobras",
         taxes_ca=_T_MOTO[0], taxes_es=_T_MOTO[1]),
    dict(codi="A1", nom_ca="Moto A1", nom_es="Moto A1", sub_ca="Fins a 125 cc · a partir de 16 anys",
         sub_es="Hasta 125 cc · a partir de 16 años", edat=16, ordre=3,
         examens_ca="Teòric comú, teòric específic, maniobres i circulació",
         examens_es="Teórico común, teórico específico, maniobras y circulación",
         taxes_ca=_T_MOTO[0], taxes_es=_T_MOTO[1]),
    dict(codi="A2", nom_ca="Moto A2", nom_es="Moto A2", sub_ca="Fins a 47 CV · a partir de 18 anys",
         sub_es="Hasta 47 CV · a partir de 18 años", edat=18, ordre=4,
         examens_ca="Teòric comú, teòric específic, maniobres i circulació",
         examens_es="Teórico común, teórico específico, maniobras y circulación",
         taxes_ca=_T_MOTO[0], taxes_es=_T_MOTO[1]),
    dict(codi="A", nom_ca="Moto A", nom_es="Moto A", sub_ca="Més de 2 anys amb l'A2",
         sub_es="Más de 2 años con el A2", edat=20, ordre=5,
         examens_ca="Pràctic de maniobres i circulació", examens_es="Práctico de maniobras y circulación",
         taxes_ca="Taxes no incloses (28,87 € + cànon de pistes 33 €)",
         taxes_es="Tasas no incluidas (28,87 € + canon de pistas 33 €)"),
]

_BASE_B_CA = ["Matrícula", "Curs intensiu de teòrica", "Tramitació de l'expedient", "1r examen teòric"]
_BASE_B_ES = ["Matrícula", "Curso intensivo de teórica", "Tramitación del expediente", "1.er examen teórico"]
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
        dict(codi="B2", nom_ca="Pack 2 · 6 pràctiques", nom_es="Pack 2 · 6 prácticas", classes=6, preu=399,
             inclou_ca=_BASE_B_CA + ["6 pràctiques de 45'"], inclou_es=_BASE_B_ES + ["6 prácticas de 45'"],
             contracte="B.docx"),
        dict(codi="B3", nom_ca="Pack 3 · 13 pràctiques", nom_es="Pack 3 · 13 prácticas", classes=13, preu=599,
             inclou_ca=_BASE_B_CA + ["13 pràctiques de 45'"], inclou_es=_BASE_B_ES + ["13 prácticas de 45'"],
             contracte="B.docx"),
        dict(codi="B4", nom_ca="Pack 4 · 21 pràctiques", nom_es="Pack 4 · 21 prácticas", classes=21, preu=799,
             inclou_ca=_BASE_B_CA + ["21 pràctiques de 45'"], inclou_es=_BASE_B_ES + ["21 prácticas de 45'"],
             contracte="B.docx", destacat=True),
    ],
    "AM": [
        dict(codi="AM", nom_ca="Pack ciclomotor", nom_es="Pack ciclomotor", classes=2, preu=319,
             inclou_ca=["Matrícula", "Tramitació de l'expedient", "1r examen teòric", "2 pràctiques de maniobres",
                        "1r examen de maniobres"],
             inclou_es=["Matrícula", "Tramitación del expediente", "1.er examen teórico", "2 prácticas de maniobras",
                        "1.er examen de maniobras"], contracte="AM.docx"),
    ],
    "A1": [
        dict(codi="A1-C", nom_ca="Sense carnet previ · Complet", nom_es="Sin carnet previo · Completo", classes=5,
             preu=595, inclou_ca=_MOTO_COMPLET_CA, inclou_es=_MOTO_COMPLET_ES, contracte="A1A2_dues_teoriques.docx"),
        dict(codi="A1-E", nom_ca="Ja tinc el B · Només teòrica específica",
             nom_es="Ya tengo el B · Solo teórica específica", classes=5, preu=499,
             inclou_ca=_MOTO_ESP_CA, inclou_es=_MOTO_ESP_ES, contracte="A2_especifica_499.docx"),
    ],
    "A2": [
        dict(codi="A2-C", nom_ca="Sense carnet previ · Complet", nom_es="Sin carnet previo · Completo", classes=5,
             preu=595, inclou_ca=_MOTO_COMPLET_CA, inclou_es=_MOTO_COMPLET_ES, contracte="A1A2_dues_teoriques.docx"),
        dict(codi="A2-E", nom_ca="Ja tinc el B · Només teòrica específica",
             nom_es="Ya tengo el B · Solo teórica específica", classes=5, preu=499,
             inclou_ca=_MOTO_ESP_CA, inclou_es=_MOTO_ESP_ES, contracte="A2_especifica_499.docx"),
        dict(codi="A2-D", nom_ca="Tinc l'A1 fa més de 2 anys · Només circulació",
             nom_es="Tengo el A1 hace más de 2 años · Solo circulación", classes=2, preu=389,
             inclou_ca=["Matrícula", "Tramitació de l'expedient", "2 pràctiques de circulació",
                        "1r examen de circulació"],
             inclou_es=["Matrícula", "Tramitación del expediente", "2 prácticas de circulación",
                        "1.er examen de circulación"], contracte="A2_directe_circulacio.docx"),
    ],
    "A": [
        dict(codi="A", nom_ca="Pack moto A", nom_es="Pack moto A", classes=6, preu=345,
             inclou_ca=["3 h de teòrica", "2 pràctiques de maniobres", "4 pràctiques de circulació"],
             inclou_es=["3 h de teórica", "2 prácticas de maniobras", "4 prácticas de circulación"],
             contracte="A.docx"),
    ],
}

PRACTIQUES = [(10, 341, 385), (15, 494, 560), (20, 636, 724), (30, 920, 1050)]


def omple(db):
    for clau, valor in AJUSTOS.items():
        if not db.get(models.Ajust, clau):
            db.add(models.Ajust(clau=clau, valor=valor))
    if not db.query(models.Centre).first():
        for c in CENTRES:
            db.add(models.Centre(**c))
    if not db.query(models.Carnet).first():
        for c in CARNETS:
            carnet = models.Carnet(**c)
            db.add(carnet)
            db.flush()
            for i, p in enumerate(PACKS.get(c["codi"], [])):
                p = dict(p)
                p["inclou_ca"] = "\n".join(p["inclou_ca"])
                p["inclou_es"] = "\n".join(p["inclou_es"])
                db.add(models.Pack(carnet_id=carnet.id, ordre=i, **p))
    if not db.query(models.PackPractiques).first():
        for n, mati, tarda in PRACTIQUES:
            db.add(models.PackPractiques(classes=n, franja="MATI", preu=mati))
            db.add(models.PackPractiques(classes=n, franja="TARDA", preu=tarda))
    db.commit()
