"""Còpia de seguretat descarregable des del panell (/gestio → Dades): un ZIP amb
- matricules.xlsx: comandes i missatges, per llegir-les amb l'Excel;
- contractes/ i rebuts/: els PDF de cada matrícula;
- dades.json: totes les taules (preus, packs, promocions, centres, ajustos, comandes…) per poder-les restaurar.
No s'hi posen les contrasenyes del panell ni els codis d'accés."""
import base64
import json
import os
import re
import tempfile
import zipfile
from datetime import date, datetime

from sqlalchemy import select

from . import documents, models
from .db import Base

SENSE_TAULES = {"codis_acces", "dispositius_confiats"}
SENSE_CAMPS = {("usuaris", "contrasenya")}
# els PDF ja van com a fitxers a part: al JSON no hi cal repetir-los
PDF_A_PART = {("comandes", "contracte_pdf"), ("comandes", "rebut_pdf")}


def _valor(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (bytes, bytearray, memoryview)):
        return "base64:" + base64.b64encode(bytes(v)).decode()
    return v


def _taules(db):
    dades = {}
    for taula in Base.metadata.sorted_tables:
        if taula.name in SENSE_TAULES:
            continue
        cols = [c for c in taula.columns if (taula.name, c.name) not in SENSE_CAMPS | PDF_A_PART]
        files = db.execute(select(*cols)).all()
        dades[taula.name] = [{c.name: _valor(v) for c, v in zip(cols, fila)} for fila in files]
    return dades


def _net(txt):
    return re.sub(r"[^\w.\- ]+", "_", txt or "").strip() or "document"


def genera(db):
    """Crea el ZIP en un fitxer temporal. Retorna (camí, nom per descarregar)."""
    from openpyxl import Workbook
    from .panell import fulla_comandes, fulla_missatges

    ara = datetime.now()
    nom = f"copia-web-rolan-{ara.strftime('%Y-%m-%d-%H%M')}.zip"
    fd, cami = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    llista = db.query(models.Comanda).order_by(models.Comanda.id).all()
    with zipfile.ZipFile(cami, "w", zipfile.ZIP_DEFLATED) as z:
        wb = Workbook()
        fulla_comandes(wb.active, llista)
        fulla_missatges(wb.create_sheet(), db.query(models.Missatge).order_by(models.Missatge.id).all())
        tmp = tempfile.SpooledTemporaryFile()
        wb.save(tmp)
        tmp.seek(0)
        z.writestr("matricules.xlsx", tmp.read())
        for c in llista:
            if c.contracte_pdf:
                z.writestr(f"contractes/{c.id:05d}-{_net(documents.nom_contracte(c))}", bytes(c.contracte_pdf))
            if c.rebut_pdf:
                z.writestr(f"rebuts/{c.id:05d}-{_net(documents.nom_rebut(c))}", bytes(c.rebut_pdf))
        z.writestr("dades.json", json.dumps({"creada": ara.isoformat(timespec="seconds"), "taules": _taules(db)},
                                            ensure_ascii=False, indent=1))
    return cami, nom
