"""Taules de la web.

Pensada per poder passar-ho tot a l'ERP més endavant: cada comanda guarda les dades de
l'alumne, el producte (amb el nom i el preu del moment), el pagament i els PDF.
"""
from datetime import datetime

from sqlalchemy import (Boolean, Date, DateTime, Float, ForeignKey, Integer, LargeBinary,
                        String, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def ara():
    return datetime.utcnow()


class Ajust(Base):
    """Dades de l'autoescola i opcions (clau → valor)."""
    __tablename__ = "ajustos"
    clau: Mapped[str] = mapped_column(String(80), primary_key=True)
    valor: Mapped[str] = mapped_column(Text, default="")


class Centre(Base):
    __tablename__ = "centres"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codi: Mapped[str] = mapped_column(String(40), unique=True)
    nom: Mapped[str] = mapped_column(String(120))
    adreca: Mapped[str] = mapped_column(String(200), default="")
    cp_localitat: Mapped[str] = mapped_column(String(120), default="")
    telefon: Mapped[str] = mapped_column(String(40), default="")
    mobil: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(160), default="")      # secretaria del centre
    maps: Mapped[str] = mapped_column(String(300), default="")       # text per buscar a Google Maps
    horari_ca: Mapped[str] = mapped_column(Text, default="")         # una línia per dia: «Dilluns | 11:15–12:00 · 18:15–19:00»
    horari_es: Mapped[str] = mapped_column(Text, default="")
    actiu: Mapped[bool] = mapped_column(Boolean, default=True)
    ordre: Mapped[int] = mapped_column(Integer, default=0)


class Carnet(Base):
    __tablename__ = "carnets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codi: Mapped[str] = mapped_column(String(10), unique=True)
    nom_ca: Mapped[str] = mapped_column(String(120))
    nom_es: Mapped[str] = mapped_column(String(120))
    sub_ca: Mapped[str] = mapped_column(String(200), default="")      # «Fins a 125 cc, a partir de 16 anys»
    sub_es: Mapped[str] = mapped_column(String(200), default="")
    examens_ca: Mapped[str] = mapped_column(String(300), default="")
    examens_es: Mapped[str] = mapped_column(String(300), default="")
    taxes_ca: Mapped[str] = mapped_column(String(300), default="")    # el que no va inclòs
    taxes_es: Mapped[str] = mapped_column(String(300), default="")
    edat: Mapped[int] = mapped_column(Integer, default=18)            # edat mínima del permís
    actiu: Mapped[bool] = mapped_column(Boolean, default=True)
    ordre: Mapped[int] = mapped_column(Integer, default=0)
    packs: Mapped[list["Pack"]] = relationship(back_populates="carnet", order_by="Pack.ordre")


class Pack(Base):
    """El que es compra en matricular-se (amb contracte)."""
    __tablename__ = "packs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    carnet_id: Mapped[int] = mapped_column(ForeignKey("carnets.id"))
    codi: Mapped[str] = mapped_column(String(20), unique=True)
    nom_ca: Mapped[str] = mapped_column(String(160))
    nom_es: Mapped[str] = mapped_column(String(160))
    inclou_ca: Mapped[str] = mapped_column(Text, default="")          # una línia per element
    inclou_es: Mapped[str] = mapped_column(Text, default="")
    classes: Mapped[int] = mapped_column(Integer, default=0)
    preu: Mapped[float] = mapped_column(Float, default=0)
    contracte: Mapped[str] = mapped_column(String(120), default="")   # plantilla .docx de app/contractes
    destacat: Mapped[bool] = mapped_column(Boolean, default=False)
    actiu: Mapped[bool] = mapped_column(Boolean, default=True)
    ordre: Mapped[int] = mapped_column(Integer, default=0)
    carnet: Mapped[Carnet] = relationship(back_populates="packs")


class PackPractiques(Base):
    """Packs de pràctiques per a alumnes que ja estan matriculats (sense contracte)."""
    __tablename__ = "packs_practiques"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classes: Mapped[int] = mapped_column(Integer)
    franja: Mapped[str] = mapped_column(String(10))                    # MATI | TARDA
    preu: Mapped[float] = mapped_column(Float)
    actiu: Mapped[bool] = mapped_column(Boolean, default=True)


class Promocio(Base):
    __tablename__ = "promocions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(120))                      # «Black Friday»
    percentatge: Mapped[float] = mapped_column(Float, default=0)       # 20 = -20 %
    codi: Mapped[str] = mapped_column(String(40), default="")         # buit = s'aplica sola
    aplica: Mapped[str] = mapped_column(String(20), default="tot")     # tot | matricula | practiques
    inici: Mapped[datetime] = mapped_column(DateTime)
    fi: Mapped[datetime] = mapped_column(DateTime)
    banner_ca: Mapped[str] = mapped_column(String(200), default="")
    banner_es: Mapped[str] = mapped_column(String(200), default="")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Comanda(Base):
    """Una matrícula o una compra de pràctiques feta a la web."""
    __tablename__ = "comandes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tipus: Mapped[str] = mapped_column(String(20))                     # matricula | practiques
    estat: Mapped[str] = mapped_column(String(20), default="dades")    # dades | signada | pagada | cancel·lada
    idioma: Mapped[str] = mapped_column(String(2), default="ca")
    creat_en: Mapped[datetime] = mapped_column(DateTime, default=ara)
    pagat_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    centre_id: Mapped[int | None] = mapped_column(ForeignKey("centres.id"), nullable=True)
    # producte (copiat: si després canvia el preu, la comanda conserva el d'aquell moment)
    carnet_codi: Mapped[str] = mapped_column(String(10), default="")
    pack_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    producte: Mapped[str] = mapped_column(String(200), default="")
    producte_es: Mapped[str] = mapped_column(String(200), default="")
    preu_base: Mapped[float] = mapped_column(Float, default=0)
    descompte: Mapped[float] = mapped_column(Float, default=0)
    promocio: Mapped[str] = mapped_column(String(160), default="")
    taxa: Mapped[float] = mapped_column(Float, default=0)             # taxa DGT afegida al pagament
    canon: Mapped[float] = mapped_column(Float, default=0)            # cànon de pistes afegit al pagament
    total: Mapped[float] = mapped_column(Float, default=0)
    franja: Mapped[str] = mapped_column(String(20), default="")        # preferència d'horari
    contacte_preferit: Mapped[str] = mapped_column(String(20), default="")  # whatsapp | correu | trucada
    # alumne
    nom: Mapped[str] = mapped_column(String(120), default="")
    cognoms: Mapped[str] = mapped_column(String(160), default="")
    dni: Mapped[str] = mapped_column(String(20), default="")
    naixement: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    email: Mapped[str] = mapped_column(String(160), default="")
    telefon: Mapped[str] = mapped_column(String(40), default="")
    adreca: Mapped[str] = mapped_column(String(200), default="")
    cp: Mapped[str] = mapped_column(String(10), default="")
    localitat: Mapped[str] = mapped_column(String(120), default="")
    tutor_nom: Mapped[str] = mapped_column(String(200), default="")    # si és menor d'edat
    tutor_dni: Mapped[str] = mapped_column(String(20), default="")
    observacions: Mapped[str] = mapped_column(Text, default="")
    # contracte
    signatura: Mapped[str] = mapped_column(Text, default="")          # imatge PNG en data URL
    signat_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ip_signatura: Mapped[str] = mapped_column(String(64), default="")
    acceptacions: Mapped[str] = mapped_column(Text, default="")
    contracte_pdf: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # pagament
    stripe_sessio: Mapped[str] = mapped_column(String(255), default="", index=True)
    stripe_pagament: Mapped[str] = mapped_column(String(255), default="")
    num_rebut: Mapped[str] = mapped_column(String(30), default="")
    rebut_pdf: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # avisos
    correus: Mapped[str] = mapped_column(Text, default="")             # registre dels enviaments
    nota_interna: Mapped[str] = mapped_column(Text, default="")
    centre: Mapped[Centre | None] = relationship()

    def producte_en(self, idioma):
        return (self.producte_es or self.producte) if idioma == "es" else self.producte

    @property
    def nom_complet(self):
        return f"{self.nom} {self.cognoms}".strip()


class Missatge(Base):
    """Formulari de contacte (també arriba per correu a la secretaria del centre)."""
    __tablename__ = "missatges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creat_en: Mapped[datetime] = mapped_column(DateTime, default=ara)
    centre_id: Mapped[int | None] = mapped_column(ForeignKey("centres.id"), nullable=True)
    nom: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(160))
    telefon: Mapped[str] = mapped_column(String(40), default="")
    text: Mapped[str] = mapped_column(Text)
    enviat: Mapped[str] = mapped_column(String(200), default="")
    centre: Mapped[Centre | None] = relationship()


class Usuari(Base):
    """Persones que entren al panell intern (/gestio)."""
    __tablename__ = "usuaris"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True)
    nom: Mapped[str] = mapped_column(String(160), default="")
    contrasenya: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(20), default="secretaria")  # admin | secretaria
    centre_id: Mapped[int | None] = mapped_column(ForeignKey("centres.id"), nullable=True)
    actiu: Mapped[bool] = mapped_column(Boolean, default=True)
    centre: Mapped[Centre | None] = relationship()


class CodiAcces(Base):
    """Codi de 6 xifres enviat per correu per entrar al panell (segon factor)."""
    __tablename__ = "codis_acces"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuari_id: Mapped[int] = mapped_column(ForeignKey("usuaris.id"), index=True)
    sal: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(128))
    creat_en: Mapped[datetime] = mapped_column(DateTime, default=ara)
    caduca: Mapped[datetime] = mapped_column(DateTime)
    intents: Mapped[int] = mapped_column(Integer, default=0)
    usat: Mapped[bool] = mapped_column(Boolean, default=False)


class DispositiuConfiat(Base):
    """Navegador on s'ha marcat «Recorda aquest dispositiu»: no demana el codi durant 30 dies."""
    __tablename__ = "dispositius_confiats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuari_id: Mapped[int] = mapped_column(ForeignKey("usuaris.id"), index=True)
    hash: Mapped[str] = mapped_column(String(128), unique=True)
    caduca: Mapped[datetime] = mapped_column(DateTime)
