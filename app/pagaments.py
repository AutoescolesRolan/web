"""Pagament amb Stripe Checkout: la targeta s'escriu a la pàgina segura de Stripe, mai a la nostra.

Variables d'entorn:
    STRIPE_SECRET_KEY      sk_test_… (proves) o sk_live_… (real)
    STRIPE_WEBHOOK_SECRET  whsec_…   (avís de Stripe quan el pagament es completa)

L'import el calcula sempre el servidor i es guarda a la metadata de la sessió; en tornar de
Stripe es comprova que el que s'ha pagat coincideix exactament amb la comanda.
"""
import os
import secrets
from types import SimpleNamespace

try:
    import stripe
except ImportError:      # s'instal·la des de requirements.txt
    stripe = None


def _clau():
    return (os.environ.get("STRIPE_SECRET_KEY") or "").strip()


def demo() -> bool:
    """Mode de demostració per veure la web a l'ordinador: pagament simulat, sense Stripe.
    Només amb ROLAN_DEMO=1 i sense clau de Stripe (mai s'activa sol a Render)."""
    return os.environ.get("ROLAN_DEMO") == "1" and not _clau()


def configurat() -> bool:
    return bool(stripe and _clau()) or demo()


def mode_proves() -> bool:
    return _clau().startswith("sk_test_") or demo()


_DEMO = {}      # sessions de pagament simulades (només en mode demostració)


def sessio_demo(sid):
    return _DEMO.get(sid) if demo() else None


def cents(eur) -> int:
    return int(round(float(eur or 0) * 100))


def crea_sessio(comanda, linies, url_ok: str, url_cancel: str):
    """linies: [(nom, import_eur)]. Torna la sessió de Stripe (té .url i .id)."""
    if demo():
        sid = "demo_" + secrets.token_urlsafe(12)
        total = sum(cents(p) for _, p in linies if cents(p) > 0)
        _DEMO[sid] = {"id": sid, "payment_status": "unpaid", "currency": "eur", "amount_total": total,
                      "metadata": {"comanda": comanda.token, "import_cents": str(total)},
                      "payment_intent": "pi_" + sid, "linies": linies,
                      "url_ok": url_ok.replace("{CHECKOUT_SESSION_ID}", sid), "url_cancel": url_cancel}
        return SimpleNamespace(id=sid, url=f"/pagament-demo/{sid}")
    stripe.api_key = _clau()
    items = [{"price_data": {"currency": "eur", "unit_amount": cents(preu), "product_data": {"name": nom[:250]}},
              "quantity": 1} for nom, preu in linies if cents(preu) > 0]
    total = sum(i["price_data"]["unit_amount"] for i in items)
    kw = dict(
        mode="payment", line_items=items, success_url=url_ok, cancel_url=url_cancel,
        client_reference_id=comanda.token, customer_email=comanda.email or None,
        metadata={"comanda": comanda.token, "tipus": comanda.tipus, "import_cents": str(total), "moneda": "eur"},
        payment_intent_data={"description": f"{comanda.producte} · {comanda.nom_complet}"[:500],
                             "metadata": {"comanda": comanda.token}},
        locale="es" if comanda.idioma == "es" else "auto",
    )
    kw = {k: v for k, v in kw.items() if v is not None}
    return stripe.checkout.Session.create(**kw)


def recupera(session_id: str):
    if demo():
        return _DEMO.get(session_id)
    stripe.api_key = _clau()
    return stripe.checkout.Session.retrieve(session_id)


def _get(obj, clau, defecte=None):
    try:
        return obj[clau]
    except Exception:
        return getattr(obj, clau, defecte)


def sessio_pagada(sess, comanda, total_eur) -> bool:
    """La sessió és d'aquesta comanda, està pagada i l'import és el que tocava."""
    if not sess:
        return False
    md = _get(sess, "metadata") or {}
    return (_get(sess, "payment_status") == "paid"
            and _get(md, "comanda") == comanda.token
            and str(_get(sess, "currency") or "").lower() == "eur"
            and int(_get(sess, "amount_total") or -1) == cents(total_eur)
            and _get(md, "import_cents") == str(cents(total_eur)))


def id_pagament(sess) -> str:
    pi = _get(sess, "payment_intent")
    if isinstance(pi, str):
        return pi
    return _get(pi, "id", "") or ""


def webhook_event(payload: bytes, signatura: str):
    secret = (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()
    if not (stripe and secret):
        return None
    return stripe.Webhook.construct_event(payload, signatura, secret)
