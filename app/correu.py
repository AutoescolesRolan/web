"""Enviament de correus.

Mètode preferent: Resend (variables RESEND_API_KEY i MAIL_FROM). Alternativa: SMTP
(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, MAIL_FROM). Si no hi ha res configurat,
el correu no s'envia però tampoc es trenca res: queda apuntat a la comanda i es pot
tornar a enviar des del panell.
"""
import base64
import json
import os
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

ENVIATS = []          # només per a les proves: els correus «enviats» sense configuració


def _remitent():
    return (os.environ.get("MAIL_FROM") or "").strip() or "Autoescoles Rolan <onboarding@resend.dev>"


def configurat() -> bool:
    return bool((os.environ.get("RESEND_API_KEY") or "").strip() or (os.environ.get("SMTP_HOST") or "").strip())


def envia(a, assumpte: str, html: str, text: str, adjunts=None, respondre_a: str = "") -> tuple:
    """a: correu o llista de correus. adjunts: [(nom, bytes, mime)]. Torna (ok, missatge)."""
    destinataris = [x.strip() for x in ([a] if isinstance(a, str) else a) if x and x.strip()]
    if not destinataris:
        return False, "sense destinatari"
    adjunts = adjunts or []
    clau = (os.environ.get("RESEND_API_KEY") or "").strip()
    if clau:
        dades = {"from": _remitent(), "to": destinataris, "subject": assumpte, "html": html, "text": text}
        if respondre_a:
            dades["reply_to"] = respondre_a
        if adjunts:
            dades["attachments"] = [{"filename": n, "content": base64.b64encode(b).decode()} for n, b, _ in adjunts]
        req = urllib.request.Request(
            "https://api.resend.com/emails", data=json.dumps(dades).encode(), method="POST",
            headers={"Authorization": f"Bearer {clau}", "Content-Type": "application/json",
                     "User-Agent": "RolanWeb/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return 200 <= r.status < 300, f"enviat (Resend {r.status})"
        except urllib.error.HTTPError as e:
            try:
                detall = e.read().decode("utf-8", "ignore")[:300]
            except Exception:
                detall = ""
            return False, f"Resend ha respost {e.code}: {detall}"
        except Exception as e:
            return False, f"error amb Resend: {e}"

    host = (os.environ.get("SMTP_HOST") or "").strip()
    if host:
        m = EmailMessage()
        m["From"] = _remitent()
        m["To"] = ", ".join(destinataris)
        m["Subject"] = assumpte
        if respondre_a:
            m["Reply-To"] = respondre_a
        m.set_content(text)
        m.add_alternative(html, subtype="html")
        for n, b, mime in adjunts:
            mt, _, st = (mime or "application/octet-stream").partition("/")
            m.add_attachment(b, maintype=mt, subtype=st or "octet-stream", filename=n)
        try:
            with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT") or 587), timeout=25) as s:
                s.starttls()
                if os.environ.get("SMTP_USER"):
                    s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
                s.send_message(m)
            return True, "enviat (SMTP)"
        except Exception as e:
            return False, f"error SMTP: {e}"

    ENVIATS.append({"a": destinataris, "assumpte": assumpte, "text": text,
                    "adjunts": [n for n, _, _ in adjunts], "respondre_a": respondre_a})
    print(f"[correu] (sense configurar) → {destinataris}: {assumpte}")
    return False, "correu no configurat"
